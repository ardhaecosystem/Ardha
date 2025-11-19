"""
DatabaseView model for Notion-style database views.

This module defines the DatabaseView model representing different ways to
visualize and interact with database data (table, board, calendar, etc.).
"""

from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import (
    JSON,
    Boolean,
    CheckConstraint,
    ForeignKey,
    Index,
    Integer,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ardha.models.base import Base, BaseModel

if TYPE_CHECKING:
    from ardha.models.database import Database
    from ardha.models.user import User


class DatabaseView(BaseModel, Base):
    """
    DatabaseView model representing a view of database data.

    Views define different ways to visualize and interact with database entries,
    such as table view, Kanban board, calendar, timeline, etc.

    Supported view types:
        - table: Spreadsheet-style view with rows and columns
        - board: Kanban board grouped by a property
        - calendar: Calendar view based on date property
        - list: Simple list view
        - gallery: Card-based gallery view
        - timeline: Gantt chart timeline view

    Attributes:
        database_id: Foreign key to the owning database
        name: View display name (e.g., "All Tasks", "By Status", "Calendar")
        view_type: Type of view from supported types
        config: JSON configuration specific to view type
        position: Display order for view tabs (0-based)
        is_default: Whether this is the default view for the database
        created_by_user_id: UUID of user who created this view
        created_at: Timestamp when view was created
        updated_at: Timestamp when view was last updated
        database: Relationship to parent Database
        created_by: Relationship to User who created this view
    """

    __tablename__ = "database_views"

    # ============= Identity & Organization =============

    database_id: Mapped[UUID] = mapped_column(
        ForeignKey("databases.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Foreign key to owning database",
    )

    name: Mapped[str] = mapped_column(String(200), nullable=False, comment="View display name")

    # ============= View Type & Configuration =============

    view_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        comment="View type: table, board, calendar, list, gallery, timeline",
    )

    config: Mapped[dict] = mapped_column(
        JSON,
        nullable=False,
        default=dict,
        comment="View-specific configuration in JSON format",
    )

    # ============= Display & Behavior =============

    position: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        comment="Display order for view tabs (0-based)",
    )

    is_default: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        index=True,
        comment="Whether this is the default view",
    )

    # ============= Ownership =============

    created_by_user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="UUID of user who created this view",
    )

    # created_at and updated_at inherited from BaseModel

    # ============= Relationships =============

    # Many-to-one: Database relationship
    database: Mapped["Database"] = relationship(
        "Database",
        back_populates="views",
    )

    # Many-to-one: Creator relationship
    created_by: Mapped["User"] = relationship(
        "User",
        back_populates="created_views",
        foreign_keys=[created_by_user_id],
    )

    # ============= Constraints & Indexes =============

    __table_args__ = (
        # Index for ordering queries
        Index("ix_view_database_position", "database_id", "position"),
        # Index for default view lookup
        Index("ix_view_database_default", "database_id", "is_default"),
        # Unique constraint on (database_id, name)
        UniqueConstraint(
            "database_id",
            "name",
            name="uq_view_database_name",
        ),
        # Check constraint for valid position
        CheckConstraint("position >= 0", name="ck_view_position"),
    )

    # ============= Helper Methods =============

    def __repr__(self) -> str:
        """String representation of DatabaseView."""
        return (
            f"<DatabaseView(id={self.id}, "
            f"name='{self.name}', "
            f"type={self.view_type}, "
            f"database_id={self.database_id}, "
            f"is_default={self.is_default})>"
        )
