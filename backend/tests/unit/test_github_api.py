"""
Unit tests for GitHub API Client.

Tests all GitHubAPIClient methods with mocked PyGithub responses.
"""

from datetime import datetime, timezone
from unittest.mock import Mock

import pytest
from github import GithubException

from ardha.core.github_exceptions import (
    GitHubAuthenticationError,
    GitHubPermissionError,
    GitHubPullRequestError,
    GitHubRateLimitError,
    GitHubRepositoryNotFoundError,
)
from ardha.services.github_api import TokenEncryption

# ============= Token Encryption Tests =============


@pytest.mark.asyncio
async def test_token_encryption(mock_env_encryption_key):
    """Test token encryption works correctly."""
    token = "ghp_test1234567890"

    # Encrypt token
    encrypted = TokenEncryption.encrypt_token(token)
    assert encrypted != token
    assert len(encrypted) > len(token)

    # Decrypt token
    decrypted = TokenEncryption.decrypt_token(encrypted)
    assert decrypted == token


@pytest.mark.asyncio
async def test_token_encryption_missing_key():
    """Test encryption fails without environment key."""
    with pytest.raises(ValueError, match="GITHUB_TOKEN_ENCRYPTION_KEY not set"):
        TokenEncryption.get_encryption_key()


# ============= Authentication & Repository Tests =============


@pytest.mark.asyncio
async def test_verify_token_success(github_api_client, mock_github_client, mock_user):
    """Test successful token verification."""
    mock_github_client.get_user.return_value = mock_user
    mock_github_client.get_rate_limit.return_value = Mock()

    # Mock the scopes attribute
    mock_requester = Mock()
    mock_requester.oauth_scopes = ["repo", "user"]
    mock_github_client._Github__requester = mock_requester

    result = await github_api_client.verify_token()

    assert result["login"] == "testuser"
    assert result["name"] == "Test User"
    assert result["email"] == "test@example.com"
    assert result["avatar_url"] == "https://github.com/avatar/test"
    assert result["scopes"] == ["repo", "user"]


@pytest.mark.asyncio
async def test_verify_token_invalid(
    github_api_client, mock_github_client, mock_github_exception_401
):
    """Test token verification with invalid token."""
    mock_github_client.get_user.side_effect = mock_github_exception_401

    with pytest.raises(GitHubAuthenticationError) as exc_info:
        await github_api_client.verify_token()

    assert exc_info.value.status_code == 401


@pytest.mark.asyncio
async def test_get_repository_success(github_api_client, mock_github_client, mock_repository):
    """Test successful repository retrieval."""
    mock_github_client.get_repo.return_value = mock_repository

    result = await github_api_client.get_repository("owner", "test-repo")

    assert result["name"] == "test-repo"
    assert result["full_name"] == "owner/test-repo"
    assert result["description"] == "Test repository"
    assert result["default_branch"] == "main"
    assert result["private"] is False
    mock_github_client.get_repo.assert_called_once_with("owner/test-repo")


@pytest.mark.asyncio
async def test_get_repository_not_found(
    github_api_client, mock_github_client, mock_github_exception_404
):
    """Test repository not found error."""
    mock_github_client.get_repo.side_effect = mock_github_exception_404

    with pytest.raises(GitHubRepositoryNotFoundError):
        await github_api_client.get_repository("owner", "nonexistent")


@pytest.mark.asyncio
async def test_check_repository_access_success(
    github_api_client, mock_github_client, mock_repository
):
    """Test successful repository access check."""
    mock_github_client.get_repo.return_value = mock_repository

    result = await github_api_client.check_repository_access("owner", "test-repo")

    assert result is True


@pytest.mark.asyncio
async def test_check_repository_access_denied(
    github_api_client, mock_github_client, mock_github_exception_404
):
    """Test repository access check when access denied."""
    mock_github_client.get_repo.side_effect = mock_github_exception_404

    result = await github_api_client.check_repository_access("owner", "private-repo")

    assert result is False


@pytest.mark.asyncio
async def test_get_repository_branches(
    github_api_client, mock_github_client, mock_repository, mock_branch
):
    """Test getting repository branches."""
    mock_github_client.get_repo.return_value = mock_repository
    mock_repository.get_branches.return_value = [mock_branch]

    result = await github_api_client.get_repository_branches("owner", "test-repo")

    assert result == ["main"]


