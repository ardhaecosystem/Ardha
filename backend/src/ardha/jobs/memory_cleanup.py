"""
Memory cleanup and maintenance jobs.

This module provides Celery tasks for automatic memory cleanup,
archiving, and maintenance operations.
"""

import logging
from datetime import datetime, timedelta

from celery import Task

from ..core.celery_app import celery_app
from ..core.database import async_session_factory
from ..repositories.memory_repository import MemoryRepository
from ..services.memory_service import MemoryService

logger = logging.getLogger(__name__)


class CleanupTask(Task):
    """Base task for cleanup operations."""

    def __init__(self):
        super().__init__()
        self._memory_service = None

    async def get_memory_service(self) -> MemoryService:
        """Get memory service instance with database session."""
        if self._memory_service is None:
            async with async_session_factory() as db:
                repository = MemoryRepository(db)
                self._memory_service = MemoryService(memory_repository=repository)
        return self._memory_service


@celery_app.task(
    base=CleanupTask, name="ardha.jobs.memory_cleanup.cleanup_expired_memories", bind=True
)
async def cleanup_expired_memories(self):
    """
    Delete expired short-term memories.

    Runs daily at 2 AM.
    """
    try:
        logger.info("Cleaning up expired memories")

        memory_service = await self.get_memory_service()
        deleted_count = await memory_service.delete_expired_memories()

        logger.info(f"Deleted {deleted_count} expired memories")
        return {"success": True, "deleted": deleted_count}

    except Exception as e:
        logger.error(f"Failed to cleanup expired memories: {e}")
        return {"success": False, "error": str(e)}


@celery_app.task(base=CleanupTask, name="ardha.jobs.memory_cleanup.archive_old_memories", bind=True)
async def archive_old_memories(self):
    """
    Archive memories not accessed in 6 months.

    Runs weekly on Sunday at 3 AM.
    """
    try:
        logger.info("Archiving old unused memories")

        cutoff_date = datetime.utcnow() - timedelta(days=180)

        memory_service = await self.get_memory_service()
        archived_count = await memory_service.archive_old_memories(
            last_accessed_before=cutoff_date, max_importance=5  # Don't archive important memories
        )

        logger.info(f"Archived {archived_count} old memories")
        return {"success": True, "archived": archived_count}

    except Exception as e:
        logger.error(f"Failed to archive old memories: {e}")
        return {"success": False, "error": str(e)}


@celery_app.task(
    base=CleanupTask, name="ardha.jobs.memory_cleanup.cleanup_orphaned_vectors", bind=True
)
async def cleanup_orphaned_vectors(self):
    """
    Remove vectors from Qdrant that don't have PostgreSQL records.

    Manual trigger only.
    """
    try:
        logger.info("Cleaning up orphaned vectors in Qdrant")

        memory_service = await self.get_memory_service()
        cleaned_count = await memory_service.cleanup_orphaned_vectors()

        logger.info(f"Cleaned up {cleaned_count} orphaned vectors")
        return {"success": True, "cleaned": cleaned_count}

    except Exception as e:
        logger.error(f"Failed to cleanup orphaned vectors: {e}")
        return {"success": False, "error": str(e)}


@celery_app.task(
    base=CleanupTask, name="ardha.jobs.memory_cleanup.optimize_qdrant_collections", bind=True
)
async def optimize_qdrant_collections(self):
    """
    Optimize Qdrant collections for better performance.

    Runs monthly on the 1st at 1 AM.
    """
    try:
        logger.info("Optimizing Qdrant collections")

        memory_service = await self.get_memory_service()
        optimized_collections = await memory_service.optimize_qdrant_collections()

        logger.info(f"Optimized {len(optimized_collections)} Qdrant collections")
        return {"success": True, "optimized_collections": optimized_collections}

    except Exception as e:
        logger.error(f"Failed to optimize Qdrant collections: {e}")
        return {"success": False, "error": str(e)}


@celery_app.task(base=CleanupTask, name="ardha.jobs.memory_cleanup.cleanup_old_links", bind=True)
async def cleanup_old_links(self):
    """
    Remove old memory links that are no longer relevant.

    Runs weekly on Saturday at 2 AM.
    """
    try:
        logger.info("Cleaning up old memory links")

        memory_service = await self.get_memory_service()
        cleaned_links = await memory_service.cleanup_old_links(
            days_old=90, min_strength=0.3  # Remove links older than 90 days  # Remove weak links
        )

        logger.info(f"Cleaned up {cleaned_links} old memory links")
        return {"success": True, "cleaned_links": cleaned_links}

    except Exception as e:
        logger.error(f"Failed to cleanup old memory links: {e}")
        return {"success": False, "error": str(e)}


# Note: The cleanup methods are now implemented in MemoryService
# The jobs above call the actual methods directly


logger.info("Memory cleanup jobs configured successfully")
