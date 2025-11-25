"""
Manual testing script for background jobs.

Run this to manually test each job execution.
This file is temporary and can be deleted after validation.

Usage:
    cd backend
    poetry run python -m tests.manual_job_test
"""

import asyncio
import logging
from datetime import datetime, timezone

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


async def test_git_jobs():
    """Test Git-related jobs."""
    logger.info("=" * 70)
    logger.info("=== Testing Git Jobs ===")
    logger.info("=" * 70)

    try:
        from ardha.jobs.git_jobs import ingest_commit_to_memory

        logger.info("✅ git_jobs module imported successfully")
        logger.info("   - ingest_commit_to_memory: %s", ingest_commit_to_memory)

    except ImportError as e:
        logger.error(f"❌ Failed to import git_jobs: {e}")
        return

    logger.info("")


async def test_task_jobs():
    """Test Task-related jobs."""
    logger.info("=" * 70)
    logger.info("=== Testing Task Jobs ===")
    logger.info("=" * 70)

    try:
        from ardha.jobs.task_jobs import calculate_team_velocity, send_overdue_task_reminders

        logger.info("✅ task_jobs module imported successfully")

        # Test velocity calculation
        logger.info("\n📊 Testing calculate_team_velocity...")
        try:
            result = await calculate_team_velocity()
            logger.info(f"   ✅ SUCCESS: {result['success']}")
            logger.info("   📈 Metrics:")
            if "metrics" in result:
                for key, value in result["metrics"].items():
                    logger.info(f"      - {key}: {value}")
        except Exception as e:
            logger.error(f"   ❌ FAILED: {e}")

        # Test reminders
        logger.info("\n📬 Testing send_overdue_task_reminders...")
        try:
            result = await send_overdue_task_reminders()
            logger.info(f"   ✅ SUCCESS: {result['success']}")
            logger.info(f"   📧 Overdue tasks: {result.get('overdue_tasks_count', 0)}")
            logger.info(f"   📨 Reminders sent: {result.get('reminders_sent', 0)}")
        except Exception as e:
            logger.error(f"   ❌ FAILED: {e}")

    except ImportError as e:
        logger.error(f"❌ Failed to import task_jobs: {e}")

    logger.info("")


async def test_cost_jobs():
    """Test Cost & Analytics jobs."""
    logger.info("=" * 70)
    logger.info("=== Testing Cost Jobs ===")
    logger.info("=" * 70)

    try:
        from ardha.jobs.cost_jobs import (
            analyze_ai_usage_patterns,
            calculate_project_analytics,
            generate_daily_cost_report,
        )

        logger.info("✅ cost_jobs module imported successfully")

        # Test daily report
        logger.info("\n💰 Testing generate_daily_cost_report...")
        try:
            result = await generate_daily_cost_report()
            logger.info(f"   ✅ SUCCESS: {result['success']}")
            if "report" in result:
                summary = result["report"]["summary"]
                logger.info(f"   💵 Total cost: ${summary['total_cost']:.4f}")
                logger.info(f"   📊 Total operations: {summary['total_operations']}")
                logger.info(f"   🎯 Total tokens: {summary['total_tokens']}")
        except Exception as e:
            logger.error(f"   ❌ FAILED: {e}")

        # Test pattern analysis
        logger.info("\n📈 Testing analyze_ai_usage_patterns...")
        try:
            result = await analyze_ai_usage_patterns()
            logger.info(f"   ✅ SUCCESS: {result['success']}")
            if "analysis" in result:
                analysis = result["analysis"]
                logger.info(f"   📅 Average daily cost: ${analysis['average_daily_cost']:.4f}")
                logger.info(f"   🔥 High-cost ops: {len(analysis['high_cost_operations'])}")
                logger.info(f"   💡 Recommendations: {len(analysis['recommendations'])}")
        except Exception as e:
            logger.error(f"   ❌ FAILED: {e}")

        # Test project analytics
        logger.info("\n📊 Testing calculate_project_analytics...")
        try:
            result = await calculate_project_analytics()
            logger.info(f"   ✅ SUCCESS: {result['success']}")
            logger.info(f"   🗂️  Project count: {result.get('project_count', 0)}")
            if result.get("analytics"):
                logger.info(f"   📈 Analytics entries: {len(result['analytics'])}")
        except Exception as e:
            logger.error(f"   ❌ FAILED: {e}")

    except ImportError as e:
        logger.error(f"❌ Failed to import cost_jobs: {e}")

    logger.info("")


async def test_maintenance_jobs():
    """Test Maintenance jobs."""
    logger.info("=" * 70)
    logger.info("=== Testing Maintenance Jobs ===")
    logger.info("=" * 70)

    try:
        from ardha.jobs.maintenance_jobs import backup_database, cleanup_old_sessions

        logger.info("✅ maintenance_jobs module imported successfully")

        # Test session cleanup
        logger.info("\n🧹 Testing cleanup_old_sessions...")
        try:
            result = await cleanup_old_sessions()
            logger.info(f"   ✅ SUCCESS: {result['success']}")
            if "statistics" in result:
                stats = result["statistics"]
                logger.info(f"   🔍 Keys checked: {stats['keys_checked']}")
                logger.info(f"   🗑️  Keys deleted: {stats['keys_deleted']}")
                if "by_pattern" in stats:
                    logger.info(f"   📋 By pattern: {stats['by_pattern']}")
        except Exception as e:
            logger.error(f"   ❌ FAILED: {e}")

        # Test backup (note: this is sync function)
        logger.info("\n💾 Testing backup_database...")
        logger.info("   ⚠️  NOTE: Backup requires pg_dump, may fail in test environment")
        try:
            result = backup_database()
            if result.get("success"):
                logger.info("   ✅ SUCCESS")
                logger.info(f"   📦 Backup file: {result.get('backup_file')}")
                logger.info(f"   📏 Size: {result.get('backup_size_mb', 0):.2f} MB")
            else:
                logger.warning(f"   ⚠️  FAILED: {result.get('error')}")
                logger.info("   💡 This is expected if pg_dump is not available")
        except Exception as e:
            logger.warning(f"   ⚠️  FAILED: {e}")
            logger.info("   💡 This is expected if pg_dump is not available")

    except ImportError as e:
        logger.error(f"❌ Failed to import maintenance_jobs: {e}")

    logger.info("")


