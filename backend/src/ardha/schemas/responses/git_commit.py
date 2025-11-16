"""
Response schemas for Git commit operations.

This module defines Pydantic schemas for git-related API responses.
"""

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from ardha.schemas.git_commit import (
    GitCommitResponse,
    GitCommitWithDiff,
    GitCommitListResponse,
    FileChangeDetail,
    ContributorStats,
    DailyActivity,
    TaskLinkResponse,
)


class GitStatusResponse(BaseModel):
    """Schema for git repository status."""
    
    untracked: list[str] = Field(default_factory=list)
    modified: list[str] = Field(default_factory=list)
    staged: list[str] = Field(default_factory=list)
    deleted: list[str] = Field(default_factory=list)
    renamed: list[tuple[str, str]] = Field(default_factory=list)
    counts: dict = Field(
        default_factory=lambda: {
            "untracked": 0,
            "modified": 0,
            "staged": 0,
            "deleted": 0,
            "renamed": 0,
        }
    )
    is_clean: bool = Field(True, description="Whether working directory is clean")
    current_branch: str = Field(..., description="Current branch name")


class GitDiffResponse(BaseModel):
    """Schema for git diff response."""
    
    diff: str = Field(..., description="Unified diff output")
    file_path: Optional[str] = Field(None, description="File path if specific file diff")
    ref1: Optional[str] = Field(None, description="First reference")
    ref2: Optional[str] = Field(None, description="Second reference")
    insertions: int = Field(0, description="Total lines added")
    deletions: int = Field(0, description="Total lines removed")
    files_changed: int = Field(0, description="Number of files changed")


class GitBranchResponse(BaseModel):
    """Schema for git branches response."""
    
    branches: list[str] = Field(..., description="List of branch names")
    current: str = Field(..., description="Current branch name")
    remote_branches: list[str] = Field(default_factory=list, description="Remote branches")


class GitPushResponse(BaseModel):
    """Schema for git push response."""
    
    success: bool = Field(True, description="Whether push was successful")
    pushed_count: int = Field(0, description="Number of commits pushed")
    branch: str = Field(..., description="Branch that was pushed")
    remote: str = Field("origin", description="Remote that was pushed to")
    errors: list[str] = Field(default_factory=list)


class GitPullResponse(BaseModel):
    """Schema for git pull response."""
    
    success: bool = Field(True, description="Whether pull was successful")
    new_commits: int = Field(0, description="Number of new commits pulled")
    branch: str = Field(..., description="Branch that was pulled")
    remote: str = Field("origin", description="Remote that was pulled from")
    conflicts: list[str] = Field(default_factory=list, description="Merge conflicts if any")
    errors: list[str] = Field(default_factory=list)


class GitCommitWithDiffResponse(GitCommitWithDiff):
    """Schema for git commit response with diff."""
    
    model_config = ConfigDict(from_attributes=True)


class GitRevertResponse(BaseModel):
    """Schema for git revert response."""
    
    success: bool = Field(True, description="Whether revert was successful")
    original_commit: GitCommitResponse = Field(..., description="Original commit that was reverted")
    revert_commit: GitCommitResponse = Field(..., description="New revert commit")
    conflicts: list[str] = Field(default_factory=list, description="Merge conflicts if any")


class GitSyncResponse(BaseModel):
    """Schema for git sync response."""
    
    synced_commits: int = Field(0, description="Number of commits synced")
    new_commits: int = Field(0, description="Number of new commits added")
    updated_commits: int = Field(0, description="Number of commits updated")
    linked_tasks: int = Field(0, description="Number of tasks linked to commits")
    errors: list[str] = Field(default_factory=list)


class GitStatsResponse(BaseModel):
    """Schema for git repository statistics."""
    
    total_commits: int
    total_insertions: int
    total_deletions: int
    total_files_changed: int
    branches: list[str]
    top_contributors: list[ContributorStats]
    recent_activity: list[DailyActivity]
    first_commit_date: Optional[datetime] = None
    last_commit_date: Optional[datetime] = None
    active_days: int = Field(0, description="Number of days with commits")


class GitFileHistoryResponse(BaseModel):
    """Schema for file commit history."""
    
    file_id: UUID
    file_path: str
    commits: list[GitCommitResponse]
    total_commits: int
    first_commit: Optional[GitCommitResponse] = None
    last_commit: Optional[GitCommitResponse] = None


class GitOperationResponse(BaseModel):
    """Schema for generic git operation responses."""
    
    success: bool = Field(True, description="Whether operation was successful")
    message: str = Field(..., description="Operation result message")
    data: Optional[dict] = Field(None, description="Additional operation data")
    errors: list[str] = Field(default_factory=list)


class GitCommitWithFilesResponse(BaseModel):
    """Schema for git commit with file changes."""
    
    id: UUID
    sha: str
    short_sha: str
    message: str
    author_name: str
    author_email: str
    branch: str
    committed_at: datetime
    is_merge: bool
    files_changed: int
    insertions: int
    deletions: int
    linked_task_ids: list[str]
    closes_task_ids: list[str]
    file_changes: list[FileChangeDetail]


class GitCommitStatsResponse(BaseModel):
    """Schema for git commit statistics."""
    
    total_commits: int
    total_insertions: int
    total_deletions: int
    total_files_changed: int
    branches: list[str]
    top_contributors: list[ContributorStats]