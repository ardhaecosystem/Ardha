"""
DatabaseProperty model for Notion-style database properties.

This module defines the DatabaseProperty model representing a column/field
in a Notion-style database with dynamic type configuration.
"""

from typing import TYPE_CHECKING, Any
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


class DatabaseProperty(BaseModel, Base):
    """
    DatabaseProperty model representing a column in a Notion-style database.

    Properties define the schema of a database, with each property having a type
    (text, number, select, etc.) and type-specific configuration stored in JSON.

    Supported property types:
        - text: Plain text field
        - number: Numeric field
        - select: Single-select dropdown
        - multiselect: Multi-select dropdown
        - date: Date or date range
        - checkbox: Boolean checkbox
        - url: URL field
        - email: Email field
        - phone: Phone number field
        - formula: Computed field based on other properties
        - rollup: Aggregation from related entries
        - relation: Link to entries in another database
        - created_time: Auto-populated creation timestamp
        - created_by: Auto-populated creator
        - last_edited_time: Auto-populated last edit timestamp
        - last_edited_by: Auto-populated last editor

    Attributes:
        database_id: Foreign key to the owning database
        name: Property display name (e.g., "Status", "Priority", "Assignee")
        property_type: Type of property from supported types
        config: JSON configuration specific to property type
        position: Display order (0-based, for column ordering)
        is_required: Whether this property requires a value
        is_visible: Whether this property is visible by default
        created_at: Timestamp when property was created
        updated_at: Timestamp when property was last updated
        database: Relationship to parent Database
    """

    __tablename__ = "database_properties"

    # ============= Identity & Organization =============

    database_id: Mapped[UUID] = mapped_column(
        ForeignKey("databases.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Foreign key to owning database",
    )

    name: Mapped[str] = mapped_column(String(200), nullable=False, comment="Property display name")

    # ============= Property Type & Configuration =============

    property_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
        comment=(
            "Property type: text, number, select, multiselect, date, checkbox, "
            "url, email, phone, formula, rollup, relation, created_time, "
            "created_by, last_edited_time, last_edited_by"
        ),
    )

    config: Mapped[dict | None] = mapped_column(
        JSON,
        nullable=True,
        comment="Type-specific configuration in JSON format",
    )

    # ============= Display & Behavior =============

    position: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        comment="Display order for column positioning (0-based)",
    )

    is_required: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        comment="Whether this property requires a value",
    )

    is_visible: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
        comment="Whether this property is visible by default",
    )

    # created_at and updated_at inherited from BaseModel

    # ============= Relationships =============

    # Many-to-one: Database relationship
    database: Mapped["Database"] = relationship(
        "Database",
        back_populates="properties",
    )

    # ============= Constraints & Indexes =============

    __table_args__ = (
        # Index for ordering queries
        Index("ix_property_database_position", "database_id", "position"),
        # Index for filtering by property type
        Index("ix_property_database_type", "database_id", "property_type"),
        # Unique constraint on (database_id, name)
        UniqueConstraint(
            "database_id",
            "name",
            name="uq_property_database_name",
        ),
        # Check constraint for valid position
        CheckConstraint("position >= 0", name="ck_property_position"),
    )

    # ============= Helper Methods =============

    def validate_value(self, value: Any) -> bool:
        """
        Validate if a value is appropriate for this property type.

        Args:
            value: The value to validate (in JSON format)

        Returns:
            True if value is valid for this property type, False otherwise

        Examples:
            # Text property
            property.validate_value({"text": "Hello"})  # True
            property.validate_value({"number": 123})    # False

            # Number property
            property.validate_value({"number": 123.45})  # True
            property.validate_value({"text": "abc"})     # False

            # Select property
            property.validate_value({"select": {"name": "High", "color": "#ff0000"}})  # True

            # Checkbox property
            property.validate_value({"checkbox": True})  # True
        """
        if value is None:
            return not self.is_required

        if not isinstance(value, dict):
            return False

        # Validate based on property type
        valid_types = {
            "text": lambda v: "text" in v and isinstance(v.get("text"), str),
            "number": lambda v: "number" in v and isinstance(v.get("number"), (int, float)),
            "select": lambda v: "select" in v and isinstance(v.get("select"), dict),
            "multiselect": lambda v: "multiselect" in v and isinstance(v.get("multiselect"), list),
            "date": lambda v: "date" in v and isinstance(v.get("date"), dict),
            "checkbox": lambda v: "checkbox" in v and isinstance(v.get("checkbox"), bool),
            "url": lambda v: "url" in v and isinstance(v.get("url"), str),
            "email": lambda v: "email" in v and isinstance(v.get("email"), str),
            "phone": lambda v: "phone" in v and isinstance(v.get("phone"), str),
            "relation": lambda v: "relations" in v and isinstance(v.get("relations"), list),
            "formula": lambda v: "formula" in v and isinstance(v.get("formula"), dict),
            "rollup": lambda v: "rollup" in v and isinstance(v.get("rollup"), dict),
        }

        # Auto-populated fields don't need validation
        if self.property_type in [
            "created_time",
            "created_by",
            "last_edited_time",
            "last_edited_by",
        ]:
            return True

        validator = valid_types.get(self.property_type)
        if not validator:
            return False

        return validator(value)

    def __repr__(self) -> str:
        """String representation of DatabaseProperty."""
        return (
            f"<DatabaseProperty(id={self.id}, "
            f"name='{self.name}', "
            f"type={self.property_type}, "
            f"database_id={self.database_id}, "
            f"position={self.position})>"
        )
