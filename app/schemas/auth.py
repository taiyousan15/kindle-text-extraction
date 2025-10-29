"""
Authentication Schemas

認証関連のPydanticスキーマ定義
"""
from pydantic import BaseModel, EmailStr, Field, ConfigDict
from typing import Optional
from datetime import datetime


# ========================================
# User Schemas
# ========================================

class UserBase(BaseModel):
    """ユーザーベーススキーマ"""
    email: EmailStr
    name: Optional[str] = None


class UserCreate(BaseModel):
    """ユーザー登録リクエスト"""
    email: EmailStr = Field(..., description="メールアドレス")
    password: str = Field(..., min_length=8, max_length=100, description="パスワード（8文字以上）")
    name: Optional[str] = Field(None, max_length=255, description="ユーザー名（オプション）")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "email": "user@example.com",
                "password": "securepassword123",
                "name": "山田太郎"
            }
        }
    )


class UserLogin(BaseModel):
    """ユーザーログインリクエスト"""
    email: EmailStr = Field(..., description="メールアドレス")
    password: str = Field(..., description="パスワード")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "email": "user@example.com",
                "password": "securepassword123"
            }
        }
    )


class UserResponse(BaseModel):
    """ユーザー情報レスポンス"""
    id: int
    email: EmailStr
    name: Optional[str] = None
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class UserUpdate(BaseModel):
    """ユーザー情報更新リクエスト"""
    name: Optional[str] = Field(None, max_length=255, description="ユーザー名")
    email: Optional[EmailStr] = Field(None, description="メールアドレス")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "name": "新しい名前",
                "email": "newemail@example.com"
            }
        }
    )


class PasswordChange(BaseModel):
    """パスワード変更リクエスト"""
    old_password: str = Field(..., description="現在のパスワード")
    new_password: str = Field(..., min_length=8, max_length=100, description="新しいパスワード（8文字以上）")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "old_password": "oldpassword123",
                "new_password": "newsecurepassword456"
            }
        }
    )


# ========================================
# Token Schemas
# ========================================

class Token(BaseModel):
    """トークンレスポンス"""
    access_token: str = Field(..., description="アクセストークン（有効期限: 30分）")
    refresh_token: str = Field(..., description="リフレッシュトークン（有効期限: 7日）")
    token_type: str = Field(default="bearer", description="トークンタイプ")
    expires_in: int = Field(..., description="アクセストークン有効期限（秒）")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                "token_type": "bearer",
                "expires_in": 1800
            }
        }
    )


class TokenData(BaseModel):
    """トークンペイロードデータ"""
    sub: Optional[int] = None  # subject (user_id)
    email: Optional[str] = None
    exp: Optional[datetime] = None  # expiration time
    iat: Optional[datetime] = None  # issued at
    token_type: Optional[str] = None  # "access" or "refresh"


class RefreshTokenRequest(BaseModel):
    """リフレッシュトークンリクエスト"""
    refresh_token: str = Field(..., description="リフレッシュトークン")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
            }
        }
    )


# ========================================
# Response Schemas
# ========================================

class RegisterResponse(BaseModel):
    """ユーザー登録レスポンス"""
    user: UserResponse
    message: str = "User registered successfully"

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "user": {
                    "id": 1,
                    "email": "user@example.com",
                    "name": "山田太郎",
                    "is_active": True,
                    "created_at": "2025-01-01T00:00:00",
                    "updated_at": "2025-01-01T00:00:00"
                },
                "message": "User registered successfully"
            }
        }
    )


class LoginResponse(BaseModel):
    """ログインレスポンス"""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int
    user: UserResponse

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                "token_type": "bearer",
                "expires_in": 1800,
                "user": {
                    "id": 1,
                    "email": "user@example.com",
                    "name": "山田太郎",
                    "is_active": True,
                    "created_at": "2025-01-01T00:00:00",
                    "updated_at": "2025-01-01T00:00:00"
                }
            }
        }
    )


class MessageResponse(BaseModel):
    """汎用メッセージレスポンス"""
    message: str

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "message": "Operation successful"
            }
        }
    )
