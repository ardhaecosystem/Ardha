"""
Task API routes.

This module provides REST API endpoints for task management including:
- CRUD operations
- Status management
- Dependencies
- Tags
- Activity log
- Special views (Board, Calendar, Timeline)
"""

import logging
from collections import defaultdict
from datetime import datetime, timedelta
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from ardha.core.database import get_db
from ardha.core.security import get_current_user
from ardha.models.user import User
from ardha.schemas.requests.task import (
    TaskAssignRequest,
    TaskCreateRequest,
    TaskDependencyRequest,
    TaskFilterRequest,
    TaskStatusUpdateRequest,
    TaskTagRequest,
    TaskUpdateRequest,
)
from ardha.schemas.responses.task import (
    TaskActivityResponse,
    TaskBoardResponse,
    TaskCalendarResponse,
    TaskDependencyResponse,
    TaskListResponse,
    TaskResponse,
    TaskTagResponse,
    TaskTimelineResponse,
)
from ardha.services.task_service import (
    CircularDependencyError,
    InsufficientTaskPermissionsError,
    InvalidStatusTransitionError,
    TaskNotFoundError,
    TaskService,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/tasks", tags=["tasks"])


# ============= Helper Functions =============


def _build_task_response(task: Any, check_blocked: bool = False) -> TaskResponse:
    """
    Build TaskResponse from Task model.
    
    Args:
        task: Task model instance
        check_blocked: Whether to compute is_blocked field
        
    Returns:
        TaskResponse with populated fields
    """
    # Build task response with relationships
    response_data = {
        "id": task.id,
        "project_id": task.project_id,
        "identifier": task.identifier,
        "title": task.title,
        "description": task.description,
        "status": task.status,
        "assignee_id": task.assignee_id,
        "created_by_id": task.created_by_id,
        "phase": task.phase,
        "milestone_id": task.milestone_id,
        "epic": task.epic,
        "estimate_hours": task.estimate_hours,
        "actual_hours": task.actual_hours,
        "complexity": task.complexity,
        "priority": task.priority,
        "openspec_change_path": task.openspec_change_path,
        "ai_generated": task.ai_generated,
        "ai_confidence": task.ai_confidence,
        "related_commits": task.related_commits or [],
        "related_prs": task.related_prs or [],
        "related_files": task.related_files or [],
        "due_date": task.due_date,
        "started_at": task.started_at,
        "completed_at": task.completed_at,
        "created_at": task.created_at,
        "updated_at": task.updated_at,
    }
    
    # Add assignee info if available
    if task.assignee:
        response_data["assignee_username"] = task.assignee.username
        response_data["assignee_full_name"] = task.assignee.full_name
    
    # Add creator info if available
    if task.created_by:
        response_data["created_by_username"] = task.created_by.username
        response_data["created_by_full_name"] = task.created_by.full_name
    
    # Add tags
    if task.tags:
        response_data["tags"] = [
            TaskTagResponse.model_validate(tag) for tag in task.tags
        ]
    
    # Check if task is blocked (only if dependencies are already loaded)
    if check_blocked:
        try:
            # Check if dependencies are loaded (not lazy)
            dependencies = task.dependencies if hasattr(task, '__dict__') and 'dependencies' in task.__dict__ else []
            if dependencies:
                incomplete_deps = [
                    dep for dep in dependencies
                    if dep.depends_on_task and dep.depends_on_task.status != "done"
                ]
                response_data["is_blocked"] = len(incomplete_deps) > 0
        except:
            # If accessing dependencies fails, assume not blocked
            response_data["is_blocked"] = False
    
    return TaskResponse(**response_data)


# ============= Task CRUD Endpoints =============


@router.post(
    "/projects/{project_id}/tasks",
    response_model=TaskResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create new task",
    description="Create a new task in the specified project.",
)
async def create_task(
    project_id: UUID,
    task_data: TaskCreateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> TaskResponse:
    """
    Create a new task.
    
    Requires project member permissions.
    Automatically generates unique identifier (e.g., ARD-001).
    """
    service = TaskService(db)
    
    try:
        # Convert request to dict
        task_dict = task_data.model_dump(exclude_none=True, exclude={"tags", "depends_on"})
        
        # Create task
        task = await service.create_task(
            project_id=project_id,
            task_data=task_dict,
            created_by_id=current_user.id,
        )
        
        # Add tags if provided
        if task_data.tags:
            for tag_name in task_data.tags:
                await service.add_tag_to_task(
                    task_id=task.id,
                    user_id=current_user.id,
                    tag_name=tag_name,
                )
        
        # Add dependencies if provided
        if task_data.depends_on:
            for depends_on_id in task_data.depends_on:
                try:
                    await service.add_dependency(
                        task_id=task.id,
                        user_id=current_user.id,
                        depends_on_task_id=depends_on_id,
                    )
                except CircularDependencyError:
                    # Skip circular dependencies, but don't fail entire request
                    logger.warning(f"Skipping circular dependency: {task.id} → {depends_on_id}")
        
        # Commit transaction
        await db.commit()
        
        # Reload task with all relationships using repository
        task = await service.repository.get_by_id(task.id)
        if not task:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Task created but failed to reload",
            )
        
        return _build_task_response(task)
        
    except InsufficientTaskPermissionsError as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e),
        )
    except Exception as e:
        await db.rollback()
        logger.error(f"Error creating task: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create task",
        )


