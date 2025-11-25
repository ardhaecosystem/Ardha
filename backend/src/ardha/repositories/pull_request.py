"""
Pull Request repository for data access abstraction.

This module provides the repository pattern implementation for PullRequest model,
handling all database operations related to GitHub pull requests, including task
linking, commit associations, and review/CI status tracking.
"""

import logging
from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ardha.models.git_commit import GitCommit
from ardha.models.github_integration import PullRequest, pr_commits, pr_tasks
from ardha.models.task import Task

logger = logging.getLogger(__name__)


class PullRequestRepository:
    """
    Repository for PullRequest model database operations.

    Provides data access methods for pull request operations including CRUD,
    state management, task and commit linking, review and CI/CD status tracking.
    Follows the repository pattern to abstract database implementation details
    from business logic.

    Attributes:
        session: SQLAlchemy async session for database operations
    """

    def __init__(self, session: AsyncSession) -> None:
        """
        Initialize the PullRequestRepository with a database session.

        Args:
            session: SQLAlchemy async session for database operations
        """
        self.session = session

    async def create(self, pr: PullRequest) -> PullRequest:
        """
        Create a new pull request.

        Handles unique constraint (integration_id, pr_number).

        Args:
            pr: PullRequest instance to create

        Returns:
            Created PullRequest with generated ID

        Raises:
            IntegrityError: If PR with same number already exists
            SQLAlchemyError: If database operation fails
        """
        try:
            self.session.add(pr)
            await self.session.flush()
            await self.session.refresh(pr)
            logger.info(
                f"Created pull request #{pr.pr_number} (ID: {pr.id}) "
                f"for project {pr.project_id}"
            )
            return pr
        except IntegrityError:
            logger.warning(
                f"PR #{pr.pr_number} already exists for integration " f"{pr.github_integration_id}"
            )
            raise
        except SQLAlchemyError as e:
            logger.error(f"Error creating pull request: {e}", exc_info=True)
            raise

    async def get_by_id(self, pr_id: UUID) -> PullRequest | None:
        """
        Fetch a pull request by its UUID.

        Eagerly loads relationships to prevent N+1 queries.

        Args:
            pr_id: UUID of the pull request

        Returns:
            PullRequest object if found, None otherwise

        Raises:
            SQLAlchemyError: If database query fails
        """
        try:
            stmt = (
                select(PullRequest)
                .where(PullRequest.id == pr_id)
                .options(
                    selectinload(PullRequest.github_integration),
                    selectinload(PullRequest.project),
                    selectinload(PullRequest.author_user),
                    selectinload(PullRequest.linked_tasks),
                    selectinload(PullRequest.commits),
                )
            )
            result = await self.session.execute(stmt)
            return result.scalar_one_or_none()
        except SQLAlchemyError as e:
            logger.error(f"Error fetching PR by id {pr_id}: {e}", exc_info=True)
            raise

    async def get_by_number(
        self, github_integration_id: UUID, pr_number: int
    ) -> PullRequest | None:
        """
        Fetch a pull request by integration and PR number.

        Args:
            github_integration_id: UUID of the GitHub integration
            pr_number: GitHub PR number

        Returns:
            PullRequest object if found, None otherwise

        Raises:
            SQLAlchemyError: If database query fails
        """
        try:
            stmt = select(PullRequest).where(
                PullRequest.github_integration_id == github_integration_id,
                PullRequest.pr_number == pr_number,
            )
            result = await self.session.execute(stmt)
            return result.scalar_one_or_none()
        except SQLAlchemyError as e:
            logger.error(
                f"Error fetching PR #{pr_number} for integration " f"{github_integration_id}: {e}",
                exc_info=True,
            )
            raise

    async def get_by_github_id(self, github_pr_id: int) -> PullRequest | None:
        """
        Fetch a pull request by GitHub's internal PR ID.

        Args:
            github_pr_id: GitHub's internal PR ID

        Returns:
            PullRequest object if found, None otherwise

        Raises:
            SQLAlchemyError: If database query fails
        """
        try:
            stmt = select(PullRequest).where(PullRequest.github_pr_id == github_pr_id)
            result = await self.session.execute(stmt)
            return result.scalar_one_or_none()
        except SQLAlchemyError as e:
            logger.error(f"Error fetching PR by GitHub ID {github_pr_id}: {e}", exc_info=True)
            raise

    async def list_by_project(
        self,
        project_id: UUID,
        state: str | None = None,
        author_user_id: UUID | None = None,
        skip: int = 0,
        limit: int = 50,
    ) -> list[PullRequest]:
        """
        Fetch pull requests for a specific project.

        Args:
            project_id: UUID of the project
            state: Optional state filter (open, closed, merged, draft)
            author_user_id: Optional author filter
            skip: Number of records to skip (pagination)
            limit: Maximum records to return (max 100)

        Returns:
            List of PullRequest objects ordered by created_at DESC

        Raises:
            SQLAlchemyError: If database query fails
        """
        try:
            stmt = select(PullRequest).where(PullRequest.project_id == project_id)

            # Apply optional filters
            if state:
                stmt = stmt.where(PullRequest.state == state)
            if author_user_id:
                stmt = stmt.where(PullRequest.author_user_id == author_user_id)

            # Apply pagination and ordering
            stmt = stmt.order_by(PullRequest.created_at.desc()).offset(skip).limit(min(limit, 100))

            result = await self.session.execute(stmt)
            prs = list(result.scalars().all())
            logger.info(f"Found {len(prs)} PRs for project {project_id}")
            return prs
        except SQLAlchemyError as e:
            logger.error(f"Error listing PRs for project {project_id}: {e}", exc_info=True)
            raise

    async def list_by_integration(
        self,
        github_integration_id: UUID,
        state: str | None = None,
        skip: int = 0,
        limit: int = 50,
    ) -> list[PullRequest]:
        """
        Fetch pull requests for a GitHub integration.

        Args:
            github_integration_id: UUID of the GitHub integration
            state: Optional state filter
            skip: Number of records to skip (pagination)
            limit: Maximum records to return (max 100)

        Returns:
            List of PullRequest objects ordered by created_at DESC

        Raises:
            SQLAlchemyError: If database query fails
        """
        try:
            stmt = select(PullRequest).where(
                PullRequest.github_integration_id == github_integration_id
            )

            # Apply optional state filter
            if state:
                stmt = stmt.where(PullRequest.state == state)

            # Apply pagination and ordering
            stmt = stmt.order_by(PullRequest.created_at.desc()).offset(skip).limit(min(limit, 100))

            result = await self.session.execute(stmt)
            prs = list(result.scalars().all())
            logger.info(f"Found {len(prs)} PRs for GitHub integration {github_integration_id}")
            return prs
        except SQLAlchemyError as e:
            logger.error(
                f"Error listing PRs for integration {github_integration_id}: {e}",
                exc_info=True,
            )
            raise

    async def list_open_prs(self, project_id: UUID) -> list[PullRequest]:
        """
        Get all open pull requests for a project.

        Filters by state='open'.

        Args:
            project_id: UUID of the project

        Returns:
            List of open PullRequest objects

        Raises:
            SQLAlchemyError: If database query fails
        """
        try:
            stmt = (
                select(PullRequest)
                .where(
                    PullRequest.project_id == project_id,
                    PullRequest.state == "open",
                )
                .order_by(PullRequest.created_at.desc())
            )
            result = await self.session.execute(stmt)
            prs = list(result.scalars().all())
            logger.info(f"Found {len(prs)} open PRs for project {project_id}")
            return prs
        except SQLAlchemyError as e:
            logger.error(f"Error listing open PRs for project {project_id}: {e}", exc_info=True)
            raise

    async def update(self, pr_id: UUID, update_data: dict[str, Any]) -> PullRequest | None:
        """
        Update pull request fields.

        Updates specified fields and automatically sets updated_at timestamp.

        Args:
            pr_id: UUID of PR to update
            update_data: Dictionary of fields to update

        Returns:
            Updated PullRequest if found, None otherwise

        Raises:
            IntegrityError: If update violates constraints
            SQLAlchemyError: If database operation fails
        """
        try:
            pr = await self.get_by_id(pr_id)
            if not pr:
                logger.warning(f"Cannot update: PR {pr_id} not found")
                return None

            # Update only provided fields
            for key, value in update_data.items():
                if hasattr(pr, key):
                    setattr(pr, key, value)
                else:
                    logger.warning(f"Skipping unknown field: {key}")

            await self.session.flush()
            await self.session.refresh(pr)
            logger.info(f"Updated PR {pr_id}")
            return pr
        except IntegrityError as e:
            logger.warning(f"Integrity error updating PR {pr_id}: {e}")
            raise
        except SQLAlchemyError as e:
            logger.error(f"Error updating PR {pr_id}: {e}", exc_info=True)
            raise

    async def update_from_github(
        self, pr_id: UUID, github_data: dict[str, Any]
    ) -> PullRequest | None:
        """
        Update PR from GitHub API response.

        Parses GitHub API response and updates all relevant fields,
        then sets synced_at to current time.

        Args:
            pr_id: UUID of PR to update
            github_data: Dictionary from GitHub API pull request endpoint

        Returns:
            Updated PullRequest if found, None otherwise

        Raises:
            SQLAlchemyError: If database operation fails
        """
        try:
            pr = await self.get_by_id(pr_id)
            if not pr:
                logger.warning(f"Cannot update from GitHub: PR {pr_id} not found")
                return None

            # Use model's update method
            pr.update_from_github(github_data)

            await self.session.flush()
            await self.session.refresh(pr)
            logger.info(f"Updated PR {pr_id} from GitHub API")
            return pr
        except SQLAlchemyError as e:
            logger.error(f"Error updating PR {pr_id} from GitHub: {e}", exc_info=True)
            raise

    async def update_state(
        self,
        pr_id: UUID,
        new_state: str,
        merged_at: datetime | None = None,
        closed_at: datetime | None = None,
    ) -> PullRequest | None:
        """
        Update PR state with optional timestamps.

        Args:
            pr_id: UUID of PR to update
            new_state: New state (open, closed, merged, draft)
            merged_at: Optional merge timestamp
            closed_at: Optional close timestamp

        Returns:
            Updated PullRequest if found, None otherwise

        Raises:
            SQLAlchemyError: If database operation fails
        """
        try:
            pr = await self.get_by_id(pr_id)
            if not pr:
                logger.warning(f"Cannot update state: PR {pr_id} not found")
                return None

            pr.state = new_state

            if merged_at:
                pr.merged_at = merged_at
                pr.merged = True
            if closed_at:
                pr.closed_at = closed_at

            await self.session.flush()
            await self.session.refresh(pr)
            logger.info(f"Updated PR {pr_id} state to {new_state}")
            return pr
        except SQLAlchemyError as e:
            logger.error(f"Error updating PR state for {pr_id}: {e}", exc_info=True)
            raise

    async def update_checks_status(
        self,
        pr_id: UUID,
        checks_status: str,
        checks_count: int,
        required_checks_passed: bool,
    ) -> PullRequest | None:
        """
        Update CI/CD check status for a PR.

        Args:
            pr_id: UUID of PR to update
            checks_status: New checks status (pending, success, failure, error, cancelled)
            checks_count: Total checks count
            required_checks_passed: Whether required checks passed

        Returns:
            Updated PullRequest if found, None otherwise

        Raises:
            SQLAlchemyError: If database operation fails
        """
        try:
            pr = await self.get_by_id(pr_id)
            if not pr:
                logger.warning(f"Cannot update checks: PR {pr_id} not found")
                return None

            pr.checks_status = checks_status
            pr.checks_count = checks_count
            pr.required_checks_passed = required_checks_passed

            await self.session.flush()
            await self.session.refresh(pr)
            logger.info(f"Updated checks status for PR {pr_id} to {checks_status}")
            return pr
        except SQLAlchemyError as e:
            logger.error(f"Error updating checks status for {pr_id}: {e}", exc_info=True)
            raise

    async def update_review_status(
        self,
        pr_id: UUID,
        review_status: str,
        reviews_count: int,
        approvals_count: int,
    ) -> PullRequest | None:
        """
        Update review status for a PR.

        Args:
            pr_id: UUID of PR to update
            review_status: New review status (pending, approved, changes_requested, dismissed)
            reviews_count: Total reviews count
            approvals_count: Approvals count

        Returns:
            Updated PullRequest if found, None otherwise

        Raises:
            SQLAlchemyError: If database operation fails
        """
        try:
            pr = await self.get_by_id(pr_id)
            if not pr:
                logger.warning(f"Cannot update review: PR {pr_id} not found")
                return None

            pr.review_status = review_status
            pr.reviews_count = reviews_count
            pr.approvals_count = approvals_count

            await self.session.flush()
            await self.session.refresh(pr)
            logger.info(f"Updated review status for PR {pr_id} to {review_status}")
            return pr
        except SQLAlchemyError as e:
            logger.error(f"Error updating review status for {pr_id}: {e}", exc_info=True)
            raise

    async def link_to_tasks(
        self,
        pr_id: UUID,
        task_ids: list[UUID],
        link_type: str = "mentioned",
        linked_from: str = "pr_description",
    ) -> None:
        """
        Create PR-to-task associations.

        Uses bulk insert for efficiency, handles duplicates gracefully.

        Args:
            pr_id: UUID of the PR
            task_ids: List of task UUIDs to link
            link_type: Type of link (mentioned, implements, closes, related)
            linked_from: Source of link (commit_message, pr_description, pr_comment)

        Raises:
            SQLAlchemyError: If database operation fails
        """
        try:
            if not task_ids:
                return

            # Prepare values for bulk insert
            values = [
                {
                    "pr_id": pr_id,
                    "task_id": task_id,
                    "link_type": link_type,
                    "linked_from": linked_from,
                }
                for task_id in task_ids
            ]

            # Use insert().on_conflict_do_nothing() for graceful duplicate handling
            stmt = insert(pr_tasks).values(values)
            # Note: PostgreSQL-specific on_conflict_do_nothing
            stmt = stmt.on_conflict_do_nothing(index_elements=["pr_id", "task_id"])

            await self.session.execute(stmt)
            await self.session.flush()

            logger.info(
                f"Linked {len(task_ids)} tasks to PR {pr_id} " f"with link_type={link_type}"
            )
        except SQLAlchemyError as e:
            logger.error(f"Error linking tasks to PR {pr_id}: {e}", exc_info=True)
            raise

    async def link_to_commits(self, pr_id: UUID, commit_ids: list[UUID]) -> None:
        """
        Create PR-to-commit associations.

        Sets position based on order in list. Uses bulk insert.

        Args:
            pr_id: UUID of the PR
            commit_ids: List of commit UUIDs to link (in order)

        Raises:
            SQLAlchemyError: If database operation fails
        """
        try:
            if not commit_ids:
                return

            # Prepare values with position based on list order
            values = [
                {
                    "pr_id": pr_id,
                    "commit_id": commit_id,
                    "position": idx,
                }
                for idx, commit_id in enumerate(commit_ids)
            ]

            # Use insert().on_conflict_do_nothing() for graceful duplicate handling
            stmt = insert(pr_commits).values(values)
            stmt = stmt.on_conflict_do_nothing(index_elements=["pr_id", "commit_id"])

            await self.session.execute(stmt)
            await self.session.flush()

            logger.info(f"Linked {len(commit_ids)} commits to PR {pr_id}")
        except SQLAlchemyError as e:
            logger.error(f"Error linking commits to PR {pr_id}: {e}", exc_info=True)
            raise

    async def get_linked_tasks(self, pr_id: UUID) -> list[Task]:
        """
        Get tasks linked to a PR.

        Uses join to efficiently fetch task details.

        Args:
            pr_id: UUID of the PR

        Returns:
            List of Task objects linked to the PR

        Raises:
            SQLAlchemyError: If database query fails
        """
        try:
            stmt = (
                select(Task)
                .join(pr_tasks, Task.id == pr_tasks.c.task_id)
                .where(pr_tasks.c.pr_id == pr_id)
            )
            result = await self.session.execute(stmt)
            tasks = list(result.scalars().all())
            logger.info(f"Found {len(tasks)} linked tasks for PR {pr_id}")
            return tasks
        except SQLAlchemyError as e:
            logger.error(f"Error fetching linked tasks for PR {pr_id}: {e}", exc_info=True)
            raise

    async def get_linked_commits(self, pr_id: UUID) -> list[GitCommit]:
        """
        Get commits in a PR.

        Orders commits by position in the association table.

        Args:
            pr_id: UUID of the PR

        Returns:
            List of GitCommit objects ordered by position

        Raises:
            SQLAlchemyError: If database query fails
        """
        try:
            stmt = (
                select(GitCommit)
                .join(pr_commits, GitCommit.id == pr_commits.c.commit_id)
                .where(pr_commits.c.pr_id == pr_id)
                .order_by(pr_commits.c.position)
            )
            result = await self.session.execute(stmt)
            commits = list(result.scalars().all())
            logger.info(f"Found {len(commits)} commits for PR {pr_id}")
            return commits
        except SQLAlchemyError as e:
            logger.error(f"Error fetching linked commits for PR {pr_id}: {e}", exc_info=True)
            raise

    async def count_by_project(self, project_id: UUID, state: str | None = None) -> int:
        """
        Count pull requests for a project.

        Args:
            project_id: UUID of the project
            state: Optional state filter

        Returns:
            Count of PRs matching criteria

        Raises:
            SQLAlchemyError: If database query fails
        """
        try:
            stmt = (
                select(func.count())
                .select_from(PullRequest)
                .where(PullRequest.project_id == project_id)
            )

            if state:
                stmt = stmt.where(PullRequest.state == state)

            result = await self.session.execute(stmt)
            count = result.scalar() or 0
            logger.info(f"Counted {count} PRs for project {project_id}")
            return count
        except SQLAlchemyError as e:
            logger.error(f"Error counting PRs for project {project_id}: {e}", exc_info=True)
            raise

    async def get_pr_with_full_details(
        self, pr_id: UUID
    ) -> tuple[PullRequest, list[Task], list[GitCommit]] | None:
        """
        Get PR with all relationships loaded.

        Efficiently fetches PR, tasks, and commits in optimized queries.

        Args:
            pr_id: UUID of the PR

        Returns:
            Tuple of (PR, tasks, commits) if found, None if PR not found

        Raises:
            SQLAlchemyError: If database query fails
        """
        try:
            # Fetch PR with basic relationships
            pr = await self.get_by_id(pr_id)
            if not pr:
                return None

            # Fetch linked tasks
            tasks = await self.get_linked_tasks(pr_id)

            # Fetch linked commits
            commits = await self.get_linked_commits(pr_id)

            logger.info(
                f"Fetched PR {pr_id} with {len(tasks)} tasks " f"and {len(commits)} commits"
            )
            return (pr, tasks, commits)
        except SQLAlchemyError as e:
            logger.error(f"Error fetching full details for PR {pr_id}: {e}", exc_info=True)
            raise
