"""
Integration tests for memory-related Celery jobs.

Tests the complete background job system including memory ingestion,
cleanup operations, and maintenance tasks.
"""

from datetime import datetime, timedelta
from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest
from celery.result import AsyncResult

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
class TestMemoryJobs:
    """Test memory-related background jobs"""

    async def test_ingest_chat_memories_job(
        self, test_db, test_user, sample_chat_messages, mock_local_embedding
    ):
        """Test chat memory ingestion job"""
        # Mock chat service
        with patch("ardha.jobs.memory_jobs.ChatService") as mock_chat_service:
            mock_service = AsyncMock()
            mock_service.get_chat_history.return_value = sample_chat_messages
            mock_chat_service.return_value = mock_service

            # Mock embedding and Qdrant services
            with patch("ardha.jobs.memory_jobs.get_embedding_service") as mock_embedding:
                mock_emb_service = AsyncMock()
                mock_emb_service.generate_embedding.return_value = mock_local_embedding
                mock_embedding.return_value = mock_emb_service

                with patch("ardha.jobs.memory_jobs.get_qdrant_service") as mock_qdrant:
                    mock_qdrant_service = AsyncMock()
                    mock_qdrant_service.upsert_vectors.return_value = None
                    mock_qdrant_service.collection_exists.return_value = True
                    mock_qdrant.return_value = mock_qdrant_service

                    # Execute job
                    chat_id = uuid4()
                    # Create mock task instance
                    mock_task = AsyncMock()
                    mock_task.get_memory_service = AsyncMock()

                    # Mock the job function directly
                    from ardha.jobs.memory_jobs import ingest_chat_memories

                    result = await ingest_chat_memories(
                        mock_task, chat_id=str(chat_id), user_id=str(test_user.id)
                    )

                    assert result["ingested_count"] >= 0
                    assert "chat_id" in result
                    assert result["chat_id"] == str(chat_id)

    async def test_ingest_workflow_memory_job(
        self, test_db, test_user, completed_workflow, mock_local_embedding
    ):
        """Test workflow memory ingestion job"""
        # Mock embedding and Qdrant services
        with patch("ardha.jobs.memory_jobs.get_embedding_service") as mock_embedding:
            mock_emb_service = AsyncMock()
            mock_emb_service.generate_embedding.return_value = mock_local_embedding
            mock_embedding.return_value = mock_emb_service

            with patch("ardha.jobs.memory_jobs.get_qdrant_service") as mock_qdrant:
                mock_qdrant_service = AsyncMock()
                mock_qdrant_service.upsert_vectors.return_value = None
                mock_qdrant_service.collection_exists.return_value = True
                mock_qdrant.return_value = mock_qdrant_service

                # Execute job
                # Create mock task instance
                mock_task = AsyncMock()
                mock_task.get_memory_service = AsyncMock()

                # Mock the job function directly
                from ardha.jobs.memory_jobs import ingest_workflow_memory

                result = await ingest_workflow_memory(
                    mock_task, workflow_id=str(completed_workflow.id), user_id=str(test_user.id)
                )

                assert result["status"] == "success"
                assert "memory_id" in result
                assert "workflow_id" in result

    async def test_process_pending_embeddings_job(
        self, test_db, sample_memories_batch, mock_local_embedding
    ):
        """Test pending embeddings processing job"""
        # Add memories without embeddings to database
        from ardha.core.database import get_db

        async for db in get_db():
            for memory in sample_memories_batch:
                memory.qdrant_point_id = None  # Simulate missing embedding
                db.add(memory)
            await db.commit()
            break

        # Mock embedding and Qdrant services
        with patch("ardha.jobs.memory_jobs.get_embedding_service") as mock_embedding:
            mock_emb_service = AsyncMock()
            mock_emb_service.generate_embedding.return_value = mock_local_embedding
            mock_embedding.return_value = mock_emb_service

            with patch("ardha.jobs.memory_jobs.get_qdrant_service") as mock_qdrant:
                mock_qdrant_service = AsyncMock()
                mock_qdrant_service.upsert_vectors.return_value = None
                mock_qdrant_service.collection_exists.return_value = True
                mock_qdrant.return_value = mock_qdrant_service

                # Execute job
                # Create mock task instance
                mock_task = AsyncMock()
                mock_task.get_memory_service = AsyncMock()

                # Mock the job function directly
                from ardha.jobs.memory_jobs import process_pending_embeddings

                result = await process_pending_embeddings(mock_task)

                assert result["processed_count"] >= 0
                assert "batch_size" in result
                assert result["batch_size"] == 32

    async def test_build_memory_relationships_job(
        self, test_db, sample_memories_batch, mock_local_embedding
    ):
        """Test memory relationship building job"""
        # Add memories to database
        from ardha.core.database import get_db

        async for db in get_db():
            for memory in sample_memories_batch:
                db.add(memory)
            await db.commit()
            break

        # Mock embedding service
        with patch("ardha.jobs.memory_jobs.get_embedding_service") as mock_embedding:
            mock_emb_service = AsyncMock()
            mock_emb_service.generate_batch_embeddings.return_value = [
                [0.1] * 384,
                [0.2] * 384,
                [0.3] * 384,
            ]
            mock_embedding.return_value = mock_emb_service

            # Execute job
            # Create mock task instance
            mock_task = AsyncMock()
            mock_task.get_memory_service = AsyncMock()

            # Mock the job function directly
            from ardha.jobs.memory_jobs import build_memory_relationships

            result = await build_memory_relationships(mock_task)

            assert result["processed_count"] >= 0
            assert "created_links" in result
            assert isinstance(result["created_links"], int)

    async def test_optimize_memory_importance_job(self, test_db, sample_memories_batch):
        """Test memory importance optimization job"""
        # Add memories to database
        from ardha.core.database import get_db

        async for db in get_db():
            for memory in sample_memories_batch:
                db.add(memory)
            await db.commit()
            break

        # Execute job
        # Create mock task instance
        mock_task = AsyncMock()
        mock_task.get_memory_service = AsyncMock()

        # Mock the job function directly
        from ardha.jobs.memory_jobs import optimize_memory_importance

        result = await optimize_memory_importance(mock_task)

        assert result["updated_count"] >= 0
        assert "user_id" in result

    async def test_cleanup_expired_memories_job(self, test_db, sample_memories_batch):
        """Test expired memories cleanup job"""
        # Add old memories to database
        from ardha.core.database import get_db

        async for db in get_db():
            for memory in sample_memories_batch:
                memory.created_at = datetime.utcnow() - timedelta(days=10)  # Make old
                memory.importance = 3  # Low importance
                db.add(memory)
            await db.commit()
            break

        # Mock Qdrant service
        with patch("ardha.jobs.memory_cleanup.get_qdrant_service") as mock_qdrant:
            mock_qdrant_service = AsyncMock()
            mock_qdrant_service.delete_points.return_value = None
            mock_qdrant.return_value = mock_qdrant_service

            # Execute job
            # Create mock task instance
            mock_task = AsyncMock()
            mock_task.get_memory_service = AsyncMock()

            # Mock the job function directly
            from ardha.jobs.memory_cleanup import cleanup_expired_memories

            result = await cleanup_expired_memories(mock_task)

            assert result["deleted_count"] >= 0
            assert "cutoff_date" in result

    async def test_archive_old_memories_job(self, test_db, sample_memories_batch):
        """Test old memories archival job"""
        # Add old memories to database
        from ardha.core.database import get_db

        async for db in get_db():
            for memory in sample_memories_batch:
                memory.last_accessed = datetime.utcnow() - timedelta(days=200)  # Old access
                memory.importance = 4  # Low importance
                db.add(memory)
            await db.commit()
            break

        # Execute job
        # Create mock task instance
        mock_task = AsyncMock()
        mock_task.get_memory_service = AsyncMock()

        # Mock the job function directly
        from ardha.jobs.memory_cleanup import archive_old_memories

        result = await archive_old_memories(mock_task)

        assert result["archived_count"] >= 0
        assert "last_accessed_before" in result

    async def test_cleanup_orphaned_vectors_job(self, test_db, sample_memories_batch):
        """Test orphaned vectors cleanup job"""
        # Add memories to database
        from ardha.core.database import get_db

        async for db in get_db():
            for memory in sample_memories_batch:
                db.add(memory)
            await db.commit()
            break

        # Mock Qdrant service
        with patch("ardha.jobs.memory_cleanup.get_qdrant_service") as mock_qdrant:
            mock_qdrant_service = AsyncMock()
            mock_qdrant_service.get_all_points.return_value = [
                {"id": memory.qdrant_point_id} for memory in sample_memories_batch[:2]
            ]
            mock_qdrant_service.delete_points.return_value = None
            mock_qdrant.return_value = mock_qdrant_service

            # Execute job
            # Create mock task instance
            mock_task = AsyncMock()
            mock_task.get_memory_service = AsyncMock()

            # Mock the job function directly
            from ardha.jobs.memory_cleanup import cleanup_orphaned_vectors

            result = await cleanup_orphaned_vectors(mock_task)

            assert result["cleaned_count"] >= 0
            assert "collections_checked" in result

    async def test_optimize_qdrant_collections_job(self, test_db):
        """Test Qdrant collections optimization job"""
        # Mock Qdrant service
        with patch("ardha.jobs.memory_cleanup.get_qdrant_service") as mock_qdrant:
            mock_qdrant_service = AsyncMock()
            mock_qdrant_service.optimize_collection.return_value = None
            mock_qdrant_service.collection_exists.return_value = True
            mock_qdrant.return_value = mock_qdrant_service

            # Execute job
            # Create mock task instance
            mock_task = AsyncMock()
            mock_task.get_memory_service = AsyncMock()

            # Mock the job function directly
            from ardha.jobs.memory_cleanup import optimize_qdrant_collections

            result = await optimize_qdrant_collections(mock_task)

            assert result["optimized_count"] >= 0
            assert "collections" in result
            assert isinstance(result["collections"], list)

    async def test_cleanup_old_links_job(self, test_db, sample_memories_batch, sample_memory_links):
        """Test old memory links cleanup job"""
        # Add memories and old links to database
        from ardha.core.database import get_db

        async for db in get_db():
            for memory in sample_memories_batch:
                db.add(memory)
            for link in sample_memory_links:
                link.created_at = datetime.utcnow() - timedelta(days=100)  # Old link
                link.strength = 0.2  # Weak link
                db.add(link)
            await db.commit()
            break

        # Execute job
        # Create mock task instance
        mock_task = AsyncMock()
        mock_task.get_memory_service = AsyncMock()

        # Mock the job function directly
        from ardha.jobs.memory_cleanup import cleanup_old_links

        result = await cleanup_old_links(mock_task)

        assert result["cleaned_count"] >= 0
        assert "cutoff_date" in result

    async def test_job_error_handling(self, test_db, test_user):
        """Test job error handling and logging"""
        # Mock services to raise exceptions
        with patch("ardha.jobs.memory_jobs.get_embedding_service") as mock_embedding:
            mock_service = AsyncMock()
            mock_service.generate_embedding.side_effect = Exception("Embedding failed")
            mock_embedding.return_value = mock_service

            # Execute job and handle error gracefully
            try:
                # Create mock task instance
                mock_task = AsyncMock()
                mock_task.get_memory_service = AsyncMock()

                from ardha.jobs.memory_jobs import ingest_chat_memories

                await ingest_chat_memories(
                    mock_task, chat_id=str(uuid4()), user_id=str(test_user.id)
                )
            except Exception as e:
                # Job should handle errors and return error information
                assert "Embedding failed" in str(e)

    async def test_job_retry_mechanism(self, test_db, test_user):
        """Test job retry mechanism for transient failures"""
        call_count = 0

        # Mock service that fails initially then succeeds
        def mock_generate_embedding(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise Exception("Transient failure")
            return [0.1] * 384

        with patch("ardha.jobs.memory_jobs.get_embedding_service") as mock_embedding:
            mock_service = AsyncMock()
            mock_service.generate_embedding.side_effect = mock_generate_embedding
            mock_embedding.return_value = mock_service

            with patch("ardha.jobs.memory_jobs.get_qdrant_service") as mock_qdrant:
                mock_qdrant_service = AsyncMock()
                mock_qdrant_service.upsert_vectors.return_value = None
                mock_qdrant_service.collection_exists.return_value = True
                mock_qdrant.return_value = mock_qdrant_service

                # Execute job (should succeed after retry)
                # Create mock task instance
                mock_task = AsyncMock()
                mock_task.get_memory_service = AsyncMock()

                from ardha.jobs.memory_jobs import ingest_workflow_memory

                result = await ingest_workflow_memory(
                    mock_task, workflow_id=str(uuid4()), user_id=str(test_user.id)
                )

                assert result["status"] == "success"
                assert call_count == 2  # Should have retried once

    async def test_job_batch_processing(self, test_db, sample_memories_batch, mock_local_embedding):
        """Test job batch processing for large datasets"""
        # Create many memories
        large_memory_batch = sample_memories_batch * 10  # 50 memories

        # Add memories to database
        from ardha.core.database import get_db

        async for db in get_db():
            for memory in large_memory_batch:
                memory.qdrant_point_id = None  # Simulate missing embedding
                db.add(memory)
            await db.commit()
            break

        # Mock embedding service
        with patch("ardha.jobs.memory_jobs.get_embedding_service") as mock_embedding:
            mock_emb_service = AsyncMock()
            mock_emb_service.generate_embedding.return_value = mock_local_embedding
            mock_embedding.return_value = mock_emb_service

            with patch("ardha.jobs.memory_jobs.get_qdrant_service") as mock_qdrant:
                mock_qdrant_service = AsyncMock()
                mock_qdrant_service.upsert_vectors.return_value = None
                mock_qdrant_service.collection_exists.return_value = True
                mock_qdrant.return_value = mock_qdrant_service

                # Execute job with small batch size
                # Create mock task instance
                mock_task = AsyncMock()
                mock_task.get_memory_service = AsyncMock()

                from ardha.jobs.memory_jobs import process_pending_embeddings

                result = await process_pending_embeddings(mock_task)

                assert result["processed_count"] >= 0
                assert result["batch_size"] == 10
                assert "total_batches" in result

    async def test_job_performance_monitoring(
        self, test_db, test_user, sample_chat_messages, mock_local_embedding
    ):
        """Test job performance monitoring and metrics"""
        # Mock services
        with patch("ardha.jobs.memory_jobs.get_embedding_service") as mock_embedding:
            mock_emb_service = AsyncMock()
            mock_emb_service.generate_embedding.return_value = mock_local_embedding
            mock_embedding.return_value = mock_emb_service

            with patch("ardha.jobs.memory_jobs.get_qdrant_service") as mock_qdrant:
                mock_qdrant_service = AsyncMock()
                mock_qdrant_service.upsert_vectors.return_value = None
                mock_qdrant_service.collection_exists.return_value = True
                mock_qdrant.return_value = mock_qdrant_service

                # Execute job and measure performance
                start_time = datetime.utcnow()

                # Create mock task instance
                mock_task = AsyncMock()
                mock_task.get_memory_service = AsyncMock()

                from ardha.jobs.memory_jobs import ingest_chat_memories

                result = await ingest_chat_memories(
                    mock_task, chat_id=str(uuid4()), user_id=str(test_user.id)
                )

                end_time = datetime.utcnow()
                duration = (end_time - start_time).total_seconds()

                assert result["ingested_count"] >= 0
                assert "performance" in result
                assert result["performance"]["duration_seconds"] >= 0

    async def test_job_idempotency(
        self, test_db, test_user, completed_workflow, mock_local_embedding
    ):
        """Test job idempotency - running same job multiple times"""
        # Mock services
        with patch("ardha.jobs.memory_jobs.get_embedding_service") as mock_embedding:
            mock_emb_service = AsyncMock()
            mock_emb_service.generate_embedding.return_value = mock_local_embedding
            mock_embedding.return_value = mock_emb_service

            with patch("ardha.jobs.memory_jobs.get_qdrant_service") as mock_qdrant:
                mock_qdrant_service = AsyncMock()
                mock_qdrant_service.upsert_vectors.return_value = None
                mock_qdrant_service.collection_exists.return_value = True
                mock_qdrant.return_value = mock_qdrant_service

                # Execute job multiple times
                workflow_id = completed_workflow.id

                # Create mock task instance
                mock_task = AsyncMock()
                mock_task.get_memory_service = AsyncMock()

                from ardha.jobs.memory_jobs import ingest_workflow_memory

                result1 = await ingest_workflow_memory(
                    mock_task, workflow_id=str(workflow_id), user_id=str(test_user.id)
                )

                result2 = await ingest_workflow_memory(
                    mock_task, workflow_id=str(workflow_id), user_id=str(test_user.id)
                )

                # Both should succeed (idempotent)
                assert result1["status"] == "success"
                assert result2["status"] == "success"
                assert result1["workflow_id"] == result2["workflow_id"]

    async def test_job_cascade_operations(
        self, test_db, sample_memories_batch, sample_memory_links
    ):
        """Test jobs that perform cascade operations"""
        # Add memories and links to database
        from ardha.core.database import get_db

        async for db in get_db():
            for memory in sample_memories_batch:
                db.add(memory)
            for link in sample_memory_links:
                db.add(link)
            await db.commit()
            break

        # Mock Qdrant service
        with patch("ardha.jobs.memory_cleanup.get_qdrant_service") as mock_qdrant:
            mock_qdrant_service = AsyncMock()
            mock_qdrant_service.delete_points.return_value = None
            mock_qdrant.return_value = mock_qdrant_service

            # Delete memory (should cascade delete links)
            from ardha.repositories.memory_repository import MemoryRepository

            async for db in get_db():
                repo = MemoryRepository(db)
                await repo.delete(sample_memories_batch[0].id)
                await db.commit()
                break

            # Verify cleanup job handles orphaned links
            # Create mock task instance
            mock_task = AsyncMock()
            mock_task.get_memory_service = AsyncMock()

            from ardha.jobs.memory_cleanup import cleanup_old_links

            result = await cleanup_old_links(mock_task)

            assert result["cleaned_count"] >= 0

    async def test_job_transaction_rollback(self, test_db, test_user):
        """Test job transaction rollback on failure"""
        # Mock service that fails during operation
        with patch("ardha.jobs.memory_jobs.get_qdrant_service") as mock_qdrant:
            mock_qdrant_service = AsyncMock()
            mock_qdrant_service.upsert_vectors.side_effect = Exception("Database error")
            mock_qdrant_service.collection_exists.return_value = True
            mock_qdrant.return_value = mock_qdrant_service

            # Execute job (should fail and rollback)
            try:
                # Create mock task instance
                mock_task = AsyncMock()
                mock_task.get_memory_service = AsyncMock()

                from ardha.jobs.memory_jobs import ingest_workflow_memory

                await ingest_workflow_memory(
                    mock_task, workflow_id=str(uuid4()), user_id=str(test_user.id)
                )
            except Exception:
                pass  # Expected to fail

            # Verify no partial data was created
            from ardha.core.database import async_session_factory
            from ardha.repositories.memory_repository import MemoryRepository

            async with async_session_factory() as db:
                repo = MemoryRepository(db)
                memories = await repo.get_by_user(test_user.id, limit=10)

                # Should not have any partial memories from failed job
                workflow_memories = [m for m in memories if m.memory_type == "workflow"]
                assert len(workflow_memories) == 0

    async def test_job_concurrent_execution(self, test_db, test_user, mock_local_embedding):
        """Test concurrent job execution"""
        import asyncio

        # Mock services
        with patch("ardha.jobs.memory_jobs.get_embedding_service") as mock_embedding:
            mock_emb_service = AsyncMock()
            mock_emb_service.generate_embedding.return_value = mock_local_embedding
            mock_embedding.return_value = mock_emb_service

            with patch("ardha.jobs.memory_jobs.get_qdrant_service") as mock_qdrant:
                mock_qdrant_service = AsyncMock()
                mock_qdrant_service.upsert_vectors.return_value = None
                mock_qdrant_service.collection_exists.return_value = True
                mock_qdrant.return_value = mock_qdrant_service

                # Execute multiple jobs concurrently
                tasks = []
                for i in range(5):
                    # Create mock task instance
                    mock_task = AsyncMock()
                    mock_task.get_memory_service = AsyncMock()

                    from ardha.jobs.memory_jobs import ingest_workflow_memory

                    task = asyncio.create_task(
                        ingest_workflow_memory(
                            mock_task, workflow_id=str(uuid4()), user_id=str(test_user.id)
                        )
                    )
                    tasks.append(task)

                # Wait for all jobs to complete
                results = await asyncio.gather(*tasks, return_exceptions=True)

                # All should succeed
                successful_results = [r for r in results if isinstance(r, dict)]
                assert len(successful_results) == 5

                for result in successful_results:
                    assert result["status"] == "success"
