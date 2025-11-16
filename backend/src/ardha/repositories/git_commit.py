"""
GitCommit repository for data access abstraction.

This module provides the repository pattern implementation for the GitCommit model,
handling all database operations related to git commit history and task/file linking.
"""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple, TYPE_CHECKING
from uuid import UUID

from sqlalchemy import select, and_, or_, func, insert, delete
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ardha.models.git_commit import GitCommit, file_commits, task_commits
from ardha.schemas.file import ChangeType

if TYPE_CHECKING:
    from ardha.models.file import File
    from ardha.models.task import Task

logger = logging.getLogger(__name__)


class GitCommitRepository:
    """
    Repository for GitCommit model database operations.

    Provides data access methods for git commit-related operations including
    CRUD operations, task/file linking, commit history queries, and
    relationship loading. Follows the repository pattern to abstract
    database implementation details from business logic.

    Attributes:
        session: SQLAlchemy async session for database operations
    """

    def __init__(self, session: AsyncSession):
        """
        Initialize the GitCommitRepository with a database session.

        Args:
            session: SQLAlchemy async session for database operations
        """
        self.session = session

    async def create(self, commit: GitCommit) -> GitCommit:
        """
        Create a new git commit in the database.

        Args:
            commit: GitCommit model instance to create

        Returns:
            Created GitCommit object with ID and timestamps

        Raises:
            IntegrityError: If unique constraint violated (project_id, sha)
            SQLAlchemyError: If database operation fails
        """
        try:
            self.session.add(commit)
            await self.session.commit()
            await self.session.refresh(commit)
            logger.info(f"Created git commit {commit.id} with sha '{commit.sha}'")
            return commit
        except IntegrityError as e:
            logger.warning(f"Integrity error creating git commit: {e}")
            await self.session.rollback()
            raise
        except SQLAlchemyError as e:
            logger.error(f"Error creating git commit: {e}", exc_info=True)
            await self.session.rollback()
            raise

    async def get_by_id(self, commit_id: UUID) -> Optional[GitCommit]:
        """
        Fetch a git commit by its UUID.

        Args:
            commit_id: UUID of the commit to fetch

        Returns:
            GitCommit object if found, None otherwise

        Raises:
            SQLAlchemyError: If database query fails
        """
        try:
            stmt = select(GitCommit).where(GitCommit.id == commit_id).options(
                selectinload(GitCommit.project),
                selectinload(GitCommit.ardha_user),
                selectinload(GitCommit.files),
                selectinload(GitCommit.linked_tasks)
            )
            result = await self.session.execute(stmt)
            return result.scalar_one_or_none()
        except SQLAlchemyError as e:
            logger.error(f"Error fetching git commit by id {commit_id}: {e}", exc_info=True)
            raise

    async def get_by_sha(self, project_id: UUID, sha: str) -> Optional[GitCommit]:
        """
        Fetch a git commit by project_id and SHA.

        Args:
            project_id: UUID of the project
            sha: Git commit SHA (full or short, 7+ chars)

        Returns:
            GitCommit object if found, None otherwise

        Raises:
            SQLAlchemyError: If database query fails
        """
        try:
            # Handle both full SHA (40) and short SHA (7+)
            if len(sha) >= 40:
                # Full SHA match
                stmt = select(GitCommit).where(
                    and_(GitCommit.project_id == project_id, GitCommit.sha == sha)
                )
            else:
                # Short SHA match
                stmt = select(GitCommit).where(
                    and_(GitCommit.project_id == project_id, GitCommit.short_sha == sha)
                )

            stmt = stmt.options(
                selectinload(GitCommit.project),
                selectinload(GitCommit.ardha_user)
            )

            result = await self.session.execute(stmt)
            return result.scalar_one_or_none()
        except SQLAlchemyError as e:
            logger.error(f"Error fetching git commit by sha {sha}: {e}", exc_info=True)
            raise

    async def list_by_project(
        self,
        project_id: UUID,
        branch: Optional[str] = None,
        author_email: Optional[str] = None,
        since: Optional[datetime] = None,
        until: Optional[datetime] = None,
        skip: int = 0,
        limit: int = 50,
    ) -> List[GitCommit]:
        """
        List git commits in a project with optional filtering.

        Args:
            project_id: UUID of the project
            branch: Optional branch filter
            author_email: Optional author email filter
            since: Optional start date filter
            until: Optional end date filter
            skip: Number of records to skip (for pagination)
            limit: Maximum number of records to return

        Returns:
            List of GitCommit objects

        Raises:
            SQLAlchemyError: If database query fails
        """
        try:
            stmt = select(GitCommit).where(GitCommit.project_id == project_id)

            # Apply filters
            if branch:
                stmt = stmt.where(GitCommit.branch == branch)
            if author_email:
                stmt = stmt.where(GitCommit.author_email == author_email)
            if since:
                stmt = stmt.where(GitCommit.committed_at >= since)
            if until:
                stmt = stmt.where(GitCommit.committed_at <= until)

            # Apply pagination and ordering
            stmt = stmt.order_by(GitCommit.committed_at.desc()).offset(skip).limit(min(limit, 50))

            result = await self.session.execute(stmt)
            return list(result.scalars().all())
        except SQLAlchemyError as e:
            logger.error(f"Error listing git commits for project {project_id}: {e}", exc_info=True)
            raise

    async def list_by_file(
        self,
        file_id: UUID,
        max_count: int = 50,
    ) -> List[GitCommit]:
        """
        Get commits that changed a specific file.

        Args:
            file_id: UUID of the file
            max_count: Maximum number of commits to return

        Returns:
            List of GitCommit objects that modified the file

        Raises:
            SQLAlchemyError: If database query fails
        """
        try:
            stmt = (
                select(GitCommit)
                .join(file_commits, GitCommit.id == file_commits.c.commit_id)
                .where(file_commits.c.file_id == file_id)
                .order_by(GitCommit.committed_at.desc())
                .limit(min(max_count, 50))
            )

            result = await self.session.execute(stmt)
            return list(result.scalars().all())
        except SQLAlchemyError as e:
            logger.error(f"Error listing commits for file {file_id}: {e}", exc_info=True)
            raise

    async def list_by_task(
        self,
        task_id: UUID,
        max_count: int = 50,
    ) -> List[GitCommit]:
        """
        Get commits linked to a specific task.

        Args:
            task_id: UUID of the task
            max_count: Maximum number of commits to return

        Returns:
            List of GitCommit objects linked to the task

        Raises:
            SQLAlchemyError: If database query fails
        """
        try:
            stmt = (
                select(GitCommit)
                .join(task_commits, GitCommit.id == task_commits.c.commit_id)
                .where(task_commits.c.task_id == task_id)
                .order_by(GitCommit.committed_at.desc())
                .limit(min(max_count, 50))
            )

            result = await self.session.execute(stmt)
            return list(result.scalars().all())
        except SQLAlchemyError as e:
            logger.error(f"Error listing commits for task {task_id}: {e}", exc_info=True)
            raise

    async def list_by_user(
        self,
        user_id: UUID,
        project_id: Optional[UUID] = None,
        skip: int = 0,
        limit: int = 50,
    ) -> List[GitCommit]:
        """
        Get commits by a specific Ardha user.

        Args:
            user_id: UUID of the Ardha user
            project_id: Optional project filter
            skip: Number of records to skip (for pagination)
            limit: Maximum number of records to return

        Returns:
            List of GitCommit objects by the user

        Raises:
            SQLAlchemyError: If database query fails
        """
        try:
            stmt = select(GitCommit).where(GitCommit.ardha_user_id == user_id)

            if project_id:
                stmt = stmt.where(GitCommit.project_id == project_id)

            stmt = stmt.order_by(GitCommit.committed_at.desc()).offset(skip).limit(min(limit, 50))

            result = await self.session.execute(stmt)
            return list(result.scalars().all())
        except SQLAlchemyError as e:
            logger.error(f"Error listing commits for user {user_id}: {e}", exc_info=True)
            raise

    async def update(self, commit_id: UUID, update_data: Dict[str, Any]) -> Optional[GitCommit]:
        """
        Update git commit fields.

        Args:
            commit_id: UUID of commit to update
            update_data: Dictionary of fields to update

        Returns:
            Updated GitCommit object if found, None otherwise

        Raises:
            SQLAlchemyError: If database operation fails
        """
        try:
            commit = await self.get_by_id(commit_id)
            if not commit:
                logger.warning(f"Cannot update: git commit {commit_id} not found")
                return None

            # Update fields
            for key, value in update_data.items():
                if hasattr(commit, key):
                    setattr(commit, key, value)
                else:
                    logger.warning(f"Skipping unknown field: {key}")

            await self.session.commit()
            await self.session.refresh(commit)
            logger.info(f"Updated git commit {commit_id}")
            return commit
        except SQLAlchemyError as e:
            logger.error(f"Error updating git commit {commit_id}: {e}", exc_info=True)
            await self.session.rollback()
            raise

    async def link_to_tasks(
        self,
        commit_id: UUID,
        task_ids: List[UUID],
        link_type: str = "mentioned",
    ) -> None:
        """
        Link a commit to multiple tasks.

        Args:
            commit_id: UUID of the commit
            task_ids: List of task UUIDs to link
            link_type: Type of link (mentioned, closes, fixes, implements)

        Raises:
            SQLAlchemyError: If database operation fails
        """
        try:
            # Prepare bulk insert data
            insert_data = [
                {
                    "task_id": task_id,
                    "commit_id": commit_id,
                    "link_type": link_type,
                }
                for task_id in task_ids
            ]

            # Use insert with conflict handling for PostgreSQL
            # For now, we'll use a simple approach and let duplicates raise errors
            # In a production environment, you might want to use database-specific conflict resolution
            try:
                stmt = insert(task_commits).values(insert_data)
                await self.session.execute(stmt)
            except IntegrityError:
                # Duplicates already exist, which is fine for this operation
                logger.debug(f"Some task links already exist for commit {commit_id}")
                pass
            await self.session.commit()
            logger.info(f"Linked commit {commit_id} to {len(task_ids)} tasks")
        except SQLAlchemyError as e:
            logger.error(f"Error linking commit {commit_id} to tasks: {e}", exc_info=True)
            await self.session.rollback()
            raise

    async def unlink_from_tasks(self, commit_id: UUID, task_ids: List[UUID]) -> None:
        """
        Unlink a commit from multiple tasks.

        Args:
            commit_id: UUID of the commit
            task_ids: List of task UUIDs to unlink

        Raises:
            SQLAlchemyError: If database operation fails
        """
        try:
            stmt = delete(task_commits).where(
                and_(
                    task_commits.c.commit_id == commit_id,
                    task_commits.c.task_id.in_(task_ids)
                )
            )

            result = await self.session.execute(stmt)
            await self.session.commit()
            logger.info(f"Unlinked commit {commit_id} from {result.rowcount} tasks")
        except SQLAlchemyError as e:
            logger.error(f"Error unlinking commit {commit_id} from tasks: {e}", exc_info=True)
            await self.session.rollback()
            raise

    async def link_to_files(
        self,
        commit_id: UUID,
        file_changes: List[Dict],
    ) -> None:
        """
        Link a commit to files with change details.

        Args:
            commit_id: UUID of the commit
            file_changes: List of file change dictionaries

        Raises:
            SQLAlchemyError: If database operation fails
        """
        try:
            # Prepare bulk insert data
            insert_data = []
            for change in file_changes:
                insert_data.append({
                    "file_id": change["file_id"],
                    "commit_id": commit_id,
                    "change_type": change["change_type"].value,
                    "old_path": change.get("old_path"),
                    "insertions": change.get("insertions", 0),
                    "deletions": change.get("deletions", 0),
                })

            # Clear existing file links for this commit
            await self.session.execute(
                delete(file_commits).where(file_commits.c.commit_id == commit_id)
            )

            # Insert new file links
            if insert_data:
                stmt = insert(file_commits).values(insert_data)
                await self.session.execute(stmt)

            await self.session.commit()
            logger.info(f"Linked commit {commit_id} to {len(insert_data)} files")
        except SQLAlchemyError as e:
            logger.error(f"Error linking commit {commit_id} to files: {e}", exc_info=True)
            await self.session.rollback()
            raise

    async def get_commit_with_files(
        self,
        commit_id: UUID,
    ) -> Optional[Tuple[GitCommit, List[Tuple["File", Dict]]]]:
        """
        Get commit with all changed files and their change details.

        Args:
            commit_id: UUID of the commit

        Returns:
            Tuple of (commit, [(file, change_info)]) if found, None otherwise

        Raises:
            SQLAlchemyError: If database query fails
        """
        try:
            # Import here to avoid circular imports
            from ardha.models.file import File

            # Get commit
            commit = await self.get_by_id(commit_id)
            if not commit:
                return None

            # Get file changes with details
            stmt = (
                select(
                    File,
                    file_commits.c.change_type,
                    file_commits.c.old_path,
                    file_commits.c.insertions,
                    file_commits.c.deletions,
                )
                .join(file_commits, File.id == file_commits.c.file_id)
                .where(file_commits.c.commit_id == commit_id)
                .order_by(File.path)
            )

            result = await self.session.execute(stmt)
            file_changes = []

            for row in result.all():
                file, change_type, old_path, insertions, deletions = row
                change_info = {
                    "change_type": change_type,
                    "old_path": old_path,
                    "insertions": insertions,
                    "deletions": deletions,
                }
                file_changes.append((file, change_info))

            return (commit, file_changes)
        except SQLAlchemyError as e:
            logger.error(f"Error getting commit {commit_id} with files: {e}", exc_info=True)
            raise

    async def count_by_project(
        self,
        project_id: UUID,
        branch: Optional[str] = None,
    ) -> int:
        """
        Count commits in a project.

        Args:
            project_id: UUID of the project
            branch: Optional branch filter

        Returns:
            Number of commits matching criteria

        Raises:
            SQLAlchemyError: If database query fails
        """
        try:
            stmt = select(func.count(GitCommit.id)).where(GitCommit.project_id == project_id)

            if branch:
                stmt = stmt.where(GitCommit.branch == branch)

            result = await self.session.execute(stmt)
            return result.scalar() or 0
        except SQLAlchemyError as e:
            logger.error(f"Error counting commits for project {project_id}: {e}", exc_info=True)
            raise

    async def get_latest_commit(
        self,
        project_id: UUID,
        branch: Optional[str] = None,
    ) -> Optional[GitCommit]:
        """
        Get the most recent commit in a project.

        Args:
            project_id: UUID of the project
            branch: Optional branch filter

        Returns:
            Most recent GitCommit object if found, None otherwise

        Raises:
            SQLAlchemyError: If database query fails
        """
        try:
            stmt = select(GitCommit).where(GitCommit.project_id == project_id)

            if branch:
                stmt = stmt.where(GitCommit.branch == branch)

            stmt = stmt.order_by(GitCommit.committed_at.desc()).limit(1)

            result = await self.session.execute(stmt)
            return result.scalar_one_or_none()
        except SQLAlchemyError as e:
            logger.error(f"Error getting latest commit for project {project_id}: {e}", exc_info=True)
            raise

    async def bulk_create(self, commits: List[GitCommit]) -> List[GitCommit]:
        """
        Create multiple commits in one transaction.

        Args:
            commits: List of GitCommit objects to create

        Returns:
            List of created GitCommit objects

        Raises:
            SQLAlchemyError: If database operation fails
        """
        try:
            self.session.add_all(commits)
            await self.session.commit()
            
            # Refresh all commits to get their IDs
            for commit in commits:
                await self.session.refresh(commit)
            
            logger.info(f"Bulk created {len(commits)} git commits")
            return commits
        except IntegrityError as e:
            logger.warning(f"Integrity error in bulk create: {e}")
            await self.session.rollback()
            raise
        except SQLAlchemyError as e:
            logger.error(f"Error in bulk creating git commits: {e}", exc_info=True)
            await self.session.rollback()
            raise