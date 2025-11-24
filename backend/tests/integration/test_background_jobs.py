"""
Integration tests for background jobs.

Tests all Week 11 background jobs with real database and Redis.
Validates job execution, error handling, and integration with services.
"""

from datetime import datetime, timedelta, timezone
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from ardha.jobs.cost_jobs import (
    analyze_ai_usage_patterns,
    calculate_project_analytics,
    generate_daily_cost_report,
)
from ardha.jobs.git_jobs import ingest_commit_to_memory
from ardha.jobs.maintenance_jobs import backup_database, cleanup_old_sessions
from ardha.jobs.task_jobs import calculate_team_velocity, send_overdue_task_reminders
from ardha.models.ai_usage import AIOperation, AIUsage
from ardha.models.git_commit import GitCommit
from ardha.models.task import Task


@pytest.mark.asyncio
class TestGitJobs:
    """Test Git-related background jobs."""

    async def test_ingest_commit_to_memory_success(
        self,
        test_db,
        test_user,
        test_project,
    ):
        """Test successful commit memory ingestion."""
        # Create test commit with meaningful message
        commit = GitCommit(
            id=uuid4(),
            project_id=test_project["id"],
            sha="abc123def456789012345678901234567890abcd",
            short_sha="abc123d",
            message=(
                "refactor: improved authentication flow\n\n"
                "Decided to use JWT tokens instead of sessions\n"
                "Closes #123, fixes TAS-001"
            ),
            author_name=test_user["user"]["full_name"],
            author_email=test_user["user"]["email"],
            committed_at=datetime.now(timezone.utc),
            branch="feature/auth",
            files_changed=3,
            insertions=45,
            deletions=12,
            ardha_user_id=test_user["user"]["id"],
        )
        test_db.add(commit)
        await test_db.commit()

        # Mock memory service to avoid Qdrant dependency
        with patch("ardha.jobs.git_jobs.MemoryService") as mock_service:
            mock_memory = MagicMock()
            mock_memory.id = uuid4()
            mock_service.return_value.create_memory = AsyncMock(return_value=mock_memory)

            # Execute job
            result = await ingest_commit_to_memory(str(commit.id))

            # Verify result
            assert result["success"] is True
            assert result["commit_id"] == str(commit.id)
            assert "memory_id" in result
            assert "insights" in result

            # Verify insights extracted
            insights = result["insights"]
            assert "technical_decisions" in insights
            assert "code_changes" in insights
            assert "related_tasks" in insights

            # Verify task references found
            assert len(insights["related_tasks"]) >= 2  # Should find #123 and TAS-001

            # Verify memory service called
            mock_service.return_value.create_memory.assert_called_once()

    async def test_ingest_commit_to_memory_not_found(self):
        """Test commit ingestion with non-existent commit."""
        fake_id = str(uuid4())

        with pytest.raises(ValueError, match=f"Commit {fake_id} not found"):
            await ingest_commit_to_memory(fake_id)


@pytest.mark.asyncio
class TestTaskJobs:
    """Test Task-related background jobs."""

    async def test_calculate_team_velocity_with_data(
        self,
        test_db,
        test_completed_tasks,
    ):
        """Test team velocity calculation with completed tasks."""
        # Execute job
        result = await calculate_team_velocity()

        # Verify result structure
        assert result["success"] is True
        assert "metrics" in result

        metrics = result["metrics"]
        assert "calculated_at" in metrics
        assert "tasks_completed_this_week" in metrics
        assert "tasks_completed_this_month" in metrics
        assert "average_completion_days" in metrics
        assert "velocity_current_week" in metrics
        assert "velocity_4_week_average" in metrics
        assert "trend" in metrics
        assert "trend_percentage" in metrics

        # Verify counts are reasonable
        assert metrics["tasks_completed_this_week"] >= 0
        assert metrics["tasks_completed_this_month"] >= 0
        assert metrics["average_completion_days"] >= 0

    async def test_calculate_team_velocity_no_data(self, test_db):
        """Test team velocity with no completed tasks."""
        # Execute job
        result = await calculate_team_velocity()

        # Should still succeed with zero values
        assert result["success"] is True
        assert result["metrics"]["tasks_completed_this_week"] == 0
        assert result["metrics"]["velocity_current_week"] == 0

    async def test_send_overdue_task_reminders_success(
        self,
        test_db,
        test_overdue_tasks,
    ):
        """Test overdue task reminder sending."""
        # Execute job
        result = await send_overdue_task_reminders()

        # Verify result
        assert result["success"] is True
        assert "overdue_tasks_count" in result
        assert "reminders_sent" in result
        assert "timestamp" in result

        # Should find our 3 overdue tasks
        assert result["overdue_tasks_count"] >= 3
        assert result["reminders_sent"] >= 1  # At least 1 user

    async def test_send_overdue_task_reminders_no_tasks(self, test_db):
        """Test reminders when no overdue tasks exist."""
        # Execute job
        result = await send_overdue_task_reminders()

        # Should succeed with zero counts
        assert result["success"] is True
        assert result["overdue_tasks_count"] == 0
        assert result["reminders_sent"] == 0


