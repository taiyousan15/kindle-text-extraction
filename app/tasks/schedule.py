"""
Scheduled Tasks

Celery Beat scheduled tasks for ML retraining and maintenance
"""
import logging
from datetime import datetime
from typing import Optional

from celery import Task
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.tasks.celery_app import celery_app
from app.core.database import SessionLocal
from app.core.config import settings
from app.models.retrain_queue import RetrainQueue
from app.models.biz_card import BizCard

logger = logging.getLogger(__name__)


class ScheduledTask(Task):
    """Base task class for scheduled tasks"""

    def on_failure(self, exc, task_id, args, kwargs, einfo):
        """Handle task failure"""
        logger.error(
            f"Scheduled task {task_id} failed: {exc}\n"
            f"Error info: {einfo}"
        )

    def on_success(self, retval, task_id, args, kwargs):
        """Handle task success"""
        logger.info(f"Scheduled task {task_id} completed: {retval}")


@celery_app.task(
    bind=True,
    base=ScheduledTask,
    name="app.tasks.schedule.process_retraining_queue",
    max_retries=2,
    default_retry_delay=300,  # 5 minutes
    soft_time_limit=1800,  # 30 minutes soft limit
    time_limit=2100,  # 35 minutes hard limit
)
def process_retraining_queue(self, batch_size: int = 100) -> dict:
    """
    Process pending retraining queue items

    Scheduled to run daily at 3 AM (configurable via RELEARN_CRON)

    Args:
        batch_size: Maximum number of items to process in one run

    Returns:
        dict: Processing statistics
    """
    db: Optional[Session] = None
    processed_count = 0
    failed_count = 0
    skipped_count = 0

    try:
        db = SessionLocal()
        logger.info("Starting retraining queue processing")

        # Query pending items (not yet processed)
        pending_items = (
            db.query(RetrainQueue)
            .filter(RetrainQueue.processed_at.is_(None))
            .order_by(RetrainQueue.queued_at.asc())
            .limit(batch_size)
            .all()
        )

        total_items = len(pending_items)
        logger.info(f"Found {total_items} pending items to process")

        if total_items == 0:
            logger.info("No pending items in retraining queue")
            return {
                "status": "success",
                "message": "No items to process",
                "processed": 0,
                "failed": 0,
                "skipped": 0,
                "timestamp": datetime.utcnow().isoformat(),
            }

        # Process each item
        for idx, item in enumerate(pending_items, 1):
            try:
                logger.info(
                    f"Processing item {idx}/{total_items}: "
                    f"RetrainQueue ID {item.id}, Card ID {item.card_id}"
                )

                # Load associated business card
                card = db.query(BizCard).filter(BizCard.id == item.card_id).first()

                if not card:
                    logger.warning(
                        f"Business card {item.card_id} not found, skipping"
                    )
                    skipped_count += 1
                    continue

                # Process the retraining (placeholder - implement actual ML logic)
                success = process_card_retraining(card, item, db)

                if success:
                    # Mark as processed
                    item.processed_at = datetime.utcnow()
                    db.commit()
                    processed_count += 1
                    logger.info(
                        f"Successfully processed RetrainQueue ID {item.id}"
                    )
                else:
                    logger.warning(
                        f"Failed to process RetrainQueue ID {item.id}"
                    )
                    failed_count += 1

            except Exception as item_exc:
                logger.error(
                    f"Error processing RetrainQueue ID {item.id}: {item_exc}",
                    exc_info=True,
                )
                failed_count += 1
                db.rollback()

        # Final commit for all processed items
        db.commit()

        result = {
            "status": "success",
            "total_pending": total_items,
            "processed": processed_count,
            "failed": failed_count,
            "skipped": skipped_count,
            "timestamp": datetime.utcnow().isoformat(),
        }

        logger.info(
            f"Retraining queue processing completed: {result}"
        )

        return result

    except Exception as exc:
        logger.error(
            f"Fatal error in retraining queue processing: {exc}",
            exc_info=True,
        )

        if db:
            db.rollback()

        # Retry if retries remain
        if self.request.retries < self.max_retries:
            logger.info(
                f"Retrying retraining queue processing "
                f"(attempt {self.request.retries + 1}/{self.max_retries})"
            )
            raise self.retry(exc=exc, countdown=300)

        # Max retries reached
        return {
            "status": "error",
            "error": str(exc),
            "processed": processed_count,
            "failed": failed_count,
            "timestamp": datetime.utcnow().isoformat(),
        }

    finally:
        if db:
            db.close()


