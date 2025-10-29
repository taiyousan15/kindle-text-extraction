"""
PostgreSQL データベース接続設定

接続プール、セッション管理、エラーハンドリングを統合
"""
from sqlalchemy import create_engine, event, pool, text
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import QueuePool
from typing import Generator
import logging
import os

# Import Base from models to ensure consistency
from app.models.base import Base

logger = logging.getLogger(__name__)

# 環境変数から接続情報を取得
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://kindle_user:kindle_password@localhost:5432/kindle_ocr"
)

# SQLAlchemy Engine設定（接続プール最適化）
engine = create_engine(
    DATABASE_URL,
    # 接続プール設定
    poolclass=QueuePool,
    pool_size=10,                    # 常時接続数
    max_overflow=20,                 # 追加接続数（最大30接続）
    pool_timeout=30,                 # 接続待機タイムアウト（秒）
    pool_recycle=3600,               # 接続再利用時間（1時間）
    pool_pre_ping=True,              # 接続前にPing（切断検出）

    # その他のオプション
    echo=False,                      # SQLログ出力（本番はFalse）
    future=True,                     # SQLAlchemy 2.0スタイル
    connect_args={
        "connect_timeout": 10,       # 接続タイムアウト（秒）
        "options": "-c timezone=Asia/Tokyo"  # タイムゾーン設定
    }
)

# セッションファクトリー
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
    expire_on_commit=False  # コミット後もオブジェクト使用可能
)


# Dependency for FastAPI
def get_db() -> Generator[Session, None, None]:
    """
    FastAPI依存性注入用のDB セッション取得

    使用例:
        @app.get("/books")
        def get_books(db: Session = Depends(get_db)):
            return db.query(Book).all()
    """
    db = SessionLocal()
    try:
        yield db
    except Exception as e:
        logger.error(f"❌ Database error: {e}", exc_info=True)
        db.rollback()
        raise
    finally:
        db.close()


# Event listeners for connection pool monitoring
@event.listens_for(engine, "connect")
def receive_connect(dbapi_conn, connection_record):
    """接続確立時のログ"""
    logger.debug("🔌 Database connection established")


@event.listens_for(engine, "checkout")
def receive_checkout(dbapi_conn, connection_record, connection_proxy):
    """接続プールからチェックアウト時のログ"""
    logger.debug("📤 Connection checked out from pool")


@event.listens_for(engine, "checkin")
def receive_checkin(dbapi_conn, connection_record):
    """接続プールへチェックイン時のログ"""
    logger.debug("📥 Connection returned to pool")


# Initialization functions
def create_tables():
    """全テーブルを作成（開発用）"""
    logger.info("📊 Creating database tables...")
    Base.metadata.create_all(bind=engine)
    logger.info("✅ Database tables created successfully")


def drop_tables():
    """全テーブルを削除（開発用・危険）"""
    logger.warning("⚠️ Dropping all database tables...")
    Base.metadata.drop_all(bind=engine)
    logger.info("🗑️ All tables dropped")


def check_connection() -> bool:
    """
    データベース接続チェック

    Returns:
        接続成功でTrue
    """
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        logger.info("✅ Database connection successful")
        return True
    except Exception as e:
        logger.error(f"❌ Database connection failed: {e}", exc_info=True)
        return False


# Context manager for standalone usage
class DatabaseSession:
    """
    スタンドアロン用のDBセッション（with文で使用）

    使用例:
        with DatabaseSession() as db:
            books = db.query(Book).all()
    """
    def __enter__(self) -> Session:
        self.db = SessionLocal()
        return self.db

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is not None:
            logger.error(f"❌ Transaction error: {exc_val}", exc_info=True)
            self.db.rollback()
        self.db.close()


# Health check function
async def health_check() -> dict:
    """
    ヘルスチェック用の非同期関数

    Returns:
        {"status": "healthy", "pool_size": 10, ...}
    """
    try:
        # 接続テスト
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))

        # プール状態取得
        pool_status = engine.pool.status()

        return {
            "status": "healthy",
            "database": "postgresql",
            "pool_status": pool_status,
            "pool_size": engine.pool.size(),
            "checked_out": engine.pool.checkedout()
        }
    except Exception as e:
        logger.error(f"❌ Health check failed: {e}", exc_info=True)
        return {
            "status": "unhealthy",
            "error": str(e)
        }


# Example usage
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    # 接続テスト
    if check_connection():
        print("✅ Database connection successful!")

        # プール状態確認
        print(f"📊 Pool size: {engine.pool.size()}")
        print(f"📊 Pool status: {engine.pool.status()}")
    else:
        print("❌ Database connection failed!")