@pytest.mark.asyncio
class TestCostJobs:
    """Test Cost & Analytics background jobs."""

    async def test_generate_daily_cost_report_with_data(
        self,
        test_db,
        test_ai_usage_yesterday,
    ):
        """Test daily cost report generation with data."""
        # Execute job
        result = await generate_daily_cost_report()

        # Verify result structure
        assert result["success"] is True
        assert "report" in result

        report = result["report"]
        assert "date" in report
        assert "generated_at" in report
        assert "summary" in report
        assert "operation_breakdown" in report
        assert "model_breakdown" in report
        assert "user_breakdown" in report
        assert "project_breakdown" in report

        # Verify summary
        summary = report["summary"]
        assert summary["total_cost"] > 0  # Should have some cost from fixtures
        assert summary["total_operations"] >= 3  # We created 3 usage records
        assert summary["total_tokens"] > 0

    async def test_generate_daily_cost_report_no_data(self, test_db):
        """Test daily cost report with no usage data."""
        # Execute job
        result = await generate_daily_cost_report()

        # Should succeed with zero values
        assert result["success"] is True
        assert result["report"]["summary"]["total_cost"] == 0
        assert result["report"]["summary"]["total_operations"] == 0

    async def test_analyze_ai_usage_patterns_with_data(
        self,
        test_db,
        test_ai_usage_week,
    ):
        """Test AI usage pattern analysis."""
        # Execute job
        result = await analyze_ai_usage_patterns()

        # Verify result structure
        assert result["success"] is True
        assert "analysis" in result

        analysis = result["analysis"]
        assert "analyzed_at" in analysis
        assert "period" in analysis
        assert "high_cost_operations" in analysis
        assert "daily_costs" in analysis
        assert "average_daily_cost" in analysis
        assert "usage_spikes" in analysis
        assert "model_distribution" in analysis
        assert "recommendations" in analysis

        # Verify daily costs array
        assert len(analysis["daily_costs"]) == 7  # 7 days

    async def test_analyze_ai_usage_patterns_no_data(self, test_db):
        """Test usage analysis with no data."""
        # Execute job
        result = await analyze_ai_usage_patterns()

        # Should succeed with empty analysis
        assert result["success"] is True
        assert result["analysis"]["average_daily_cost"] == 0

    async def test_calculate_project_analytics_with_data(
        self,
        test_db,
        test_projects_with_tasks,
        test_ai_usage_week,
    ):
        """Test project analytics calculation."""
        # Execute job
        result = await calculate_project_analytics()

        # Verify result structure
        assert result["success"] is True
        assert "calculated_at" in result
        assert "project_count" in result
        assert "analytics" in result

        # Should find our test projects
        assert result["project_count"] >= 2
        assert len(result["analytics"]) >= 2

        # Verify analytics structure
        for project_data in result["analytics"]:
            assert "project_id" in project_data
            assert "project_name" in project_data
            assert "task_metrics" in project_data
            assert "ai_metrics" in project_data

            # Verify metrics
            task_metrics = project_data["task_metrics"]
            assert "total_tasks" in task_metrics
            assert "completed_tasks" in task_metrics
            assert "completion_rate" in task_metrics

    async def test_calculate_project_analytics_no_projects(self, test_db):
        """Test analytics with no projects."""
        # Execute job
        result = await calculate_project_analytics()

        # Should succeed with zero projects
        assert result["success"] is True
        assert result["project_count"] == 0
        assert result["analytics"] == []


