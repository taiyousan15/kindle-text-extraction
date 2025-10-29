"""
Authentication Service

JWT認証、パスワードハッシュ、トークン生成・検証を行うサービス
"""
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy.orm import Session
import logging

from app.models.user import User
from app.core.config import settings

logger = logging.getLogger(__name__)

# パスワードハッシュ化設定
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class AuthService:
    """認証サービスクラス"""

    @staticmethod
    def verify_password(plain_password: str, hashed_password: str) -> bool:
        """
        パスワードを検証

        Args:
            plain_password: プレーンテキストパスワード
            hashed_password: ハッシュ化されたパスワード

        Returns:
            bool: パスワードが一致すればTrue
        """
        return pwd_context.verify(plain_password, hashed_password)

    @staticmethod
    def get_password_hash(password: str) -> str:
        """
        パスワードをハッシュ化

        Args:
            password: プレーンテキストパスワード

        Returns:
            str: ハッシュ化されたパスワード
        """
        return pwd_context.hash(password)

    @staticmethod
    def create_access_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
        """
        アクセストークンを生成

        Args:
            data: トークンに含めるデータ（通常はuser_id, email）
            expires_delta: 有効期限（指定がなければ設定値を使用）

        Returns:
            str: JWT アクセストークン
        """
        to_encode = data.copy()

        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)

        to_encode.update({
            "exp": expire,
            "iat": datetime.utcnow(),
            "type": "access"
        })

        encoded_jwt = jwt.encode(
            to_encode,
            settings.JWT_SECRET_KEY,
            algorithm=settings.JWT_ALGORITHM
        )

        return encoded_jwt

    @staticmethod
    def create_refresh_token(data: Dict[str, Any]) -> str:
        """
        リフレッシュトークンを生成

        Args:
            data: トークンに含めるデータ（通常はuser_id, email）

        Returns:
            str: JWT リフレッシュトークン
        """
        to_encode = data.copy()
        expire = datetime.utcnow() + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)

        to_encode.update({
            "exp": expire,
            "iat": datetime.utcnow(),
            "type": "refresh"
        })

        encoded_jwt = jwt.encode(
            to_encode,
            settings.JWT_SECRET_KEY,
            algorithm=settings.JWT_ALGORITHM
        )

        return encoded_jwt

    @staticmethod
    def decode_token(token: str) -> Optional[Dict[str, Any]]:
        """
        JWTトークンをデコード

        Args:
            token: JWTトークン

        Returns:
            Optional[Dict[str, Any]]: デコードされたペイロード、失敗時はNone
        """
        try:
            payload = jwt.decode(
                token,
                settings.JWT_SECRET_KEY,
                algorithms=[settings.JWT_ALGORITHM]
            )
            return payload
        except JWTError as e:
            logger.warning(f"JWT decode error: {e}")
            return None

    @staticmethod
    def authenticate_user(db: Session, email: str, password: str) -> Optional[User]:
        """
        ユーザーを認証

        Args:
            db: データベースセッション
            email: メールアドレス
            password: パスワード

        Returns:
            Optional[User]: 認証成功時はUserオブジェクト、失敗時はNone
        """
        user = db.query(User).filter(User.email == email).first()

        if not user:
            logger.info(f"User not found: {email}")
            return None

        if not AuthService.verify_password(password, user.hashed_password):
            logger.info(f"Invalid password for user: {email}")
            return None

        if not user.is_active:
            logger.info(f"Inactive user attempted login: {email}")
            return None

        logger.info(f"User authenticated successfully: {email}")
        return user

    @staticmethod
    def create_user(db: Session, email: str, password: str, name: Optional[str] = None) -> User:
        """
        新規ユーザーを作成

        Args:
            db: データベースセッション
            email: メールアドレス
            password: パスワード
            name: ユーザー名（オプション）

        Returns:
            User: 作成されたUserオブジェクト

        Raises:
            ValueError: ユーザーが既に存在する場合
        """
        # メールアドレスの重複チェック
        existing_user = db.query(User).filter(User.email == email).first()
        if existing_user:
            raise ValueError(f"User with email {email} already exists")

        # パスワードをハッシュ化
        hashed_password = AuthService.get_password_hash(password)

        # ユーザー作成
        user = User(
            email=email,
            name=name or email.split("@")[0],  # デフォルト名はメールのローカル部
            hashed_password=hashed_password,
            is_active=True
        )

        db.add(user)
        db.commit()
        db.refresh(user)

        logger.info(f"User created successfully: {email}")
        return user

    @staticmethod
    def get_user_by_email(db: Session, email: str) -> Optional[User]:
        """
        メールアドレスでユーザーを取得

        Args:
            db: データベースセッション
            email: メールアドレス

        Returns:
            Optional[User]: ユーザーオブジェクト、存在しなければNone
        """
        return db.query(User).filter(User.email == email).first()

    @staticmethod
    def get_user_by_id(db: Session, user_id: int) -> Optional[User]:
        """
        IDでユーザーを取得

        Args:
            db: データベースセッション
            user_id: ユーザーID

        Returns:
            Optional[User]: ユーザーオブジェクト、存在しなければNone
        """
        return db.query(User).filter(User.id == user_id).first()


# シングルトンインスタンス
auth_service = AuthService()
