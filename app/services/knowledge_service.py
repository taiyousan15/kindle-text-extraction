"""
Knowledge Extraction Service

LLMベースのナレッジ抽出サービス
- Phase 4-1: LLM-based knowledge extraction
- Phase 4-2: YAML/JSON structured output
- Phase 4-3: Entity extraction (NER)
- Phase 4-4: Relationship extraction
"""
import logging
import re
import json
import yaml
import time
from typing import Optional, List, Dict, Any, Tuple
from sqlalchemy.orm import Session

from app.services.llm_service import LLMService
from app.models.knowledge import Knowledge
from app.models.job import Job
from app.models.ocr_result import OCRResult
from app.schemas.knowledge import (
    Entity,
    EntityType,
    Relationship,
    RelationType,
    Concept,
    Fact,
    Process,
    Insight,
    ActionItem,
    StructuredKnowledge,
    KnowledgeGraph,
    KnowledgeGraphNode,
    KnowledgeGraphEdge,
    ImportanceLevel,
    OutputFormat,
)

logger = logging.getLogger(__name__)


class KnowledgeService:
    """ナレッジ抽出サービス"""

    def __init__(self, llm_service: Optional[LLMService] = None):
        """
        初期化

        Args:
            llm_service: LLMサービスインスタンス（Noneの場合は新規作成）
        """
        self.llm = llm_service or LLMService(provider="anthropic")
        self.is_mock = self.llm.is_mock

    # ========== Phase 4-1: Knowledge Extraction ==========

    def extract_knowledge(
        self,
        text: str,
        book_title: str,
        language: Optional[str] = None,
        include_entities: bool = True,
        include_relationships: bool = True,
        min_confidence: float = 0.5
    ) -> Dict[str, Any]:
        """
        テキストからナレッジを抽出

        Args:
            text: 抽出対象テキスト
            book_title: 書籍タイトル
            language: 言語（'ja' or 'en'、Noneの場合は自動検出）
            include_entities: エンティティ抽出を含むか
            include_relationships: 関係性抽出を含むか
            min_confidence: 最小信頼度

        Returns:
            {
                "structured_data": StructuredKnowledge,
                "entities": List[Entity],
                "relationships": List[Relationship],
                "quality_score": float,
                "language": str,
                "token_usage": dict
            }
        """
        start_time = time.time()

        # 言語検出
        if language is None:
            language = self._detect_language(text)

        logger.info(
            f"Extracting knowledge from text (length={len(text)}, "
            f"language={language}, book_title={book_title})"
        )

        # モックモード
        if self.is_mock:
            return self._extract_knowledge_mock(
                text, book_title, language, include_entities, include_relationships
            )

        # 1. 構造化ナレッジ抽出（概念、事実、プロセス、洞察、アクション）
        structured_data = self._extract_structured_knowledge(
            text, book_title, language
        )

        # 2. エンティティ抽出（オプション）
        entities = []
        if include_entities:
            entities = self._extract_entities_internal(
                text, language, min_confidence
            )
            structured_data["entities"] = entities

        # 3. 関係性抽出（オプション）
        relationships = []
        if include_relationships and entities:
            relationships = self._extract_relationships_internal(
                text, entities, language, min_confidence
            )
            structured_data["relationships"] = relationships

        # 品質スコア計算
        quality_score = self._calculate_quality_score(structured_data)

        processing_time = time.time() - start_time

        logger.info(
            f"Knowledge extraction completed in {processing_time:.2f}s "
            f"(quality_score={quality_score:.2f})"
        )

        return {
            "structured_data": structured_data,
            "entities": entities,
            "relationships": relationships,
            "quality_score": quality_score,
            "language": language,
            "token_usage": self.llm.get_token_usage(),
            "processing_time": processing_time
        }

    def _extract_structured_knowledge(
        self,
        text: str,
        book_title: str,
        language: str
    ) -> StructuredKnowledge:
        """
        構造化ナレッジ抽出（概念、事実、プロセス、洞察、アクション）

        Args:
            text: テキスト
            book_title: 書籍タイトル
            language: 言語

        Returns:
            StructuredKnowledge
        """
        # チャンク分割（長文対応）
        chunks = self._split_into_chunks(text, max_length=3000)

        all_concepts = []
        all_facts = []
        all_processes = []
        all_insights = []
        all_action_items = []
        all_topics = []

        for i, chunk in enumerate(chunks):
            logger.debug(f"Processing chunk {i+1}/{len(chunks)}")

            # プロンプト構築
            system_prompt = self._build_knowledge_extraction_system_prompt(language)
            user_prompt = self._build_knowledge_extraction_user_prompt(
                chunk, book_title, language
            )

            # LLM生成
            result = self.llm.generate(
                prompt=user_prompt,
                system_prompt=system_prompt
            )

            # パース
            parsed = self._parse_knowledge_extraction_response(
                result["content"], language
            )

            all_concepts.extend(parsed["concepts"])
            all_facts.extend(parsed["facts"])
            all_processes.extend(parsed["processes"])
            all_insights.extend(parsed["insights"])
            all_action_items.extend(parsed["action_items"])
            all_topics.extend(parsed["main_topics"])

        # 重複削除
        unique_topics = list(set(all_topics))

        return StructuredKnowledge(
            book_title=book_title,
            main_topics=unique_topics[:10],  # 上位10トピック
            concepts=all_concepts[:20],
            facts=all_facts[:30],
            processes=all_processes[:10],
            insights=all_insights[:15],
            action_items=all_action_items[:15],
            entities=[],
            relationships=[]
        )

    def _build_knowledge_extraction_system_prompt(self, language: str) -> str:
        """ナレッジ抽出用システムプロンプト"""
        if language == "ja":
            return """あなたは書籍や文書から重要なナレッジを抽出する専門家です。
以下の情報を抽出してください：

1. **主要トピック**: 文書の主要なテーマ（3-5個）
2. **概念**: 重要な概念とその定義（重要度付き）
3. **事実**: 重要な事実や統計データ
4. **プロセス**: 説明されている手順やプロセス
5. **洞察**: 重要な洞察や学び
6. **アクションアイテム**: 実行可能な推奨事項

日本語で正確に抽出し、構造化された形式で出力してください。"""
        else:
            return """You are an expert at extracting important knowledge from books and documents.
Extract the following information:

1. **Main Topics**: Key themes (3-5 topics)
2. **Concepts**: Important concepts with definitions (with importance level)
3. **Facts**: Important facts and statistics
4. **Processes**: Described procedures or processes
5. **Insights**: Key insights and learnings
6. **Action Items**: Actionable recommendations

Extract accurately and output in a structured format."""

    def _build_knowledge_extraction_user_prompt(
        self,
        text: str,
        book_title: str,
        language: str
    ) -> str:
        """ナレッジ抽出用ユーザープロンプト"""
        if language == "ja":
            return f"""以下のテキストから重要なナレッジを抽出してください。

【書籍タイトル】
{book_title}

【テキスト】
{text}

【出力形式】
以下のJSON形式で出力してください：

{{
  "main_topics": ["トピック1", "トピック2", ...],
  "concepts": [
    {{
      "name": "概念名",
      "definition": "定義",
      "importance": "high|medium|low"
    }}
  ],
  "facts": [
    {{
      "statement": "事実の記述",
      "confidence": 0.9
    }}
  ],
  "processes": [
    {{
      "name": "プロセス名",
      "steps": ["ステップ1", "ステップ2"],
      "description": "説明"
    }}
  ],
  "insights": [
    {{
      "text": "洞察の内容",
      "category": "カテゴリ",
      "importance": "high|medium|low"
    }}
  ],
  "action_items": [
    {{
      "action": "アクション内容",
      "priority": "high|medium|low",
      "context": "コンテキスト"
    }}
  ]
}}"""
        else:
            return f"""Extract important knowledge from the following text.

【Book Title】
{book_title}

【Text】
{text}

【Output Format】
Output in the following JSON format:

{{
  "main_topics": ["Topic 1", "Topic 2", ...],
  "concepts": [
    {{
      "name": "Concept name",
      "definition": "Definition",
      "importance": "high|medium|low"
    }}
  ],
  "facts": [
    {{
      "statement": "Fact statement",
      "confidence": 0.9
    }}
  ],
  "processes": [
    {{
      "name": "Process name",
      "steps": ["Step 1", "Step 2"],
      "description": "Description"
    }}
  ],
  "insights": [
    {{
      "text": "Insight content",
      "category": "Category",
      "importance": "high|medium|low"
    }}
  ],
  "action_items": [
    {{
      "action": "Action content",
      "priority": "high|medium|low",
      "context": "Context"
    }}
  ]
}}"""

    def _parse_knowledge_extraction_response(
        self,
        response: str,
        language: str
    ) -> Dict[str, Any]:
        """
        ナレッジ抽出レスポンスをパース

        Args:
            response: LLMレスポンス
            language: 言語

        Returns:
            パースされた辞書
        """
        try:
            # JSON抽出
            json_match = re.search(r'\{[\s\S]*\}', response)
            if json_match:
                data = json.loads(json_match.group())
            else:
                logger.warning("Failed to parse JSON from response")
                return self._empty_knowledge_response()

            # Pydanticモデルに変換
            concepts = [
                Concept(
                    name=c.get("name", ""),
                    definition=c.get("definition", ""),
                    importance=ImportanceLevel(c.get("importance", "medium"))
                )
                for c in data.get("concepts", [])
            ]

            facts = [
                Fact(
                    statement=f.get("statement", ""),
                    confidence=f.get("confidence", 0.8)
                )
                for f in data.get("facts", [])
            ]

            processes = [
                Process(
                    name=p.get("name", ""),
                    steps=p.get("steps", []),
                    description=p.get("description")
                )
                for p in data.get("processes", [])
            ]

            insights = [
                Insight(
                    text=i.get("text", ""),
                    category=i.get("category", "general"),
                    importance=ImportanceLevel(i.get("importance", "medium"))
                )
                for i in data.get("insights", [])
            ]

            action_items = [
                ActionItem(
                    action=a.get("action", ""),
                    priority=ImportanceLevel(a.get("priority", "medium")),
                    context=a.get("context")
                )
                for a in data.get("action_items", [])
            ]

            return {
                "main_topics": data.get("main_topics", []),
                "concepts": concepts,
                "facts": facts,
                "processes": processes,
                "insights": insights,
                "action_items": action_items
            }

        except Exception as e:
            logger.error(f"Failed to parse knowledge extraction response: {e}")
            return self._empty_knowledge_response()

    def _empty_knowledge_response(self) -> Dict[str, Any]:
        """空のナレッジレスポンス"""
        return {
            "main_topics": [],
            "concepts": [],
            "facts": [],
            "processes": [],
            "insights": [],
            "action_items": []
        }

    # ========== Phase 4-3: Entity Extraction ==========

    def extract_entities(
        self,
        text: str,
        language: Optional[str] = None,
        entity_types: Optional[List[EntityType]] = None,
        min_confidence: float = 0.5
    ) -> List[Entity]:
        """
        エンティティ抽出（NER）

        Args:
            text: テキスト
            language: 言語
            entity_types: 抽出するエンティティタイプ
            min_confidence: 最小信頼度

        Returns:
            エンティティのリスト
        """
        if language is None:
            language = self._detect_language(text)

        logger.info(f"Extracting entities from text (language={language})")

        if self.is_mock:
            return self._extract_entities_mock(text, language)

        return self._extract_entities_internal(
            text, language, min_confidence, entity_types
        )

    def _extract_entities_internal(
        self,
        text: str,
        language: str,
        min_confidence: float = 0.5,
        entity_types: Optional[List[EntityType]] = None
    ) -> List[Entity]:
        """内部エンティティ抽出ロジック"""
        # チャンク分割
        chunks = self._split_into_chunks(text, max_length=2000)

        all_entities = []

        for chunk in chunks:
            system_prompt = self._build_entity_extraction_system_prompt(
                language, entity_types
            )
            user_prompt = self._build_entity_extraction_user_prompt(
                chunk, language
            )

            result = self.llm.generate(
                prompt=user_prompt,
                system_prompt=system_prompt
            )

            entities = self._parse_entity_extraction_response(
                result["content"], language
            )
            all_entities.extend(entities)

        # 信頼度フィルタリング
        filtered = [e for e in all_entities if e.confidence >= min_confidence]

        # 重複削除（名前ベース）
        unique_entities = self._deduplicate_entities(filtered)

        logger.info(f"Extracted {len(unique_entities)} unique entities")

        return unique_entities

    def _build_entity_extraction_system_prompt(
        self,
        language: str,
        entity_types: Optional[List[EntityType]] = None
    ) -> str:
        """エンティティ抽出用システムプロンプト"""
        types_str = ", ".join([et.value for et in entity_types]) if entity_types else "all types"

        if language == "ja":
            return f"""あなたは固有表現抽出（NER）の専門家です。
以下のエンティティタイプを抽出してください: {types_str}

- person: 人物名
- organization: 組織名、企業名
- location: 地名、国名
- date: 日付
- time: 時刻
- technical_term: 専門用語、キーワード
- metric: 数値、統計
- concept: 概念
- other: その他

各エンティティに信頼度（0.0-1.0）を付与してください。"""
        else:
            return f"""You are a Named Entity Recognition (NER) expert.
Extract the following entity types: {types_str}

- person: Person names
- organization: Organization names
- location: Locations
- date: Dates
- time: Times
- technical_term: Technical terms
- metric: Metrics, numbers
- concept: Concepts
- other: Other

Assign confidence score (0.0-1.0) to each entity."""

    def _build_entity_extraction_user_prompt(
        self,
        text: str,
        language: str
    ) -> str:
        """エンティティ抽出用ユーザープロンプト"""
        if language == "ja":
            return f"""以下のテキストからエンティティを抽出してください。

【テキスト】
{text}

【出力形式】
JSON配列で出力してください：

[
  {{
    "name": "エンティティ名",
    "type": "person|organization|location|date|time|technical_term|metric|concept|other",
    "description": "説明（オプション）",
    "confidence": 0.9
  }}
]"""
        else:
            return f"""Extract entities from the following text.

【Text】
{text}

【Output Format】
Output as JSON array:

[
  {{
    "name": "Entity name",
    "type": "person|organization|location|date|time|technical_term|metric|concept|other",
    "description": "Description (optional)",
    "confidence": 0.9
  }}
]"""

    def _parse_entity_extraction_response(
        self,
        response: str,
        language: str
    ) -> List[Entity]:
        """エンティティ抽出レスポンスをパース"""
        try:
            # JSON配列抽出
            json_match = re.search(r'\[[\s\S]*\]', response)
            if json_match:
                data = json.loads(json_match.group())
            else:
                logger.warning("Failed to parse JSON array from response")
                return []

            entities = []
            for item in data:
                try:
                    entity = Entity(
                        name=item.get("name", ""),
                        type=EntityType(item.get("type", "other")),
                        description=item.get("description"),
                        confidence=item.get("confidence", 0.7),
                        source_text=item.get("source_text")
                    )
                    entities.append(entity)
                except Exception as e:
                    logger.warning(f"Failed to parse entity: {e}")
                    continue

            return entities

        except Exception as e:
            logger.error(f"Failed to parse entity extraction response: {e}")
            return []

    def _deduplicate_entities(self, entities: List[Entity]) -> List[Entity]:
        """エンティティの重複削除"""
        seen = {}
        for entity in entities:
            key = (entity.name.lower(), entity.type)
            if key not in seen or entity.confidence > seen[key].confidence:
                seen[key] = entity
        return list(seen.values())

    # ========== Phase 4-4: Relationship Extraction ==========

    def extract_relationships(
        self,
        text: str,
        entities: List[Entity],
        language: Optional[str] = None,
        relation_types: Optional[List[RelationType]] = None,
        min_confidence: float = 0.5
    ) -> List[Relationship]:
        """
        関係性抽出

        Args:
            text: テキスト
            entities: エンティティリスト
            language: 言語
            relation_types: 抽出する関係性タイプ
            min_confidence: 最小信頼度

        Returns:
            関係性のリスト
        """
        if language is None:
            language = self._detect_language(text)

        logger.info(
            f"Extracting relationships from {len(entities)} entities "
            f"(language={language})"
        )

        if self.is_mock:
            return self._extract_relationships_mock(entities, language)

        return self._extract_relationships_internal(
            text, entities, language, min_confidence, relation_types
        )

    def _extract_relationships_internal(
        self,
        text: str,
        entities: List[Entity],
        language: str,
        min_confidence: float = 0.5,
        relation_types: Optional[List[RelationType]] = None
    ) -> List[Relationship]:
        """内部関係性抽出ロジック"""
        if not entities:
            return []

        # エンティティ名リスト
        entity_names = [e.name for e in entities]

        # チャンク分割
        chunks = self._split_into_chunks(text, max_length=2000)

        all_relationships = []

        for chunk in chunks:
            system_prompt = self._build_relationship_extraction_system_prompt(
                language, relation_types
            )
            user_prompt = self._build_relationship_extraction_user_prompt(
                chunk, entity_names, language
            )

            result = self.llm.generate(
                prompt=user_prompt,
                system_prompt=system_prompt
            )

            relationships = self._parse_relationship_extraction_response(
                result["content"], language
            )
            all_relationships.extend(relationships)

        # 信頼度フィルタリング
        filtered = [r for r in all_relationships if r.confidence >= min_confidence]

        # 重複削除
        unique_relationships = self._deduplicate_relationships(filtered)

        logger.info(f"Extracted {len(unique_relationships)} unique relationships")

        return unique_relationships

    def _build_relationship_extraction_system_prompt(
        self,
        language: str,
        relation_types: Optional[List[RelationType]] = None
    ) -> str:
        """関係性抽出用システムプロンプト"""
        types_str = ", ".join([rt.value for rt in relation_types]) if relation_types else "all types"

        if language == "ja":
            return f"""あなたは関係性抽出の専門家です。
以下の関係性タイプを抽出してください: {types_str}

- is_a: AはBの一種
- part_of: AはBの一部
- causes: AによってBが起こる
- precedes: AはBの前に起こる
- similar_to: AはBに類似
- related_to: AはBに関連
- contains: AはBを含む
- opposite_of: AはBの反対

各関係性に信頼度（0.0-1.0）を付与してください。"""
        else:
            return f"""You are a relationship extraction expert.
Extract the following relationship types: {types_str}

- is_a: A is a type of B
- part_of: A is part of B
- causes: A causes B
- precedes: A precedes B
- similar_to: A is similar to B
- related_to: A is related to B
- contains: A contains B
- opposite_of: A is opposite of B

Assign confidence score (0.0-1.0) to each relationship."""

    def _build_relationship_extraction_user_prompt(
        self,
        text: str,
        entity_names: List[str],
        language: str
    ) -> str:
        """関係性抽出用ユーザープロンプト"""
        entities_str = ", ".join(entity_names[:30])  # 最大30エンティティ

        if language == "ja":
            return f"""以下のテキストから、指定されたエンティティ間の関係性を抽出してください。

【エンティティ】
{entities_str}

【テキスト】
{text}

【出力形式】
JSON配列で出力してください：

[
  {{
    "subject": "主語エンティティ",
    "predicate": "is_a|part_of|causes|precedes|similar_to|related_to|contains|opposite_of",
    "object": "目的語エンティティ",
    "confidence": 0.9,
    "source_text": "抽出元のテキスト（オプション）"
  }}
]"""
        else:
            return f"""Extract relationships between the specified entities from the following text.

【Entities】
{entities_str}

【Text】
{text}

【Output Format】
Output as JSON array:

[
  {{
    "subject": "Subject entity",
    "predicate": "is_a|part_of|causes|precedes|similar_to|related_to|contains|opposite_of",
    "object": "Object entity",
    "confidence": 0.9,
    "source_text": "Source text (optional)"
  }}
]"""

    def _parse_relationship_extraction_response(
        self,
        response: str,
        language: str
    ) -> List[Relationship]:
        """関係性抽出レスポンスをパース"""
        try:
            # JSON配列抽出
            json_match = re.search(r'\[[\s\S]*\]', response)
            if json_match:
                data = json.loads(json_match.group())
            else:
                logger.warning("Failed to parse JSON array from response")
                return []

            relationships = []
            for item in data:
                try:
                    relationship = Relationship(
                        subject=item.get("subject", ""),
                        predicate=RelationType(item.get("predicate", "related_to")),
                        object=item.get("object", ""),
                        confidence=item.get("confidence", 0.7),
                        source_text=item.get("source_text")
                    )
                    relationships.append(relationship)
                except Exception as e:
                    logger.warning(f"Failed to parse relationship: {e}")
                    continue

            return relationships

        except Exception as e:
            logger.error(f"Failed to parse relationship extraction response: {e}")
            return []

    def _deduplicate_relationships(
        self,
        relationships: List[Relationship]
    ) -> List[Relationship]:
        """関係性の重複削除"""
        seen = {}
        for rel in relationships:
            key = (
                rel.subject.lower(),
                rel.predicate,
                rel.object.lower()
            )
            if key not in seen or rel.confidence > seen[key].confidence:
                seen[key] = rel
        return list(seen.values())

    # ========== Knowledge Graph Construction ==========

    def build_knowledge_graph(
        self,
        entities: List[Entity],
        relationships: List[Relationship],
        book_title: str
    ) -> KnowledgeGraph:
        """
        ナレッジグラフ構築

        Args:
            entities: エンティティリスト
            relationships: 関係性リスト
            book_title: 書籍タイトル

        Returns:
            KnowledgeGraph
        """
        logger.info(
            f"Building knowledge graph with {len(entities)} nodes "
            f"and {len(relationships)} edges"
        )

        # ノード作成
        nodes = []
        for entity in entities:
            node_id = self._sanitize_node_id(entity.name)
            node = KnowledgeGraphNode(
                id=node_id,
                label=entity.name,
                type=entity.type,
                properties={
                    "description": entity.description,
                    "confidence": entity.confidence
                }
            )
            nodes.append(node)

        # エッジ作成
        edges = []
        node_ids = {self._sanitize_node_id(e.name) for e in entities}

        for rel in relationships:
            source_id = self._sanitize_node_id(rel.subject)
            target_id = self._sanitize_node_id(rel.object)

            # 両方のノードが存在する場合のみエッジ追加
            if source_id in node_ids and target_id in node_ids:
                edge = KnowledgeGraphEdge(
                    source=source_id,
                    target=target_id,
                    type=rel.predicate,
                    confidence=rel.confidence
                )
                edges.append(edge)

        return KnowledgeGraph(
            nodes=nodes,
            edges=edges,
            metadata={
                "book_title": book_title,
                "node_count": len(nodes),
                "edge_count": len(edges)
            }
        )

    def _sanitize_node_id(self, name: str) -> str:
        """ノードID生成（ASCII安全）"""
        # 日本語などを含む場合は簡易ハッシュ
        import hashlib
        return hashlib.md5(name.encode()).hexdigest()[:16]

    # ========== Phase 4-2: YAML/JSON Formatting ==========

    def format_as_yaml(self, structured_data: StructuredKnowledge) -> str:
        """YAML形式に変換"""
        # Pydanticモデルを辞書に変換
        data_dict = structured_data.model_dump()
        return yaml.dump(data_dict, allow_unicode=True, sort_keys=False)

    def format_as_json(self, structured_data: StructuredKnowledge) -> str:
        """JSON形式に変換"""
        data_dict = structured_data.model_dump()
        return json.dumps(data_dict, ensure_ascii=False, indent=2)

    def format_as_markdown(self, structured_data: StructuredKnowledge) -> str:
        """Markdown形式に変換"""
        lines = [f"# {structured_data.book_title}", ""]

        # Main Topics
        if structured_data.main_topics:
            lines.append("## 主要トピック")
            for topic in structured_data.main_topics:
                lines.append(f"- {topic}")
            lines.append("")

        # Concepts
        if structured_data.concepts:
            lines.append("## 概念")
            for concept in structured_data.concepts:
                lines.append(f"### {concept.name} ({concept.importance})")
                lines.append(f"{concept.definition}")
                lines.append("")

        # Facts
        if structured_data.facts:
            lines.append("## 事実")
            for fact in structured_data.facts:
                lines.append(f"- {fact.statement} (信頼度: {fact.confidence:.2f})")
            lines.append("")

        # Processes
        if structured_data.processes:
            lines.append("## プロセス")
            for process in structured_data.processes:
                lines.append(f"### {process.name}")
                if process.description:
                    lines.append(f"{process.description}")
                for i, step in enumerate(process.steps, 1):
                    lines.append(f"{i}. {step}")
                lines.append("")

        # Insights
        if structured_data.insights:
            lines.append("## 洞察")
            for insight in structured_data.insights:
                lines.append(
                    f"- **{insight.category}** ({insight.importance}): {insight.text}"
                )
            lines.append("")

        # Action Items
        if structured_data.action_items:
            lines.append("## アクションアイテム")
            for action in structured_data.action_items:
                lines.append(f"- [{action.priority}] {action.action}")
                if action.context:
                    lines.append(f"  - {action.context}")
            lines.append("")

        return "\n".join(lines)

    def format_relationships_as_csv(
        self,
        relationships: List[Relationship]
    ) -> str:
        """関係性をCSV形式に変換"""
        import csv
        import io

        output = io.StringIO()
        writer = csv.writer(output)

        # ヘッダー
        writer.writerow([
            "Subject", "Predicate", "Object", "Confidence", "Source Text"
        ])

        # データ
        for rel in relationships:
            writer.writerow([
                rel.subject,
                rel.predicate.value,
                rel.object,
                f"{rel.confidence:.2f}",
                rel.source_text or ""
            ])

        return output.getvalue()

    # ========== Utility Methods ==========

    def _detect_language(self, text: str) -> str:
        """言語自動検出（簡易版）"""
        # 日本語文字の割合をチェック
        japanese_chars = sum(
            1 for c in text if '\u3040' <= c <= '\u309F' or  # ひらがな
            '\u30A0' <= c <= '\u30FF' or  # カタカナ
            '\u4E00' <= c <= '\u9FFF'     # 漢字
        )
        total_chars = len(text)

        if total_chars > 0 and japanese_chars / total_chars > 0.1:
            return "ja"
        return "en"

    def _split_into_chunks(
        self,
        text: str,
        max_length: int = 3000,
        overlap: int = 200
    ) -> List[str]:
        """
        テキストをチャンクに分割（オーバーラップ付き）

        Args:
            text: テキスト
            max_length: 最大文字数
            overlap: オーバーラップ文字数

        Returns:
            チャンクのリスト
        """
        if len(text) <= max_length:
            return [text]

        chunks = []
        start = 0

        while start < len(text):
            end = start + max_length
            chunk = text[start:end]

            # 文の途中で切れないように調整
            if end < len(text):
                last_period = max(
                    chunk.rfind('。'),
                    chunk.rfind('.'),
                    chunk.rfind('\n')
                )
                if last_period > max_length // 2:
                    chunk = chunk[:last_period + 1]
                    end = start + last_period + 1

            chunks.append(chunk)
            start = end - overlap

        return chunks

    def _calculate_quality_score(
        self,
        structured_data: StructuredKnowledge
    ) -> float:
        """
        品質スコア計算

        Args:
            structured_data: 構造化データ

        Returns:
            品質スコア (0.0-1.0)
        """
        score = 0.0
        weights = {
            "main_topics": 0.15,
            "concepts": 0.25,
            "facts": 0.15,
            "processes": 0.1,
            "insights": 0.2,
            "action_items": 0.15
        }

        # 各カテゴリの存在をチェック
        if structured_data.main_topics:
            score += weights["main_topics"]
        if structured_data.concepts:
            score += weights["concepts"]
        if structured_data.facts:
            score += weights["facts"]
        if structured_data.processes:
            score += weights["processes"]
        if structured_data.insights:
            score += weights["insights"]
        if structured_data.action_items:
            score += weights["action_items"]

        return min(score, 1.0)

    # ========== Mock Methods ==========

    def _extract_knowledge_mock(
        self,
        text: str,
        book_title: str,
        language: str,
        include_entities: bool,
        include_relationships: bool
    ) -> Dict[str, Any]:
        """モックナレッジ抽出"""
        concepts = [
            Concept(
                name="機械学習" if language == "ja" else "Machine Learning",
                definition="データから学習するアルゴリズム" if language == "ja" else "Algorithms that learn from data",
                importance=ImportanceLevel.HIGH
            )
        ]

        entities = []
        if include_entities:
            entities = self._extract_entities_mock(text, language)

        relationships = []
        if include_relationships and entities:
            relationships = self._extract_relationships_mock(entities, language)

        structured_data = StructuredKnowledge(
            book_title=book_title,
            main_topics=["AI", "機械学習"] if language == "ja" else ["AI", "ML"],
            concepts=concepts,
            facts=[
                Fact(
                    statement="AI市場は急成長している" if language == "ja" else "AI market is growing rapidly",
                    confidence=0.9
                )
            ],
            processes=[],
            insights=[
                Insight(
                    text="AIは様々な産業で活用されている" if language == "ja" else "AI is used in various industries",
                    category="general",
                    importance=ImportanceLevel.HIGH
                )
            ],
            action_items=[
                ActionItem(
                    action="AIツールを試してみる" if language == "ja" else "Try AI tools",
                    priority=ImportanceLevel.MEDIUM
                )
            ],
            entities=entities,
            relationships=relationships
        )

        return {
            "structured_data": structured_data,
            "entities": entities,
            "relationships": relationships,
            "quality_score": 0.75,
            "language": language,
            "token_usage": {"total": 0, "prompt": 0, "completion": 0},
            "processing_time": 0.1
        }

    def _extract_entities_mock(
        self,
        text: str,
        language: str
    ) -> List[Entity]:
        """モックエンティティ抽出"""
        if language == "ja":
            return [
                Entity(
                    name="機械学習",
                    type=EntityType.TECHNICAL_TERM,
                    description="データから学習するアルゴリズム",
                    confidence=0.95
                ),
                Entity(
                    name="深層学習",
                    type=EntityType.TECHNICAL_TERM,
                    description="多層ニューラルネットワークを使用",
                    confidence=0.9
                )
            ]
        else:
            return [
                Entity(
                    name="Machine Learning",
                    type=EntityType.TECHNICAL_TERM,
                    description="Algorithms that learn from data",
                    confidence=0.95
                ),
                Entity(
                    name="Deep Learning",
                    type=EntityType.TECHNICAL_TERM,
                    description="Uses multi-layer neural networks",
                    confidence=0.9
                )
            ]

    def _extract_relationships_mock(
        self,
        entities: List[Entity],
        language: str
    ) -> List[Relationship]:
        """モック関係性抽出"""
        if len(entities) < 2:
            return []

        return [
            Relationship(
                subject=entities[0].name,
                predicate=RelationType.IS_A,
                object="人工知能" if language == "ja" else "Artificial Intelligence",
                confidence=0.9,
                source_text="機械学習は人工知能の一種である" if language == "ja" else "ML is a type of AI"
            )
        ]


