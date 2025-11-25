"""
File repository for data access abstraction.

This module provides the repository pattern implementation for the File model,
handling all database operations related to file management and git tracking.
"""

import logging
from datetime import datetime
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Tuple
from uuid import UUID

from sqlalchemy import and_, func, or_, select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ardha.models.file import File
from ardha.schemas.file import FileType

if TYPE_CHECKING:
    from ardha.models.git_commit import GitCommit

logger = logging.getLogger(__name__)


class FileRepository:
    """
    Repository for File model database operations.

    Provides data access methods for file-related operations including
    CRUD operations, content management, git metadata tracking, and
    relationship loading with commits. Follows the repository pattern
    to abstract database implementation details from business logic.

    Attributes:
        session: SQLAlchemy async session for database operations
    """

    def __init__(self, session: AsyncSession):
        """
        Initialize the FileRepository with a database session.

        Args:
            session: SQLAlchemy async session for database operations
        """
        self.session = session

    async def create(self, file: File) -> File:
        """
        Create a new file in the database.

        Args:
            file: File model instance to create

        Returns:
            Created File object with ID and timestamps

        Raises:
            IntegrityError: If unique constraint violated (project_id, path)
            SQLAlchemyError: If database operation fails
        """
        try:
            self.session.add(file)
            await self.session.commit()
            await self.session.refresh(file)
            logger.info(f"Created file {file.id} with path '{file.path}'")
            return file
        except IntegrityError as e:
            logger.warning(f"Integrity error creating file: {e}")
            await self.session.rollback()
            raise
        except SQLAlchemyError as e:
            logger.error(f"Error creating file: {e}", exc_info=True)
            await self.session.rollback()
            raise

    async def get_by_id(self, file_id: UUID) -> Optional[File]:
        """
        Fetch a file by its UUID.

        Args:
            file_id: UUID of the file to fetch

        Returns:
            File object if found, None otherwise

        Raises:
            SQLAlchemyError: If database query fails
        """
        try:
            stmt = (
                select(File)
                .where(and_(File.id == file_id, File.is_deleted.is_(False)))
                .options(
                    selectinload(File.project),
                    selectinload(File.last_modified_by),
                    selectinload(File.commits),
                )
            )
            result = await self.session.execute(stmt)
            return result.scalar_one_or_none()
        except SQLAlchemyError as e:
            logger.error(f"Error fetching file by id {file_id}: {e}", exc_info=True)
            raise

    async def get_by_path(self, project_id: UUID, path: str) -> Optional[File]:
        """
        Fetch a file by project_id and path.

        Args:
            project_id: UUID of the project
            path: File path within the project

        Returns:
            File object if found, None otherwise

        Raises:
            SQLAlchemyError: If database query fails
        """
        try:
            stmt = (
                select(File)
                .where(and_(File.project_id == project_id, File.path == path))
                .options(selectinload(File.project), selectinload(File.last_modified_by))
            )
            result = await self.session.execute(stmt)
            return result.scalar_one_or_none()
        except SQLAlchemyError as e:
            logger.error(f"Error fetching file by path {path}: {e}", exc_info=True)
            raise

    async def list_by_project(
        self,
        project_id: UUID,
        file_type: Optional[FileType] = None,
        language: Optional[str] = None,
        include_deleted: bool = False,
        skip: int = 0,
        limit: int = 100,
    ) -> List[File]:
        """
        List files in a project with optional filtering.

        Args:
            project_id: UUID of the project
            file_type: Optional file type filter
            language: Optional programming language filter
            include_deleted: Whether to include soft-deleted files
            skip: Number of records to skip (for pagination)
            limit: Maximum number of records to return

        Returns:
            List of File objects

        Raises:
            SQLAlchemyError: If database query fails
        """
        try:
            stmt = select(File).where(File.project_id == project_id)

            # Apply filters
            if file_type:
                stmt = stmt.where(File.file_type == file_type.value)
            if language:
                stmt = stmt.where(File.language == language)
            if not include_deleted:
                stmt = stmt.where(File.is_deleted.is_(False))

            # Apply pagination and ordering
            stmt = stmt.order_by(File.path).offset(skip).limit(min(limit, 100))

            result = await self.session.execute(stmt)
            return list(result.scalars().all())
        except SQLAlchemyError as e:
            logger.error(f"Error listing files for project {project_id}: {e}", exc_info=True)
            raise

    async def list_by_directory(
        self,
        project_id: UUID,
        directory: str,
        recursive: bool = False,
    ) -> List[File]:
        """
        List files in a specific directory.

        Args:
            project_id: UUID of the project
            directory: Directory path (e.g., "src/components")
            recursive: Whether to include subdirectories

        Returns:
            List of File objects in the directory

        Raises:
            SQLAlchemyError: If database query fails
        """
        try:
            # Normalize directory path
            if not directory.endswith("/"):
                directory += "/"

            if recursive:
                # Match directory and all subdirectories
                stmt = select(File).where(
                    and_(
                        File.project_id == project_id,
                        File.path.like(f"{directory}%"),
                        File.is_deleted.is_(False),
                    )
                )
            else:
                # Match only direct children of directory
                stmt = select(File).where(
                    and_(
                        File.project_id == project_id,
                        File.path.like(f"{directory}%"),
                        ~File.path.like(f"{directory}%/%"),  # No additional subdirectories
                        File.is_deleted.is_(False),
                    )
                )

            stmt = stmt.order_by(File.path)
            result = await self.session.execute(stmt)
            return list(result.scalars().all())
        except SQLAlchemyError as e:
            logger.error(f"Error listing files in directory {directory}: {e}", exc_info=True)
            raise

    async def search_files(
        self,
        project_id: UUID,
        query: str,
        search_content: bool = False,
    ) -> List[File]:
        """
        Search files by name and optionally content.

        Args:
            project_id: UUID of the project
            query: Search query string
            search_content: Whether to search in file content

        Returns:
            List of matching File objects

        Raises:
            SQLAlchemyError: If database query fails
        """
        try:
            # Build search conditions
            name_condition = File.name.ilike(f"%{query}%")
            path_condition = File.path.ilike(f"%{query}%")

            # Base conditions
            base_conditions = [File.project_id == project_id, File.is_deleted.is_(False)]

            # Search conditions (name or path)
            search_conditions = [name_condition, path_condition]

            # Add content search if requested
            if search_content:
                content_condition = File.content.ilike(f"%{query}%")
                search_conditions.append(content_condition)

            stmt = select(File).where(and_(*base_conditions, or_(*search_conditions)))

            stmt = stmt.order_by(File.path)
            result = await self.session.execute(stmt)
            return list(result.scalars().all())
        except SQLAlchemyError as e:
            logger.error(f"Error searching files with query '{query}': {e}", exc_info=True)
            raise

    async def update(self, file_id: UUID, update_data: Dict[str, Any]) -> Optional[File]:
        """
        Update file fields.

        Args:
            file_id: UUID of file to update
            update_data: Dictionary of fields to update

        Returns:
            Updated File object if found, None otherwise

        Raises:
            SQLAlchemyError: If database operation fails
        """
        try:
            file = await self.get_by_id(file_id)
            if not file:
                logger.warning(f"Cannot update: file {file_id} not found")
                return None

            # Track if content changed for hash recalculation
            content_changed = False
            old_content = file.content

            # Update fields
            for key, value in update_data.items():
                if hasattr(file, key):
                    if key == "content" and value != old_content:
                        content_changed = True
                    setattr(file, key, value)
                else:
                    logger.warning(f"Skipping unknown field: {key}")

            # Recalculate content hash if content changed
            if content_changed and file.content:
                file.content_hash = File.calculate_content_hash(file.content)

            await self.session.commit()
            await self.session.refresh(file)
            logger.info(f"Updated file {file_id}")
            return file
        except SQLAlchemyError as e:
            logger.error(f"Error updating file {file_id}: {e}", exc_info=True)
            await self.session.rollback()
            raise

    async def update_content(
        self,
        file_id: UUID,
        content: str,
        encoding: str = "utf-8",
    ) -> Optional[File]:
        """
        Update file content and related metadata.

        Args:
            file_id: UUID of file to update
            content: New file content
            encoding: Text encoding

        Returns:
            Updated File object if found, None otherwise

        Raises:
            SQLAlchemyError: If database operation fails
        """
        try:
            file = await self.get_by_id(file_id)
            if not file:
                logger.warning(f"Cannot update content: file {file_id} not found")
                return None

            # Update content and metadata
            file.content = content
            file.content_hash = File.calculate_content_hash(content)
            file.size_bytes = len(content.encode(encoding))
            file.encoding = encoding

            await self.session.commit()
            await self.session.refresh(file)
            logger.info(f"Updated content for file {file_id}")
            return file
        except SQLAlchemyError as e:
            logger.error(f"Error updating content for file {file_id}: {e}", exc_info=True)
            await self.session.rollback()
            raise

    async def update_from_git(
        self,
        file_id: UUID,
        commit_sha: str,
        commit_message: str,
        modified_by_user_id: UUID,
        modified_at: datetime,
    ) -> Optional[File]:
        """
        Update file git metadata.

        Args:
            file_id: UUID of file to update
            commit_sha: Git commit hash
            commit_message: Git commit message
            modified_by_user_id: User who made the commit
            modified_at: Git commit timestamp

        Returns:
            Updated File object if found, None otherwise

        Raises:
            SQLAlchemyError: If database operation fails
        """
        try:
            file = await self.get_by_id(file_id)
            if not file:
                logger.warning(f"Cannot update git metadata: file {file_id} not found")
                return None

            # Update git metadata
            file.update_from_git(
                commit_sha=commit_sha,
                commit_message=commit_message,
                author_user_id=modified_by_user_id,
                committed_at=modified_at,
            )

            await self.session.commit()
            await self.session.refresh(file)
            logger.info(f"Updated git metadata for file {file_id}")
            return file
        except SQLAlchemyError as e:
            logger.error(f"Error updating git metadata for file {file_id}: {e}", exc_info=True)
            await self.session.rollback()
            raise

    async def delete(self, file_id: UUID, soft: bool = True) -> bool:
        """
        Delete a file (soft or hard delete).

        Args:
            file_id: UUID of file to delete
            soft: If True, perform soft delete; if False, hard delete

        Returns:
            True if file was deleted, False if not found

        Raises:
            SQLAlchemyError: If database operation fails
        """
        try:
            file = await self.get_by_id(file_id)
            if not file:
                logger.warning(f"Cannot delete: file {file_id} not found")
                return False

            if soft:
                # Soft delete
                file.is_deleted = True
                file.deleted_at = datetime.now()
                logger.info(f"Soft deleted file {file_id}")
            else:
                # Hard delete
                await self.session.delete(file)
                logger.info(f"Hard deleted file {file_id}")

            await self.session.commit()
            return True
        except SQLAlchemyError as e:
            logger.error(f"Error deleting file {file_id}: {e}", exc_info=True)
            await self.session.rollback()
            raise

    async def restore(self, file_id: UUID) -> Optional[File]:
        """
        Restore a soft-deleted file.

        Args:
            file_id: UUID of file to restore

        Returns:
            Restored File object if found, None otherwise

        Raises:
            SQLAlchemyError: If database operation fails
        """
        try:
            file = await self.get_by_id(file_id)
            if not file:
                logger.warning(f"Cannot restore: file {file_id} not found")
                return None

            if not file.is_deleted:
                logger.warning(f"File {file_id} is not deleted")
                return file

            # Restore file
            file.is_deleted = False
            file.deleted_at = None

            await self.session.commit()
            await self.session.refresh(file)
            logger.info(f"Restored file {file_id}")
            return file
        except SQLAlchemyError as e:
            logger.error(f"Error restoring file {file_id}: {e}", exc_info=True)
            await self.session.rollback()
            raise

    async def count_by_project(
        self,
        project_id: UUID,
        file_type: Optional[FileType] = None,
        include_deleted: bool = False,
    ) -> int:
        """
        Count files in a project.

        Args:
            project_id: UUID of the project
            file_type: Optional file type filter
            include_deleted: Whether to include soft-deleted files

        Returns:
            Number of files matching criteria

        Raises:
            SQLAlchemyError: If database query fails
        """
        try:
            stmt = select(func.count(File.id)).where(File.project_id == project_id)

            if file_type:
                stmt = stmt.where(File.file_type == file_type.value)
            if not include_deleted:
                stmt = stmt.where(File.is_deleted.is_(False))

            result = await self.session.execute(stmt)
            return result.scalar() or 0
        except SQLAlchemyError as e:
            logger.error(f"Error counting files for project {project_id}: {e}", exc_info=True)
            raise

    async def get_file_with_commits(
        self,
        file_id: UUID,
        max_commits: int = 10,
    ) -> Optional[Tuple[File, List["GitCommit"]]]:
        """
        Get file with its commit history.

        Args:
            file_id: UUID of the file
            max_commits: Maximum number of commits to return

        Returns:
            Tuple of (File, List[GitCommit]) if found, None otherwise

        Raises:
            SQLAlchemyError: If database query fails
        """
        try:
            # Import here to avoid circular imports
            from ardha.models.git_commit import GitCommit

            # Get file with commits
            stmt = (
                select(File)
                .where(File.id == file_id)
                .options(selectinload(File.commits).joinedload(GitCommit.ardha_user))
            )
            result = await self.session.execute(stmt)
            file = result.scalar_one_or_none()

            if not file:
                return None

            # Get commits ordered by date (most recent first)
            commits = sorted(file.commits, key=lambda c: c.committed_at, reverse=True)
            commits = commits[:max_commits]

            return (file, commits)
        except SQLAlchemyError as e:
            logger.error(f"Error getting file {file_id} with commits: {e}", exc_info=True)
            raise

    async def bulk_create(self, files: List[File]) -> List[File]:
        """
        Create multiple files in one transaction.

        Args:
            files: List of File objects to create

        Returns:
            List of created File objects

        Raises:
            SQLAlchemyError: If database operation fails
        """
        try:
            self.session.add_all(files)
            await self.session.commit()

            # Refresh all files to get their IDs
            for file in files:
                await self.session.refresh(file)

            logger.info(f"Bulk created {len(files)} files")
            return files
        except IntegrityError as e:
            logger.warning(f"Integrity error in bulk create: {e}")
            await self.session.rollback()
            raise
        except SQLAlchemyError as e:
            logger.error(f"Error in bulk creating files: {e}", exc_info=True)
            await self.session.rollback()
            raise

    async def get_files_modified_since(
        self,
        project_id: UUID,
        since: datetime,
    ) -> List[File]:
        """
        Get files modified after a specific date.

        Args:
            project_id: UUID of the project
            since: DateTime threshold (exclusive)

        Returns:
            List of File objects modified after the date

        Raises:
            SQLAlchemyError: If database query fails
        """
        try:
            stmt = (
                select(File)
                .where(
                    and_(
                        File.project_id == project_id,
                        File.last_modified_at > since,
                        File.is_deleted.is_(False),
                    )
                )
                .order_by(File.last_modified_at.desc())
            )

            result = await self.session.execute(stmt)
            return list(result.scalars().all())
        except SQLAlchemyError as e:
            logger.error(f"Error getting files modified since {since}: {e}", exc_info=True)
            raise
