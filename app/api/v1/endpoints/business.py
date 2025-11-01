"""
Business RAG API Endpoints

API endpoints for business document management and querying
"""
import logging
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import get_current_user_or_default
from app.models.user import User
from app.services.business_rag_service import get_business_rag_service, BusinessRAGService
from app.schemas.business import (
    DocumentUploadResponse,
    BusinessQueryRequest,
    BusinessQueryResponse,
    DocumentListRequest,
    DocumentListResponse,
    DocumentDeleteResponse,
    DocumentReindexResponse,
    DocumentStatsResponse,
    BusinessErrorResponse
)

logger = logging.getLogger(__name__)

router = APIRouter()


def get_rag_service(db: Session = Depends(get_db)) -> BusinessRAGService:
    """Dependency for BusinessRAGService"""
    return get_business_rag_service(db=db, mock_mode=False)


# ========================================
# Upload Endpoint
# ========================================

@router.post(
    "/upload",
    response_model=DocumentUploadResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Upload business document",
    description="Upload and index a business document (PDF, DOCX, or TXT)"
)
async def upload_document(
    file: UploadFile = File(..., description="Document file to upload"),
    tags: Optional[str] = Form(None, description="Comma-separated tags"),
    auto_index: bool = Form(True, description="Automatically create vector index"),
    current_user: User = Depends(get_current_user_or_default),
    rag_service: BusinessRAGService = Depends(get_rag_service)
):
    """
    Upload and process business document

    Supports:
    - PDF (.pdf)
    - Word (.docx)
    - Plain text (.txt)

    The document is automatically:
    1. Stored in the database
    2. Text extracted
    3. Chunked into smaller pieces
    4. Vectorized with embeddings
    5. Indexed for semantic search
    """
    try:
        # Validate file type
        if not file.content_type:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Could not determine file type"
            )

        # Read file content
        content = await file.read()

        if not content:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Empty file uploaded"
            )

        # Parse tags
        tag_list = []
        if tags:
            tag_list = [t.strip() for t in tags.split(",") if t.strip()]

        logger.info(
            f"Uploading document: {file.filename} "
            f"(type: {file.content_type}, size: {len(content)} bytes)"
        )

        # Upload document
        result = rag_service.upload_document(
            filename=file.filename,
            file_content=content,
            mime_type=file.content_type,
            tags=tag_list,
            auto_index=auto_index,
            user_id=current_user.id
        )

        logger.info(
            f"Document uploaded successfully: {file.filename} "
            f"(ID: {result['file_id']}, chunks: {result['chunks_created']})"
        )

        return DocumentUploadResponse(**result)

    except ValueError as e:
        logger.error(f"Validation error: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Upload failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to upload document: {str(e)}"
        )


# ========================================
# Query Endpoint
# ========================================

@router.post(
    "/query",
    response_model=BusinessQueryResponse,
    summary="Query business knowledge base",
    description="Search business documents using semantic similarity"
)
async def query_business_kb(
    request: BusinessQueryRequest,
    current_user: User = Depends(get_current_user_or_default),
    rag_service: BusinessRAGService = Depends(get_rag_service)
):
    """
    Query the business knowledge base

    Uses semantic search to find relevant document chunks based on the query.
    Returns the most similar chunks along with metadata and a combined context.

    The context can be used directly with LLMs for question answering.
    """
    try:
        logger.info(f"Business query: '{request.query[:50]}...'")

        result = rag_service.query_documents(
            query=request.query,
            top_k=request.top_k,
            file_ids=request.file_ids,
            tags=request.tags,
            similarity_threshold=request.similarity_threshold,
            user_id=current_user.id
        )

        logger.info(
            f"Query completed: {result['results_count']} results returned"
        )

        return BusinessQueryResponse(**result)

    except ValueError as e:
        logger.error(f"Validation error: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Query failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Query failed: {str(e)}"
        )


# ========================================
# List Documents Endpoint
# ========================================