# ========== Database Operations ==========

def save_knowledge_to_db(
    db: Session,
    user_id: int,
    book_title: str,
    format: str,
    yaml_text: str,
    content_blob: Optional[bytes],
    score: float
) -> Knowledge:
    """
    ナレッジをDBに保存

    Args:
        db: DBセッション
        user_id: ユーザーID
        book_title: 書籍タイトル
        format: フォーマット
        yaml_text: YAMLテキスト
        content_blob: バイナリコンテンツ
        score: 品質スコア

    Returns:
        保存されたKnowledgeモデル
    """
    knowledge = Knowledge(
        user_id=user_id,
        book_title=book_title,
        format=format,
        yaml_text=yaml_text,
        content_blob=content_blob,
        score=score
    )
    db.add(knowledge)
    db.commit()
    db.refresh(knowledge)

    logger.info(f"Saved knowledge to DB: id={knowledge.id}, book_title={book_title}")

    return knowledge


def get_knowledge_by_id(db: Session, knowledge_id: int, user_id: int) -> Optional[Knowledge]:
    """IDでナレッジ取得 (ユーザーフィルタリング)"""
    return db.query(Knowledge).filter(
        Knowledge.id == knowledge_id,
        Knowledge.user_id == user_id
    ).first()


def get_knowledge_by_book_title(
    db: Session,
    book_title: str,
    user_id: int
) -> List[Knowledge]:
    """書籍タイトルでナレッジ取得 (ユーザーフィルタリング)"""
    return db.query(Knowledge).filter(
        Knowledge.book_title == book_title,
        Knowledge.user_id == user_id
    ).order_by(Knowledge.created_at.desc()).all()


def get_text_from_job(db: Session, job_id: str, user_id: int) -> Tuple[Optional[str], Optional[str]]:
    """
    ジョブIDからテキストと書籍タイトルを取得

    Args:
        db: DBセッション
        job_id: ジョブID
        user_id: ユーザーID

    Returns:
        (text, book_title) または (None, None)
    """
    job = db.query(Job).filter(
        Job.id == job_id,
        Job.user_id == user_id
    ).first()
    if not job:
        logger.warning(f"Job not found: {job_id}")
        return None, None

    # OCR結果を取得
    ocr_results = db.query(OCRResult).filter(
        OCRResult.job_id == job_id
    ).order_by(OCRResult.page_number).all()

    if not ocr_results:
        logger.warning(f"No OCR results found for job: {job_id}")
        return None, None

    # テキスト結合
    text = "\n\n".join([r.text for r in ocr_results if r.text])

    # 書籍タイトル（最初のOCR結果から推測、または空文字列）
    book_title = ""
    if ocr_results and ocr_results[0].text:
        # 最初の行をタイトルとする（簡易版）
        first_line = ocr_results[0].text.split('\n')[0]
        book_title = first_line[:100]  # 最大100文字

    return text, book_title
