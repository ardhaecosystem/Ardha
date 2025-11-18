"""
Shared test fixtures for Ardha backend tests.

This module provides pytest fixtures for database setup, test clients,
and common test data used across unit and integration tests.
"""

from typing import AsyncGenerator

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from ardha.core.database import get_db
from ardha.main import app
from ardha.models.base import Base

# Test database URL (separate from development database)
TEST_DATABASE_URL = "postgresql+asyncpg://ardha_user:ardha_password@localhost:5432/ardha_test"


# Fix pytest-asyncio deprecation warning by removing custom event_loop fixture
# pytest-asyncio will handle event loop creation automatically


@pytest_asyncio.fixture(scope="function")
async def test_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Create test database and provide session.

    This fixture:
    1. Creates a fresh database engine for each test
    2. Drops all tables (clean slate)
    3. Creates all tables from models
    4. Provides an async session
    5. Cleans up after test completes

    Yields:
        AsyncSession for database operations
    """
    # Create async engine for test database
    engine = create_async_engine(
        TEST_DATABASE_URL,
        echo=False,  # Set to True for SQL query debugging
        pool_pre_ping=True,
    )

    # Drop and recreate all tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)

    # Create session factory
    async_session_factory = async_sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    # Provide session for test
    async with async_session_factory() as session:
        yield session

    # Cleanup
    await engine.dispose()


@pytest_asyncio.fixture
async def client(test_db: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """
    Create test client with database override.

    This fixture:
    1. Overrides the get_db dependency to use test database
    2. Creates an AsyncClient for making HTTP requests
    3. Cleans up dependency overrides after test

    Args:
        test_db: Test database session from test_db fixture

    Yields:
        AsyncClient for making API requests
    """

    async def override_get_db() -> AsyncGenerator[AsyncSession, None]:
        """Override get_db to use test database."""
        yield test_db

    # Override dependency
    app.dependency_overrides[get_db] = override_get_db

    # Create test client
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
        follow_redirects=True,
    ) as ac:
        yield ac

    # Clear overrides
    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def test_user(client: AsyncClient) -> dict:
    """
    Create test user and return authentication data.

    This fixture:
    1. Registers a new test user
    2. Logs in the user
    3. Returns user data with JWT token

    Args:
        client: Test client from client fixture

    Returns:
        Dictionary with 'token' (JWT) and 'user' (user data)
    """
    # Register user
    register_response = await client.post(
        "/api/v1/auth/register",
        json={
            "email": "test@example.com",
            "username": "testuser",
            "password": "Test123!@#",
            "full_name": "Test User",
        },
    )
    assert register_response.status_code == 201

    # Login user
    login_response = await client.post(
        "/api/v1/auth/login",
        data={
            "username": "test@example.com",
            "password": "Test123!@#",
        },
    )
    assert login_response.status_code == 200

    token_data = login_response.json()
    access_token = token_data["access_token"]

    # Get user profile
    me_response = await client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {access_token}"},
    )
    assert me_response.status_code == 200
    user_data = me_response.json()

    return {
        "token": access_token,
        "refresh_token": token_data["refresh_token"],
        "user": user_data,
    }


@pytest_asyncio.fixture
async def test_project(client: AsyncClient, test_user: dict) -> dict:
    """
    Create test project for testing.

    Args:
        client: Test client
        test_user: Authenticated test user

    Returns:
        Dictionary with project data
    """
    response = await client.post(
        "/api/v1/projects",
        headers={"Authorization": f"Bearer {test_user['token']}"},
        json={
            "name": "Test Project",
            "description": "A test project for integration tests",
            "visibility": "private",
            "tech_stack": ["Python", "FastAPI"],
        },
    )
    assert response.status_code == 201
    return response.json()


@pytest_asyncio.fixture
async def test_milestone(
    client: AsyncClient,
    test_user: dict,
    test_project: dict,
) -> dict:
    """
    Create test milestone for testing.

    Args:
        client: Test client
        test_user: Authenticated test user
        test_project: Test project

    Returns:
        Dictionary with milestone data
    """
    from datetime import datetime, timedelta

    due_date = (datetime.now() + timedelta(days=30)).isoformat()

    response = await client.post(
        f"/api/v1/milestones/projects/{test_project['id']}/milestones",
        headers={"Authorization": f"Bearer {test_user['token']}"},
        json={
            "name": "Test Milestone",
            "description": "A test milestone",
            "due_date": due_date,
            "status": "in_progress",
        },
    )
    assert response.status_code == 201
    return response.json()


@pytest_asyncio.fixture
async def test_task(
    client: AsyncClient,
    test_user: dict,
    test_project: dict,
) -> dict:
    """
    Create test task for testing.

    Args:
        client: Test client
        test_user: Authenticated test user
        test_project: Test project

    Returns:
        Dictionary with task data
    """
    response = await client.post(
        f"/api/v1/tasks/projects/{test_project['id']}/tasks",
        headers={"Authorization": f"Bearer {test_user['token']}"},
        json={
            "title": "Test Task",
            "description": "A test task",
            "priority": "medium",
            "tags": ["testing"],
        },
    )
    assert response.status_code == 201
    return response.json()


@pytest.fixture
def mock_local_embedding():
    """Mock local embedding vector for testing."""
    return [0.1] * 384  # 384-dimensional embedding vector


@pytest.fixture
def mock_embedding_batch():
    """Mock batch of embedding vectors for testing."""
    return [
        [0.1] * 384,  # First embedding
        [0.2] * 384,  # Second embedding
        [0.3] * 384,  # Third embedding
    ]


@pytest.fixture
def mock_qdrant_search_results():
    """Mock Qdrant search results for testing."""
    from uuid import uuid4

    return [
        {
            "id": str(uuid4()),
            "score": 0.9,
            "payload": {"content": "Similar memory 1", "memory_type": "fact", "importance": 8},
        },
        {
            "id": str(uuid4()),
            "score": 0.8,
            "payload": {
                "content": "Similar memory 2",
                "memory_type": "conversation",
                "importance": 6,
            },
        },
    ]


@pytest_asyncio.fixture
async def sample_memory(test_user: dict) -> dict:
    """Create a sample memory for testing."""
    from datetime import datetime
    from uuid import uuid4

    return {
        "id": uuid4(),
        "user_id": test_user["user"]["id"],
        "content": "This is a test memory about Python programming",
        "summary": "Test memory about Python",
        "memory_type": "fact",
        "source_type": "manual",
        "importance": 7,
        "qdrant_collection": f"memories_{test_user['user']['id']}",
        "qdrant_point_id": str(uuid4()),
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow(),
        "access_count": 0,
        "last_accessed": datetime.utcnow(),
        "is_archived": False,
        "expires_at": None,
    }


@pytest_asyncio.fixture
async def sample_memories_batch(test_user: dict) -> list:
    """Create a batch of sample memories for testing."""
    from datetime import datetime, timedelta
    from uuid import uuid4

    memories = []
    for i in range(5):
        memory = {
            "id": uuid4(),
            "user_id": test_user["user"]["id"],
            "content": f"Test memory content {i+1}",
            "summary": f"Test summary {i+1}",
            "memory_type": ["fact", "conversation", "decision", "action_item", "insight"][i % 5],
            "source_type": "manual",
            "importance": (i % 10) + 1,
            "qdrant_collection": f"memories_{test_user['user']['id']}",
            "qdrant_point_id": str(uuid4()),
            "created_at": datetime.utcnow() - timedelta(days=i),
            "updated_at": datetime.utcnow() - timedelta(days=i),
            "access_count": i,
            "last_accessed": datetime.utcnow() - timedelta(hours=i),
            "is_archived": False,
            "expires_at": None,
        }
        memories.append(memory)

    return memories


@pytest_asyncio.fixture
async def sample_memory_links(test_user: dict, sample_memories_batch: list) -> list:
    """Create sample memory links for testing."""
    from datetime import datetime, timedelta
    from uuid import uuid4

    links = []
    for i in range(3):
        link = {
            "id": uuid4(),
            "source_memory_id": sample_memories_batch[i]["id"],
            "target_memory_id": (
                sample_memories_batch[i + 1]["id"]
                if i + 1 < len(sample_memories_batch)
                else sample_memories_batch[0]["id"]
            ),
            "relationship_type": ["related_to", "depends_on", "supports", "contradicts"][i % 4],
            "strength": 0.8 - (i * 0.1),
            "created_at": datetime.utcnow() - timedelta(days=i),
            "updated_at": datetime.utcnow() - timedelta(days=i),
        }
        links.append(link)

    return links


@pytest_asyncio.fixture
async def sample_chat_messages(test_user: dict) -> list:
    """Create sample chat messages for testing."""
    from datetime import datetime, timedelta
    from uuid import uuid4

    messages = []
    for i in range(10):
        message = {
            "id": uuid4(),
            "chat_id": uuid4(),
            "user_id": test_user["user"]["id"],
            "content": f"This is test message {i+1} with some content about the project",
            "role": "user" if i % 2 == 0 else "assistant",
            "model": "gpt-4",
            "tokens": 50 + (i * 10),
            "created_at": datetime.utcnow() - timedelta(hours=i),
            "updated_at": datetime.utcnow() - timedelta(hours=i),
        }
        messages.append(message)

    return messages


@pytest_asyncio.fixture
async def completed_workflow(test_user: dict, test_project: dict) -> dict:
    """Create a completed workflow for testing."""
    from datetime import datetime, timedelta
    from uuid import uuid4

    return {
        "id": uuid4(),
        "user_id": test_user["user"]["id"],
        "project_id": test_project["id"],
        "workflow_type": "research",
        "status": "completed",
        "config": {"query": "Test research query", "max_results": 10},
        "result": {
            "summary": "Research completed successfully",
            "findings": ["Finding 1", "Finding 2"],
            "recommendations": ["Recommendation 1"],
        },
        "started_at": datetime.utcnow() - timedelta(hours=2),
        "completed_at": datetime.utcnow() - timedelta(hours=1),
        "created_at": datetime.utcnow() - timedelta(hours=3),
        "updated_at": datetime.utcnow() - timedelta(hours=1),
        "error_message": None,
        "retry_count": 0,
        "max_retries": 3,
    }


@pytest.fixture
def test_client(client: AsyncClient, test_user: dict) -> AsyncClient:
    """Create test client with authentication headers."""
    # Add default authorization header
    client.headers.update({"Authorization": f"Bearer {test_user['token']}"})
    return client


@pytest.fixture
def auth_headers(test_user: dict):
    """Create authentication headers from test_user fixture."""
    return {"Authorization": f"Bearer {test_user['token']}"}


# ============= OpenSpec Fixtures =============


@pytest_asyncio.fixture
async def openspec_dependencies(test_db: AsyncSession):
    """
    Create User and Project dependencies for OpenSpec tests.

    Returns:
        Tuple of (user_id, project_id)
    """
    from uuid import uuid4

    from ardha.models.project import Project
    from ardha.models.user import User

    # Create user
    user_id = uuid4()
    user = User(
        id=user_id,
        email="openspec@example.com",
        username="openspecuser",
        full_name="OpenSpec User",
        password_hash="hashed_password",
    )
    test_db.add(user)
    await test_db.flush()

    # Create project
    project_id = uuid4()
    project = Project(
        id=project_id,
        name="OpenSpec Test Project",
        slug="openspec-test-project",
        owner_id=user_id,
        visibility="private",
    )
    test_db.add(project)
    await test_db.flush()

    return user_id, project_id


@pytest_asyncio.fixture
async def sample_proposal_data(openspec_dependencies):
    """
    Sample data for creating OpenSpec proposals.

    Returns:
        Dictionary with all required proposal fields
    """
    from datetime import UTC, datetime

    user_id, project_id = openspec_dependencies

    return {
        "project_id": project_id,
        "name": "user-auth-system",
        "directory_path": "openspec/changes/user-auth-system",
        "status": "pending",
        "created_by_user_id": user_id,
        "proposal_content": """# User Authentication System

