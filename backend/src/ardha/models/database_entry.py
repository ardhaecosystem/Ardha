"""
DatabaseEntry model for Notion-style database entries.

This module defines the DatabaseEntry model representing a row in a
Notion-style database with values for each property.
"""

from datetime import datetime
from typing import TYPE_CHECKING, Any
from uuid import UUID

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Integer, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ardha.models.base import Base, BaseModel

if TYPE_CHECKING:
    from ardha.models.database import Database
    from ardha.models.database_entry_value import DatabaseEntryValue
    from ardha.models.user import User


class DatabaseEntry(BaseModel, Base):
    """
    DatabaseEntry model representing a row in a Notion-style database.

    Each entry contains values for the database's properties, stored in
    the DatabaseEntryValue relationship. Entries support manual ordering,
    tracking of creation and last edit information, and soft deletion.

    Attributes:
        database_id: Foreign key to the owning database
        position: Display order for manual sorting (0-based)
        created_by_user_id: UUID of user who created this entry
        created_at: Timestamp when entry was created
        updated_at: Timestamp when entry was last updated
        last_edited_by_user_id: UUID of user who last edited this entry
        last_edited_at: Timestamp when entry was last edited
        is_archived: Whether entry is archived (soft delete)
        archived_at: Timestamp when entry was archived
        database: Relationship to parent Database
        created_by: Relationship to User who created this entry
        last_edited_by: Relationship to User who last edited this entry
        values: Relationship to DatabaseEntryValue objects
    """

    __tablename__ = "database_entries"

    # ============= Identity & Organization =============

    database_id: Mapped[UUID] = mapped_column(
        ForeignKey("databases.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Foreign key to owning database",
    )

    position: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        comment="Display order for manual sorting (0-based)",
    )

    # ============= Ownership & Tracking =============

    created_by_user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="UUID of user who created this entry",
    )

    last_edited_by_user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="UUID of user who last edited this entry",
    )

    last_edited_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        comment="Timestamp when entry was last edited",
    )

    # ============= Archive =============

    is_archived: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False, comment="Whether entry is archived"
    )

    archived_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="Timestamp when entry was archived",
    )

    # created_at and updated_at inherited from BaseModel

    # ============= Relationships =============

    # Many-to-one: Database relationship
    database: Mapped["Database"] = relationship(
        "Database",
        back_populates="entries",
    )

    # Many-to-one: Creator relationship
    created_by: Mapped["User"] = relationship(
        "User",
        foreign_keys=[created_by_user_id],
    )

    # Many-to-one: Last editor relationship
    last_edited_by: Mapped["User"] = relationship(
        "User",
        foreign_keys=[last_edited_by_user_id],
    )

    # One-to-many: Values relationship
    values: Mapped[list["DatabaseEntryValue"]] = relationship(
        "DatabaseEntryValue",
        back_populates="entry",
        cascade="all, delete-orphan",
        lazy="select",
    )

    # ============= Constraints & Indexes =============

    __table_args__ = (
        # Index for ordering queries
        Index("ix_entry_database_position", "database_id", "position"),
        # Index for recent entries
        Index("ix_entry_database_created", "database_id", "created_at"),
        # Index for creator queries
        Index("ix_entry_creator_created", "created_by_user_id", "created_at"),
    )

    # ============= Helper Methods =============

    def get_value(self, property_id: UUID) -> dict[str, Any] | None:
        """
        Get the value for a specific property.

        Args:
            property_id: UUID of the property to get value for

        Returns:
            Value dictionary for the property, or None if not set

        Example:
            entry.get_value(status_property_id)
            # Returns: {"select": {"name": "In Progress", "color": "#3b82f6"}}
        """
        for value in self.values:
            if value.property_id == property_id:
                return value.value
        return None

    def __repr__(self) -> str:
        """String representation of DatabaseEntry."""
        return (
            f"<DatabaseEntry(id={self.id}, "
            f"database_id={self.database_id}, "
            f"position={self.position}, "
            f"is_archived={self.is_archived})>"
        )
