"""
Request schemas for task operations.

This module defines Pydantic models for task-related API requests with
comprehensive validation rules.
"""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field, field_validator


class TaskCreateRequest(BaseModel):
    """
    Request model for task creation.
    
    Validates:
    - Title length and non-empty
    - Valid status enum
    - Valid complexity enum
    - Valid priority enum
    - Non-negative time estimates
    - Due date in future
    """
    
    title: str = Field(
        ...,
        min_length=1,
        max_length=500,
        description="Task title",
    )
    
    description: str | None = Field(
        None,
        description="Detailed task description",
    )
    
    status: str = Field(
        default="todo",
        pattern="^(todo|in_progress|in_review|done|cancelled)$",
        description="Task status",
    )
    
    assignee_id: UUID | None = Field(
        None,
        description="User to assign task to",
    )
    
    phase: str | None = Field(
        None,
        max_length=100,
        description="Development phase (e.g., 'Phase 1: Backend')",
    )
    
    milestone_id: UUID | None = Field(
        None,
        description="Milestone this task belongs to",
    )
    
    epic: str | None = Field(
        None,
        max_length=255,
        description="Epic/theme for grouping",
    )
    
    estimate_hours: float | None = Field(
        None,
        ge=0,
        description="Estimated hours to complete",
    )
    
    complexity: str | None = Field(
        None,
        pattern="^(trivial|simple|medium|complex|very_complex)$",
        description="Task complexity level",
    )
    
    priority: str = Field(
        default="medium",
        pattern="^(urgent|high|medium|low)$",
        description="Task priority",
    )
    
    due_date: datetime | None = Field(
        None,
        description="Task due date",
    )
    
    tags: list[str] = Field(
        default_factory=list,
        description="Tag names to apply to task",
    )
    
    depends_on: list[UUID] = Field(
        default_factory=list,
        description="Task IDs this task depends on",
    )
    
    openspec_change_path: str | None = Field(
        None,
        max_length=500,
        description="Path to OpenSpec change directory",
    )
    
    ai_generated: bool = Field(
        default=False,
        description="Was this task created by AI?",
    )
    
    ai_confidence: float | None = Field(
        None,
        ge=0.0,
        le=1.0,
        description="AI confidence score",
    )
    
    ai_reasoning: str | None = Field(
        None,
        description="AI reasoning for task creation",
    )
    
    @field_validator("title")
    @classmethod
    def validate_title(cls, v: str) -> str:
        """Ensure title is not just whitespace."""
        if not v or not v.strip():
            raise ValueError("Title cannot be empty or whitespace only")
        return v.strip()
    
    @field_validator("tags")
    @classmethod
    def validate_tags(cls, v: list[str]) -> list[str]:
        """Clean and validate tag names."""
        cleaned = []
        for tag in v:
            tag_clean = tag.strip().lower()
            if tag_clean and tag_clean not in cleaned:
                cleaned.append(tag_clean)
        return cleaned


class TaskUpdateRequest(BaseModel):
    """
    Request model for task updates.
    
    All fields are optional for partial updates.
    """
    
    title: str | None = Field(
        None,
        min_length=1,
        max_length=500,
    )
    
    description: str | None = None
    
    status: str | None = Field(
        None,
        pattern="^(todo|in_progress|in_review|done|cancelled)$",
    )
    
    assignee_id: UUID | None = None
    
    phase: str | None = Field(None, max_length=100)
    
    milestone_id: UUID | None = None
    
    epic: str | None = Field(None, max_length=255)
    
    estimate_hours: float | None = Field(None, ge=0)
    
    actual_hours: float | None = Field(None, ge=0)
    
    complexity: str | None = Field(
        None,
        pattern="^(trivial|simple|medium|complex|very_complex)$",
    )
    
    priority: str | None = Field(
        None,
        pattern="^(urgent|high|medium|low)$",
    )
    
    due_date: datetime | None = None
    
    @field_validator("title")
    @classmethod
    def validate_title(cls, v: str | None) -> str | None:
        """Ensure title is not just whitespace if provided."""
        if v is not None:
            if not v.strip():
                raise ValueError("Title cannot be empty or whitespace only")
            return v.strip()
        return v


class TaskFilterRequest(BaseModel):
    """
    Query parameters for filtering tasks.
    
    Supports multiple filter criteria that can be combined.
    """
    
    status: list[str] | None = Field(
        None,
        description="Filter by status values",
    )
    
    assignee_id: UUID | None = Field(
        None,
        description="Filter by assignee",
    )
    
    priority: list[str] | None = Field(
        None,
        description="Filter by priority values",
    )
    
    milestone_id: UUID | None = Field(
        None,
        description="Filter by milestone",
    )
    
    has_due_date: bool | None = Field(
        None,
        description="Filter tasks with/without due dates",
    )
    
    overdue_only: bool = Field(
        default=False,
        description="Show only overdue tasks",
    )
    
    tags: list[str] | None = Field(
        None,
        description="Filter by tag names",
    )
    
    search: str | None = Field(
        None,
        description="Search in title/description/identifier",
    )
    
    sort_by: str = Field(
        default="created_at",
        pattern="^(created_at|due_date|priority|status|updated_at)$",
        description="Sort field",
    )
    
    sort_order: str = Field(
        default="desc",
        pattern="^(asc|desc)$",
        description="Sort direction",
    )


class TaskStatusUpdateRequest(BaseModel):
    """Request model for updating task status."""
    
    status: str = Field(
        ...,
        pattern="^(todo|in_progress|in_review|done|cancelled)$",
        description="New status value",
    )


class TaskAssignRequest(BaseModel):
    """Request model for assigning a task."""
    
    assignee_id: UUID = Field(
        ...,
        description="User ID to assign task to",
    )


class TaskDependencyRequest(BaseModel):
    """Request model for adding task dependency."""
    
    depends_on_task_id: UUID = Field(
        ...,
        description="Task ID that this task depends on",
    )


class TaskTagRequest(BaseModel):
    """Request model for adding tag to task."""
    
    name: str = Field(
        ...,
        min_length=1,
        max_length=50,
        description="Tag name",
    )
    
    color: str = Field(
        default="#6366f1",
        pattern="^#[0-9a-fA-F]{6}$",
        description="Hex color code",
    )
    
    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        """Clean and validate tag name."""
        cleaned = v.strip().lower()
        if not cleaned:
            raise ValueError("Tag name cannot be empty")
        return cleaned