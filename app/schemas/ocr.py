"""
OCR Schemas

Pydantic schemas for OCR endpoint request/response validation
"""
from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional


class OCRUploadResponse(BaseModel):
    """
    OCR画像アップロード時のレスポンススキーマ

    Attributes:
        job_id: ジョブID (UUID)
        book_title: 書籍タイトル
        page_num: ページ番号
        text: 抽出されたテキスト
        confidence: OCR信頼度スコア (0.0-1.0)
    """
    job_id: str = Field(..., description="ジョブID (UUID)")
    book_title: str = Field(..., description="書籍タイトル")
    page_num: int = Field(..., description="ページ番号")
    text: str = Field(..., description="抽出されたテキスト")
    confidence: Optional[float] = Field(None, description="OCR信頼度スコア (0.0-1.0)")

    class Config:
        json_schema_extra = {
            "example": {
                "job_id": "550e8400-e29b-41d4-a716-446655440000",
                "book_title": "サンプル書籍",
                "page_num": 1,
                "text": "抽出されたテキストの内容...",
                "confidence": 0.95
            }
        }


class JobResponse(BaseModel):
    """
    ジョブ情報のレスポンススキーマ

    Attributes:
        id: ジョブID (UUID)
        user_id: ユーザーID
        type: ジョブタイプ (ocr, summary, etc.)
        status: ジョブステータス (pending, processing, completed, failed)
        progress: 進捗率 (0-100)
        created_at: 作成日時
    """
    id: str = Field(..., description="ジョブID (UUID)")
    user_id: Optional[int] = Field(None, description="ユーザーID")
    type: str = Field(..., description="ジョブタイプ")
    status: str = Field(..., description="ジョブステータス")
    progress: int = Field(..., description="進捗率 (0-100)")
    created_at: datetime = Field(..., description="作成日時")

    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "id": "550e8400-e29b-41d4-a716-446655440000",
                "user_id": 1,
                "type": "ocr",
                "status": "completed",
                "progress": 100,
                "created_at": "2025-10-28T10:30:00"
            }
        }
