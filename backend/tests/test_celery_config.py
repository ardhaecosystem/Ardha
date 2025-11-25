"""
Test Celery configuration and basic functionality.
"""

from unittest.mock import MagicMock, patch

from ardha.core.celery_app import celery_app


class TestCeleryConfig:
    """Test Celery configuration."""

    def test_celery_app_exists(self):
        """Test that Celery app is properly configured."""
        assert celery_app is not None
        assert celery_app.main == "ardha"

    def test_celery_tasks_registered(self):
        """Test that tasks are properly registered."""
        # Import tasks to register them
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

        # Check that memory jobs are registered
        assert "ardha.jobs.memory_jobs.ingest_chat_memories" in celery_app.tasks
        assert "ardha.jobs.memory_jobs.ingest_workflow_memory" in celery_app.tasks
        assert "ardha.jobs.memory_jobs.process_pending_embeddings" in celery_app.tasks
        assert "ardha.jobs.memory_jobs.build_memory_relationships" in celery_app.tasks
        assert "ardha.jobs.memory_jobs.optimize_memory_importance" in celery_app.tasks

        # Check that cleanup jobs are registered
        assert "ardha.jobs.memory_cleanup.cleanup_expired_memories" in celery_app.tasks
        assert "ardha.jobs.memory_cleanup.archive_old_memories" in celery_app.tasks
        assert "ardha.jobs.memory_cleanup.cleanup_orphaned_vectors" in celery_app.tasks
        assert "ardha.jobs.memory_cleanup.optimize_qdrant_collections" in celery_app.tasks
        assert "ardha.jobs.memory_cleanup.cleanup_old_links" in celery_app.tasks

    @patch("ardha.core.celery_app.celery_app.send_task")
    def test_send_task_functionality(self, mock_send_task):
        """Test that send_task works correctly."""
        mock_send_task.return_value = MagicMock()

        # Test sending a task
        result = celery_app.send_task(
            "ardha.jobs.memory_jobs.ingest_chat_memories", args=["test-chat-id", "test-user-id"]
        )

        # Verify send_task was called with correct arguments
        mock_send_task.assert_called_once_with(
            "ardha.jobs.memory_jobs.ingest_chat_memories", args=["test-chat-id", "test-user-id"]
        )
        assert result is not None

    def test_celery_configuration(self):
        """Test Celery configuration settings."""
        # Test broker URL is set
        assert celery_app.conf.broker_url is not None

        # Test result backend is set
        assert celery_app.conf.result_backend is not None

        # Test task serializer
        assert celery_app.conf.task_serializer == "json"
        assert celery_app.conf.result_serializer == "json"
        assert celery_app.conf.accept_content == ["json"]

        # Test timezone
        assert celery_app.conf.timezone == "UTC"

        # Test enable_utc
        assert celery_app.conf.enable_utc is True

    def test_task_routes(self):
        """Test that task routing is configured."""
        routes = celery_app.conf.task_routes

        # Memory jobs should go to memory queue
        assert "ardha.jobs.memory_jobs.*" in routes
        assert routes["ardha.jobs.memory_jobs.*"]["queue"] == "memory"

        # Cleanup jobs should go to cleanup queue
        assert "ardha.jobs.memory_cleanup.*" in routes
        assert routes["ardha.jobs.memory_cleanup.*"]["queue"] == "cleanup"

    def test_worker_configuration(self):
        """Test worker configuration."""
        # Test worker concurrency
        assert celery_app.conf.worker_concurrency == 2

        # Test worker prefetch
        assert celery_app.conf.worker_prefetch_multiplier == 1

        # Test task acks late
        assert celery_app.conf.task_acks_late is True

        # Test worker disable rate limits
        assert celery_app.conf.worker_disable_rate_limits is True

    def test_task_annotations(self):
        """Test task annotations."""
        annotations = celery_app.conf.task_annotations

        # Memory tasks should have time limit
        assert "ardha.jobs.memory_jobs.*" in annotations
        assert annotations["ardha.jobs.memory_jobs.*"]["time_limit"] == 300

        # Cleanup tasks should have time limit
        assert "ardha.jobs.memory_cleanup.*" in annotations
        assert annotations["ardha.jobs.memory_cleanup.*"]["time_limit"] == 600

    def test_beat_schedule(self):
        """Test beat schedule configuration."""
        beat_schedule = celery_app.conf.beat_schedule

        # Check that scheduled tasks are configured
        assert "cleanup-expired-memories" in beat_schedule
        assert (
            beat_schedule["cleanup-expired-memories"]["task"]
            == "ardha.jobs.memory_cleanup.cleanup_expired_memories"
        )
        # Check that it's a crontab schedule (not seconds)
        from celery.schedules import crontab

        assert isinstance(beat_schedule["cleanup-expired-memories"]["schedule"], crontab)

        assert "archive-old-memories" in beat_schedule
        assert (
            beat_schedule["archive-old-memories"]["task"]
            == "ardha.jobs.memory_cleanup.archive_old_memories"
        )
        assert isinstance(beat_schedule["archive-old-memories"]["schedule"], crontab)

        assert "optimize-memory-importance" in beat_schedule
        assert (
            beat_schedule["optimize-memory-importance"]["task"]
            == "ardha.jobs.memory_jobs.optimize_memory_importance"
        )
        assert isinstance(beat_schedule["optimize-memory-importance"]["schedule"], crontab)

        assert "process-pending-embeddings" in beat_schedule
        assert (
            beat_schedule["process-pending-embeddings"]["task"]
            == "ardha.jobs.memory_jobs.process_pending_embeddings"
        )
        assert isinstance(beat_schedule["process-pending-embeddings"]["schedule"], crontab)

        assert "build-memory-relationships" in beat_schedule
        assert (
            beat_schedule["build-memory-relationships"]["task"]
            == "ardha.jobs.memory_jobs.build_memory_relationships"
        )
        assert isinstance(beat_schedule["build-memory-relationships"]["schedule"], crontab)
