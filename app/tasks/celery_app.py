"""
Celery Application Configuration

Redis-based distributed task queue for OCR processing and scheduled jobs
"""
from celery import Celery
from celery.schedules import crontab
import logging
import os

from app.core.config import settings

logger = logging.getLogger(__name__)

# Initialize Celery application
celery_app = Celery(
    "kindle_ocr",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
)

# Celery configuration
celery_app.conf.update(
    # Serialization
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",

    # Timezone
    timezone=settings.TIMEZONE,
    enable_utc=True,

    # Task routing
    task_routes={
        "app.tasks.ocr_tasks.*": {"queue": "ocr"},
        "app.tasks.schedule.*": {"queue": "scheduled"},
    },

    # Result backend settings
    result_expires=3600,  # Results expire after 1 hour
    result_backend_transport_options={
        "master_name": "mymaster",
        "visibility_timeout": 3600,
    },

    # Task execution settings
    task_track_started=True,
    task_time_limit=1800,  # 30 minutes hard limit
    task_soft_time_limit=1500,  # 25 minutes soft limit

    # Retry settings (default)
    task_default_retry_delay=60,  # Retry after 60 seconds
    task_max_retries=3,  # Maximum 3 retries

    # Worker settings
    worker_prefetch_multiplier=1,  # Prefetch one task at a time
    worker_max_tasks_per_child=1000,  # Restart worker after 1000 tasks

    # Logging
    worker_log_format="[%(asctime)s: %(levelname)s/%(processName)s] %(message)s",
    worker_task_log_format="[%(asctime)s: %(levelname)s/%(processName)s][%(task_name)s(%(task_id)s)] %(message)s",

    # Beat schedule (Celery Beat configuration)
    beat_schedule={
        "process-retraining-queue": {
            "task": "app.tasks.schedule.process_retraining_queue",
            "schedule": crontab(
                hour=int(settings.RELEARN_CRON.split()[1]) if settings.RELEARN_CRON else 3,
                minute=int(settings.RELEARN_CRON.split()[0]) if settings.RELEARN_CRON else 0,
            ),
            "options": {
                "queue": "scheduled",
            },
        },
    },
)

# Auto-discover tasks in app.tasks module
celery_app.autodiscover_tasks(["app.tasks"])


# Task event handlers
@celery_app.task(bind=True)
def debug_task(self):
    """Debug task for testing Celery configuration"""
    logger.info(f"Request: {self.request!r}")
    return f"Celery is working! Request: {self.request!r}"


# Celery signals
@celery_app.on_after_configure.connect
def setup_periodic_tasks(sender, **kwargs):
    """Setup periodic tasks after Celery is configured"""
    logger.info("Celery periodic tasks configured")


# Logging configuration
def configure_celery_logging():
    """Configure logging for Celery workers"""
    logging.basicConfig(
        level=logging.INFO,
        format="[%(asctime)s: %(levelname)s/%(name)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # Set log levels for specific modules
    logging.getLogger("celery").setLevel(logging.INFO)
    logging.getLogger("app.tasks").setLevel(logging.INFO)
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)


# Initialize logging
configure_celery_logging()

logger.info(f"Celery app initialized with broker: {settings.REDIS_URL}")
logger.info(f"Timezone: {settings.TIMEZONE}")
logger.info(f"Beat schedule: {celery_app.conf.beat_schedule}")