@router.get(
    "/documents",
    response_model=DocumentListResponse,
    summary="List documents",
    description="List all business documents with filtering and pagination"
)
async def list_documents(
    tags: Optional[str] = None,
    limit: int = 100,
    offset: int = 0,
    current_user: User = Depends(get_current_user_or_default),
    rag_service: BusinessRAGService = Depends(get_rag_service)
):
    """
    List business documents

    Supports:
    - Filtering by tags
    - Pagination with limit/offset
    - Returns document metadata and chunk counts
    """
    try:
        # Parse tags
        tag_list = None
        if tags:
            tag_list = [t.strip() for t in tags.split(",") if t.strip()]

        result = rag_service.list_documents(
            tags=tag_list,
            limit=limit,
            offset=offset,
            user_id=current_user.id
        )

        logger.info(
            f"Listed {result['count']}/{result['total']} documents "
            f"(limit: {limit}, offset: {offset})"
        )

        return DocumentListResponse(**result)

    except Exception as e:
        logger.error(f"List failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list documents: {str(e)}"
        )


# ========================================
# Delete Document Endpoint
# ========================================

@router.delete(
    "/documents/{file_id}",
    response_model=DocumentDeleteResponse,
    summary="Delete document",
    description="Delete a business document and all associated chunks"
)
async def delete_document(
    file_id: int,
    current_user: User = Depends(get_current_user_or_default),
    rag_service: BusinessRAGService = Depends(get_rag_service)
):
    """
    Delete business document

    Deletes:
    - Document file from database
    - All associated text chunks
    - All associated embeddings

    This operation is irreversible.
    """
    try:
        success = rag_service.delete_document(file_id=file_id, user_id=current_user.id)

        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Document {file_id} not found"
            )

        logger.info(f"Document {file_id} deleted successfully")

        return DocumentDeleteResponse(
            file_id=file_id,
            status="deleted",
            message=f"Document {file_id} deleted successfully"
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Delete failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete document: {str(e)}"
        )


# ========================================
# Reindex Document Endpoint
# ========================================

@router.post(
    "/reindex/{file_id}",
    response_model=DocumentReindexResponse,
    summary="Reindex document",
    description="Recreate embeddings for a document"
)
async def reindex_document(
    file_id: int,
    current_user: User = Depends(get_current_user_or_default),
    rag_service: BusinessRAGService = Depends(get_rag_service)
):
    """
    Reindex business document

    Useful when:
    - Embedding model is updated
    - Chunking strategy changes
    - Document needs to be re-processed

    Process:
    1. Delete existing chunks
    2. Re-extract text
    3. Re-chunk text
    4. Generate new embeddings
    5. Store new chunks
    """
    try:
        result = rag_service.reindex_document(file_id=file_id, user_id=current_user.id)

        logger.info(
            f"Document {file_id} reindexed: "
            f"{result['deleted_chunks']} deleted, {result['created_chunks']} created"
        )

        return DocumentReindexResponse(**result)

    except ValueError as e:
        logger.error(f"Validation error: {e}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Reindex failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to reindex document: {str(e)}"
        )


# ========================================
# Document Stats Endpoint
# ========================================

@router.get(
    "/documents/{file_id}/stats",
    response_model=DocumentStatsResponse,
    summary="Get document statistics",
    description="Get detailed statistics for a business document"
)
async def get_document_stats(
    file_id: int,
    current_user: User = Depends(get_current_user_or_default),
    rag_service: BusinessRAGService = Depends(get_rag_service)
):
    """
    Get document statistics

    Returns:
    - Document metadata
    - Chunk count
    - Average quality score
    - Upload information
    """
    try:
        result = rag_service.get_document_stats(file_id=file_id, user_id=current_user.id)

        return DocumentStatsResponse(**result)

    except ValueError as e:
        logger.error(f"Validation error: {e}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Stats failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get document stats: {str(e)}"
        )


# ========================================
# Health Check
# ========================================

@router.get(
    "/health",
    summary="Business RAG health check",
    description="Check if Business RAG service is operational"
)
async def health_check(rag_service: BusinessRAGService = Depends(get_rag_service)):
    """Business RAG service health check"""
    return {
        "status": "healthy",
        "service": "business_rag",
        "mock_mode": rag_service.mock_mode
    }
