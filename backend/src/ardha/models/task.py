"""
Task model for project work management.

This module defines the Task model with support for:
- Status tracking (todo, in_progress, in_review, done, cancelled)
- Assignment and time estimation
- OpenSpec integration
- AI-generated metadata
- Git commit linking
- Dependencies and tags (via relationships)
"""

from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Index,
    String,
    Table,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ardha.models.base import Base, BaseModel

if TYPE_CHECKING:
    from ardha.models.git_commit import GitCommit
    from ardha.models.milestone import Milestone
    from ardha.models.openspec import OpenSpecProposal
    from ardha.models.project import Project
    from ardha.models.task_activity import TaskActivity
    from ardha.models.task_dependency import TaskDependency
    from ardha.models.task_tag import TaskTag
    from ardha.models.user import User


# Association table for task-tag many-to-many relationship
task_task_tags = Table(
    "task_task_tags",
    Base.metadata,
    Column(
        "task_id",
        PG_UUID(as_uuid=True),
        ForeignKey("tasks.id", ondelete="CASCADE"),
        primary_key=True,
    ),
    Column(
        "tag_id",
        PG_UUID(as_uuid=True),
        ForeignKey("task_tags.id", ondelete="CASCADE"),
        primary_key=True,
    ),
)


class Task(Base, BaseModel):
    """
    Task model for project work management.

    Tasks are the fundamental unit of work in Ardha, supporting:
    - Flexible status workflow (todo → in_progress → in_review → done)
    - Time estimation and tracking
    - Priority and complexity levels
    - Dependencies between tasks
    - OpenSpec proposal integration
    - AI-generated task metadata
    - Git commit linking
    - Rich activity logging
    """

    __tablename__ = "tasks"

    # ============= Identity & Organization =============

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)

    project_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    identifier: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
        comment="Auto-generated unique identifier like ARD-001, ARD-002",
    )

    title: Mapped[str] = mapped_column(String(500), nullable=False)

    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    # ============= Status & Assignment =============

    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="todo",
        index=True,
        comment="Task status: todo, in_progress, in_review, done, cancelled",
    )

    assignee_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    created_by_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
        comment="User or AI that created this task",
    )

    # ============= Organization Hierarchy =============

    phase: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
        comment="Development phase (e.g., 'Phase 1: Backend')",
    )

    milestone_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("milestones.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    epic: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        comment="Epic/theme for grouping large features",
    )

    # ============= Estimation & Priority =============

    estimate_hours: Mapped[float | None] = mapped_column(Float, nullable=True)

    actual_hours: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
        comment="Tracked time spent on task",
    )

    complexity: Mapped[str | None] = mapped_column(
        String(20),
        nullable=True,
        comment="Complexity: trivial, simple, medium, complex, very_complex",
    )

    priority: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="medium",
        index=True,
        comment="Priority: urgent, high, medium, low",
    )

    # ============= OpenSpec Integration =============

    openspec_proposal_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("openspec_proposals.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        comment="Linked OpenSpec proposal",
    )

    openspec_change_path: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
        comment="Path to openspec/changes/xxx/ directory",
    )

    # ============= AI Metadata =============

    ai_generated: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        comment="Was this task created by AI?",
    )

    ai_confidence: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
        comment="AI confidence score (0.0-1.0)",
    )

    ai_reasoning: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="AI's reasoning for creating this task",
    )

    # ============= Related Items (JSON Arrays) =============

    related_commit_shas: Mapped[list[str]] = mapped_column(
        ARRAY(String),
        nullable=False,
        default=list,
        server_default="{}",
        comment="Array of git commit SHAs (legacy, use related_commits relationship)",
    )

    related_prs: Mapped[list[str]] = mapped_column(
        ARRAY(String),
        nullable=False,
        default=list,
        server_default="{}",
        comment="Array of pull request URLs",
    )

    related_files: Mapped[list[str]] = mapped_column(
        ARRAY(String),
        nullable=False,
        default=list,
        server_default="{}",
        comment="Array of file paths modified by this task",
    )

    # ============= Timestamps =============

    due_date: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="When status changed to in_progress",
    )

    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="When status changed to done",
    )

    # created_at and updated_at inherited from BaseModel

    # ============= Relationships =============

    # Many-to-one: Project relationship
    project: Mapped["Project"] = relationship(
        "Project",
        back_populates="tasks",
    )

    # Many-to-one: Assignee relationship
    assignee: Mapped["User | None"] = relationship(
        "User",
        foreign_keys=[assignee_id],
        back_populates="assigned_tasks",
    )

    # Many-to-one: Creator relationship
    created_by: Mapped["User"] = relationship(
        "User",
        foreign_keys=[created_by_id],
        back_populates="created_tasks",
    )

    # Many-to-many: Tags relationship
    tags: Mapped[list["TaskTag"]] = relationship(
        "TaskTag",
        secondary=task_task_tags,
        back_populates="tasks",
    )

    # Self-referential: Task dependencies (tasks this task depends on)
    dependencies: Mapped[list["TaskDependency"]] = relationship(
        "TaskDependency",
        foreign_keys="TaskDependency.task_id",
        back_populates="task",
        cascade="all, delete-orphan",
    )

    # Self-referential: Tasks blocked by this task
    blocking: Mapped[list["TaskDependency"]] = relationship(
        "TaskDependency",
        foreign_keys="TaskDependency.depends_on_task_id",
        back_populates="depends_on_task",
        cascade="all, delete-orphan",
    )

    # One-to-many: Activity log
    activities: Mapped[list["TaskActivity"]] = relationship(
        "TaskActivity",
        back_populates="task",
        cascade="all, delete-orphan",
        order_by="desc(TaskActivity.created_at)",
    )

    # Many-to-one: Milestone relationship
    milestone: Mapped["Milestone | None"] = relationship(
        "Milestone",
        back_populates="tasks",
    )

    # Many-to-one: OpenSpec Proposal relationship
    openspec_proposal: Mapped["OpenSpecProposal | None"] = relationship(
        "OpenSpecProposal",
        back_populates="tasks",
        foreign_keys=[openspec_proposal_id],
    )

    # Many-to-many: Git commits relationship
    related_commits: Mapped[list["GitCommit"]] = relationship(
        "GitCommit",
        secondary="task_commits",
        back_populates="linked_tasks",
    )

    # ============= Constraints =============

    __table_args__ = (
        # Unique identifier within project
        UniqueConstraint("project_id", "identifier", name="uq_task_project_identifier"),
        # Index for common queries
        Index("ix_task_status_priority", "status", "priority"),
        Index("ix_task_due_date", "due_date"),
        # Check constraints for enums
        CheckConstraint(
            "status IN ('todo', 'in_progress', 'in_review', 'done', 'cancelled')",
            name="ck_task_status",
        ),
        CheckConstraint(
            "priority IN ('urgent', 'high', 'medium', 'low')",
            name="ck_task_priority",
        ),
        CheckConstraint(
            "complexity IS NULL OR complexity IN ('trivial', 'simple', 'medium', 'complex', 'very_complex')",
            name="ck_task_complexity",
        ),
        CheckConstraint(
            "estimate_hours IS NULL OR estimate_hours >= 0",
            name="ck_task_estimate_hours",
        ),
        CheckConstraint(
            "actual_hours IS NULL OR actual_hours >= 0",
            name="ck_task_actual_hours",
        ),
        CheckConstraint(
            "ai_confidence IS NULL OR (ai_confidence >= 0 AND "
            "ai_confidence <= 1)",
            name="ck_task_ai_confidence",
        ),
    )

    def __repr__(self) -> str:
        """String representation of Task."""
        return (
            f"<Task(id={self.id}, identifier={self.identifier}, "
            f"title={self.title[:50]}, status={self.status})>"
        )
