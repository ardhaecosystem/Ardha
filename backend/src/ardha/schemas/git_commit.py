"""
Pydantic schemas for GitCommit model.

This module defines request and response schemas for git commit operations.
"""

from datetime import datetime
from enum import Enum
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from ardha.schemas.file import ChangeType


class LinkType(str, Enum):
    """Task-commit link type."""

    MENTIONED = "mentioned"
    CLOSES = "closes"
    FIXES = "fixes"
    IMPLEMENTS = "implements"


# ============= Request Schemas =============


class GitCommitBase(BaseModel):
    """Base git commit schema with common fields."""

    sha: str = Field(
        ..., min_length=40, max_length=40, description="Full git commit hash (40 chars)"
    )
    message: str = Field(..., min_length=1, max_length=10000, description="Commit message")
    author_name: str = Field(..., min_length=1, max_length=255, description="Git author name")
    author_email: str = Field(..., min_length=1, max_length=255, description="Git author email")
    branch: str = Field(..., min_length=1, max_length=255, description="Branch name")
    committed_at: datetime = Field(..., description="Git commit timestamp")

    @field_validator("sha")
    @classmethod
    def validate_sha_format(cls, v: str) -> str:
        """Validate SHA is 40 hex characters."""
        if not all(c in "0123456789abcdefABCDEF" for c in v):
            raise ValueError("SHA must be 40 hexadecimal characters")
        return v.lower()


class GitCommitCreate(GitCommitBase):
    """Schema for creating a new git commit."""

    pushed_at: datetime | None = None
    is_merge: bool = False
    parent_shas: list[str] | None = None
    files_changed: int = Field(0, ge=0)
    insertions: int = Field(0, ge=0)
    deletions: int = Field(0, ge=0)
    ardha_user_id: UUID | None = Field(None, description="Mapped Ardha user")

    @field_validator("parent_shas")
    @classmethod
    def validate_parent_shas(cls, v: list[str] | None) -> list[str] | None:
        """Validate parent SHAs are valid format."""
        if v is None:
            return v
        for sha in v:
            if len(sha) != 40 or not all(c in "0123456789abcdefABCDEF" for c in sha):
                raise ValueError(f"Invalid parent SHA format: {sha}")
        return [sha.lower() for sha in v]


class GitCommitUpdate(BaseModel):
    """Schema for updating a git commit."""

    message: str | None = Field(None, min_length=1, max_length=10000)
    pushed_at: datetime | None = None
    ardha_user_id: UUID | None = None
    linked_task_ids: list[str] | None = None
    closes_task_ids: list[str] | None = None


# ============= Response Schemas =============


class GitCommitResponse(GitCommitBase):
    """Schema for git commit response."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    project_id: UUID
    short_sha: str = Field(..., description="Short commit hash (7 chars)")
    is_merge: bool = False
    parent_shas: list[str] | None = None
    files_changed: int = 0
    insertions: int = 0
    deletions: int = 0
    linked_task_ids: list[str] | None = None
    closes_task_ids: list[str] | None = None
    ardha_user_id: UUID | None = None
    pushed_at: datetime | None = None
    synced_at: datetime | None = None
    created_at: datetime
    updated_at: datetime

    # Computed fields
    time_ago: str | None = Field(None, description="Human-readable time since commit")
    linked_tasks_count: int = Field(0, description="Number of linked tasks")
    closes_tasks_count: int = Field(0, description="Number of closed tasks")


class GitCommitWithDiff(GitCommitResponse):
    """Schema for git commit response with diff information."""

    file_changes: list["FileChangeDetail"] = Field(
        default_factory=list, description="Detailed file changes"
    )
    diff_summary: str | None = Field(None, description="Summary of changes")
    stats_summary: str = Field(..., description="Stats like '+123 -45 (5 files)'")


class FileChangeDetail(BaseModel):
    """Detailed file change information."""

    model_config = ConfigDict(from_attributes=True)

    file_id: UUID | None = None
    path: str
    change_type: ChangeType
    old_path: str | None = None
    insertions: int = 0
    deletions: int = 0
    language: str | None = None
    file_type: str | None = None


class GitCommitListResponse(BaseModel):
    """Schema for paginated git commit list."""

    commits: list[GitCommitResponse]
    total: int = Field(..., description="Total number of commits")
    page: int = Field(1, ge=1, description="Current page number")
    page_size: int = Field(10, ge=1, le=100, description="Items per page")
    has_next: bool = Field(False, description="Whether there are more pages")
    branch: str | None = Field(None, description="Filtered branch name")


class GitCommitFilterRequest(BaseModel):
    """Schema for git commit filtering."""

    branch: str | None = Field(None, description="Filter by branch name")
    author_email: str | None = Field(None, description="Filter by author email")
    since: datetime | None = Field(None, description="Filter commits after this date")
    until: datetime | None = Field(None, description="Filter commits before this date")
    search: str | None = Field(None, description="Search in commit messages")
    page: int = Field(1, ge=1)
    page_size: int = Field(20, ge=1, le=100)


class GitCommitStatsResponse(BaseModel):
    """Schema for git commit statistics."""

    total_commits: int
    total_insertions: int
    total_deletions: int
    total_files_changed: int
    branches: list[str]
    top_contributors: list["ContributorStats"]
    recent_activity: list["DailyActivity"]


class ContributorStats(BaseModel):
    """Statistics for a contributor."""

    name: str
    email: str
    commit_count: int
    insertions: int
    deletions: int
    ardha_user_id: UUID | None = None


class DailyActivity(BaseModel):
    """Daily commit activity."""

    date: datetime
    commit_count: int
    insertions: int
    deletions: int
    files_changed: int


class TaskLinkRequest(BaseModel):
    """Schema for linking commit to tasks."""

    task_ids: list[str] = Field(..., min_length=1, description="Task identifiers to link")
    link_type: LinkType = Field(LinkType.MENTIONED, description="Type of link")


class TaskLinkResponse(BaseModel):
    """Schema for task link response."""

    commit_id: UUID
    task_id: UUID
    task_identifier: str
    link_type: LinkType
    linked_at: datetime
