"""
Notification model for user notifications.

This module defines the Notification model with support for:
- Multiple notification types (task, project, database, system)
- Read/unread status tracking
- Entity linking (tasks, projects, databases, chats)
- Optional expiration for temporary notifications
- Rich notification data with JSON metadata
"""

from datetime import datetime, timezone
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from sqlalchemy import Boolean, CheckConstraint, DateTime, ForeignKey, Index, String, Text
from sqlalchemy.dialects.postgresql import JSON
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ardha.models.base import Base, BaseModel

if TYPE_CHECKING:
    from ardha.models.user import User


class Notification(Base, BaseModel):
    """
    Notification model for user notifications.

    Stores notifications for users about various events in the system
    including task assignments, completions, mentions, and system alerts.

    Attributes:
        user_id: User who receives this notification
        type: Notification type (task_assigned, mention, etc.)
        title: Short notification title (max 200 chars)
        message: Main notification message (max 1000 chars)
        data: Optional JSON data for additional context
        link_type: Type of linked entity (task, project, database, chat)
        link_id: UUID of linked entity
        is_read: Whether notification has been read
        read_at: When notification was marked as read
        expires_at: Optional expiration timestamp
    """

    __tablename__ = "notifications"

    # ============= Primary Key =============

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)

    # ============= Ownership =============

    user_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="User who receives this notification",
    )

    # ============= Notification Content =============

    type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
        comment="Notification type: task_assigned, task_completed, etc.",
    )

    title: Mapped[str] = mapped_column(
        String(200),
        nullable=False,
        comment="Short notification title",
    )

    message: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        comment="Main notification message (max 1000 chars)",
    )

    data: Mapped[dict | None] = mapped_column(
        JSON,
        nullable=True,
        comment="Additional context data in JSON format",
    )

    # ============= Entity Linking =============

    link_type: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
        comment="Type of linked entity: task, project, database, chat",
    )

    link_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        nullable=True,
        comment="UUID of linked entity",
    )

    # ============= Status Tracking =============

    is_read: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        index=True,
        comment="Whether notification has been read",
    )

    read_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="When notification was marked as read",
    )

    # ============= Timestamps =============

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
        index=True,
        comment="When notification was created",
    )

    expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="When notification should be auto-deleted",
    )

    # updated_at inherited from BaseModel

    # ============= Relationships =============

    user: Mapped["User"] = relationship(
        "User",
        back_populates="notifications",
        foreign_keys=[user_id],
    )

    # ============= Constraints =============

    __table_args__ = (
        # Composite index for efficient user queries
        Index(
            "ix_notifications_user_read_created",
            "user_id",
            "is_read",
            "created_at",
        ),
        # Check constraint for valid notification types
        CheckConstraint(
            "type IN ('task_assigned', 'task_completed', 'task_overdue', "
            "'mention', 'project_invite', 'database_update', 'system')",
            name="ck_notification_type",
        ),
        # Check constraint for valid link types
        CheckConstraint(
            "link_type IS NULL OR link_type IN ('task', 'project', " "'database', 'chat')",
            name="ck_notification_link_type",
        ),
        # Check constraint for message length
        CheckConstraint(
            "length(message) <= 1000",
            name="ck_notification_message_length",
        ),
    )

    # ============= Helper Methods =============

    def mark_as_read(self) -> None:
        """Mark notification as read with current timestamp."""
        self.is_read = True
        self.read_at = datetime.now(timezone.utc)

    def is_expired(self) -> bool:
        """
        Check if notification is expired.

        Returns:
            True if expires_at is set and has passed, False otherwise
        """
        if not self.expires_at:
            return False
        return datetime.now(timezone.utc) > self.expires_at

    def __repr__(self) -> str:
        """String representation for debugging."""
        return (
            f"<Notification(id={self.id}, "
            f"type={self.type}, "
            f"user_id={self.user_id}, "
            f"is_read={self.is_read})>"
        )
