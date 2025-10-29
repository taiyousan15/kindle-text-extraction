"""
FastAPI Application Entry Point
Kindle OCR MVP - Phase 1-8

メインアプリケーションの初期化とルーター登録
Rate Limiting Middleware 統合
"""
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import logging
import time

from app.core.database import health_check, check_connection
from app.core.config import settings

# Rate Limiting
from slowapi.errors import RateLimitExceeded
from app.services.rate_limiter import limiter, get_ip_manager, RateLimitConfig
from app.middleware.rate_limit import (
    rate_limit_error_handler,
    RateLimitMiddleware,
    IPBlacklistMiddleware
)

# ロガー設定
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    アプリケーションライフサイクル管理

    起動時: データベース接続確認、Rate Limiter初期化
    終了時: クリーンアップ
    """
    logger.info("🚀 Starting Kindle OCR Application...")

    # データベース接続確認
    if check_connection():
        logger.info("✅ Database connection established")
    else:
        logger.error("❌ Database connection failed!")

    # Rate Limiter初期化
    if settings.RATE_LIMIT_ENABLED:
        try:
            # Initialize IP manager
            ip_manager = get_ip_manager()
            app.state.ip_manager = ip_manager
            logger.info("✅ Rate limiter initialized with Redis backend")
            logger.info(f"   Storage URL: {settings.RATE_LIMIT_STORAGE_URL}")
        except Exception as e:
            logger.warning(f"⚠️ Rate limiter initialization failed: {e}")
            logger.warning("   Continuing with in-memory rate limiting")
    else:
        logger.info("⚠️ Rate limiting is DISABLED")

    yield

    logger.info("🛑 Shutting down Kindle OCR Application...")


# FastAPI アプリケーション初期化
app = FastAPI(
    title="Kindle OCR API",
    description="Kindle screenshots to structured knowledge - MVP with Rate Limiting",
    version="1.0.0 (Phase 1-8 MVP)",
    lifespan=lifespan
)

# ========================================
# ミドルウェア設定（順序重要）
# ========================================

# 1. IP Blacklist Middleware (最優先 - 不正IPをすぐにブロック)
if settings.RATE_LIMIT_ENABLED:
    app.add_middleware(IPBlacklistMiddleware)
    logger.info("✅ IP Blacklist Middleware enabled")

# 2. CORS ミドルウェア設定
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 3. Rate Limit Middleware
if settings.RATE_LIMIT_ENABLED:
    app.add_middleware(RateLimitMiddleware)
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, rate_limit_error_handler)
    logger.info("✅ Rate Limit Middleware enabled")


# ========================================
# ヘルスチェックエンドポイント
# ========================================

@app.get("/")
@limiter.limit(RateLimitConfig.STANDARD_API)
async def root(request: Request):
    """
    ルートエンドポイント - API情報
    """
    return {
        "message": "Kindle OCR API",
        "version": "1.0.0 (Phase 1-8 MVP)",
        "docs": "/docs",
        "health": "/health",
        "rate_limiting": "enabled" if settings.RATE_LIMIT_ENABLED else "disabled"
    }


@app.get("/health")
@limiter.limit(RateLimitConfig.STANDARD_API)
async def health(request: Request):
    """
    ヘルスチェックエンドポイント

    データベース接続とプール状態を確認

    Returns:
        dict: {
            "status": "healthy" | "unhealthy",
            "database": "postgresql",
            "pool_size": int,
            "checked_out": int
        }
    """
    return await health_check()


# Test endpoint for rate limiting
@app.get("/test/rate-limit")
@limiter.limit("5/minute")
async def test_rate_limit(request: Request):
    """
    Test endpoint for rate limiting (5 requests per minute)
    """
    import time as time_module
    return {
        "message": "Rate limit test endpoint",
        "limit": "5 requests per minute",
        "timestamp": time_module.time()
    }


# ========================================
# ルーター登録（Phase 1-8以降で追加）
# ========================================

# Phase 8: 認証エンドポイント
from app.api.v1.endpoints.auth import router as auth_router
app.include_router(auth_router, prefix="/api/v1/auth", tags=["Authentication"])

# Phase 1-3: OCRエンドポイント
from app.api.v1.endpoints.ocr import router as ocr_router
app.include_router(ocr_router, prefix="/api/v1/ocr", tags=["OCR"])

# Phase 1-4: 自動キャプチャエンドポイント
from app.api.v1.endpoints.capture import router as capture_router
app.include_router(capture_router, prefix="/api/v1/capture", tags=["Auto Capture"])

# Phase 2: RAGエンドポイント
from app.api.v1.endpoints.rag import router as rag_router
app.include_router(rag_router, prefix="/api/v1", tags=["RAG"])

# Phase 3: 要約エンドポイント
from app.api.v1.endpoints.summary import router as summary_router
app.include_router(summary_router, prefix="/api/v1/summary", tags=["Summary"])

# Phase 4: ナレッジ抽出エンドポイント
from app.api.v1.endpoints.knowledge import router as knowledge_router
app.include_router(knowledge_router, prefix="/api/v1/knowledge", tags=["Knowledge Extraction"])

# Phase 5: ビジネスRAGエンドポイント
from app.api.v1.endpoints.business import router as business_router
app.include_router(business_router, prefix="/api/v1/business", tags=["Business RAG"])

# Phase 6: フィードバックエンドポイント
from app.api.v1.endpoints.feedback import router as feedback_router
app.include_router(feedback_router, prefix="/api/v1/feedback", tags=["Feedback & Learning"])


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )
