"""
Summary Schemas

Pydantic schemas for Summary endpoint request/response validation
"""
from pydantic import BaseModel, Field, field_validator
from datetime import datetime
from typing import Optional, Dict, Any, List
from enum import Enum


class SummaryLength(str, Enum):
    """要約の長さ"""
    SHORT = "short"  # 100-200 chars
    MEDIUM = "medium"  # 200-500 chars
    LONG = "long"  # 500-1000 chars


class SummaryTone(str, Enum):
    """要約のトーン"""
    PROFESSIONAL = "professional"
    CASUAL = "casual"
    ACADEMIC = "academic"
    EXECUTIVE = "executive"


class SummaryGranularity(str, Enum):
    """要約の粒度"""
    HIGH_LEVEL = "high_level"
    DETAILED = "detailed"
    COMPREHENSIVE = "comprehensive"


class SummaryFormat(str, Enum):
    """要約のフォーマット"""
    PLAIN_TEXT = "plain_text"
    BULLET_POINTS = "bullet_points"
    STRUCTURED = "structured"


class SummaryCreateRequest(BaseModel):
    """
    要約作成リクエスト

    Attributes:
        text: 要約対象テキスト（textまたはjob_idのいずれか必須）
        job_id: OCRジョブID（textまたはjob_idのいずれか必須）
        book_title: 書籍タイトル（job_id使用時は不要、自動取得）
        length: 要約の長さ
        tone: トーン
        granularity: 粒度
        format: フォーマット
        language: 言語（Noneの場合は自動検出）
    """
    text: Optional[str] = Field(None, description="要約対象テキスト")
    job_id: Optional[str] = Field(None, description="OCRジョブID")
    book_title: Optional[str] = Field(None, description="書籍タイトル")
    length: SummaryLength = Field(
        SummaryLength.MEDIUM,
        description="要約の長さ"
    )
    tone: SummaryTone = Field(
        SummaryTone.PROFESSIONAL,
        description="トーン"
    )
    granularity: SummaryGranularity = Field(
        SummaryGranularity.HIGH_LEVEL,
        description="粒度"
    )
    format: SummaryFormat = Field(
        SummaryFormat.PLAIN_TEXT,
        description="フォーマット"
    )
    language: Optional[str] = Field(
        None,
        description="言語（'ja' or 'en'、Noneの場合は自動検出）"
    )

    @field_validator('language')
    @classmethod
    def validate_language(cls, v):
        if v is not None and v not in ['ja', 'en']:
            raise ValueError("Language must be 'ja' or 'en'")
        return v

    class Config:
        json_schema_extra = {
            "example": {
                "text": "人工知能は近年急速に発展しており...",
                "book_title": "AI入門",
                "length": "medium",
                "tone": "professional",
                "granularity": "high_level",
                "format": "plain_text",
                "language": "ja"
            }
        }


class SummaryMultiLevelRequest(BaseModel):
    """
    マルチレベル要約作成リクエスト

    Attributes:
        text: 要約対象テキスト（textまたはjob_idのいずれか必須）
        job_id: OCRジョブID（textまたはjob_idのいずれか必須）
        book_title: 書籍タイトル（job_id使用時は不要、自動取得）
        tone: トーン
        format: フォーマット
        language: 言語（Noneの場合は自動検出）
    """
    text: Optional[str] = Field(None, description="要約対象テキスト")
    job_id: Optional[str] = Field(None, description="OCRジョブID")
    book_title: Optional[str] = Field(None, description="書籍タイトル")
    tone: SummaryTone = Field(
        SummaryTone.PROFESSIONAL,
        description="トーン"
    )
    format: SummaryFormat = Field(
        SummaryFormat.PLAIN_TEXT,
        description="フォーマット"
    )
    language: Optional[str] = Field(
        None,
        description="言語（'ja' or 'en'、Noneの場合は自動検出）"
    )

    @field_validator('language')
    @classmethod
    def validate_language(cls, v):
        if v is not None and v not in ['ja', 'en']:
            raise ValueError("Language must be 'ja' or 'en'")
        return v

    class Config:
        json_schema_extra = {
            "example": {
                "job_id": "550e8400-e29b-41d4-a716-446655440000",
                "tone": "professional",
                "format": "plain_text"
            }
        }