def test_celery_config():
    """Test Celery configuration."""
    logger.info("=" * 70)
    logger.info("=== Testing Celery Configuration ===")
    logger.info("=" * 70)

    try:
        from ardha.core.celery_app import celery_app

        logger.info("✅ Celery app imported successfully")

        # Check task routes
        routes = celery_app.conf.task_routes
        logger.info(f"\n🔀 Task routes: {len(routes)} configured")
        for pattern, config in routes.items():
            queue = config.get("queue", "default")
            logger.info(f"   - {pattern:<40} → {queue}")

        # Check beat schedule
        schedule = celery_app.conf.beat_schedule
        logger.info(f"\n⏰ Beat schedule: {len(schedule)} tasks")
        for name, config in schedule.items():
            task = config["task"]
            logger.info(f"   - {name:<35} → {task}")

        # Check registered tasks
        tasks = [t for t in celery_app.tasks.keys() if not t.startswith("celery.")]
        logger.info(f"\n📋 Registered tasks: {len(tasks)}")

        # Group tasks by category
        git_tasks = [t for t in tasks if t.startswith("git.")]
        task_tasks = [t for t in tasks if t.startswith("tasks.")]
        cost_tasks = [t for t in tasks if t.startswith("cost.")]
        maintenance_tasks = [t for t in tasks if t.startswith("maintenance.")]
        memory_tasks = [
            t for t in tasks if t.startswith("ardha.jobs.memory") or t.startswith("memory.")
        ]

        if git_tasks:
            logger.info(f"\n   🔧 Git jobs ({len(git_tasks)}):")
            for task in sorted(git_tasks):
                logger.info(f"      - {task}")

        if task_tasks:
            logger.info(f"\n   ✅ Task jobs ({len(task_tasks)}):")
            for task in sorted(task_tasks):
                logger.info(f"      - {task}")

        if cost_tasks:
            logger.info(f"\n   💰 Cost jobs ({len(cost_tasks)}):")
            for task in sorted(cost_tasks):
                logger.info(f"      - {task}")

        if maintenance_tasks:
            logger.info(f"\n   🛠️  Maintenance jobs ({len(maintenance_tasks)}):")
            for task in sorted(maintenance_tasks):
                logger.info(f"      - {task}")

        if memory_tasks:
            logger.info("\n   🧠 Memory jobs (%s):", len(memory_tasks))
            for task in sorted(memory_tasks):
                logger.info("      - %s", task)

        # Check task annotations
        logger.info("\n⚙️  Task annotations:")
        annotations = celery_app.conf.task_annotations
        for pattern, config in annotations.items():
            logger.info(f"   - {pattern}:")
            if "rate_limit" in config:
                logger.info(f"      Rate limit: {config['rate_limit']}")
            if "time_limit" in config:
                logger.info(f"      Time limit: {config['time_limit']}s")

        logger.info("\n✅ Celery configuration validated successfully")

    except ImportError as e:
        logger.error(f"❌ Failed to import celery_app: {e}")

    logger.info("")


async def main():
    """Run all manual tests."""
    logger.info("\n")
    logger.info("🚀" * 35)
    logger.info("🚀  ARDHA BACKGROUND JOBS MANUAL TESTING")
    logger.info("🚀" * 35)
    logger.info(f"\n⏰ Started at: {datetime.now(timezone.utc).isoformat()}")
    logger.info("")

    # Test configuration first (synchronous)
    test_celery_config()

    # Test each job category (asynchronous)
    await test_task_jobs()
    await test_cost_jobs()
    await test_maintenance_jobs()
    await test_git_jobs()

    # Summary
    logger.info("=" * 70)
    logger.info("📊 MANUAL TESTING SUMMARY")
    logger.info("=" * 70)
    logger.info("")
    logger.info("✅ Completed Tests:")
    logger.info("   - Celery configuration validation")
    logger.info("   - Task jobs (calculate_team_velocity, send_overdue_task_reminders)")
    logger.info("   - Cost jobs (daily_report, usage_patterns, project_analytics)")
    logger.info("   - Maintenance jobs (cleanup_sessions, backup_database)")
    logger.info("   - Git jobs (module structure validation)")
    logger.info("")
    logger.info("📝 Next Steps:")
    logger.info("   1. Review any errors above")
    logger.info("   2. Run: poetry run pytest tests/integration/test_background_jobs.py -v")
    logger.info("   3. Fix any failing tests")
    logger.info("   4. Run: poetry run flake8 tests/")
    logger.info("   5. Run: poetry run black tests/")
    logger.info("")
    logger.info("⏰ Completed at: " + datetime.now(timezone.utc).isoformat())
    logger.info("=" * 70)
    logger.info("")


if __name__ == "__main__":
    asyncio.run(main())
