"""
Git commit service for business logic.

This module provides the business logic layer for git commit management, handling:
- Permission checks
- Git operations integration
- Task linking
- Commit metadata management
"""

import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Optional
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from ardha.models.git_commit import GitCommit
from ardha.repositories.git_commit import GitCommitRepository
from ardha.schemas.git_commit import LinkType
from ardha.services.git_service import GitService
from ardha.services.project_service import ProjectService

logger = logging.getLogger(__name__)


# ============= Custom Exceptions =============


class GitCommitNotFoundError(Exception):
    """Raised when a git commit is not found."""

    pass


class GitCommitPermissionError(Exception):
    """Raised when user lacks permissions for git commit operation."""

    pass


class GitCommitValidationError(Exception):
    """Raised when git commit validation fails."""

    pass


class GitCommitOperationError(Exception):
    """Raised when git commit operation fails."""

    pass


class GitCommitService:
    """
    Service layer for git commit business logic.

    Handles:
    - Permission-based access control
    - Git operations integration
    - Task linking and management
    - Commit metadata and history
    """

    def __init__(self, db: AsyncSession, project_root: str):
        """
        Initialize git commit service.

        Args:
            db: Async SQLAlchemy database session
            project_root: Path to project root directory
        """
        self.db = db
        self.repository = GitCommitRepository(db)
        self.project_service = ProjectService(db)
        self.git_service = GitService(Path(project_root))

    # ============= Core Git Commit Operations =============

    async def create_commit(
        self,
        project_id: UUID,
        message: str,
        user_id: UUID,
        author_name: Optional[str] = None,
        author_email: Optional[str] = None,
        file_ids: Optional[list[UUID]] = None,
    ) -> GitCommit:
        """
        Create a git commit and record it in the database.

        Args:
            project_id: Project UUID
            message: Commit message
            user_id: User creating the commit
            author_name: Optional author name override
            author_email: Optional author email override
            file_ids: Optional specific files to commit

        Returns:
            Created GitCommit object

        Raises:
            GitCommitPermissionError: If user lacks permissions
            GitCommitValidationError: If commit validation fails
            GitCommitOperationError: If commit operation fails
        """
        # Check project permissions (must be at least member)
        if not await self.project_service.check_permission(
            project_id=project_id,
            user_id=user_id,
            required_role="member",
        ):
            raise GitCommitPermissionError("Must be at least a project member to create commits")

        # Validate commit message
        await self._validate_commit_message(message)

        try:
            # Get user info for git author
            if not author_name:
                author_name = await self._get_user_name(user_id)
            if not author_email:
                author_email = await self._get_user_email(user_id)

            # Stage specific files if provided
            if file_ids:
                await self._stage_files_by_ids(file_ids)

            # Create git commit
            commit_info = self.git_service.commit(
                message=message,
                author_name=author_name,
                author_email=author_email,
            )

            # Get current branch
            current_branch = self.git_service.get_current_branch()

            # Parse commit message for task IDs
            task_info = self.git_service.parse_commit_message(message)

            # Create database record
            commit_data = {
                "project_id": project_id,
                "sha": commit_info["sha"],
                "message": message,
                "author_name": commit_info["author_name"],
                "author_email": commit_info["author_email"],
                "branch": current_branch,
                "committed_at": datetime.fromisoformat(commit_info["committed_at"]),
                "is_merge": False,
                "files_changed": commit_info["files_changed"],
                "insertions": commit_info["insertions"],
                "deletions": commit_info["deletions"],
                "ardha_user_id": user_id,
                "linked_task_ids": task_info.get("mentioned", []),
                "closes_task_ids": task_info.get("closes", []),
            }

            commit = GitCommit(**commit_data)
            created_commit = await self.repository.create(commit)

            # Link to files if specified
            if file_ids:
                await self._link_commit_to_files(created_commit.id, file_ids)

            logger.info(f"Created commit {commit_info['sha']} in project {project_id}")
            return created_commit

        except Exception as e:
            logger.error(f"Failed to create commit: {e}")
            raise GitCommitOperationError(f"Failed to create commit: {e}")

    async def get_commit(self, commit_id: UUID, user_id: UUID) -> GitCommit:
        """
        Get git commit by ID with permission check.

        Args:
            commit_id: Commit UUID
            user_id: User requesting commit

        Returns:
            GitCommit object if found and user has permission

        Raises:
            GitCommitNotFoundError: If commit not found
            GitCommitPermissionError: If user lacks permissions
        """
        commit = await self.repository.get_by_id(commit_id)
        if not commit:
            raise GitCommitNotFoundError(f"Git commit {commit_id} not found")

        # Check project access
        if not await self.project_service.check_permission(
            project_id=commit.project_id,
            user_id=user_id,
            required_role="viewer",
        ):
            raise GitCommitPermissionError("Must be a project member to view commits")

        return commit

    async def list_commits(
        self,
        project_id: UUID,
        user_id: UUID,
        branch: Optional[str] = None,
        author_email: Optional[str] = None,
        since: Optional[datetime] = None,
        until: Optional[datetime] = None,
        search: Optional[str] = None,
        skip: int = 0,
        limit: int = 50,
    ) -> tuple[list[GitCommit], int]:
        """
        List git commits in a project with filtering and permission check.

        Args:
            project_id: Project UUID
            user_id: User requesting commits
            branch: Optional branch filter
            author_email: Optional author email filter
            since: Optional start date filter
            until: Optional end date filter
            search: Optional search in commit messages
            skip: Pagination offset
            limit: Page size

        Returns:
            Tuple of (commits list, total count)

        Raises:
            GitCommitPermissionError: If user lacks permissions
        """
        # Check project access
        if not await self.project_service.check_permission(
            project_id=project_id,
            user_id=user_id,
            required_role="viewer",
        ):
            raise GitCommitPermissionError("Must be a project member to view commits")

        try:
            # Get commits from database
            commits = await self.repository.list_by_project(
                project_id=project_id,
                branch=branch,
                author_email=author_email,
                since=since,
                until=until,
                skip=skip,
                limit=limit,
            )

            # Filter by search query if provided
            if search:
                commits = [c for c in commits if search.lower() in c.message.lower()]

            # Get total count
            total = await self.repository.count_by_project(
                project_id=project_id,
                branch=branch,
            )

            return commits, total

        except Exception as e:
            logger.error(f"Failed to list commits for project {project_id}: {e}")
            raise GitCommitOperationError(f"Failed to list commits: {e}")

    async def link_commit_to_tasks(
        self,
        commit_id: UUID,
        user_id: UUID,
        task_ids: list[str],
        link_type: LinkType = LinkType.MENTIONED,
    ) -> GitCommit:
        """
        Link a commit to tasks.

        Args:
            commit_id: Commit UUID
            user_id: User performing the linking
            task_ids: List of task identifiers
            link_type: Type of link

        Returns:
            Updated GitCommit object

        Raises:
            GitCommitNotFoundError: If commit not found
            GitCommitPermissionError: If user lacks permissions
        """
        commit = await self.get_commit(commit_id, user_id)

        # Check permissions (must be at least member)
        if not await self.project_service.check_permission(
            project_id=commit.project_id,
            user_id=user_id,
            required_role="member",
        ):
            raise GitCommitPermissionError("Must be at least a project member to link tasks")

        try:
            # Convert task identifiers to UUIDs (this would need task resolution)
            # For now, we'll store them as strings and handle the conversion in the repository
            task_uuids = []
            for tid in task_ids:
                try:
                    # Try to convert to UUID if it looks like one
                    clean_tid = (
                        tid.replace("#", "")
                        .replace("TASK-", "")
                        .replace("TAS-", "")
                        .replace("ARD-", "")
                    )
                    if clean_tid.replace("-", "").isdigit():
                        task_uuids.append(UUID(clean_tid))
                    else:
                        # For non-UUID identifiers, we'll need to resolve them differently
                        # For now, skip them in the UUID list
                        pass
                except ValueError:
                    # Invalid UUID format, skip
                    pass

            # Link to tasks in database (only valid UUIDs)
            if task_uuids:
                await self.repository.link_to_tasks(
                    commit_id=commit_id,
                    task_ids=task_uuids,
                    link_type=link_type.value,
                )

            # Update commit record with task IDs
            update_data = {}
            if link_type == LinkType.MENTIONED:
                update_data["linked_task_ids"] = list(
                    set((commit.linked_task_ids or []) + task_ids)
                )
            elif link_type == LinkType.CLOSES:
                update_data["closes_task_ids"] = list(
                    set((commit.closes_task_ids or []) + task_ids)
                )

            updated_commit = await self.repository.update(commit_id, update_data)

            if not updated_commit:
                raise GitCommitOperationError("Failed to update commit record")

            logger.info(f"Linked commit {commit_id} to {len(task_ids)} tasks")
            return updated_commit

        except Exception as e:
            logger.error(f"Failed to link commit {commit_id} to tasks: {e}")
            raise GitCommitOperationError(f"Failed to link commit to tasks: {e}")

    async def get_commit_with_files(
        self,
        commit_id: UUID,
        user_id: UUID,
    ) -> tuple[GitCommit, list[tuple[Any, dict]]]:
        """
        Get commit with detailed file changes.

        Args:
            commit_id: Commit UUID
            user_id: User requesting commit details

        Returns:
            Tuple of (commit, file changes)

        Raises:
            GitCommitNotFoundError: If commit not found
            GitCommitPermissionError: If user lacks permissions
        """
        commit = await self.get_commit(commit_id, user_id)

        try:
            # Get commit with files from repository
            result = await self.repository.get_commit_with_files(commit_id)
            if not result:
                return commit, []

            _, file_changes = result
            return commit, file_changes

        except Exception as e:
            logger.error(f"Failed to get commit {commit_id} with files: {e}")
            raise GitCommitOperationError(f"Failed to get commit with files: {e}")

    async def get_file_commits(
        self,
        file_id: UUID,
        user_id: UUID,
        max_count: int = 50,
    ) -> list[GitCommit]:
        """
        Get commits that changed a specific file.

        Args:
            file_id: File UUID
            user_id: User requesting commits
            max_count: Maximum number of commits to return

        Returns:
            List of GitCommit objects

        Raises:
            GitCommitPermissionError: If user lacks permissions
        """
        # This would need to verify file access first
        # For now, we'll get commits and let the caller handle permissions

        try:
            commits = await self.repository.list_by_file(file_id, max_count)

            # Check project permissions for each commit
            filtered_commits = []
            for commit in commits:
                if await self.project_service.check_permission(
                    project_id=commit.project_id,
                    user_id=user_id,
                    required_role="viewer",
                ):
                    filtered_commits.append(commit)

            return filtered_commits

        except Exception as e:
            logger.error(f"Failed to get commits for file {file_id}: {e}")
            raise GitCommitOperationError(f"Failed to get file commits: {e}")

    async def get_user_commits(
        self,
        user_id: UUID,
        requesting_user_id: UUID,
        project_id: Optional[UUID] = None,
        skip: int = 0,
        limit: int = 50,
    ) -> list[GitCommit]:
        """
        Get commits by a specific user.

        Args:
            user_id: User whose commits to get
            requesting_user_id: User making the request
            project_id: Optional project filter
            skip: Pagination offset
            limit: Page size

        Returns:
            List of GitCommit objects

        Raises:
            GitCommitPermissionError: If user lacks permissions
        """
        try:
            commits = await self.repository.list_by_user(
                user_id=user_id,
                project_id=project_id,
                skip=skip,
                limit=limit,
            )

            # Check project permissions for each commit
            filtered_commits = []
            for commit in commits:
                if await self.project_service.check_permission(
                    project_id=commit.project_id,
                    user_id=requesting_user_id,
                    required_role="viewer",
                ):
                    filtered_commits.append(commit)

            return filtered_commits

        except Exception as e:
            logger.error(f"Failed to get commits for user {user_id}: {e}")
            raise GitCommitOperationError(f"Failed to get user commits: {e}")

    async def get_latest_commit(
        self,
        project_id: UUID,
        user_id: UUID,
        branch: Optional[str] = None,
    ) -> Optional[GitCommit]:
        """
        Get the most recent commit in a project.

        Args:
            project_id: Project UUID
            user_id: User requesting commit
            branch: Optional branch filter

        Returns:
            Latest GitCommit object or None

        Raises:
            GitCommitPermissionError: If user lacks permissions
        """
        # Check project access
        if not await self.project_service.check_permission(
            project_id=project_id,
            user_id=user_id,
            required_role="viewer",
        ):
            raise GitCommitPermissionError("Must be a project member to view commits")

        try:
            return await self.repository.get_latest_commit(
                project_id=project_id,
                branch=branch,
            )

        except Exception as e:
            logger.error(f"Failed to get latest commit for project {project_id}: {e}")
            raise GitCommitOperationError(f"Failed to get latest commit: {e}")

    async def sync_commits_from_git(
        self,
        project_id: UUID,
        user_id: UUID,
        branch: Optional[str] = None,
        since: Optional[datetime] = None,
    ) -> dict:
        """
        Sync commits from git repository to database.

        Args:
            project_id: Project UUID
            user_id: User performing sync
            branch: Optional branch filter
            since: Optional start date

        Returns:
            Sync statistics

        Raises:
            GitCommitPermissionError: If user lacks permissions
        """
        # Check permissions (must be at least admin)
        if not await self.project_service.check_permission(
            project_id=project_id,
            user_id=user_id,
            required_role="admin",
        ):
            raise GitCommitPermissionError("Must be project admin or owner to sync commits")

        try:
            # Get commit history from git
            git_commits = self.git_service.get_commit_history(
                branch=branch,
                max_count=1000,  # Limit for performance
            )

            synced_count = 0
            new_commits = 0
            updated_commits = 0

            for git_commit in git_commits:
                # Check if commit already exists
                existing_commit = await self.repository.get_by_sha(
                    project_id=project_id,
                    sha=git_commit["sha"],
                )

                if not existing_commit:
                    # Create new commit record
                    commit_data = {
                        "project_id": project_id,
                        "sha": git_commit["sha"],
                        "message": git_commit["message"],
                        "author_name": git_commit["author_name"],
                        "author_email": git_commit["author_email"],
                        "branch": git_commit.get("branch", "main"),
                        "committed_at": datetime.fromisoformat(git_commit["committed_at"]),
                        "is_merge": False,
                        "files_changed": git_commit["files_changed"],
                        "insertions": git_commit["insertions"],
                        "deletions": git_commit["deletions"],
                        "ardha_user_id": await self._map_git_author_to_user(
                            git_commit["author_email"]
                        ),
                    }

                    commit = GitCommit(**commit_data)
                    await self.repository.create(commit)
                    new_commits += 1
                else:
                    # Update existing commit if needed
                    updated_commits += 1

                synced_count += 1

            return {
                "synced_count": synced_count,
                "new_commits": new_commits,
                "updated_commits": updated_commits,
                "branch": branch or "all",
            }

        except Exception as e:
            logger.error(f"Failed to sync commits for project {project_id}: {e}")
            raise GitCommitOperationError(f"Failed to sync commits: {e}")

    async def get_commit_stats(
        self,
        project_id: UUID,
        user_id: UUID,
        branch: Optional[str] = None,
    ) -> dict:
        """
        Get commit statistics for a project.

        Args:
            project_id: Project UUID
            user_id: User requesting stats
            branch: Optional branch filter

        Returns:
            Commit statistics

        Raises:
            GitCommitPermissionError: If user lacks permissions
        """
        # Check project access
        if not await self.project_service.check_permission(
            project_id=project_id,
            user_id=user_id,
            required_role="viewer",
        ):
            raise GitCommitPermissionError("Must be a project member to view commit stats")

        try:
            # Get all commits for the project
            commits = await self.repository.list_by_project(
                project_id=project_id,
                branch=branch,
                skip=0,
                limit=1000,  # Limit for performance
            )

            # Calculate statistics
            total_commits = len(commits)
            total_insertions = sum(c.insertions for c in commits)
            total_deletions = sum(c.deletions for c in commits)
            total_files_changed = sum(c.files_changed for c in commits)

            # Get unique branches
            branches = list(set(c.branch for c in commits if c.branch))

            # Get top contributors
            contributor_stats = {}
            for commit in commits:
                email = commit.author_email
                if email not in contributor_stats:
                    contributor_stats[email] = {
                        "name": commit.author_name,
                        "email": email,
                        "commit_count": 0,
                        "insertions": 0,
                        "deletions": 0,
                    }
                contributor_stats[email]["commit_count"] += 1
                contributor_stats[email]["insertions"] += commit.insertions
                contributor_stats[email]["deletions"] += commit.deletions

            top_contributors = sorted(
                contributor_stats.values(),
                key=lambda x: x["commit_count"],
                reverse=True,
            )[:10]

            return {
                "total_commits": total_commits,
                "total_insertions": total_insertions,
                "total_deletions": total_deletions,
                "total_files_changed": total_files_changed,
                "branches": branches,
                "top_contributors": top_contributors,
            }

        except Exception as e:
            logger.error(f"Failed to get commit stats for project {project_id}: {e}")
            raise GitCommitOperationError(f"Failed to get commit stats: {e}")

    # ============= Helper Methods =============

    async def _validate_commit_message(self, message: str) -> None:
        """Validate commit message."""
        if not message or not message.strip():
            raise GitCommitValidationError("Commit message cannot be empty")

        if len(message) > 10000:
            raise GitCommitValidationError("Commit message too long (max 10000 characters)")

    async def _stage_files_by_ids(self, file_ids: list[UUID]) -> None:
        """Stage files by their database IDs."""
        # This would need to resolve file IDs to paths
        # For now, we'll stage all changes
        if self.git_service.is_initialized():
            status = self.git_service.get_status()
            all_files = (
                status["untracked"] + status["modified"] + status["staged"] + status["deleted"]
            )
            if all_files:
                self.git_service.stage_files(all_files)

    async def _link_commit_to_files(self, commit_id: UUID, file_ids: list[UUID]) -> None:
        """Link commit to files with change details."""
        # This would need to resolve file IDs and get change details
        # For now, we'll create basic file links
        file_changes = []
        for file_id in file_ids:
            file_changes.append(
                {
                    "file_id": file_id,
                    "change_type": "modified",  # Default
                    "insertions": 0,
                    "deletions": 0,
                }
            )

        if file_changes:
            await self.repository.link_to_files(commit_id, file_changes)

    async def _get_user_name(self, user_id: UUID) -> str:
        """Get user name for git operations."""
        # This would typically query the user repository
        return f"User-{user_id.hex[:8]}"

    async def _get_user_email(self, user_id: UUID) -> str:
        """Get user email for git operations."""
        # This would typically query the user repository
        return f"user-{user_id.hex[:8]}@ardha.local"

    async def _map_git_author_to_user(self, author_email: str) -> Optional[UUID]:
        """Map git author email to Ardha user ID."""
        # This would typically query the user repository
        # For now, return None to indicate unmapped
        return None
