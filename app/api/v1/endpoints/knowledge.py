"""
Knowledge Extraction Endpoint

ナレッジ抽出機能のエンドポイント
Phase 4 Complete Implementation (4-1 to 4-4)
"""
from fastapi import APIRouter, Depends, HTTPException, status, Response
from fastapi.responses import PlainTextResponse
from sqlalchemy.orm import Session
from typing import List, Optional
import logging
from datetime import datetime

from app.core.database import get_db
from app.core.security import get_current_active_user
from app.models.knowledge import Knowledge
from app.models.user import User
from app.schemas.knowledge import (
    # Knowledge Extraction
    KnowledgeExtractRequest,
    KnowledgeExtractResponse,
    KnowledgeDetail,
    KnowledgeListResponse,
    KnowledgeExportRequest,
    KnowledgeExportResponse,
    # Entity Extraction
    EntityExtractRequest,
    EntityExtractResponse,
    # Relationship Extraction
    RelationshipExtractRequest,
    RelationshipExtractResponse,
    # Knowledge Graph
    KnowledgeGraph,
    # Common
    OutputFormat,
    ExportFormat,
    TokenUsage,
    ErrorResponse,
)
from app.services.knowledge_service import (
    KnowledgeService,
    get_text_from_job,
    save_knowledge_to_db,
    get_knowledge_by_id,
    get_knowledge_by_book_title,
)

# ロガー設定
logger = logging.getLogger(__name__)

# ルーター設定
router = APIRouter()


# ========== Knowledge Extraction Endpoints ==========

