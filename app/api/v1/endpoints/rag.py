"""
RAG API Endpoints

RAG（Retrieval Augmented Generation）機能のエンドポイント
+ Rate Limiting (Phase 1-8)
"""
import logging
import time
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form, Request
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import get_current_user_or_default
from app.models.user import User
from app.schemas.rag import (
    RAGQueryRequest,
    RAGQueryResponse,
    RAGIndexRequest,
    RAGIndexResponse,
    RAGSearchRequest,
    RAGSearchResponse,
    VectorStoreStats,
    RetrievedDocument,
    TokenUsage
)
from app.services.llm_service import get_llm_service
from app.services.embedding_service import get_embedding_service
from app.services.vector_store import VectorStore
from app.models.biz_file import BizFile
from app.services.rate_limiter import limiter, RateLimitConfig

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/rag", tags=["RAG"])


# ==================== RAG Query ====================

@router.post("/query", response_model=RAGQueryResponse)
@limiter.limit(RateLimitConfig.RAG_QUERY)
def rag_query(
    http_request: Request,
    request: RAGQueryRequest,
    current_user: User = Depends(get_current_user_or_default),
    db: Session = Depends(get_db)
):
    """
    RAGクエリエンドポイント

    ベクトル検索 → LLM生成
    """
    start_time = time.time()

    try:
        logger.info(f"RAG query received: {request.query[:50]}...")

        # ベクトルストア初期化
        vector_store = VectorStore(db)

        # 類似ドキュメント検索
        logger.debug(f"Searching for top {request.top_k} similar documents...")
        search_results = vector_store.similarity_search(
            query=request.query,
            k=request.top_k,
            score_threshold=request.score_threshold,
            file_ids=request.file_ids
        )

        if not search_results:
            logger.warning("No documents found for query")
            return RAGQueryResponse(
                answer="申し訳ございません。該当するドキュメントが見つかりませんでした。",
                sources=[],
                query=request.query,
                tokens=None,
                model="none",
                is_mock=True,
                processing_time=time.time() - start_time
            )

        # RetrievedDocument形式に変換
        sources = [
            RetrievedDocument(
                id=result["id"],
                content=result["content"],
                score=result["score"],
                similarity=result["similarity"],
                file_id=result["file_id"],
                filename=result["filename"]
            )
            for result in search_results
        ]

        # LLMサービス初期化
        llm_service = get_llm_service(provider=request.provider)

        # RAG生成
        logger.debug("Generating answer with LLM...")
        context_documents = [doc.content for doc in sources]

        llm_result = llm_service.generate_with_context(
            query=request.query,
            context_documents=context_documents,
            system_prompt=request.system_prompt
        )

        # トークン使用量
        tokens = None
        if not llm_result["is_mock"]:
            tokens = TokenUsage(
                total=llm_result["tokens"]["total"],
                prompt=llm_result["tokens"]["prompt"],
                completion=llm_result["tokens"]["completion"]
            )

        processing_time = time.time() - start_time

        logger.info(
            f"RAG query completed. "
            f"Sources: {len(sources)}, "
            f"Processing time: {processing_time:.2f}s"
        )

        return RAGQueryResponse(
            answer=llm_result["content"],
            sources=sources,
            query=request.query,
            tokens=tokens,
            model=llm_result["model"],
            is_mock=llm_result["is_mock"],
            processing_time=processing_time
        )

    except Exception as e:
        logger.error(f"RAG query failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"RAG query failed: {str(e)}"
        )


# ==================== RAG Index ====================

@router.post("/index", response_model=RAGIndexResponse)
def rag_index(
    request: RAGIndexRequest,
    current_user: User = Depends(get_current_user_or_default),
    db: Session = Depends(get_db)
):
    """
    ドキュメントインデックス化エンドポイント

    テキスト抽出 → Embedding生成 → ベクトルストア保存
    """
    start_time = time.time()

    try:
        logger.info(f"Indexing request received: file_id={request.file_id}")

        # ファイル取得またはコンテンツ直接指定
        if request.file_id:
            # 既存ファイルからインデックス化 (ユーザーフィルタリング)
            biz_file = db.query(BizFile).filter(
                BizFile.id == request.file_id,
                BizFile.user_id == current_user.id
            ).first()
            if not biz_file:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"File not found: id={request.file_id}"
                )

            # ファイルからテキスト抽出（簡易版 - 実際はPDF/DOCX等の処理が必要）
            if request.content:
                content = request.content
            else:
                # BizFile.file_blobからテキスト抽出（TODO: 実装）
                content = biz_file.file_blob.decode("utf-8", errors="ignore")

            file_id = request.file_id
            filename = biz_file.filename

        elif request.content and request.filename:
            # 新規ファイル作成
            biz_file = BizFile(
                filename=request.filename,
                user_id=current_user.id,
                tags=request.tags,
                file_blob=request.content.encode("utf-8"),
                file_size=len(request.content),
                mime_type="text/plain"
            )
            db.add(biz_file)
            db.commit()
            db.refresh(biz_file)

            file_id = biz_file.id
            filename = biz_file.filename
            content = request.content

        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Either file_id or (content + filename) must be provided"
            )

        # チャンキング（簡易版）
        chunks = _chunk_text(
            text=content,
            chunk_size=request.chunk_size,
            overlap=request.chunk_overlap
        )

        logger.info(f"Text chunked into {len(chunks)} chunks")

        # ベクトルストアに追加
        vector_store = VectorStore(db)
        biz_cards = vector_store.add_documents(
            documents=chunks,
            file_id=file_id
        )

        processing_time = time.time() - start_time

        logger.info(
            f"Indexing completed. "
            f"Indexed: {len(biz_cards)} documents, "
            f"Processing time: {processing_time:.2f}s"
        )

        return RAGIndexResponse(
            file_id=file_id,
            filename=filename,
            indexed_count=len(biz_cards),
            total_characters=len(content),
            processing_time=processing_time,
            status="success",
            message=f"Successfully indexed {len(biz_cards)} documents"
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Indexing failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Indexing failed: {str(e)}"
        )


