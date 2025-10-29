"""
Capture Schemas

Pydantic schemas for auto-capture endpoint request/response validation
Phase 1-4 Implementation
"""
from pydantic import BaseModel, Field, EmailStr
from typing import Optional, List
from datetime import datetime


class CaptureStartRequest(BaseModel):
    """
    自動キャプチャ開始リクエスト

    Attributes:
        amazon_email: AmazonアカウントのEメールアドレス
        amazon_password: Amazonアカウントのパスワード
        book_url: Kindle Cloud ReaderのブックURL
        book_title: 書籍タイトル (オプション、デフォルト: "Untitled")
        max_pages: 最大キャプチャページ数 (オプション、デフォルト: 100)
        headless: ヘッドレスモード (オプション、デフォルト: True)
    """
    amazon_email: EmailStr = Field(..., description="AmazonアカウントのEメールアドレス")
    amazon_password: str = Field(..., description="Amazonアカウントのパスワード", min_length=6)
    book_url: str = Field(..., description="Kindle Cloud ReaderのブックURL")
    book_title: str = Field(default="Untitled", description="書籍タイトル")
    max_pages: int = Field(default=100, ge=1, le=500, description="最大キャプチャページ数")
    headless: bool = Field(default=True, description="ヘッドレスモード")

    class Config:
        json_schema_extra = {
            "example": {
                "amazon_email": "user@example.com",
                "amazon_password": "your-password",
                "book_url": "https://read.amazon.com/kindle-library",
                "book_title": "プロンプトエンジニアリング入門",
                "max_pages": 50,
                "headless": True
            }
        }


class CaptureStartResponse(BaseModel):
    """
    自動キャプチャ開始レスポンス

    Attributes:
        job_id: ジョブID (UUID)
        status: ジョブステータス (pending, processing, completed, failed)
        message: レスポンスメッセージ
    """
    job_id: str = Field(..., description="ジョブID (UUID)")
    status: str = Field(..., description="ジョブステータス")
    message: str = Field(..., description="レスポンスメッセージ")

    class Config:
        json_schema_extra = {
            "example": {
                "job_id": "550e8400-e29b-41d4-a716-446655440000",
                "status": "pending",
                "message": "自動キャプチャジョブを開始しました。/api/v1/capture/status/{job_id} でステータスを確認してください。"
            }
        }


class OCRResultSummary(BaseModel):
    """
    OCR結果サマリー

    Attributes:
        page_num: ページ番号
        text: 抽出されたテキスト
        confidence: OCR信頼度スコア (0.0-1.0)
    """
    page_num: int = Field(..., description="ページ番号")
    text: str = Field(..., description="抽出されたテキスト")
    confidence: Optional[float] = Field(None, description="OCR信頼度スコア (0.0-1.0)")

    class Config:
        from_attributes = True


class CaptureStatusResponse(BaseModel):
    """
    キャプチャステータスレスポンス

    Attributes:
        job_id: ジョブID (UUID)
        status: ジョブステータス (pending, processing, completed, failed)
        progress: 進捗率 (0-100)
        pages_captured: キャプチャ済みページ数
        total_pages: 総ページ数
        error_message: エラーメッセージ (エラー時のみ)
        ocr_results: OCR結果のリスト
        created_at: ジョブ作成日時
        completed_at: ジョブ完了日時
    """
    job_id: str = Field(..., description="ジョブID (UUID)")
    status: str = Field(..., description="ジョブステータス")
    progress: int = Field(..., description="進捗率 (0-100)")
    pages_captured: int = Field(..., description="キャプチャ済みページ数")
    total_pages: Optional[int] = Field(None, description="総ページ数")
    error_message: Optional[str] = Field(None, description="エラーメッセージ")
    ocr_results: List[OCRResultSummary] = Field(default=[], description="OCR結果のリスト")
    created_at: datetime = Field(..., description="ジョブ作成日時")
    completed_at: Optional[datetime] = Field(None, description="ジョブ完了日時")

    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "job_id": "550e8400-e29b-41d4-a716-446655440000",
                "status": "processing",
                "progress": 50,
                "pages_captured": 25,
                "total_pages": 50,
                "error_message": None,
                "ocr_results": [
                    {
                        "page_num": 1,
                        "text": "第1章 はじめに...",
                        "confidence": 0.95
                    }
                ],
                "created_at": "2025-10-28T10:30:00",
                "completed_at": None
            }
        }
