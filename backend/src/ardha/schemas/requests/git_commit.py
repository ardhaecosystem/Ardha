"""
Request schemas for Git commit operations.

This module defines Pydantic schemas for git-related API requests.
"""

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field, field_validator

from ardha.schemas.git_commit import LinkType


class CreateCommitRequest(BaseModel):
    """Schema for creating a git commit."""

    project_id: UUID = Field(..., description="Project UUID")
    message: str = Field(..., min_length=1, max_length=10000, description="Commit message")
    file_ids: Optional[list[UUID]] = Field(
        None, description="Specific files to commit (null for all staged)"
    )
    author_name: Optional[str] = Field(None, description="Override git author name")
    author_email: Optional[str] = Field(None, description="Override git author email")

    @field_validator("author_email")
    @classmethod
    def validate_email(cls, v: Optional[str]) -> Optional[str]:
        """Validate email format if provided."""
        if v is None:
            return v
        if "@" not in v or "." not in v.split("@")[-1]:
            raise ValueError("Invalid email format")
        return v


class GitPushRequest(BaseModel):
    """Schema for pushing commits to remote."""

    branch: Optional[str] = Field(None, description="Branch to push (null for current)")
    remote: str = Field("origin", description="Remote name")
    force: bool = Field(False, description="Force push (use with caution)")


class GitPullRequest(BaseModel):
    """Schema for pulling commits from remote."""

    branch: Optional[str] = Field(None, description="Branch to pull (null for current)")
    remote: str = Field("origin", description="Remote name")


class CreateBranchRequest(BaseModel):
    """Schema for creating a new branch."""

    name: str = Field(..., min_length=1, max_length=255, description="Branch name")
    start_point: Optional[str] = Field(None, description="Starting point (commit SHA or branch)")


class CheckoutBranchRequest(BaseModel):
    """Schema for switching branches."""

    branch: str = Field(..., min_length=1, max_length=255, description="Branch name")
    create: bool = Field(False, description="Create branch if it doesn't exist")


class GitCommitListRequest(BaseModel):
    """Schema for listing git commits."""

    branch: Optional[str] = Field(None, description="Filter by branch name")
    author_email: Optional[str] = Field(None, description="Filter by author email")
    since: Optional[datetime] = Field(None, description="Filter commits after this date")
    until: Optional[datetime] = Field(None, description="Filter commits before this date")
    search: Optional[str] = Field(None, description="Search in commit messages")
    skip: int = Field(0, ge=0, description="Number of commits to skip")
    limit: int = Field(50, ge=1, le=100, description="Maximum commits to return")


class TaskLinkRequest(BaseModel):
    """Schema for linking commit to tasks."""

    task_ids: list[str] = Field(..., min_length=1, description="Task identifiers to link")
    link_type: LinkType = Field(LinkType.MENTIONED, description="Type of link")


class LinkTasksRequest(BaseModel):
    """Schema for linking commit to tasks (alias for TaskLinkRequest)."""

    task_ids: list[str] = Field(..., min_length=1, description="Task identifiers to link")
    link_type: LinkType = Field(LinkType.MENTIONED, description="Type of link")


class SyncCommitsRequest(BaseModel):
    """Schema for syncing commits from git."""

    branch: Optional[str] = Field(None, description="Filter by branch")
    since: Optional[datetime] = Field(None, description="Filter commits since this date")


class GitStatusRequest(BaseModel):
    """Schema for getting git status."""

    include_untracked: bool = Field(True, description="Include untracked files")
    include_ignored: bool = Field(False, description="Include ignored files")


class GitDiffRequest(BaseModel):
    """Schema for getting git diff."""

    ref1: Optional[str] = Field(None, description="First reference (commit, branch)")
    ref2: Optional[str] = Field(None, description="Second reference (commit, branch)")
    file_path: Optional[str] = Field(None, description="Specific file path for diff")
    context_lines: int = Field(3, ge=0, le=50, description="Number of context lines")
