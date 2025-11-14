"""
Celery app configuration for background jobs.

This module configures Celery for asynchronous task processing,
including scheduled tasks for memory maintenance and cleanup.
"""

import logging

from celery import Celery
from celery.schedules import crontab

from ..core.config import get_settings

logger = logging.getLogger(__name__)

# Get settings
settings = get_settings()

# Initialize Celery
celery_app = Celery("ardha", broker=settings.redis.url, backend=settings.redis.url)

# Celery configuration
celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=3600,  # 1 hour max
    task_soft_time_limit=3300,  # 55 minutes warning
    task_acks_late=True,  # Acknowledge after completion
    task_reject_on_worker_lost=True,
    worker_prefetch_multiplier=1,  # One task at a time
    result_expires=86400,  # Results expire in 24 hours
    worker_concurrency=2,  # 2 worker processes
    worker_disable_rate_limits=True,
    # Task routing
    task_routes={
        "ardha.jobs.memory_jobs.*": {"queue": "memory"},
        "ardha.jobs.memory_cleanup.*": {"queue": "cleanup"},
    },
    # Task annotations
    task_annotations={
        "ardha.jobs.memory_jobs.*": {"time_limit": 300},  # 5 minutes
        "ardha.jobs.memory_cleanup.*": {"time_limit": 600},  # 10 minutes
    },
)

# Scheduled tasks (Celery Beat)
celery_app.conf.beat_schedule = {
    # Cleanup expired memories daily at 2 AM
    "cleanup-expired-memories": {
        "task": "ardha.jobs.memory_cleanup.cleanup_expired_memories",
        "schedule": crontab(hour="2", minute="0"),
    },
    # Archive old unused memories weekly
    "archive-old-memories": {
        "task": "ardha.jobs.memory_cleanup.archive_old_memories",
        "schedule": crontab(day_of_week="0", hour="3", minute="0"),  # Sunday 3 AM
    },
    # Optimize memory importance daily at 4 AM
    "optimize-memory-importance": {
        "task": "ardha.jobs.memory_jobs.optimize_memory_importance",
        "schedule": crontab(hour="4", minute="0"),
    },
    # Process pending embeddings every hour
    "process-pending-embeddings": {
        "task": "ardha.jobs.memory_jobs.process_pending_embeddings",
        "schedule": crontab(minute="0"),  # Every hour
    },
    # Build memory relationships daily at 5 AM
    "build-memory-relationships": {
        "task": "ardha.jobs.memory_jobs.build_memory_relationships",
        "schedule": crontab(hour="5", minute="0"),
    },
}


@celery_app.task(bind=True)
def debug_task(self):
    """Debug task to test Celery setup"""
    logger.info(f"Request: {self.request!r}")
    return "Celery is working!"


logger.info("Celery app configured successfully")