@pytest.mark.asyncio
class TestMaintenanceJobs:
    """Test Maintenance background jobs."""

    async def test_cleanup_old_sessions_with_redis(self):
        """Test Redis session cleanup."""
        # Mock Redis to avoid connection dependency
        with patch("ardha.jobs.maintenance_jobs.Redis") as mock_redis:
            mock_client = AsyncMock()
            mock_redis.from_url.return_value = mock_client

            # Mock scan results
            mock_client.scan.return_value = (0, [])  # No keys found
            mock_client.close = AsyncMock()

            # Execute job
        result = await cleanup_old_sessions()

        # Verify result structure
        assert result["success"] is True
        assert "cleaned_at" in result
        assert "statistics" in result

        stats = result["statistics"]
        assert "keys_checked" in stats
        assert "keys_deleted" in stats
        assert "by_pattern" in stats

        # Should have checked some keys
        assert stats["keys_checked"] >= 0

    async def test_cleanup_old_sessions_error_handling(self):
        """Test cleanup with Redis connection error."""
        with patch("ardha.jobs.maintenance_jobs.Redis") as mock_redis:
            mock_redis.from_url.side_effect = Exception("Redis connection failed")

            with pytest.raises(Exception, match="Redis connection failed"):
                await cleanup_old_sessions()

    def test_backup_database_structure(self, tmp_path):
        """Test database backup function structure."""
        # Mock subprocess to avoid actual backup
        with patch("ardha.jobs.maintenance_jobs.subprocess") as mock_subprocess:
            # Mock pg_dump success
            pg_dump_result = MagicMock()
            pg_dump_result.returncode = 0
            pg_dump_result.stderr = ""

            # Mock gzip success
            gzip_result = MagicMock()
            gzip_result.returncode = 0
            gzip_result.stderr = ""

            mock_subprocess.run.side_effect = [pg_dump_result, gzip_result]

            # Mock Path and file operations
            with patch("ardha.jobs.maintenance_jobs.Path") as mock_path:
                mock_backup_dir = tmp_path
                mock_path.return_value = mock_backup_dir

                # Create dummy backup files
                backup_sql = tmp_path / "test.sql"
                backup_sql.write_text("dummy sql")
                backup_gz = tmp_path / "test.sql.gz"
                backup_gz.write_text("dummy gz")

                # Mock mkdir
                mock_backup_dir.mkdir = MagicMock()

                # Mock file path operations
                timestamp_mock = "20240101_120000"
                with patch("ardha.jobs.maintenance_jobs.datetime") as mock_dt:
                    mock_now = MagicMock()
                    mock_now.strftime.return_value = timestamp_mock
                    mock_dt.now.return_value = mock_now
                    mock_dt.side_effect = lambda *args, **kw: datetime(*args, **kw)

                    with patch("ardha.jobs.maintenance_jobs.cleanup_old_backups"):
                        # Execute job
                        result = backup_database()

                        # Verify return structure
                        assert result["success"] is True
                        assert "backup_file" in result
                        assert "backup_size_mb" in result


