"""
Knowledge Schemas

Pydantic schemas for Knowledge Extraction endpoint request/response validation
"""
from pydantic import BaseModel, Field, field_validator
from datetime import datetime
from typing import Optional, List, Dict, Any
from enum import Enum


class OutputFormat(str, Enum):
    """出力フォーマット"""
    YAML = "yaml"
    JSON = "json"
    MARKDOWN = "markdown"
    CSV = "csv"  # For relations export


class EntityType(str, Enum):
    """エンティティタイプ"""
    PERSON = "person"  # 人物名
    ORGANIZATION = "organization"  # 組織名
    LOCATION = "location"  # 地名
    DATE = "date"  # 日付
    TIME = "time"  # 時刻
    TECHNICAL_TERM = "technical_term"  # 専門用語
    METRIC = "metric"  # 数値・統計
    CONCEPT = "concept"  # 概念
    OTHER = "other"  # その他


class RelationType(str, Enum):
    """関係性タイプ"""
    IS_A = "is_a"  # AはBの一種
    PART_OF = "part_of"  # AはBの一部
    CAUSES = "causes"  # AによってBが起こる
    PRECEDES = "precedes"  # AはBの前に起こる
    SIMILAR_TO = "similar_to"  # AはBに類似
    RELATED_TO = "related_to"  # AはBに関連
    CONTAINS = "contains"  # AはBを含む
    OPPOSITE_OF = "opposite_of"  # AはBの反対


class ImportanceLevel(str, Enum):
    """重要度レベル"""
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


# ========== Entities ==========

class Entity(BaseModel):
    """
    抽出されたエンティティ

    Attributes:
        name: エンティティ名
        type: エンティティタイプ
        description: 説明・定義
        confidence: 信頼度スコア (0.0-1.0)
        source_text: 抽出元のテキスト
        page_number: ページ番号（あれば）
    """
    name: str = Field(..., description="エンティティ名")
    type: EntityType = Field(..., description="エンティティタイプ")
    description: Optional[str] = Field(None, description="説明・定義")
    confidence: float = Field(..., ge=0.0, le=1.0, description="信頼度スコア")
    source_text: Optional[str] = Field(None, description="抽出元のテキスト")
    page_number: Optional[int] = Field(None, description="ページ番号")

    class Config:
        json_schema_extra = {
            "example": {
                "name": "機械学習",
                "type": "technical_term",
                "description": "データから学習するアルゴリズムの総称",
                "confidence": 0.95,
                "source_text": "機械学習はデータから学習するアルゴリズムの総称である。",
                "page_number": 10
            }
        }


class EntityExtractRequest(BaseModel):
    """
    エンティティ抽出リクエスト

    Attributes:
        text: 抽出対象テキスト（textまたはjob_idのいずれか必須）
        job_id: OCRジョブID（textまたはjob_idのいずれか必須）
        entity_types: 抽出するエンティティタイプ（指定しない場合は全タイプ）
        min_confidence: 最小信頼度（これ未満は除外）
        language: 言語（Noneの場合は自動検出）
    """
    text: Optional[str] = Field(None, description="抽出対象テキスト")
    job_id: Optional[str] = Field(None, description="OCRジョブID")
    entity_types: Optional[List[EntityType]] = Field(
        None,
        description="抽出するエンティティタイプ"
    )
    min_confidence: float = Field(
        0.5,
        ge=0.0,
        le=1.0,
        description="最小信頼度"
    )
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
                "job_id": "550e8400-e29b-41d4-a716-446655440000",
                "entity_types": ["person", "technical_term"],
                "min_confidence": 0.7,
                "language": "ja"
            }
        }


class EntityExtractResponse(BaseModel):
    """
    エンティティ抽出レスポンス

    Attributes:
        entities: 抽出されたエンティティのリスト
        total_count: 総エンティティ数
        by_type: タイプ別のカウント
        language: 検出された言語
        processing_time: 処理時間（秒）
        is_mock: モックレスポンスかどうか
    """
    entities: List[Entity] = Field(..., description="抽出されたエンティティ")
    total_count: int = Field(..., description="総エンティティ数")
    by_type: Dict[str, int] = Field(..., description="タイプ別のカウント")
    language: str = Field(..., description="検出された言語")
    processing_time: float = Field(..., description="処理時間（秒）")
    is_mock: bool = Field(..., description="モックレスポンスかどうか")

    class Config:
        json_schema_extra = {
            "example": {
                "entities": [
                    {
                        "name": "機械学習",
                        "type": "technical_term",
                        "description": "データから学習するアルゴリズム",
                        "confidence": 0.95,
                        "source_text": "機械学習はデータから学習する...",
                        "page_number": 10
                    }
                ],
                "total_count": 15,
                "by_type": {
                    "technical_term": 8,
                    "person": 5,
                    "organization": 2
                },
                "language": "ja",
                "processing_time": 2.5,
                "is_mock": False
            }
        }


