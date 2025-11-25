"""
Database model for Notion-style databases.

This module defines the Database model representing a Notion-style database
that can contain structured data with dynamic properties and multiple views.
"""

from datetime import datetime
from typing import TYPE_CHECKING, Any
from uuid import UUID

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ardha.models.base import Base, BaseModel

if TYPE_CHECKING:
    from ardha.models.database_entry import DatabaseEntry
    from ardha.models.database_property import DatabaseProperty
    from ardha.models.database_view import DatabaseView
    from ardha.models.project import Project
    from ardha.models.user import User


class Database(BaseModel, Base):
    """
    Database model representing a Notion-style database.

    Databases are flexible, structured data containers within projects,
    similar to Notion databases. They support dynamic properties, multiple
    views (table, board, calendar, etc.), and can be used as templates.

    Attributes:
        project_id: Foreign key to the owning project
        name: Database display name (max 200 chars)
        description: Optional detailed description
        icon: Optional emoji icon (e.g., "📊", "🗂️")
        color: Optional hex color code (e.g., "#3b82f6")
        is_template: Whether this database is a template for creation
        template_id: If created from template, references the template
        created_by_user_id: UUID of the user who created this database
        created_at: Timestamp when database was created
        updated_at: Timestamp when database was last updated
        is_archived: Whether database is archived (soft delete)
        archived_at: Timestamp when database was archived
        project: Relationship to parent Project
        created_by: Relationship to User who created this database
        properties: Relationship to DatabaseProperty objects
        views: Relationship to DatabaseView objects
        entries: Relationship to DatabaseEntry objects
        template_instances: Self-reference for databases created from this template
    """

    __tablename__ = "databases"

    # ============= Identity & Organization =============

    project_id: Mapped[UUID] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Foreign key to owning project",
    )

    name: Mapped[str] = mapped_column(String(200), nullable=False, comment="Database display name")

    description: Mapped[str | None] = mapped_column(
        Text, nullable=True, comment="Optional detailed description"
    )

    icon: Mapped[str | None] = mapped_column(
        String(50), nullable=True, comment="Optional emoji icon"
    )

    color: Mapped[str | None] = mapped_column(
        String(20), nullable=True, comment="Optional hex color code"
    )

    # ============= Template System =============

    is_template: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False, comment="Whether this is a template"
    )

    template_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("databases.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        comment="Reference to template if created from one",
    )

    # ============= Ownership =============

    created_by_user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="UUID of user who created this database",
    )

    # ============= Archive =============

    is_archived: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False, index=True, comment="Whether database is archived"
    )

    archived_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="Timestamp when database was archived",
    )

    # created_at and updated_at inherited from BaseModel

    # ============= Relationships =============

    # Many-to-one: Project relationship
    project: Mapped["Project"] = relationship(
        "Project",
        back_populates="databases",
    )

    # Many-to-one: Creator relationship
    created_by: Mapped["User"] = relationship(
        "User",
        back_populates="created_databases",
        foreign_keys=[created_by_user_id],
    )

    # One-to-many: Properties relationship
    properties: Mapped[list["DatabaseProperty"]] = relationship(
        "DatabaseProperty",
        back_populates="database",
        cascade="all, delete-orphan",
        lazy="select",
    )

    # One-to-many: Views relationship
    views: Mapped[list["DatabaseView"]] = relationship(
        "DatabaseView",
        back_populates="database",
        cascade="all, delete-orphan",
        lazy="select",
    )

    # One-to-many: Entries relationship
    entries: Mapped[list["DatabaseEntry"]] = relationship(
        "DatabaseEntry",
        back_populates="database",
        cascade="all, delete-orphan",
        lazy="select",
    )

    # Self-reference for template instances (one template → many instances)
    # The template is the "one" side, template_instances is the "many" side
    template_instances: Mapped[list["Database"]] = relationship(
        "Database",
        back_populates="template",
        primaryjoin="Database.id == foreign(Database.template_id)",
        lazy="select",
    )

    # Many-to-one: Template relationship (many instances → one template)
    template: Mapped["Database | None"] = relationship(
        "Database",
        back_populates="template_instances",
        primaryjoin="Database.template_id == remote(Database.id)",
        uselist=False,
        lazy="select",
    )

    # ============= Constraints & Indexes =============

    __table_args__ = (
        # Index for project queries with sorting
        Index("ix_database_project_created", "project_id", "created_at"),
        # Index for project + name lookups
        Index("ix_database_project_name", "project_id", "name"),
        # Index for template lookups
        Index("ix_database_template", "is_template"),
        # Index for template instances
        Index("ix_database_template_id", "template_id"),
        # Partial unique index on (project_id, name) for non-archived databases
        Index(
            "uq_database_project_name",
            "project_id",
            "name",
            unique=True,
            postgresql_where="is_archived = false",
        ),
    )

    # ============= Helper Methods =============

    def to_dict(self) -> dict[str, Any]:
        """
        Convert database to dictionary representation.

        Returns:
            Dictionary with all database fields
        """
        return {
            "id": str(self.id),
            "project_id": str(self.project_id),
            "name": self.name,
            "description": self.description,
            "icon": self.icon,
            "color": self.color,
            "is_template": self.is_template,
            "template_id": str(self.template_id) if self.template_id else None,
            "created_by_user_id": str(self.created_by_user_id),
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "is_archived": self.is_archived,
            "archived_at": self.archived_at.isoformat() if self.archived_at else None,
        }

    def __repr__(self) -> str:
        """String representation of Database."""
        return (
            f"<Database(id={self.id}, "
            f"name='{self.name}', "
            f"project_id={self.project_id}, "
            f"is_template={self.is_template}, "
            f"is_archived={self.is_archived})>"
        )
