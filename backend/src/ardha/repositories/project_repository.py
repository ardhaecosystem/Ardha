"""
Project repository for data access abstraction.

This module provides the repository pattern implementation for Project and
ProjectMember models, handling all database operations related to projects
and team membership.
"""

import logging
import secrets
from uuid import UUID

from slugify import slugify
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ardha.models.project import Project
from ardha.models.project_member import ProjectMember

logger = logging.getLogger(__name__)


class ProjectRepository:
    """
    Repository for Project and ProjectMember model database operations.

    Provides data access methods for project-related operations including
    CRUD operations, member management, and pagination. Follows the repository
    pattern to abstract database implementation details from business logic.

    Attributes:
        db: SQLAlchemy async session for database operations
    """

    def __init__(self, db: AsyncSession) -> None:
        """
        Initialize the ProjectRepository with a database session.

        Args:
            db: SQLAlchemy async session for database operations
        """
        self.db = db

    async def get_by_id(self, project_id: UUID) -> Project | None:
        """
        Fetch a project by its UUID.

        Args:
            project_id: UUID of the project to fetch

        Returns:
            Project object if found, None otherwise

        Raises:
            SQLAlchemyError: If database query fails
        """
        try:
            stmt = select(Project).where(Project.id == project_id)
            result = await self.db.execute(stmt)
            return result.scalar_one_or_none()
        except SQLAlchemyError as e:
            logger.error(f"Error fetching project by id {project_id}: {e}", exc_info=True)
            raise

    async def get_by_slug(self, slug: str) -> Project | None:
        """
        Fetch a project by its URL slug.

        Used for URL routing and slug uniqueness validation.

        Args:
            slug: URL-safe project identifier

        Returns:
            Project object if found, None otherwise

        Raises:
            SQLAlchemyError: If database query fails
        """
        try:
            stmt = select(Project).where(Project.slug == slug)
            result = await self.db.execute(stmt)
            return result.scalar_one_or_none()
        except SQLAlchemyError as e:
            logger.error(f"Error fetching project by slug {slug}: {e}", exc_info=True)
            raise

    async def get_by_owner(
        self,
        owner_id: UUID,
        skip: int = 0,
        limit: int = 100,
        include_archived: bool = False,
    ) -> list[Project]:
        """
        Fetch projects owned by a specific user.

        Args:
            owner_id: UUID of the project owner
            skip: Number of records to skip (for pagination)
            limit: Maximum number of records to return (capped at 100)
            include_archived: Whether to include archived projects

        Returns:
            List of Project objects

        Raises:
            SQLAlchemyError: If database query fails
        """
        try:
            stmt = select(Project).where(Project.owner_id == owner_id)

            # Filter out archived projects by default
            if not include_archived:
                stmt = stmt.where(Project.is_archived == False)

            # Apply pagination
            stmt = stmt.offset(skip).limit(min(limit, 100))

            result = await self.db.execute(stmt)
            return list(result.scalars().all())
        except SQLAlchemyError as e:
            logger.error(f"Error fetching projects by owner {owner_id}: {e}", exc_info=True)
            raise

    async def get_user_projects(
        self,
        user_id: UUID,
        skip: int = 0,
        limit: int = 100,
        include_archived: bool = False,
    ) -> list[Project]:
        """
        Fetch all projects where user is a member (including owned projects).

        Args:
            user_id: UUID of the user
            skip: Number of records to skip (for pagination)
            limit: Maximum number of records to return (capped at 100)
            include_archived: Whether to include archived projects

        Returns:
            List of Project objects

        Raises:
            SQLAlchemyError: If database query fails
        """
        try:
            # Join with project_members to get all projects user is member of
            stmt = (
                select(Project)
                .join(ProjectMember, Project.id == ProjectMember.project_id)
                .where(ProjectMember.user_id == user_id)
            )

            # Filter out archived projects by default
            if not include_archived:
                stmt = stmt.where(Project.is_archived == False)

            # Apply pagination
            stmt = stmt.offset(skip).limit(min(limit, 100))

            result = await self.db.execute(stmt)
            return list(result.scalars().all())
        except SQLAlchemyError as e:
            logger.error(f"Error fetching projects for user {user_id}: {e}", exc_info=True)
            raise

    async def _generate_unique_slug(self, name: str) -> str:
        """
        Generate a unique URL slug from project name.

        Creates a URL-safe slug from the project name. If a duplicate exists,
        appends a random 6-character suffix.

        Args:
            name: Project name to slugify

        Returns:
            Unique URL-safe slug

        Raises:
            SQLAlchemyError: If database query fails
        """
        base_slug = slugify(name, max_length=200)
        slug = base_slug

        # Check for duplicates and append random suffix if needed
        attempts = 0
        max_attempts = 10

        while attempts < max_attempts:
            existing = await self.get_by_slug(slug)
            if not existing:
                return slug

            # Generate random 6-character suffix
            suffix = secrets.token_hex(3)
            slug = f"{base_slug}-{suffix}"
            attempts += 1

        # Fallback: use full random suffix if still duplicate
        raise ValueError(
            f"Failed to generate unique slug for '{name}' after {max_attempts} attempts"
        )

    async def create(self, project_data: dict, owner_id: UUID) -> Project:
        """
        Create a new project and add owner as member.

        Automatically generates a unique slug from the project name and creates
        a ProjectMember entry with 'owner' role for the creating user.

        Args:
            project_data: Dictionary containing project fields (name, description, etc.)
            owner_id: UUID of the user creating the project

        Returns:
            Created Project object with generated ID and timestamps

        Raises:
            ValueError: If slug generation fails
            IntegrityError: If unique constraint violated
            SQLAlchemyError: If database operation fails
        """
        try:
            # Generate unique slug from name
            name = project_data.get("name", "")
            if not name:
                raise ValueError("Project name is required")

            slug = await self._generate_unique_slug(name)

            # Create project with generated slug
            project_data["slug"] = slug
            project_data["owner_id"] = owner_id

            project = Project(**project_data)
            self.db.add(project)
            await self.db.flush()
            await self.db.refresh(project)

            # Add owner as project member with 'owner' role
            owner_member = ProjectMember(
                project_id=project.id,
                user_id=owner_id,
                role="owner",
            )
            self.db.add(owner_member)
            await self.db.flush()

            logger.info(f"Created project {project.id} with owner {owner_id}")
            return project
        except IntegrityError as e:
            logger.warning(f"Integrity error creating project: {e}")
            raise
        except SQLAlchemyError as e:
            logger.error(f"Error creating project: {e}", exc_info=True)
            raise

    async def update(self, project_id: UUID, **kwargs) -> Project | None:
        """
        Update project fields.

        Updates specified fields for a project identified by UUID.
        Only updates fields provided in kwargs. Does not update slug automatically.

        Args:
            project_id: UUID of project to update
            **kwargs: Fields to update (e.g., name="New Name", description="...")

        Returns:
            Updated Project object if found, None if project doesn't exist

        Raises:
            IntegrityError: If update violates unique constraints
            SQLAlchemyError: If database operation fails
        """
        try:
            project = await self.get_by_id(project_id)
            if not project:
                logger.warning(f"Cannot update: project {project_id} not found")
                return None

            # Update only provided fields
            for key, value in kwargs.items():
                if hasattr(project, key):
                    setattr(project, key, value)
                else:
                    logger.warning(f"Skipping unknown field: {key}")

            await self.db.flush()
            await self.db.refresh(project)
            logger.info(f"Updated project {project_id}")
            return project
        except IntegrityError as e:
            logger.warning(f"Integrity error updating project {project_id}: {e}")
            raise
        except SQLAlchemyError as e:
            logger.error(f"Error updating project {project_id}: {e}", exc_info=True)
            raise

    async def archive(self, project_id: UUID) -> bool:
        """
        Archive a project (soft delete).

        Sets is_archived to True and records archived_at timestamp.
        Archived projects are excluded from default queries but can be restored.

        Args:
            project_id: UUID of project to archive

        Returns:
            True if project was archived, False if project not found

        Raises:
            SQLAlchemyError: If database operation fails
        """
        try:
            from datetime import datetime, timezone

            project = await self.get_by_id(project_id)
            if not project:
                logger.warning(f"Cannot archive: project {project_id} not found")
                return False

            project.is_archived = True
            project.archived_at = datetime.now(timezone.utc)
            await self.db.flush()
            logger.info(f"Archived project {project_id}")
            return True
        except SQLAlchemyError as e:
            logger.error(f"Error archiving project {project_id}: {e}", exc_info=True)
            raise

    async def delete(self, project_id: UUID) -> bool:
        """
        Hard delete a project and all associated data.

        Permanently removes project and all ProjectMember records (cascade delete).
        Use archive() for soft delete to preserve data.

        Args:
            project_id: UUID of project to delete

        Returns:
            True if project was deleted, False if project not found

        Raises:
            SQLAlchemyError: If database operation fails
        """
        try:
            project = await self.get_by_id(project_id)
            if not project:
                logger.warning(f"Cannot delete: project {project_id} not found")
                return False

            await self.db.delete(project)
            await self.db.flush()
            logger.info(f"Hard deleted project {project_id}")
            return True
        except SQLAlchemyError as e:
            logger.error(f"Error deleting project {project_id}: {e}", exc_info=True)
            raise

    async def add_member(
        self,
        project_id: UUID,
        user_id: UUID,
        role: str = "member",
    ) -> ProjectMember:
        """
        Add a team member to a project.

        Creates a ProjectMember entry associating a user with a project.
        Eagerly loads user relationship to avoid lazy loading errors.

        Args:
            project_id: UUID of the project
            user_id: UUID of the user to add
            role: User's role ('owner', 'admin', 'member', 'viewer')

        Returns:
            Created ProjectMember object with user data loaded

        Raises:
            IntegrityError: If user is already a member
            SQLAlchemyError: If database operation fails
        """
        try:
            member = ProjectMember(
                project_id=project_id,
                user_id=user_id,
                role=role,
            )
            self.db.add(member)
            await self.db.flush()

            # Reload with user relationship eagerly loaded
            stmt = (
                select(ProjectMember)
                .where(ProjectMember.id == member.id)
                .options(selectinload(ProjectMember.user))
            )
            result = await self.db.execute(stmt)
            member = result.scalar_one()

            logger.info(f"Added user {user_id} to project {project_id} with role {role}")
            return member
        except IntegrityError as e:
            logger.warning(f"User {user_id} is already a member of project {project_id}")
            raise
        except SQLAlchemyError as e:
            logger.error(f"Error adding member to project {project_id}: {e}", exc_info=True)
            raise

    async def remove_member(self, project_id: UUID, user_id: UUID) -> bool:
        """
        Remove a team member from a project.

        Deletes the ProjectMember entry. Cannot remove the project owner.

        Args:
            project_id: UUID of the project
            user_id: UUID of the user to remove

        Returns:
            True if member was removed, False if member not found

        Raises:
            ValueError: If attempting to remove project owner
            SQLAlchemyError: If database operation fails
        """
        try:
            stmt = select(ProjectMember).where(
                ProjectMember.project_id == project_id,
                ProjectMember.user_id == user_id,
            )
            result = await self.db.execute(stmt)
            member = result.scalar_one_or_none()

            if not member:
                logger.warning(f"Member {user_id} not found in project {project_id}")
                return False

            # Prevent removing the owner
            if member.role == "owner":
                raise ValueError("Cannot remove project owner. Transfer ownership first.")

            await self.db.delete(member)
            await self.db.flush()
            logger.info(f"Removed user {user_id} from project {project_id}")
            return True
        except SQLAlchemyError as e:
            logger.error(f"Error removing member from project {project_id}: {e}", exc_info=True)
            raise

    async def update_member_role(
        self,
        project_id: UUID,
        user_id: UUID,
        role: str,
    ) -> ProjectMember | None:
        """
        Update a team member's role in a project.

        Eagerly loads user relationship to avoid lazy loading errors.

        Args:
            project_id: UUID of the project
            user_id: UUID of the user
            role: New role ('owner', 'admin', 'member', 'viewer')

        Returns:
            Updated ProjectMember object with user data, or None if member not found

        Raises:
            SQLAlchemyError: If database operation fails
        """
        try:
            stmt = (
                select(ProjectMember)
                .where(
                    ProjectMember.project_id == project_id,
                    ProjectMember.user_id == user_id,
                )
                .options(selectinload(ProjectMember.user))
            )
            result = await self.db.execute(stmt)
            member = result.scalar_one_or_none()

            if not member:
                logger.warning(f"Member {user_id} not found in project {project_id}")
                return None

            member.role = role
            await self.db.flush()

            # Reload to ensure user relationship is still loaded
            stmt = (
                select(ProjectMember)
                .where(ProjectMember.id == member.id)
                .options(selectinload(ProjectMember.user))
            )
            result = await self.db.execute(stmt)
            member = result.scalar_one()

            logger.info(f"Updated role for user {user_id} in project {project_id} to {role}")
            return member
        except SQLAlchemyError as e:
            logger.error(f"Error updating member role in project {project_id}: {e}", exc_info=True)
            raise

    async def get_project_members(self, project_id: UUID) -> list[ProjectMember]:
        """
        Fetch all members of a project.

        Eagerly loads associated user data for efficient access.

        Args:
            project_id: UUID of the project

        Returns:
            List of ProjectMember objects with user relationships loaded

        Raises:
            SQLAlchemyError: If database query fails
        """
        try:
            stmt = (
                select(ProjectMember)
                .where(ProjectMember.project_id == project_id)
                .options(selectinload(ProjectMember.user))
            )
            result = await self.db.execute(stmt)
            return list(result.scalars().all())
        except SQLAlchemyError as e:
            logger.error(f"Error fetching members for project {project_id}: {e}", exc_info=True)
            raise

    async def get_member_role(self, project_id: UUID, user_id: UUID) -> str | None:
        """
        Get a user's role in a project.

        Args:
            project_id: UUID of the project
            user_id: UUID of the user

        Returns:
            Role string if user is a member, None otherwise

        Raises:
            SQLAlchemyError: If database query fails
        """
        try:
            stmt = select(ProjectMember.role).where(
                ProjectMember.project_id == project_id,
                ProjectMember.user_id == user_id,
            )
            result = await self.db.execute(stmt)
            return result.scalar_one_or_none()
        except SQLAlchemyError as e:
            logger.error(f"Error fetching member role for project {project_id}: {e}", exc_info=True)
            raise
