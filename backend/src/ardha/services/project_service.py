"""
Project service for business logic.

This module provides business logic for project management, including CRUD operations,
member management, and permission checks.
"""

import logging
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from ardha.models.project import Project
from ardha.models.project_member import ProjectMember
from ardha.repositories.project_repository import ProjectRepository
from ardha.schemas.requests.project import (
    ProjectCreateRequest,
    ProjectUpdateRequest,
)

logger = logging.getLogger(__name__)

# Role hierarchy for permission checks
ROLE_HIERARCHY = {
    "owner": 4,
    "admin": 3,
    "member": 2,
    "viewer": 1,
}


class ProjectNotFoundError(Exception):
    """Raised when project is not found."""
    pass


class InsufficientPermissionsError(Exception):
    """Raised when user lacks required permissions."""
    pass


class ProjectSlugExistsError(Exception):
    """Raised when slug already exists (should be rare with auto-generation)."""
    pass


class ProjectService:
    """
    Service for project management business logic.
    
    Handles project CRUD operations, member management, and permission checks.
    Enforces role-based access control with hierarchical permissions.
    
    Attributes:
        db: SQLAlchemy async session
        repository: ProjectRepository for data access
    """
    
    def __init__(self, db: AsyncSession) -> None:
        """
        Initialize ProjectService.
        
        Args:
            db: SQLAlchemy async session for database operations
        """
        self.db = db
        self.repository = ProjectRepository(db)
    
    async def create_project(
        self,
        project_data: ProjectCreateRequest,
        owner_id: UUID,
    ) -> Project:
        """
        Create a new project.
        
        Creates project with auto-generated unique slug and automatically
        adds the owner as a project member with 'owner' role.
        
        Args:
            project_data: Project creation request data
            owner_id: UUID of the user creating the project
            
        Returns:
            Created Project object
            
        Raises:
            ValueError: If slug generation fails
            SQLAlchemyError: If database operation fails
        """
        logger.info(f"Creating project '{project_data.name}' for owner {owner_id}")
        
        # Convert Pydantic model to dict, excluding None values
        project_dict = project_data.model_dump(exclude_none=True)
        
        # Create project (repository handles slug generation and owner membership)
        project = await self.repository.create(project_dict, owner_id)
        await self.db.flush()
        await self.db.refresh(project)
        
        logger.info(f"Created project {project.id} with slug '{project.slug}'")
        return project
    
    async def get_project(self, project_id: UUID) -> Project:
        """
        Get project by ID.
        
        Args:
            project_id: UUID of the project
            
        Returns:
            Project object
            
        Raises:
            ProjectNotFoundError: If project not found
        """
        project = await self.repository.get_by_id(project_id)
        if not project:
            logger.warning(f"Project {project_id} not found")
            raise ProjectNotFoundError(f"Project {project_id} not found")
        return project
    
    async def get_project_by_slug(self, slug: str) -> Project:
        """
        Get project by slug.
        
        Args:
            slug: URL-safe project identifier
            
        Returns:
            Project object
            
        Raises:
            ProjectNotFoundError: If project not found
        """
        project = await self.repository.get_by_slug(slug)
        if not project:
            logger.warning(f"Project with slug '{slug}' not found")
            raise ProjectNotFoundError(f"Project with slug '{slug}' not found")
        return project
    
    async def get_user_projects(
        self,
        user_id: UUID,
        skip: int = 0,
        limit: int = 100,
        include_archived: bool = False,
    ) -> tuple[list[Project], int]:
        """
        Get all projects where user is a member.
        
        Args:
            user_id: UUID of the user
            skip: Number of records to skip (pagination)
            limit: Maximum number of records to return
            include_archived: Whether to include archived projects
            
        Returns:
            Tuple of (list of projects, total count)
        """
        projects = await self.repository.get_user_projects(
            user_id,
            skip=skip,
            limit=limit,
            include_archived=include_archived,
        )
        
        # Get total count (for pagination)
        total_projects = await self.repository.get_user_projects(
            user_id,
            skip=0,
            limit=10000,  # Get all for count
            include_archived=include_archived,
        )
        
        return projects, len(total_projects)
    
    async def update_project(
        self,
        project_id: UUID,
        user_id: UUID,
        update_data: ProjectUpdateRequest,
    ) -> Project:
        """
        Update project.
        
        Requires owner or admin role.
        
        Args:
            project_id: UUID of project to update
            user_id: UUID of user making the request
            update_data: Fields to update
            
        Returns:
            Updated Project object
            
        Raises:
            ProjectNotFoundError: If project not found
            InsufficientPermissionsError: If user lacks permissions
        """
        # Check permissions (owner or admin)
        if not await self.check_permission(project_id, user_id, "admin"):
            logger.warning(
                f"User {user_id} lacks permission to update project {project_id}"
            )
            raise InsufficientPermissionsError(
                "Only project owner or admin can update project"
            )
        
        # Convert Pydantic model to dict, excluding None values
        update_dict = update_data.model_dump(exclude_none=True)
        
        if not update_dict:
            # No fields to update
            return await self.get_project(project_id)
        
        logger.info(f"Updating project {project_id} with fields: {list(update_dict.keys())}")
        
        project = await self.repository.update(project_id, **update_dict)
        if not project:
            raise ProjectNotFoundError(f"Project {project_id} not found")
        
        await self.db.flush()
        await self.db.refresh(project)
        
        logger.info(f"Updated project {project_id}")
        return project
    
    async def archive_project(self, project_id: UUID, user_id: UUID) -> bool:
        """
        Archive a project (soft delete).
        
        Requires owner or admin role.
        
        Args:
            project_id: UUID of project to archive
            user_id: UUID of user making the request
            
        Returns:
            True if archived successfully
            
        Raises:
            ProjectNotFoundError: If project not found
            InsufficientPermissionsError: If user lacks permissions
        """
        # Check permissions (owner or admin)
        if not await self.check_permission(project_id, user_id, "admin"):
            logger.warning(
                f"User {user_id} lacks permission to archive project {project_id}"
            )
            raise InsufficientPermissionsError(
                "Only project owner or admin can archive project"
            )
        
        logger.info(f"Archiving project {project_id}")
        
        success = await self.repository.archive(project_id)
        if not success:
            raise ProjectNotFoundError(f"Project {project_id} not found")
        
        await self.db.flush()
        logger.info(f"Archived project {project_id}")
        return True
    
    async def delete_project(self, project_id: UUID, user_id: UUID) -> bool:
        """
        Delete a project permanently.
        
        Requires owner role only.
        
        Args:
            project_id: UUID of project to delete
            user_id: UUID of user making the request
            
        Returns:
            True if deleted successfully
            
        Raises:
            ProjectNotFoundError: If project not found
            InsufficientPermissionsError: If user is not owner
        """
        # Check permissions (owner only)
        if not await self.check_permission(project_id, user_id, "owner"):
            logger.warning(
                f"User {user_id} lacks permission to delete project {project_id}"
            )
            raise InsufficientPermissionsError(
                "Only project owner can delete project"
            )
        
        logger.info(f"Deleting project {project_id}")
        
        success = await self.repository.delete(project_id)
        if not success:
            raise ProjectNotFoundError(f"Project {project_id} not found")
        
        await self.db.flush()
        logger.info(f"Deleted project {project_id}")
        return True
    
    async def add_member(
        self,
        project_id: UUID,
        requester_id: UUID,
        user_id: UUID,
        role: str,
    ) -> ProjectMember:
        """
        Add a member to the project.
        
        Requires owner or admin role.
        
        Args:
            project_id: UUID of the project
            requester_id: UUID of user making the request
            user_id: UUID of user to add
            role: Role to assign (admin/member/viewer)
            
        Returns:
            Created ProjectMember object
            
        Raises:
            ProjectNotFoundError: If project not found
            InsufficientPermissionsError: If requester lacks permissions
            IntegrityError: If user is already a member
        """
        # Check permissions (owner or admin)
        if not await self.check_permission(project_id, requester_id, "admin"):
            logger.warning(
                f"User {requester_id} lacks permission to add members to project {project_id}"
            )
            raise InsufficientPermissionsError(
                "Only project owner or admin can add members"
            )
        
        logger.info(f"Adding user {user_id} to project {project_id} with role {role}")
        
        member = await self.repository.add_member(project_id, user_id, role)
        await self.db.flush()
        await self.db.refresh(member)
        
        logger.info(f"Added user {user_id} to project {project_id}")
        return member
    
    async def remove_member(
        self,
        project_id: UUID,
        requester_id: UUID,
        user_id: UUID,
    ) -> bool:
        """
        Remove a member from the project.
        
        Requires owner or admin role. Cannot remove the owner.
        
        Args:
            project_id: UUID of the project
            requester_id: UUID of user making the request
            user_id: UUID of user to remove
            
        Returns:
            True if removed successfully
            
        Raises:
            ProjectNotFoundError: If project or member not found
            InsufficientPermissionsError: If requester lacks permissions
            ValueError: If attempting to remove owner
        """
        # Check permissions (owner or admin)
        if not await self.check_permission(project_id, requester_id, "admin"):
            logger.warning(
                f"User {requester_id} lacks permission to remove members from project {project_id}"
            )
            raise InsufficientPermissionsError(
                "Only project owner or admin can remove members"
            )
        
        logger.info(f"Removing user {user_id} from project {project_id}")
        
        success = await self.repository.remove_member(project_id, user_id)
        if not success:
            logger.warning(f"Member {user_id} not found in project {project_id}")
            raise ProjectNotFoundError(
                f"User {user_id} is not a member of project {project_id}"
            )
        
        await self.db.flush()
        logger.info(f"Removed user {user_id} from project {project_id}")
        return True
    
    async def update_member_role(
        self,
        project_id: UUID,
        requester_id: UUID,
        user_id: UUID,
        role: str,
    ) -> ProjectMember:
        """
        Update a member's role.
        
        Requires owner or admin role.
        
        Args:
            project_id: UUID of the project
            requester_id: UUID of user making the request
            user_id: UUID of user to update
            role: New role (admin/member/viewer)
            
        Returns:
            Updated ProjectMember object
            
        Raises:
            ProjectNotFoundError: If project or member not found
            InsufficientPermissionsError: If requester lacks permissions
        """
        # Check permissions (owner or admin)
        if not await self.check_permission(project_id, requester_id, "admin"):
            logger.warning(
                f"User {requester_id} lacks permission to update roles in project {project_id}"
            )
            raise InsufficientPermissionsError(
                "Only project owner or admin can update member roles"
            )
        
        logger.info(f"Updating role for user {user_id} in project {project_id} to {role}")
        
        member = await self.repository.update_member_role(project_id, user_id, role)
        if not member:
            logger.warning(f"Member {user_id} not found in project {project_id}")
            raise ProjectNotFoundError(
                f"User {user_id} is not a member of project {project_id}"
            )
        
        await self.db.flush()
        await self.db.refresh(member)
        
        logger.info(f"Updated role for user {user_id} in project {project_id}")
        return member
    
    async def get_project_members(self, project_id: UUID) -> list[ProjectMember]:
        """
        Get all members of a project.
        
        Args:
            project_id: UUID of the project
            
        Returns:
            List of ProjectMember objects with user data loaded
        """
        return await self.repository.get_project_members(project_id)
    
    async def check_permission(
        self,
        project_id: UUID,
        user_id: UUID,
        required_role: str,
    ) -> bool:
        """
        Check if user has required role or higher.
        
        Uses role hierarchy: owner > admin > member > viewer
        
        Args:
            project_id: UUID of the project
            user_id: UUID of the user
            required_role: Minimum required role
            
        Returns:
            True if user has required permission, False otherwise
        """
        user_role = await self.repository.get_member_role(project_id, user_id)
        if not user_role:
            return False
        
        user_level = ROLE_HIERARCHY.get(user_role, 0)
        required_level = ROLE_HIERARCHY.get(required_role, 0)
        
        return user_level >= required_level
    
    async def get_member_count(self, project_id: UUID) -> int:
        """
        Get the number of members in a project.
        
        Args:
            project_id: UUID of the project
            
        Returns:
            Number of members
        """
        members = await self.repository.get_project_members(project_id)
        return len(members)