@pytest.mark.asyncio
async def test_get_default_branch(github_api_client, mock_github_client, mock_repository):
    """Test getting default branch."""
    mock_github_client.get_repo.return_value = mock_repository

    result = await github_api_client.get_default_branch("owner", "test-repo")

    assert result == "main"


# ============= Pull Request Tests =============


@pytest.mark.asyncio
async def test_create_pull_request(
    github_api_client, mock_github_client, mock_repository, mock_pull_request
):
    """Test creating pull request."""
    mock_github_client.get_repo.return_value = mock_repository
    mock_repository.create_pull.return_value = mock_pull_request

    result = await github_api_client.create_pull_request(
        owner="owner",
        repo="test-repo",
        title="Test PR",
        body="Test description",
        head="feature/test",
        base="main",
        draft=False,
    )

    assert result["number"] == 123
    assert result["title"] == "Test PR"
    assert result["state"] == "open"
    assert result["head_branch"] == "feature/test"
    assert result["base_branch"] == "main"


@pytest.mark.asyncio
async def test_get_pull_request(
    github_api_client, mock_github_client, mock_repository, mock_pull_request
):
    """Test getting pull request details."""
    mock_github_client.get_repo.return_value = mock_repository
    mock_repository.get_pull.return_value = mock_pull_request

    result = await github_api_client.get_pull_request("owner", "test-repo", 123)

    assert result["number"] == 123
    assert result["title"] == "Test PR"
    assert result["state"] == "open"
    assert result["additions"] == 10
    assert result["deletions"] == 5


@pytest.mark.asyncio
async def test_get_pull_request_not_found(
    github_api_client, mock_github_client, mock_repository, mock_github_exception_404
):
    """Test getting non-existent pull request."""
    mock_github_client.get_repo.return_value = mock_repository
    mock_repository.get_pull.side_effect = GithubException(
        status=404,
        data={"message": "Pull request not found"},
        headers={},
    )

    with pytest.raises(GitHubPullRequestError):
        await github_api_client.get_pull_request("owner", "test-repo", 999)


@pytest.mark.asyncio
async def test_list_pull_requests(
    github_api_client, mock_github_client, mock_repository, mock_pull_request
):
    """Test listing pull requests."""
    mock_github_client.get_repo.return_value = mock_repository
    mock_repository.get_pulls.return_value = [mock_pull_request]

    result = await github_api_client.list_pull_requests(
        owner="owner",
        repo="test-repo",
        state="open",
    )

    assert len(result) == 1
    assert result[0]["number"] == 123
    assert result[0]["title"] == "Test PR"


@pytest.mark.asyncio
async def test_update_pull_request(
    github_api_client, mock_github_client, mock_repository, mock_pull_request
):
    """Test updating pull request."""
    mock_github_client.get_repo.return_value = mock_repository
    mock_repository.get_pull.return_value = mock_pull_request

    result = await github_api_client.update_pull_request(
        owner="owner",
        repo="test-repo",
        pr_number=123,
        title="Updated Title",
    )

    assert result["number"] == 123
    mock_pull_request.edit.assert_called_once_with(title="Updated Title")


@pytest.mark.asyncio
async def test_merge_pull_request(
    github_api_client,
    mock_github_client,
    mock_repository,
    mock_pull_request,
    mock_merge_result,
):
    """Test merging pull request."""
    mock_github_client.get_repo.return_value = mock_repository
    mock_repository.get_pull.return_value = mock_pull_request
    mock_pull_request.merge.return_value = mock_merge_result

    result = await github_api_client.merge_pull_request(
        owner="owner",
        repo="test-repo",
        pr_number=123,
        merge_method="squash",
    )

    assert result["merged"] is True
    assert result["sha"] == "merged123abc"


@pytest.mark.asyncio
async def test_merge_pull_request_not_mergeable(
    github_api_client, mock_github_client, mock_repository, mock_pull_request
):
    """Test merging unmergeable pull request."""
    mock_github_client.get_repo.return_value = mock_repository
    mock_pull_request.mergeable = False
    mock_repository.get_pull.return_value = mock_pull_request

    with pytest.raises(GitHubPullRequestError, match="not mergeable"):
        await github_api_client.merge_pull_request("owner", "test-repo", 123)


