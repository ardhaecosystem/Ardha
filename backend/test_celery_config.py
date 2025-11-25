#!/usr/bin/env python3
"""
Simple test script for Celery configuration.

This script tests the Celery app configuration without importing
the full application modules to avoid SQLAlchemy conflicts.
"""

import logging
import os
import sys

# Add the src directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def test_celery_import():
    """Test that Celery app can be imported."""
    logger.info("Testing Celery app import...")

    try:
        from ardha.core.celery_app import celery_app

        assert celery_app is not None, "Celery app not initialized"
        logger.info("✅ Celery app import test passed")
        return celery_app
    except Exception as e:
        logger.error(f"❌ Celery app import test failed: {e}")
        raise


def test_celery_configuration(celery_app):
    """Test Celery app configuration."""
    logger.info("Testing Celery app configuration...")

    try:
        # Check basic configuration
        assert celery_app.conf.task_serializer == "json", "Task serializer not configured"
        assert celery_app.conf.result_serializer == "json", "Result serializer not configured"
        assert celery_app.conf.timezone == "UTC", "Timezone not configured"
        assert celery_app.conf.enable_utc is True, "UTC not enabled"

        # Check worker configuration
        assert celery_app.conf.worker_concurrency == 2, "Worker concurrency not configured"
        assert celery_app.conf.task_time_limit == 3600, "Task time limit not configured"
        assert celery_app.conf.task_soft_time_limit == 3300, "Task soft time limit not configured"

        logger.info("✅ Celery app configuration test passed")

    except Exception as e:
        logger.error(f"❌ Celery app configuration test failed: {e}")
        raise


def test_beat_schedule(celery_app):
    """Test that beat schedule is configured."""
    logger.info("Testing beat schedule...")

    try:
        beat_schedule = celery_app.conf.beat_schedule
        assert beat_schedule is not None, "Beat schedule not configured"

        expected_tasks = [
            "cleanup-expired-memories",
            "archive-old-memories",
            "optimize-memory-importance",
            "process-pending-embeddings",
            "build-memory-relationships",
        ]

        for task_name in expected_tasks:
            assert task_name in beat_schedule, f"Task {task_name} not in beat schedule"
            # Check that each task has a schedule and task name
            task_config = beat_schedule[task_name]
            assert "task" in task_config, f"Task {task_name} missing task name"
            assert "schedule" in task_config, f"Task {task_name} missing schedule"

        logger.info("✅ Beat schedule test passed")

    except Exception as e:
        logger.error(f"❌ Beat schedule test failed: {e}")
        raise


def test_task_routing(celery_app):
    """Test that task routing is configured."""
    logger.info("Testing task routing...")

    try:
        task_routes = celery_app.conf.task_routes
        assert task_routes is not None, "Task routes not configured"

        expected_routes = {
            "ardha.jobs.memory_jobs.*": {"queue": "memory"},
            "ardha.jobs.memory_cleanup.*": {"queue": "cleanup"},
        }

        for pattern, route in expected_routes.items():
            assert pattern in task_routes, f"Route pattern {pattern} not found"
            assert task_routes[pattern] == route, f"Route for {pattern} not configured correctly"

        logger.info("✅ Task routing test passed")

    except Exception as e:
        logger.error(f"❌ Task routing test failed: {e}")
        raise


def test_task_annotations(celery_app):
    """Test that task annotations are configured."""
    logger.info("Testing task annotations...")

    try:
        task_annotations = celery_app.conf.task_annotations
        assert task_annotations is not None, "Task annotations not configured"

        expected_annotations = {
            "ardha.jobs.memory_jobs.*": {"time_limit": 300},  # 5 minutes
            "ardha.jobs.memory_cleanup.*": {"time_limit": 600},  # 10 minutes
        }

        for pattern, annotation in expected_annotations.items():
            assert pattern in task_annotations, f"Annotation pattern {pattern} not found"
            assert (
                task_annotations[pattern] == annotation
            ), f"Annotation for {pattern} not configured correctly"

        logger.info("✅ Task annotations test passed")

    except Exception as e:
        logger.error(f"❌ Task annotations test failed: {e}")
        raise


def test_debug_task(celery_app):
    """Test debug task registration."""
    logger.info("Testing debug task registration...")

    try:
        # Check if debug task is registered
        debug_task_name = "ardha.core.celery_app.debug_task"
        assert debug_task_name in celery_app.tasks, f"Debug task {debug_task_name} not registered"

        debug_task = celery_app.tasks[debug_task_name]
        assert debug_task is not None, "Debug task not found"

        logger.info("✅ Debug task registration test passed")

    except Exception as e:
        logger.error(f"❌ Debug task registration test failed: {e}")
        raise


def run_all_tests():
    """Run all tests."""
    logger.info("🚀 Starting Celery configuration tests...")

    try:
        # Test import first
        celery_app = test_celery_import()

        # Run configuration tests
        test_celery_configuration(celery_app)
        test_beat_schedule(celery_app)
        test_task_routing(celery_app)
        test_task_annotations(celery_app)
        test_debug_task(celery_app)

        logger.info("🎉 All Celery configuration tests passed!")
        logger.info("📋 Configuration Summary:")
        logger.info(f"   - Task Serializer: {celery_app.conf.task_serializer}")
        logger.info(f"   - Timezone: {celery_app.conf.timezone}")
        logger.info(f"   - Worker Concurrency: {celery_app.conf.worker_concurrency}")
        logger.info(f"   - Beat Schedule Tasks: {len(celery_app.conf.beat_schedule)}")
        logger.info(f"   - Task Routes: {len(celery_app.conf.task_routes)}")
        logger.info(f"   - Task Annotations: {len(celery_app.conf.task_annotations)}")

        return True

    except Exception as e:
        logger.error(f"❌ Tests failed: {e}")
        return False


if __name__ == "__main__":
    success = run_all_tests()
    exit(0 if success else 1)