@router.post("/index/upload", response_model=RAGIndexResponse)
async def rag_index_upload(
    file: UploadFile = File(...),
    tags: str = Form(default=""),
    chunk_size: int = Form(default=500),
    chunk_overlap: int = Form(default=50),
    current_user: User = Depends(get_current_user_or_default),
    db: Session = Depends(get_db)
):
    """
    ファイルアップロード + インデックス化エンドポイント

    ファイルアップロード → テキスト抽出 → Embedding生成 → 保存
    """
    start_time = time.time()

    try:
        logger.info(f"File upload received: {file.filename}")

        # ファイル読み込み
        file_content = await file.read()

        # BizFile作成
        tags_list = [tag.strip() for tag in tags.split(",") if tag.strip()]

        biz_file = BizFile(
            filename=file.filename,
            user_id=current_user.id,
            tags=tags_list if tags_list else None,
            file_blob=file_content,
            file_size=len(file_content),
            mime_type=file.content_type
        )
        db.add(biz_file)
        db.commit()
        db.refresh(biz_file)

        # テキスト抽出（簡易版）
        try:
            content = file_content.decode("utf-8", errors="ignore")
        except Exception as e:
            logger.warning(f"Failed to decode as UTF-8: {e}")
            content = str(file_content)

        # チャンキング
        chunks = _chunk_text(
            text=content,
            chunk_size=chunk_size,
            overlap=chunk_overlap
        )

        # ベクトルストアに追加
        vector_store = VectorStore(db)
        biz_cards = vector_store.add_documents(
            documents=chunks,
            file_id=biz_file.id
        )

        processing_time = time.time() - start_time

        logger.info(
            f"Upload and indexing completed. "
            f"File: {file.filename}, "
            f"Indexed: {len(biz_cards)} documents"
        )

        return RAGIndexResponse(
            file_id=biz_file.id,
            filename=biz_file.filename,
            indexed_count=len(biz_cards),
            total_characters=len(content),
            processing_time=processing_time,
            status="success",
            message=f"Successfully uploaded and indexed {len(biz_cards)} documents"
        )

    except Exception as e:
        logger.error(f"Upload and indexing failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Upload and indexing failed: {str(e)}"
        )


# ==================== RAG Search ====================

@router.post("/search", response_model=RAGSearchResponse)
def rag_search(
    request: RAGSearchRequest,
    current_user: User = Depends(get_current_user_or_default),
    db: Session = Depends(get_db)
):
    """
    RAG検索エンドポイント（LLM不使用）

    ベクトル類似度検索のみ
    """
    start_time = time.time()

    try:
        logger.info(f"Search request received: {request.query[:50]}...")

        # ベクトルストア初期化
        vector_store = VectorStore(db)

        # 類似ドキュメント検索
        search_results = vector_store.similarity_search(
            query=request.query,
            k=request.top_k,
            score_threshold=request.score_threshold,
            file_ids=request.file_ids
        )

        # RetrievedDocument形式に変換
        results = [
            RetrievedDocument(
                id=result["id"],
                content=result["content"],
                score=result["score"],
                similarity=result["similarity"],
                file_id=result["file_id"],
                filename=result["filename"]
            )
            for result in search_results
        ]

        processing_time = time.time() - start_time

        logger.info(
            f"Search completed. "
            f"Results: {len(results)}, "
            f"Processing time: {processing_time:.2f}s"
        )

        return RAGSearchResponse(
            query=request.query,
            results=results,
            total_count=len(results),
            processing_time=processing_time
        )

    except Exception as e:
        logger.error(f"Search failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Search failed: {str(e)}"
        )


# ==================== Statistics ====================

@router.get("/stats", response_model=VectorStoreStats)
def get_vector_store_stats(
    current_user: User = Depends(get_current_user_or_default),
    db: Session = Depends(get_db)
):
    """
    ベクトルストア統計取得エンドポイント
    """
    try:
        vector_store = VectorStore(db)
        stats = vector_store.get_statistics()

        return VectorStoreStats(
            total_documents=stats["total_documents"],
            total_files=stats["total_files"],
            documents_with_embeddings=stats["documents_with_embeddings"],
            avg_embedding_dim=stats["avg_embedding_dim"],
            embedding_coverage=stats["embedding_coverage"]
        )

    except Exception as e:
        logger.error(f"Failed to get statistics: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get statistics: {str(e)}"
        )


# ==================== Helper Functions ====================

def _chunk_text(text: str, chunk_size: int = 500, overlap: int = 50) -> List[str]:
    """
    テキストをチャンクに分割

    Args:
        text: 入力テキスト
        chunk_size: チャンクサイズ（文字数）
        overlap: 重複サイズ（文字数）

    Returns:
        チャンクリスト
    """
    if not text:
        return []

    chunks = []
    start = 0

    while start < len(text):
        end = start + chunk_size
        chunk = text[start:end]

        # 空白で区切られた完全な単語にする（可能な場合）
        if end < len(text):
            last_space = chunk.rfind(" ")
            if last_space > chunk_size // 2:  # チャンクの半分以上なら調整
                chunk = chunk[:last_space]
                end = start + last_space

        chunks.append(chunk.strip())
        start = end - overlap

    logger.debug(f"Text chunked: {len(chunks)} chunks, avg size: {len(text) / len(chunks):.0f}")

    return chunks
