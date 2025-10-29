"""
Feedback Schemas

Pydantic schemas for feedback collection and learning
"""
from pydantic import BaseModel, Field, validator
from typing import Optional, Dict, Any, List
from datetime import datetime


# ========================================
# Feedback Submission
# ========================================

class FeedbackSubmitRequest(BaseModel):
    """Request to submit feedback"""
    query: str = Field(..., min_length=1, max_length=5000, description="User query")
    answer: str = Field(..., min_length=1, max_length=10000, description="System answer")
    rating: int = Field(..., ge=1, le=5, description="Rating (1-5 stars)")
    user_id: Optional[int] = Field(default=None, description="Optional user ID")
    metadata: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Additional metadata (e.g., response time, model used)"
    )

    @validator('rating')
    def validate_rating(cls, v):
        if v < 1 or v > 5:
            raise ValueError("Rating must be between 1 and 5")
        return v


class FeedbackSubmitResponse(BaseModel):
    """Response for feedback submission"""
    feedback_id: int = Field(..., description="Created feedback ID")
    status: str = Field(..., description="Submission status")
    message: str = Field(..., description="Status message")
    queued_for_retraining: bool = Field(
        default=False,
        description="Whether feedback was queued for retraining"
    )
    created_at: str = Field(..., description="Creation timestamp (ISO 8601)")


# ========================================
# Feedback Statistics
# ========================================

class FeedbackStats(BaseModel):
    """Feedback statistics"""
    total_feedbacks: int = Field(..., description="Total number of feedbacks")
    average_rating: float = Field(..., description="Average rating (1-5)")
    rating_distribution: Dict[int, int] = Field(
        ...,
        description="Distribution of ratings {1: count, 2: count, ...}"
    )
    positive_count: int = Field(..., description="Count of positive feedbacks (4-5 stars)")
    negative_count: int = Field(..., description="Count of negative feedbacks (1-2 stars)")
    neutral_count: int = Field(..., description="Count of neutral feedbacks (3 stars)")
    recent_feedbacks: int = Field(..., description="Feedbacks in last 24 hours")
    timestamp: str = Field(..., description="Stats generation timestamp (ISO 8601)")


class FeedbackStatsRequest(BaseModel):
    """Request for feedback statistics"""
    user_id: Optional[int] = Field(default=None, description="Filter by user ID")
    days: int = Field(default=30, ge=1, le=365, description="Period in days")


# ========================================
# Retraining
# ========================================

class RetrainingTriggerRequest(BaseModel):
    """Request to trigger retraining"""
    card_ids: Optional[List[int]] = Field(
        default=None,
        description="Specific card IDs to retrain (if None, uses feedback data)"
    )
    force: bool = Field(
        default=False,
        description="Force immediate retraining (bypass scheduling)"
    )
    batch_size: int = Field(
        default=100,
        ge=1,
        le=1000,
        description="Batch size for processing"
    )


class RetrainingTriggerResponse(BaseModel):
    """Response for retraining trigger"""
    status: str = Field(..., description="Trigger status")
    message: str = Field(..., description="Status message")
    queued_items: int = Field(..., description="Number of items queued")
    task_id: Optional[str] = Field(default=None, description="Celery task ID (if async)")
    timestamp: str = Field(..., description="Trigger timestamp (ISO 8601)")


# ========================================
# Feedback History
# ========================================

class FeedbackItem(BaseModel):
    """Single feedback item"""
    feedback_id: int = Field(..., description="Feedback ID")
    query: str = Field(..., description="User query")
    answer: str = Field(..., description="System answer")
    rating: int = Field(..., description="Rating (1-5)")
    user_id: Optional[int] = Field(default=None, description="User ID")
    created_at: str = Field(..., description="Creation timestamp (ISO 8601)")


class FeedbackListRequest(BaseModel):
    """Request for feedback list"""
    user_id: Optional[int] = Field(default=None, description="Filter by user ID")
    rating: Optional[int] = Field(default=None, ge=1, le=5, description="Filter by rating")
    limit: int = Field(default=100, ge=1, le=1000, description="Max results")
    offset: int = Field(default=0, ge=0, description="Pagination offset")


class FeedbackListResponse(BaseModel):
    """Response for feedback list"""
    total: int = Field(..., description="Total feedback count")
    count: int = Field(..., description="Returned feedback count")
    limit: int = Field(..., description="Limit parameter")
    offset: int = Field(..., description="Offset parameter")
    feedbacks: List[FeedbackItem] = Field(..., description="Feedback list")


# ========================================
# Learning Insights
# ========================================

class LearningInsight(BaseModel):
    """Learning insight from feedback data"""
    insight_type: str = Field(..., description="Type of insight")
    description: str = Field(..., description="Insight description")
    data: Dict[str, Any] = Field(..., description="Supporting data")
    priority: str = Field(..., description="Priority (high/medium/low)")


class LearningInsightsResponse(BaseModel):
    """Response for learning insights"""
    total_insights: int = Field(..., description="Number of insights generated")
    insights: List[LearningInsight] = Field(..., description="List of insights")
    recommendations: List[str] = Field(..., description="Actionable recommendations")
    timestamp: str = Field(..., description="Generation timestamp (ISO 8601)")


# ========================================
# Error Response
# ========================================

class FeedbackErrorResponse(BaseModel):
    """Error response for feedback operations"""
    error: str = Field(..., description="Error type")
    message: str = Field(..., description="Error message")
    details: Optional[dict] = Field(default=None, description="Additional details")
