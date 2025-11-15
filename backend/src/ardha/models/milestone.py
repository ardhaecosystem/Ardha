"""
Milestone model for the Ardha application.

This module defines the Milestone model representing major goals or releases
within a project. Milestones group related tasks together with target dates.
"""

from datetime import datetime, timezone
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ardha.models.base import Base, BaseModel

if TYPE_CHECKING:
    from ardha.models.project import Project
    from ardha.models.task import Task


class Milestone(BaseModel, Base):
    """
    Milestone model representing a major goal or release within a project.

    Milestones help organize tasks into phases or releases, providing a roadmap
    view of project progress. They support flexible date tracking, progress
    calculation, and drag-drop ordering.

    Attributes:
        project_id: Foreign key to the project
        name: Milestone display name (e.g., "Phase 1: Backend", "MVP Release")
        description: Optional detailed description
        status: Current status (not_started, in_progress, completed, cancelled)
        color: Hex color code for UI display (default: blue #3b82f6)
        start_date: Optional start date
        due_date: Optional target completion date
        completed_at: Timestamp when status changed to completed
        progress_percentage: Calculated progress 0-100 based on task completion
        order: Display order for drag-drop sorting (unique per project)
        project: Relationship to parent Project
        tasks: Relationship to linked Task objects
    """

    __tablename__ = "milestones"

    # ============= Identity & Organization =============

    project_id: Mapped[UUID] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Foreign key to owning project",
    )

    name: Mapped[str] = mapped_column(String(255), nullable=False, comment="Milestone display name")

    description: Mapped[str | None] = mapped_column(
        Text, nullable=True, comment="Optional detailed description"
    )

    # ============= Status & Progress =============

    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="not_started",
        index=True,
        comment="Status: not_started, in_progress, completed, cancelled",
    )

    color: Mapped[str] = mapped_column(
        String(7),
        nullable=False,
        default="#3b82f6",
        comment="Hex color code for UI display (e.g., #3b82f6)",
    )

    progress_percentage: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        comment="Progress 0-100, calculated from task completion",
    )

    # ============= Dates =============

    start_date: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, comment="Optional start date"
    )

    due_date: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        index=True,
        comment="Optional target completion date",
    )

    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, comment="Timestamp when status changed to completed"
    )

    # ============= Ordering =============

    order: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        comment="Display order for drag-drop sorting (auto-assigned on creation)",
    )

    # created_at and updated_at inherited from BaseModel

    # ============= Relationships =============

    # Many-to-one: Project relationship
    project: Mapped["Project"] = relationship(
        "Project",
        back_populates="milestones",
    )

    # One-to-many: Tasks relationship
    tasks: Mapped[list["Task"]] = relationship(
        "Task",
        back_populates="milestone",
        foreign_keys="Task.milestone_id",
    )

    # ============= Constraints & Indexes =============

    __table_args__ = (
        # Index for ordering queries (no unique constraint to allow flexibility)
        Index("ix_milestone_project_order", "project_id", "order"),
        # Index for timeline queries
        Index("ix_milestone_due_date", "due_date"),
        # Check constraints for data validation
        CheckConstraint(
            "status IN ('not_started', 'in_progress', 'completed', 'cancelled')",
            name="ck_milestone_status",
        ),
        CheckConstraint(
            "progress_percentage >= 0 AND progress_percentage <= 100", name="ck_milestone_progress"
        ),
        CheckConstraint("color ~ '^#[0-9A-Fa-f]{6}$'", name="ck_milestone_color"),
        CheckConstraint('"order" >= 0', name="ck_milestone_order"),
    )

    # ============= Computed Properties =============

    @property
    def is_overdue(self) -> bool:
        """
        Check if milestone is overdue.

        Returns False if:
        - Status is completed or cancelled
        - No due date set

        Returns:
            True if milestone is past due date, False otherwise
        """
        if self.status in ["completed", "cancelled"]:
            return False
        if not self.due_date:
            return False
        return datetime.now(timezone.utc) > self.due_date

    @property
    def days_remaining(self) -> int | None:
        """
        Calculate days until due date.

        Returns None if:
        - Status is completed or cancelled
        - No due date set

        Returns:
            Number of days remaining (0 if overdue), or None
        """
        if not self.due_date or self.status in ["completed", "cancelled"]:
            return None

        delta = self.due_date - datetime.now(timezone.utc)
        return max(0, delta.days)

    def __repr__(self) -> str:
        """String representation of Milestone."""
        return (
            f"<Milestone(id={self.id}, "
            f"name='{self.name}', "
            f"status={self.status}, "
            f"progress={self.progress_percentage}%)>"
        )
