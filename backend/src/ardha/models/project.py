"""
Project model for the Ardha application.

This module defines the Project model representing project workspaces in Ardha.
Projects are the top-level organizational unit containing tasks, files, and team members.
"""

from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import JSON, Boolean, DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ardha.models.base import Base, BaseModel

if TYPE_CHECKING:
    from ardha.models.ai_usage import AIUsage
    from ardha.models.chat import Chat
    from ardha.models.database import Database
    from ardha.models.file import File
    from ardha.models.git_commit import GitCommit
    from ardha.models.github_integration import GitHubIntegration, PullRequest
    from ardha.models.memory import Memory
    from ardha.models.milestone import Milestone
    from ardha.models.openspec import OpenSpecProposal
    from ardha.models.project_member import ProjectMember
    from ardha.models.task import Task
    from ardha.models.task_tag import TaskTag
    from ardha.models.user import User


class Project(BaseModel, Base):
    """
    Project model representing a project workspace.

    Projects are the primary organizational unit in Ardha, containing tasks,
    files, Git repositories, and team members with role-based permissions.

    Attributes:
        name: Project display name (max 255 chars, indexed for search)
        description: Optional detailed project description
        slug: URL-safe unique identifier (auto-generated from name)
        owner_id: UUID of the user who created the project
        visibility: Access control level ('private', 'team', 'public')
        tech_stack: JSON array of technology tags (e.g., ["Python", "React"])
        git_repo_url: Optional Git repository URL
        git_branch: Default Git branch name (default: 'main')
        openspec_enabled: Whether OpenSpec is enabled for this project
        openspec_path: Path to OpenSpec directory within project
        is_archived: Whether project is archived (soft delete)
        archived_at: Timestamp when project was archived
        owner: Relationship to User who owns the project
        members: Relationship to ProjectMember association records
    """

    __tablename__ = "projects"

    # Core fields
    name: Mapped[str] = mapped_column(
        String(255), nullable=False, index=True, comment="Project display name"
    )

    description: Mapped[str | None] = mapped_column(
        Text, nullable=True, comment="Project description"
    )

    slug: Mapped[str] = mapped_column(
        String(255), unique=True, nullable=False, index=True, comment="URL-safe unique identifier"
    )

    # Ownership
    owner_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="UUID of the project owner",
    )

    # Settings
    visibility: Mapped[str] = mapped_column(
        String(50),
        default="private",
        nullable=False,
        comment="Access control level (private/team/public)",
    )

    tech_stack: Mapped[list[str]] = mapped_column(
        JSON, default=list, nullable=False, comment="JSON array of technology tags"
    )

    # Git integration
    git_repo_url: Mapped[str | None] = mapped_column(
        String(500), nullable=True, comment="Git repository URL"
    )

    git_branch: Mapped[str] = mapped_column(
        String(255), default="main", nullable=False, comment="Default Git branch name"
    )

    # OpenSpec configuration
    openspec_enabled: Mapped[bool] = mapped_column(
        Boolean, default=True, nullable=False, comment="Whether OpenSpec is enabled"
    )

    openspec_path: Mapped[str] = mapped_column(
        String(255), default="openspec/", nullable=False, comment="Path to OpenSpec directory"
    )

    # Archive
    is_archived: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False, index=True, comment="Whether project is archived"
    )

    archived_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, comment="Timestamp when project was archived"
    )

    # Relationships
    owner: Mapped["User"] = relationship(
        "User", back_populates="owned_projects", foreign_keys=[owner_id]
    )

    members: Mapped[list["ProjectMember"]] = relationship(
        "ProjectMember", back_populates="project", cascade="all, delete-orphan", lazy="select"
    )

    tasks: Mapped[list["Task"]] = relationship(
        "Task", back_populates="project", cascade="all, delete-orphan", lazy="select"
    )

    task_tags: Mapped[list["TaskTag"]] = relationship(
        "TaskTag", back_populates="project", cascade="all, delete-orphan", lazy="select"
    )

    milestones: Mapped[list["Milestone"]] = relationship(
        "Milestone", back_populates="project", cascade="all, delete-orphan", lazy="select"
    )

    chats: Mapped[list["Chat"]] = relationship(
        "Chat", back_populates="project", cascade="all, delete-orphan", lazy="select"
    )

    ai_usage: Mapped[list["AIUsage"]] = relationship(
        "AIUsage", back_populates="project", cascade="all, delete-orphan", lazy="select"
    )

    memories: Mapped[list["Memory"]] = relationship(
        "Memory", back_populates="project", cascade="all, delete-orphan", lazy="select"
    )

    openspec_proposals: Mapped[list["OpenSpecProposal"]] = relationship(
        "OpenSpecProposal",
        back_populates="project",
        cascade="all, delete-orphan",
        lazy="select",
    )

    files: Mapped[list["File"]] = relationship(
        "File",
        back_populates="project",
        cascade="all, delete-orphan",
        lazy="select",
    )

    git_commits: Mapped[list["GitCommit"]] = relationship(
        "GitCommit",
        back_populates="project",
        cascade="all, delete-orphan",
        lazy="select",
    )

    github_integration: Mapped["GitHubIntegration | None"] = relationship(
        "GitHubIntegration",
        back_populates="project",
        uselist=False,
        cascade="all, delete-orphan",
    )

    pull_requests: Mapped[list["PullRequest"]] = relationship(
        "PullRequest",
        back_populates="project",
        cascade="all, delete-orphan",
        lazy="select",
    )

    databases: Mapped[list["Database"]] = relationship(
        "Database",
        back_populates="project",
        cascade="all, delete-orphan",
        lazy="select",
    )

    def __repr__(self) -> str:
        """String representation for debugging."""
        return (
            f"<Project(id={self.id}, "
            f"slug='{self.slug}', "
            f"name='{self.name}', "
            f"owner_id={self.owner_id}, "
            f"is_archived={self.is_archived})>"
        )
