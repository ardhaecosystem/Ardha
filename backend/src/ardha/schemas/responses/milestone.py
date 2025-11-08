"""
Response schemas for milestone operations.

This module defines Pydantic models for formatting milestone-related API responses.
"""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, computed_field


class MilestoneResponse(BaseModel):
    """Response schema for milestone."""
    
    id: UUID
    project_id: UUID
    name: str
    description: str | None
    status: str
    color: str
    start_date: datetime | None
    due_date: datetime | None
    completed_at: datetime | None
    progress_percentage: int
    order: int
    created_at: datetime
    updated_at: datetime
    
    # Computed fields (optional, can be added by services)
    task_count: int | None = None
    is_overdue: bool | None = None
    days_remaining: int | None = None
    
    model_config = ConfigDict(from_attributes=True)


class MilestoneSummaryResponse(BaseModel):
    """Response schema for milestone summary with statistics."""
    
    milestone: MilestoneResponse
    task_stats: dict[str, int]  # {"todo": 5, "in_progress": 2, "done": 3, ...}
    total_tasks: int
    completed_tasks: int
    auto_progress: int  # Calculated progress based on task completion
    
    model_config = ConfigDict(from_attributes=True)


class MilestoneListResponse(BaseModel):
    """Response schema for paginated milestone list."""
    
    milestones: list[MilestoneResponse]
    total: int
    
    model_config = ConfigDict(from_attributes=True)