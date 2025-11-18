"""
Test fixtures for GitHub integration tests.

Provides reusable test data for GitHub integrations, pull requests,
and webhook payloads.
"""

from datetime import datetime, timezone
from uuid import UUID, uuid4

import pytest
import pytest_asyncio

from ardha.models.github_integration import GitHubIntegration, PullRequest


@pytest_asyncio.fixture
async def github_integration(test_project: dict, test_user: dict, test_db, mock_env_encryption_key):
    """Create a test GitHub integration with properly encrypted token."""
    from ardha.services.github_api import TokenEncryption

    # Encrypt a test token using the mock encryption key
    encrypted_token = TokenEncryption.encrypt_token("ghp_test_token_123")

    integration = GitHubIntegration(
        project_id=UUID(test_project["id"]),
        repository_owner="testowner",
        repository_name="testrepo",
        repository_url="https://github.com/testowner/testrepo",
        default_branch="main",
        access_token_encrypted=encrypted_token,
        auto_create_pr=False,
        auto_link_tasks=True,
        require_review=True,
        connection_status="connected",
        created_by_user_id=UUID(test_user["user"]["id"]),
    )

    test_db.add(integration)
    await test_db.flush()
    await test_db.refresh(integration)

    return integration


@pytest_asyncio.fixture
async def sample_pull_request(github_integration: GitHubIntegration, test_db):
    """Create a test pull request."""
    pr = PullRequest(
        github_integration_id=github_integration.id,
        project_id=github_integration.project_id,
        pr_number=42,
        github_pr_id=123456789,
        title="Test Pull Request",
        description="This is a test PR\n\nCloses TAS-001",
        state="open",
        head_branch="feature/test",
        base_branch="main",
        head_sha="abc123def456",
        author_github_username="testuser",
        is_draft=False,
        html_url="https://github.com/testowner/testrepo/pull/42",
        api_url="https://api.github.com/repos/testowner/testrepo/pulls/42",
    )

    test_db.add(pr)
    await test_db.flush()
    await test_db.refresh(pr)

    return pr


@pytest.fixture
def mock_github_api_responses():
    """Mock GitHub API responses."""
    return {
        "repository": {
            "name": "testrepo",
            "full_name": "testowner/testrepo",
            "description": "Test repository",
            "url": "https://github.com/testowner/testrepo",
            "clone_url": "https://github.com/testowner/testrepo.git",
            "default_branch": "main",
            "private": False,
            "fork": False,
            "archived": False,
            "created_at": "2024-01-01T00:00:00Z",
            "updated_at": "2024-11-18T00:00:00Z",
        },
        "pull_request": {
            "number": 42,
            "id": 123456789,
            "title": "Test Pull Request",
            "body": "This is a test PR",
            "state": "open",
            "html_url": "https://github.com/testowner/testrepo/pull/42",
            "api_url": "https://api.github.com/repos/testowner/testrepo/pulls/42",
            "head_branch": "feature/test",
            "base_branch": "main",
            "head_sha": "abc123def456",
            "author": "testuser",
            "draft": False,
            "mergeable": True,
            "merged": False,
            "created_at": "2024-11-18T00:00:00Z",
            "updated_at": "2024-11-18T00:00:00Z",
        },
        "webhook": {
            "id": 123456,
            "url": "https://api.ardha.dev/webhooks/github",
            "events": ["pull_request", "push"],
            "active": True,
            "created_at": "2024-11-18T00:00:00Z",
        },
    }


@pytest.fixture
def sample_webhook_payload():
    """Factory for creating webhook payloads."""

    def _create_payload(event_type: str, action: str):
        """Create webhook payload for specified event and action."""
        base_payload = {
            "action": action,
            "repository": {
                "name": "testrepo",
                "owner": {"login": "testowner"},
            },
        }

        if event_type == "pull_request":
            base_payload["pull_request"] = {
                "number": 42,
                "id": 123456789,
                "title": "Test Pull Request",
                "body": "Test PR body",
                "state": "open",
                "merged": False,
                "draft": False,
                "mergeable": True,
                "head": {
                    "ref": "feature/test",
                    "sha": "abc123def456",
                },
                "base": {
                    "ref": "main",
                },
                "user": {
                    "login": "testuser",
                },
                "html_url": "https://github.com/testowner/testrepo/pull/42",
                "url": "https://api.github.com/repos/testowner/testrepo/pulls/42",
                "created_at": "2024-11-18T00:00:00Z",
                "updated_at": "2024-11-18T00:00:00Z",
            }
        elif event_type == "push":
            base_payload["ref"] = "refs/heads/main"
            base_payload["commits"] = [
                {
                    "id": "abc123",
                    "message": "Test commit\n\nCloses TAS-001",
                    "author": {
                        "name": "Test User",
                        "email": "test@example.com",
                    },
                }
            ]
        elif event_type == "check_suite":
            base_payload["check_suite"] = {
                "id": 789,
                "head_sha": "abc123def456",
                "status": "completed",
                "conclusion": "success",
            }
        elif event_type == "pull_request_review":
            base_payload["review"] = {
                "id": 456,
                "state": "approved",
                "body": "Looks good!",
                "user": {
                    "login": "reviewer",
                },
            }
            base_payload["pull_request"] = {
                "number": 42,
            }

        return base_payload

    return _create_payload


@pytest.fixture
def sample_github_integration_data():
    """Sample data for creating GitHub integration."""
    return {
        "repository_owner": "testowner",
        "repository_name": "testrepo",
        "access_token": "ghp_test_token_abc123",
        "auto_create_pr": False,
        "auto_link_tasks": True,
        "require_review": True,
    }


@pytest.fixture
def sample_pr_data():
    """Sample data for creating pull request."""
    return {
        "title": "Add new feature",
        "body": "This PR adds a new feature\n\nImplements TAS-001",
        "head_branch": "feature/new-feature",
        "base_branch": "main",
        "draft": False,
    }


@pytest.fixture
def sample_webhook_setup_data():
    """Sample data for webhook setup."""
    return {
        "webhook_url": "https://api.ardha.dev/webhooks/github",
        "events": ["pull_request", "push", "pull_request_review", "check_suite"],
    }
