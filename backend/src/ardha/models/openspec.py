"""
OpenSpec Proposal model for AI-generated project specifications.

This module defines the OpenSpecProposal model for managing AI-generated
OpenSpec proposals with full lifecycle tracking from creation to archival.
"""

from datetime import datetime
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
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ardha.models.base import Base, BaseModel

if TYPE_CHECKING:
    from ardha.models.project import Project
    from ardha.models.task import Task
    from ardha.models.user import User


class OpenSpecProposal(BaseModel, Base):
    """
    OpenSpec Proposal model for AI-generated project specifications.

    Represents an OpenSpec proposal with full lifecycle management:
    - Creation and content storage
    - Approval workflow
    - Task synchronization
    - Archival and completion tracking

    Attributes:
        id: UUID primary key
        project_id: UUID of parent project
        name: Unique proposal name within project (e.g., 'user-auth-system')
        directory_path: Full path to proposal directory
        status: Current proposal status (pending, approved, etc.)
        created_by_user_id: UUID of user who created the proposal
        proposal_content: Content of proposal.md file
        tasks_content: Content of tasks.md file
        spec_delta_content: Content of spec-delta.md file
        metadata_json: Parsed metadata.json content
        approved_by_user_id: UUID of approver (nullable)
        approved_at: Timestamp of approval
        archived_at: Timestamp of archival
        completion_percentage: Progress percentage (0-100)
        task_sync_status: Status of task synchronization
        last_sync_at: Last synchronization timestamp
        sync_error_message: Error message from sync operation
        created_at: Creation timestamp
        updated_at: Last update timestamp
    """

    __tablename__ = "openspec_proposals"

    # ============= Core Fields =============

    project_id: Mapped[UUID] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="UUID of parent project",
    )

    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        comment="Unique proposal name within project",
    )

    directory_path: Mapped[str] = mapped_column(
        String(512),
        nullable=False,
        comment="Full path to proposal directory (e.g., openspec/changes/xxx)",
    )

    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="pending",
        index=True,
        comment="Proposal status: pending, approved, rejected, in_progress, " "completed, archived",
    )

    created_by_user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
        comment="UUID of user who created the proposal",
    )

    # ============= Content Fields =============

    proposal_content: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="Content of proposal.md file",
    )

    tasks_content: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="Content of tasks.md file",
    )

    spec_delta_content: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="Content of spec-delta.md file",
    )

    metadata_json: Mapped[dict | None] = mapped_column(
        JSONB,
        nullable=True,
        comment="Parsed metadata.json content",
    )

    # ============= Workflow Fields =============

    approved_by_user_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        comment="UUID of user who approved the proposal",
    )

    approved_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="Timestamp when proposal was approved",
    )

    archived_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="Timestamp when proposal was archived",
    )

    completion_percentage: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        comment="Progress percentage calculated from synced tasks (0-100)",
    )

    # ============= Tracking Fields =============

    task_sync_status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="not_synced",
        comment="Task sync status: not_synced, syncing, synced, sync_failed",
    )

    last_sync_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="Timestamp of last task synchronization",
    )

    sync_error_message: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="Error message from last sync operation",
    )

    # ============= Relationships =============

    project: Mapped["Project"] = relationship(
        "Project",
        back_populates="openspec_proposals",
    )

    created_by: Mapped["User"] = relationship(
        "User",
        foreign_keys=[created_by_user_id],
        back_populates="created_openspec_proposals",
    )

    approved_by: Mapped["User | None"] = relationship(
        "User",
        foreign_keys=[approved_by_user_id],
        back_populates="approved_openspec_proposals",
    )

    tasks: Mapped[list["Task"]] = relationship(
        "Task",
        back_populates="openspec_proposal",
        foreign_keys="[Task.openspec_proposal_id]",
    )

    # ============= Constraints =============

    __table_args__ = (
        UniqueConstraint("project_id", "name", name="uq_openspec_project_name"),
        Index("ix_openspec_project_status", "project_id", "status"),
        Index("ix_openspec_status", "status"),
        Index("ix_openspec_created_at", "created_at"),
        CheckConstraint(
            "status IN ('pending', 'approved', 'rejected', 'in_progress', "
            "'completed', 'archived')",
            name="ck_openspec_status",
        ),
        CheckConstraint(
            "task_sync_status IN ('not_synced', 'syncing', 'synced', " "'sync_failed')",
            name="ck_openspec_task_sync_status",
        ),
        CheckConstraint(
            "completion_percentage >= 0 AND completion_percentage <= 100",
            name="ck_openspec_completion_percentage",
        ),
    )

    # ============= Methods =============

    def __repr__(self) -> str:
        """String representation for debugging."""
        return (
            f"<OpenSpecProposal(id={self.id}, "
            f"name='{self.name}', "
            f"status='{self.status}', "
            f"project_id={self.project_id})>"
        )

    def to_dict(self) -> dict:
        """
        Serialize model to dictionary.

        Returns:
            Dictionary with all model fields
        """
        return {
            "id": str(self.id),
            "project_id": str(self.project_id),
            "name": self.name,
            "directory_path": self.directory_path,
            "status": self.status,
            "created_by_user_id": str(self.created_by_user_id),
            "proposal_content": self.proposal_content,
            "tasks_content": self.tasks_content,
            "spec_delta_content": self.spec_delta_content,
            "metadata_json": self.metadata_json,
            "approved_by_user_id": (
                str(self.approved_by_user_id) if self.approved_by_user_id else None
            ),
            "approved_at": (self.approved_at.isoformat() if self.approved_at else None),
            "archived_at": (self.archived_at.isoformat() if self.archived_at else None),
            "completion_percentage": self.completion_percentage,
            "task_sync_status": self.task_sync_status,
            "last_sync_at": (self.last_sync_at.isoformat() if self.last_sync_at else None),
            "sync_error_message": self.sync_error_message,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }

    @property
    def is_editable(self) -> bool:
        """
        Check if proposal can be edited.

        Returns:
            True if status is pending or rejected
        """
        return self.status in ("pending", "rejected")

    @property
    def can_approve(self) -> bool:
        """
        Check if proposal can be approved.

        Returns:
            True if status is pending
        """
        return self.status == "pending"

    def calculate_completion(self) -> int:
        """
        Calculate completion percentage from synced tasks.

        Returns:
            Percentage of completed tasks (0-100)
        """
        if not self.tasks:
            return 0

        completed_tasks = sum(1 for task in self.tasks if task.status == "done")
        total_tasks = len(self.tasks)

        if total_tasks == 0:
            return 0

        return int((completed_tasks / total_tasks) * 100)