@router.post(
    "/extract",
    response_model=KnowledgeExtractResponse,
    status_code=status.HTTP_201_CREATED,
    summary="ナレッジ抽出",
    description="テキストまたはOCRジョブからナレッジを抽出します（Phase 4-1, 4-2）"
)
async def extract_knowledge(
    request: KnowledgeExtractRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    ナレッジ抽出エンドポイント

    - textまたはjob_idのいずれか必須
    - 構造化データ（概念、事実、プロセス、洞察、アクション）を抽出
    - エンティティと関係性もオプションで抽出可能
    - YAML/JSON/Markdownフォーマットで出力
    """
    logger.info(f"Knowledge extraction request: format={request.format}")

    # テキスト取得
    if request.text:
        text = request.text
        book_title = request.book_title or "Untitled"
        job_id = None
    elif request.job_id:
        text, book_title_from_job = get_text_from_job(db, request.job_id, current_user.id)
        if text is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Job not found or no text available: {request.job_id}"
            )
        book_title = request.book_title or book_title_from_job or "Untitled"
        job_id = request.job_id
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Either 'text' or 'job_id' must be provided"
        )

    # ナレッジ抽出
    try:
        service = KnowledgeService()
        result = service.extract_knowledge(
            text=text,
            book_title=book_title,
            language=request.language,
            include_entities=request.include_entities,
            include_relationships=request.include_relationships,
            min_confidence=request.min_confidence
        )

        structured_data = result["structured_data"]
        quality_score = result["quality_score"]
        language = result["language"]
        token_usage = result["token_usage"]
        processing_time = result["processing_time"]

        # フォーマット変換
        if request.format == OutputFormat.YAML:
            yaml_text = service.format_as_yaml(structured_data)
            json_text = None
            markdown_text = None
            content_blob = yaml_text.encode('utf-8')
        elif request.format == OutputFormat.JSON:
            yaml_text = service.format_as_json(structured_data)  # JSONをyaml_textに保存
            json_text = yaml_text
            markdown_text = None
            content_blob = yaml_text.encode('utf-8')
        elif request.format == OutputFormat.MARKDOWN:
            yaml_text = service.format_as_markdown(structured_data)
            json_text = None
            markdown_text = yaml_text
            content_blob = yaml_text.encode('utf-8')
        else:
            yaml_text = service.format_as_yaml(structured_data)
            json_text = None
            markdown_text = None
            content_blob = yaml_text.encode('utf-8')

        # DB保存
        knowledge = save_knowledge_to_db(
            db=db,
            user_id=current_user.id,
            book_title=book_title,
            format=request.format.value,
            yaml_text=yaml_text,
            content_blob=content_blob,
            score=quality_score
        )

        logger.info(
            f"Knowledge extraction completed: knowledge_id={knowledge.id}, "
            f"score={quality_score:.2f}, time={processing_time:.2f}s"
        )

        return KnowledgeExtractResponse(
            knowledge_id=knowledge.id,
            job_id=job_id,
            book_title=book_title,
            format=request.format,
            structured_data=structured_data,
            yaml_text=yaml_text if request.format == OutputFormat.YAML else None,
            json_text=json_text,
            markdown_text=markdown_text,
            quality_score=quality_score,
            language=language,
            token_usage=TokenUsage(**token_usage),
            processing_time=processing_time,
            is_mock=service.is_mock,
            created_at=knowledge.created_at
        )

    except Exception as e:
        logger.error(f"Knowledge extraction failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Knowledge extraction failed: {str(e)}"
        )


@router.get(
    "/{knowledge_id}",
    response_model=KnowledgeExtractResponse,
    summary="ナレッジ取得",
    description="IDでナレッジを取得します"
)
async def get_knowledge(
    knowledge_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """ナレッジ取得エンドポイント"""
    knowledge = get_knowledge_by_id(db, knowledge_id, current_user.id)

    if not knowledge:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Knowledge not found: {knowledge_id}"
        )

    try:
        # YAML/JSONからstructured_dataを復元
        import yaml
        import json

        if knowledge.format == "json":
            data_dict = json.loads(knowledge.yaml_text)
        else:
            data_dict = yaml.safe_load(knowledge.yaml_text)

        from app.schemas.knowledge import StructuredKnowledge
        structured_data = StructuredKnowledge(**data_dict)

        # フォーマット別のテキスト設定
        yaml_text = None
        json_text = None
        markdown_text = None

        if knowledge.format == "yaml":
            yaml_text = knowledge.yaml_text
        elif knowledge.format == "json":
            json_text = knowledge.yaml_text
        elif knowledge.format == "markdown":
            markdown_text = knowledge.yaml_text

        return KnowledgeExtractResponse(
            knowledge_id=knowledge.id,
            job_id=None,
            book_title=knowledge.book_title,
            format=OutputFormat(knowledge.format),
            structured_data=structured_data,
            yaml_text=yaml_text,
            json_text=json_text,
            markdown_text=markdown_text,
            quality_score=knowledge.score or 0.0,
            language="ja",  # デフォルト
            token_usage=TokenUsage(total=0, prompt=0, completion=0),
            processing_time=0.0,
            is_mock=False,
            created_at=knowledge.created_at
        )

    except Exception as e:
        logger.error(f"Failed to load knowledge: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to load knowledge: {str(e)}"
        )


@router.get(
    "/book/{book_title}",
    response_model=KnowledgeListResponse,
    summary="書籍別ナレッジ取得",
    description="書籍タイトルでナレッジを取得します"
)
async def get_knowledge_by_book(
    book_title: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """書籍別ナレッジ取得エンドポイント"""
    knowledge_list = get_knowledge_by_book_title(db, book_title, current_user.id)

    details = [
        KnowledgeDetail(
            id=k.id,
            book_title=k.book_title,
            format=k.format,
            score=k.score,
            created_at=k.created_at
        )
        for k in knowledge_list
    ]

    return KnowledgeListResponse(
        knowledge=details,
        total=len(details)
    )


@router.post(
    "/{knowledge_id}/export",
    summary="ナレッジエクスポート",
    description="ナレッジをファイル形式でエクスポートします"
)
async def export_knowledge(
    knowledge_id: int,
    request: KnowledgeExportRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """ナレッジエクスポートエンドポイント"""
    knowledge = get_knowledge_by_id(db, knowledge_id, current_user.id)

    if not knowledge:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Knowledge not found: {knowledge_id}"
        )

    try:
        # フォーマット変換
        service = KnowledgeService()

        # structured_dataを復元
        import yaml
        import json

        if knowledge.format == "json":
            data_dict = json.loads(knowledge.yaml_text)
        else:
            data_dict = yaml.safe_load(knowledge.yaml_text)

        from app.schemas.knowledge import StructuredKnowledge
        structured_data = StructuredKnowledge(**data_dict)

        # エクスポート形式に変換
        if request.format == ExportFormat.YAML:
            content = service.format_as_yaml(structured_data)
            extension = "yaml"
            media_type = "application/x-yaml"
        elif request.format == ExportFormat.JSON:
            content = service.format_as_json(structured_data)
            extension = "json"
            media_type = "application/json"
        elif request.format == ExportFormat.MARKDOWN:
            content = service.format_as_markdown(structured_data)
            extension = "md"
            media_type = "text/markdown"
        elif request.format == ExportFormat.CSV:
            # CSVは関係性のみ
            if structured_data.relationships:
                content = service.format_relationships_as_csv(
                    structured_data.relationships
                )
            else:
                content = "Subject,Predicate,Object,Confidence,Source Text\n"
            extension = "csv"
            media_type = "text/csv"
        else:
            content = knowledge.yaml_text
            extension = "txt"
            media_type = "text/plain"

        # メタデータ追加（オプション）
        if request.include_metadata:
            metadata = f"""---
Book Title: {knowledge.book_title}
Format: {knowledge.format}
Quality Score: {knowledge.score or 0.0}
Created At: {knowledge.created_at}
Knowledge ID: {knowledge.id}
---

"""
            content = metadata + content

        # ファイル名生成
        safe_title = "".join(
            c for c in knowledge.book_title if c.isalnum() or c in (' ', '-', '_')
        ).strip()[:50]
        filename = f"{safe_title}_knowledge.{extension}"

        # レスポンス
        return Response(
            content=content.encode('utf-8'),
            media_type=media_type,
            headers={
                "Content-Disposition": f'attachment; filename="{filename}"'
            }
        )

    except Exception as e:
        logger.error(f"Export failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Export failed: {str(e)}"
        )


# ========== Entity Extraction Endpoints (Phase 4-3) ==========

@router.post(
    "/extract-entities",
    response_model=EntityExtractResponse,
    summary="エンティティ抽出",
    description="テキストまたはOCRジョブからエンティティを抽出します（Phase 4-3）"
)
async def extract_entities(
    request: EntityExtractRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    エンティティ抽出エンドポイント（Phase 4-3）

    - 人物名、組織名、地名、専門用語などを抽出
    - Named Entity Recognition (NER) with Japanese support
    - 信頼度スコア付き
    """
    logger.info(f"Entity extraction request: min_confidence={request.min_confidence}")

    # テキスト取得
    if request.text:
        text = request.text
    elif request.job_id:
        text, _ = get_text_from_job(db, request.job_id, current_user.id)
        if text is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Job not found or no text available: {request.job_id}"
            )
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Either 'text' or 'job_id' must be provided"
        )

    # エンティティ抽出
    try:
        import time
        start_time = time.time()

        service = KnowledgeService()
        entities = service.extract_entities(
            text=text,
            language=request.language,
            entity_types=request.entity_types,
            min_confidence=request.min_confidence
        )

        processing_time = time.time() - start_time

        # タイプ別カウント
        by_type = {}
        for entity in entities:
            type_name = entity.type.value
            by_type[type_name] = by_type.get(type_name, 0) + 1

        # 言語検出
        language = request.language or service._detect_language(text)

        logger.info(
            f"Entity extraction completed: {len(entities)} entities, "
            f"time={processing_time:.2f}s"
        )

        return EntityExtractResponse(
            entities=entities,
            total_count=len(entities),
            by_type=by_type,
            language=language,
            processing_time=processing_time,
            is_mock=service.is_mock
        )

    except Exception as e:
        logger.error(f"Entity extraction failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Entity extraction failed: {str(e)}"
        )