## Summary
Implement JWT-based authentication with OAuth support.

## Motivation
Users need secure authentication to access the platform.

## Implementation Plan
1. Create User model
2. Implement JWT token generation
3. Add OAuth providers (GitHub, Google)
""",
        "tasks_content": """# Tasks

## TAS-001: Create User Model
- Create SQLAlchemy User model
- Add email, password_hash fields
- Create migration

## TAS-002: Implement JWT Service
- Token generation
- Token validation
- Refresh token logic

## TAS-003: OAuth Integration
- GitHub OAuth flow
- Google OAuth flow
""",
        "spec_delta_content": """# Specification Changes

## Database Schema
- Add `users` table
- Add `oauth_accounts` table

## API Endpoints
- POST /api/v1/auth/register
- POST /api/v1/auth/login
- POST /api/v1/auth/refresh
""",
        "metadata_json": {
            "proposal_id": "user-auth-system",
            "title": "User Authentication System",
            "author": "AI Assistant",
            "created_at": datetime.now(UTC).isoformat(),
            "priority": "high",
            "estimated_effort": "3 days",
            "tags": ["backend", "security", "authentication"],
        },
        "task_sync_status": "not_synced",
        "completion_percentage": 0,
    }


@pytest_asyncio.fixture
async def sample_proposals_batch(openspec_dependencies):
    """
    Batch of sample proposals for pagination and filtering tests.

    Returns:
        List of 5 proposal data dictionaries with different statuses
    """
    from datetime import UTC, datetime

    user_id, project_id = openspec_dependencies

    return [
        {
            "project_id": project_id,
            "name": "proposal-pending-1",
            "directory_path": "openspec/changes/proposal-pending-1",
            "status": "pending",
            "created_by_user_id": user_id,
            "proposal_content": "# Pending Proposal 1\n...",
            "tasks_content": "# Tasks\n## TAS-001: Task 1\n...",
            "spec_delta_content": "# Changes\n...",
            "metadata_json": {"proposal_id": "proposal-pending-1", "priority": "low"},
        },
        {
            "project_id": project_id,
            "name": "proposal-approved-1",
            "directory_path": "openspec/changes/proposal-approved-1",
            "status": "approved",
            "created_by_user_id": user_id,
            "approved_by_user_id": user_id,  # Use same user as creator
            "approved_at": datetime.now(UTC),
            "proposal_content": "# Approved Proposal 1\n...",
            "tasks_content": "# Tasks\n## TAS-001: Task 1\n...",
            "spec_delta_content": "# Changes\n...",
            "metadata_json": {"proposal_id": "proposal-approved-1", "priority": "high"},
        },
        {
            "project_id": project_id,
            "name": "proposal-in-progress",
            "directory_path": "openspec/changes/proposal-in-progress",
            "status": "in_progress",
            "created_by_user_id": user_id,
            "proposal_content": "# In Progress Proposal\n...",
            "tasks_content": "# Tasks\n## TAS-001: Task 1\n...",
            "spec_delta_content": "# Changes\n...",
            "metadata_json": {"proposal_id": "proposal-in-progress", "priority": "medium"},
            "task_sync_status": "synced",
            "completion_percentage": 50,
        },
        {
            "project_id": project_id,
            "name": "proposal-archived-1",
            "directory_path": "openspec/archive/proposal-archived-1",
            "status": "archived",
            "created_by_user_id": user_id,
            "archived_at": datetime.now(UTC),
            "proposal_content": "# Archived Proposal 1\n...",
            "tasks_content": "# Tasks\n## TAS-001: Task 1\n...",
            "spec_delta_content": "# Changes\n...",
            "metadata_json": {"proposal_id": "proposal-archived-1", "priority": "low"},
            "completion_percentage": 100,
        },
        {
            "project_id": project_id,
            "name": "proposal-rejected",
            "directory_path": "openspec/changes/proposal-rejected",
            "status": "rejected",
            "created_by_user_id": user_id,
            "proposal_content": "# Rejected Proposal\n...",
            "tasks_content": "# Tasks\n## TAS-001: Task 1\n...",
            "spec_delta_content": "# Changes\n...",
            "metadata_json": {"proposal_id": "proposal-rejected", "priority": "low"},
        },
    ]


@pytest_asyncio.fixture
async def test_openspec_proposal(
    test_db: AsyncSession,
    test_user: dict,
    test_project: dict,
) -> dict:
    """
    Create test OpenSpec proposal for testing.

    Args:
        test_db: Test database session
        test_user: Authenticated test user
        test_project: Test project

    Returns:
        Dictionary with proposal data
    """
    from ardha.models.openspec import OpenSpecProposal

    proposal = OpenSpecProposal(
        project_id=test_project["id"],
        name="test-openspec-proposal",
        directory_path="openspec/changes/test-openspec-proposal",
        status="pending",
        created_by_user_id=test_user["user"]["id"],
        proposal_content="# Test Proposal\n## Summary\nTest content",
        tasks_content="# Tasks\n## TAS-001: Test Task\nTest task content",
        spec_delta_content="# Changes\n- Test change",
        metadata_json={
            "proposal_id": "test-openspec-proposal",
            "title": "Test Proposal",
            "priority": "medium",
        },
    )

    test_db.add(proposal)
    await test_db.flush()
    await test_db.refresh(proposal)

    return {
        "id": str(proposal.id),
        "project_id": str(proposal.project_id),
        "name": proposal.name,
        "status": proposal.status,
        "created_by_user_id": str(proposal.created_by_user_id),
    }


# ============= GitHub Fixtures =============


@pytest.fixture
def mock_github_client():
    """Mock PyGithub Github client."""
    from unittest.mock import Mock, patch

    with patch("ardha.services.github_api.Github") as mock:
        mock_instance = Mock()
        mock.return_value = mock_instance
        yield mock_instance


@pytest.fixture
def github_api_client(mock_github_client):
    """GitHubAPIClient with mocked PyGithub."""
    from ardha.services.github_api import GitHubAPIClient

    return GitHubAPIClient(access_token="test_token_12345")


@pytest.fixture
def mock_user():
    """Mock GitHub user."""
    from unittest.mock import Mock

    user = Mock()
    user.login = "testuser"
    user.name = "Test User"
    user.email = "test@example.com"
    user.avatar_url = "https://github.com/avatar/test"
    user.bio = "Test bio"
    user.company = "Test Company"
    user.location = "Test City"
    return user


@pytest.fixture
def mock_repository():
    """Mock GitHub repository."""
    from datetime import datetime, timezone
    from unittest.mock import Mock

    repo = Mock()
    repo.name = "test-repo"
    repo.full_name = "owner/test-repo"
    repo.description = "Test repository"
    repo.html_url = "https://github.com/owner/test-repo"
    repo.clone_url = "https://github.com/owner/test-repo.git"
    repo.default_branch = "main"
    repo.private = False
    repo.fork = False
    repo.archived = False
    repo.created_at = datetime(2024, 1, 1, tzinfo=timezone.utc)
    repo.updated_at = datetime(2024, 11, 1, tzinfo=timezone.utc)
    repo.permissions = Mock(admin=True, push=True, pull=True)
    return repo


@pytest.fixture
def mock_branch():
    """Mock GitHub branch."""
    from unittest.mock import Mock

    branch = Mock()
    branch.name = "main"
    branch.commit = Mock(sha="abc123")
    return branch


@pytest.fixture
def mock_pull_request():
    """Mock GitHub pull request."""
    from datetime import datetime, timezone
    from unittest.mock import Mock

    pr = Mock()
    pr.number = 123
    pr.id = 456789
    pr.title = "Test PR"
    pr.body = "Test PR description"
    pr.state = "open"
    pr.html_url = "https://github.com/owner/repo/pull/123"
    pr.url = "https://api.github.com/repos/owner/repo/pulls/123"
    pr.draft = False
    pr.mergeable = True
    pr.merged = False
    pr.merged_at = None
    pr.closed_at = None
    pr.additions = 10
    pr.deletions = 5
    pr.changed_files = 2
    pr.commits = 3

    pr.head = Mock()
    pr.head.ref = "feature/test"
    pr.head.sha = "def456"

    pr.base = Mock()
    pr.base.ref = "main"

    pr.user = Mock()
    pr.user.login = "testuser"

    pr.created_at = datetime(2024, 11, 1, tzinfo=timezone.utc)
    pr.updated_at = datetime(2024, 11, 15, tzinfo=timezone.utc)

    return pr


@pytest.fixture
def mock_commit():
    """Mock GitHub commit."""
    from datetime import datetime, timezone
    from unittest.mock import Mock

    commit = Mock()
    commit.sha = "abc123def456"

    commit.commit = Mock()
    commit.commit.message = "feat: add new feature"

    commit.commit.author = Mock()
    commit.commit.author.name = "Test User"
    commit.commit.author.email = "test@example.com"
    commit.commit.author.date = datetime(2024, 11, 15, tzinfo=timezone.utc)

    commit.stats = Mock()
    commit.stats.additions = 100
    commit.stats.deletions = 50
    commit.stats.total = 150

    commit.files = Mock()
    commit.files.totalCount = 5

    return commit


@pytest.fixture
def mock_commit_file():
    """Mock GitHub commit file."""
    from unittest.mock import Mock

    file = Mock()
    file.filename = "src/test.py"
    file.status = "modified"
    file.additions = 10
    file.deletions = 5
    file.changes = 15
    file.patch = "@@ -1,3 +1,5 @@\n+new line\n old line"
    return file


@pytest.fixture
def mock_review():
    """Mock GitHub PR review."""
    from datetime import datetime, timezone
    from unittest.mock import Mock

    review = Mock()
    review.id = 789
    review.user = Mock()
    review.user.login = "reviewer"
    review.state = "APPROVED"
    review.body = "Looks good!"
    review.submitted_at = datetime(2024, 11, 15, tzinfo=timezone.utc)
    return review


@pytest.fixture
def mock_check_run():
    """Mock GitHub check run."""
    from datetime import datetime, timezone
    from unittest.mock import Mock

    check = Mock()
    check.id = 12345
    check.name = "tests"
    check.status = "completed"
    check.conclusion = "success"
    check.started_at = datetime(2024, 11, 15, 10, 0, 0, tzinfo=timezone.utc)
    check.completed_at = datetime(2024, 11, 15, 10, 5, 0, tzinfo=timezone.utc)
    return check


@pytest.fixture
def mock_check_runs(mock_check_run):
    """Mock paginated check runs."""
    from unittest.mock import Mock

    check_runs = Mock()
    check_runs.totalCount = 1
    check_runs.__iter__ = Mock(return_value=iter([mock_check_run]))
    return check_runs


@pytest.fixture
def mock_webhook():
    """Mock GitHub webhook."""
    from datetime import datetime, timezone
    from unittest.mock import Mock

    hook = Mock()
    hook.id = 999
    hook.config = {
        "url": "https://example.com/webhook",
        "content_type": "json",
    }
    hook.events = ["pull_request", "push"]
    hook.active = True
    hook.created_at = datetime(2024, 10, 1, tzinfo=timezone.utc)
    hook.updated_at = datetime(2024, 11, 1, tzinfo=timezone.utc)
    return hook


@pytest.fixture
def mock_commit_status():
    """Mock GitHub commit status."""
    from datetime import datetime, timezone
    from unittest.mock import Mock

    status = Mock()
    status.id = 111222
    status.state = "success"
    status.description = "All tests passed"
    status.context = "ardha/tests"
    status.target_url = "https://example.com/build/123"
    status.created_at = datetime(2024, 11, 15, tzinfo=timezone.utc)
    return status


@pytest.fixture
def mock_issue_comment():
    """Mock GitHub issue/PR comment."""
    from datetime import datetime, timezone
    from unittest.mock import Mock

    comment = Mock()
    comment.id = 333444
    comment.body = "Test comment"
    comment.user = Mock()
    comment.user.login = "testuser"
    comment.created_at = datetime(2024, 11, 15, tzinfo=timezone.utc)
    return comment


@pytest.fixture
def mock_merge_result():
    """Mock PR merge result."""
    from unittest.mock import Mock

    result = Mock()
    result.merged = True
    result.sha = "merged123abc"
    result.message = "Pull Request successfully merged"
    return result


@pytest.fixture
def mock_rate_limit():
    """Mock GitHub rate limit."""
    from datetime import datetime, timezone
    from unittest.mock import Mock

    rate_limit = Mock()
    core = Mock()
    core.limit = 5000
    core.remaining = 4999
    core.reset = datetime(2024, 11, 15, 12, 0, 0, tzinfo=timezone.utc)
    rate_limit.core = core
    return rate_limit


@pytest.fixture
def mock_github_exception_401():
    """Mock GitHub 401 authentication error."""
    from github import GithubException

    error = GithubException(
        status=401,
        data={"message": "Bad credentials"},
        headers={},
    )
    return error


@pytest.fixture
def mock_github_exception_404():
    """Mock GitHub 404 not found error."""
    from github import GithubException

    error = GithubException(
        status=404,
        data={"message": "Not Found"},
        headers={},
    )
    return error


@pytest.fixture
def mock_github_exception_429():
    """Mock GitHub 429 rate limit error."""
    from datetime import datetime, timezone

    from github import GithubException

    reset_timestamp = int(datetime(2024, 11, 15, 12, 0, 0, tzinfo=timezone.utc).timestamp())

    error = GithubException(
        status=429,
        data={"message": "API rate limit exceeded"},
        headers={"X-RateLimit-Reset": str(reset_timestamp)},
    )
    return error


@pytest.fixture
def mock_github_exception_422():
    """Mock GitHub 422 validation error."""
    from github import GithubException

    error = GithubException(
        status=422,
        data={"message": "Validation Failed"},
        headers={},
    )
    return error


@pytest.fixture
def encryption_key():
    """Encryption key for testing."""
    from cryptography.fernet import Fernet

    return Fernet.generate_key().decode()


@pytest.fixture
def mock_env_encryption_key(encryption_key, monkeypatch):
    """Set GITHUB_TOKEN_ENCRYPTION_KEY environment variable."""
    monkeypatch.setenv("GITHUB_TOKEN_ENCRYPTION_KEY", encryption_key)
    yield encryption_key


# ============= Database Model Fixtures for Repository Tests =============


@pytest_asyncio.fixture
async def sample_user(test_db: AsyncSession):
    """Create a sample User for repository tests."""
    from ardha.models.user import User

    user = User(
        email="repotest@example.com",
        username="repotest",
        full_name="Repo Test User",
        password_hash="hashed_password_123",
        is_active=True,
    )
    test_db.add(user)
    await test_db.flush()
    await test_db.refresh(user)
    return user


@pytest_asyncio.fixture
async def sample_project(test_db: AsyncSession, sample_user):
    """Create a sample Project for repository tests."""
    from ardha.models.project import Project
    from ardha.models.project_member import ProjectMember

    project = Project(
        name="GitHub Integration Test Project",
        slug="github-integration-test",
        description="Test project for GitHub integration",
        owner_id=sample_user.id,
        visibility="private",
    )
    test_db.add(project)
    await test_db.flush()
    await test_db.refresh(project)

    # Add owner as member
    member = ProjectMember(
        project_id=project.id,
        user_id=sample_user.id,
        role="owner",
    )
    test_db.add(member)
    await test_db.flush()

    return project


@pytest_asyncio.fixture
async def sample_github_integration(test_db: AsyncSession, sample_user, sample_project):
    """Create a sample GitHubIntegration for repository tests."""
    from ardha.models.github_integration import GitHubIntegration

    integration = GitHubIntegration(
        project_id=sample_project.id,
        repository_owner="ardhaecosystem",
        repository_name="Ardha",
        repository_url="https://github.com/ardhaecosystem/Ardha",
        default_branch="main",
        access_token_encrypted="encrypted_test_token_abc123",
        created_by_user_id=sample_user.id,
        connection_status="disconnected",
        is_active=True,
    )
    test_db.add(integration)
    await test_db.flush()
    await test_db.refresh(integration)
    return integration


@pytest_asyncio.fixture
async def sample_pull_request(test_db: AsyncSession, sample_github_integration, sample_project):
    """Create a sample PullRequest for repository tests."""
    from ardha.models.github_integration import PullRequest

    pr = PullRequest(
        github_integration_id=sample_github_integration.id,
        project_id=sample_project.id,
        pr_number=1,
        github_pr_id=123456789,
        title="Test Pull Request",
        description="This is a test PR for repository testing",
        state="open",
        head_branch="feature/test",
        base_branch="main",
        head_sha="abc123def456",
        author_github_username="testuser",
        html_url="https://github.com/ardhaecosystem/Ardha/pull/1",
        api_url="https://api.github.com/repos/ardhaecosystem/Ardha/pulls/1",
    )
    test_db.add(pr)
    await test_db.flush()
    await test_db.refresh(pr)
    return pr


@pytest_asyncio.fixture
async def sample_tasks(test_db: AsyncSession, sample_user, sample_project) -> list:
    """Create sample Tasks for repository tests."""
    from ardha.models.task import Task

    tasks = []
    for i in range(3):
        task = Task(
            project_id=sample_project.id,
            identifier=f"TAS-00{i+1}",
            title=f"Test Task {i+1}",
            description=f"Task description {i+1}",
            status="todo",
            priority="medium",
            created_by_id=sample_user.id,
        )
        test_db.add(task)
        tasks.append(task)

    await test_db.flush()
    for task in tasks:
        await test_db.refresh(task)

    return tasks


@pytest_asyncio.fixture
async def sample_git_commits(test_db: AsyncSession, sample_project, sample_user) -> list:
    """Create sample GitCommits for repository tests."""
    from datetime import datetime, timezone

    from ardha.models.git_commit import GitCommit

    commits = []
    for i in range(3):
        commit = GitCommit(
            project_id=sample_project.id,
            sha=f"abc{i}123def456789012345678901234567890",
            short_sha=f"abc{i}12",
            message=f"feat: test commit {i+1}",
            author_name="Test Author",
            author_email="author@example.com",
            committed_at=datetime.now(timezone.utc),
            branch="main",
            ardha_user_id=sample_user.id,
        )
        test_db.add(commit)
        commits.append(commit)

    await test_db.flush()
    for commit in commits:
        await test_db.refresh(commit)

    return commits