class TestCeleryConfiguration:
    """Test Celery configuration and task registration."""

    def test_task_routes_configured(self):
        """Test all task routing is configured."""
        from ardha.core.celery_app import celery_app

        routes = celery_app.conf.task_routes

        # Verify routing patterns exist
        assert "ardha.jobs.memory_jobs.*" in routes
        assert "ardha.jobs.memory_cleanup.*" in routes
        assert "git.*" in routes
        assert "tasks.*" in routes
        assert "cost.*" in routes
        assert "maintenance.*" in routes

        # Verify queue assignments
        assert routes["git.*"]["queue"] == "memory"
        assert routes["tasks.*"]["queue"] == "analytics"
        assert routes["cost.*"]["queue"] == "analytics"
        assert routes["maintenance.*"]["queue"] == "maintenance"

    def test_beat_schedule_configured(self):
        """Test beat schedule has all Week 11 tasks."""
        from ardha.core.celery_app import celery_app

        schedule = celery_app.conf.beat_schedule

        # Week 11 Task #1 - Git & Task jobs
        assert "calculate-team-velocity" in schedule
        assert schedule["calculate-team-velocity"]["task"] == "tasks.calculate_team_velocity"

        assert "send-overdue-reminders" in schedule
        assert schedule["send-overdue-reminders"]["task"] == "tasks.send_overdue_task_reminders"

        # Week 11 Task #2 - Cost jobs
        assert "generate-daily-cost-report" in schedule
        assert schedule["generate-daily-cost-report"]["task"] == "cost.generate_daily_cost_report"

        assert "analyze-usage-patterns" in schedule
        assert schedule["analyze-usage-patterns"]["task"] == "cost.analyze_ai_usage_patterns"

        assert "calculate-project-analytics" in schedule
        assert schedule["calculate-project-analytics"]["task"] == "cost.calculate_project_analytics"

        # Week 11 Task #3 - Maintenance jobs
        assert "cleanup-old-sessions" in schedule
        assert schedule["cleanup-old-sessions"]["task"] == "maintenance.cleanup_old_sessions"

        assert "backup-database" in schedule
        assert schedule["backup-database"]["task"] == "maintenance.backup_database"

    def test_task_annotations_configured(self):
        """Test task annotations (rate limits, time limits)."""
        from ardha.core.celery_app import celery_app

        annotations = celery_app.conf.task_annotations

        # Check rate limits
        assert "git.*" in annotations
        assert annotations["git.*"]["rate_limit"] == "10/m"

        assert "tasks.*" in annotations
        assert annotations["tasks.*"]["rate_limit"] == "5/m"

        assert "cost.*" in annotations
        assert annotations["cost.*"]["rate_limit"] == "5/m"

        assert "maintenance.*" in annotations
        assert annotations["maintenance.*"]["rate_limit"] == "1/h"

        # Check time limits
        assert annotations["git.*"]["time_limit"] == 300  # 5 minutes
        assert annotations["tasks.*"]["time_limit"] == 600  # 10 minutes
        assert annotations["maintenance.*"]["time_limit"] == 1800  # 30 minutes

    def test_all_week11_jobs_registered(self):
        """Test all Week 11 jobs are registered with Celery."""
        from ardha.core.celery_app import celery_app

        registered_tasks = celery_app.tasks.keys()

        # Git jobs (Week 11 Task #1)
        assert "git.ingest_commit_to_memory" in registered_tasks

        # Task jobs (Week 11 Task #1)
        assert "tasks.calculate_team_velocity" in registered_tasks
        assert "tasks.send_overdue_task_reminders" in registered_tasks

        # Cost jobs (Week 11 Task #2)
        assert "cost.generate_daily_cost_report" in registered_tasks
        assert "cost.analyze_ai_usage_patterns" in registered_tasks
        assert "cost.calculate_project_analytics" in registered_tasks

        # Maintenance jobs (Week 11 Task #3)
        assert "maintenance.cleanup_old_sessions" in registered_tasks
        assert "maintenance.backup_database" in registered_tasks


@pytest.mark.asyncio
class TestJobErrorHandling:
    """Test error handling in background jobs."""

    async def test_git_job_handles_invalid_uuid(self):
        """Test git job with invalid UUID."""
        with pytest.raises(Exception):  # Will raise ValueError or similar
            await ingest_commit_to_memory("not-a-uuid")

    async def test_jobs_log_errors(self, caplog):
        """Test that jobs log errors properly."""
        import logging

        caplog.set_level(logging.ERROR)

        # Try to ingest non-existent commit
        fake_id = str(uuid4())
        try:
            await ingest_commit_to_memory(fake_id)
        except Exception:
            pass

        # Verify error was logged
        assert any("Error ingesting commit" in record.message for record in caplog.records)


