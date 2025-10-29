"""
OCR Result Model

OCR結果を管理するモデル
"""
from sqlalchemy import String, Text, Float, LargeBinary, DateTime, ForeignKey, UniqueConstraint, func, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship
from typing import TYPE_CHECKING
from datetime import datetime

from app.models.base import Base, SerializeMixin

if TYPE_CHECKING:
    from app.models.job import Job


class OCRResult(Base, SerializeMixin):
    """OCR結果モデル"""

    __tablename__ = "ocr_results"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    job_id: Mapped[str] = mapped_column(String(36), ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False, index=True)
    book_title: Mapped[str] = mapped_column(String(255), nullable=False)
    page_num: Mapped[int] = mapped_column(nullable=False)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    confidence: Mapped[float | None] = mapped_column(Float)
    image_blob: Mapped[bytes | None] = mapped_column(LargeBinary)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now(), nullable=False)

    # Relationships
    job: Mapped["Job"] = relationship(back_populates="ocr_results")

    # Constraints
    __table_args__ = (
        UniqueConstraint("job_id", "page_num", name="uq_job_page"),
        Index("idx_ocr_book_title", "book_title"),
        Index("idx_ocr_job_page", "job_id", "page_num"),
    )

    def __repr__(self) -> str:
        return (
            f"<OCRResult(id={self.id}, job_id='{self.job_id}', "
            f"book_title='{self.book_title}', page_num={self.page_num})>"
        )
