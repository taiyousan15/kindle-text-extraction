"""
RAG Schemas

RAGエンドポイント用のリクエスト/レスポンススキーマ
"""
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime


# ==================== RAG Query ====================

class RAGQueryRequest(BaseModel):
    """RAGクエリリクエスト"""

    query: str = Field(..., description="ユーザークエリ", min_length=1, max_length=2000)
    top_k: int = Field(default=5, description="取得するドキュメント数", ge=1, le=20)
    score_threshold: Optional[float] = Field(
        default=None,
        description="類似度閾値（0.0-1.0）",
        ge=0.0,
        le=1.0
    )
    file_ids: Optional[List[int]] = Field(
        default=None,
        description="検索対象ファイルIDリスト（Noneの場合は全体検索）"
    )
    provider: str = Field(
        default="anthropic",
        description="LLMプロバイダー（anthropic/openai）"
    )
    temperature: float = Field(
        default=0.7,
        description="生成の多様性（0.0-1.0）",
        ge=0.0,
        le=1.0
    )
    system_prompt: Optional[str] = Field(
        default=None,
        description="カスタムシステムプロンプト"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "query": "Pythonの特徴を教えてください",
                "top_k": 5,
                "score_threshold": 0.7,
                "file_ids": None,
                "provider": "anthropic",
                "temperature": 0.7
            }
        }


class RetrievedDocument(BaseModel):
    """取得されたドキュメント"""

    id: int = Field(..., description="ドキュメントID")
    content: str = Field(..., description="ドキュメント内容")
    score: Optional[float] = Field(None, description="ドキュメントスコア")
    similarity: float = Field(..., description="類似度（0.0-1.0）")
    file_id: int = Field(..., description="ファイルID")
    filename: str = Field(..., description="ファイル名")

    class Config:
        json_schema_extra = {
            "example": {
                "id": 123,
                "content": "Pythonは高水準プログラミング言語です。",
                "score": None,
                "similarity": 0.92,
                "file_id": 1,
                "filename": "python_intro.pdf"
            }
        }


class TokenUsage(BaseModel):
    """トークン使用量"""

    total: int = Field(..., description="総トークン数")
    prompt: int = Field(..., description="プロンプトトークン数")
    completion: int = Field(..., description="生成トークン数")


class RAGQueryResponse(BaseModel):
    """RAGクエリレスポンス"""

    answer: str = Field(..., description="生成された回答")
    sources: List[RetrievedDocument] = Field(..., description="参照したドキュメント")
    query: str = Field(..., description="元のクエリ")
    tokens: Optional[TokenUsage] = Field(None, description="トークン使用量")
    model: str = Field(..., description="使用したモデル名")
    is_mock: bool = Field(default=False, description="モックレスポンスかどうか")
    processing_time: float = Field(..., description="処理時間（秒）")

    class Config:
        json_schema_extra = {
            "example": {
                "answer": "Pythonは高水準プログラミング言語で、読みやすく書きやすい構文が特徴です。",
                "sources": [
                    {
                        "id": 123,
                        "content": "Pythonは高水準プログラミング言語です。",
                        "score": None,
                        "similarity": 0.92,
                        "file_id": 1,
                        "filename": "python_intro.pdf"
                    }
                ],
                "query": "Pythonの特徴を教えてください",
                "tokens": {"total": 150, "prompt": 100, "completion": 50},
                "model": "claude-3-sonnet-20240229",
                "is_mock": False,
                "processing_time": 2.5
            }
        }


# ==================== RAG Index ====================