class TokenUsage(BaseModel):
    """トークン使用量"""
    total: int = Field(..., description="総トークン数")
    prompt: int = Field(..., description="プロンプトトークン数")
    completion: int = Field(..., description="生成トークン数")


class SummaryLevelDetail(BaseModel):
    """要約レベルの詳細"""
    summary: str = Field(..., description="要約テキスト")
    level: int = Field(..., description="レベル番号（1-3）")
    tokens: TokenUsage = Field(..., description="トークン使用量")


class SummaryCreateResponse(BaseModel):
    """
    要約作成レスポンス

    Attributes:
        summary_id: 要約ID
        job_id: 関連するジョブID
        book_title: 書籍タイトル
        summary_text: 要約テキスト
        language: 検出された言語
        granularity: 粒度
        length: 長さ
        tone: トーン
        format: フォーマット
        token_usage: トークン使用量
        chunks: 処理したチャンク数
        is_mock: モックレスポンスかどうか
        created_at: 作成日時
    """
    summary_id: int = Field(..., description="要約ID")
    job_id: str = Field(..., description="関連するジョブID")
    book_title: str = Field(..., description="書籍タイトル")
    summary_text: str = Field(..., description="要約テキスト")
    language: str = Field(..., description="検出された言語")
    granularity: str = Field(..., description="粒度")
    length: str = Field(..., description="長さ")
    tone: str = Field(..., description="トーン")
    format: str = Field(..., description="フォーマット")
    token_usage: TokenUsage = Field(..., description="トークン使用量")
    chunks: int = Field(..., description="処理したチャンク数")
    is_mock: bool = Field(..., description="モックレスポンスかどうか")
    created_at: datetime = Field(..., description="作成日時")

    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "summary_id": 1,
                "job_id": "550e8400-e29b-41d4-a716-446655440000",
                "book_title": "AI入門",
                "summary_text": "人工知能は急速に発展し、様々な産業で活用されている。",
                "language": "ja",
                "granularity": "high_level",
                "length": "medium",
                "tone": "professional",
                "format": "plain_text",
                "token_usage": {
                    "total": 250,
                    "prompt": 180,
                    "completion": 70
                },
                "chunks": 1,
                "is_mock": False,
                "created_at": "2025-10-28T10:30:00"
            }
        }


class SummaryMultiLevelResponse(BaseModel):
    """
    マルチレベル要約レスポンス

    Attributes:
        job_id: 関連するジョブID
        book_title: 書籍タイトル
        language: 検出された言語
        level_1: エグゼクティブサマリー（50-100文字）
        level_2: 標準要約（200-300文字）
        level_3: 詳細要約（500-1000文字）
        total_tokens: 合計トークン使用量
        summary_ids: 保存された要約のIDリスト
        is_mock: モックレスポンスかどうか
        created_at: 作成日時
    """
    job_id: str = Field(..., description="関連するジョブID")
    book_title: str = Field(..., description="書籍タイトル")
    language: str = Field(..., description="検出された言語")
    level_1: SummaryLevelDetail = Field(..., description="エグゼクティブサマリー")
    level_2: SummaryLevelDetail = Field(..., description="標準要約")
    level_3: SummaryLevelDetail = Field(..., description="詳細要約")
    total_tokens: TokenUsage = Field(..., description="合計トークン使用量")
    summary_ids: List[int] = Field(..., description="保存された要約のIDリスト")
    is_mock: bool = Field(..., description="モックレスポンスかどうか")
    created_at: datetime = Field(..., description="作成日時")

    class Config:
        json_schema_extra = {
            "example": {
                "job_id": "550e8400-e29b-41d4-a716-446655440000",
                "book_title": "AI入門",
                "language": "ja",
                "level_1": {
                    "summary": "AIは急速に発展し、様々な産業で活用されている。",
                    "level": 1,
                    "tokens": {"total": 100, "prompt": 80, "completion": 20}
                },
                "level_2": {
                    "summary": "人工知能（AI）は近年急速に発展し...",
                    "level": 2,
                    "tokens": {"total": 200, "prompt": 150, "completion": 50}
                },
                "level_3": {
                    "summary": "人工知能（AI）は近年急速に発展しており...",
                    "level": 3,
                    "tokens": {"total": 400, "prompt": 300, "completion": 100}
                },
                "total_tokens": {
                    "total": 700,
                    "prompt": 530,
                    "completion": 170
                },
                "summary_ids": [1, 2, 3],
                "is_mock": False,
                "created_at": "2025-10-28T10:30:00"
            }
        }


