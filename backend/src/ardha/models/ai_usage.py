"""
AI Usage model for Ardha application.

This module defines the AIUsage model for tracking AI operations and costs.
Provides analytics for token usage, costs, and operation types across users and projects.
"""

from datetime import date, datetime
from decimal import Decimal
from enum import Enum
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import Date, ForeignKey, Index, Integer, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ardha.models.base import Base, BaseModel

if TYPE_CHECKING:
    from ardha.models.project import Project
    from ardha.models.user import User


class AIOperation(str, Enum):
    """AI operation type enumeration for different AI interactions."""

    CHAT = "chat"
    WORKFLOW = "workflow"
    EMBEDDING = "embedding"
    TASK_GEN = "task_gen"


class AIUsage(BaseModel, Base):
    """
    AI Usage model for tracking AI operations and costs.

    Tracks all AI operations with detailed metrics for cost analysis,
    usage patterns, and budget management across users and projects.

    Attributes:
        model_name: Name of AI model used (e.g., "gpt-4", "claude-3")
        operation: Type of AI operation performed
        tokens_input: Number of input tokens consumed
        tokens_output: Number of output tokens generated
        cost: Cost of the operation (6 decimal places)
        date: Date for daily aggregation queries
        user: User who performed the operation
        project: Associated project (nullable for personal operations)
    """

    __tablename__ = "ai_usage"

    # Core fields
    model_name: Mapped[str] = mapped_column(
        String(100), nullable=False, index=True, comment="Name of AI model used"
    )

    operation: Mapped[AIOperation] = mapped_column(
        String(20), nullable=False, index=True, comment="Type of AI operation performed"
    )

    # Token and cost tracking
    tokens_input: Mapped[int] = mapped_column(
        Integer, nullable=False, comment="Number of input tokens consumed"
    )

    tokens_output: Mapped[int] = mapped_column(
        Integer, nullable=False, comment="Number of output tokens generated"
    )

    cost: Mapped[Decimal] = mapped_column(
        Numeric(10, 6), nullable=False, comment="Cost of the operation"
    )

    # Date for aggregation
    usage_date: Mapped[date] = mapped_column(
        Date, nullable=False, index=True, comment="Date for daily aggregation queries"
    )

    # Foreign keys
    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="UUID of user who performed the operation",
    )

    project_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("projects.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        comment="UUID of associated project (nullable for personal operations)",
    )

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="ai_usage", lazy="select")

    project: Mapped["Project"] = relationship("Project", back_populates="ai_usage", lazy="select")

    def __repr__(self) -> str:
        """String representation for debugging."""
        return (
            f"<AIUsage(id={self.id}, "
            f"model_name='{self.model_name}', "
            f"operation='{self.operation.value}', "
            f"user_id={self.user_id}, "
            f"project_id={self.project_id}, "
            f"cost={self.cost})>"
        )


# Indexes for query performance
Index("ix_ai_usage_user_id_date", AIUsage.user_id, AIUsage.usage_date.desc())
Index("ix_ai_usage_project_id_date", AIUsage.project_id, AIUsage.usage_date.desc())
