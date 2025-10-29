"""
Knowledge Model

ナレッジベースを管理するモデル
"""
from sqlalchemy import String, Float, Text, LargeBinary, DateTime, func, Index
from sqlalchemy.orm import Mapped, mapped_column
from datetime import datetime
from app.models.base import Base, SerializeMixin


class Knowledge(Base, SerializeMixin):
    """ナレッジモデル"""

    __tablename__ = "knowledge"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    book_title: Mapped[str] = mapped_column(String(255), nullable=False)
    format: Mapped[str] = mapped_column(String(10), nullable=False)
    score: Mapped[float | None] = mapped_column(Float)
    yaml_text: Mapped[str] = mapped_column(Text, nullable=False)
    content_blob: Mapped[bytes | None] = mapped_column(LargeBinary)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now(), nullable=False)

    # Indexes
    __table_args__ = (
        Index("idx_knowledge_book_title", "book_title"),
        Index("idx_knowledge_format", "format"),
        Index("idx_knowledge_score", "score"),
    )

    def __repr__(self) -> str:
        return (
            f"<Knowledge(id={self.id}, book_title='{self.book_title}', "
            f"format='{self.format}', score={self.score})>"
        )
