"""
Request schemas for notification operations.

This module defines Pydantic schemas for notification API requests,
including enums for notification types, link types, and email frequencies.
"""

from datetime import datetime, time
from enum import Enum
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field, field_validator

# ============= Enums =============


class NotificationType(str, Enum):
    """Valid notification types."""

    TASK_ASSIGNED = "task_assigned"
    TASK_COMPLETED = "task_completed"
    TASK_OVERDUE = "task_overdue"
    MENTION = "mention"
    PROJECT_INVITE = "project_invite"
    DATABASE_UPDATE = "database_update"
    SYSTEM = "system"


class LinkType(str, Enum):
    """Valid linked entity types."""

    TASK = "task"
    PROJECT = "project"
    DATABASE = "database"
    CHAT = "chat"


class EmailFrequency(str, Enum):
    """Valid email frequency options."""

    INSTANT = "instant"
    DAILY = "daily"
    WEEKLY = "weekly"
    NEVER = "never"


# ============= Request Schemas =============


class NotificationCreateRequest(BaseModel):
    """Request to create notification."""

    user_id: UUID = Field(..., description="User ID to send notification to")
    type: NotificationType = Field(..., description="Notification type")
    title: str = Field(
        ...,
        min_length=1,
        max_length=200,
        description="Notification title",
    )
    message: str = Field(
        ...,
        min_length=1,
        max_length=1000,
        description="Notification message",
    )
    data: dict[str, Any] | None = Field(
        None,
        description="Additional context data",
    )
    link_type: LinkType | None = Field(
        None,
        description="Type of linked entity",
    )
    link_id: UUID | None = Field(
        None,
        description="UUID of linked entity",
    )
    expires_at: datetime | None = Field(
        None,
        description="When notification should expire",
    )

    @field_validator("title")
    @classmethod
    def validate_title(cls, v: str) -> str:
        """Validate title is not empty or whitespace."""
        if not v.strip():
            raise ValueError("Title cannot be empty or whitespace")
        return v.strip()

    @field_validator("message")
    @classmethod
    def validate_message(cls, v: str) -> str:
        """Validate message is not empty or whitespace."""
        if not v.strip():
            raise ValueError("Message cannot be empty or whitespace")
        return v.strip()


class NotificationUpdateRequest(BaseModel):
    """Request to update notification (primarily for marking as read)."""

    is_read: bool | None = Field(
        None,
        description="Mark notification as read/unread",
    )


class NotificationPreferenceUpdateRequest(BaseModel):
    """Request to update notification preferences."""

    email_enabled: bool | None = Field(
        None,
        description="Enable email notifications globally",
    )
    push_enabled: bool | None = Field(
        None,
        description="Enable push notifications globally",
    )
    task_assigned: bool | None = Field(
        None,
        description="Notify when assigned to task",
    )
    task_completed: bool | None = Field(
        None,
        description="Notify when assigned task is completed",
    )
    task_overdue: bool | None = Field(
        None,
        description="Notify about overdue tasks",
    )
    mentions: bool | None = Field(
        None,
        description="Notify when mentioned in comments/chat",
    )
    project_invites: bool | None = Field(
        None,
        description="Notify when invited to project",
    )
    database_updates: bool | None = Field(
        None,
        description="Notify about database changes",
    )
    system_notifications: bool | None = Field(
        None,
        description="Notify about system announcements",
    )
    email_frequency: EmailFrequency | None = Field(
        None,
        description="Email digest frequency",
    )
    quiet_hours_start: time | None = Field(
        None,
        description="Start of quiet hours (no notifications)",
    )
    quiet_hours_end: time | None = Field(
        None,
        description="End of quiet hours",
    )


class BulkNotificationCreateRequest(BaseModel):
    """Request to create multiple notifications."""

    notifications: list[NotificationCreateRequest] = Field(
        ...,
        max_length=100,
        description="List of notifications to create (max 100)",
    )

    @field_validator("notifications")
    @classmethod
    def validate_notifications_not_empty(
        cls, v: list[NotificationCreateRequest]
    ) -> list[NotificationCreateRequest]:
        """Validate at least one notification provided."""
        if not v:
            raise ValueError("At least one notification required")
        return v
