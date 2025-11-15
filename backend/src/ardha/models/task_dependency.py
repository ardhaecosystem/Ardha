"""
TaskDependency model for task dependencies.

This module defines self-referential relationships between tasks,
allowing tasks to depend on other tasks (blocking/depends_on).
"""

from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from sqlalchemy import ForeignKey, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ardha.models.base import Base, BaseModel

if TYPE_CHECKING:
    from ardha.models.task import Task


class TaskDependency(Base, BaseModel):
    """
    Task dependency model for self-referential task relationships.

    Represents a dependency between two tasks:
    - task_id: The task that has the dependency
    - depends_on_task_id: The task that must be completed first

    Example:
        Task A depends on Task B → Task B must be completed before Task A can start
        Task B blocks Task A → Task A is blocked until Task B is complete
    """

    __tablename__ = "task_dependencies"

    # ============= Primary Fields =============

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)

    task_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("tasks.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="The task that has the dependency",
    )

    depends_on_task_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("tasks.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="The task that must be completed first",
    )

    dependency_type: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="depends_on",
        comment="Type: blocks or depends_on",
    )

    # created_at inherited from BaseModel

    # ============= Relationships =============

    # The task that has the dependency
    task: Mapped["Task"] = relationship(
        "Task",
        foreign_keys=[task_id],
        back_populates="dependencies",
    )

    # The task that must be completed first
    depends_on_task: Mapped["Task"] = relationship(
        "Task",
        foreign_keys=[depends_on_task_id],
        back_populates="blocking",
    )

    # ============= Constraints =============

    __table_args__ = (
        # Prevent duplicate dependencies
        UniqueConstraint(
            "task_id",
            "depends_on_task_id",
            name="uq_task_dependency_task_depends_on",
        ),
    )

    def __repr__(self) -> str:
        """String representation of TaskDependency."""
        return f"<TaskDependency(task_id={self.task_id}, depends_on={self.depends_on_task_id})>"
