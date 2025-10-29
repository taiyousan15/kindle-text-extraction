"""
Security Dependencies

FastAPI 依存性注入用の認証関数群
"""
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from typing import Optional
import logging

from app.core.database import get_db
from app.services.auth_service import auth_service
from app.models.user import User

logger = logging.getLogger(__name__)

# Bearer トークン認証スキーム
security = HTTPBearer()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
) -> User:
    """
    現在のユーザーを取得（認証必須）

    Args:
        credentials: HTTPベアラートークン
        db: データベースセッション

    Returns:
        User: 認証されたユーザー

    Raises:
        HTTPException: トークンが無効、期限切れ、ユーザーが存在しない場合
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    # トークンを取得
    token = credentials.credentials

    # トークンをデコード
    payload = auth_service.decode_token(token)
    if payload is None:
        logger.warning("Invalid token provided")
        raise credentials_exception

    # トークンタイプを確認
    token_type = payload.get("type")
    if token_type != "access":
        logger.warning(f"Invalid token type: {token_type}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token type. Access token required.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # ユーザーIDを取得
    user_id: Optional[int] = payload.get("sub")
    if user_id is None:
        logger.warning("Token missing user ID")
        raise credentials_exception

    # ユーザーを取得
    user = auth_service.get_user_by_id(db, user_id=int(user_id))
    if user is None:
        logger.warning(f"User not found: {user_id}")
        raise credentials_exception

    logger.debug(f"User authenticated: {user.email}")
    return user


async def get_current_active_user(
    current_user: User = Depends(get_current_user)
) -> User:
    """
    現在のアクティブユーザーを取得

    Args:
        current_user: 認証されたユーザー

    Returns:
        User: アクティブなユーザー

    Raises:
        HTTPException: ユーザーが非アクティブの場合
    """
    if not current_user.is_active:
        logger.warning(f"Inactive user attempted access: {current_user.email}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Inactive user"
        )

    return current_user


async def get_current_user_optional(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: Session = Depends(get_db)
) -> Optional[User]:
    """
    現在のユーザーを取得（認証オプション）

    認証トークンがない場合はNoneを返す。
    トークンがある場合は検証を行う。

    Args:
        credentials: HTTPベアラートークン（オプション）
        db: データベースセッション

    Returns:
        Optional[User]: 認証されたユーザー、またはNone
    """
    if credentials is None:
        return None

    try:
        return await get_current_user(credentials, db)
    except HTTPException:
        return None


def require_admin(current_user: User = Depends(get_current_active_user)) -> User:
    """
    管理者権限を要求（将来の拡張用）

    Args:
        current_user: 認証されたアクティブユーザー

    Returns:
        User: 管理者ユーザー

    Raises:
        HTTPException: ユーザーが管理者でない場合

    Note:
        現在のUserモデルには is_admin フィールドがないため、
        将来の拡張として実装準備のみ。
    """
    # 将来の拡張: User モデルに is_admin フィールドを追加
    # if not current_user.is_admin:
    #     raise HTTPException(
    #         status_code=status.HTTP_403_FORBIDDEN,
    #         detail="Admin privileges required"
    #     )

    # 現時点では全ユーザーを許可（MVP対応）
    logger.warning("Admin check not implemented - allowing all active users")
    return current_user
