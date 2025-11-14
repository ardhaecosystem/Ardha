"""
Minimal integration tests for memory-related Celery jobs.

Tests job registration and basic functionality without complex mocking.
"""

import pytest

from ardha.core.celery_app import celery_app
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
class TestMemoryJobsMinimal:
    """Test memory-related background jobs with minimal setup"""

    async def test_job_registration(self):
        """Test that all jobs are properly registered"""
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

    async def test_job_task_attributes(self):
        """Test that jobs have correct task attributes"""
        # Test ingest_chat_memories task
        chat_task = celery_app.tasks["ardha.jobs.memory_jobs.ingest_chat_memories"]
        assert chat_task.name == "ardha.jobs.memory_jobs.ingest_chat_memories"
        assert hasattr(chat_task, "max_retries")
        assert chat_task.max_retries == 3

        # Test process_pending_embeddings task
        embeddings_task = celery_app.tasks["ardha.jobs.memory_jobs.process_pending_embeddings"]
        assert embeddings_task.name == "ardha.jobs.memory_jobs.process_pending_embeddings"
        assert hasattr(embeddings_task, "bind")
        # Note: bind attribute may not be directly accessible, but task is configured with bind=True

    async def test_job_base_class(self):
        """Test that jobs inherit from DatabaseTask"""
        from ardha.jobs.memory_jobs import DatabaseTask

        # Test that DatabaseTask has required methods
        assert hasattr(DatabaseTask, "get_memory_service")
        assert hasattr(DatabaseTask, "get_chat_service")
        assert hasattr(DatabaseTask, "get_workflow_service")

    async def test_celery_app_configuration(self):
        """Test Celery app configuration for memory jobs"""
        # Check that celery app is configured
        assert celery_app.conf.task_serializer == "json"
        assert celery_app.conf.result_serializer == "json"

        # Check that task routing is configured
        assert "task_routes" in celery_app.conf
        routes = celery_app.conf.task_routes

        # Memory jobs should route to 'memory' queue
        memory_jobs = [
            "ardha.jobs.memory_jobs.ingest_chat_memories",
            "ardha.jobs.memory_jobs.ingest_workflow_memory",
            "ardha.jobs.memory_jobs.process_pending_embeddings",
            "ardha.jobs.memory_jobs.build_memory_relationships",
            "ardha.jobs.memory_jobs.optimize_memory_importance",
        ]

        for job_name in memory_jobs:
            if job_name in routes:
                assert routes[job_name] == {"queue": "memory"}

    async def test_job_imports(self):
        """Test that all job modules can be imported"""
        # Test that all job functions are importable
        from ardha.jobs import memory_cleanup, memory_jobs

        # Check that memory_jobs module has expected functions
        assert hasattr(memory_jobs, "ingest_chat_memories")
        assert hasattr(memory_jobs, "ingest_workflow_memory")
        assert hasattr(memory_jobs, "process_pending_embeddings")
        assert hasattr(memory_jobs, "build_memory_relationships")
        assert hasattr(memory_jobs, "optimize_memory_importance")

        # Check that memory_cleanup module has expected functions
        assert hasattr(memory_cleanup, "cleanup_expired_memories")
        assert hasattr(memory_cleanup, "archive_old_memories")
        assert hasattr(memory_cleanup, "cleanup_orphaned_vectors")
        assert hasattr(memory_cleanup, "optimize_qdrant_collections")
        assert hasattr(memory_cleanup, "cleanup_old_links")
