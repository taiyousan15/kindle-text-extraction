"""
Summary Model

要約結果を管理するモデル
"""
from sqlalchemy import String, Text, DateTime, ForeignKey, func, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship
from typing import TYPE_CHECKING
from datetime import datetime

from app.models.base import Base, SerializeMixin

if TYPE_CHECKING:
    from app.models.job import Job


class Summary(Base, SerializeMixin):
    """要約モデル"""

    __tablename__ = "summaries"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    job_id: Mapped[str] = mapped_column(String(36), ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False, index=True)
    book_title: Mapped[str] = mapped_column(String(255), nullable=False)
    summary_text: Mapped[str] = mapped_column(Text, nullable=False)
    granularity: Mapped[str | None] = mapped_column(String(50))
    length: Mapped[str | None] = mapped_column(String(50))
    tone: Mapped[str | None] = mapped_column(String(50))
    format: Mapped[str | None] = mapped_column(String(50))
    language: Mapped[str | None] = mapped_column(String(10))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now(), nullable=False)

    # Relationships
    job: Mapped["Job"] = relationship(back_populates="summaries")

    # Indexes
    __table_args__ = (
        Index("idx_summary_book_title", "book_title"),
        Index("idx_summary_job", "job_id"),
    )

    def __repr__(self) -> str:
        return (
            f"<Summary(id={self.id}, job_id='{self.job_id}', "
            f"book_title='{self.book_title}', granularity='{self.granularity}')>"
        )