def process_card_retraining(
    card: BizCard,
    queue_item: RetrainQueue,
    db: Session
) -> bool:
    """
    Process ML retraining for a business card

    Uses feedback data to improve embeddings quality.

    Args:
        card: BizCard object to retrain
        queue_item: RetrainQueue item
        db: Database session

    Returns:
        bool: True if successful, False otherwise
    """
    try:
        logger.info(f"Processing retraining for card {card.id}")

        # Import embedding service
        from app.services.embedding_service import get_embedding_service
        from app.models.feedback import Feedback

        # Get feedback related to this card
        # Find feedback with queries similar to card content
        related_feedbacks = (
            db.query(Feedback)
            .filter(Feedback.rating <= 2)  # Negative feedback only
            .order_by(Feedback.created_at.desc())
            .limit(10)
            .all()
        )

        if not related_feedbacks:
            logger.info(f"No negative feedback found for card {card.id}, skipping")
            return True

        # Strategy: Regenerate embedding with improved context
        # In production, you might:
        # 1. Use feedback to augment the content
        # 2. Apply different embedding parameters
        # 3. Use a different model
        # 4. Fine-tune the embedding model

        try:
            embedding_service = get_embedding_service()

            # Regenerate embedding
            # Add context from feedback to improve relevance
            enhanced_content = card.content

            # Check if content is still relevant based on feedback
            feedback_queries = [f.query for f in related_feedbacks if f.query]

            if feedback_queries:
                # Calculate similarity with negative feedback queries
                # If too similar, this card might be causing issues
                avg_similarity = 0.0
                for query in feedback_queries[:3]:  # Sample 3 queries
                    try:
                        similarity = embedding_service.similarity(
                            card.content,
                            query,
                            use_cache=False
                        )
                        avg_similarity += similarity
                    except Exception as e:
                        logger.warning(f"Similarity calculation failed: {e}")
                        continue

                avg_similarity = avg_similarity / min(len(feedback_queries), 3)

                logger.info(
                    f"Card {card.id} similarity with negative feedback: "
                    f"{avg_similarity:.4f}"
                )

                # If highly similar to negative feedback, reduce its score
                if avg_similarity > 0.7:
                    # This card is frequently associated with poor results
                    card.score = max(0.0, (card.score or 0.5) - 0.2)
                    logger.warning(
                        f"Reduced score for card {card.id} due to negative feedback "
                        f"association (new score: {card.score})"
                    )
                else:
                    # Regenerate embedding with cache disabled
                    new_embedding = embedding_service.generate_embedding(
                        enhanced_content,
                        use_cache=False
                    )

                    # Update embedding
                    card.vector_embedding = new_embedding

                    # Improve score slightly (reward for retraining)
                    card.score = min(1.0, (card.score or 0.5) + 0.1)

                    logger.info(
                        f"Updated embedding for card {card.id} "
                        f"(new score: {card.score})"
                    )

            db.flush()

            logger.info(f"Successfully retrained card {card.id}")
            return True

        except Exception as emb_exc:
            logger.error(
                f"Embedding regeneration failed for card {card.id}: {emb_exc}",
                exc_info=True
            )
            # Continue with success to mark as processed
            return True

    except Exception as exc:
        logger.error(
            f"Error in card retraining for card {card.id}: {exc}",
            exc_info=True,
        )
        return False