@pytest.mark.asyncio
class TestJobIntegration:
    """Test integration between jobs and services."""

    async def test_git_job_creates_memory(
        self,
        test_db,
        test_commit,
    ):
        """Test that git job actually creates memory entry."""
        # Mock memory service
        with patch("ardha.jobs.git_jobs.MemoryService") as mock_service:
            mock_memory = MagicMock()
            mock_memory.id = uuid4()
            mock_service.return_value.create_memory = AsyncMock(return_value=mock_memory)

            # Execute job
            result = await ingest_commit_to_memory(str(test_commit.id))

            # Verify memory was created
            assert result["success"] is True

            # Verify memory service was called with correct params
            call_args = mock_service.return_value.create_memory.call_args
            assert call_args is not None

            # Check that content includes commit message
            kwargs = call_args.kwargs
            assert "Git Commit:" in kwargs["content"]
            assert kwargs["memory_type"] == "code_decision"
            assert kwargs["source_type"] == "git_commit"

    async def test_cost_jobs_query_database_correctly(
        self,
        test_db,
        test_ai_usage_yesterday,
    ):
        """Test that cost jobs correctly query the database."""
        # Execute report generation
        result = await generate_daily_cost_report()

        # Verify data was found
        assert result["success"] is True
        assert result["report"]["summary"]["total_operations"] >= 3

        # Verify breakdowns are populated
        assert len(result["report"]["operation_breakdown"]) > 0
        assert len(result["report"]["model_breakdown"]) > 0
        assert len(result["report"]["user_breakdown"]) > 0

    async def test_task_velocity_with_month_old_tasks(
        self,
        test_db,
        test_user,
        test_project,
    ):
        """Test velocity calculation with tasks from 4 weeks ago."""
        # Create tasks completed 4 weeks ago
        for i in range(3):
            task = Task(
                id=uuid4(),
                project_id=test_project["id"],
                identifier=f"OLD-{i}",
                title=f"Old Task {i}",
                description="Old task",
                status="done",
                created_by_id=test_user["user"]["id"],
                created_at=datetime.now(timezone.utc) - timedelta(days=30),
                completed_at=datetime.now(timezone.utc) - timedelta(days=28),
            )
            test_db.add(task)

        await test_db.commit()

        # Execute job
        result = await calculate_team_velocity()

        # Should include in monthly count
        assert result["success"] is True
        assert result["metrics"]["tasks_completed_this_month"] >= 3


@pytest.mark.asyncio
class TestJobPerformance:
    """Test job performance and resource usage."""

    async def test_velocity_calculation_is_fast(
        self,
        test_db,
        test_completed_tasks,
    ):
        """Test that velocity calculation completes quickly."""
        import time

        start = time.time()
        result = await calculate_team_velocity()
        duration = time.time() - start

        # Should complete in under 5 seconds
        assert duration < 5.0
        assert result["success"] is True

    async def test_cost_report_handles_large_dataset(
        self,
        test_db,
        test_user,
        test_project,
    ):
        """Test cost report with large number of records."""
        # Create 50 usage records for yesterday
        now = datetime.now(timezone.utc)
        yesterday = (now - timedelta(days=1)).replace(hour=12, minute=0, second=0)

        for i in range(50):
            usage = AIUsage(
                id=uuid4(),
                user_id=test_user["user"]["id"],
                project_id=test_project["id"],
                operation=AIOperation.CHAT,
                model_name="gpt-4",
                tokens_input=100,
                tokens_output=50,
                cost=Decimal("0.01"),
                usage_date=yesterday.date(),  # Extract date for aggregation
                created_at=yesterday,
            )
            test_db.add(usage)

        await test_db.commit()

        # Execute job - should handle large dataset
        result = await generate_daily_cost_report()

        assert result["success"] is True
        assert result["report"]["summary"]["total_operations"] >= 50
