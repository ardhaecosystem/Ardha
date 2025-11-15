"""
User model for authentication and user management.

This module defines the User model with support for:
- Email/password authentication
- OAuth authentication (GitHub, Google)
- User profile information
- Account status management
"""

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ardha.models.base import Base, BaseModel

if TYPE_CHECKING:
    from ardha.models.ai_usage import AIUsage
    from ardha.models.chat import Chat
    from ardha.models.memory import Memory
    from ardha.models.openspec import OpenSpecProposal
    from ardha.models.project import Project
    from ardha.models.project_member import ProjectMember
    from ardha.models.task import Task
    from ardha.models.task_activity import TaskActivity


class User(Base, BaseModel):
    """
    User model for authentication and profile management.

    Supports both traditional email/password authentication and OAuth
    (GitHub, Google). OAuth users may not have a password_hash.

    Attributes:
        email: User's email address (unique, indexed)
        username: User's unique username (indexed)
        full_name: User's full display name
        password_hash: Hashed password (nullable for OAuth users)
        is_active: Whether the account is active
        is_superuser: Whether user has admin privileges
        avatar_url: URL to user's profile picture
        github_id: GitHub OAuth user ID (unique, indexed)
        google_id: Google OAuth user ID (unique, indexed)
        last_login_at: Timestamp of last successful login
    """

    __tablename__ = "users"

    # Core identity fields
    email: Mapped[str] = mapped_column(
        String(255), unique=True, index=True, nullable=False, comment="User's email address"
    )

    username: Mapped[str] = mapped_column(
        String(50), unique=True, index=True, nullable=False, comment="User's unique username"
    )

    full_name: Mapped[str | None] = mapped_column(
        String(255), nullable=True, comment="User's full display name"
    )

    # Authentication fields
    password_hash: Mapped[str | None] = mapped_column(
        String(255), nullable=True, comment="Hashed password (null for OAuth users)"
    )

    # Account status fields
    is_active: Mapped[bool] = mapped_column(
        Boolean, default=True, nullable=False, comment="Whether the account is active"
    )

    is_superuser: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False, comment="Whether user has admin privileges"
    )

    # Profile fields
    avatar_url: Mapped[str | None] = mapped_column(
        String(500), nullable=True, comment="URL to user's profile picture"
    )

    # OAuth provider IDs (unique and indexed for lookups)
    github_id: Mapped[str | None] = mapped_column(
        String(100), unique=True, index=True, nullable=True, comment="GitHub OAuth user ID"
    )

    google_id: Mapped[str | None] = mapped_column(
        String(100), unique=True, index=True, nullable=True, comment="Google OAuth user ID"
    )

    # Activity tracking
    last_login_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, comment="Timestamp of last successful login"
    )

    # Relationships
    owned_projects: Mapped[list["Project"]] = relationship(
        "Project", back_populates="owner", foreign_keys="Project.owner_id", lazy="select"
    )

    project_memberships: Mapped[list["ProjectMember"]] = relationship(
        "ProjectMember", back_populates="user", foreign_keys="ProjectMember.user_id", lazy="select"
    )

    assigned_tasks: Mapped[list["Task"]] = relationship(
        "Task", back_populates="assignee", foreign_keys="Task.assignee_id", lazy="select"
    )

    created_tasks: Mapped[list["Task"]] = relationship(
        "Task", back_populates="created_by", foreign_keys="Task.created_by_id", lazy="select"
    )

    task_activities: Mapped[list["TaskActivity"]] = relationship(
        "TaskActivity", back_populates="user", lazy="select"
    )

    chats: Mapped[list["Chat"]] = relationship(
        "Chat", back_populates="user", cascade="all, delete-orphan", lazy="select"
    )

    ai_usage: Mapped[list["AIUsage"]] = relationship(
        "AIUsage", back_populates="user", cascade="all, delete-orphan", lazy="select"
    )

    memories: Mapped[list["Memory"]] = relationship(
        "Memory", back_populates="user", cascade="all, delete-orphan", lazy="select"
    )

    created_openspec_proposals: Mapped[list["OpenSpecProposal"]] = relationship(
        "OpenSpecProposal",
        foreign_keys="OpenSpecProposal.created_by_user_id",
        back_populates="created_by",
        lazy="select",
    )

    approved_openspec_proposals: Mapped[list["OpenSpecProposal"]] = relationship(
        "OpenSpecProposal",
        foreign_keys="OpenSpecProposal.approved_by_user_id",
        back_populates="approved_by",
        lazy="select",
    )

    def __repr__(self) -> str:
        """String representation for debugging."""
        return (
            f"<User(id={self.id}, "
            f"username='{self.username}', "
            f"email='{self.email}', "
            f"is_active={self.is_active})>"
        )