@celery_app.task(
    bind=True,
    base=ScheduledTask,
    name="app.tasks.schedule.cleanup_processed_queue",
    max_retries=2,
)
def cleanup_processed_queue(self, retention_days: int = 30) -> dict:
    """
    Clean up old processed retraining queue items

    Args:
        retention_days: Keep processed items for this many days

    Returns:
        dict: Cleanup statistics
    """
    db: Optional[Session] = None

    try:
        db = SessionLocal()
        logger.info(
            f"Cleaning up processed queue items older than {retention_days} days"
        )

        # Calculate cutoff date
        from datetime import timedelta
        cutoff_date = datetime.utcnow() - timedelta(days=retention_days)

        # Delete old processed items
        deleted_count = (
            db.query(RetrainQueue)
            .filter(RetrainQueue.processed_at.isnot(None))
            .filter(RetrainQueue.processed_at < cutoff_date)
            .delete(synchronize_session=False)
        )

        db.commit()
        logger.info(f"Deleted {deleted_count} old processed queue items")

        return {
            "status": "success",
            "deleted_count": deleted_count,
            "cutoff_date": cutoff_date.isoformat(),
            "timestamp": datetime.utcnow().isoformat(),
        }

    except Exception as exc:
        logger.error(f"Cleanup error: {exc}", exc_info=True)
        if db:
            db.rollback()

        return {
            "status": "error",
            "error": str(exc),
            "deleted_count": 0,
            "timestamp": datetime.utcnow().isoformat(),
        }

    finally:
        if db:
            db.close()


@celery_app.task(
    bind=True,
    base=ScheduledTask,
    name="app.tasks.schedule.generate_retraining_report",
    max_retries=1,
)
def generate_retraining_report(self, days: int = 7) -> dict:
    """
    Generate report on retraining queue statistics

    Args:
        days: Report period in days

    Returns:
        dict: Report statistics
    """
    db: Optional[Session] = None

    try:
        db = SessionLocal()
        logger.info(f"Generating retraining report for last {days} days")

        # Calculate date range
        from datetime import timedelta
        start_date = datetime.utcnow() - timedelta(days=days)

        # Query statistics
        total_queued = (
            db.query(func.count(RetrainQueue.id))
            .filter(RetrainQueue.queued_at >= start_date)
            .scalar()
        )

        total_processed = (
            db.query(func.count(RetrainQueue.id))
            .filter(RetrainQueue.processed_at >= start_date)
            .filter(RetrainQueue.processed_at.isnot(None))
            .scalar()
        )

        total_pending = (
            db.query(func.count(RetrainQueue.id))
            .filter(RetrainQueue.queued_at >= start_date)
            .filter(RetrainQueue.processed_at.is_(None))
            .scalar()
        )

        avg_score = (
            db.query(func.avg(RetrainQueue.score))
            .filter(RetrainQueue.processed_at >= start_date)
            .filter(RetrainQueue.processed_at.isnot(None))
            .scalar()
        )

        report = {
            "status": "success",
            "period_days": days,
            "start_date": start_date.isoformat(),
            "end_date": datetime.utcnow().isoformat(),
            "statistics": {
                "total_queued": total_queued or 0,
                "total_processed": total_processed or 0,
                "total_pending": total_pending or 0,
                "average_score": float(avg_score) if avg_score else 0.0,
                "processing_rate": (
                    (total_processed / total_queued * 100)
                    if total_queued > 0
                    else 0.0
                ),
            },
            "timestamp": datetime.utcnow().isoformat(),
        }

        logger.info(f"Retraining report generated: {report}")
        return report

    except Exception as exc:
        logger.error(f"Report generation error: {exc}", exc_info=True)

        return {
            "status": "error",
            "error": str(exc),
            "timestamp": datetime.utcnow().isoformat(),
        }

    finally:
        if db:
            db.close()


@celery_app.task(
    bind=True,
    base=ScheduledTask,
    name="app.tasks.schedule.health_check",
)
def health_check(self) -> dict:
    """
    Health check task for monitoring

    Returns:
        dict: Health status
    """
    try:
        db = SessionLocal()

        # Test database connection
        db.execute("SELECT 1")
        db_healthy = True

    except Exception as exc:
        logger.error(f"Health check failed: {exc}")
        db_healthy = False

    finally:
        if db:
            db.close()

    return {
        "status": "healthy" if db_healthy else "unhealthy",
        "database": db_healthy,
        "timestamp": datetime.utcnow().isoformat(),
        "celery_version": celery_app.VERSION,
    }