@pytest.mark.asyncio
async def test_get_pr_commits(
    github_api_client, mock_github_client, mock_repository, mock_pull_request, mock_commit
):
    """Test getting PR commits."""
    mock_github_client.get_repo.return_value = mock_repository
    mock_repository.get_pull.return_value = mock_pull_request
    mock_pull_request.get_commits.return_value = [mock_commit]

    result = await github_api_client.get_pr_commits("owner", "test-repo", 123)

    assert len(result) == 1
    assert result[0]["sha"] == "abc123def456"
    assert result[0]["message"] == "feat: add new feature"


@pytest.mark.asyncio
async def test_get_pr_files(
    github_api_client,
    mock_github_client,
    mock_repository,
    mock_pull_request,
    mock_commit_file,
):
    """Test getting PR files."""
    mock_github_client.get_repo.return_value = mock_repository
    mock_repository.get_pull.return_value = mock_pull_request
    mock_pull_request.get_files.return_value = [mock_commit_file]

    result = await github_api_client.get_pr_files("owner", "test-repo", 123)

    assert len(result) == 1
    assert result[0]["filename"] == "src/test.py"
    assert result[0]["status"] == "modified"
    assert result[0]["additions"] == 10


@pytest.mark.asyncio
async def test_get_pr_reviews(
    github_api_client, mock_github_client, mock_repository, mock_pull_request, mock_review
):
    """Test getting PR reviews."""
    mock_github_client.get_repo.return_value = mock_repository
    mock_repository.get_pull.return_value = mock_pull_request
    mock_pull_request.get_reviews.return_value = [mock_review]

    result = await github_api_client.get_pr_reviews("owner", "test-repo", 123)

    assert len(result) == 1
    assert result[0]["state"] == "APPROVED"
    assert result[0]["user"] == "reviewer"


@pytest.mark.asyncio
async def test_get_pr_checks(
    github_api_client,
    mock_github_client,
    mock_repository,
    mock_pull_request,
    mock_commit,
    mock_check_runs,
):
    """Test getting PR checks."""
    mock_github_client.get_repo.return_value = mock_repository
    mock_repository.get_pull.return_value = mock_pull_request
    mock_repository.get_commit.return_value = mock_commit
    mock_commit.get_check_runs.return_value = mock_check_runs

    result = await github_api_client.get_pr_checks("owner", "test-repo", 123)

    assert result["total_count"] == 1
    assert len(result["checks"]) == 1
    assert result["checks"][0]["status"] == "completed"


@pytest.mark.asyncio
async def test_add_pr_comment(
    github_api_client,
    mock_github_client,
    mock_repository,
    mock_pull_request,
    mock_issue_comment,
):
    """Test adding comment to PR."""
    mock_github_client.get_repo.return_value = mock_repository
    mock_repository.get_pull.return_value = mock_pull_request
    mock_pull_request.create_issue_comment.return_value = mock_issue_comment

    result = await github_api_client.add_pr_comment(
        owner="owner",
        repo="test-repo",
        pr_number=123,
        body="Test comment",
    )

    assert result["id"] == 333444
    assert result["body"] == "Test comment"
    assert result["user"] == "testuser"


# ============= Webhook Tests =============


@pytest.mark.asyncio
async def test_create_webhook(github_api_client, mock_github_client, mock_repository, mock_webhook):
    """Test creating webhook."""
    mock_github_client.get_repo.return_value = mock_repository
    mock_repository.create_hook.return_value = mock_webhook

    result = await github_api_client.create_webhook(
        owner="owner",
        repo="test-repo",
        webhook_url="https://example.com/webhook",
        events=["pull_request", "push"],
        secret="secret123",
    )

    assert result["id"] == 999
    assert result["url"] == "https://example.com/webhook"
    assert result["events"] == ["pull_request", "push"]
    assert result["active"] is True


@pytest.mark.asyncio
async def test_list_webhooks(github_api_client, mock_github_client, mock_repository, mock_webhook):
    """Test listing webhooks."""
    mock_github_client.get_repo.return_value = mock_repository
    mock_repository.get_hooks.return_value = [mock_webhook]

    result = await github_api_client.list_webhooks("owner", "test-repo")

    assert len(result) == 1
    assert result[0]["id"] == 999
    assert result[0]["active"] is True


@pytest.mark.asyncio
async def test_get_webhook(github_api_client, mock_github_client, mock_repository, mock_webhook):
    """Test getting specific webhook."""
    mock_github_client.get_repo.return_value = mock_repository
    mock_repository.get_hook.return_value = mock_webhook

    result = await github_api_client.get_webhook("owner", "test-repo", 999)

    assert result["id"] == 999
    assert result["url"] == "https://example.com/webhook"


