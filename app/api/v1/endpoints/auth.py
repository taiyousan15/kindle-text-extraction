"""
Authentication Endpoints

ユーザー登録、ログイン、トークン管理のエンドポイント
+ Rate Limiting (Phase 1-8) - Brute Force Protection
"""
from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
import logging

from app.core.database import get_db
from app.core.security import get_current_active_user
from app.services.auth_service import auth_service
from app.schemas.auth import (
    UserCreate,
    UserLogin,
    UserResponse,
    LoginResponse,
    RegisterResponse,
    Token,
    RefreshTokenRequest,
    MessageResponse,
    PasswordChange
)
from app.models.user import User
from app.core.config import settings
from app.services.rate_limiter import limiter, RateLimitConfig

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/register", response_model=RegisterResponse, status_code=status.HTTP_201_CREATED)
@limiter.limit(RateLimitConfig.AUTH)
async def register(
    request: Request,
    user_data: UserCreate,
    db: Session = Depends(get_db)
) -> RegisterResponse:
    """
    新規ユーザー登録

    Args:
        user_data: ユーザー登録情報（email, password, name）
        db: データベースセッション

    Returns:
        RegisterResponse: 登録されたユーザー情報

    Raises:
        HTTPException: メールアドレスが既に使用されている場合
    """
    logger.info(f"New user registration attempt: {user_data.email}")

    try:
        # ユーザー作成
        user = auth_service.create_user(
            db=db,
            email=user_data.email,
            password=user_data.password,
            name=user_data.name
        )

        logger.info(f"User registered successfully: {user.email} (ID: {user.id})")

        return RegisterResponse(
            user=UserResponse.model_validate(user),
            message="User registered successfully"
        )

    except ValueError as e:
        logger.warning(f"Registration failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except IntegrityError as e:
        db.rollback()
        logger.error(f"Database integrity error during registration: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    except Exception as e:
        db.rollback()
        logger.error(f"Unexpected error during registration: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to register user"
        )


@router.post("/login", response_model=LoginResponse)
@limiter.limit(RateLimitConfig.AUTH)
async def login(
    request: Request,
    credentials: UserLogin,
    db: Session = Depends(get_db)
) -> LoginResponse:
    """
    ユーザーログイン

    Args:
        credentials: ログイン情報（email, password）
        db: データベースセッション

    Returns:
        LoginResponse: アクセストークン、リフレッシュトークン、ユーザー情報

    Raises:
        HTTPException: 認証失敗時
    """
    logger.info(f"Login attempt: {credentials.email}")

    # ユーザー認証
    user = auth_service.authenticate_user(
        db=db,
        email=credentials.email,
        password=credentials.password
    )

    if not user:
        logger.warning(f"Failed login attempt: {credentials.email}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # トークン生成
    token_data = {
        "sub": str(user.id),
        "email": user.email
    }

    access_token = auth_service.create_access_token(data=token_data)
    refresh_token = auth_service.create_refresh_token(data=token_data)

    logger.info(f"User logged in successfully: {user.email} (ID: {user.id})")

    return LoginResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,  # 秒単位
        user=UserResponse.model_validate(user)
    )


@router.post("/refresh", response_model=Token)
async def refresh_token(
    refresh_request: RefreshTokenRequest,
    db: Session = Depends(get_db)
) -> Token:
    """
    アクセストークンをリフレッシュ

    Args:
        refresh_request: リフレッシュトークン
        db: データベースセッション

    Returns:
        Token: 新しいアクセストークンとリフレッシュトークン

    Raises:
        HTTPException: リフレッシュトークンが無効な場合
    """
    # リフレッシュトークンをデコード
    payload = auth_service.decode_token(refresh_request.refresh_token)

    if payload is None:
        logger.warning("Invalid refresh token provided")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # トークンタイプを確認
    if payload.get("type") != "refresh":
        logger.warning("Non-refresh token used for refresh endpoint")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token type",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # ユーザーIDを取得
    user_id = payload.get("sub")
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # ユーザーを取得
    user = auth_service.get_user_by_id(db, user_id=int(user_id))
    if user is None or not user.is_active:
        logger.warning(f"Refresh token for non-existent or inactive user: {user_id}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # 新しいトークンを生成
    token_data = {
        "sub": str(user.id),
        "email": user.email
    }

    new_access_token = auth_service.create_access_token(data=token_data)
    new_refresh_token = auth_service.create_refresh_token(data=token_data)

    logger.info(f"Token refreshed for user: {user.email} (ID: {user.id})")

    return Token(
        access_token=new_access_token,
        refresh_token=new_refresh_token,
        token_type="bearer",
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60
    )


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(
    current_user: User = Depends(get_current_active_user)
) -> UserResponse:
    """
    現在のユーザー情報を取得

    Args:
        current_user: 認証されたユーザー（依存性注入）

    Returns:
        UserResponse: ユーザー情報
    """
    logger.debug(f"User info requested: {current_user.email}")
    return UserResponse.model_validate(current_user)


@router.post("/logout", response_model=MessageResponse)
async def logout(
    current_user: User = Depends(get_current_active_user)
) -> MessageResponse:
    """
    ログアウト

    Note:
        JWTトークンはステートレスなため、サーバー側での無効化は実装していない。
        クライアント側でトークンを削除することでログアウトを実現する。
        将来的には Redis にトークンブラックリストを実装可能。

    Args:
        current_user: 認証されたユーザー（依存性注入）

    Returns:
        MessageResponse: ログアウト成功メッセージ
    """
    logger.info(f"User logged out: {current_user.email} (ID: {current_user.id})")

    return MessageResponse(
        message="Logged out successfully. Please delete the token on the client side."
    )


@router.post("/change-password", response_model=MessageResponse)
async def change_password(
    password_data: PasswordChange,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
) -> MessageResponse:
    """
    パスワード変更

    Args:
        password_data: パスワード変更情報（old_password, new_password）
        current_user: 認証されたユーザー（依存性注入）
        db: データベースセッション

    Returns:
        MessageResponse: パスワード変更成功メッセージ

    Raises:
        HTTPException: 現在のパスワードが正しくない場合
    """
    logger.info(f"Password change requested: {current_user.email}")

    # 現在のパスワードを検証
    if not auth_service.verify_password(password_data.old_password, current_user.hashed_password):
        logger.warning(f"Invalid old password for user: {current_user.email}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect"
        )

    # 新しいパスワードをハッシュ化
    new_hashed_password = auth_service.get_password_hash(password_data.new_password)

    # パスワードを更新
    current_user.hashed_password = new_hashed_password
    db.commit()

    logger.info(f"Password changed successfully: {current_user.email}")

    return MessageResponse(
        message="Password changed successfully"
    )