@router.get(
    "/projects/{project_id}/tasks",
    response_model=TaskListResponse,
    summary="List project tasks",
    description="Get filtered and paginated list of tasks for a project.",
)
async def list_project_tasks(
    project_id: UUID,
    status_filter: list[str] | None = Query(None, alias="status"),
    assignee_id: UUID | None = None,
    priority: list[str] | None = None,
    milestone_id: UUID | None = None,
    has_due_date: bool | None = None,
    overdue_only: bool = False,
    tags: list[str] | None = None,
    search: str | None = None,
    sort_by: str = "created_at",
    sort_order: str = "desc",
    skip: int = 0,
    limit: int = Query(default=100, le=100),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> TaskListResponse:
    """
    List tasks for a project with filtering and pagination.
    
    Supports filtering by:
    - Status (multi-select)
    - Assignee
    - Priority (multi-select)
    - Milestone
    - Due date presence
    - Overdue status
    - Tags (multi-select)
    - Search (title/description/identifier)
    
    Sorting options:
    - created_at, due_date, priority, status, updated_at
    """
    service = TaskService(db)
    
    try:
        # Build filters
        filters = {
            "status": status_filter,
            "assignee_id": assignee_id,
            "priority": priority,
            "milestone_id": milestone_id,
            "has_due_date": has_due_date,
            "overdue_only": overdue_only,
            "tags": tags,
            "search": search,
            "sort_by": sort_by,
            "sort_order": sort_order,
        }
        
        # Get tasks
        tasks, total = await service.get_project_tasks(
            project_id=project_id,
            user_id=current_user.id,
            filters=filters,
            skip=skip,
            limit=limit,
        )
        
        # Get status counts
        status_counts = await service.repository.count_by_status(project_id)
        
        # Build responses
        task_responses = [_build_task_response(task, check_blocked=True) for task in tasks]
        
        return TaskListResponse(
            tasks=task_responses,
            total=total,
            skip=skip,
            limit=limit,
            status_counts=status_counts,
        )
        
    except InsufficientTaskPermissionsError as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e),
        )


@router.get(
    "/{task_id}",
    response_model=TaskResponse,
    summary="Get task by ID",
    description="Get detailed task information by UUID.",
)
async def get_task(
    task_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> TaskResponse:
    """Get task by ID with all relationships loaded."""
    service = TaskService(db)
    
    try:
        task = await service.get_task(task_id, current_user.id)
        return _build_task_response(task, check_blocked=True)
        
    except TaskNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Task {task_id} not found",
        )
    except InsufficientTaskPermissionsError as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e),
        )


