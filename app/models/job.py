"""
Job Model

OCR処理ジョブを管理するモデル
"""
import uuid
from sqlalchemy import String, DateTime, Text, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from typing import List, TYPE_CHECKING
from datetime import datetime

from app.models.base import Base, SerializeMixin

if TYPE_CHECKING:
    from app.models.user import User
    from app.models.ocr_result import OCRResult
    from app.models.summary import Summary


class Job(Base, SerializeMixin):
    """ジョブモデル"""

    __tablename__ = "jobs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True, index=True)
    type: Mapped[str] = mapped_column(String(50), nullable=False)
    status: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    progress: Mapped[int] = mapped_column(default=0)
    error_message: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now(), nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime)

    # Relationships
    user: Mapped["User"] = relationship(back_populates="jobs")
    ocr_results: Mapped[List["OCRResult"]] = relationship(
        back_populates="job",
        cascade="all, delete-orphan"
    )
    summaries: Mapped[List["Summary"]] = relationship(
        back_populates="job",
        cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return (
            f"<Job(id='{self.id}', type='{self.type}', "
            f"status='{self.status}', progress={self.progress})>"
        )
