"""
Business RAG Schemas

Pydantic schemas for business document management
"""
from pydantic import BaseModel, Field, validator
from typing import List, Optional
from datetime import datetime


# ========================================
# Upload Schemas
# ========================================

class DocumentUploadResponse(BaseModel):
    """Response for document upload"""
    file_id: int = Field(..., description="Uploaded file ID")
    filename: str = Field(..., description="Original filename")
    file_size: int = Field(..., description="File size in bytes")
    mime_type: str = Field(..., description="MIME type")
    chunks_created: int = Field(..., description="Number of chunks created")
    status: str = Field(..., description="Upload status")
    uploaded_at: str = Field(..., description="Upload timestamp (ISO 8601)")


# ========================================
# Query Schemas
# ========================================

class BusinessQueryRequest(BaseModel):
    """Request for business knowledge base query"""
    query: str = Field(..., min_length=1, max_length=1000, description="Search query")
    top_k: int = Field(default=5, ge=1, le=20, description="Number of results")
    file_ids: Optional[List[int]] = Field(default=None, description="Filter by file IDs")
    tags: Optional[List[str]] = Field(default=None, description="Filter by tags")
    similarity_threshold: float = Field(
        default=0.5,
        ge=0.0,
        le=1.0,
        description="Minimum similarity score"
    )

    @validator('query')
    def query_not_empty(cls, v):
        if not v.strip():
            raise ValueError("Query cannot be empty")
        return v.strip()


class BusinessQueryResult(BaseModel):
    """Single query result"""
    card_id: int = Field(..., description="BizCard ID")
    content: str = Field(..., description="Chunk content")
    file_id: int = Field(..., description="Source file ID")
    filename: str = Field(..., description="Source filename")
    tags: List[str] = Field(default_factory=list, description="Document tags")
    similarity: float = Field(..., description="Similarity score (0-1)")
    indexed_at: str = Field(..., description="Index timestamp (ISO 8601)")


class BusinessQueryResponse(BaseModel):
    """Response for business query"""
    query: str = Field(..., description="Original query")
    results_count: int = Field(..., description="Number of results returned")
    results: List[BusinessQueryResult] = Field(..., description="Query results")
    context: str = Field(..., description="Combined context for LLM")
    timestamp: str = Field(..., description="Query timestamp (ISO 8601)")


# ========================================
# Document List Schemas
# ========================================

class DocumentInfo(BaseModel):
    """Document information"""
    file_id: int = Field(..., description="File ID")
    filename: str = Field(..., description="Filename")
    file_size: int = Field(..., description="File size in bytes")
    mime_type: str = Field(..., description="MIME type")
    tags: List[str] = Field(default_factory=list, description="Document tags")
    chunk_count: int = Field(..., description="Number of chunks")
    uploaded_at: str = Field(..., description="Upload timestamp (ISO 8601)")


class DocumentListRequest(BaseModel):
    """Request for document list"""
    tags: Optional[List[str]] = Field(default=None, description="Filter by tags")
    limit: int = Field(default=100, ge=1, le=1000, description="Max results")
    offset: int = Field(default=0, ge=0, description="Pagination offset")


class DocumentListResponse(BaseModel):
    """Response for document list"""
    total: int = Field(..., description="Total document count")
    count: int = Field(..., description="Returned document count")
    limit: int = Field(..., description="Limit parameter")
    offset: int = Field(..., description="Offset parameter")
    documents: List[DocumentInfo] = Field(..., description="Document list")


# ========================================
# Document Operations
# ========================================

class DocumentDeleteResponse(BaseModel):
    """Response for document deletion"""
    file_id: int = Field(..., description="Deleted file ID")
    status: str = Field(..., description="Deletion status")
    message: str = Field(..., description="Status message")


class DocumentReindexResponse(BaseModel):
    """Response for document reindexing"""
    file_id: int = Field(..., description="Reindexed file ID")
    filename: str = Field(..., description="Filename")
    deleted_chunks: int = Field(..., description="Number of chunks deleted")
    created_chunks: int = Field(..., description="Number of chunks created")
    status: str = Field(..., description="Reindex status")
    timestamp: str = Field(..., description="Reindex timestamp (ISO 8601)")


class DocumentStatsResponse(BaseModel):
    """Response for document statistics"""
    file_id: int = Field(..., description="File ID")
    filename: str = Field(..., description="Filename")
    file_size: int = Field(..., description="File size in bytes")
    mime_type: str = Field(..., description="MIME type")
    tags: List[str] = Field(default_factory=list, description="Document tags")
    chunk_count: int = Field(..., description="Number of chunks")
    average_score: float = Field(..., description="Average chunk score")
    uploaded_at: str = Field(..., description="Upload timestamp (ISO 8601)")


# ========================================
# Error Response
# ========================================

class BusinessErrorResponse(BaseModel):
    """Error response"""
    error: str = Field(..., description="Error type")
    message: str = Field(..., description="Error message")
    details: Optional[dict] = Field(default=None, description="Additional details")
