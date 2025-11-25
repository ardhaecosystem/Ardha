"""
Simplified integration tests for memory-related Celery jobs.

Tests complete background job system including memory ingestion,
cleanup operations, and maintenance tasks.
"""

from datetime import datetime, timedelta
from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest

from ardha.jobs.memory_cleanup import (
    archive_old_memories,
    cleanup_expired_memories,
    cleanup_old_links,
    cleanup_orphaned_vectors,
    optimize_qdrant_collections,
)
from ardha.jobs.memory_jobs import (
    build_memory_relationships,
    ingest_chat_memories,
    ingest_workflow_memory,
    optimize_memory_importance,
    process_pending_embeddings,
)


@pytest.mark.asyncio
class TestMemoryJobsSimple:
    """Test memory-related background jobs with simplified mocking"""

    async def test_ingest_chat_memories_job(self, test_user, sample_chat_messages):
        """Test chat memory ingestion job"""
        # Mock memory service
        with patch("ardha.services.memory_service.MemoryService") as mock_memory_service:
            mock_mem_service = AsyncMock()
            mock_mem_service.ingest_from_chat.return_value = [
                AsyncMock(id=uuid4(), content="Test memory 1"),
                AsyncMock(id=uuid4(), content="Test memory 2"),
            ]

            # Execute job
            chat_id = uuid4()
            # Create mock task instance
            mock_task = AsyncMock()
            mock_task.get_memory_service.return_value = mock_mem_service

            # Mock job function directly - call the actual function logic
            from ardha.jobs.memory_jobs import ingest_chat_memories

            # Mock the task's get_memory_service method
            mock_task.get_memory_service.return_value = mock_mem_service

            # Call the actual task function with mock task as self
            result = await ingest_chat_memories.__func__(
                mock_task, str(chat_id), str(test_user["user"]["id"])
            )

            assert result["success"] is True
            assert "memories_created" in result
            assert result["chat_id"] == str(chat_id)

    async def test_ingest_workflow_memory_job(self, test_user, completed_workflow):
        """Test workflow memory ingestion job"""
        # Mock memory service
        with patch("ardha.services.memory_service.MemoryService") as mock_memory_service:
            mock_mem_service = AsyncMock()
            mock_memory = AsyncMock(id=uuid4(), content="Workflow memory")
            mock_mem_service.ingest_from_workflow.return_value = mock_memory

            # Execute job
            # Create mock task instance
            mock_task = AsyncMock()
            mock_task.get_memory_service.return_value = mock_mem_service

            # Mock job function directly
            from ardha.jobs.memory_jobs import ingest_workflow_memory

            result = await ingest_workflow_memory(
                mock_task,
                workflow_id=str(completed_workflow["id"]),
                user_id=str(test_user["user"]["id"]),
            )

            assert result["success"] is True
            assert "memory_id" in result
            assert result["workflow_id"] == str(completed_workflow["id"])

    async def test_process_pending_embeddings_job(self, sample_memories_batch):
        """Test pending embeddings processing job"""
        # Mock memory service
        with patch("ardha.services.memory_service.MemoryService") as mock_memory_service:
            mock_mem_service = AsyncMock()
            mock_mem_service.get_memories_without_embeddings.return_value = sample_memories_batch[
                :3
            ]
            mock_mem_service.generate_and_store_embedding.return_value = None

            # Execute job
            # Create mock task instance
            mock_task = AsyncMock()
            mock_task.get_memory_service.return_value = mock_mem_service

            # Mock job function directly
            from ardha.jobs.memory_jobs import process_pending_embeddings

            result = await process_pending_embeddings(mock_task)

            assert result["success"] is True
            assert "processed" in result
            assert result["processed"] == 3

    async def test_build_memory_relationships_job(self, sample_memories_batch):
        """Test memory relationship building job"""
        # Mock memory service
        with patch("ardha.services.memory_service.MemoryService") as mock_memory_service:
            mock_mem_service = AsyncMock()
            mock_mem_service.get_recent_unlinked_memories.return_value = sample_memories_batch[:2]
            mock_mem_service.find_similar_memories.return_value = []
            mock_mem_service.create_memory_link.return_value = None

            # Execute job
            # Create mock task instance
            mock_task = AsyncMock()
            mock_task.get_memory_service.return_value = mock_mem_service

            # Mock job function directly
            from ardha.jobs.memory_jobs import build_memory_relationships

            result = await build_memory_relationships(mock_task)

            assert result["success"] is True
            assert "relationships_created" in result

    async def test_optimize_memory_importance_job(self, sample_memories_batch):
        """Test memory importance optimization job"""
        # Mock memory service
        with patch("ardha.services.memory_service.MemoryService") as mock_memory_service:
            mock_mem_service = AsyncMock()
            mock_mem_service.get_memories_by_age.return_value = sample_memories_batch[:2]
            mock_mem_service.calculate_importance.return_value = 8
            mock_mem_service.update_memory_importance.return_value = None

            # Execute job
            # Create mock task instance
            mock_task = AsyncMock()
            mock_task.get_memory_service.return_value = mock_mem_service

            # Mock job function directly
            from ardha.jobs.memory_jobs import optimize_memory_importance

            result = await optimize_memory_importance(mock_task)

            assert result["success"] is True
            assert "updated" in result

    async def test_cleanup_expired_memories_job(self, sample_memories_batch):
        """Test expired memories cleanup job"""
        # Mock memory service
        with patch("ardha.services.memory_service.MemoryService") as mock_memory_service:
            mock_mem_service = AsyncMock()
            mock_mem_service.delete_expired_memories.return_value = 2

            # Execute job
            # Create mock task instance
            mock_task = AsyncMock()
            mock_task.get_memory_service.return_value = mock_mem_service

            # Mock job function directly
            from ardha.jobs.memory_cleanup import cleanup_expired_memories

            result = await cleanup_expired_memories(mock_task)

            assert result["success"] is True
            assert "deleted" in result
            assert result["deleted"] == 2

    async def test_archive_old_memories_job(self, sample_memories_batch):
        """Test old memories archival job"""
        # Mock memory service
        with patch("ardha.services.memory_service.MemoryService") as mock_memory_service:
            mock_mem_service = AsyncMock()
            mock_mem_service.archive_old_memories.return_value = 1

            # Execute job
            # Create mock task instance
            mock_task = AsyncMock()
            mock_task.get_memory_service.return_value = mock_mem_service

            # Mock job function directly
            from ardha.jobs.memory_cleanup import archive_old_memories

            result = await archive_old_memories(mock_task)

            assert result["success"] is True
            assert "archived" in result
            assert result["archived"] == 1

    async def test_cleanup_orphaned_vectors_job(self):
        """Test orphaned vectors cleanup job"""
        # Mock memory service
        with patch("ardha.services.memory_service.MemoryService") as mock_memory_service:
            mock_mem_service = AsyncMock()
            mock_mem_service.cleanup_orphaned_vectors.return_value = 3

            # Execute job
            # Create mock task instance
            mock_task = AsyncMock()
            mock_task.get_memory_service.return_value = mock_mem_service

            # Mock job function directly
            from ardha.jobs.memory_cleanup import cleanup_orphaned_vectors

            result = await cleanup_orphaned_vectors(mock_task)

            assert result["success"] is True
            assert "cleaned" in result
            assert result["cleaned"] == 3

    async def test_optimize_qdrant_collections_job(self):
        """Test Qdrant collections optimization job"""
        # Mock memory service
        with patch("ardha.services.memory_service.MemoryService") as mock_memory_service:
            mock_mem_service = AsyncMock()
            mock_mem_service.optimize_qdrant_collections.return_value = [
                "memories_user1",
                "memories_user2",
            ]

            # Execute job
            # Create mock task instance
            mock_task = AsyncMock()
            mock_task.get_memory_service.return_value = mock_mem_service

            # Mock job function directly
            from ardha.jobs.memory_cleanup import optimize_qdrant_collections

            result = await optimize_qdrant_collections(mock_task)

            assert result["success"] is True
            assert "optimized_collections" in result
            assert len(result["optimized_collections"]) == 2

    async def test_cleanup_old_links_job(self):
        """Test old memory links cleanup job"""
        # Mock memory service
        with patch("ardha.services.memory_service.MemoryService") as mock_memory_service:
            mock_mem_service = AsyncMock()
            mock_mem_service.cleanup_old_links.return_value = 1

            # Execute job
            # Create mock task instance
            mock_task = AsyncMock()
            mock_task.get_memory_service.return_value = mock_mem_service

            # Mock job function directly
            from ardha.jobs.memory_cleanup import cleanup_old_links

            result = await cleanup_old_links(mock_task)

            assert result["success"] is True
            assert "cleaned_links" in result
            assert result["cleaned_links"] == 1

    async def test_job_error_handling(self, test_user):
        """Test job error handling and logging"""
        # Mock memory service to raise exception
        with patch("ardha.services.memory_service.MemoryService") as mock_memory_service:
            mock_mem_service = AsyncMock()
            mock_mem_service.ingest_from_chat.side_effect = Exception("Service error")

            # Execute job and handle error gracefully
            try:
                # Create mock task instance
                mock_task = AsyncMock()
                mock_task.get_memory_service.return_value = mock_mem_service

                from ardha.jobs.memory_jobs import ingest_chat_memories

                await ingest_chat_memories(
                    mock_task, chat_id=str(uuid4()), user_id=str(test_user["user"]["id"])
                )
            except Exception as e:
                # Job should handle errors and return error information
                assert "Service error" in str(e)

    async def test_job_registration(self):
        """Test that all jobs are properly registered"""
        from ardha.core.celery_app import celery_app

        # Check that all memory jobs are registered
        job_names = [
            "ardha.jobs.memory_jobs.ingest_chat_memories",
            "ardha.jobs.memory_jobs.ingest_workflow_memory",
            "ardha.jobs.memory_jobs.process_pending_embeddings",
            "ardha.jobs.memory_jobs.build_memory_relationships",
            "ardha.jobs.memory_jobs.optimize_memory_importance",
            "ardha.jobs.memory_cleanup.cleanup_expired_memories",
            "ardha.jobs.memory_cleanup.archive_old_memories",
            "ardha.jobs.memory_cleanup.cleanup_orphaned_vectors",
            "ardha.jobs.memory_cleanup.optimize_qdrant_collections",
            "ardha.jobs.memory_cleanup.cleanup_old_links",
        ]

        for job_name in job_names:
            assert job_name in celery_app.tasks
            job = celery_app.tasks[job_name]
            assert job is not None
            assert hasattr(job, "run")
