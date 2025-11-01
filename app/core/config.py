"""
Application Configuration
環境変数から設定を読み込み
"""
import os
from typing import List
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """アプリケーション設定"""

    # ================== Database ==================
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL",
        "postgresql://kindle_user:kindle_password@localhost:5432/kindle_ocr"
    )

    # ================== Redis ==================
    REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")

    # ================== Rate Limiting ==================
    RATE_LIMIT_ENABLED: bool = os.getenv("RATE_LIMIT_ENABLED", "true").lower() == "true"
    RATE_LIMIT_STORAGE_URL: str = os.getenv(
        "RATE_LIMIT_STORAGE_URL",
        "redis://localhost:6379/1"  # Use DB 1 for rate limiting
    )

    # ================== API Keys ==================
    ANTHROPIC_API_KEY: str = os.getenv("ANTHROPIC_API_KEY", "")
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")

    # ================== Amazon Credentials ==================
    AMAZON_EMAIL: str = os.getenv("AMAZON_EMAIL", "")
    AMAZON_PASSWORD: str = os.getenv("AMAZON_PASSWORD", "")

    # ================== JWT Authentication ==================
    AUTH_ENABLED: bool = os.getenv("AUTH_ENABLED", "true").lower() == "true"
    SECRET_KEY: str = os.getenv("SECRET_KEY", "your-secret-key-change-this-in-production")
    JWT_SECRET_KEY: str = os.getenv("JWT_SECRET_KEY", "your-jwt-secret-key-change-this-in-production")
    JWT_ALGORITHM: str = os.getenv("JWT_ALGORITHM", "HS256")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30"))
    REFRESH_TOKEN_EXPIRE_DAYS: int = int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", "7"))

    # ================== CORS ==================
    @property
    def ALLOWED_ORIGINS(self) -> List[str]:
        """Parse ALLOWED_ORIGINS from env or use defaults"""
        origins_str = os.getenv("ALLOWED_ORIGINS", "http://localhost:8501,http://localhost:3000,http://localhost:8000")
        return [origin.strip() for origin in origins_str.split(",")]

    # ================== Token Management ==================
    MONTHLY_TOKEN_CAP: int = int(os.getenv("MONTHLY_TOKEN_CAP", "10000000"))

    # ================== Celery Beat ==================
    RELEARN_CRON: str = os.getenv("RELEARN_CRON", "0 3 * * *")  # 毎日午前3時

    # ================== Timezone ==================
    TIMEZONE: str = os.getenv("TIMEZONE", "Asia/Tokyo")

    # ================== Tesseract ==================
    TESSDATA_PREFIX: str = os.getenv(
        "TESSDATA_PREFIX",
        "/usr/share/tesseract-ocr/4.00/tessdata"
    )

    # ================== File Paths ==================
    UPLOAD_DIR: str = "./uploads"
    CAPTURE_DIR: str = "./captures"
    LOG_DIR: str = "./logs"

    class Config:
        env_file = ".env"
        case_sensitive = True
        extra = "ignore"  # 未定義の環境変数を無視


# グローバル設定インスタンス
settings = Settings()