class RAGIndexRequest(BaseModel):
    """ドキュメントインデックス化リクエスト"""

    file_id: Optional[int] = Field(
        default=None,
        description="既存ファイルID（アップロード済みの場合）"
    )
    content: Optional[str] = Field(
        default=None,
        description="テキストコンテンツ（直接指定する場合）"
    )
    filename: Optional[str] = Field(
        default=None,
        description="ファイル名（新規作成時）"
    )
    tags: Optional[List[str]] = Field(
        default=None,
        description="タグリスト"
    )
    chunk_size: int = Field(
        default=500,
        description="チャンクサイズ（文字数）",
        ge=100,
        le=2000
    )
    chunk_overlap: int = Field(
        default=50,
        description="チャンク重複サイズ（文字数）",
        ge=0,
        le=500
    )

    class Config:
        json_schema_extra = {
            "example": {
                "file_id": 1,
                "content": None,
                "filename": None,
                "tags": ["python", "tutorial"],
                "chunk_size": 500,
                "chunk_overlap": 50
            }
        }


class RAGIndexResponse(BaseModel):
    """ドキュメントインデックス化レスポンス"""

    file_id: int = Field(..., description="ファイルID")
    filename: str = Field(..., description="ファイル名")
    indexed_count: int = Field(..., description="インデックス化されたドキュメント数")
    total_characters: int = Field(..., description="総文字数")
    processing_time: float = Field(..., description="処理時間（秒）")
    status: str = Field(..., description="ステータス（success/partial/failed）")
    message: Optional[str] = Field(None, description="メッセージ")

    class Config:
        json_schema_extra = {
            "example": {
                "file_id": 1,
                "filename": "python_intro.pdf",
                "indexed_count": 10,
                "total_characters": 5000,
                "processing_time": 3.2,
                "status": "success",
                "message": "Successfully indexed 10 documents"
            }
        }


# ==================== RAG Search ====================

class RAGSearchRequest(BaseModel):
    """RAG検索リクエスト（LLM不使用）"""

    query: str = Field(..., description="検索クエリ", min_length=1, max_length=2000)
    top_k: int = Field(default=5, description="取得件数", ge=1, le=50)
    score_threshold: Optional[float] = Field(
        default=None,
        description="類似度閾値（0.0-1.0）",
        ge=0.0,
        le=1.0
    )
    file_ids: Optional[List[int]] = Field(
        default=None,
        description="検索対象ファイルIDリスト"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "query": "Pythonの特徴",
                "top_k": 5,
                "score_threshold": 0.7,
                "file_ids": [1, 2, 3]
            }
        }


class RAGSearchResponse(BaseModel):
    """RAG検索レスポンス"""

    query: str = Field(..., description="検索クエリ")
    results: List[RetrievedDocument] = Field(..., description="検索結果")
    total_count: int = Field(..., description="総検索結果数")
    processing_time: float = Field(..., description="処理時間（秒）")

    class Config:
        json_schema_extra = {
            "example": {
                "query": "Pythonの特徴",
                "results": [
                    {
                        "id": 123,
                        "content": "Pythonは高水準プログラミング言語です。",
                        "score": None,
                        "similarity": 0.92,
                        "file_id": 1,
                        "filename": "python_intro.pdf"
                    }
                ],
                "total_count": 1,
                "processing_time": 0.5
            }
        }


# ==================== Vector Store Statistics ====================

class VectorStoreStats(BaseModel):
    """ベクトルストア統計"""

    total_documents: int = Field(..., description="総ドキュメント数")
    total_files: int = Field(..., description="総ファイル数")
    documents_with_embeddings: int = Field(..., description="Embedding付きドキュメント数")
    avg_embedding_dim: int = Field(..., description="平均Embedding次元数")
    embedding_coverage: float = Field(..., description="Embeddingカバレッジ（0.0-1.0）")

    class Config:
        json_schema_extra = {
            "example": {
                "total_documents": 100,
                "total_files": 10,
                "documents_with_embeddings": 95,
                "avg_embedding_dim": 384,
                "embedding_coverage": 0.95
            }
        }


# ==================== Error Response ====================

class RAGErrorResponse(BaseModel):
    """RAGエラーレスポンス"""

    error: str = Field(..., description="エラーメッセージ")
    detail: Optional[str] = Field(None, description="詳細情報")
    status_code: int = Field(..., description="HTTPステータスコード")

    class Config:
        json_schema_extra = {
            "example": {
                "error": "Document not found",
                "detail": "File ID 999 does not exist",
                "status_code": 404
            }
        }
