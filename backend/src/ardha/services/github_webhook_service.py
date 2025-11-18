"""
GitHub Webhook Service for event processing.

This module processes GitHub webhook events to automate task status updates,
PR synchronization, and commit tracking. Handles signature verification,
event routing, and idempotent processing.
"""

import hashlib
import hmac
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, List, Optional
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from ardha.models.github_webhook import GitHubWebhookDelivery
from ardha.repositories.github_integration import GitHubIntegrationRepository
from ardha.repositories.pull_request import PullRequestRepository
from ardha.services.git_commit_service import GitCommitService
from ardha.services.task_service import TaskService

logger = logging.getLogger(__name__)


# ============= Custom Exceptions =============


class WebhookVerificationError(Exception):
    """Raised when webhook signature verification fails."""

    pass


class WebhookProcessingError(Exception):
    """Raised when webhook processing fails."""

    pass


# ============= Service Class =============


class GitHubWebhookService:
    """
    Service for processing GitHub webhook events.

    Handles webhook signature verification, event routing, and automated
    task/PR updates based on GitHub events.
    """

    def __init__(
        self,
        integration_repo: GitHubIntegrationRepository,
        pr_repo: PullRequestRepository,
        task_service: TaskService,
        commit_service: GitCommitService,
        db: AsyncSession,
    ):
        """
        Initialize GitHubWebhookService.

        Args:
            integration_repo: Repository for GitHub integrations
            pr_repo: Repository for pull requests
            task_service: Service for task operations
            commit_service: Service for commit operations
            db: Async SQLAlchemy database session
        """
        self.integration_repo = integration_repo
        self.pr_repo = pr_repo
        self.task_service = task_service
        self.commit_service = commit_service
        self.db = db

    # ============= Main Webhook Processing =============

    async def process_webhook(
        self,
        integration_id: UUID,
        delivery_id: str,
        event_type: str,
        action: Optional[str],
        payload: dict,
        signature: str,
    ) -> dict:
        """
        Process GitHub webhook event.

        Verifies signature, routes to appropriate handler, and records delivery.

        Args:
            integration_id: GitHub integration UUID
            delivery_id: GitHub delivery UUID
            event_type: GitHub event type (pull_request, push, etc.)
            action: Optional event action (opened, closed, etc.)
            payload: Webhook payload
            signature: X-Hub-Signature-256 header value

        Returns:
            Dict with processing result

        Raises:
            WebhookVerificationError: If signature is invalid
            WebhookProcessingError: If processing fails
        """
        # Verify signature
        if not await self.verify_webhook_signature(integration_id, payload, signature):
            logger.warning(f"Invalid webhook signature for delivery {delivery_id}")
            raise WebhookVerificationError("Invalid webhook signature")

        # Record webhook delivery
        delivery = GitHubWebhookDelivery(
            github_integration_id=integration_id,
            delivery_id=delivery_id,
            event_type=event_type,
            action=action,
            payload=payload,
            status="received",
        )

        try:
            delivery = await self.integration_repo.record_webhook_delivery(
                integration_id,
                delivery,
            )
        except Exception as e:
            logger.error(f"Failed to record webhook delivery: {e}")
            raise WebhookProcessingError(f"Failed to record delivery: {e}")

        # Route to appropriate handler
        try:
            if event_type == "pull_request":
                await self.handle_pull_request_event(payload)
            elif event_type == "push":
                await self.handle_push_event(payload)
            elif event_type == "pull_request_review":
                await self.handle_pull_request_review_event(payload)
            elif event_type == "check_suite":
                await self.handle_check_suite_event(payload)
            elif event_type == "check_run":
                await self.handle_check_run_event(payload)
            elif event_type == "status":
                await self.handle_status_event(payload)
            else:
                logger.info(f"Unhandled event type: {event_type}")

            # Mark delivery as processed
            delivery.status = "processed"
            delivery.processed_at = datetime.now(timezone.utc)

            logger.info(f"Successfully processed {event_type} webhook (delivery {delivery_id})")

            return {
                "status": "processed",
                "delivery_id": delivery_id,
                "event_type": event_type,
            }

        except Exception as e:
            # Mark delivery as failed
            delivery.status = "failed"
            delivery.error_message = str(e)
            logger.error(f"Failed to process webhook {delivery_id}: {e}", exc_info=True)

            raise WebhookProcessingError(f"Failed to process webhook: {e}")

    # ============= Event Handlers =============

    async def handle_pull_request_event(self, payload: dict) -> None:
        """
        Handle pull_request webhook event.

        Processes PR actions: opened, closed, reopened, edited, synchronize.
        Automatically creates/updates PR in database and links to tasks.

        Args:
            payload: Webhook payload dictionary
        """
        action = payload.get("action")
        pr_data = payload.get("pull_request", {})
        repo_data = payload.get("repository", {})

        # Extract PR information
        pr_number = pr_data.get("number")
        repo_owner = repo_data.get("owner", {}).get("login")
        repo_name = repo_data.get("name")

        logger.info(
            f"Processing PR event: {action} for PR #{pr_number} in {repo_owner}/{repo_name}"
        )

        # Find integration by repository
        integration = await self.integration_repo.get_by_repository(repo_owner, repo_name)
        if not integration:
            logger.warning(f"No integration found for repository {repo_owner}/{repo_name}")
            return

        # Get or create PR in database
        pr = await self.pr_repo.get_by_number(integration.id, pr_number)

        if action in ("opened", "reopened", "edited", "synchronize"):
            if not pr:
                # Create new PR
                pr = await self._create_pr_from_payload(integration, pr_data)
            else:
                # Update existing PR
                await self._update_pr_from_payload(pr.id, pr_data)

            # Link to tasks (parse description)
            await self._link_pr_to_tasks_from_payload(
                pr.id if pr else None, pr_data, integration.project_id
            )

        elif action == "closed":
            if pr:
                # Update PR state
                merged = pr_data.get("merged", False)
                await self.pr_repo.update_state(
                    pr.id,
                    "merged" if merged else "closed",
                    merged_at=datetime.now(timezone.utc) if merged else None,
                    closed_at=datetime.now(timezone.utc),
                )

                # Close linked tasks if merged
                if merged:
                    await self.update_tasks_from_pr_merge(pr.id)

                # Update statistics
                if merged:
                    await self.integration_repo.update_statistics(
                        integration.id,
                        merged_prs=1,
                    )
                else:
                    await self.integration_repo.update_statistics(
                        integration.id,
                        closed_prs=1,
                    )

        logger.info(f"Completed PR event processing for PR #{pr_number}")

    async def handle_push_event(self, payload: dict) -> None:
        """
        Handle push webhook event.

        Syncs commits to database and links to tasks from commit messages.

        Args:
            payload: Webhook payload dictionary
        """
        repo_data = payload.get("repository", {})
        commits = payload.get("commits", [])
        ref = payload.get("ref", "")

        repo_owner = repo_data.get("owner", {}).get("login")
        repo_name = repo_data.get("name")
        branch = ref.replace("refs/heads/", "")

        logger.info(
            f"Processing push event: {len(commits)} commits to {branch} in {repo_owner}/{repo_name}"
        )

        # Find integration
        integration = await self.integration_repo.get_by_repository(repo_owner, repo_name)
        if not integration:
            logger.warning(f"No integration found for repository {repo_owner}/{repo_name}")
            return

        # Process each commit
        for commit_data in commits:
            sha = commit_data.get("id")
            message = commit_data.get("message", "")

            # Check if commit exists in database
            from ardha.repositories.git_commit import (
                GitCommitRepository,
            )

            commit_repo = GitCommitRepository(self.db)
            existing_commit = await commit_repo.get_by_sha(
                integration.project_id, sha
            )

            if not existing_commit and sha and message:
                # Create commit record (simplified - full implementation would sync via commit_service)
                logger.info(f"Found new commit {sha[:7]} - would sync to database")
                # TODO: Implement full commit sync

            # Parse commit message for task IDs and update task status
            if message and integration.auto_link_tasks:
                await self._update_tasks_from_commit(
                    message,
                    integration.project_id,
                    sha,
                    is_default_branch=(branch == integration.default_branch),
                )

        logger.info(f"Completed push event processing for {len(commits)} commits")

    async def handle_pull_request_review_event(self, payload: dict) -> None:
        """
        Handle pull_request_review webhook event.

        Updates PR review status and approval count.

        Args:
            payload: Webhook payload dictionary
        """
        review_data = payload.get("review", {})
        pr_data = payload.get("pull_request", {})
        repo_data = payload.get("repository", {})

        pr_number = pr_data.get("number")
        review_state = review_data.get("state")
        repo_owner = repo_data.get("owner", {}).get("login")
        repo_name = repo_data.get("name")

        logger.info(
            f"Processing PR review event: {review_state} for PR #{pr_number} "
            f"in {repo_owner}/{repo_name}"
        )

        # Find integration
        integration = await self.integration_repo.get_by_repository(repo_owner, repo_name)
        if not integration:
            return

        # Find PR
        pr = await self.pr_repo.get_by_number(integration.id, pr_number)
        if not pr:
            logger.warning(f"PR #{pr_number} not found in database")
            return

        # Update review status (simplified)
        reviews_count = pr.reviews_count + 1
        approvals_count = pr.approvals_count + (1 if review_state == "approved" else 0)

        # Determine overall review status
        if review_state == "approved" and approvals_count > 0:
            review_status = "approved"
        elif review_state == "changes_requested":
            review_status = "changes_requested"
        else:
            review_status = pr.review_status

        await self.pr_repo.update_review_status(
            pr.id,
            review_status=review_status,
            reviews_count=reviews_count,
            approvals_count=approvals_count,
        )

        logger.info(f"Updated review status for PR #{pr_number}")

    async def handle_check_suite_event(self, payload: dict) -> None:
        """
        Handle check_suite webhook event.

        Updates PR check status when CI/CD suite completes.

        Args:
            payload: Webhook payload dictionary
        """
        check_suite = payload.get("check_suite", {})
        action = payload.get("action")
        repo_data = payload.get("repository", {})

        conclusion = check_suite.get("conclusion")
        head_sha = check_suite.get("head_sha")
        repo_owner = repo_data.get("owner", {}).get("login")
        repo_name = repo_data.get("name")

        logger.info(
            f"Processing check suite event: {action} with conclusion {conclusion} "
            f"for {head_sha[:7]} in {repo_owner}/{repo_name}"
        )

        # Find integration
        integration = await self.integration_repo.get_by_repository(repo_owner, repo_name)
        if not integration:
            return

        # Find PR(s) with this head SHA
        prs = await self.pr_repo.list_by_integration(integration.id)
        for pr in prs:
            if pr.head_sha == head_sha:
                # Update checks status based on conclusion
                if conclusion == "success":
                    checks_status = "success"
                    required_checks_passed = True
                elif conclusion == "failure":
                    checks_status = "failure"
                    required_checks_passed = False
                elif conclusion == "cancelled":
                    checks_status = "cancelled"
                    required_checks_passed = False
                else:
                    checks_status = "pending"
                    required_checks_passed = False

                await self.pr_repo.update_checks_status(
                    pr.id,
                    checks_status=checks_status,
                    checks_count=pr.checks_count,
                    required_checks_passed=required_checks_passed,
                )

                logger.info(f"Updated checks status for PR #{pr.pr_number} to {checks_status}")

    async def handle_check_run_event(self, payload: dict) -> None:
        """
        Handle check_run webhook event.

        Updates PR check status when individual check completes.

        Args:
            payload: Webhook payload dictionary
        """
        check_run = payload.get("check_run", {})
        action = payload.get("action")
        repo_data = payload.get("repository", {})

        status = check_run.get("status")
        conclusion = check_run.get("conclusion")
        head_sha = check_run.get("head_sha")
        check_name = check_run.get("name")
        repo_owner = repo_data.get("owner", {}).get("login")
        repo_name = repo_data.get("name")

        logger.info(
            f"Processing check run event: {action} for '{check_name}' "
            f"with conclusion {conclusion} in {repo_owner}/{repo_name}"
        )

        # Find integration
        integration = await self.integration_repo.get_by_repository(repo_owner, repo_name)
        if not integration:
            return

        # Find PR with this head SHA
        prs = await self.pr_repo.list_by_integration(integration.id)
        for pr in prs:
            if pr.head_sha == head_sha:
                # Update checks count if completed
                if status == "completed":
                    checks_count = pr.checks_count + 1
                    await self.pr_repo.update_checks_status(
                        pr.id,
                        checks_status=pr.checks_status,
                        checks_count=checks_count,
                        required_checks_passed=pr.required_checks_passed,
                    )

                logger.info(f"Updated check run for PR #{pr.pr_number}")

    async def handle_status_event(self, payload: dict) -> None:
        """
        Handle status webhook event (commit status updates).

        Updates PR status information.

        Args:
            payload: Webhook payload dictionary
        """
        sha = payload.get("sha")
        state = payload.get("state")
        context = payload.get("context")
        repo_data = payload.get("repository", {})

        repo_owner = repo_data.get("owner", {}).get("login")
        repo_name = repo_data.get("name")

        logger.info(
            f"Processing status event: {state} for {context} "
            f"on commit {sha[:7] if sha else 'unknown'} in {repo_owner}/{repo_name}"
        )

        # Find integration
        integration = await self.integration_repo.get_by_repository(repo_owner, repo_name)
        if not integration:
            return

        # Find PR(s) with this SHA
        prs = await self.pr_repo.list_by_integration(integration.id)
        for pr in prs:
            if pr.head_sha == sha:
                # Update status based on state (simplified)
                logger.info(f"Status update for PR #{pr.pr_number}: {state} ({context})")
                # In a full implementation, we'd track individual status contexts

    # ============= Signature Verification =============

    async def verify_webhook_signature(
        self,
        integration_id: UUID,
        payload: dict,
        signature_header: str,
    ) -> bool:
        """
        Verify webhook signature using HMAC-SHA256.

        Args:
            integration_id: GitHub integration UUID
            payload: Webhook payload dictionary
            signature_header: X-Hub-Signature-256 header value

        Returns:
            True if signature is valid, False otherwise
        """
        integration = await self.integration_repo.get_by_id(integration_id)
        if not integration or not integration.webhook_secret:
            logger.warning(
                f"Cannot verify signature: integration {integration_id} "
                f"not found or missing webhook_secret"
            )
            return False

        # GitHub sends signature as 'sha256=<hash>'
        if not signature_header.startswith("sha256="):
            return False

        expected_signature = signature_header[7:]  # Remove 'sha256=' prefix

        # Convert payload to string (as received)
        import json

        payload_str = json.dumps(payload, separators=(",", ":"))

        # Compute HMAC-SHA256
        mac = hmac.new(
            integration.webhook_secret.encode("utf-8"),
            msg=payload_str.encode("utf-8"),
            digestmod=hashlib.sha256,
        )
        computed_signature = mac.hexdigest()

        # Constant-time comparison
        is_valid = hmac.compare_digest(computed_signature, expected_signature)
        logger.debug(f"Webhook signature verification for {integration_id}: {is_valid}")
        return is_valid

    # ============= Task ID Extraction =============

    async def extract_task_ids_from_pr(self, pr_data: dict) -> tuple[List[str], List[str]]:
        """
        Extract task IDs from PR title and body.

        Args:
            pr_data: PR data from webhook payload

        Returns:
            Tuple of (mentioned_ids, closes_ids)
        """
        title = pr_data.get("title", "")
        body = pr_data.get("body", "")

        # Combine title and body
        combined_text = f"{title}\n{body}"

        # Use GitService to parse task IDs
        from tempfile import gettempdir

        from ardha.services.git_service import GitService

        temp_path = Path(gettempdir())  # Use system temp dir
        git_service = GitService(temp_path)  # noqa: S108
        task_info = git_service.parse_commit_message(combined_text)

        mentioned_ids = task_info.get("mentioned", [])
        closes_ids = (
            task_info.get("closes", []) + task_info.get("fixes", []) + task_info.get("resolves", [])
        )

        return mentioned_ids, closes_ids

    # ============= Task Automation =============

    async def update_tasks_from_pr_merge(self, pr_id: UUID) -> int:
        """
        Automatically close tasks when PR merges.

        Updates tasks with "closes" link type to "done" status.

        Args:
            pr_id: PR UUID

        Returns:
            Count of updated tasks
        """
        pr = await self.pr_repo.get_by_id(pr_id)
        if not pr or not pr.closes_task_ids:
            return 0

        updated_count = 0

        for task_id_str in pr.closes_task_ids:
            try:
                task_id = UUID(task_id_str)

                # Get the task
                from ardha.repositories.task_repository import TaskRepository

                task_repo = TaskRepository(self.db)
                task = await task_repo.get_by_id(task_id)

                if task and task.status != "done":
                    # Update task status (bypass user requirement for automated update)
                    await task_repo.update_status(task_id, "done")

                    # Log activity
                    await task_repo.log_activity(
                        task_id=task_id,
                        user_id=None,  # System action
                        action="pr_merged",
                        comment=f"Automatically closed by PR #{pr.pr_number}",
                    )

                    updated_count += 1
                    logger.info(f"Auto-closed task {task.identifier} from PR #{pr.pr_number} merge")

            except Exception as e:
                logger.warning(f"Failed to auto-close task {task_id_str}: {e}")

        return updated_count

    # ============= Helper Methods =============

    async def _create_pr_from_payload(
        self,
        integration: Any,  # GitHubIntegration
        pr_data: dict,
    ) -> Any:  # PullRequest
        """
        Create PullRequest from webhook payload.

        Args:
            integration: GitHubIntegration instance
            pr_data: PR data from webhook

        Returns:
            Created PullRequest
        """
        from ardha.models.github_integration import PullRequest

        pr = PullRequest(
            github_integration_id=integration.id,
            project_id=integration.project_id,
            pr_number=pr_data["number"],
            github_pr_id=pr_data["id"],
            title=pr_data["title"],
            description=pr_data.get("body", ""),
            state=pr_data["state"],
            head_branch=pr_data["head"]["ref"],
            base_branch=pr_data["base"]["ref"],
            head_sha=pr_data["head"]["sha"],
            author_github_username=pr_data.get("user", {}).get("login", "unknown"),
            is_draft=pr_data.get("draft", False),
            mergeable=pr_data.get("mergeable"),
            merged=pr_data.get("merged", False),
            html_url=pr_data["html_url"],
            api_url=pr_data["url"],
        )

        # Parse timestamps
        if pr_data.get("created_at"):
            pr.created_at = datetime.fromisoformat(pr_data["created_at"].replace("Z", "+00:00"))
        if pr_data.get("updated_at"):
            pr.updated_at = datetime.fromisoformat(pr_data["updated_at"].replace("Z", "+00:00"))

        pr = await self.pr_repo.create(pr)
        await self.db.flush()

        logger.info(f"Created PR #{pr.pr_number} from webhook payload")
        return pr

    async def _update_pr_from_payload(self, pr_id: UUID, pr_data: dict) -> None:
        """
        Update PR from webhook payload.

        Args:
            pr_id: PR UUID
            pr_data: PR data from webhook
        """
        update_data = {
            "title": pr_data.get("title"),
            "description": pr_data.get("body", ""),
            "state": pr_data.get("state"),
            "head_sha": pr_data["head"]["sha"],
            "is_draft": pr_data.get("draft", False),
            "mergeable": pr_data.get("mergeable"),
            "merged": pr_data.get("merged", False),
        }

        # Parse timestamps
        if pr_data.get("updated_at"):
            update_data["updated_at"] = datetime.fromisoformat(
                pr_data["updated_at"].replace("Z", "+00:00")
            )

        await self.pr_repo.update(pr_id, update_data)
        logger.info("Updated PR from webhook payload")

    async def _link_pr_to_tasks_from_payload(
        self,
        pr_id: Optional[UUID],
        pr_data: dict,
        project_id: UUID,
    ) -> None:
        """
        Parse PR data and link to tasks.

        Args:
            pr_id: PR UUID (may be None if PR not yet created)
            pr_data: PR data from webhook
            project_id: Project UUID
        """
        if not pr_id:
            return

        # Extract task IDs
        mentioned_ids, closes_ids = await self.extract_task_ids_from_pr(pr_data)

        if not mentioned_ids and not closes_ids:
            return

        # Get task UUIDs from identifiers
        from ardha.repositories.task_repository import TaskRepository

        task_repo = TaskRepository(self.db)

        mentioned_uuids = []
        closes_uuids = []

        for task_id in mentioned_ids:
            task = await task_repo.get_by_identifier(project_id, task_id)
            if task:
                mentioned_uuids.append(task.id)

        for task_id in closes_ids:
            task = await task_repo.get_by_identifier(project_id, task_id)
            if task:
                closes_uuids.append(task.id)

        # Link tasks
        if mentioned_uuids:
            await self.pr_repo.link_to_tasks(
                pr_id,
                mentioned_uuids,
                link_type="mentioned",
                linked_from="pr_description",
            )

        if closes_uuids:
            await self.pr_repo.link_to_tasks(
                pr_id,
                closes_uuids,
                link_type="closes",
                linked_from="pr_description",
            )

            # Update PR's closes_task_ids
            await self.pr_repo.update(
                pr_id,
                {"closes_task_ids": [str(uid) for uid in closes_uuids]},
            )

        logger.info(
            f"Linked PR to {len(mentioned_uuids)} mentioned and {len(closes_uuids)} closing tasks"
        )

    async def _update_tasks_from_commit(
        self,
        commit_message: str,
        project_id: UUID,
        commit_sha: str,
        is_default_branch: bool = False,
    ) -> None:
        """
        Update task status from commit message.

        Args:
            commit_message: Commit message text
            project_id: Project UUID
            commit_sha: Commit SHA
            is_default_branch: Whether commit is to default branch
        """
        # Parse commit message
        from tempfile import gettempdir

        from ardha.services.git_service import GitService

        temp_path = Path(gettempdir())  # Use system temp dir
        git_service = GitService(temp_path)  # noqa: S108
        task_info = git_service.parse_commit_message(commit_message)

        # Get closing task IDs
        closes_ids = (
            task_info.get("closes", []) + task_info.get("fixes", []) + task_info.get("resolves", [])
        )

        if not closes_ids:
            return

        # Get task repository
        from ardha.repositories.task_repository import TaskRepository

        task_repo = TaskRepository(self.db)

        # Update tasks if on default branch
        if is_default_branch:
            for task_id in closes_ids:
                task = await task_repo.get_by_identifier(project_id, task_id)
                if task and task.status != "done":
                    # Update status
                    await task_repo.update_status(task.id, "done")

                    # Log activity
                    await task_repo.log_activity(
                        task_id=task.id,
                        user_id=None,  # System action
                        action="commit_closed",
                        comment=f"Automatically closed by commit {commit_sha[:7]}",
                    )

                    logger.info(f"Auto-closed task {task.identifier} from commit {commit_sha[:7]}")
