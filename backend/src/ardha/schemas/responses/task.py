"""
Response schemas for task operations.

This module defines Pydantic models for task-related API responses with
nested data structures for tags, dependencies, and activities.
"""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, computed_field


class TaskTagResponse(BaseModel):
    """Response model for task tag."""

    id: UUID
    name: str
    color: str

    model_config = ConfigDict(from_attributes=True)


class TaskDependencyResponse(BaseModel):
    """Response model for task dependency with related task info."""

    id: UUID
    task_id: UUID
    depends_on_task_id: UUID
    depends_on_task_identifier: str | None = None
    depends_on_task_title: str | None = None
    depends_on_task_status: str | None = None

    model_config = ConfigDict(from_attributes=True)


class TaskActivityResponse(BaseModel):
    """Response model for task activity log entry."""

    id: UUID
    action: str
    old_value: str | None
    new_value: str | None
    comment: str | None
    created_at: datetime
    user_id: UUID | None
    user_username: str | None = None
    user_full_name: str | None = None

    model_config = ConfigDict(from_attributes=True)


class TaskResponse(BaseModel):
    """
    Response model for task with all related data.

    Includes:
    - All task fields
    - Assignee and creator info
    - Tags
    - Dependencies
    - Computed fields (is_blocked)
    """

    # Identity
    id: UUID
    project_id: UUID
    identifier: str

    # Core fields
    title: str
    description: str | None
    status: str

    # Assignment
    assignee_id: UUID | None
    assignee_username: str | None = None
    assignee_full_name: str | None = None
    created_by_id: UUID
    created_by_username: str | None = None
    created_by_full_name: str | None = None

    # Organization
    phase: str | None
    milestone_id: UUID | None
    epic: str | None

    # Estimation
    estimate_hours: float | None
    actual_hours: float | None
    complexity: str | None
    priority: str

    # OpenSpec
    openspec_change_path: str | None

    # AI metadata
    ai_generated: bool
    ai_confidence: float | None

    # Related items
    related_commits: list[str]
    related_prs: list[str]
    related_files: list[str]

    # Timestamps
    due_date: datetime | None
    started_at: datetime | None
    completed_at: datetime | None
    created_at: datetime
    updated_at: datetime

    # Relationships (will be populated by API layer)
    tags: list[TaskTagResponse] = []
    dependencies: list[TaskDependencyResponse] = []
    blocking: list[TaskDependencyResponse] = []
    is_blocked: bool = False  # Computed: has incomplete dependencies

    model_config = ConfigDict(from_attributes=True)


class TaskListResponse(BaseModel):
    """Response model for paginated task list."""

    tasks: list[TaskResponse]
    total: int
    skip: int = 0
    limit: int = 100
    status_counts: dict[str, int] = {}  # Count per status for board view

    model_config = ConfigDict(from_attributes=True)


class TaskBoardResponse(BaseModel):
    """
    Response model for board view.

    Groups tasks by status with counts for each column.
    """

    todo: list[TaskResponse] = []
    in_progress: list[TaskResponse] = []
    in_review: list[TaskResponse] = []
    done: list[TaskResponse] = []
    cancelled: list[TaskResponse] = []

    total: int
    counts: dict[str, int]  # Per-status counts


class TaskCalendarResponse(BaseModel):
    """Response model for calendar view (tasks grouped by date)."""

    tasks_by_date: dict[str, list[TaskResponse]]  # ISO date string -> tasks
    total: int
    date_range_start: datetime
    date_range_end: datetime


class TaskTimelineResponse(BaseModel):
    """
    Response model for timeline/Gantt view.

    Includes tasks with dates and dependencies for timeline visualization.
    """

    tasks: list[TaskResponse]
    total: int
    earliest_date: datetime | None
    latest_date: datetime | None