# ========== Relationships ==========

class Relationship(BaseModel):
    """
    エンティティ間の関係性

    Attributes:
        subject: 主語エンティティ
        predicate: 述語（関係性タイプ）
        object: 目的語エンティティ
        confidence: 信頼度スコア (0.0-1.0)
        source_text: 抽出元のテキスト
        page_number: ページ番号（あれば）
    """
    subject: str = Field(..., description="主語エンティティ")
    predicate: RelationType = Field(..., description="述語（関係性タイプ）")
    object: str = Field(..., description="目的語エンティティ")
    confidence: float = Field(..., ge=0.0, le=1.0, description="信頼度スコア")
    source_text: Optional[str] = Field(None, description="抽出元のテキスト")
    page_number: Optional[int] = Field(None, description="ページ番号")

    class Config:
        json_schema_extra = {
            "example": {
                "subject": "機械学習",
                "predicate": "is_a",
                "object": "人工知能",
                "confidence": 0.9,
                "source_text": "機械学習は人工知能の一種である。",
                "page_number": 12
            }
        }


class RelationshipExtractRequest(BaseModel):
    """
    関係性抽出リクエスト

    Attributes:
        entities: エンティティのリスト（事前に抽出済み）
        text: 抽出対象テキスト（textまたはjob_idのいずれか必須）
        job_id: OCRジョブID（textまたはjob_idのいずれか必須）
        relation_types: 抽出する関係性タイプ（指定しない場合は全タイプ）
        min_confidence: 最小信頼度
        language: 言語
    """
    entities: Optional[List[Entity]] = Field(
        None,
        description="エンティティのリスト（事前抽出済み）"
    )
    text: Optional[str] = Field(None, description="抽出対象テキスト")
    job_id: Optional[str] = Field(None, description="OCRジョブID")
    relation_types: Optional[List[RelationType]] = Field(
        None,
        description="抽出する関係性タイプ"
    )
    min_confidence: float = Field(
        0.5,
        ge=0.0,
        le=1.0,
        description="最小信頼度"
    )
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
                "job_id": "550e8400-e29b-41d4-a716-446655440000",
                "relation_types": ["is_a", "causes"],
                "min_confidence": 0.7
            }
        }


class RelationshipExtractResponse(BaseModel):
    """
    関係性抽出レスポンス

    Attributes:
        relationships: 抽出された関係性のリスト
        total_count: 総関係性数
        by_type: タイプ別のカウント
        processing_time: 処理時間（秒）
        is_mock: モックレスポンスかどうか
    """
    relationships: List[Relationship] = Field(..., description="抽出された関係性")
    total_count: int = Field(..., description="総関係性数")
    by_type: Dict[str, int] = Field(..., description="タイプ別のカウント")
    processing_time: float = Field(..., description="処理時間（秒）")
    is_mock: bool = Field(..., description="モックレスポンスかどうか")

    class Config:
        json_schema_extra = {
            "example": {
                "relationships": [
                    {
                        "subject": "機械学習",
                        "predicate": "is_a",
                        "object": "人工知能",
                        "confidence": 0.9,
                        "source_text": "機械学習は人工知能の一種である。",
                        "page_number": 12
                    }
                ],
                "total_count": 10,
                "by_type": {
                    "is_a": 5,
                    "causes": 3,
                    "related_to": 2
                },
                "processing_time": 3.5,
                "is_mock": False
            }
        }


# ========== Knowledge Graph ==========

class KnowledgeGraphNode(BaseModel):
    """ナレッジグラフのノード"""
    id: str = Field(..., description="ノードID")
    label: str = Field(..., description="ラベル")
    type: EntityType = Field(..., description="エンティティタイプ")
    properties: Dict[str, Any] = Field(default_factory=dict, description="追加プロパティ")


class KnowledgeGraphEdge(BaseModel):
    """ナレッジグラフのエッジ"""
    source: str = Field(..., description="ソースノードID")
    target: str = Field(..., description="ターゲットノードID")
    type: RelationType = Field(..., description="関係性タイプ")
    confidence: float = Field(..., ge=0.0, le=1.0, description="信頼度")