@pytest.mark.asyncio
async def test_update_webhook(github_api_client, mock_github_client, mock_repository, mock_webhook):
    """Test updating webhook."""
    mock_github_client.get_repo.return_value = mock_repository
    mock_repository.get_hook.return_value = mock_webhook

    result = await github_api_client.update_webhook(
        owner="owner",
        repo="test-repo",
        webhook_id=999,
        active=False,
    )

    assert result["id"] == 999
    mock_webhook.edit.assert_called_once()


@pytest.mark.asyncio
async def test_delete_webhook(github_api_client, mock_github_client, mock_repository, mock_webhook):
    """Test deleting webhook."""
    mock_github_client.get_repo.return_value = mock_repository
    mock_repository.get_hook.return_value = mock_webhook

    # Should not raise exception
    await github_api_client.delete_webhook("owner", "test-repo", 999)

    mock_webhook.delete.assert_called_once()


# ============= Commit & Status Tests =============


@pytest.mark.asyncio
async def test_get_commit(github_api_client, mock_github_client, mock_repository, mock_commit):
    """Test getting commit details."""
    mock_github_client.get_repo.return_value = mock_repository
    mock_repository.get_commit.return_value = mock_commit

    result = await github_api_client.get_commit("owner", "test-repo", "abc123")

    assert result["sha"] == "abc123def456"
    assert result["message"] == "feat: add new feature"
    assert result["author"] == "Test User"
    assert result["stats"]["additions"] == 100
    assert result["files_count"] == 5


@pytest.mark.asyncio
async def test_create_commit_status(
    github_api_client,
    mock_github_client,
    mock_repository,
    mock_commit,
    mock_commit_status,
):
    """Test creating commit status."""
    mock_github_client.get_repo.return_value = mock_repository
    mock_repository.get_commit.return_value = mock_commit
    mock_commit.create_status.return_value = mock_commit_status

    result = await github_api_client.create_commit_status(
        owner="owner",
        repo="test-repo",
        sha="abc123",
        state="success",
        description="All tests passed",
        context="ardha/tests",
    )

    assert result["state"] == "success"
    assert result["context"] == "ardha/tests"


@pytest.mark.asyncio
async def test_get_commit_statuses(
    github_api_client,
    mock_github_client,
    mock_repository,
    mock_commit,
    mock_commit_status,
):
    """Test getting commit statuses."""
    mock_github_client.get_repo.return_value = mock_repository
    mock_repository.get_commit.return_value = mock_commit
    mock_commit.get_statuses.return_value = [mock_commit_status]

    result = await github_api_client.get_commit_statuses("owner", "test-repo", "abc123")

    assert len(result) == 1
    assert result[0]["state"] == "success"


# ============= User & Rate Limit Tests =============


@pytest.mark.asyncio
async def test_get_authenticated_user(github_api_client, mock_github_client, mock_user):
    """Test getting authenticated user."""
    mock_github_client.get_user.return_value = mock_user

    result = await github_api_client.get_authenticated_user()

    assert result["login"] == "testuser"
    assert result["name"] == "Test User"
    assert result["email"] == "test@example.com"


@pytest.mark.asyncio
async def test_get_rate_limit(github_api_client, mock_github_client, mock_rate_limit):
    """Test getting rate limit."""
    mock_github_client.get_rate_limit.return_value = mock_rate_limit

    result = await github_api_client.get_rate_limit()

    assert result["limit"] == 5000
    assert result["remaining"] == 4999
    assert result["used"] == 1


# ============= Error Handling Tests =============


@pytest.mark.asyncio
async def test_handle_authentication_error(
    github_api_client, mock_github_client, mock_github_exception_401
):
    """Test handling 401 authentication error."""
    mock_github_client.get_user.side_effect = mock_github_exception_401

    with pytest.raises(GitHubAuthenticationError) as exc_info:
        await github_api_client.verify_token()

    assert exc_info.value.status_code == 401
    assert "Bad credentials" in str(exc_info.value)


@pytest.mark.asyncio
async def test_handle_rate_limit_error(
    github_api_client, mock_github_client, mock_github_exception_429
):
    """Test handling 429 rate limit error."""
    mock_github_client.get_user.side_effect = mock_github_exception_429

    with pytest.raises(GitHubRateLimitError) as exc_info:
        await github_api_client.verify_token()

    assert exc_info.value.reset_at is not None
    assert "rate limit exceeded" in str(exc_info.value).lower()


