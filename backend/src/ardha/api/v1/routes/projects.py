"""
Project API routes.

This module defines REST API endpoints for project management,
including CRUD operations and team member management.
"""

import logging
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from ardha.core.database import get_db
from ardha.core.security import get_current_active_user
from ardha.models.user import User
from ardha.schemas.requests.project import (
    ProjectCreateRequest,
    ProjectMemberAddRequest,
    ProjectMemberUpdateRequest,
    ProjectUpdateRequest,
)
from ardha.schemas.responses.project import (
    ProjectListResponse,
    ProjectMemberResponse,
    ProjectResponse,
)
from ardha.services.project_service import (
    InsufficientPermissionsError,
    ProjectNotFoundError,
    ProjectService,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/projects", tags=["Projects"])


@router.post(
    "/",
    response_model=ProjectResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new project",
    description="Create a new project. The authenticated user becomes the project owner.",
)
async def create_project(
    project_data: ProjectCreateRequest,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> ProjectResponse:
    """
    Create a new project.

    - **name**: Project name (required, 1-255 characters)
    - **description**: Optional project description
    - **visibility**: Access level (private/team/public, default: private)
    - **tech_stack**: List of technology tags
    - **git_repo_url**: Optional Git repository URL
    - **git_branch**: Git branch name (default: main)
    - **openspec_enabled**: Enable OpenSpec (default: true)
    - **openspec_path**: OpenSpec directory path (default: openspec/)

    Returns the created project with auto-generated slug.
    The creator is automatically added as project owner.
    """
    try:
        service = ProjectService(db)
        project = await service.create_project(project_data, current_user.id)

        # Get member count
        member_count = await service.get_member_count(project.id)

        # Convert to response model
        response = ProjectResponse.model_validate(project)
        response.member_count = member_count

        return response
    except ValueError as e:
        logger.error(f"Validation error creating project: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except Exception as e:
        logger.error(f"Error creating project: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create project",
        )


@router.get(
    "/",
    response_model=ProjectListResponse,
    summary="List user's projects",
    description="Get all projects where the authenticated user is a member (paginated).",
)
async def list_user_projects(
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(100, ge=1, le=100, description="Maximum records to return"),
    include_archived: bool = Query(False, description="Include archived projects"),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> ProjectListResponse:
    """
    List all projects where user is a member.

    Query parameters:
    - **skip**: Number of records to skip (pagination, default: 0)
    - **limit**: Maximum number of records (1-100, default: 100)
    - **include_archived**: Include archived projects (default: false)

    Returns paginated list of projects with member counts.
    """
    try:
        service = ProjectService(db)
        projects, total = await service.get_user_projects(
            current_user.id,
            skip=skip,
            limit=limit,
            include_archived=include_archived,
        )

        # Add member counts to each project
        project_responses = []
        for project in projects:
            response = ProjectResponse.model_validate(project)
            response.member_count = await service.get_member_count(project.id)
            project_responses.append(response)

        return ProjectListResponse(
            projects=project_responses,
            total=total,
            skip=skip,
            limit=limit,
        )
    except Exception as e:
        logger.error(f"Error listing projects: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to list projects",
        )


@router.get(
    "/{project_id}",
    response_model=ProjectResponse,
    summary="Get project details",
    description="Get detailed information about a specific project. User must be a project member.",
)
async def get_project(
    project_id: UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> ProjectResponse:
    """
    Get project by ID.

    User must be a member of the project to view it.

    Returns full project details including member count.
    """
    try:
        service = ProjectService(db)

        # Check if user is a member
        if not await service.check_permission(project_id, current_user.id, "viewer"):
            logger.warning(
                f"User {current_user.id} attempted to access project {project_id} without permission"
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You are not a member of this project",
            )

        project = await service.get_project(project_id)
        member_count = await service.get_member_count(project_id)

        response = ProjectResponse.model_validate(project)
        response.member_count = member_count

        return response
    except ProjectNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project {project_id} not found",
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting project {project_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get project",
        )


@router.get(
    "/slug/{slug}",
    response_model=ProjectResponse,
    summary="Get project by slug",
    description="Get project by its URL slug. User must be a project member.",
)
async def get_project_by_slug(
    slug: str,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> ProjectResponse:
    """
    Get project by slug.

    User must be a member of the project to view it.

    Returns full project details including member count.
    """
    try:
        service = ProjectService(db)
        project = await service.get_project_by_slug(slug)

        # Check if user is a member
        if not await service.check_permission(project.id, current_user.id, "viewer"):
            logger.warning(
                f"User {current_user.id} attempted to access project '{slug}' without permission"
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You are not a member of this project",
            )

        member_count = await service.get_member_count(project.id)

        response = ProjectResponse.model_validate(project)
        response.member_count = member_count

        return response
    except ProjectNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project with slug '{slug}' not found",
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting project by slug '{slug}': {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get project",
        )


@router.patch(
    "/{project_id}",
    response_model=ProjectResponse,
    summary="Update project",
    description="Update project details. Requires owner or admin role.",
)
async def update_project(
    project_id: UUID,
    update_data: ProjectUpdateRequest,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> ProjectResponse:
    """
    Update project.

    Requires owner or admin role.
    Only provided fields will be updated.

    Returns updated project with member count.
    """
    try:
        service = ProjectService(db)
        project = await service.update_project(project_id, current_user.id, update_data)

        member_count = await service.get_member_count(project_id)

        response = ProjectResponse.model_validate(project)
        response.member_count = member_count

        return response
    except ProjectNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project {project_id} not found",
        )
    except InsufficientPermissionsError as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e),
        )
    except Exception as e:
        logger.error(f"Error updating project {project_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update project",
        )


@router.post(
    "/{project_id}/archive",
    summary="Archive project",
    description="Archive a project (soft delete). Requires owner or admin role.",
)
async def archive_project(
    project_id: UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """
    Archive project.

    Requires owner or admin role.
    Archived projects are hidden from default queries but can be restored.

    Returns success message.
    """
    try:
        service = ProjectService(db)
        await service.archive_project(project_id, current_user.id)

        return {"message": "Project archived successfully"}
    except ProjectNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project {project_id} not found",
        )
    except InsufficientPermissionsError as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e),
        )
    except Exception as e:
        logger.error(f"Error archiving project {project_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to archive project",
        )


@router.delete(
    "/{project_id}",
    summary="Delete project",
    description="Permanently delete a project. Requires owner role. This action cannot be undone.",
)
async def delete_project(
    project_id: UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """
    Delete project permanently.

    Requires owner role only.
    This action cannot be undone. All project data and members will be removed.

    Returns success message.
    """
    try:
        service = ProjectService(db)
        await service.delete_project(project_id, current_user.id)

        return {"message": "Project deleted successfully"}
    except ProjectNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project {project_id} not found",
        )
    except InsufficientPermissionsError as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e),
        )
    except Exception as e:
        logger.error(f"Error deleting project {project_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete project",
        )


