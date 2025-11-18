"""
GitHub Integration Service for business logic orchestration.

This module orchestrates GitHub API operations with database persistence,
handling GitHub integration setup, pull request management, webhook configuration,
and task automation.
"""

import logging
import secrets
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from ardha.core.github_exceptions import (
    GitHubAPIError,
    GitHubAuthenticationError,
    GitHubPullRequestError,
)
from ardha.models.github_integration import GitHubIntegration, PullRequest
from ardha.repositories.github_integration import GitHubIntegrationRepository
from ardha.repositories.pull_request import PullRequestRepository
from ardha.services.git_commit_service import GitCommitService
from ardha.services.github_api import GitHubAPIClient, TokenEncryption
from ardha.services.project_service import ProjectService
from ardha.services.task_service import TaskService

logger = logging.getLogger(__name__)


# ============= Custom Exceptions =============


class GitHubIntegrationNotFoundError(Exception):
    """Raised when GitHub integration is not found."""

    pass


class GitHubIntegrationExistsError(Exception):
    """Raised when project already has a GitHub integration."""

    pass


class GitHubPRNotFoundError(Exception):
    """Raised when pull request is not found."""

    pass


class InsufficientGitHubPermissionsError(Exception):
    """Raised when user lacks GitHub integration permissions."""

    pass


# ============= Service Class =============