@pytest.mark.asyncio
async def test_handle_not_found_error(
    github_api_client, mock_github_client, mock_github_exception_404
):
    """Test handling 404 not found error."""
    mock_github_client.get_repo.side_effect = mock_github_exception_404

    with pytest.raises(GitHubRepositoryNotFoundError):
        await github_api_client.get_repository("owner", "nonexistent")


@pytest.mark.asyncio
async def test_handle_permission_error(
    github_api_client, mock_github_client, mock_github_exception_422
):
    """Test handling 422 permission error."""
    mock_github_client.get_repo.side_effect = mock_github_exception_422

    with pytest.raises(GitHubPermissionError):
        await github_api_client.get_repository("owner", "test-repo")


# ============= Async Operation Tests =============


@pytest.mark.asyncio
async def test_async_operation(github_api_client, mock_github_client, mock_user):
    """Test that operations run asynchronously."""
    mock_github_client.get_user.return_value = mock_user

    # This should not block
    result = await github_api_client.get_authenticated_user()

    assert result["login"] == "testuser"


@pytest.mark.asyncio
async def test_client_close(github_api_client):
    """Test client cleanup."""
    await github_api_client.close()

    # Client should be None after close
    assert github_api_client._client is None


# ============= Edge Cases =============


@pytest.mark.asyncio
async def test_list_prs_with_base_filter(
    github_api_client, mock_github_client, mock_repository, mock_pull_request
):
    """Test listing PRs with base branch filter."""
    mock_github_client.get_repo.return_value = mock_repository

    # Create mock PRs with different base branches
    pr1 = Mock()
    pr1.number = 1
    pr1.id = 1
    pr1.title = "PR to main"
    pr1.state = "open"
    pr1.html_url = "https://github.com/owner/repo/pull/1"
    pr1.draft = False
    pr1.head = Mock(ref="feature/1")
    pr1.base = Mock(ref="main")
    pr1.user = Mock(login="user1")
    pr1.created_at = datetime(2024, 11, 1, tzinfo=timezone.utc)

    pr2 = Mock()
    pr2.number = 2
    pr2.id = 2
    pr2.title = "PR to dev"
    pr2.state = "open"
    pr2.html_url = "https://github.com/owner/repo/pull/2"
    pr2.draft = False
    pr2.head = Mock(ref="feature/2")
    pr2.base = Mock(ref="dev")
    pr2.user = Mock(login="user2")
    pr2.created_at = datetime(2024, 11, 2, tzinfo=timezone.utc)

    mock_repository.get_pulls.return_value = [pr1, pr2]

    result = await github_api_client.list_pull_requests(
        owner="owner",
        repo="test-repo",
        state="open",
        base="main",
    )

    # Should only return PR to main
    assert len(result) == 1
    assert result[0]["number"] == 1
    assert result[0]["base_branch"] == "main"


@pytest.mark.asyncio
async def test_create_pr_as_draft(
    github_api_client, mock_github_client, mock_repository, mock_pull_request
):
    """Test creating draft pull request."""
    mock_github_client.get_repo.return_value = mock_repository
    mock_pull_request.draft = True
    mock_repository.create_pull.return_value = mock_pull_request

    result = await github_api_client.create_pull_request(
        owner="owner",
        repo="test-repo",
        title="Draft PR",
        body="Work in progress",
        head="feature/wip",
        base="main",
        draft=True,
    )

    assert result["draft"] is True
    mock_repository.create_pull.assert_called_once_with(
        title="Draft PR",
        body="Work in progress",
        head="feature/wip",
        base="main",
        draft=True,
    )


@pytest.mark.asyncio
async def test_merge_with_custom_message(
    github_api_client,
    mock_github_client,
    mock_repository,
    mock_pull_request,
    mock_merge_result,
):
    """Test merging PR with custom commit message."""
    mock_github_client.get_repo.return_value = mock_repository
    mock_repository.get_pull.return_value = mock_pull_request
    mock_pull_request.merge.return_value = mock_merge_result

    result = await github_api_client.merge_pull_request(
        owner="owner",
        repo="test-repo",
        pr_number=123,
        commit_message="Custom merge message",
        merge_method="squash",
    )

    assert result["merged"] is True
    mock_pull_request.merge.assert_called_once_with(
        commit_message="Custom merge message",
        merge_method="squash",
    )
