"""
Milestone API routes.

This module defines FastAPI routes for milestone management operations including
CRUD, status updates, progress tracking, and analytics.
"""

import logging
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from ardha.core.database import get_db
from ardha.core.security import get_current_active_user
from ardha.models.user import User
from ardha.schemas.requests.milestone import (
    MilestoneCreateRequest,
    MilestoneProgressUpdateRequest,
    MilestoneReorderRequest,
    MilestoneStatusUpdateRequest,
    MilestoneUpdateRequest,
)
from ardha.schemas.responses.milestone import (
    MilestoneListResponse,
    MilestoneResponse,
    MilestoneSummaryResponse,
)
from ardha.services.milestone_service import (
    InsufficientMilestonePermissionsError,
    InvalidMilestoneStatusError,
    MilestoneHasTasksError,
    MilestoneNotFoundError,
    MilestoneService,
)

logger = logging.getLogger(__name__)

router = APIRouter(tags=["milestones"])


# ============= Milestone CRUD =============


@router.post(
    "/projects/{project_id}/milestones",
    response_model=MilestoneResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new milestone",
    description="Create a new milestone for a project. Requires project member access.",
)
async def create_milestone(
    project_id: UUID,
    milestone_data: MilestoneCreateRequest,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> MilestoneResponse:
    """
    Create a new milestone.
    
    **Permissions:** Requires project member access (member role or higher).
    
    **Request Body:**
    - **name**: Milestone display name (required, max 255 chars)
    - **description**: Optional detailed description
    - **status**: Status (default: not_started)
    - **color**: Hex color code (default: #3b82f6)
    - **start_date**: Optional start date
    - **due_date**: Optional target completion date
    - **order**: Display order (default: appended to end)
    
    **Returns:**
    - **201 Created**: Milestone created successfully
    - **400 Bad Request**: Invalid data
    - **403 Forbidden**: User lacks permissions
    - **404 Not Found**: Project not found
    """
    try:
        service = MilestoneService(db)
        milestone = await service.create_milestone(
            milestone_data,
            project_id,
            current_user.id,
        )
        
        # Add computed fields
        response = MilestoneResponse.model_validate(milestone)
        response.is_overdue = milestone.is_overdue
        response.days_remaining = milestone.days_remaining
        
        return response
    except InsufficientMilestonePermissionsError as e:
        logger.warning(f"Permission denied creating milestone: {e}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e),
        )
    except IntegrityError as e:
        logger.error(f"Integrity error creating milestone: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Database constraint violation: {str(e)}",
        )
    except Exception as e:
        logger.error(f"Error creating milestone: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create milestone: {str(e)}",
        )


@router.get(
    "/projects/{project_id}/milestones",
    response_model=MilestoneListResponse,
    summary="List project milestones",
    description="Get all milestones for a project, ordered by display order.",
)
async def list_project_milestones(
    project_id: UUID,
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(100, ge=1, le=100, description="Maximum records to return"),
    milestone_status: str | None = Query(None, description="Filter by status", alias="status"),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> MilestoneListResponse:
    """
    List all milestones for a project.
    
    **Permissions:** Requires project member access.
    
    **Query Parameters:**
    - **skip**: Pagination offset (default: 0)
    - **limit**: Maximum results per page (default: 100, max: 100)
    - **status**: Filter by status (optional)
    
    **Returns:**
    - **200 OK**: List of milestones with total count
    - **403 Forbidden**: User lacks permissions
    - **404 Not Found**: Project not found
    """
    try:
        service = MilestoneService(db)
        
        if milestone_status:
            # Filter by status
            milestones = await service.repository.get_by_status(project_id, milestone_status)
            # Apply pagination manually
            milestones = milestones[skip:skip + limit]
        else:
            milestones = await service.get_project_milestones(
                project_id,
                current_user.id,
                skip=skip,
                limit=limit,
            )
        
        # Get total count
        all_milestones = await service.repository.get_project_milestones(
            project_id, skip=0, limit=10000
        )
        total = len(all_milestones)
        
        # Add computed fields
        responses = []
        for milestone in milestones:
            response = MilestoneResponse.model_validate(milestone)
            response.is_overdue = milestone.is_overdue
            response.days_remaining = milestone.days_remaining
            responses.append(response)
        
        return MilestoneListResponse(milestones=responses, total=total)
    except InsufficientMilestonePermissionsError as e:
        logger.warning(f"Permission denied listing milestones: {e}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e),
        )
    except Exception as e:
        logger.error(f"Error listing milestones: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to list milestones",
        )


@router.get(
    "/{milestone_id}",
    response_model=MilestoneResponse,
    summary="Get milestone details",
    description="Get detailed information about a specific milestone.",
)
async def get_milestone(
    milestone_id: UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> MilestoneResponse:
    """
    Get milestone by ID.
    
    **Permissions:** Requires project member access.
    
    **Returns:**
    - **200 OK**: Milestone details
    - **403 Forbidden**: User lacks permissions
    - **404 Not Found**: Milestone not found
    """
    try:
        service = MilestoneService(db)
        milestone = await service.get_milestone(milestone_id, current_user.id)
        
        # Add computed fields
        response = MilestoneResponse.model_validate(milestone)
        response.is_overdue = milestone.is_overdue
        response.days_remaining = milestone.days_remaining
        
        return response
    except MilestoneNotFoundError as e:
        logger.warning(f"Milestone not found: {e}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except InsufficientMilestonePermissionsError as e:
        logger.warning(f"Permission denied getting milestone: {e}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e),
        )
    except Exception as e:
        logger.error(f"Error getting milestone: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get milestone",
        )


@router.patch(
    "/{milestone_id}",
    response_model=MilestoneResponse,
    summary="Update milestone",
    description="Update milestone fields. All fields are optional.",
)
async def update_milestone(
    milestone_id: UUID,
    update_data: MilestoneUpdateRequest,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> MilestoneResponse:
    """
    Update milestone.
    
    **Permissions:** Requires project member access.
    
    **Request Body:** All fields optional
    - **name**: New milestone name
    - **description**: New description
    - **status**: New status
    - **color**: New color
    - **start_date**: New start date
    - **due_date**: New due date
    - **progress_percentage**: New progress (0-100)
    - **order**: New display order
    
    **Returns:**
    - **200 OK**: Updated milestone
    - **400 Bad Request**: Invalid data
    - **403 Forbidden**: User lacks permissions
    - **404 Not Found**: Milestone not found
    """
    try:
        service = MilestoneService(db)
        milestone = await service.update_milestone(
            milestone_id,
            current_user.id,
            update_data,
        )
        
        # Add computed fields
        response = MilestoneResponse.model_validate(milestone)
        response.is_overdue = milestone.is_overdue
        response.days_remaining = milestone.days_remaining
        
        return response
    except MilestoneNotFoundError as e:
        logger.warning(f"Milestone not found: {e}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except InsufficientMilestonePermissionsError as e:
        logger.warning(f"Permission denied updating milestone: {e}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e),
        )
    except Exception as e:
        logger.error(f"Error updating milestone: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update milestone",
        )


@router.delete(
    "/{milestone_id}",
    summary="Delete milestone",
    description="Delete a milestone. Prevents deletion if milestone has linked tasks.",
)
async def delete_milestone(
    milestone_id: UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """
    Delete a milestone.
    
    **Permissions:** Requires owner or admin role.
    
    **Protection:** Cannot delete milestone with linked tasks.
    
    **Returns:**
    - **200 OK**: Milestone deleted successfully
    - **400 Bad Request**: Milestone has linked tasks
    - **403 Forbidden**: User lacks permissions
    - **404 Not Found**: Milestone not found
    """
    try:
        service = MilestoneService(db)
        await service.delete_milestone(milestone_id, current_user.id)
        return {"message": "Milestone deleted successfully"}
    except MilestoneNotFoundError as e:
        logger.warning(f"Milestone not found: {e}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except MilestoneHasTasksError as e:
        logger.warning(f"Cannot delete milestone with tasks: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except InsufficientMilestonePermissionsError as e:
        logger.warning(f"Permission denied deleting milestone: {e}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e),
        )
    except Exception as e:
        logger.error(f"Error deleting milestone: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete milestone",
        )


# ============= Status Management =============


@router.patch(
    "/{milestone_id}/status",
    response_model=MilestoneResponse,
    summary="Update milestone status",
    description="Update milestone status with validation and automatic timestamp management.",
)
async def update_milestone_status(
    milestone_id: UUID,
    status_data: MilestoneStatusUpdateRequest,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> MilestoneResponse:
    """
    Update milestone status.
    
    **Permissions:** Requires project member access.
    
    **Features:**
    - Validates status transitions (e.g., not_started → in_progress)
    - Automatically sets completed_at when status → completed
    - Clears completed_at when leaving completed status
    
    **Valid Transitions:**
    - not_started → in_progress, cancelled
    - in_progress → completed, not_started, cancelled
    - completed → in_progress (reopen)
    - cancelled → not_started (uncancel)
    
    **Returns:**
    - **200 OK**: Status updated successfully
    - **400 Bad Request**: Invalid status transition
    - **403 Forbidden**: User lacks permissions
    - **404 Not Found**: Milestone not found
    """
    try:
        service = MilestoneService(db)
        milestone = await service.update_status(
            milestone_id,
            current_user.id,
            status_data.status,
        )
        
        # Add computed fields
        response = MilestoneResponse.model_validate(milestone)
        response.is_overdue = milestone.is_overdue
        response.days_remaining = milestone.days_remaining
        
        return response
    except MilestoneNotFoundError as e:
        logger.warning(f"Milestone not found: {e}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except InvalidMilestoneStatusError as e:
        logger.warning(f"Invalid status transition: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except InsufficientMilestonePermissionsError as e:
        logger.warning(f"Permission denied updating status: {e}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e),
        )
    except Exception as e:
        logger.error(f"Error updating milestone status: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update milestone status",
        )


# ============= Progress Management =============


@router.patch(
    "/{milestone_id}/progress",
    response_model=MilestoneResponse,
    summary="Manually update milestone progress",
    description="Manually set milestone progress percentage (0-100).",
)
async def update_milestone_progress(
    milestone_id: UUID,
    progress_data: MilestoneProgressUpdateRequest,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> MilestoneResponse:
    """
    Manually update milestone progress.
    
    **Permissions:** Requires project member access.
    
    **Request Body:**
    - **progress_percentage**: Progress value (0-100)
    
    **Returns:**
    - **200 OK**: Progress updated successfully
    - **400 Bad Request**: Invalid progress value
    - **403 Forbidden**: User lacks permissions
    - **404 Not Found**: Milestone not found
    """
    try:
        service = MilestoneService(db)
        milestone = await service.update_progress(
            milestone_id,
            current_user.id,
            progress_data.progress_percentage,
        )
        
        # Add computed fields
        response = MilestoneResponse.model_validate(milestone)
        response.is_overdue = milestone.is_overdue
        response.days_remaining = milestone.days_remaining
        
        return response
    except MilestoneNotFoundError as e:
        logger.warning(f"Milestone not found: {e}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except ValueError as e:
        logger.warning(f"Invalid progress value: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except InsufficientMilestonePermissionsError as e:
        logger.warning(f"Permission denied updating progress: {e}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e),
        )
    except Exception as e:
        logger.error(f"Error updating milestone progress: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update milestone progress",
        )


@router.post(
    "/{milestone_id}/recalculate",
    response_model=MilestoneResponse,
    summary="Auto-calculate milestone progress",
    description="Recalculate progress from task completion. Formula: (completed_tasks / total_tasks) * 100",
)
async def recalculate_milestone_progress(
    milestone_id: UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> MilestoneResponse:
    """
    Auto-calculate progress from task completion.
    
    **Permissions:** No permission check (system operation).
    
    **Calculation:**
    - progress = (completed_tasks / total_tasks) * 100
    - Returns 0 if no tasks exist
    
    **Returns:**
    - **200 OK**: Progress recalculated successfully
    - **404 Not Found**: Milestone not found
    """
    try:
        service = MilestoneService(db)
        milestone = await service.recalculate_progress(milestone_id)
        
        # Add computed fields
        response = MilestoneResponse.model_validate(milestone)
        response.is_overdue = milestone.is_overdue
        response.days_remaining = milestone.days_remaining
        
        return response
    except MilestoneNotFoundError as e:
        logger.warning(f"Milestone not found: {e}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except Exception as e:
        logger.error(f"Error recalculating milestone progress: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to recalculate milestone progress",
        )


# ============= Ordering =============


@router.patch(
    "/{milestone_id}/reorder",
    response_model=MilestoneResponse,
    summary="Reorder milestone",
    description="Change milestone display order for drag-drop UI. Handles order collision automatically.",
)
async def reorder_milestone(
    milestone_id: UUID,
    reorder_data: MilestoneReorderRequest,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> MilestoneResponse:
    """
    Change milestone order (for drag-drop UI).
    
    **Permissions:** Requires project member access.
    
    **Features:**
    - Automatically shifts other milestones to make room
    - Maintains unique order within project
    
    **Request Body:**
    - **new_order**: New order value (>= 0)
    
    **Returns:**
    - **200 OK**: Milestone reordered successfully
    - **400 Bad Request**: Invalid order value
    - **403 Forbidden**: User lacks permissions
    - **404 Not Found**: Milestone not found
    """
    try:
        service = MilestoneService(db)
        milestone = await service.reorder_milestone(
            milestone_id,
            current_user.id,
            reorder_data.new_order,
        )
        
        # Add computed fields
        response = MilestoneResponse.model_validate(milestone)
        response.is_overdue = milestone.is_overdue
        response.days_remaining = milestone.days_remaining
        
        return response
    except MilestoneNotFoundError as e:
        logger.warning(f"Milestone not found: {e}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except ValueError as e:
        logger.warning(f"Invalid order value: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except InsufficientMilestonePermissionsError as e:
        logger.warning(f"Permission denied reordering milestone: {e}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e),
        )
    except Exception as e:
        logger.error(f"Error reordering milestone: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to reorder milestone",
        )


# ============= Analytics & Views =============


@router.get(
    "/{milestone_id}/summary",
    response_model=MilestoneSummaryResponse,
    summary="Get milestone summary with statistics",
    description="Get milestone details with task counts by status and progress statistics.",
)
async def get_milestone_summary(
    milestone_id: UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> MilestoneSummaryResponse:
    """
    Get milestone summary with statistics.
    
    **Permissions:** Requires project member access.
    
    **Returns:**
    - **milestone**: Full milestone data
    - **task_stats**: Task counts by status (todo, in_progress, in_review, done, cancelled)
    - **total_tasks**: Total number of tasks
    - **completed_tasks**: Number of completed tasks
    - **auto_progress**: Auto-calculated progress from task completion
    
    **Returns:**
    - **200 OK**: Milestone summary
    - **403 Forbidden**: User lacks permissions
    - **404 Not Found**: Milestone not found
    """
    try:
        service = MilestoneService(db)
        summary = await service.get_milestone_summary(milestone_id, current_user.id)
        
        # Add computed fields to milestone
        milestone = summary['milestone']
        milestone_response = MilestoneResponse.model_validate(milestone)
        milestone_response.is_overdue = milestone.is_overdue
        milestone_response.days_remaining = milestone.days_remaining
        
        return MilestoneSummaryResponse(
            milestone=milestone_response,
            task_stats=summary['task_stats'],
            total_tasks=summary['total_tasks'],
            completed_tasks=summary['completed_tasks'],
            auto_progress=summary['auto_progress'],
        )
    except MilestoneNotFoundError as e:
        logger.warning(f"Milestone not found: {e}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except InsufficientMilestonePermissionsError as e:
        logger.warning(f"Permission denied getting summary: {e}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e),
        )
    except Exception as e:
        logger.error(f"Error getting milestone summary: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get milestone summary",
        )


@router.get(
    "/projects/{project_id}/milestones/roadmap",
    response_model=list[MilestoneResponse],
    summary="Get project roadmap",
    description="Get all milestones for roadmap/timeline visualization, ordered by display order.",
)
async def get_project_roadmap(
    project_id: UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> list[MilestoneResponse]:
    """
    Get project roadmap (all milestones).
    
    **Permissions:** Requires project member access.
    
    **Perfect for:**
    - Roadmap/timeline visualization
    - Gantt chart views
    - Project planning dashboards
    
    **Returns:**
    - **200 OK**: List of all milestones ordered by order/dates
    - **403 Forbidden**: User lacks permissions
    - **404 Not Found**: Project not found
    """
    try:
        service = MilestoneService(db)
        milestones = await service.get_project_roadmap(project_id, current_user.id)
        
        # Add computed fields
        responses = []
        for milestone in milestones:
            response = MilestoneResponse.model_validate(milestone)
            response.is_overdue = milestone.is_overdue
            response.days_remaining = milestone.days_remaining
            responses.append(response)
        
        return responses
    except InsufficientMilestonePermissionsError as e:
        logger.warning(f"Permission denied getting roadmap: {e}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e),
        )
    except Exception as e:
        logger.error(f"Error getting project roadmap: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get project roadmap",
        )


@router.get(
    "/projects/{project_id}/milestones/upcoming",
    response_model=list[MilestoneResponse],
    summary="Get upcoming milestones",
    description="Get milestones due within the next N days (default: 30).",
)
async def get_upcoming_milestones(
    project_id: UUID,
    days: int = Query(30, ge=1, le=365, description="Number of days to look ahead"),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> list[MilestoneResponse]:
    """
    Get milestones due within N days.
    
    **Permissions:** Requires project member access.
    
    **Query Parameters:**
    - **days**: Number of days to look ahead (default: 30, max: 365)
    
    **Excludes:**
    - Completed milestones
    - Cancelled milestones
    - Milestones without due dates
    
    **Returns:**
    - **200 OK**: List of upcoming milestones ordered by due date
    - **403 Forbidden**: User lacks permissions
    - **404 Not Found**: Project not found
    """
    try:
        service = MilestoneService(db)
        milestones = await service.get_upcoming_milestones(
            project_id,
            current_user.id,
            days,
        )
        
        # Add computed fields
        responses = []
        for milestone in milestones:
            response = MilestoneResponse.model_validate(milestone)
            response.is_overdue = milestone.is_overdue
            response.days_remaining = milestone.days_remaining
            responses.append(response)
        
        return responses
    except InsufficientMilestonePermissionsError as e:
        logger.warning(f"Permission denied getting upcoming milestones: {e}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e),
        )
    except Exception as e:
        logger.error(f"Error getting upcoming milestones: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get upcoming milestones",
        )