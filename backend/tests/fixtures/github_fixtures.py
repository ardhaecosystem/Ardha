"""
Test fixtures for GitHub API operations.

Provides mock objects and data for testing GitHubAPIClient.
"""

from datetime import datetime, timezone
from unittest.mock import Mock, patch

import pytest


@pytest.fixture
def mock_github_client():
    """Mock PyGithub Github client."""
    with patch("github.Github") as mock:
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
    branch = Mock()
    branch.name = "main"
    branch.commit = Mock(sha="abc123")
    return branch


@pytest.fixture
def mock_pull_request():
    """Mock GitHub pull request."""
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

    # Head branch
    pr.head = Mock()
    pr.head.ref = "feature/test"
    pr.head.sha = "def456"

    # Base branch
    pr.base = Mock()
    pr.base.ref = "main"

    # Author
    pr.user = Mock()
    pr.user.login = "testuser"

    # Timestamps
    pr.created_at = datetime(2024, 11, 1, tzinfo=timezone.utc)
    pr.updated_at = datetime(2024, 11, 15, tzinfo=timezone.utc)

    return pr


@pytest.fixture
def mock_pr_merged():
    """Mock merged pull request."""
    pr = Mock()
    pr.number = 124
    pr.id = 456790
    pr.title = "Merged PR"
    pr.body = "This PR was merged"
    pr.state = "closed"
    pr.html_url = "https://github.com/owner/repo/pull/124"
    pr.url = "https://api.github.com/repos/owner/repo/pulls/124"
    pr.draft = False
    pr.mergeable = None
    pr.merged = True
    pr.merged_at = datetime(2024, 11, 10, tzinfo=timezone.utc)
    pr.closed_at = datetime(2024, 11, 10, tzinfo=timezone.utc)
    pr.additions = 20
    pr.deletions = 10
    pr.changed_files = 5
    pr.commits = 5

    pr.head = Mock()
    pr.head.ref = "feature/merged"
    pr.head.sha = "ghi789"

    pr.base = Mock()
    pr.base.ref = "main"

    pr.user = Mock()
    pr.user.login = "testuser"

    pr.created_at = datetime(2024, 11, 5, tzinfo=timezone.utc)
    pr.updated_at = datetime(2024, 11, 10, tzinfo=timezone.utc)

    return pr


@pytest.fixture
def mock_commit():
    """Mock GitHub commit."""
    commit = Mock()
    commit.sha = "abc123def456"

    # Commit metadata
    commit.commit = Mock()
    commit.commit.message = "feat: add new feature"

    # Author info
    commit.commit.author = Mock()
    commit.commit.author.name = "Test User"
    commit.commit.author.email = "test@example.com"
    commit.commit.author.date = datetime(2024, 11, 15, tzinfo=timezone.utc)

    # Stats
    commit.stats = Mock()
    commit.stats.additions = 100
    commit.stats.deletions = 50
    commit.stats.total = 150

    # Files - mock PaginatedList
    commit.files = Mock()
    commit.files.totalCount = 5

    return commit


@pytest.fixture
def mock_commit_file():
    """Mock GitHub commit file."""
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
    check_runs = Mock()
    check_runs.totalCount = 1
    check_runs.__iter__ = Mock(return_value=iter([mock_check_run]))
    return check_runs


@pytest.fixture
def mock_webhook():
    """Mock GitHub webhook."""
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
    result = Mock()
    result.merged = True
    result.sha = "merged123abc"
    result.message = "Pull Request successfully merged"
    return result


@pytest.fixture
def mock_rate_limit():
    """Mock GitHub rate limit."""
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
def github_test_token():
    """GitHub test token (fake)."""
    return "ghp_test1234567890abcdef"


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
