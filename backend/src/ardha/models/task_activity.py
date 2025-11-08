"""
TaskActivity model for audit logging.

This module defines the activity/audit log for all task changes,
allowing full history tracking of task modifications.
"""

from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ardha.models.base import Base, BaseModel

if TYPE_CHECKING:
    from ardha.models.task import Task
    from ardha.models.user import User


class TaskActivity(Base, BaseModel):
    """
    Task activity model for comprehensive audit logging.
    
    Tracks all changes to tasks including:
    - Status changes
    - Assignment changes
    - Field updates
    - Comments
    - Git commit linking
    - Dependency changes
    
    This provides a complete history of task evolution for:
    - Accountability (who changed what when)
    - Debugging (why did this task change?)
    - Metrics (how long in each status?)
    - AI learning (what patterns lead to success?)
    """
    
    __tablename__ = "task_activities"
    
    # ============= Primary Fields =============
    
    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    
    task_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("tasks.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    
    user_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        comment="User who performed this action (null if AI)",
    )
    
    action: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        comment="Action type (e.g., 'created', 'status_changed', 'assigned')",
    )
    
    old_value: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="Previous value (JSON string for complex types)",
    )
    
    new_value: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="New value (JSON string for complex types)",
    )
    
    comment: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="Optional user comment explaining the change",
    )
    
    # created_at inherited from BaseModel
    
    # ============= Relationships =============
    
    # Many-to-one: Task relationship
    task: Mapped["Task"] = relationship(
        "Task",
        back_populates="activities",
    )
    
    # Many-to-one: User relationship
    user: Mapped["User | None"] = relationship(
        "User",
        back_populates="task_activities",
    )
    
    def __repr__(self) -> str:
        """String representation of TaskActivity."""
        return f"<TaskActivity(task_id={self.task_id}, action={self.action})>"


# Common activity action types (for reference):
ACTIVITY_ACTIONS = {
    "created": "Task created",
    "status_changed": "Status updated",
    "assigned": "Assignee added",
    "unassigned": "Assignee removed",
    "title_changed": "Title updated",
    "description_changed": "Description updated",
    "priority_changed": "Priority updated",
    "estimate_changed": "Time estimate updated",
    "due_date_changed": "Due date updated",
    "dependency_added": "Dependency added",
    "dependency_removed": "Dependency removed",
    "tag_added": "Tag added",
    "tag_removed": "Tag removed",
    "commented": "User comment added",
    "git_commit_linked": "Git commit associated",
    "openspec_linked": "OpenSpec proposal linked",
}