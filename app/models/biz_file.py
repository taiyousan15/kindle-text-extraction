"""
Business File Model

ビジネスファイルを管理するモデル
"""
from sqlalchemy import String, LargeBinary, DateTime, func, Index
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.orm import Mapped, mapped_column, relationship
from typing import List, TYPE_CHECKING
from datetime import datetime

from app.models.base import Base, SerializeMixin

if TYPE_CHECKING:
    from app.models.biz_card import BizCard


class BizFile(Base, SerializeMixin):
    """ビジネスファイルモデル"""

    __tablename__ = "biz_files"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    tags: Mapped[list[str] | None] = mapped_column(ARRAY(String))
    file_blob: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    file_size: Mapped[int | None] = mapped_column()
    mime_type: Mapped[str | None] = mapped_column(String(100))
    uploaded_at: Mapped[datetime] = mapped_column(DateTime, default=func.now(), nullable=False)

    # Relationships
    biz_cards: Mapped[List["BizCard"]] = relationship(
        back_populates="file",
        cascade="all, delete-orphan"
    )

    # Indexes
    __table_args__ = (
        Index("idx_biz_file_filename", "filename"),
        Index("idx_biz_file_uploaded", "uploaded_at"),
    )

    def __repr__(self) -> str:
        return (
            f"<BizFile(id={self.id}, filename='{self.filename}', "
            f"file_size={self.file_size}, mime_type='{self.mime_type}')>"
        )
