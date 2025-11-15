"""
ProjectMember association model for the Ardha application.

This module defines the ProjectMember model representing the many-to-many
relationship between users and projects with role-based permissions.
"""

from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import DateTime, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from ardha.models.base import Base, BaseModel

if TYPE_CHECKING:
    from ardha.models.project import Project
    from ardha.models.user import User


class ProjectMember(BaseModel, Base):
    """
    Association model for project team members with roles.

    Implements the many-to-many relationship between users and projects,
    with additional role-based access control. Each user can be a member
    of multiple projects, and each project can have multiple members.

    Roles:
        - 'owner': Project creator, full control (assigned automatically)
        - 'admin': Can manage project settings and members
        - 'member': Can view and edit project content
        - 'viewer': Read-only access to project

    Attributes:
        project_id: UUID of the project
        user_id: UUID of the user
        role: User's role in the project ('owner', 'admin', 'member', 'viewer')
        joined_at: Timestamp when user joined the project
        project: Relationship to Project
        user: Relationship to User
    """

    __tablename__ = "project_members"

    # Foreign keys
    project_id: Mapped[UUID] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="UUID of the project",
    )

    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="UUID of the user",
    )

    # Role field
    role: Mapped[str] = mapped_column(
        String(50), nullable=False, comment="User's role in project (owner/admin/member/viewer)"
    )

    # Activity tracking
    joined_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        comment="Timestamp when user joined project",
    )

    # Relationships
    project: Mapped["Project"] = relationship(
        "Project", back_populates="members", foreign_keys=[project_id]
    )

    user: Mapped["User"] = relationship(
        "User", back_populates="project_memberships", foreign_keys=[user_id]
    )

    # Table constraints
    __table_args__ = (UniqueConstraint("project_id", "user_id", name="uq_project_user"),)

    def __repr__(self) -> str:
        """String representation for debugging."""
        return (
            f"<ProjectMember(id={self.id}, "
            f"project_id={self.project_id}, "
            f"user_id={self.user_id}, "
            f"role='{self.role}')>"
        )
