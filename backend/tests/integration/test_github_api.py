"""
Integration tests for GitHub API endpoints.

Tests GitHub integration setup, pull request management, webhook processing,
and task automation features.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from tests.fixtures.github_fixtures import (
    github_integration,
    mock_github_api_responses,
    sample_pull_request,
    sample_webhook_payload,
)


@pytest.mark.asyncio
class TestGitHubIntegration:
    """Test GitHub integration CRUD operations."""

    async def test_create_github_integration(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_project: dict,
        mock_github_api_responses,
        mock_env_encryption_key,
    ):
        """Test creating GitHub integration."""
        with patch(
            "ardha.services.github_integration_service.GitHubAPIClient"
        ) as mock_client_class:
            # Setup mocks
            mock_client = AsyncMock()
            mock_client_class.return_value = mock_client
            mock_client.verify_token.return_value = {"login": "testuser"}
            mock_client.check_repository_access.return_value = True
            mock_client.get_repository.return_value = mock_github_api_responses["repository"]
            mock_client.close = AsyncMock()

            # Request data
            request_data = {
                "repository_owner": "testowner",
                "repository_name": "testrepo",
                "access_token": "ghp_test_token_123",
                "auto_create_pr": True,
                "auto_link_tasks": True,
                "require_review": False,
            }

            # Create integration
            response = await client.post(
                f"/api/v1/github/projects/{test_project['id']}/github/integration",
                json=request_data,
                headers=auth_headers,
            )

            assert response.status_code == 201
            data = response.json()
            assert data["repository_owner"] == "testowner"
            assert data["repository_name"] == "testrepo"
            assert data["connection_status"] == "connected"
            assert data["auto_create_pr"] is True
            assert data["auto_link_tasks"] is True
            assert "access_token_encrypted" not in data  # Token not exposed

    async def test_get_github_integration(
        self,
        client: AsyncClient,
        auth_headers: dict,
        github_integration,
    ):
        """Test retrieving GitHub integration."""
        response = await client.get(
            f"/api/v1/github/projects/{github_integration.project_id}/github/integration",
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == str(github_integration.id)
        assert data["repository_owner"] == github_integration.repository_owner
        assert data["repository_name"] == github_integration.repository_name

    async def test_get_integration_not_found(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_project: dict,
    ):
        """Test getting non-existent integration returns 404."""
        response = await client.get(
            f"/api/v1/github/projects/{test_project['id']}/github/integration",
            headers=auth_headers,
        )

        assert response.status_code == 404
        detail = response.json()["detail"].lower()
        assert "not found" in detail or "no github integration" in detail

    async def test_update_github_integration(
        self,
        client: AsyncClient,
        auth_headers: dict,
        github_integration,
    ):
        """Test updating GitHub integration configuration."""
        update_data = {
            "auto_create_pr": False,
            "require_review": True,
        }

        response = await client.patch(
            f"/api/v1/github/projects/{github_integration.project_id}/github/integration",
            json=update_data,
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["auto_create_pr"] is False
        assert data["require_review"] is True

    async def test_delete_github_integration(
        self,
        client: AsyncClient,
        auth_headers: dict,
        github_integration,
    ):
        """Test deleting GitHub integration."""
        with patch(
            "ardha.services.github_integration_service.GitHubAPIClient"
        ) as mock_client_class:
            # Setup mocks
            mock_client = AsyncMock()
            mock_client_class.return_value = mock_client
            mock_client.list_webhooks.return_value = []
            mock_client.close = AsyncMock()

            response = await client.delete(
                f"/api/v1/github/projects/{github_integration.project_id}/github/integration",
                headers=auth_headers,
            )

            assert response.status_code == 200
            assert response.json()["success"] is True

            # Verify integration is deleted
            get_response = await client.get(
                f"/api/v1/github/projects/{github_integration.project_id}/github/integration",
                headers=auth_headers,
            )
            assert get_response.status_code == 404

    async def test_setup_webhook(
        self,
        client: AsyncClient,
        auth_headers: dict,
        github_integration,
        mock_env_encryption_key,
    ):
        """Test setting up GitHub webhook."""
        with patch(
            "ardha.services.github_integration_service.GitHubAPIClient"
        ) as mock_client_class:
            # Setup mocks
            mock_client = AsyncMock()
            mock_client_class.return_value = mock_client
            mock_client.create_webhook.return_value = {
                "id": 123456,
                "url": "https://api.ardha.dev/webhooks/github",
                "events": ["pull_request", "push"],
                "active": True,
            }
            mock_client.close = AsyncMock()

            request_data = {
                "webhook_url": "https://api.ardha.dev/webhooks/github",
                "events": ["pull_request", "push", "pull_request_review"],
            }

            response = await client.post(
                f"/api/v1/github/projects/{github_integration.project_id}/github/webhook",
                json=request_data,
                headers=auth_headers,
            )

            assert response.status_code == 200
            data = response.json()
            assert data["webhook_id"] == 123456
            assert data["webhook_url"] == request_data["webhook_url"]
            assert data["secret_configured"] is True


@pytest.mark.asyncio
class TestPullRequests:
    """Test pull request operations."""

    async def test_create_pull_request(
        self,
        client: AsyncClient,
        auth_headers: dict,
        github_integration,
        mock_github_api_responses,
        mock_env_encryption_key,
    ):
        """Test creating pull request via API."""
        with patch(
            "ardha.services.github_integration_service.GitHubAPIClient"
        ) as mock_client_class:
            # Setup mocks
            mock_client = AsyncMock()
            mock_client_class.return_value = mock_client
            mock_client.create_pull_request.return_value = {
                "number": 99,
                "id": 999999,
                "title": "Add new feature",
                "body": "This PR adds a new feature\n\nCloses TAS-001",
                "state": "open",
                "html_url": "https://github.com/testowner/testrepo/pull/99",
                "api_url": "https://api.github.com/repos/testowner/testrepo/pulls/99",
                "head_branch": "feature/new-feature",
                "base_branch": "main",
                "head_sha": "xyz789",
                "author": "testuser",
                "draft": False,
                "mergeable": True,
                "merged": False,
            }
            mock_client.get_pr_commits.return_value = []
            mock_client.close = AsyncMock()

            request_data = {
                "title": "Add new feature",
                "body": "This PR adds a new feature\n\nCloses TAS-001",
                "head_branch": "feature/new-feature",
                "base_branch": "main",
                "draft": False,
            }

            response = await client.post(
                f"/api/v1/github/projects/{github_integration.project_id}/github/pr",
                json=request_data,
                headers=auth_headers,
            )

            assert response.status_code == 201
            data = response.json()
            assert data["title"] == request_data["title"]
            assert data["pr_number"] == 99

    async def test_list_pull_requests(
        self,
        client: AsyncClient,
        auth_headers: dict,
        github_integration,
        sample_pull_request,
    ):
        """Test listing pull requests."""
        response = await client.get(
            f"/api/v1/github/projects/{github_integration.project_id}/github/prs",
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert "prs" in data
        assert "total" in data
        assert data["total"] >= 1

    async def test_get_pull_request_details(
        self,
        client: AsyncClient,
        auth_headers: dict,
        sample_pull_request,
    ):
        """Test getting PR details with tasks and commits."""
        response = await client.get(
            f"/api/v1/github/github/prs/{sample_pull_request.id}",
            params={"sync_from_github": False},
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == str(sample_pull_request.id)
        assert "linked_tasks" in data
        assert "commits" in data

    async def test_sync_pull_requests(
        self,
        client: AsyncClient,
        auth_headers: dict,
        github_integration,
        mock_github_api_responses,
    ):
        """Test syncing PRs from GitHub."""
        with patch(
            "ardha.services.github_integration_service.GitHubAPIClient"
        ) as mock_client_class:
            # Setup mocks
            mock_client = AsyncMock()
            mock_client_class.return_value = mock_client
            mock_client.list_pull_requests.return_value = [
                mock_github_api_responses["pull_request"]
            ]
            mock_client.get_pull_request.return_value = mock_github_api_responses["pull_request"]
            mock_client.get_pr_commits.return_value = []
            mock_client.close = AsyncMock()

            request_data = {"full_sync": False}

            response = await client.post(
                f"/api/v1/github/projects/{github_integration.project_id}/github/sync",
                json=request_data,
                headers=auth_headers,
            )

            assert response.status_code == 200
            data = response.json()
            assert "synced_count" in data
            assert data["synced_count"] >= 0

    async def test_merge_pull_request(
        self,
        client: AsyncClient,
        auth_headers: dict,
        sample_pull_request,
        test_user,
        mock_env_encryption_key,
    ):
        """Test merging pull request."""
        with patch(
            "ardha.services.github_integration_service.GitHubAPIClient"
        ) as mock_client_class:
            # Setup mocks
            mock_client = AsyncMock()
            mock_client_class.return_value = mock_client
            mock_client.merge_pull_request.return_value = {
                "merged": True,
                "sha": "abc123",
                "message": "Merged successfully",
            }
            mock_client.close = AsyncMock()

            request_data = {
                "merge_method": "squash",
                "commit_message": "Merge feature",
            }

            response = await client.post(
                f"/api/v1/github/github/prs/{sample_pull_request.id}/merge",
                json=request_data,
                headers=auth_headers,
            )

            assert response.status_code == 200
            data = response.json()
            assert data["state"] == "merged"

    async def test_close_pull_request(
        self,
        client: AsyncClient,
        auth_headers: dict,
        sample_pull_request,
        mock_env_encryption_key,
    ):
        """Test closing pull request without merging."""
        with patch(
            "ardha.services.github_integration_service.GitHubAPIClient"
        ) as mock_client_class:
            # Setup mocks
            mock_client = AsyncMock()
            mock_client_class.return_value = mock_client
            mock_client.update_pull_request.return_value = {"state": "closed"}
            mock_client.close = AsyncMock()

            response = await client.post(
                f"/api/v1/github/github/prs/{sample_pull_request.id}/close",
                headers=auth_headers,
            )

            assert response.status_code == 200
            data = response.json()
            assert data["state"] == "closed"


@pytest.mark.asyncio
class TestGitHubWebhooks:
    """Test GitHub webhook processing."""

    async def test_webhook_pr_opened(
        self,
        client: AsyncClient,
        github_integration,
        sample_webhook_payload,
    ):
        """Test processing pull_request opened webhook."""
        payload = sample_webhook_payload("pull_request", "opened")

        # Update payload with correct repository
        payload["repository"]["owner"]["login"] = github_integration.repository_owner
        payload["repository"]["name"] = github_integration.repository_name

        with patch("ardha.api.v1.webhooks.github.process_webhook_async") as mock_process:
            response = await client.post(
                "/api/v1/webhooks/github",
                json=payload,
                headers={
                    "X-GitHub-Event": "pull_request",
                    "X-GitHub-Delivery": "test-delivery-123",
                    "X-Hub-Signature-256": "sha256=fakesignature",
                },
            )

            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "received"
            assert data["event_type"] == "pull_request"

    async def test_webhook_pr_merged(
        self,
        client: AsyncClient,
        github_integration,
        sample_pull_request,
        sample_webhook_payload,
    ):
        """Test processing pull_request closed (merged) webhook."""
        payload = sample_webhook_payload("pull_request", "closed")
        payload["pull_request"]["merged"] = True
        payload["pull_request"]["number"] = sample_pull_request.pr_number
        payload["repository"]["owner"]["login"] = github_integration.repository_owner
        payload["repository"]["name"] = github_integration.repository_name

        with patch("ardha.api.v1.webhooks.github.process_webhook_async") as mock_process:
            response = await client.post(
                "/api/v1/webhooks/github",
                json=payload,
                headers={
                    "X-GitHub-Event": "pull_request",
                    "X-GitHub-Delivery": "test-delivery-merge",
                    "X-Hub-Signature-256": "sha256=fakesignature",
                },
            )

            assert response.status_code == 200

    async def test_webhook_check_suite(
        self,
        client: AsyncClient,
        github_integration,
        sample_webhook_payload,
    ):
        """Test processing check_suite webhook."""
        payload = sample_webhook_payload("check_suite", "completed")
        payload["repository"]["owner"]["login"] = github_integration.repository_owner
        payload["repository"]["name"] = github_integration.repository_name

        with patch("ardha.api.v1.webhooks.github.process_webhook_async") as mock_process:
            response = await client.post(
                "/api/v1/webhooks/github",
                json=payload,
                headers={
                    "X-GitHub-Event": "check_suite",
                    "X-GitHub-Delivery": "test-delivery-checks",
                    "X-Hub-Signature-256": "sha256=fakesignature",
                },
            )

            assert response.status_code == 200

    async def test_webhook_missing_repository(
        self,
        client: AsyncClient,
    ):
        """Test webhook with missing repository information."""
        payload = {"action": "opened"}  # No repository data

        response = await client.post(
            "/api/v1/webhooks/github",
            json=payload,
            headers={
                "X-GitHub-Event": "pull_request",
                "X-GitHub-Delivery": "test-delivery-bad",
                "X-Hub-Signature-256": "sha256=fakesignature",
            },
        )

        assert response.status_code == 400
        assert "repository" in response.json()["detail"].lower()

    async def test_webhook_integration_not_found(
        self,
        client: AsyncClient,
        sample_webhook_payload,
    ):
        """Test webhook for repository with no integration."""
        payload = sample_webhook_payload("pull_request", "opened")
        payload["repository"]["owner"]["login"] = "nonexistent"
        payload["repository"]["name"] = "repo"

        response = await client.post(
            "/api/v1/webhooks/github",
            json=payload,
            headers={
                "X-GitHub-Event": "pull_request",
                "X-GitHub-Delivery": "test-delivery-404",
                "X-Hub-Signature-256": "sha256=fakesignature",
            },
        )

        assert response.status_code == 404


@pytest.mark.asyncio
class TestTaskAutomation:
    """Test automatic task status updates from GitHub events."""

    async def test_task_auto_close_on_pr_merge(
        self,
        client: AsyncClient,
        auth_headers: dict,
        github_integration,
        test_task: dict,
        test_db: AsyncSession,
        mock_env_encryption_key,
    ):
        """Test tasks are auto-closed when PR merges."""
        from uuid import UUID

        from ardha.models.github_integration import PullRequest

        # Create PR that closes the task
        pr = PullRequest(
            github_integration_id=github_integration.id,
            project_id=github_integration.project_id,
            pr_number=123,
            github_pr_id=999,
            title="Fix bug",
            description=f"Closes {test_task['identifier']}",
            state="open",
            head_branch="bugfix",
            base_branch="main",
            head_sha="abc123",
            author_github_username="testuser",
            html_url="https://github.com/test/repo/pull/123",
            api_url="https://api.github.com/repos/test/repo/pulls/123",
            closes_task_ids=[test_task["id"]],
        )

        test_db.add(pr)
        await test_db.flush()
        await test_db.refresh(pr)

        # Mock GitHub API
        with patch(
            "ardha.services.github_integration_service.GitHubAPIClient"
        ) as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value = mock_client
            mock_client.merge_pull_request.return_value = {
                "merged": True,
                "sha": "def456",
                "message": "Merged",
            }
            mock_client.close = AsyncMock()

            # Merge the PR
            response = await client.post(
                f"/api/v1/github/github/prs/{pr.id}/merge",
                json={"merge_method": "merge"},
                headers=auth_headers,
            )

            assert response.status_code == 200

            # Verify task was closed
            from ardha.repositories.task_repository import TaskRepository

            task_repo = TaskRepository(test_db)
            updated_task = await task_repo.get_by_id(UUID(test_task["id"]))
            assert updated_task is not None
            assert updated_task.status == "done"


@pytest.mark.asyncio
class TestGitHubStatistics:
    """Test GitHub statistics endpoints."""

    async def test_get_project_stats(
        self,
        client: AsyncClient,
        auth_headers: dict,
        github_integration,
        sample_pull_request,
    ):
        """Test retrieving GitHub statistics."""
        response = await client.get(
            f"/api/v1/github/projects/{github_integration.project_id}/github/stats",
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert "total_prs" in data
        assert "open_prs" in data
        assert "merged_prs" in data
        assert "contributor_count" in data
        assert isinstance(data["most_active_contributors"], list)

    async def test_verify_connection(
        self,
        client: AsyncClient,
        auth_headers: dict,
        github_integration,
    ):
        """Test verifying GitHub connection status."""
        with patch(
            "ardha.services.github_integration_service.GitHubAPIClient"
        ) as mock_client_class:
            # Setup mocks
            mock_client = AsyncMock()
            mock_client_class.return_value = mock_client
            mock_client.verify_token.return_value = {"login": "testuser"}
            mock_client.check_repository_access.return_value = True
            mock_client.close = AsyncMock()

            response = await client.get(
                f"/api/v1/github/projects/{github_integration.project_id}/github/connection",
                headers=auth_headers,
            )

            assert response.status_code == 200
            data = response.json()
            assert data["connected"] is True
            assert data["token_valid"] is True
            assert data["repository_accessible"] is True


@pytest.mark.asyncio
class TestPermissions:
    """Test GitHub API permission enforcement."""

    async def test_create_integration_requires_admin(
        self,
        client: AsyncClient,
        test_project: dict,
        test_user: dict,
        test_db: AsyncSession,
    ):
        """Test creating integration requires admin role."""
        from uuid import UUID

        from ardha.models.project_member import ProjectMember
        from ardha.models.user import User

        # Create a second user
        second_user = User(
            email="viewer@example.com",
            username="vieweruser",
            full_name="Viewer User",
            password_hash="hashed_password",
        )
        test_db.add(second_user)
        await test_db.flush()
        await test_db.refresh(second_user)

        # Add second user as viewer
        member = ProjectMember(
            project_id=UUID(test_project["id"]),
            user_id=second_user.id,
            role="viewer",
        )
        test_db.add(member)
        await test_db.flush()

        # Create auth token for viewer user
        from ardha.core.security import create_access_token

        viewer_token = create_access_token({"sub": str(second_user.id)})
        viewer_headers = {"Authorization": f"Bearer {viewer_token}"}

        request_data = {
            "repository_owner": "test",
            "repository_name": "repo",
            "access_token": "ghp_test",
        }

        response = await client.post(
            f"/api/v1/github/projects/{test_project['id']}/github/integration",
            json=request_data,
            headers=viewer_headers,
        )

        assert response.status_code == 403

    async def test_viewer_can_access_integration(
        self,
        client: AsyncClient,
        github_integration,
        test_user: dict,
        test_db: AsyncSession,
    ):
        """Test viewer role can view integration."""
        from uuid import UUID

        from ardha.models.project_member import ProjectMember
        from ardha.models.user import User

        # Create a second user
        viewer_user = User(
            email="viewer2@example.com",
            username="viewer2",
            full_name="Viewer Two",
            password_hash="hashed_password",
        )
        test_db.add(viewer_user)
        await test_db.flush()
        await test_db.refresh(viewer_user)

        # Add user as viewer
        member = ProjectMember(
            project_id=github_integration.project_id,
            user_id=viewer_user.id,
            role="viewer",
        )
        test_db.add(member)
        await test_db.flush()

        # Create auth token
        from ardha.core.security import create_access_token

        viewer_token = create_access_token({"sub": str(viewer_user.id)})
        viewer_headers = {"Authorization": f"Bearer {viewer_token}"}

        response = await client.get(
            f"/api/v1/github/projects/{github_integration.project_id}/github/integration",
            headers=viewer_headers,
        )

        assert response.status_code == 200
