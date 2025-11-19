"""
DatabaseEntryValue model for Notion-style database entry values.

This module defines the DatabaseEntryValue model representing the value
of a specific property in a database entry (a cell in the table).
"""

from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import JSON, ForeignKey, Index, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ardha.models.base import Base, BaseModel

if TYPE_CHECKING:
    from ardha.models.database_entry import DatabaseEntry
    from ardha.models.database_property import DatabaseProperty


class DatabaseEntryValue(BaseModel, Base):
    """
    DatabaseEntryValue model representing a property value in a database entry.

    This is essentially a cell in the database table, storing the value for
    a specific property in a specific entry. Values are stored in flexible
    JSON format to accommodate different property types.

    Value format examples by property type:
        - text: {"text": "Hello World"}
        - number: {"number": 123.45}
        - select: {"select": {"name": "High", "color": "#ff0000"}}
        - multiselect: {"multiselect": [{"name": "Tag1", "color": "#0000ff"}]}
        - date: {"date": {"start": "2024-01-01", "end": "2024-01-31"}}
        - checkbox: {"checkbox": true}
        - url: {"url": "https://example.com"}
        - email: {"email": "user@example.com"}
        - phone: {"phone": "+1234567890"}
        - relation: {"relations": ["entry_id_1", "entry_id_2"]}
        - formula: {"formula": {"result": 42, "error": null}}
        - rollup: {"rollup": {"value": 10, "type": "number"}}

    Attributes:
        entry_id: Foreign key to the entry (row)
        property_id: Foreign key to the property (column)
        value: JSON value in type-specific format
        created_at: Timestamp when value was created
        updated_at: Timestamp when value was last updated
        entry: Relationship to parent DatabaseEntry
        property: Relationship to DatabaseProperty definition
    """

    __tablename__ = "database_entry_values"

    # ============= Identity =============

    entry_id: Mapped[UUID] = mapped_column(
        ForeignKey("database_entries.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Foreign key to database entry (row)",
    )

    property_id: Mapped[UUID] = mapped_column(
        ForeignKey("database_properties.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Foreign key to database property (column)",
    )

    # ============= Value Storage =============

    value: Mapped[dict | None] = mapped_column(
        JSON,
        nullable=True,
        comment="Property value in JSON format",
    )

    # created_at and updated_at inherited from BaseModel

    # ============= Relationships =============

    # Many-to-one: Entry relationship
    entry: Mapped["DatabaseEntry"] = relationship(
        "DatabaseEntry",
        back_populates="values",
    )

    # Many-to-one: Property relationship
    property: Mapped["DatabaseProperty"] = relationship(
        "DatabaseProperty",
    )

    # ============= Constraints & Indexes =============

    __table_args__ = (
        # Unique constraint on (entry_id, property_id) - one value per property per entry
        UniqueConstraint(
            "entry_id",
            "property_id",
            name="uq_entry_value_entry_property",
        ),
        # Index for property-based queries
        Index("ix_entry_value_property", "property_id"),
    )

    # ============= Helper Methods =============

    def __repr__(self) -> str:
        """String representation of DatabaseEntryValue."""
        value_preview = str(self.value)[:50] if self.value else "None"
        return (
            f"<DatabaseEntryValue(id={self.id}, "
            f"entry_id={self.entry_id}, "
            f"property_id={self.property_id}, "
            f"value={value_preview})>"
        )
