"""
Retrain Queue Model

再学習キューを管理するモデル
"""
from sqlalchemy import Float, DateTime, ForeignKey, func, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship
from typing import TYPE_CHECKING
from datetime import datetime

from app.models.base import Base, SerializeMixin

if TYPE_CHECKING:
    from app.models.biz_card import BizCard


class RetrainQueue(Base, SerializeMixin):
    """再学習キューモデル"""

    __tablename__ = "retrain_queue"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    card_id: Mapped[int] = mapped_column(ForeignKey("biz_cards.id", ondelete="CASCADE"), nullable=False, index=True)
    score: Mapped[float | None] = mapped_column(Float)
    queued_at: Mapped[datetime] = mapped_column(DateTime, default=func.now(), nullable=False)
    processed_at: Mapped[datetime | None] = mapped_column(DateTime)

    # Relationships
    card: Mapped["BizCard"] = relationship(back_populates="retrain_queues")

    # Indexes
    __table_args__ = (
        Index("idx_retrain_card", "card_id"),
        Index("idx_retrain_queued", "queued_at"),
        Index("idx_retrain_processed", "processed_at"),
        Index("idx_retrain_pending", "processed_at", postgresql_where=mapped_column("processed_at").is_(None)),
    )

    def __repr__(self) -> str:
        return (
            f"<RetrainQueue(id={self.id}, card_id={self.card_id}, "
            f"score={self.score}, processed={self.processed_at is not None})>"
        )
