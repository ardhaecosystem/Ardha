"""
Memory ingestion and maintenance jobs.

This module provides Celery tasks for automatic memory ingestion,
embedding processing, and memory relationship building.
"""

import logging
from uuid import UUID

from celery import Task

from ..core.celery_app import celery_app
from ..core.database import async_session_factory
from ..repositories.memory_repository import MemoryRepository
from ..services.chat_service import ChatService
from ..services.memory_service import MemoryService
from ..services.workflow_service import WorkflowService

logger = logging.getLogger(__name__)


class DatabaseTask(Task):
    """Base task with database session management."""

    def __init__(self):
        super().__init__()
        self._memory_service = None
        self._chat_service = None
        self._workflow_service = None

    async def get_memory_service(self) -> MemoryService:
        """Get memory service instance with database session."""
        async with async_session_factory() as db:
            repository = MemoryRepository(db)
            return MemoryService(memory_repository=repository)

    async def get_chat_service(self) -> ChatService:
        """Get chat service instance with database session."""
        async with async_session_factory() as db:
            return ChatService(db)

    async def get_workflow_service(self) -> WorkflowService:
        """Get workflow service instance with database session."""
        async with async_session_factory() as db:
            return WorkflowService(db)


@celery_app.task(
    base=DatabaseTask,
    name="ardha.jobs.memory_jobs.ingest_chat_memories",
    bind=True,
    max_retries=3,
    default_retry_delay=300,  # 5 minutes
)
async def ingest_chat_memories(self, chat_id: str, user_id: str):
    """
    Extract and store important information from chat.

    Triggered when:
    - Chat reaches 10+ messages
    - User manually requests ingestion
    - Chat is marked as complete
    """
    try:
        logger.info(f"Starting memory ingestion for chat {chat_id}")

        memory_service = await self.get_memory_service()
        memories = await memory_service.ingest_from_chat(
            chat_id=UUID(chat_id), user_id=UUID(user_id), min_importance=6
        )

        logger.info(f"Created {len(memories)} memories from chat {chat_id}")
        return {"success": True, "memories_created": len(memories), "chat_id": chat_id}

    except Exception as e:
        logger.error(f"Failed to ingest chat memories: {e}")
        raise self.retry(exc=e)


@celery_app.task(
    base=DatabaseTask,
    name="ardha.jobs.memory_jobs.ingest_workflow_memory",
    bind=True,
    max_retries=3,
)
async def ingest_workflow_memory(self, workflow_id: str, user_id: str):
    """
    Store workflow output as memory.

    Triggered when:
    - Workflow completes successfully
    - Workflow produces important insights
    """
    try:
        logger.info(f"Ingesting workflow memory: {workflow_id}")

        memory_service = await self.get_memory_service()
        memory = await memory_service.ingest_from_workflow(
            workflow_id=UUID(workflow_id), user_id=UUID(user_id)
        )

        logger.info(f"Created memory {memory.id} from workflow {workflow_id}")
        return {"success": True, "memory_id": str(memory.id), "workflow_id": workflow_id}

    except Exception as e:
        logger.error(f"Failed to ingest workflow memory: {e}")
        raise self.retry(exc=e)


@celery_app.task(
    base=DatabaseTask, name="ardha.jobs.memory_jobs.process_pending_embeddings", bind=True
)
async def process_pending_embeddings(self):
    """
    Generate embeddings for memories that don't have them yet.

    Uses local all-MiniLM-L6-v2 model (FREE!).
    Runs every hour.
    """
    try:
        logger.info("Processing pending embeddings")

        memory_service = await self.get_memory_service()
        # Find memories without embeddings
        pending_memories = await memory_service.get_memories_without_embeddings(limit=100)

        if not pending_memories:
            logger.info("No pending embeddings to process")
            return {"success": True, "processed": 0}

        # Generate embeddings in batch (uses local model - FREE!)
        processed_count = 0
        for memory in pending_memories:
            try:
                await memory_service.generate_and_store_embedding(memory.id)
                processed_count += 1
            except Exception as e:
                logger.error(f"Failed to process memory {memory.id}: {e}")
                continue

        logger.info(f"Processed {processed_count} pending embeddings")
        return {"success": True, "processed": processed_count}

    except Exception as e:
        logger.error(f"Failed to process pending embeddings: {e}")
        return {"success": False, "error": str(e)}


@celery_app.task(
    base=DatabaseTask, name="ardha.jobs.memory_jobs.build_memory_relationships", bind=True
)
async def build_memory_relationships(self):
    """
    Find and create relationships between similar memories.

    Uses semantic search with local embeddings (FREE!).
    Runs daily.
    """
    try:
        logger.info("Building memory relationships")

        memory_service = await self.get_memory_service()
        # Get recent memories without relationships
        recent_memories = await memory_service.get_recent_unlinked_memories(days=7, limit=50)

        relationships_created = 0
        for memory in recent_memories:
            try:
                # Find similar memories (uses local embeddings - FREE!)
                similar = await memory_service.find_similar_memories(
                    memory_id=memory.id, min_score=0.7, limit=5
                )

                # Create relationship links
                for similar_memory, score in similar:
                    await memory_service.create_memory_link(
                        from_id=memory.id,
                        to_id=similar_memory.id,
                        relationship_type="related_to",
                        strength=score,
                    )
                    relationships_created += 1

            except Exception as e:
                logger.error(f"Failed to build relationships for {memory.id}: {e}")
                continue

        logger.info(f"Created {relationships_created} memory relationships")
        return {"success": True, "relationships_created": relationships_created}

    except Exception as e:
        logger.error(f"Failed to build relationships: {e}")
        return {"success": False, "error": str(e)}


@celery_app.task(
    base=DatabaseTask, name="ardha.jobs.memory_jobs.optimize_memory_importance", bind=True
)
async def optimize_memory_importance(self):
    """
    Recalculate importance scores based on access patterns.

    Runs daily at 4 AM.
    """
    try:
        logger.info("Optimizing memory importance scores")

        # Get all memories updated in last 30 days
        memory_service = await self.get_memory_service()
        recent_memories = await memory_service.get_memories_by_age(days=30, limit=1000)

        updated_count = 0
        for memory in recent_memories:
            try:
                # Recalculate importance
                new_importance = await memory_service.calculate_importance(memory_id=memory.id)

                # Update if changed significantly (±2 points)
                if abs(new_importance - memory.importance) >= 2:
                    await memory_service.update_memory_importance(
                        memory_id=memory.id, importance=new_importance
                    )
                    updated_count += 1

            except Exception as e:
                logger.error(f"Failed to optimize memory {memory.id}: {e}")
                continue

        logger.info(f"Updated importance for {updated_count} memories")
        return {"success": True, "updated": updated_count}

    except Exception as e:
        logger.error(f"Failed to optimize importance: {e}")
        return {"success": False, "error": str(e)}


# Note: All helper methods are now implemented in MemoryService
# The jobs above call the actual methods directly


logger.info("Memory jobs configured successfully")
