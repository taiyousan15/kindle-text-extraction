"""
Schemas Package

Pydantic schemas for request/response validation
"""
from app.schemas.ocr import OCRUploadResponse, JobResponse
from app.schemas.capture import (
    CaptureStartRequest,
    CaptureStartResponse,
    CaptureStatusResponse,
    OCRResultSummary
)
from app.schemas.business import (
    DocumentUploadResponse,
    BusinessQueryRequest,
    BusinessQueryResponse,
    DocumentListResponse,
    DocumentDeleteResponse,
    DocumentReindexResponse,
)
from app.schemas.feedback import (
    FeedbackSubmitRequest,
    FeedbackSubmitResponse,
    FeedbackStats,
    RetrainingTriggerResponse,
    FeedbackListResponse,
)
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
    Entity,
    EntityType,
    # Relationship Extraction
    RelationshipExtractRequest,
    RelationshipExtractResponse,
    Relationship,
    RelationType,
    # Knowledge Graph
    KnowledgeGraph,
    KnowledgeGraphNode,
    KnowledgeGraphEdge,
    # Structured Knowledge
    StructuredKnowledge,
    Concept,
    Fact,
    Process,
    Insight,
    ActionItem,
    # Enums
    OutputFormat,
    ExportFormat,
    ImportanceLevel,
    # Common
    TokenUsage,
    ErrorResponse,
)

__all__ = [
    # OCR
    "OCRUploadResponse",
    "JobResponse",
    # Capture
    "CaptureStartRequest",
    "CaptureStartResponse",
    "CaptureStatusResponse",
    "OCRResultSummary",
    # Business RAG
    "DocumentUploadResponse",
    "BusinessQueryRequest",
    "BusinessQueryResponse",
    "DocumentListResponse",
    "DocumentDeleteResponse",
    "DocumentReindexResponse",
    # Feedback
    "FeedbackSubmitRequest",
    "FeedbackSubmitResponse",
    "FeedbackStats",
    "RetrainingTriggerResponse",
    "FeedbackListResponse",
    # Knowledge Extraction
    "KnowledgeExtractRequest",
    "KnowledgeExtractResponse",
    "KnowledgeDetail",
    "KnowledgeListResponse",
    "KnowledgeExportRequest",
    "KnowledgeExportResponse",
    # Entity Extraction
    "EntityExtractRequest",
    "EntityExtractResponse",
    "Entity",
    "EntityType",
    # Relationship Extraction
    "RelationshipExtractRequest",
    "RelationshipExtractResponse",
    "Relationship",
    "RelationType",
    # Knowledge Graph
    "KnowledgeGraph",
    "KnowledgeGraphNode",
    "KnowledgeGraphEdge",
    # Structured Knowledge
    "StructuredKnowledge",
    "Concept",
    "Fact",
    "Process",
    "Insight",
    "ActionItem",
    # Enums
    "OutputFormat",
    "ExportFormat",
    "ImportanceLevel",
    # Common
    "TokenUsage",
    "ErrorResponse",
]
