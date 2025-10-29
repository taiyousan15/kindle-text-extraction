"""
OCR Processing Tasks

Celery tasks for asynchronous OCR processing with pytesseract
"""
import logging
import traceback
from datetime import datetime
from typing import Optional
import pytesseract
from PIL import Image
import io

from celery import Task
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError

from app.tasks.celery_app import celery_app
from app.core.database import SessionLocal
from app.core.config import settings
from app.models.job import Job
from app.models.ocr_result import OCRResult

logger = logging.getLogger(__name__)

# Configure Tesseract
if settings.TESSDATA_PREFIX:
    pytesseract.pytesseract.tesseract_cmd = settings.TESSDATA_PREFIX


class OCRTask(Task):
    """Base task class with database session management"""

    def __call__(self, *args, **kwargs):
        """Execute task with database session"""
        return super().__call__(*args, **kwargs)

    def on_failure(self, exc, task_id, args, kwargs, einfo):
        """Handle task failure"""
        logger.error(
            f"Task {task_id} failed: {exc}\n"
            f"Args: {args}\n"
            f"Kwargs: {kwargs}\n"
            f"Error info: {einfo}"
        )

    def on_success(self, retval, task_id, args, kwargs):
        """Handle task success"""
        logger.info(f"Task {task_id} completed successfully")

    def on_retry(self, exc, task_id, args, kwargs, einfo):
        """Handle task retry"""
        logger.warning(f"Task {task_id} retrying due to: {exc}")


@celery_app.task(
    bind=True,
    base=OCRTask,
    name="app.tasks.ocr_tasks.process_ocr_job",
    max_retries=3,
    default_retry_delay=60,
    acks_late=True,
    reject_on_worker_lost=True,
)
def process_ocr_job(self, job_id: str) -> dict:
    """
    Process OCR job asynchronously

    Args:
        job_id: Job ID to process

    Returns:
        dict: Processing result with status and details

    Raises:
        Exception: On processing failure (will trigger retry)
    """
    db: Optional[Session] = None
    job: Optional[Job] = None

    try:
        # Create database session
        db = SessionLocal()
        logger.info(f"Starting OCR job processing: {job_id}")

        # Load job from database
        job = db.query(Job).filter(Job.id == job_id).first()
        if not job:
            raise ValueError(f"Job not found: {job_id}")

        # Update job status to processing
        job.status = "processing"
        job.progress = 0
        db.commit()
        logger.info(f"Job {job_id} status updated to 'processing'")

        # Get image data from job (assuming job has image_path or image_blob)
        # For MVP, we'll assume the image path is stored in the job
        # This needs to be adjusted based on actual job structure

        # Update progress
        job.progress = 10
        db.commit()

        # Process OCR (placeholder - actual implementation depends on image source)
        ocr_text, confidence = process_image_ocr(job, db)

        # Update progress
        job.progress = 80
        db.commit()

        # Save OCR result to database
        ocr_result = OCRResult(
            job_id=job.id,
            book_title="Extracted from OCR",  # Can be enhanced
            page_num=1,  # Can be enhanced for multi-page
            text=ocr_text,
            confidence=confidence,
            image_blob=None,  # Optionally store image
        )
        db.add(ocr_result)
        db.commit()
        logger.info(f"OCR result saved for job {job_id}")

        # Update progress
        job.progress = 90
        db.commit()

        # Mark job as completed
        job.status = "completed"
        job.progress = 100
        job.completed_at = datetime.utcnow()
        db.commit()

        logger.info(f"Job {job_id} completed successfully")

        return {
            "status": "success",
            "job_id": job_id,
            "result_id": ocr_result.id,
            "text_length": len(ocr_text),
            "confidence": confidence,
        }

    except Exception as exc:
        # Log the error
        logger.error(
            f"Error processing job {job_id}: {exc}\n"
            f"Traceback: {traceback.format_exc()}"
        )

        # Update job status to failed
        if db and job:
            try:
                job.status = "failed"
                job.error_message = str(exc)
                job.completed_at = datetime.utcnow()
                db.commit()
                logger.info(f"Job {job_id} marked as failed")
            except Exception as db_exc:
                logger.error(f"Failed to update job status: {db_exc}")
                db.rollback()

        # Retry if retries remain
        if self.request.retries < self.max_retries:
            logger.info(
                f"Retrying job {job_id} "
                f"(attempt {self.request.retries + 1}/{self.max_retries})"
            )
            raise self.retry(exc=exc, countdown=60 * (self.request.retries + 1))

        # Max retries reached, raise exception
        raise exc

    finally:
        # Close database session
        if db:
            db.close()