@router.get(
    "/identifier/{project_id}/{identifier}",
    response_model=TaskResponse,
    summary="Get task by identifier",
    description="Get task by project-specific identifier (e.g., ARD-001).",
)
async def get_task_by_identifier(
    project_id: UUID,
    identifier: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> TaskResponse:
    """Get task by identifier string."""
    service = TaskService(db)
    
    # Get task
    task = await service.repository.get_by_identifier(project_id, identifier)
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Task {identifier} not found in project",
        )
    
    try:
        # Verify permissions
        await service.get_task(task.id, current_user.id)
        return _build_task_response(task, check_blocked=True)
        
    except InsufficientTaskPermissionsError as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e),
        )


@router.patch(
    "/{task_id}",
    response_model=TaskResponse,
    summary="Update task",
    description="Update task fields (partial update).",
)
async def update_task(
    task_id: UUID,
    update_data: TaskUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> TaskResponse:
    """Update task fields with activity logging."""
    service = TaskService(db)
    
    try:
        # Convert request to dict
        update_dict = update_data.model_dump(exclude_none=True)
        
        if not update_dict:
            # No changes, just return current task
            task = await service.get_task(task_id, current_user.id)
            return _build_task_response(task, check_blocked=True)
        
        # Update task
        task = await service.update_task(
            task_id=task_id,
            user_id=current_user.id,
            update_data=update_dict,
        )
        
        await db.commit()
        await db.refresh(task)
        
        return _build_task_response(task, check_blocked=True)
        
    except TaskNotFoundError:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Task {task_id} not found",
        )
    except InsufficientTaskPermissionsError as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e),
        )
    except Exception as e:
        await db.rollback()
        logger.error(f"Error updating task: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update task",
        )


@router.delete(
    "/{task_id}",
    status_code=status.HTTP_200_OK,
    summary="Delete task",
    description="Delete a task (requires admin permissions).",
)
async def delete_task(
    task_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, str]:
    """Delete task permanently."""
    service = TaskService(db)
    
    try:
        success = await service.delete_task(task_id, current_user.id)
        await db.commit()
        
        if success:
            return {"message": "Task deleted successfully"}
        else:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Task not found",
            )
            
    except TaskNotFoundError:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Task {task_id} not found",
        )
    except InsufficientTaskPermissionsError as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e),
        )


# ============= Status Management =============


@router.patch(
    "/{task_id}/status",
    response_model=TaskResponse,
    summary="Update task status",
    description="Update task status with transition validation.",
)
async def update_task_status(
    task_id: UUID,
    status_update: TaskStatusUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> TaskResponse:
    """
    Update task status.
    
    Validates status transitions and updates timestamps automatically:
    - todo → in_progress: Sets started_at
    - * → done: Sets completed_at
    - done → in_review: Clears completed_at
    """
    service = TaskService(db)
    
    try:
        task = await service.update_status(
            task_id=task_id,
            user_id=current_user.id,
            new_status=status_update.status,
        )
        
        await db.commit()
        
        # Reload with relationships
        task = await service.repository.get_by_id(task_id)
        if not task:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to reload task",
            )
        
        return _build_task_response(task, check_blocked=True)
        
    except TaskNotFoundError:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Task {task_id} not found",
        )
    except InvalidStatusTransitionError as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except InsufficientTaskPermissionsError as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e),
        )


@router.post(
    "/{task_id}/assign",
    response_model=TaskResponse,
    summary="Assign task",
    description="Assign task to a user.",
)
async def assign_task(
    task_id: UUID,
    assign_data: TaskAssignRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> TaskResponse:
    """Assign task to a user."""
    service = TaskService(db)
    
    try:
        task = await service.assign_task(
            task_id=task_id,
            user_id=current_user.id,
            assignee_id=assign_data.assignee_id,
        )
        
        await db.commit()
        
        # Reload with relationships
        task = await service.repository.get_by_id(task_id)
        if not task:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to reload task",
            )
        
        return _build_task_response(task, check_blocked=True)
        
    except TaskNotFoundError:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Task {task_id} not found",
        )
    except InsufficientTaskPermissionsError as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e),
        )