class SummaryDetail(BaseModel):
    """
    要約詳細情報

    Attributes:
        id: 要約ID
        job_id: 関連するジョブID
        book_title: 書籍タイトル
        summary_text: 要約テキスト
        granularity: 粒度
        length: 長さ
        tone: トーン
        format: フォーマット
        language: 言語
        created_at: 作成日時
    """
    id: int = Field(..., description="要約ID")
    job_id: str = Field(..., description="関連するジョブID")
    book_title: str = Field(..., description="書籍タイトル")
    summary_text: str = Field(..., description="要約テキスト")
    granularity: Optional[str] = Field(None, description="粒度")
    length: Optional[str] = Field(None, description="長さ")
    tone: Optional[str] = Field(None, description="トーン")
    format: Optional[str] = Field(None, description="フォーマット")
    language: Optional[str] = Field(None, description="言語")
    created_at: datetime = Field(..., description="作成日時")

    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "id": 1,
                "job_id": "550e8400-e29b-41d4-a716-446655440000",
                "book_title": "AI入門",
                "summary_text": "人工知能は急速に発展し、様々な産業で活用されている。",
                "granularity": "high_level",
                "length": "medium",
                "tone": "professional",
                "format": "plain_text",
                "language": "ja",
                "created_at": "2025-10-28T10:30:00"
            }
        }


class SummaryListResponse(BaseModel):
    """
    要約リストレスポンス

    Attributes:
        summaries: 要約のリスト
        total: 総件数
    """
    summaries: List[SummaryDetail] = Field(..., description="要約のリスト")
    total: int = Field(..., description="総件数")

    class Config:
        json_schema_extra = {
            "example": {
                "summaries": [
                    {
                        "id": 1,
                        "job_id": "550e8400-e29b-41d4-a716-446655440000",
                        "book_title": "AI入門",
                        "summary_text": "人工知能は急速に発展...",
                        "granularity": "high_level",
                        "length": "medium",
                        "tone": "professional",
                        "created_at": "2025-10-28T10:30:00"
                    }
                ],
                "total": 1
            }
        }


class SummaryRegenerateRequest(BaseModel):
    """
    要約再生成リクエスト

    Attributes:
        length: 要約の長さ
        tone: トーン
        granularity: 粒度
        format: フォーマット
        language: 言語
    """
    length: Optional[SummaryLength] = Field(None, description="要約の長さ")
    tone: Optional[SummaryTone] = Field(None, description="トーン")
    granularity: Optional[SummaryGranularity] = Field(None, description="粒度")
    format: Optional[SummaryFormat] = Field(None, description="フォーマット")
    language: Optional[str] = Field(None, description="言語（'ja' or 'en'）")

    @field_validator('language')
    @classmethod
    def validate_language(cls, v):
        if v is not None and v not in ['ja', 'en']:
            raise ValueError("Language must be 'ja' or 'en'")
        return v

    class Config:
        json_schema_extra = {
            "example": {
                "length": "long",
                "tone": "academic",
                "granularity": "comprehensive",
                "format": "bullet_points"
            }
        }


class ErrorResponse(BaseModel):
    """エラーレスポンス"""
    error: str = Field(..., description="エラーメッセージ")
    detail: Optional[str] = Field(None, description="詳細情報")

    class Config:
        json_schema_extra = {
            "example": {
                "error": "Invalid request",
                "detail": "Either text or job_id must be provided"
            }
        }