def process_image_ocr(job: Job, db: Session) -> tuple[str, float]:
    """
    Process image with pytesseract OCR

    Args:
        job: Job object with image data
        db: Database session

    Returns:
        tuple: (ocr_text, confidence_score)
    """
    try:
        # For MVP, we'll use a placeholder implementation
        # Actual implementation should load image from job.image_path or job.image_blob

        # Example: Load image from file path (if available)
        # image_path = job.metadata.get("image_path")  # Assuming metadata field
        # if not image_path:
        #     raise ValueError("No image path in job")

        # For now, return placeholder data
        # TODO: Implement actual OCR processing
        logger.warning(
            f"Using placeholder OCR for job {job.id}. "
            "Implement actual pytesseract processing."
        )

        # Placeholder OCR result
        ocr_text = "Sample OCR text from image processing"
        confidence = 0.95

        # Actual pytesseract implementation would be:
        # image = Image.open(image_path)
        # ocr_data = pytesseract.image_to_data(image, output_type=pytesseract.Output.DICT)
        # ocr_text = pytesseract.image_to_string(image, lang='jpn')
        # confidence = calculate_confidence(ocr_data)

        return ocr_text, confidence

    except Exception as exc:
        logger.error(f"OCR processing error: {exc}")
        raise


def calculate_confidence(ocr_data: dict) -> float:
    """
    Calculate average confidence from pytesseract output

    Args:
        ocr_data: Pytesseract output dictionary

    Returns:
        float: Average confidence score (0-1)
    """
    try:
        confidences = [
            float(conf) for conf in ocr_data.get("conf", [])
            if conf != "-1"
        ]
        if not confidences:
            return 0.0

        avg_confidence = sum(confidences) / len(confidences)
        return avg_confidence / 100.0  # Convert to 0-1 range

    except Exception as exc:
        logger.error(f"Confidence calculation error: {exc}")
        return 0.0


@celery_app.task(
    bind=True,
    name="app.tasks.ocr_tasks.process_batch_ocr",
    max_retries=3,
    default_retry_delay=60,
)
def process_batch_ocr(self, job_ids: list[str]) -> dict:
    """
    Process multiple OCR jobs in batch

    Args:
        job_ids: List of job IDs to process

    Returns:
        dict: Batch processing results
    """
    logger.info(f"Starting batch OCR processing for {len(job_ids)} jobs")

    results = {
        "total": len(job_ids),
        "successful": 0,
        "failed": 0,
        "details": [],
    }

    for job_id in job_ids:
        try:
            result = process_ocr_job.apply_async(args=[job_id])
            results["successful"] += 1
            results["details"].append({
                "job_id": job_id,
                "status": "queued",
                "task_id": result.id,
            })
        except Exception as exc:
            logger.error(f"Failed to queue job {job_id}: {exc}")
            results["failed"] += 1
            results["details"].append({
                "job_id": job_id,
                "status": "error",
                "error": str(exc),
            })

    logger.info(
        f"Batch processing completed: "
        f"{results['successful']} successful, {results['failed']} failed"
    )

    return results


@celery_app.task(
    bind=True,
    name="app.tasks.ocr_tasks.cleanup_old_jobs",
    max_retries=2,
)
def cleanup_old_jobs(self, days: int = 30) -> dict:
    """
    Clean up old completed/failed jobs

    Args:
        days: Delete jobs older than this many days

    Returns:
        dict: Cleanup statistics
    """
    db: Optional[Session] = None

    try:
        db = SessionLocal()
        logger.info(f"Cleaning up jobs older than {days} days")

        # Calculate cutoff date
        from datetime import timedelta
        cutoff_date = datetime.utcnow() - timedelta(days=days)

        # Delete old jobs
        deleted_count = (
            db.query(Job)
            .filter(Job.completed_at < cutoff_date)
            .filter(Job.status.in_(["completed", "failed"]))
            .delete(synchronize_session=False)
        )

        db.commit()
        logger.info(f"Deleted {deleted_count} old jobs")

        return {
            "status": "success",
            "deleted_count": deleted_count,
            "cutoff_date": cutoff_date.isoformat(),
        }

    except Exception as exc:
        logger.error(f"Cleanup error: {exc}")
        if db:
            db.rollback()
        raise

    finally:
        if db:
            db.close()