class KnowledgeGraph(BaseModel):
    """
    ナレッジグラフ

    Attributes:
        nodes: ノードのリスト
        edges: エッジのリスト
        metadata: メタデータ
    """
    nodes: List[KnowledgeGraphNode] = Field(..., description="ノード")
    edges: List[KnowledgeGraphEdge] = Field(..., description="エッジ")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="メタデータ")

    class Config:
        json_schema_extra = {
            "example": {
                "nodes": [
                    {
                        "id": "ml",
                        "label": "機械学習",
                        "type": "technical_term",
                        "properties": {"importance": "high"}
                    },
                    {
                        "id": "ai",
                        "label": "人工知能",
                        "type": "technical_term",
                        "properties": {"importance": "high"}
                    }
                ],
                "edges": [
                    {
                        "source": "ml",
                        "target": "ai",
                        "type": "is_a",
                        "confidence": 0.9
                    }
                ],
                "metadata": {
                    "book_title": "AI入門",
                    "created_at": "2025-10-28"
                }
            }
        }


# ========== Knowledge Extraction ==========

class Concept(BaseModel):
    """概念"""
    name: str = Field(..., description="概念名")
    definition: str = Field(..., description="定義")
    importance: ImportanceLevel = Field(..., description="重要度")
    page_number: Optional[int] = Field(None, description="ページ番号")


class Fact(BaseModel):
    """事実"""
    statement: str = Field(..., description="事実の記述")
    source_page: Optional[int] = Field(None, description="ソースページ")
    confidence: float = Field(..., ge=0.0, le=1.0, description="信頼度")


class Process(BaseModel):
    """プロセス・手順"""
    name: str = Field(..., description="プロセス名")
    steps: List[str] = Field(..., description="ステップのリスト")
    description: Optional[str] = Field(None, description="説明")


class Insight(BaseModel):
    """洞察・重要ポイント"""
    text: str = Field(..., description="洞察の内容")
    category: str = Field(..., description="カテゴリ")
    importance: ImportanceLevel = Field(..., description="重要度")


class ActionItem(BaseModel):
    """アクションアイテム"""
    action: str = Field(..., description="アクション内容")
    priority: ImportanceLevel = Field(..., description="優先度")
    context: Optional[str] = Field(None, description="コンテキスト")


class StructuredKnowledge(BaseModel):
    """
    構造化されたナレッジ

    Attributes:
        book_title: 書籍タイトル
        main_topics: 主要トピック
        concepts: 概念のリスト
        facts: 事実のリスト
        processes: プロセスのリスト
        insights: 洞察のリスト
        action_items: アクションアイテムのリスト
        entities: エンティティのリスト
        relationships: 関係性のリスト
    """
    book_title: str = Field(..., description="書籍タイトル")
    main_topics: List[str] = Field(default_factory=list, description="主要トピック")
    concepts: List[Concept] = Field(default_factory=list, description="概念")
    facts: List[Fact] = Field(default_factory=list, description="事実")
    processes: List[Process] = Field(default_factory=list, description="プロセス")
    insights: List[Insight] = Field(default_factory=list, description="洞察")
    action_items: List[ActionItem] = Field(default_factory=list, description="アクションアイテム")
    entities: List[Entity] = Field(default_factory=list, description="エンティティ")
    relationships: List[Relationship] = Field(default_factory=list, description="関係性")


class KnowledgeExtractRequest(BaseModel):
    """
    ナレッジ抽出リクエスト

    Attributes:
        text: 抽出対象テキスト（textまたはjob_idのいずれか必須）
        job_id: OCRジョブID（textまたはjob_idのいずれか必須）
        book_title: 書籍タイトル（job_id使用時は自動取得）
        format: 出力フォーマット
        include_entities: エンティティ抽出を含むか
        include_relationships: 関係性抽出を含むか
        language: 言語（Noneの場合は自動検出）
        min_confidence: 最小信頼度
    """
    text: Optional[str] = Field(None, description="抽出対象テキスト")
    job_id: Optional[str] = Field(None, description="OCRジョブID")
    book_title: Optional[str] = Field(None, description="書籍タイトル")
    format: OutputFormat = Field(
        OutputFormat.YAML,
        description="出力フォーマット"
    )
    include_entities: bool = Field(True, description="エンティティ抽出を含むか")
    include_relationships: bool = Field(
        True,
        description="関係性抽出を含むか"
    )
    language: Optional[str] = Field(None, description="言語（'ja' or 'en'）")
    min_confidence: float = Field(
        0.5,
        ge=0.0,
        le=1.0,
        description="最小信頼度"
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
                "format": "yaml",
                "include_entities": True,
                "include_relationships": True,
                "language": "ja",
                "min_confidence": 0.7
            }
        }


class TokenUsage(BaseModel):
    """トークン使用量"""
    total: int = Field(..., description="総トークン数")
    prompt: int = Field(..., description="プロンプトトークン数")
    completion: int = Field(..., description="生成トークン数")


