"""
SQLAlchemy Base Models and Mixins.

This module provides the foundation for all database models, including:
- DeclarativeBase for SQLAlchemy ORM
- BaseModel mixin with id and timestamps
- SoftDeleteMixin for soft deletion support
"""

from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import Boolean, DateTime, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """
    Base class for all SQLAlchemy models.

    This is the declarative base that all models inherit from.
    Uses SQLAlchemy 2.0 declarative syntax.
    """

    pass


class BaseModel:
    """
    Mixin that adds id and timestamp fields to models.

    Provides:
    - id: UUID primary key (auto-generated)
    - created_at: Timestamp when record was created
    - updated_at: Timestamp when record was last updated

    Usage:
        class User(Base, BaseModel):
            __tablename__ = "users"
            email: Mapped[str] = mapped_column(String(255), unique=True)
    """

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4, comment="Primary key UUID")

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        comment="Timestamp when record was created",
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        comment="Timestamp when record was last updated",
    )


class SoftDeleteMixin:
    """
    Mixin that adds soft delete functionality to models.

    Provides:
    - is_deleted: Boolean flag for soft deletion
    - deleted_at: Timestamp when record was soft deleted

    Usage:
        class User(Base, BaseModel, SoftDeleteMixin):
            __tablename__ = "users"
            email: Mapped[str] = mapped_column(String(255), unique=True)

    When soft deleting, set is_deleted=True and deleted_at=datetime.now()
    """

    is_deleted: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False, comment="Soft delete flag"
    )

    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, comment="Timestamp when record was soft deleted"
    )