# ========== Relationship Extraction Endpoints (Phase 4-4) ==========

@router.post(
    "/extract-relations",
    response_model=RelationshipExtractResponse,
    summary="関係性抽出",
    description="エンティティ間の関係性を抽出します（Phase 4-4）"
)
async def extract_relationships(
    request: RelationshipExtractRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    関係性抽出エンドポイント（Phase 4-4）

    - エンティティ間の関係（IS_A, CAUSES, PART_OF等）を抽出
    - ナレッジグラフ構築に使用可能
    - トリプレット形式（主語、述語、目的語）
    """
    logger.info(f"Relationship extraction request: min_confidence={request.min_confidence}")

    # テキスト取得
    if request.text:
        text = request.text
    elif request.job_id:
        text, _ = get_text_from_job(db, request.job_id, current_user.id)
        if text is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Job not found or no text available: {request.job_id}"
            )
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Either 'text' or 'job_id' must be provided"
        )

    # エンティティ取得（事前提供または抽出）
    if request.entities:
        entities = request.entities
    else:
        # エンティティを先に抽出
        service = KnowledgeService()
        entities = service.extract_entities(
            text=text,
            language=request.language,
            min_confidence=request.min_confidence
        )

    if not entities:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No entities found. Please provide entities or ensure text contains extractable entities."
        )

    # 関係性抽出
    try:
        import time
        start_time = time.time()

        service = KnowledgeService()
        relationships = service.extract_relationships(
            text=text,
            entities=entities,
            language=request.language,
            relation_types=request.relation_types,
            min_confidence=request.min_confidence
        )

        processing_time = time.time() - start_time

        # タイプ別カウント
        by_type = {}
        for rel in relationships:
            type_name = rel.predicate.value
            by_type[type_name] = by_type.get(type_name, 0) + 1

        logger.info(
            f"Relationship extraction completed: {len(relationships)} relationships, "
            f"time={processing_time:.2f}s"
        )

        return RelationshipExtractResponse(
            relationships=relationships,
            total_count=len(relationships),
            by_type=by_type,
            processing_time=processing_time,
            is_mock=service.is_mock
        )

    except Exception as e:
        logger.error(f"Relationship extraction failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Relationship extraction failed: {str(e)}"
        )


@router.post(
    "/build-graph",
    response_model=KnowledgeGraph,
    summary="ナレッジグラフ構築",
    description="エンティティと関係性からナレッジグラフを構築します（Phase 4-4）"
)
async def build_knowledge_graph(
    request: RelationshipExtractRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    ナレッジグラフ構築エンドポイント（Phase 4-4）

    - エンティティをノード、関係性をエッジとするグラフを生成
    - 可視化やグラフデータベースへの保存に使用可能
    """
    logger.info("Building knowledge graph")

    # テキスト取得
    if request.text:
        text = request.text
        book_title = "Untitled"
    elif request.job_id:
        text, book_title = get_text_from_job(db, request.job_id, current_user.id)
        if text is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Job not found or no text available: {request.job_id}"
            )
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Either 'text' or 'job_id' must be provided"
        )

    try:
        service = KnowledgeService()

        # エンティティと関係性抽出
        if request.entities:
            entities = request.entities
        else:
            entities = service.extract_entities(
                text=text,
                language=request.language,
                min_confidence=request.min_confidence
            )

        relationships = service.extract_relationships(
            text=text,
            entities=entities,
            language=request.language,
            relation_types=request.relation_types,
            min_confidence=request.min_confidence
        )

        # ナレッジグラフ構築
        graph = service.build_knowledge_graph(
            entities=entities,
            relationships=relationships,
            book_title=book_title
        )

        logger.info(
            f"Knowledge graph built: {len(graph.nodes)} nodes, "
            f"{len(graph.edges)} edges"
        )

        return graph

    except Exception as e:
        logger.error(f"Knowledge graph building failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Knowledge graph building failed: {str(e)}"
        )


# ========== Health Check ==========

@router.get(
    "/health",
    summary="ヘルスチェック",
    description="Knowledge APIのヘルスチェック"
)
async def health_check():
    """ヘルスチェックエンドポイント"""
    return {
        "status": "healthy",
        "service": "knowledge",
        "version": "1.0.0",
        "features": [
            "knowledge_extraction",
            "entity_extraction",
            "relationship_extraction",
            "knowledge_graph"
        ]
    }
