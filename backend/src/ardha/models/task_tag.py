"""
TaskTag model for task categorization.

This module defines tags that can be applied to tasks for
flexible categorization and filtering.
"""

from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from sqlalchemy import ForeignKey, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ardha.models.base import Base, BaseModel

if TYPE_CHECKING:
    from ardha.models.project import Project
    from ardha.models.task import Task


class TaskTag(Base, BaseModel):
    """
    Task tag model for flexible task categorization.
    
    Tags are project-specific and can be used to categorize tasks
    by feature, technology, priority, or any custom criteria.
    
    Examples:
        - backend, frontend, database
        - bug, feature, enhancement
        - high-priority, needs-review
        - sprint-1, sprint-2
    """
    
    __tablename__ = "task_tags"
    
    # ============= Primary Fields =============
    
    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    
    project_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    
    name: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        comment="Tag name (e.g., 'backend', 'high-priority')",
    )
    
    color: Mapped[str] = mapped_column(
        String(7),
        nullable=False,
        default="#6366f1",  # Purple (Ardha brand color)
        comment="Hex color code for UI display",
    )
    
    # created_at inherited from BaseModel
    
    # ============= Relationships =============
    
    # Many-to-one: Project relationship
    project: Mapped["Project"] = relationship(
        "Project",
        back_populates="task_tags",
    )
    
    # Many-to-many: Tasks relationship
    tasks: Mapped[list["Task"]] = relationship(
        "Task",
        secondary="task_task_tags",
        back_populates="tags",
    )
    
    # ============= Constraints =============
    
    __table_args__ = (
        # Tag names must be unique within a project
        UniqueConstraint(
            "project_id",
            "name",
            name="uq_task_tag_project_name",
        ),
    )
    
    def __repr__(self) -> str:
        """String representation of TaskTag."""
        return f"<TaskTag(name={self.name}, color={self.color})>"