class GitHubIntegrationService:
    """
    Service layer for GitHub integration management.

    Orchestrates GitHub API operations with database persistence,
    handling integration setup, PR management, webhooks, and task automation.
    """

    def __init__(
        self,
        integration_repo: GitHubIntegrationRepository,
        pr_repo: PullRequestRepository,
        project_service: ProjectService,
        task_service: TaskService,
        db: AsyncSession,
    ):
        """
        Initialize GitHubIntegrationService.

        Args:
            integration_repo: Repository for GitHub integrations
            pr_repo: Repository for pull requests
            project_service: Service for project operations
            task_service: Service for task operations
            db: Async SQLAlchemy database session
        """
        self.integration_repo = integration_repo
        self.pr_repo = pr_repo
        self.project_service = project_service
        self.task_service = task_service
        self.db = db

    # ============= Integration Management =============

    async def create_integration(
        self,
        project_id: UUID,
        repository_owner: str,
        repository_name: str,
        access_token: str,
        user_id: UUID,
        configuration: Optional[Dict] = None,
    ) -> GitHubIntegration:
        """
        Create GitHub integration for a project.

        Verifies user permissions, validates GitHub token, encrypts token,
        checks repository access, and optionally sets up webhook.

        Args:
            project_id: Project UUID
            repository_owner: GitHub username or organization
            repository_name: Repository name
            access_token: GitHub personal access token
            user_id: User creating integration
            configuration: Optional configuration dict

        Returns:
            Created GitHubIntegration

        Raises:
            InsufficientGitHubPermissionsError: If user lacks admin access
            GitHubIntegrationExistsError: If integration already exists
            GitHubAuthenticationError: If token is invalid
            GitHubAPIError: If repository is inaccessible
        """
        # Verify user has admin access to project
        if not await self.project_service.check_permission(
            project_id=project_id,
            user_id=user_id,
            required_role="admin",
        ):
            raise InsufficientGitHubPermissionsError(
                "Must be project admin or owner to create GitHub integration"
            )

        # Check if integration already exists
        existing = await self.integration_repo.get_by_project(project_id)
        if existing:
            raise GitHubIntegrationExistsError(
                f"Project already has GitHub integration for {existing.repository_owner}/"
                f"{existing.repository_name}"
            )

        # Verify token with GitHub API
        client = GitHubAPIClient(access_token)
        try:
            user_info = await client.verify_token()
            logger.info(f"Verified GitHub token for user: {user_info['login']}")
        except GitHubAuthenticationError:
            logger.error("Invalid GitHub access token")
            raise
        finally:
            await client.close()

        # Check repository access
        repo_accessible = await client.check_repository_access(repository_owner, repository_name)
        if not repo_accessible:
            raise GitHubAPIError(
                f"Cannot access repository {repository_owner}/{repository_name}. "
                "Verify the token has repo permissions."
            )

        # Get repository details
        repo_data = await client.get_repository(repository_owner, repository_name)
        await client.close()

        # Encrypt access token
        encrypted_token = TokenEncryption.encrypt_token(access_token)

        # Extract configuration
        config = configuration or {}
        auto_create_pr = config.get("auto_create_pr", False)
        auto_link_tasks = config.get("auto_link_tasks", True)
        require_review = config.get("require_review", True)

        # Create integration
        integration = GitHubIntegration(
            project_id=project_id,
            repository_owner=repository_owner,
            repository_name=repository_name,
            repository_url=repo_data["url"],
            default_branch=repo_data["default_branch"],
            access_token_encrypted=encrypted_token,
            auto_create_pr=auto_create_pr,
            auto_link_tasks=auto_link_tasks,
            require_review=require_review,
            connection_status="connected",
            created_by_user_id=user_id,
        )

        integration = await self.integration_repo.create(integration)
        await self.db.flush()
        await self.db.refresh(integration)

        logger.info(
            f"Created GitHub integration for project {project_id}: "
            f"{repository_owner}/{repository_name}"
        )

        return integration

    async def get_integration(
        self,
        project_id: UUID,
        user_id: UUID,
    ) -> GitHubIntegration:
        """
        Get GitHub integration for a project.

        Args:
            project_id: Project UUID
            user_id: User requesting integration

        Returns:
            GitHubIntegration

        Raises:
            GitHubIntegrationNotFoundError: If integration not found
            InsufficientGitHubPermissionsError: If user lacks access
        """
        # Verify user has project access
        if not await self.project_service.check_permission(
            project_id=project_id,
            user_id=user_id,
            required_role="viewer",
        ):
            raise InsufficientGitHubPermissionsError(
                "Must be project member to view GitHub integration"
            )

        integration = await self.integration_repo.get_by_project(project_id)
        if not integration:
            raise GitHubIntegrationNotFoundError(
                f"No GitHub integration found for project {project_id}"
            )

        return integration

    async def update_integration(
        self,
        project_id: UUID,
        update_data: Dict,
        user_id: UUID,
    ) -> GitHubIntegration:
        """
        Update GitHub integration configuration.

        Args:
            project_id: Project UUID
            update_data: Fields to update
            user_id: User updating integration

        Returns:
            Updated GitHubIntegration

        Raises:
            GitHubIntegrationNotFoundError: If integration not found
            InsufficientGitHubPermissionsError: If user lacks admin access
            GitHubAuthenticationError: If new token is invalid
        """
        # Verify user has admin access
        if not await self.project_service.check_permission(
            project_id=project_id,
            user_id=user_id,
            required_role="admin",
        ):
            raise InsufficientGitHubPermissionsError(
                "Must be project admin or owner to update GitHub integration"
            )

        integration = await self.integration_repo.get_by_project(project_id)
        if not integration:
            raise GitHubIntegrationNotFoundError(
                f"No GitHub integration found for project {project_id}"
            )

        # If updating access token, verify it first
        if "access_token" in update_data:
            new_token = update_data["access_token"]
            client = GitHubAPIClient(new_token)
            try:
                await client.verify_token()
                # Encrypt new token
                update_data["access_token_encrypted"] = TokenEncryption.encrypt_token(new_token)
                del update_data["access_token"]  # Remove plain token
                update_data["connection_status"] = "connected"
                update_data["sync_error"] = None
            except GitHubAuthenticationError:
                logger.error("Invalid GitHub access token during update")
                raise
            finally:
                await client.close()

        # Update integration
        updated_integration = await self.integration_repo.update(integration.id, update_data)

        if not updated_integration:
            raise GitHubIntegrationNotFoundError(
                f"Integration for project {project_id} not found during update"
            )

        await self.db.flush()
        await self.db.refresh(updated_integration)

        logger.info(f"Updated GitHub integration for project {project_id}")
        return updated_integration

    async def delete_integration(
        self,
        project_id: UUID,
        user_id: UUID,
    ) -> bool:
        """
        Delete GitHub integration (cascade to PRs).

        Removes webhooks from GitHub before deleting local records.

        Args:
            project_id: Project UUID
            user_id: User deleting integration

        Returns:
            True if deleted successfully

        Raises:
            GitHubIntegrationNotFoundError: If integration not found
            InsufficientGitHubPermissionsError: If user lacks admin access
        """
        # Verify user has admin access
        if not await self.project_service.check_permission(
            project_id=project_id,
            user_id=user_id,
            required_role="admin",
        ):
            raise InsufficientGitHubPermissionsError(
                "Must be project admin or owner to delete GitHub integration"
            )

        integration = await self.integration_repo.get_by_project(project_id)
        if not integration:
            raise GitHubIntegrationNotFoundError(
                f"No GitHub integration found for project {project_id}"
            )

        # Delete webhooks from GitHub (best effort)
        if integration.webhook_url:
            try:
                token = TokenEncryption.decrypt_token(integration.access_token_encrypted)
                client = GitHubAPIClient(token)
                webhooks = await client.list_webhooks(
                    integration.repository_owner,
                    integration.repository_name,
                )
                # Delete webhooks that match our URL
                for webhook in webhooks:
                    if webhook.get("url") == integration.webhook_url:
                        await client.delete_webhook(
                            integration.repository_owner,
                            integration.repository_name,
                            webhook["id"],
                        )
                await client.close()
            except Exception as e:
                logger.warning(f"Failed to delete webhooks from GitHub: {e}")

        # Delete integration (cascade to PRs and webhook deliveries)
        success = await self.integration_repo.delete(integration.id)
        await self.db.flush()

        logger.info(f"Deleted GitHub integration for project {project_id}")
        return success

    # ============= Pull Request Operations =============

    async def sync_pull_requests(
        self,
        project_id: UUID,
        user_id: UUID,
        full_sync: bool = False,
    ) -> int:
        """
        Sync pull requests from GitHub to database.

        Fetches PRs from GitHub, creates/updates database records,
        links to tasks, and associates with commits.

        Args:
            project_id: Project UUID
            user_id: User requesting sync
            full_sync: If True, sync all PRs; if False, sync only recent

        Returns:
            Count of synced PRs

        Raises:
            GitHubIntegrationNotFoundError: If integration not found
            InsufficientGitHubPermissionsError: If user lacks access
        """
        # Verify user has access
        if not await self.project_service.check_permission(
            project_id=project_id,
            user_id=user_id,
            required_role="member",
        ):
            raise InsufficientGitHubPermissionsError("Must be project member to sync pull requests")

        integration = await self.integration_repo.get_by_project(project_id)
        if not integration:
            raise GitHubIntegrationNotFoundError(
                f"No GitHub integration found for project {project_id}"
            )

        # Create GitHub API client
        token = TokenEncryption.decrypt_token(integration.access_token_encrypted)
        client = GitHubAPIClient(token)

        synced_count = 0

        try:
            # Fetch PRs from GitHub
            state = "all" if full_sync else "open"
            prs_data = await client.list_pull_requests(
                integration.repository_owner,
                integration.repository_name,
                state=state,
            )

            # Process each PR
            for pr_data in prs_data:
                # Check if PR exists
                pr = await self.pr_repo.get_by_number(
                    integration.id,
                    pr_data["number"],
                )

                if pr:
                    # Update existing PR
                    full_pr_data = await client.get_pull_request(
                        integration.repository_owner,
                        integration.repository_name,
                        pr_data["number"],
                    )
                    await self.pr_repo.update_from_github(pr.id, full_pr_data)
                else:
                    # Create new PR
                    full_pr_data = await client.get_pull_request(
                        integration.repository_owner,
                        integration.repository_name,
                        pr_data["number"],
                    )
                    pr = await self._create_pr_from_github(
                        integration,
                        full_pr_data,
                    )

                # Link to tasks (parse PR description)
                await self._link_pr_to_tasks(pr)

                # Link to commits
                await self._link_pr_to_commits(pr, integration, client)

                synced_count += 1

            # Update integration sync timestamp
            await self.integration_repo.update_connection_status(
                integration.id,
                "connected",
            )

            logger.info(
                f"Synced {synced_count} PRs for project {project_id} "
                f"from {integration.repository_owner}/{integration.repository_name}"
            )

        except Exception as e:
            logger.error(f"Error syncing PRs: {e}", exc_info=True)
            await self.integration_repo.update_connection_status(
                integration.id,
                "error",
                str(e),
            )
            raise
        finally:
            await client.close()

        return synced_count

    async def create_pull_request(
        self,
        project_id: UUID,
        title: str,
        body: str,
        head_branch: str,
        base_branch: Optional[str],
        draft: bool,
        user_id: UUID,
        linked_task_ids: Optional[List[UUID]] = None,
    ) -> PullRequest:
        """
        Create pull request on GitHub and database.

        Args:
            project_id: Project UUID
            title: PR title
            body: PR description
            head_branch: Source branch
            base_branch: Target branch (defaults to repo default)
            draft: Create as draft PR
            user_id: User creating PR
            linked_task_ids: Optional task UUIDs to link

        Returns:
            Created PullRequest

        Raises:
            GitHubIntegrationNotFoundError: If integration not found
            InsufficientGitHubPermissionsError: If user lacks access
            GitHubPullRequestError: If PR creation fails
        """
        # Verify user has access
        if not await self.project_service.check_permission(
            project_id=project_id,
            user_id=user_id,
            required_role="member",
        ):
            raise InsufficientGitHubPermissionsError(
                "Must be project member to create pull requests"
            )

        integration = await self.integration_repo.get_by_project(project_id)
        if not integration:
            raise GitHubIntegrationNotFoundError(
                f"No GitHub integration found for project {project_id}"
            )

        # Use default branch if base not specified
        if not base_branch:
            base_branch = integration.default_branch

        # Create GitHub API client
        token = TokenEncryption.decrypt_token(integration.access_token_encrypted)
        client = GitHubAPIClient(token)

        try:
            # Create PR on GitHub
            pr_data = await client.create_pull_request(
                integration.repository_owner,
                integration.repository_name,
                title=title,
                body=body,
                head=head_branch,
                base=base_branch,
                draft=draft,
            )

            # Create PR in database
            pr = await self._create_pr_from_github(
                integration,
                pr_data,
                author_user_id=user_id,
            )

            # Store pr_number before any session issues
            pr_number = pr.pr_number
            pr_id = pr.id

            # Link to tasks if provided
            if linked_task_ids:
                await self.pr_repo.link_to_tasks(
                    pr_id,
                    linked_task_ids,
                    link_type="implements",
                    linked_from="pr_creation",
                )

            # Update statistics
            await self.integration_repo.update_statistics(
                integration.id,
                total_prs=1,
            )

            # Refresh PR to ensure all attributes are loaded
            await self.db.refresh(pr)

            logger.info(f"Created PR #{pr_number} for project {project_id}: {title}")

            return pr

        finally:
            await client.close()

    async def get_pull_request(
        self,
        pr_id: UUID,
        user_id: UUID,
        sync_from_github: bool = False,
    ) -> PullRequest:
        """
        Get pull request details.

        Args:
            pr_id: PR UUID
            user_id: User requesting PR
            sync_from_github: If True, fetch latest from GitHub first

        Returns:
            PullRequest

        Raises:
            GitHubPRNotFoundError: If PR not found
            InsufficientGitHubPermissionsError: If user lacks access
        """
        pr = await self.pr_repo.get_by_id(pr_id)
        if not pr:
            raise GitHubPRNotFoundError(f"Pull request {pr_id} not found")

        # Verify user has project access
        if not await self.project_service.check_permission(
            project_id=pr.project_id,
            user_id=user_id,
            required_role="viewer",
        ):
            raise InsufficientGitHubPermissionsError("Must be project member to view pull requests")

        # Optionally sync from GitHub
        if sync_from_github:
            pr = await self.update_pull_request_from_github(pr_id)

        return pr

    async def update_pull_request_from_github(
        self,
        pr_id: UUID,
    ) -> PullRequest:
        """
        Update PR with latest data from GitHub.

        Args:
            pr_id: PR UUID

        Returns:
            Updated PullRequest

        Raises:
            GitHubPRNotFoundError: If PR not found
        """
        pr = await self.pr_repo.get_by_id(pr_id)
        if not pr:
            raise GitHubPRNotFoundError(f"Pull request {pr_id} not found")

        integration = await self.integration_repo.get_by_id(pr.github_integration_id)
        if not integration:
            raise GitHubIntegrationNotFoundError(
                f"GitHub integration {pr.github_integration_id} not found"
            )

        # Create GitHub API client
        token = TokenEncryption.decrypt_token(integration.access_token_encrypted)
        client = GitHubAPIClient(token)

        try:
            # Fetch latest PR data from GitHub
            pr_data = await client.get_pull_request(
                integration.repository_owner,
                integration.repository_name,
                pr.pr_number,
            )

            # Update database record
            updated_pr = await self.pr_repo.update_from_github(pr.id, pr_data)

            if not updated_pr:
                raise GitHubPRNotFoundError(f"PR {pr_id} not found during update")

            # Update linked commits if head SHA changed
            if pr_data.get("head_sha") != updated_pr.head_sha:
                await self._link_pr_to_commits(updated_pr, integration, client)

            logger.info(f"Updated PR #{updated_pr.pr_number} from GitHub")

        finally:
            await client.close()

        return updated_pr

    async def merge_pull_request(
        self,
        pr_id: UUID,
        user_id: UUID,
        merge_method: str = "merge",
        commit_message: Optional[str] = None,
    ) -> PullRequest:
        """
        Merge pull request on GitHub.

        Automatically closes linked tasks that have "closes" link type.

        Args:
            pr_id: PR UUID
            user_id: User merging PR
            merge_method: Merge method (merge, squash, rebase)
            commit_message: Optional merge commit message

        Returns:
            Merged PullRequest

        Raises:
            GitHubPRNotFoundError: If PR not found
            InsufficientGitHubPermissionsError: If user lacks admin access
            GitHubPullRequestError: If PR is not mergeable
        """
        pr = await self.pr_repo.get_by_id(pr_id)
        if not pr:
            raise GitHubPRNotFoundError(f"Pull request {pr_id} not found")

        # Verify user has admin access
        if not await self.project_service.check_permission(
            project_id=pr.project_id,
            user_id=user_id,
            required_role="admin",
        ):
            raise InsufficientGitHubPermissionsError(
                "Must be project admin or owner to merge pull requests"
            )

        integration = await self.integration_repo.get_by_id(pr.github_integration_id)
        if not integration:
            raise GitHubIntegrationNotFoundError(
                f"GitHub integration {pr.github_integration_id} not found"
            )

        # Check if PR is mergeable
        if pr.mergeable is False:
            raise GitHubPullRequestError(
                f"PR #{pr.pr_number} is not mergeable",
                pr_number=pr.pr_number,
                operation="merge",
            )

        # Create GitHub API client
        token = TokenEncryption.decrypt_token(integration.access_token_encrypted)
        client = GitHubAPIClient(token)

        try:
            # Merge PR on GitHub
            merge_result = await client.merge_pull_request(
                integration.repository_owner,
                integration.repository_name,
                pr.pr_number,
                commit_message=commit_message,
                merge_method=merge_method,
            )

            # Update PR state
            updated_pr = await self.pr_repo.update_state(
                pr.id,
                "merged",
                merged_at=datetime.now(timezone.utc),
            )

            if not updated_pr:
                raise GitHubPRNotFoundError(f"PR {pr_id} not found during merge")

            # Store attributes before session issues
            pr_number = updated_pr.pr_number
            closes_task_ids = updated_pr.closes_task_ids

            # Close linked tasks
            if closes_task_ids:
                for task_id_str in closes_task_ids:
                    try:
                        task_id = UUID(task_id_str)
                        await self.task_service.update_status(
                            task_id=task_id,
                            user_id=user_id,
                            new_status="done",
                        )
                        logger.info(f"Auto-closed task {task_id} from PR merge")
                    except Exception as e:
                        logger.warning(f"Failed to auto-close task {task_id_str}: {e}")

            # Update statistics
            await self.integration_repo.update_statistics(
                integration.id,
                merged_prs=1,
            )

            # Refresh to ensure all attributes loaded
            await self.db.refresh(updated_pr)

            logger.info(f"Merged PR #{pr_number} using {merge_method} method")

        finally:
            await client.close()

        return updated_pr

    async def close_pull_request(
        self,
        pr_id: UUID,
        user_id: UUID,
    ) -> PullRequest:
        """
        Close pull request on GitHub without merging.

        Args:
            pr_id: PR UUID
            user_id: User closing PR

        Returns:
            Closed PullRequest

        Raises:
            GitHubPRNotFoundError: If PR not found
            InsufficientGitHubPermissionsError: If user lacks access
        """
        pr = await self.pr_repo.get_by_id(pr_id)
        if not pr:
            raise GitHubPRNotFoundError(f"Pull request {pr_id} not found")

        # Verify user has access
        if not await self.project_service.check_permission(
            project_id=pr.project_id,
            user_id=user_id,
            required_role="member",
        ):
            raise InsufficientGitHubPermissionsError(
                "Must be project member to close pull requests"
            )

        integration = await self.integration_repo.get_by_id(pr.github_integration_id)
        if not integration:
            raise GitHubIntegrationNotFoundError(
                f"GitHub integration {pr.github_integration_id} not found"
            )

        # Create GitHub API client
        token = TokenEncryption.decrypt_token(integration.access_token_encrypted)
        client = GitHubAPIClient(token)

        try:
            # Close PR on GitHub
            await client.update_pull_request(
                integration.repository_owner,
                integration.repository_name,
                pr.pr_number,
                state="closed",
            )

            # Update PR state
            updated_pr = await self.pr_repo.update_state(
                pr.id,
                "closed",
                closed_at=datetime.now(timezone.utc),
            )

            if not updated_pr:
                raise GitHubPRNotFoundError(f"PR {pr_id} not found during close")

            # Store pr_number before session issues
            pr_number = updated_pr.pr_number

            # Update statistics
            await self.integration_repo.update_statistics(
                integration.id,
                closed_prs=1,
            )

            # Refresh to ensure all attributes loaded
            await self.db.refresh(updated_pr)

            logger.info(f"Closed PR #{pr_number} without merging")

        finally:
            await client.close()

        return updated_pr

    # ============= Webhook Management =============

    async def setup_webhook(
        self,
        project_id: UUID,
        webhook_url: str,
        events: List[str],
        user_id: UUID,
    ) -> Dict:
        """
        Setup GitHub webhook for repository.

        Args:
            project_id: Project UUID
            webhook_url: Webhook callback URL
            events: List of webhook events
            user_id: User setting up webhook

        Returns:
            Dict with webhook data

        Raises:
            GitHubIntegrationNotFoundError: If integration not found
            InsufficientGitHubPermissionsError: If user lacks admin access
        """
        # Verify user has admin access
        if not await self.project_service.check_permission(
            project_id=project_id,
            user_id=user_id,
            required_role="admin",
        ):
            raise InsufficientGitHubPermissionsError(
                "Must be project admin or owner to setup webhooks"
            )

        integration = await self.integration_repo.get_by_project(project_id)
        if not integration:
            raise GitHubIntegrationNotFoundError(
                f"No GitHub integration found for project {project_id}"
            )

        # Generate webhook secret
        webhook_secret = secrets.token_urlsafe(32)

        # Create GitHub API client
        token = TokenEncryption.decrypt_token(integration.access_token_encrypted)
        client = GitHubAPIClient(token)

        try:
            # Create webhook via GitHub API
            webhook_data = await client.create_webhook(
                integration.repository_owner,
                integration.repository_name,
                webhook_url=webhook_url,
                events=events,
                secret=webhook_secret,
            )

            # Update integration with webhook info
            await self.integration_repo.update(
                integration.id,
                {
                    "webhook_secret": webhook_secret,
                    "webhook_url": webhook_url,
                    "webhook_events": events,
                },
            )

            logger.info(
                f"Created webhook for {integration.repository_owner}/"
                f"{integration.repository_name}"
            )

            return webhook_data

        finally:
            await client.close()

    async def verify_connection(self, project_id: UUID, user_id: UUID) -> Dict:
        """
        Verify GitHub connection status.

        Tests token validity and repository access.

        Args:
            project_id: Project UUID
            user_id: User requesting verification

        Returns:
            Dict with connection status information

        Raises:
            GitHubIntegrationNotFoundError: If integration not found
            InsufficientGitHubPermissionsError: If user lacks access
        """
        # Verify user has access
        if not await self.project_service.check_permission(
            project_id=project_id,
            user_id=user_id,
            required_role="viewer",
        ):
            raise InsufficientGitHubPermissionsError("Must be project member to verify connection")

        integration = await self.integration_repo.get_by_project(project_id)
        if not integration:
            raise GitHubIntegrationNotFoundError(
                f"No GitHub integration found for project {project_id}"
            )

        # Create GitHub API client
        token = TokenEncryption.decrypt_token(integration.access_token_encrypted)
        client = GitHubAPIClient(token)

        connection_info = {
            "connected": False,
            "connection_status": "disconnected",
            "repository_accessible": False,
            "token_valid": False,
            "webhook_configured": bool(integration.webhook_url),
            "last_sync_at": integration.last_sync_at,
            "error_message": None,
        }

        try:
            # Verify token
            await client.verify_token()
            connection_info["token_valid"] = True

            # Check repository access
            repo_accessible = await client.check_repository_access(
                integration.repository_owner,
                integration.repository_name,
            )
            connection_info["repository_accessible"] = repo_accessible

            if repo_accessible:
                connection_info["connected"] = True
                connection_info["connection_status"] = "connected"

                # Update integration status
                await self.integration_repo.update_connection_status(
                    integration.id,
                    "connected",
                )
            else:
                connection_info["connection_status"] = "error"
                connection_info["error_message"] = "Repository not accessible"

                await self.integration_repo.update_connection_status(
                    integration.id,
                    "error",
                    "Repository not accessible",
                )

        except GitHubAuthenticationError as e:
            connection_info["connection_status"] = "unauthorized"
            connection_info["error_message"] = str(e)

            await self.integration_repo.update_connection_status(
                integration.id,
                "unauthorized",
                str(e),
            )

        except Exception as e:
            connection_info["connection_status"] = "error"
            connection_info["error_message"] = str(e)

            await self.integration_repo.update_connection_status(
                integration.id,
                "error",
                str(e),
            )

        finally:
            await client.close()

        logger.info(
            f"Verified connection for project {project_id}: "
            f"{connection_info['connection_status']}"
        )

        return connection_info

    async def get_pr_checks(self, pr_id: UUID, user_id: UUID) -> Dict:
        """
        Get PR CI/CD check status from GitHub.

        Args:
            pr_id: PR UUID
            user_id: User requesting checks

        Returns:
            Dict with check run data

        Raises:
            GitHubPRNotFoundError: If PR not found
            InsufficientGitHubPermissionsError: If user lacks access
        """
        pr = await self.pr_repo.get_by_id(pr_id)
        if not pr:
            raise GitHubPRNotFoundError(f"Pull request {pr_id} not found")

        # Verify user has project access
        if not await self.project_service.check_permission(
            project_id=pr.project_id,
            user_id=user_id,
            required_role="viewer",
        ):
            raise InsufficientGitHubPermissionsError("Must be project member to view PR checks")

        integration = await self.integration_repo.get_by_id(pr.github_integration_id)
        if not integration:
            raise GitHubIntegrationNotFoundError(
                f"GitHub integration {pr.github_integration_id} not found"
            )

        # Create GitHub API client
        token = TokenEncryption.decrypt_token(integration.access_token_encrypted)
        client = GitHubAPIClient(token)

        try:
            # Fetch check runs from GitHub
            checks_data = await client.get_pr_checks(
                integration.repository_owner,
                integration.repository_name,
                pr.pr_number,
            )

            # Update PR checks status
            all_passed = all(
                check.get("conclusion") == "success"
                for check in checks_data.get("checks", [])
                if check.get("status") == "completed"
            )
            checks_status = "success" if all_passed else "pending"

            await self.pr_repo.update_checks_status(
                pr.id,
                checks_status=checks_status,
                checks_count=checks_data.get("total_count", 0),
                required_checks_passed=all_passed,
            )

            logger.info(f"Fetched {checks_data['total_count']} checks for PR #{pr.pr_number}")

            return checks_data

        finally:
            await client.close()

    async def list_pull_requests(
        self,
        project_id: UUID,
        user_id: UUID,
        state: Optional[str] = None,
        skip: int = 0,
        limit: int = 50,
    ) -> List[PullRequest]:
        """
        List pull requests for a project.

        Args:
            project_id: Project UUID
            user_id: User requesting list
            state: Optional state filter (open, closed, merged, draft)
            skip: Pagination offset
            limit: Page size

        Returns:
            List of PullRequest objects

        Raises:
            InsufficientGitHubPermissionsError: If user lacks access
        """
        # Verify user has project access
        if not await self.project_service.check_permission(
            project_id=project_id,
            user_id=user_id,
            required_role="viewer",
        ):
            raise InsufficientGitHubPermissionsError("Must be project member to list pull requests")

        prs = await self.pr_repo.list_by_project(
            project_id=project_id,
            state=state,
            skip=skip,
            limit=limit,
        )

        logger.info(f"Listed {len(prs)} PRs for project {project_id}")
        return prs

    async def get_project_statistics(
        self,
        project_id: UUID,
        user_id: UUID,
    ) -> Dict:
        """
        Get GitHub statistics for a project.

        Calculates PR metrics and contributor stats.

        Args:
            project_id: Project UUID
            user_id: User requesting statistics

        Returns:
            Dict with statistics

        Raises:
            GitHubIntegrationNotFoundError: If integration not found
            InsufficientGitHubPermissionsError: If user lacks access
        """
        # Verify user has project access
        if not await self.project_service.check_permission(
            project_id=project_id,
            user_id=user_id,
            required_role="viewer",
        ):
            raise InsufficientGitHubPermissionsError("Must be project member to view statistics")

        integration = await self.integration_repo.get_by_project(project_id)
        if not integration:
            raise GitHubIntegrationNotFoundError(
                f"No GitHub integration found for project {project_id}"
            )

        # Get PR counts
        total = await self.pr_repo.count_by_project(project_id)
        open_count = await self.pr_repo.count_by_project(project_id, state="open")
        merged_count = await self.pr_repo.count_by_project(project_id, state="merged")
        closed_count = await self.pr_repo.count_by_project(project_id, state="closed")

        # Get all PRs for detailed analysis
        all_prs = await self.pr_repo.list_by_project(project_id, limit=1000)

        # Calculate average merge time
        merge_times = []
        for pr in all_prs:
            if pr.merged and pr.merged_at and pr.created_at:
                time_diff = pr.merged_at - pr.created_at
                merge_times.append(time_diff.total_seconds() / 3600)  # Hours

        avg_merge_time = sum(merge_times) / len(merge_times) if merge_times else None

        # Count unique contributors
        contributors = set()
        contributor_pr_counts = {}
        for pr in all_prs:
            if pr.author_github_username:
                contributors.add(pr.author_github_username)
                contributor_pr_counts[pr.author_github_username] = (
                    contributor_pr_counts.get(pr.author_github_username, 0) + 1
                )

        # Get most active contributors (top 5)
        most_active = sorted(
            contributor_pr_counts.items(),
            key=lambda x: x[1],
            reverse=True,
        )[:5]

        statistics = {
            "total_prs": total,
            "open_prs": open_count,
            "merged_prs": merged_count,
            "closed_prs": closed_count,
            "average_merge_time_hours": avg_merge_time,
            "total_commits": integration.total_prs,  # Approximation
            "contributor_count": len(contributors),
            "most_active_contributors": [
                {"username": username, "pr_count": count} for username, count in most_active
            ],
        }

        logger.info(f"Calculated statistics for project {project_id}")
        return statistics

    # ============= Helper Methods =============

    async def _create_pr_from_github(
        self,
        integration: GitHubIntegration,
        pr_data: Dict,
        author_user_id: Optional[UUID] = None,
    ) -> PullRequest:
        """
        Create PullRequest from GitHub API data.

        Args:
            integration: GitHubIntegration instance
            pr_data: PR data from GitHub API
            author_user_id: Optional Ardha user ID

        Returns:
            Created PullRequest
        """
        pr = PullRequest(
            github_integration_id=integration.id,
            project_id=integration.project_id,
            pr_number=pr_data["number"],
            github_pr_id=pr_data["id"],
            title=pr_data["title"],
            description=pr_data.get("body", ""),
            state=pr_data["state"],
            head_branch=pr_data["head_branch"],
            base_branch=pr_data["base_branch"],
            head_sha=pr_data["head_sha"],
            author_github_username=pr_data.get("author", "unknown"),
            author_user_id=author_user_id,
            is_draft=pr_data.get("draft", False),
            mergeable=pr_data.get("mergeable"),
            merged=pr_data.get("merged", False),
            html_url=pr_data["html_url"],
            api_url=pr_data["api_url"],
        )

        # Parse timestamps
        if pr_data.get("merged_at"):
            pr.merged_at = datetime.fromisoformat(pr_data["merged_at"].replace("Z", "+00:00"))
        if pr_data.get("closed_at"):
            pr.closed_at = datetime.fromisoformat(pr_data["closed_at"].replace("Z", "+00:00"))

        # Set change statistics if available
        if "additions" in pr_data:
            pr.additions = pr_data["additions"]
        if "deletions" in pr_data:
            pr.deletions = pr_data["deletions"]
        if "changed_files" in pr_data:
            pr.changed_files = pr_data["changed_files"]
        if "commits" in pr_data:
            pr.commits_count = pr_data["commits"]

        pr = await self.pr_repo.create(pr)
        await self.db.flush()
        await self.db.refresh(pr)

        return pr

    async def _link_pr_to_tasks(self, pr: PullRequest) -> None:
        """
        Parse PR description and link mentioned tasks.

        Args:
            pr: PullRequest instance
        """
        if not pr.description:
            return

        # Use GitService to parse task IDs from description
        from ardha.services.git_service import GitService

        # Create a temporary GitService instance for parsing
        git_service = GitService(Path("/tmp"))  # Path doesn't matter for parsing
        task_info = git_service.parse_commit_message(pr.description)

        # Extract mentioned and closes IDs
        mentioned_ids = task_info.get("mentioned", [])
        closes_ids = (
            task_info.get("closes", []) + task_info.get("fixes", []) + task_info.get("resolves", [])
        )

        # Get task UUIDs from identifiers
        mentioned_uuids = []
        closes_uuids = []

        from ardha.repositories.task_repository import TaskRepository

        task_repo = TaskRepository(self.db)

        for task_id in mentioned_ids:
            task = await task_repo.get_by_identifier(pr.project_id, task_id)
            if task:
                mentioned_uuids.append(task.id)

        for task_id in closes_ids:
            task = await task_repo.get_by_identifier(pr.project_id, task_id)
            if task:
                closes_uuids.append(task.id)

        # Link tasks
        if mentioned_uuids:
            await self.pr_repo.link_to_tasks(
                pr.id,
                mentioned_uuids,
                link_type="mentioned",
                linked_from="pr_description",
            )

        if closes_uuids:
            await self.pr_repo.link_to_tasks(
                pr.id,
                closes_uuids,
                link_type="closes",
                linked_from="pr_description",
            )

            # Update PR's closes_task_ids
            await self.pr_repo.update(
                pr.id,
                {"closes_task_ids": [str(uid) for uid in closes_uuids]},
            )

        logger.info(
            f"Linked PR #{pr.pr_number} to {len(mentioned_uuids)} mentioned "
            f"and {len(closes_uuids)} closing tasks"
        )

    async def _link_pr_to_commits(
        self,
        pr: PullRequest,
        integration: GitHubIntegration,
        client: GitHubAPIClient,
    ) -> None:
        """
        Link PR to its commits in database.

        Args:
            pr: PullRequest instance
            integration: GitHubIntegration instance
            client: GitHubAPIClient instance
        """
        try:
            # Get commits from GitHub
            commits_data = await client.get_pr_commits(
                integration.repository_owner,
                integration.repository_name,
                pr.pr_number,
            )

            # Find matching commits in database
            from ardha.repositories.git_commit import GitCommitRepository

            commit_repo = GitCommitRepository(self.db)
            commit_ids = []

            for commit_data in commits_data:
                commit = await commit_repo.get_by_sha(
                    pr.project_id,
                    commit_data["sha"],
                )
                if commit:
                    commit_ids.append(commit.id)

            # Link commits to PR
            if commit_ids:
                await self.pr_repo.link_to_commits(pr.id, commit_ids)
                logger.info(f"Linked {len(commit_ids)} commits to PR #{pr.pr_number}")

        except Exception as e:
            logger.warning(f"Failed to link commits to PR #{pr.pr_number}: {e}")
