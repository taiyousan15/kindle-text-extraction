"""
Feedback Service

Handles user feedback collection, analytics, and retraining queue management
"""
import logging
from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime, timedelta
from collections import defaultdict

from sqlalchemy.orm import Session
from sqlalchemy import func, desc

from app.models.feedback import Feedback
from app.models.biz_card import BizCard
from app.models.retrain_queue import RetrainQueue

logger = logging.getLogger(__name__)


class FeedbackService:
    """Service for managing user feedback and learning"""

    # Rating thresholds
    POSITIVE_THRESHOLD = 4  # 4-5 stars = positive
    NEGATIVE_THRESHOLD = 2  # 1-2 stars = negative
    RETRAIN_THRESHOLD = 2   # Queue for retraining if rating <= 2

    def __init__(self, db: Session):
        """
        Initialize Feedback Service

        Args:
            db: Database session
        """
        self.db = db

    def submit_feedback(
        self,
        query: str,
        answer: str,
        rating: int,
        user_id: Optional[int] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Submit user feedback

        Args:
            query: User query
            answer: System answer
            rating: Rating (1-5)
            user_id: Optional user ID
            metadata: Optional metadata

        Returns:
            dict: Feedback submission result
        """
        try:
            # Validate rating
            if rating < 1 or rating > 5:
                raise ValueError("Rating must be between 1 and 5")

            # Create feedback record
            feedback = Feedback(
                query=query,
                answer=answer,
                rating=rating,
                user_id=user_id
            )

            self.db.add(feedback)
            self.db.flush()

            logger.info(
                f"Feedback submitted: ID {feedback.id}, rating {rating}, "
                f"user_id {user_id}"
            )

            # Queue for retraining if negative feedback
            queued_for_retraining = False
            if rating <= self.RETRAIN_THRESHOLD:
                queued_for_retraining = self._queue_negative_feedback(
                    feedback, query, answer
                )

            self.db.commit()

            return {
                "feedback_id": feedback.id,
                "status": "submitted",
                "message": "Feedback submitted successfully",
                "queued_for_retraining": queued_for_retraining,
                "created_at": feedback.created_at.isoformat()
            }

        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to submit feedback: {e}", exc_info=True)
            raise

    def _queue_negative_feedback(
        self,
        feedback: Feedback,
        query: str,
        answer: str
    ) -> bool:
        """
        Queue negative feedback for retraining

        Args:
            feedback: Feedback object
            query: Query text
            answer: Answer text

        Returns:
            bool: True if queued
        """
        try:
            # Find related BizCards (simplified approach)
            # In production, you'd extract card IDs from the answer metadata
            # For now, we'll find cards with similar content

            # Extract potential card content from answer
            # This is a simplified approach - in production, track card IDs used
            cards = self.db.query(BizCard).filter(
                BizCard.content.ilike(f"%{query[:50]}%")
            ).limit(5).all()

            queued_count = 0
            for card in cards:
                # Check if already in retrain queue
                existing = self.db.query(RetrainQueue).filter(
                    RetrainQueue.card_id == card.id,
                    RetrainQueue.processed_at.is_(None)
                ).first()

                if not existing:
                    # Add to retrain queue
                    retrain_item = RetrainQueue(
                        card_id=card.id,
                        score=float(feedback.rating)
                    )
                    self.db.add(retrain_item)
                    queued_count += 1

            self.db.flush()

            logger.info(
                f"Queued {queued_count} cards for retraining based on "
                f"negative feedback {feedback.id}"
            )

            return queued_count > 0

        except Exception as e:
            logger.error(f"Failed to queue negative feedback: {e}", exc_info=True)
            return False

    def get_feedback_stats(
        self,
        user_id: Optional[int] = None,
        days: int = 30
    ) -> Dict[str, Any]:
        """
        Get feedback statistics

        Args:
            user_id: Optional user filter
            days: Period in days

        Returns:
            dict: Statistics
        """
        try:
            # Date range
            start_date = datetime.utcnow() - timedelta(days=days)

            # Base query
            query = self.db.query(Feedback).filter(
                Feedback.created_at >= start_date
            )

            if user_id:
                query = query.filter(Feedback.user_id == user_id)

            # Total count
            total_feedbacks = query.count()

            if total_feedbacks == 0:
                return self._empty_stats()

            # Average rating
            avg_rating = query.with_entities(
                func.avg(Feedback.rating)
            ).scalar()

            # Rating distribution
            rating_dist_raw = query.with_entities(
                Feedback.rating,
                func.count(Feedback.id)
            ).group_by(Feedback.rating).all()

            rating_distribution = {rating: count for rating, count in rating_dist_raw}

            # Ensure all ratings are present
            for i in range(1, 6):
                if i not in rating_distribution:
                    rating_distribution[i] = 0

            # Categorize feedback
            positive_count = sum(
                count for rating, count in rating_distribution.items()
                if rating >= self.POSITIVE_THRESHOLD
            )

            negative_count = sum(
                count for rating, count in rating_distribution.items()
                if rating <= self.NEGATIVE_THRESHOLD
            )

            neutral_count = total_feedbacks - positive_count - negative_count

            # Recent feedbacks (last 24 hours)
            recent_date = datetime.utcnow() - timedelta(hours=24)
            recent_feedbacks = query.filter(
                Feedback.created_at >= recent_date
            ).count()

            return {
                "total_feedbacks": total_feedbacks,
                "average_rating": float(avg_rating) if avg_rating else 0.0,
                "rating_distribution": rating_distribution,
                "positive_count": positive_count,
                "negative_count": negative_count,
                "neutral_count": neutral_count,
                "recent_feedbacks": recent_feedbacks,
                "timestamp": datetime.utcnow().isoformat()
            }

        except Exception as e:
            logger.error(f"Failed to get feedback stats: {e}", exc_info=True)
            raise

    def _empty_stats(self) -> Dict[str, Any]:
        """Return empty statistics"""
        return {
            "total_feedbacks": 0,
            "average_rating": 0.0,
            "rating_distribution": {1: 0, 2: 0, 3: 0, 4: 0, 5: 0},
            "positive_count": 0,
            "negative_count": 0,
            "neutral_count": 0,
            "recent_feedbacks": 0,
            "timestamp": datetime.utcnow().isoformat()
        }

    def list_feedbacks(
        self,
        user_id: Optional[int] = None,
        rating: Optional[int] = None,
        limit: int = 100,
        offset: int = 0
    ) -> Dict[str, Any]:
        """
        List feedbacks with filtering

        Args:
            user_id: Optional user filter
            rating: Optional rating filter
            limit: Max results
            offset: Pagination offset

        Returns:
            dict: Feedback list
        """
        try:
            query = self.db.query(Feedback)

            # Apply filters
            if user_id:
                query = query.filter(Feedback.user_id == user_id)

            if rating:
                query = query.filter(Feedback.rating == rating)

            # Count total
            total = query.count()

            # Paginate
            feedbacks = query.order_by(
                desc(Feedback.created_at)
            ).limit(limit).offset(offset).all()

            # Build response
            feedback_list = []
            for feedback in feedbacks:
                feedback_list.append({
                    "feedback_id": feedback.id,
                    "query": feedback.query,
                    "answer": feedback.answer,
                    "rating": feedback.rating,
                    "user_id": feedback.user_id,
                    "created_at": feedback.created_at.isoformat()
                })

            return {
                "total": total,
                "count": len(feedback_list),
                "limit": limit,
                "offset": offset,
                "feedbacks": feedback_list
            }

        except Exception as e:
            logger.error(f"Failed to list feedbacks: {e}", exc_info=True)
            raise

    def trigger_retraining(
        self,
        card_ids: Optional[List[int]] = None,
        force: bool = False,
        batch_size: int = 100
    ) -> Dict[str, Any]:
        """
        Trigger retraining process

        Args:
            card_ids: Specific card IDs (if None, uses feedback data)
            force: Force immediate retraining
            batch_size: Batch size

        Returns:
            dict: Trigger result
        """
        try:
            queued_items = 0

            if card_ids:
                # Queue specific cards
                for card_id in card_ids:
                    # Check if card exists
                    card = self.db.query(BizCard).filter(
                        BizCard.id == card_id
                    ).first()

                    if not card:
                        logger.warning(f"Card {card_id} not found, skipping")
                        continue

                    # Check if already queued
                    existing = self.db.query(RetrainQueue).filter(
                        RetrainQueue.card_id == card_id,
                        RetrainQueue.processed_at.is_(None)
                    ).first()

                    if existing:
                        logger.info(f"Card {card_id} already in queue, skipping")
                        continue

                    # Add to queue
                    retrain_item = RetrainQueue(
                        card_id=card_id,
                        score=0.0
                    )
                    self.db.add(retrain_item)
                    queued_items += 1

            else:
                # Queue based on negative feedback
                # Find cards associated with low-rated feedback
                negative_feedbacks = self.db.query(Feedback).filter(
                    Feedback.rating <= self.RETRAIN_THRESHOLD
                ).order_by(desc(Feedback.created_at)).limit(batch_size).all()

                logger.info(
                    f"Found {len(negative_feedbacks)} negative feedbacks to process"
                )

                for feedback in negative_feedbacks:
                    # Find related cards (simplified)
                    cards = self.db.query(BizCard).filter(
                        BizCard.content.ilike(f"%{feedback.query[:50]}%")
                    ).limit(3).all()

                    for card in cards:
                        # Check if already queued
                        existing = self.db.query(RetrainQueue).filter(
                            RetrainQueue.card_id == card.id,
                            RetrainQueue.processed_at.is_(None)
                        ).first()

                        if not existing:
                            retrain_item = RetrainQueue(
                                card_id=card.id,
                                score=float(feedback.rating)
                            )
                            self.db.add(retrain_item)
                            queued_items += 1

            self.db.commit()

            logger.info(f"Queued {queued_items} items for retraining")

            # If force, trigger immediate processing
            task_id = None
            if force and queued_items > 0:
                try:
                    from app.tasks.schedule import process_retraining_queue
                    result = process_retraining_queue.apply_async()
                    task_id = result.id
                    logger.info(f"Triggered immediate retraining: task {task_id}")
                except Exception as e:
                    logger.error(f"Failed to trigger immediate retraining: {e}")

            return {
                "status": "queued" if not force else "triggered",
                "message": f"Queued {queued_items} items for retraining",
                "queued_items": queued_items,
                "task_id": task_id,
                "timestamp": datetime.utcnow().isoformat()
            }

        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to trigger retraining: {e}", exc_info=True)
            raise

    def get_learning_insights(self, days: int = 30) -> Dict[str, Any]:
        """
        Generate learning insights from feedback data

        Args:
            days: Period in days

        Returns:
            dict: Insights and recommendations
        """
        try:
            start_date = datetime.utcnow() - timedelta(days=days)

            # Get feedback stats
            stats = self.get_feedback_stats(days=days)

            insights = []
            recommendations = []

            # Insight 1: Overall satisfaction
            avg_rating = stats["average_rating"]
            if avg_rating >= 4.0:
                insights.append({
                    "insight_type": "satisfaction",
                    "description": "High user satisfaction",
                    "data": {"average_rating": avg_rating},
                    "priority": "low"
                })
                recommendations.append("Continue current approach")
            elif avg_rating >= 3.0:
                insights.append({
                    "insight_type": "satisfaction",
                    "description": "Moderate user satisfaction",
                    "data": {"average_rating": avg_rating},
                    "priority": "medium"
                })
                recommendations.append("Investigate improvement opportunities")
            else:
                insights.append({
                    "insight_type": "satisfaction",
                    "description": "Low user satisfaction",
                    "data": {"average_rating": avg_rating},
                    "priority": "high"
                })
                recommendations.append("Urgent: Review and improve system responses")

            # Insight 2: Negative feedback trend
            negative_ratio = (
                stats["negative_count"] / stats["total_feedbacks"]
                if stats["total_feedbacks"] > 0 else 0
            )

            if negative_ratio > 0.3:
                insights.append({
                    "insight_type": "negative_trend",
                    "description": "High negative feedback ratio",
                    "data": {
                        "negative_count": stats["negative_count"],
                        "total": stats["total_feedbacks"],
                        "ratio": negative_ratio
                    },
                    "priority": "high"
                })
                recommendations.append("Trigger immediate retraining")

            # Insight 3: Recent activity
            if stats["recent_feedbacks"] == 0:
                insights.append({
                    "insight_type": "engagement",
                    "description": "No recent feedback (24h)",
                    "data": {"recent_feedbacks": 0},
                    "priority": "medium"
                })
                recommendations.append("Consider prompting users for feedback")

            # Insight 4: Rating distribution
            distribution = stats["rating_distribution"]
            if distribution.get(3, 0) > stats["total_feedbacks"] * 0.5:
                insights.append({
                    "insight_type": "polarization",
                    "description": "High neutral feedback - unclear user sentiment",
                    "data": {"neutral_count": distribution.get(3, 0)},
                    "priority": "medium"
                })
                recommendations.append("Improve response quality to increase satisfaction")

            return {
                "total_insights": len(insights),
                "insights": insights,
                "recommendations": recommendations,
                "timestamp": datetime.utcnow().isoformat()
            }

        except Exception as e:
            logger.error(f"Failed to generate insights: {e}", exc_info=True)
            raise


def get_feedback_service(db: Session) -> FeedbackService:
    """
    Factory function for FeedbackService

    Args:
        db: Database session

    Returns:
        FeedbackService instance
    """
    return FeedbackService(db=db)