@router.post(
    "/{task_id}/unassign",
    response_model=TaskResponse,
    summary="Unassign task",
    description="Remove assignee from task.",
)
async def unassign_task(
    task_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> TaskResponse:
    """Remove assignee from task."""
    service = TaskService(db)
    
    try:
        task = await service.unassign_task(task_id, current_user.id)
        
        await db.commit()
        
        # Reload with relationships
        task = await service.repository.get_by_id(task_id)
        if not task:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to reload task",
            )
        
        return _build_task_response(task, check_blocked=True)
        
    except TaskNotFoundError:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Task {task_id} not found",
        )
    except InsufficientTaskPermissionsError as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e),
        )


# ============= Dependencies =============


@router.post(
    "/{task_id}/dependencies",
    response_model=TaskDependencyResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Add task dependency",
    description="Add a dependency between tasks (prevents circular dependencies).",
)
async def add_task_dependency(
    task_id: UUID,
    dependency_data: TaskDependencyRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> TaskDependencyResponse:
    """Add dependency: task depends on another task."""
    service = TaskService(db)
    
    try:
        dependency = await service.add_dependency(
            task_id=task_id,
            user_id=current_user.id,
            depends_on_task_id=dependency_data.depends_on_task_id,
        )
        
        await db.commit()
        await db.refresh(dependency)
        
        # Build response with task info (fetch task separately to avoid lazy loading)
        depends_on_task = await service.repository.get_by_id(dependency.depends_on_task_id)
        
        response_data = {
            "id": dependency.id,
            "task_id": dependency.task_id,
            "depends_on_task_id": dependency.depends_on_task_id,
        }
        
        if depends_on_task:
            response_data["depends_on_task_identifier"] = depends_on_task.identifier
            response_data["depends_on_task_title"] = depends_on_task.title
            response_data["depends_on_task_status"] = depends_on_task.status
        
        return TaskDependencyResponse(**response_data)
        
    except TaskNotFoundError as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except CircularDependencyError as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except InsufficientTaskPermissionsError as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e),
        )
    except ValueError as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.delete(
    "/{task_id}/dependencies/{depends_on_task_id}",
    status_code=status.HTTP_200_OK,
    summary="Remove task dependency",
    description="Remove a dependency between tasks.",
)
async def remove_task_dependency(
    task_id: UUID,
    depends_on_task_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, str]:
    """Remove dependency."""
    service = TaskService(db)
    
    try:
        success = await service.remove_dependency(
            task_id=task_id,
            user_id=current_user.id,
            depends_on_task_id=depends_on_task_id,
        )
        
        await db.commit()
        
        if success:
            return {"message": "Dependency removed successfully"}
        else:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Dependency not found",
            )
            
    except TaskNotFoundError:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found",
        )
    except InsufficientTaskPermissionsError as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e),
        )


@router.get(
    "/{task_id}/dependencies",
    response_model=list[TaskDependencyResponse],
    summary="List task dependencies",
    description="Get all dependencies for a task.",
)
async def list_task_dependencies(
    task_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[TaskDependencyResponse]:
    """Get all tasks this task depends on."""
    service = TaskService(db)
    
    try:
        # Verify access
        task = await service.get_task(task_id, current_user.id)
        
        # Get dependencies
        dependencies = await service.repository.get_dependencies(task_id)
        
        # Build responses
        responses = []
        for dep_task in dependencies:
            # Find the dependency record
            dep_record = next(
                (d for d in task.dependencies if d.depends_on_task_id == dep_task.id),
                None,
            )
            
            if dep_record:
                responses.append(
                    TaskDependencyResponse(
                        id=dep_record.id,
                        task_id=dep_record.task_id,
                        depends_on_task_id=dep_task.id,
                        depends_on_task_identifier=dep_task.identifier,
                        depends_on_task_title=dep_task.title,
                        depends_on_task_status=dep_task.status,
                    )
                )
        
        return responses
        
    except TaskNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Task {task_id} not found",
        )
    except InsufficientTaskPermissionsError as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e),
        )


