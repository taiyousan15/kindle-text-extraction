"""
Business Card Model

ビジネスカード（RAG）を管理するモデル
"""
from sqlalchemy import Text, Float, DateTime, ForeignKey, func, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship
from pgvector.sqlalchemy import Vector
from typing import List, TYPE_CHECKING, Any
from datetime import datetime

from app.models.base import Base, SerializeMixin

if TYPE_CHECKING:
    from app.models.biz_file import BizFile
    from app.models.retrain_queue import RetrainQueue


class BizCard(Base, SerializeMixin):
    """ビジネスカード（RAG）モデル"""

    __tablename__ = "biz_cards"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    file_id: Mapped[int] = mapped_column(ForeignKey("biz_files.id", ondelete="CASCADE"), nullable=False, index=True)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    vector_embedding: Mapped[Any | None] = mapped_column(Vector(384))
    score: Mapped[float | None] = mapped_column(Float)
    indexed_at: Mapped[datetime] = mapped_column(DateTime, default=func.now(), nullable=False)

    # Relationships
    file: Mapped["BizFile"] = relationship(back_populates="biz_cards")
    retrain_queues: Mapped[List["RetrainQueue"]] = relationship(
        back_populates="card",
        cascade="all, delete-orphan"
    )

    # Indexes
    __table_args__ = (
        Index("idx_biz_card_file", "file_id"),
        Index("idx_biz_card_score", "score"),
        Index("idx_biz_card_indexed", "indexed_at"),
    )

    def __repr__(self) -> str:
        return (
            f"<BizCard(id={self.id}, file_id={self.file_id}, "
            f"score={self.score})>"
        )
