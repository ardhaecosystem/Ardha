"""
Response schemas for notification operations.

This module defines Pydantic schemas for notification API responses,
including single notifications, lists, preferences, and statistics.
"""

from datetime import datetime, time
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


# ============= Response Schemas =============


class NotificationResponse(BaseModel):
    """Response for single notification."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID = Field(..., description="Notification ID")
    user_id: UUID = Field(..., description="User ID")
    type: str = Field(..., description="Notification type")
    title: str = Field(..., description="Notification title")
    message: str = Field(..., description="Notification message")
    data: dict[str, Any] | None = Field(None, description="Additional context")
    link_type: str | None = Field(None, description="Linked entity type")
    link_id: UUID | None = Field(None, description="Linked entity ID")
    is_read: bool = Field(..., description="Read status")
    read_at: datetime | None = Field(None, description="When marked as read")
    created_at: datetime = Field(..., description="When created")
    expires_at: datetime | None = Field(None, description="When expires")


class NotificationListResponse(BaseModel):
    """Response for notification list with pagination."""

    notifications: list[NotificationResponse] = Field(..., description="List of notifications")
    total: int = Field(..., description="Total count of notifications")
    unread_count: int = Field(..., description="Count of unread notifications")
    page: int = Field(..., description="Current page number")
    page_size: int = Field(..., description="Items per page")


class NotificationPreferenceResponse(BaseModel):
    """Response for notification preferences."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID = Field(..., description="Preference ID")
    user_id: UUID = Field(..., description="User ID")
    email_enabled: bool = Field(..., description="Email notifications enabled")
    push_enabled: bool = Field(..., description="Push notifications enabled")
    task_assigned: bool = Field(..., description="Task assigned notifications")
    task_completed: bool = Field(..., description="Task completed notifications")
    task_overdue: bool = Field(..., description="Task overdue notifications")
    mentions: bool = Field(..., description="Mention notifications")
    project_invites: bool = Field(..., description="Project invite notifications")
    database_updates: bool = Field(..., description="Database update notifications")
    system_notifications: bool = Field(..., description="System notifications")
    email_frequency: str = Field(..., description="Email digest frequency")
    quiet_hours_start: time | None = Field(None, description="Quiet hours start time")
    quiet_hours_end: time | None = Field(None, description="Quiet hours end time")
    created_at: datetime = Field(..., description="When created")
    updated_at: datetime = Field(..., description="When last updated")


class NotificationStatsResponse(BaseModel):
    """Response for notification statistics."""

    total_count: int = Field(..., description="Total notifications")
    unread_count: int = Field(..., description="Unread notifications")
    by_type: dict[str, int] = Field(..., description="Count of notifications by type")
    recent_notifications: list[NotificationResponse] = Field(
        ..., description="Recent notifications (max 5)"
    )
