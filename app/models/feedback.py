"""
Feedback Model

フィードバックを管理するモデル
"""
from sqlalchemy import Text, DateTime, ForeignKey, CheckConstraint, func, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship
from typing import TYPE_CHECKING
from datetime import datetime

from app.models.base import Base, SerializeMixin

if TYPE_CHECKING:
    from app.models.user import User


class Feedback(Base, SerializeMixin):
    """フィードバックモデル"""

    __tablename__ = "feedbacks"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    query: Mapped[str] = mapped_column(Text, nullable=False)
    answer: Mapped[str] = mapped_column(Text, nullable=False)
    rating: Mapped[int | None] = mapped_column(CheckConstraint("rating >= 1 AND rating <= 5"))
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now(), nullable=False)

    # Relationships
    user: Mapped["User"] = relationship(back_populates="feedbacks")

    # Indexes
    __table_args__ = (
        Index("idx_feedback_user", "user_id"),
        Index("idx_feedback_created", "created_at"),
        Index("idx_feedback_rating", "rating"),
    )

    def __repr__(self) -> str:
        return (
            f"<Feedback(id={self.id}, user_id={self.user_id}, "
            f"rating={self.rating})>"
        )
