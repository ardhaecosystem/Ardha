"""
Project response schemas for API responses.

This module defines Pydantic models for formatting project-related responses.
"""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class ProjectMemberResponse(BaseModel):
    """
    Response schema for project member.

    Includes member metadata and associated user information.

    Attributes:
        id: ProjectMember UUID
        user_id: UUID of the user
        role: Member's role (owner/admin/member/viewer)
        joined_at: When user joined the project
        user_email: User's email (if available)
        user_username: User's username (if available)
        user_full_name: User's full name (if available)
    """

    id: UUID
    user_id: UUID
    role: str
    joined_at: datetime

    # User data (populated from relationship)
    user_email: str | None = None
    user_username: str | None = None
    user_full_name: str | None = None

    model_config = ConfigDict(from_attributes=True)


class ProjectResponse(BaseModel):
    """
    Response schema for project.

    Complete project information including metadata, settings, and statistics.

    Attributes:
        id: Project UUID
        name: Project display name
        description: Project description
        slug: URL-safe unique identifier
        owner_id: UUID of project owner
        visibility: Access control level (private/team/public)
        tech_stack: List of technology tags
        git_repo_url: Git repository URL
        git_branch: Default Git branch
        openspec_enabled: Whether OpenSpec is enabled
        openspec_path: Path to OpenSpec directory
        is_archived: Whether project is archived
        archived_at: When project was archived
        created_at: When project was created
        updated_at: When project was last updated
        member_count: Number of team members (computed)
    """

    id: UUID
    name: str
    description: str | None
    slug: str
    owner_id: UUID
    visibility: str
    tech_stack: list[str]
    git_repo_url: str | None
    git_branch: str
    openspec_enabled: bool
    openspec_path: str
    is_archived: bool
    archived_at: datetime | None
    created_at: datetime
    updated_at: datetime

    # Computed fields
    member_count: int | None = None

    model_config = ConfigDict(from_attributes=True)


class ProjectListResponse(BaseModel):
    """
    Response schema for paginated project list.

    Attributes:
        projects: List of projects
        total: Total number of projects (before pagination)
        skip: Number of records skipped
        limit: Maximum results per page
    """

    projects: list[ProjectResponse]
    total: int
    skip: int = 0
    limit: int = 100
