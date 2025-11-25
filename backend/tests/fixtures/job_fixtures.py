"""
Test fixtures for background jobs.

Provides reusable test data for Git, Task, Cost, and Maintenance jobs.
"""

from datetime import datetime, timedelta, timezone
from decimal import Decimal
from uuid import uuid4

import pytest

from ardha.models.ai_usage import AIOperation, AIUsage
from ardha.models.git_commit import GitCommit
from ardha.models.task import Task


@pytest.fixture
async def test_commit(test_db, test_user, test_project):
    """Create test Git commit with file changes."""
    commit = GitCommit(
        id=uuid4(),
        project_id=test_project["id"],
        sha="abc123def456789012345678901234567890abcd",
        short_sha="abc123d",
        message="feat: implement authentication system\n\nCloses #123, TAS-001",
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
    await test_db.refresh(commit)
    return commit


@pytest.fixture
async def test_completed_tasks(test_db, test_user, test_project):
    """Create test tasks with various completion states."""
    tasks = []

    # Create tasks completed over last 7 days
    for i in range(5):
        task = Task(
            id=uuid4(),
            project_id=test_project["id"],
            identifier=f"TAS-{100 + i}",
            title=f"Completed Task {i}",
            description=f"Test task completed {i} days ago",
            status="done",
            created_by_id=test_user["user"]["id"],
            assignee_id=test_user["user"]["id"],
            created_at=datetime.now(timezone.utc) - timedelta(days=i + 1),
            completed_at=datetime.now(timezone.utc) - timedelta(days=i),
        )
        tasks.append(task)
        test_db.add(task)

    await test_db.commit()
    for task in tasks:
        await test_db.refresh(task)

    return tasks


@pytest.fixture
async def test_overdue_tasks(test_db, test_user, test_project):
    """Create test overdue tasks."""
    tasks = []

    # Create overdue tasks (past due, not completed)
    for i in range(3):
        task = Task(
            id=uuid4(),
            project_id=test_project["id"],
            identifier=f"TAS-{200 + i}",
            title=f"Overdue Task {i}",
            description=f"This task is {i + 1} days overdue",
            status="in_progress",
            created_by_id=test_user["user"]["id"],
            assignee_id=test_user["user"]["id"],
            due_date=datetime.now(timezone.utc) - timedelta(days=i + 1),
        )
        tasks.append(task)
        test_db.add(task)

    await test_db.commit()
    for task in tasks:
        await test_db.refresh(task)

    return tasks


@pytest.fixture
async def test_ai_usage_yesterday(test_db, test_user, test_project):
    """Create AI usage records for yesterday."""
    usage_records = []

    # Yesterday's date range
    now = datetime.now(timezone.utc)
    yesterday_start = (now - timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)

    # Create varied usage records
    operations = [
        (AIOperation.CHAT, "gpt-4", 100, 50, Decimal("0.05")),
        (AIOperation.CHAT, "gpt-4", 200, 100, Decimal("0.10")),
        (AIOperation.WORKFLOW, "claude-sonnet-4", 300, 150, Decimal("0.15")),
    ]

    for op, model, input_tok, output_tok, cost in operations:
        created_time = yesterday_start + timedelta(hours=10)
        usage = AIUsage(
            id=uuid4(),
            user_id=test_user["user"]["id"],
            project_id=test_project["id"],
            operation=op,
            model_name=model,
            tokens_input=input_tok,
            tokens_output=output_tok,
            cost=cost,
            usage_date=created_time.date(),  # Extract date for aggregation
            created_at=created_time,
        )
        usage_records.append(usage)
        test_db.add(usage)

    await test_db.commit()
    return usage_records


@pytest.fixture
async def test_ai_usage_week(test_db, test_user, test_project):
    """Create AI usage records for last 7 days."""
    usage_records = []

    for day in range(7):
        for _ in range(2):
            created_time = datetime.now(timezone.utc) - timedelta(days=day)
            usage = AIUsage(
                id=uuid4(),
                user_id=test_user["user"]["id"],
                project_id=test_project["id"],
                operation=AIOperation.CHAT,
                model_name="gpt-4",
                tokens_input=100,
                tokens_output=50,
                cost=Decimal("0.05"),
                usage_date=created_time.date(),  # Extract date for aggregation
                created_at=created_time,
            )
            usage_records.append(usage)
            test_db.add(usage)

    await test_db.commit()
    return usage_records


@pytest.fixture
async def test_projects_with_tasks(test_db, test_user):
    """Create test projects with tasks for analytics."""
    from ardha.models.project import Project

    projects = []

    for i in range(2):
        project = Project(
            id=uuid4(),
            name=f"Test Project {i}",
            slug=f"test-project-{i}",
            description=f"Test project for analytics {i}",
            owner_id=test_user["user"]["id"],
            visibility="private",
        )
        test_db.add(project)
        await test_db.flush()

        # Add tasks to project
        for j in range(5):
            task = Task(
                id=uuid4(),
                project_id=project.id,
                identifier=f"TP{i}-{j}",
                title=f"Project {i} Task {j}",
                description="Test task",
                status="done" if j < 3 else "in_progress",
                created_by_id=test_user["user"]["id"],
                created_at=datetime.now(timezone.utc) - timedelta(days=10),
                completed_at=(datetime.now(timezone.utc) - timedelta(days=5) if j < 3 else None),
            )
            test_db.add(task)

        projects.append(project)

    await test_db.commit()
    for project in projects:
        await test_db.refresh(project)

    return projects


# Removed redis_mock - using direct patches in tests instead