class KnowledgeExtractResponse(BaseModel):
    """
    ナレッジ抽出レスポンス

    Attributes:
        knowledge_id: ナレッジID
        job_id: 関連するジョブID
        book_title: 書籍タイトル
        format: 出力フォーマット
        structured_data: 構造化データ
        yaml_text: YAML形式テキスト（formatがyamlの場合）
        json_text: JSON形式テキスト（formatがjsonの場合）
        markdown_text: Markdown形式テキスト（formatがmarkdownの場合）
        quality_score: 品質スコア (0.0-1.0)
        language: 検出された言語
        token_usage: トークン使用量
        processing_time: 処理時間（秒）
        is_mock: モックレスポンスかどうか
        created_at: 作成日時
    """
    knowledge_id: int = Field(..., description="ナレッジID")
    job_id: Optional[str] = Field(None, description="関連するジョブID")
    book_title: str = Field(..., description="書籍タイトル")
    format: OutputFormat = Field(..., description="出力フォーマット")
    structured_data: StructuredKnowledge = Field(..., description="構造化データ")
    yaml_text: Optional[str] = Field(None, description="YAML形式テキスト")
    json_text: Optional[str] = Field(None, description="JSON形式テキスト")
    markdown_text: Optional[str] = Field(None, description="Markdown形式テキスト")
    quality_score: float = Field(..., ge=0.0, le=1.0, description="品質スコア")
    language: str = Field(..., description="検出された言語")
    token_usage: TokenUsage = Field(..., description="トークン使用量")
    processing_time: float = Field(..., description="処理時間（秒）")
    is_mock: bool = Field(..., description="モックレスポンスかどうか")
    created_at: datetime = Field(..., description="作成日時")

    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "knowledge_id": 1,
                "job_id": "550e8400-e29b-41d4-a716-446655440000",
                "book_title": "AI入門",
                "format": "yaml",
                "structured_data": {
                    "book_title": "AI入門",
                    "main_topics": ["機械学習", "深層学習"],
                    "concepts": [
                        {
                            "name": "機械学習",
                            "definition": "データから学習するアルゴリズム",
                            "importance": "high"
                        }
                    ],
                    "facts": [],
                    "processes": [],
                    "insights": [],
                    "action_items": [],
                    "entities": [],
                    "relationships": []
                },
                "yaml_text": "book_title: AI入門\nmain_topics:\n  - 機械学習",
                "quality_score": 0.85,
                "language": "ja",
                "token_usage": {
                    "total": 500,
                    "prompt": 400,
                    "completion": 100
                },
                "processing_time": 5.5,
                "is_mock": False,
                "created_at": "2025-10-28T10:30:00"
            }
        }


class KnowledgeDetail(BaseModel):
    """
    ナレッジ詳細情報

    Attributes:
        id: ナレッジID
        book_title: 書籍タイトル
        format: フォーマット
        score: 品質スコア
        created_at: 作成日時
    """
    id: int = Field(..., description="ナレッジID")
    book_title: str = Field(..., description="書籍タイトル")
    format: str = Field(..., description="フォーマット")
    score: Optional[float] = Field(None, description="品質スコア")
    created_at: datetime = Field(..., description="作成日時")

    class Config:
        from_attributes = True


class KnowledgeListResponse(BaseModel):
    """ナレッジリストレスポンス"""
    knowledge: List[KnowledgeDetail] = Field(..., description="ナレッジリスト")
    total: int = Field(..., description="総件数")


class ExportFormat(str, Enum):
    """エクスポートフォーマット"""
    YAML = "yaml"
    JSON = "json"
    MARKDOWN = "markdown"
    CSV = "csv"


class KnowledgeExportRequest(BaseModel):
    """ナレッジエクスポートリクエスト"""
    format: ExportFormat = Field(..., description="エクスポートフォーマット")
    include_metadata: bool = Field(True, description="メタデータを含むか")

    class Config:
        json_schema_extra = {
            "example": {
                "format": "yaml",
                "include_metadata": True
            }
        }


class KnowledgeExportResponse(BaseModel):
    """ナレッジエクスポートレスポンス"""
    content: str = Field(..., description="エクスポートされたコンテンツ")
    format: ExportFormat = Field(..., description="フォーマット")
    filename: str = Field(..., description="推奨ファイル名")
    size_bytes: int = Field(..., description="サイズ（バイト）")

    class Config:
        json_schema_extra = {
            "example": {
                "content": "book_title: AI入門\n...",
                "format": "yaml",
                "filename": "ai_intro_knowledge.yaml",
                "size_bytes": 1024
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