@router.get(
    "/{project_id}/members",
    response_model=list[ProjectMemberResponse],
    summary="List project members",
    description="Get all members of a project. User must be a project member.",
)
async def get_project_members(
    project_id: UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> list[ProjectMemberResponse]:
    """
    List all project members.

    User must be a member to view the member list.

    Returns list of members with user information.
    """
    try:
        service = ProjectService(db)

        # Check if user is a member
        if not await service.check_permission(project_id, current_user.id, "viewer"):
            logger.warning(
                f"User {current_user.id} attempted to view members of project {project_id} without permission"
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You are not a member of this project",
            )

        members = await service.get_project_members(project_id)

        # Load user data separately to avoid lazy loading issues
        from ardha.repositories.user_repository import UserRepository

        user_repo = UserRepository(db)

        # Populate user data in response
        member_responses = []
        for member in members:
            response = ProjectMemberResponse.model_validate(member)
            user = await user_repo.get_by_id(member.user_id)
            if user:
                response.user_email = user.email
                response.user_username = user.username
                response.user_full_name = user.full_name
            member_responses.append(response)

        return member_responses
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error listing members for project {project_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to list project members",
        )


@router.post(
    "/{project_id}/members",
    response_model=ProjectMemberResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Add project member",
    description="Add a new member to the project. Requires owner or admin role.",
)
async def add_project_member(
    project_id: UUID,
    member_data: ProjectMemberAddRequest,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> ProjectMemberResponse:
    """
    Add member to project.

    Requires owner or admin role.
    Cannot add user as 'owner' (owner is assigned at project creation).

    - **user_id**: UUID of user to add
    - **role**: Role to assign (admin/member/viewer)

    Returns created project member.
    """
    try:
        service = ProjectService(db)
        member = await service.add_member(
            project_id,
            current_user.id,
            member_data.user_id,
            member_data.role,
        )

        # Load user data separately to avoid lazy loading issues
        from ardha.repositories.user_repository import UserRepository

        user_repo = UserRepository(db)
        user = await user_repo.get_by_id(member_data.user_id)

        # Populate response
        response = ProjectMemberResponse.model_validate(member)
        if user:
            response.user_email = user.email
            response.user_username = user.username
            response.user_full_name = user.full_name

        return response
    except ProjectNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project {project_id} not found",
        )
    except InsufficientPermissionsError as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e),
        )
    except IntegrityError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"User {member_data.user_id} is already a member of this project",
        )
    except Exception as e:
        logger.error(f"Error adding member to project {project_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to add project member",
        )


