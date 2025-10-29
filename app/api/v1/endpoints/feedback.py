"""
Feedback API Endpoints

API endpoints for feedback collection and learning system
"""
import logging
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import get_current_active_user
from app.models.user import User
from app.services.feedback_service import get_feedback_service, FeedbackService
from app.schemas.feedback import (
    FeedbackSubmitRequest,
    FeedbackSubmitResponse,
    FeedbackStatsRequest,
    FeedbackStats,
    RetrainingTriggerRequest,
    RetrainingTriggerResponse,
    FeedbackListRequest,
    FeedbackListResponse,
    LearningInsightsResponse,
    FeedbackErrorResponse
)

logger = logging.getLogger(__name__)

router = APIRouter()


def get_service(db: Session = Depends(get_db)) -> FeedbackService:
    """Dependency for FeedbackService"""
    return get_feedback_service(db=db)


# ========================================
# Submit Feedback
# ========================================

@router.post(
    "/submit",
    response_model=FeedbackSubmitResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Submit feedback",
    description="Submit user feedback for a query/answer pair"
)
async def submit_feedback(
    request: FeedbackSubmitRequest,
    current_user: User = Depends(get_current_active_user),
    service: FeedbackService = Depends(get_service)
):
    """
    Submit user feedback

    Accepts a query, answer, and rating (1-5 stars).
    Negative feedback (1-2 stars) is automatically queued for retraining.

    Use this to:
    - Collect user satisfaction data
    - Identify problematic responses
    - Improve model performance over time
    """
    try:
        logger.info(
            f"Submitting feedback: rating {request.rating}, "
            f"user_id {current_user.id}"
        )

        result = service.submit_feedback(
            query=request.query,
            answer=request.answer,
            rating=request.rating,
            user_id=current_user.id,
            metadata=request.metadata
        )

        logger.info(
            f"Feedback submitted: ID {result['feedback_id']}, "
            f"queued_for_retraining: {result['queued_for_retraining']}"
        )

        return FeedbackSubmitResponse(**result)

    except ValueError as e:
        logger.error(f"Validation error: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Feedback submission failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to submit feedback: {str(e)}"
        )


# ========================================
# Get Statistics
# ========================================

@router.get(
    "/stats",
    response_model=FeedbackStats,
    summary="Get feedback statistics",
    description="Get aggregated feedback statistics and trends"
)
async def get_feedback_stats(
    days: int = 30,
    current_user: User = Depends(get_current_active_user),
    service: FeedbackService = Depends(get_service)
):
    """
    Get feedback statistics

    Returns:
    - Total feedback count
    - Average rating
    - Rating distribution
    - Positive/negative/neutral counts
    - Recent activity (24h)

    Useful for:
    - Monitoring user satisfaction
    - Identifying trends
    - Dashboard visualizations
    """
    try:
        logger.info(f"Getting feedback stats: user_id={current_user.id}, days={days}")

        stats = service.get_feedback_stats(user_id=current_user.id, days=days)

        logger.info(
            f"Stats retrieved: {stats['total_feedbacks']} feedbacks, "
            f"avg rating {stats['average_rating']:.2f}"
        )

        return FeedbackStats(**stats)

    except Exception as e:
        logger.error(f"Failed to get stats: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get statistics: {str(e)}"
        )


# ========================================
# List Feedbacks
# ========================================

@router.get(
    "/list",
    response_model=FeedbackListResponse,
    summary="List feedbacks",
    description="List feedbacks with filtering and pagination"
)
async def list_feedbacks(
    rating: Optional[int] = None,
    limit: int = 100,
    offset: int = 0,
    current_user: User = Depends(get_current_active_user),
    service: FeedbackService = Depends(get_service)
):
    """
    List feedbacks

    Supports:
    - Filtering by user ID
    - Filtering by rating
    - Pagination with limit/offset

    Useful for:
    - Reviewing user feedback
    - Analyzing specific ratings
    - Audit trails
    """
    try:
        logger.info(
            f"Listing feedbacks: user_id={current_user.id}, rating={rating}, "
            f"limit={limit}, offset={offset}"
        )

        result = service.list_feedbacks(
            user_id=current_user.id,
            rating=rating,
            limit=limit,
            offset=offset
        )

        logger.info(f"Listed {result['count']}/{result['total']} feedbacks")

        return FeedbackListResponse(**result)

    except Exception as e:
        logger.error(f"Failed to list feedbacks: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list feedbacks: {str(e)}"
        )


# ========================================
# Trigger Retraining
# ========================================

@router.post(
    "/trigger-retrain",
    response_model=RetrainingTriggerResponse,
    summary="Trigger retraining",
    description="Manually trigger model retraining based on feedback"
)
async def trigger_retraining(
    request: RetrainingTriggerRequest,
    current_user: User = Depends(get_current_active_user),
    service: FeedbackService = Depends(get_service)
):
    """
    Trigger retraining

    Options:
    - Retrain specific cards (via card_ids)
    - Retrain based on negative feedback (card_ids=None)
    - Force immediate processing (force=True)
    - Scheduled processing (force=False, default)

    Process:
    1. Identifies cards needing retraining
    2. Queues them in retrain_queue table
    3. Optionally triggers immediate Celery task
    4. Scheduled task runs daily at 3 AM (configurable)

    Useful for:
    - Manual intervention after bad feedback
    - Testing retraining pipeline
    - Emergency updates
    """
    try:
        logger.info(
            f"Triggering retraining: card_ids={request.card_ids}, "
            f"force={request.force}"
        )

        result = service.trigger_retraining(
            card_ids=request.card_ids,
            force=request.force,
            batch_size=request.batch_size
        )

        logger.info(
            f"Retraining triggered: {result['queued_items']} items queued, "
            f"task_id: {result.get('task_id')}"
        )

        return RetrainingTriggerResponse(**result)

    except Exception as e:
        logger.error(f"Failed to trigger retraining: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to trigger retraining: {str(e)}"
        )


# ========================================
# Learning Insights
# ========================================

@router.get(
    "/insights",
    response_model=LearningInsightsResponse,
    summary="Get learning insights",
    description="Get AI-generated insights from feedback data"
)
async def get_learning_insights(
    days: int = 30,
    current_user: User = Depends(get_current_active_user),
    service: FeedbackService = Depends(get_service)
):
    """
    Get learning insights

    Analyzes feedback data to generate:
    - Satisfaction trends
    - Problem areas
    - Improvement recommendations
    - Actionable insights

    Insights are categorized by priority (high/medium/low).

    Useful for:
    - Product improvement
    - Identifying issues
    - Strategic planning
    """
    try:
        logger.info(f"Generating learning insights for {days} days")

        result = service.get_learning_insights(days=days)

        logger.info(
            f"Generated {result['total_insights']} insights, "
            f"{len(result['recommendations'])} recommendations"
        )

        return LearningInsightsResponse(**result)

    except Exception as e:
        logger.error(f"Failed to generate insights: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate insights: {str(e)}"
        )


# ========================================
# Health Check
# ========================================

@router.get(
    "/health",
    summary="Feedback service health check",
    description="Check if feedback service is operational"
)
async def health_check(service: FeedbackService = Depends(get_service)):
    """Feedback service health check"""
    return {
        "status": "healthy",
        "service": "feedback",
        "database": "connected"
    }
