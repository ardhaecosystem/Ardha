"""
GitHub API response schemas for output formatting.

This module defines Pydantic models for formatting GitHub integration
and pull request API responses.
"""

from datetime import datetime
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class GitHubIntegrationResponse(BaseModel):
    """Response schema for GitHub integration details."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    project_id: UUID
    repository_owner: str
    repository_name: str
    repository_url: str
    default_branch: str
    auto_create_pr: bool
    auto_link_tasks: bool
    require_review: bool
    branch_protection_enabled: bool
    webhook_url: Optional[str] = None
    webhook_events: Optional[List[str]] = None
    is_active: bool
    last_sync_at: Optional[datetime] = None
    sync_error: Optional[str] = None
    connection_status: str
    total_prs: int
    merged_prs: int
    closed_prs: int
    webhook_events_received: int
    created_by_user_id: UUID
    created_at: datetime
    updated_at: datetime


class PullRequestResponse(BaseModel):
    """Response schema for pull request details."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    github_integration_id: UUID
    project_id: UUID
    pr_number: int
    github_pr_id: int
    title: str
    description: Optional[str] = None
    state: str
    head_branch: str
    base_branch: str
    head_sha: str
    author_github_username: str
    author_user_id: Optional[UUID] = None
    is_draft: bool
    mergeable: Optional[bool] = None
    merged: bool
    merged_at: Optional[datetime] = None
    merged_by_github_username: Optional[str] = None
    closed_at: Optional[datetime] = None
    review_status: str
    reviews_count: int
    approvals_count: int
    checks_status: str
    checks_count: int
    required_checks_passed: bool
    additions: int
    deletions: int
    changed_files: int
    commits_count: int
    html_url: str
    api_url: str
    linked_task_ids: Optional[List[str]] = None
    closes_task_ids: Optional[List[str]] = None
    created_at: datetime
    updated_at: datetime
    synced_at: datetime


class PullRequestWithDetailsResponse(PullRequestResponse):
    """Extended PR response with task and commit details."""

    linked_tasks: List[dict] = Field(
        default_factory=list,
        description="Linked task details",
    )
    commits: List[dict] = Field(
        default_factory=list,
        description="PR commits",
    )


class PaginatedPRResponse(BaseModel):
    """Response schema for paginated pull request list."""

    prs: List[PullRequestResponse]
    total: int
    skip: int
    limit: int


class WebhookResponse(BaseModel):
    """Response schema for webhook setup."""

    webhook_id: int
    webhook_url: str
    events: List[str]
    active: bool
    created_at: Optional[datetime] = None
    secret_configured: bool


class GitHubStatsResponse(BaseModel):
    """Response schema for GitHub project statistics."""

    total_prs: int = Field(
        description="Total pull requests",
    )
    open_prs: int = Field(
        description="Open pull requests",
    )
    merged_prs: int = Field(
        description="Merged pull requests",
    )
    closed_prs: int = Field(
        description="Closed pull requests",
    )
    average_merge_time_hours: Optional[float] = Field(
        default=None,
        description="Average time to merge in hours",
    )
    total_commits: int = Field(
        description="Total commits tracked",
    )
    contributor_count: int = Field(
        description="Unique contributors",
    )
    most_active_contributors: List[dict] = Field(
        default_factory=list,
        description="Top contributors by PR count",
    )


class GitHubConnectionStatusResponse(BaseModel):
    """Response schema for verifying GitHub connection."""

    connected: bool
    connection_status: str
    repository_accessible: bool
    token_valid: bool
    webhook_configured: bool
    last_sync_at: Optional[datetime] = None
    error_message: Optional[str] = None


class WebhookDeliveryResponse(BaseModel):
    """Response schema for webhook delivery status."""

    status: str = Field(
        description="Processing status: received, queued, processed, failed",
    )
    delivery_id: str = Field(
        description="GitHub webhook delivery UUID",
    )
    event_type: str = Field(
        description="GitHub event type (pull_request, push, etc.)",
    )
    received_at: datetime = Field(
        description="When webhook was received",
    )