@router.delete(
    "/{project_id}/members/{user_id}",
    summary="Remove project member",
    description="Remove a member from the project. Requires owner or admin role. Cannot remove owner.",
)
async def remove_project_member(
    project_id: UUID,
    user_id: UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """
    Remove member from project.

    Requires owner or admin role.
    Cannot remove the project owner.

    Returns success message.
    """
    try:
        service = ProjectService(db)
        await service.remove_member(project_id, current_user.id, user_id)

        return {"message": "Member removed successfully"}
    except ProjectNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User {user_id} is not a member of project {project_id}",
        )
    except InsufficientPermissionsError as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e),
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except Exception as e:
        logger.error(
            f"Error removing member {user_id} from project {project_id}: {e}",
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to remove project member",
        )


@router.patch(
    "/{project_id}/members/{user_id}",
    response_model=ProjectMemberResponse,
    summary="Update member role",
    description="Update a member's role. Requires owner or admin role.",
)
async def update_member_role(
    project_id: UUID,
    user_id: UUID,
    role_data: ProjectMemberUpdateRequest,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> ProjectMemberResponse:
    """
    Update member's role.

    Requires owner or admin role.
    Cannot change to 'owner' role (owner transfer is separate).

    - **role**: New role (admin/member/viewer)

    Returns updated project member.
    """
    try:
        service = ProjectService(db)
        member = await service.update_member_role(
            project_id,
            current_user.id,
            user_id,
            role_data.role,
        )

        # Load user data separately to avoid lazy loading issues
        from ardha.repositories.user_repository import UserRepository

        user_repo = UserRepository(db)
        user = await user_repo.get_by_id(user_id)

        # Populate response
        response = ProjectMemberResponse.model_validate(member)
        if user:
            response.user_email = user.email
            response.user_username = user.username
            response.user_full_name = user.full_name

        return response
    except ProjectNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User {user_id} is not a member of project {project_id}",
        )
    except InsufficientPermissionsError as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e),
        )
    except Exception as e:
        logger.error(
            f"Error updating role for member {user_id} in project {project_id}: {e}",
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update member role",
        )
