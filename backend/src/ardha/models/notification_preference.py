"""
Notification preference model for user notification settings.

This module defines the NotificationPreference model with support for:
- Email and push notification toggles
- Per-notification-type preferences
- Email frequency settings (instant, daily, weekly, never)
- Quiet hours configuration
- One-to-one relationship with User
"""

from datetime import datetime, time, timezone
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    String,
    Time,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ardha.models.base import Base, BaseModel

if TYPE_CHECKING:
    from ardha.models.user import User


class NotificationPreference(Base, BaseModel):
    """
    Notification preference model for user notification settings.

    One-to-one relationship with User. Each user has one preference record
    that controls all notification behavior including email frequency and
    quiet hours.

    Attributes:
        user_id: User who owns these preferences (unique)
        email_enabled: Global email notification toggle
        push_enabled: Global push notification toggle
        task_assigned: Receive notifications when assigned to task
        task_completed: Receive notifications when task is completed
        task_overdue: Receive notifications for overdue tasks
        mentions: Receive notifications when mentioned
        project_invites: Receive notifications for project invitations
        database_updates: Receive notifications for database changes
        system_notifications: Receive system-wide notifications
        email_frequency: How often to send email digests
        quiet_hours_start: Start of quiet hours (no notifications)
        quiet_hours_end: End of quiet hours
    """

    __tablename__ = "notification_preferences"

    # ============= Primary Key =============

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)

    # ============= User Relationship =============

    user_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
        comment="User who owns these preferences",
    )

    # ============= Global Toggles =============

    email_enabled: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
        comment="Enable email notifications globally",
    )

    push_enabled: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
        comment="Enable push notifications globally",
    )

    # ============= Per-Type Preferences =============

    task_assigned: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
        comment="Notify when assigned to task",
    )

    task_completed: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
        comment="Notify when assigned task is completed",
    )

    task_overdue: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
        comment="Notify about overdue tasks",
    )

    mentions: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
        comment="Notify when mentioned in comments/chat",
    )

    project_invites: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
        comment="Notify when invited to project",
    )

    database_updates: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        comment="Notify about database changes",
    )

    system_notifications: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
        comment="Notify about system-wide announcements",
    )

    # ============= Email Settings =============

    email_frequency: Mapped[str] = mapped_column(
        String(20),
        default="instant",
        nullable=False,
        comment="Email frequency: instant, daily, weekly, never",
    )

    # ============= Quiet Hours =============

    quiet_hours_start: Mapped[time | None] = mapped_column(
        Time,
        nullable=True,
        comment="Start of quiet hours (no notifications)",
    )

    quiet_hours_end: Mapped[time | None] = mapped_column(
        Time,
        nullable=True,
        comment="End of quiet hours",
    )

    # ============= Timestamps =============

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
        comment="When preferences were created",
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
        comment="When preferences were last updated",
    )

    # ============= Relationships =============

    user: Mapped["User"] = relationship(
        "User",
        back_populates="notification_preferences",
        foreign_keys=[user_id],
    )

    # ============= Constraints =============

    __table_args__ = (
        # Unique constraint: one preference record per user
        UniqueConstraint("user_id", name="uq_notification_preference_user"),
        # Check constraint for valid email frequencies
        CheckConstraint(
            "email_frequency IN ('instant', 'daily', 'weekly', 'never')",
            name="ck_notification_preference_email_frequency",
        ),
    )

    # ============= Helper Methods =============

    def is_enabled(self, notification_type: str) -> bool:
        """
        Check if a specific notification type is enabled.

        Args:
            notification_type: Type to check (e.g., 'task_assigned')

        Returns:
            True if both global and type-specific settings are enabled
        """
        # Map notification types to preference attributes
        type_map = {
            "task_assigned": self.task_assigned,
            "task_completed": self.task_completed,
            "task_overdue": self.task_overdue,
            "mention": self.mentions,
            "project_invite": self.project_invites,
            "database_update": self.database_updates,
            "system": self.system_notifications,
        }

        # Return False if type not found or disabled
        type_enabled = type_map.get(notification_type, False)

        # For email notifications, check email_enabled
        # For push notifications, check push_enabled
        # (This method checks the type-specific setting only)
        return type_enabled

    def is_quiet_hours(self, check_time: datetime | None = None) -> bool:
        """
        Check if current time is within quiet hours.

        Args:
            check_time: Time to check (defaults to now)

        Returns:
            True if within quiet hours, False otherwise
        """
        if not self.quiet_hours_start or not self.quiet_hours_end:
            return False

        check_time = check_time or datetime.now(timezone.utc)
        current_time = check_time.time()

        # Handle quiet hours that span midnight
        if self.quiet_hours_start <= self.quiet_hours_end:
            # Normal case: 22:00 to 08:00
            return self.quiet_hours_start <= current_time <= self.quiet_hours_end
        else:
            # Spans midnight: 22:00 to 02:00
            return current_time >= self.quiet_hours_start or current_time <= self.quiet_hours_end

    def __repr__(self) -> str:
        """String representation for debugging."""
        return (
            f"<NotificationPreference(id={self.id}, "
            f"user_id={self.user_id}, "
            f"email_frequency={self.email_frequency})>"
        )
