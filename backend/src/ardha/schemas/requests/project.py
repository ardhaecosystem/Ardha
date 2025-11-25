"""
Project request schemas for API validation.

This module defines Pydantic models for validating project-related requests.
"""

from uuid import UUID

from pydantic import BaseModel, Field, field_validator


class ProjectCreateRequest(BaseModel):
    """
    Request schema for creating a new project.

    Attributes:
        name: Project name (1-255 characters, required)
        description: Optional project description
        visibility: Access level (private/team/public, default: private)
        tech_stack: List of technology tags (e.g., ["Python", "React"])
        git_repo_url: Optional Git repository URL
        git_branch: Git branch name (default: main)
        openspec_enabled: Whether OpenSpec is enabled (default: True)
        openspec_path: Path to OpenSpec directory (default: openspec/)
    """

    name: str = Field(..., min_length=1, max_length=255, description="Project name")
    description: str | None = Field(None, description="Project description")
    visibility: str = Field(
        default="private", pattern="^(private|team|public)$", description="Access control level"
    )
    tech_stack: list[str] = Field(default_factory=list, description="Technology stack tags")
    git_repo_url: str | None = Field(None, max_length=500, description="Git repository URL")
    git_branch: str = Field(default="main", max_length=255, description="Default Git branch")
    openspec_enabled: bool = Field(default=True, description="Enable OpenSpec for this project")
    openspec_path: str = Field(
        default="openspec/", max_length=255, description="Path to OpenSpec directory"
    )

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        """
        Validate project name.

        Args:
            v: Project name to validate

        Returns:
            Stripped project name

        Raises:
            ValueError: If name is empty after stripping whitespace
        """
        stripped = v.strip()
        if not stripped:
            raise ValueError("Project name cannot be empty or whitespace")
        return stripped

    @field_validator("tech_stack")
    @classmethod
    def validate_tech_stack(cls, v: list[str]) -> list[str]:
        """
        Validate and clean tech stack list.

        Args:
            v: List of technology tags

        Returns:
            Cleaned list with stripped tags
        """
        # Remove empty strings and strip whitespace
        return [tag.strip() for tag in v if tag.strip()]


class ProjectUpdateRequest(BaseModel):
    """
    Request schema for updating an existing project.

    All fields are optional. Only provided fields will be updated.

    Attributes:
        name: New project name (1-255 characters)
        description: New project description
        visibility: New access level (private/team/public)
        tech_stack: New technology stack list
        git_repo_url: New Git repository URL
        git_branch: New Git branch name
        openspec_enabled: Enable/disable OpenSpec
        openspec_path: New OpenSpec directory path
    """

    name: str | None = Field(None, min_length=1, max_length=255, description="Project name")
    description: str | None = Field(None, description="Project description")
    visibility: str | None = Field(
        None, pattern="^(private|team|public)$", description="Access control level"
    )
    tech_stack: list[str] | None = Field(None, description="Technology stack tags")
    git_repo_url: str | None = Field(None, max_length=500, description="Git repository URL")
    git_branch: str | None = Field(None, max_length=255, description="Default Git branch")
    openspec_enabled: bool | None = Field(None, description="Enable OpenSpec for this project")
    openspec_path: str | None = Field(
        None, max_length=255, description="Path to OpenSpec directory"
    )

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str | None) -> str | None:
        """Validate project name if provided."""
        if v is None:
            return v
        stripped = v.strip()
        if not stripped:
            raise ValueError("Project name cannot be empty or whitespace")
        return stripped

    @field_validator("tech_stack")
    @classmethod
    def validate_tech_stack(cls, v: list[str] | None) -> list[str] | None:
        """Validate tech stack if provided."""
        if v is None:
            return v
        return [tag.strip() for tag in v if tag.strip()]


class ProjectMemberAddRequest(BaseModel):
    """
    Request schema for adding a member to a project.

    Note: Cannot add user as 'owner' role. Owner is assigned at project creation.

    Attributes:
        user_id: UUID of the user to add
        role: Role to assign (admin/member/viewer)
    """

    user_id: UUID = Field(..., description="UUID of user to add to project")
    role: str = Field(
        ..., pattern="^(admin|member|viewer)$", description="Role to assign (admin/member/viewer)"
    )


class ProjectMemberUpdateRequest(BaseModel):
    """
    Request schema for updating a member's role.

    Note: Cannot change to 'owner' role. Owner transfer is a separate operation.

    Attributes:
        role: New role to assign (admin/member/viewer)
    """

    role: str = Field(
        ..., pattern="^(admin|member|viewer)$", description="New role (admin/member/viewer)"
    )
