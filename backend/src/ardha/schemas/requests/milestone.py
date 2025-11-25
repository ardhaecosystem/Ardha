"""
Request schemas for milestone operations.

This module defines Pydantic models for validating milestone-related API requests.
"""

from datetime import datetime

from pydantic import BaseModel, Field, field_validator


class MilestoneCreateRequest(BaseModel):
    """Request schema for creating a milestone."""

    name: str = Field(..., min_length=1, max_length=255, description="Milestone display name")
    description: str | None = Field(None, description="Optional detailed description")
    status: str = Field(
        default="not_started",
        pattern="^(not_started|in_progress|completed|cancelled)$",
        description="Milestone status",
    )
    color: str = Field(
        default="#3b82f6", pattern="^#[0-9A-Fa-f]{6}$", description="Hex color code (e.g., #3b82f6)"
    )
    start_date: datetime | None = Field(None, description="Optional start date")
    due_date: datetime | None = Field(None, description="Optional target completion date")
    order: int | None = Field(
        None, ge=0, description="Display order (auto-assigned if not provided)"
    )

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        """Validate milestone name is not empty."""
        if not v.strip():
            raise ValueError("Milestone name cannot be empty or whitespace only")
        return v.strip()

    @field_validator("due_date")
    @classmethod
    def validate_due_date(cls, v: datetime | None, info) -> datetime | None:
        """Validate due_date is after start_date if both are provided."""
        if v and info.data.get("start_date"):
            if v < info.data["start_date"]:
                raise ValueError("Due date must be after start date")
        return v


class MilestoneUpdateRequest(BaseModel):
    """Request schema for updating a milestone (all fields optional)."""

    name: str | None = Field(
        None, min_length=1, max_length=255, description="Milestone display name"
    )
    description: str | None = Field(None, description="Optional detailed description")
    status: str | None = Field(
        None,
        pattern="^(not_started|in_progress|completed|cancelled)$",
        description="Milestone status",
    )
    color: str | None = Field(None, pattern="^#[0-9A-Fa-f]{6}$", description="Hex color code")
    start_date: datetime | None = Field(None, description="Optional start date")
    due_date: datetime | None = Field(None, description="Optional target completion date")
    progress_percentage: int | None = Field(None, ge=0, le=100, description="Progress 0-100")
    order: int | None = Field(None, ge=0, description="Display order")

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str | None) -> str | None:
        """Validate milestone name is not empty if provided."""
        if v is not None and not v.strip():
            raise ValueError("Milestone name cannot be empty or whitespace only")
        return v.strip() if v else None


class MilestoneStatusUpdateRequest(BaseModel):
    """Request schema for updating milestone status."""

    status: str = Field(
        ..., pattern="^(not_started|in_progress|completed|cancelled)$", description="New status"
    )


class MilestoneProgressUpdateRequest(BaseModel):
    """Request schema for updating milestone progress."""

    progress_percentage: int = Field(..., ge=0, le=100, description="Progress 0-100")


class MilestoneReorderRequest(BaseModel):
    """Request schema for reordering a milestone."""

    new_order: int = Field(..., ge=0, description="New order value")