# ============= Tags =============


@router.post(
    "/{task_id}/tags",
    response_model=TaskResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Add tag to task",
    description="Add or create a tag and apply to task.",
)
async def add_task_tag(
    task_id: UUID,
    tag_data: TaskTagRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> TaskResponse:
    """Add tag to task (creates tag if doesn't exist)."""
    service = TaskService(db)
    
    try:
        task = await service.add_tag_to_task(
            task_id=task_id,
            user_id=current_user.id,
            tag_name=tag_data.name,
            color=tag_data.color,
        )
        
        await db.commit()
        
        # Reload with relationships
        task = await service.repository.get_by_id(task_id)
        if not task:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to reload task",
            )
        
        return _build_task_response(task, check_blocked=True)
        
    except TaskNotFoundError:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Task {task_id} not found",
        )
    except InsufficientTaskPermissionsError as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e),
        )


@router.delete(
    "/{task_id}/tags/{tag_id}",
    response_model=TaskResponse,
    summary="Remove tag from task",
    description="Remove a tag from task.",
)
async def remove_task_tag(
    task_id: UUID,
    tag_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> TaskResponse:
    """Remove tag from task."""
    service = TaskService(db)
    
    try:
        task = await service.remove_tag_from_task(
            task_id=task_id,
            user_id=current_user.id,
            tag_id=tag_id,
        )
        
        await db.commit()
        
        # Reload with relationships
        task = await service.repository.get_by_id(task_id)
        if not task:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to reload task",
            )
        
        return _build_task_response(task, check_blocked=True)
        
    except TaskNotFoundError:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Task {task_id} not found",
        )
    except InsufficientTaskPermissionsError as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e),
        )


# ============= Activity Log =============


@router.get(
    "/{task_id}/activities",
    response_model=list[TaskActivityResponse],
    summary="Get task activity log",
    description="Get comprehensive activity history for a task.",
)
async def get_task_activities(
    task_id: UUID,
    limit: int = Query(default=50, le=100),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[TaskActivityResponse]:
    """Get activity log for task."""
    service = TaskService(db)
    
    try:
        # Verify access
        await service.get_task(task_id, current_user.id)
        
        # Get activities
        activities = await service.repository.get_task_activities(task_id, limit)
        
        # Build responses
        responses = []
        for activity in activities:
            response_data = {
                "id": activity.id,
                "action": activity.action,
                "old_value": activity.old_value,
                "new_value": activity.new_value,
                "comment": activity.comment,
                "created_at": activity.created_at,
                "user_id": activity.user_id,
            }
            
            if activity.user:
                response_data["user_username"] = activity.user.username
                response_data["user_full_name"] = activity.user.full_name
            
            responses.append(TaskActivityResponse(**response_data))
        
        return responses
        
    except TaskNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Task {task_id} not found",
        )
    except InsufficientTaskPermissionsError as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e),
        )


# ============= Special Views =============


@router.get(
    "/projects/{project_id}/tasks/board",
    response_model=TaskBoardResponse,
    summary="Get board view",
    description="Get tasks grouped by status (Kanban board view).",
)
async def get_task_board(
    project_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> TaskBoardResponse:
    """Get board view with tasks grouped by status."""
    service = TaskService(db)
    
    try:
        # Get all tasks (no pagination for board view)
        tasks, total = await service.get_project_tasks(
            project_id=project_id,
            user_id=current_user.id,
            filters={},
            skip=0,
            limit=1000,  # Board shows all tasks
        )
        
        # Get status counts
        counts = await service.repository.count_by_status(project_id)
        
        # Group by status
        grouped: dict[str, list[TaskResponse]] = {
            "todo": [],
            "in_progress": [],
            "in_review": [],
            "done": [],
            "cancelled": [],
        }
        
        for task in tasks:
            task_response = _build_task_response(task, check_blocked=True)
            if task.status in grouped:
                grouped[task.status].append(task_response)
        
        return TaskBoardResponse(
            todo=grouped["todo"],
            in_progress=grouped["in_progress"],
            in_review=grouped["in_review"],
            done=grouped["done"],
            cancelled=grouped["cancelled"],
            total=total,
            counts=counts,
        )
        
    except InsufficientTaskPermissionsError as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e),
        )


@router.get(
    "/projects/{project_id}/tasks/calendar",
    response_model=TaskCalendarResponse,
    summary="Get calendar view",
    description="Get tasks grouped by due date for calendar view.",
)
async def get_task_calendar(
    project_id: UUID,
    start_date: datetime | None = None,
    end_date: datetime | None = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> TaskCalendarResponse:
    """Get calendar view with tasks grouped by due date."""
    service = TaskService(db)
    
    try:
        # Default date range: 30 days back to 90 days forward
        if not start_date:
            start_date = datetime.utcnow() - timedelta(days=30)
        if not end_date:
            end_date = datetime.utcnow() + timedelta(days=90)
        
        # Get tasks with due dates in range
        filters = {
            "has_due_date": True,
            "sort_by": "due_date",
            "sort_order": "asc",
        }
        
        tasks, total = await service.get_project_tasks(
            project_id=project_id,
            user_id=current_user.id,
            filters=filters,
            skip=0,
            limit=1000,  # Calendar shows all in range
        )
        
        # Group by date
        tasks_by_date: dict[str, list[TaskResponse]] = defaultdict(list)
        
        for task in tasks:
            if task.due_date and start_date <= task.due_date <= end_date:
                date_key = task.due_date.date().isoformat()
                task_response = _build_task_response(task)
                tasks_by_date[date_key].append(task_response)
        
        return TaskCalendarResponse(
            tasks_by_date=dict(tasks_by_date),
            total=len([t for tasks in tasks_by_date.values() for t in tasks]),
            date_range_start=start_date,
            date_range_end=end_date,
        )
        
    except InsufficientTaskPermissionsError as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e),
        )


@router.get(
    "/projects/{project_id}/tasks/timeline",
    response_model=TaskTimelineResponse,
    summary="Get timeline view",
    description="Get tasks for timeline/Gantt chart view.",
)
async def get_task_timeline(
    project_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> TaskTimelineResponse:
    """Get timeline view with tasks and dependencies."""
    service = TaskService(db)
    
    try:
        # Get tasks with dependencies loaded
        filters = {
            "sort_by": "created_at",
            "sort_order": "asc",
        }
        
        tasks, total = await service.get_project_tasks(
            project_id=project_id,
            user_id=current_user.id,
            filters=filters,
            skip=0,
            limit=1000,  # Timeline shows all
        )
        
        # Build responses
        task_responses = [_build_task_response(task, check_blocked=True) for task in tasks]
        
        # Find date range
        earliest_date = None
        latest_date = None
        
        for task in tasks:
            if task.created_at:
                if not earliest_date or task.created_at < earliest_date:
                    earliest_date = task.created_at
            
            if task.due_date:
                if not latest_date or task.due_date > latest_date:
                    latest_date = task.due_date
            elif task.created_at:
                if not latest_date or task.created_at > latest_date:
                    latest_date = task.created_at
        
        return TaskTimelineResponse(
            tasks=task_responses,
            total=total,
            earliest_date=earliest_date,
            latest_date=latest_date,
        )
        
    except InsufficientTaskPermissionsError as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e),
        )