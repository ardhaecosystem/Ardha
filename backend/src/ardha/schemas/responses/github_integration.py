"""
GitHub Integration response schemas for API responses.

This module defines Pydantic models for GitHub integration API responses.
"""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, computed_field


class GitHubIntegrationResponse(BaseModel):
    """
    Response schema for GitHub integration.

    Excludes encrypted tokens for security.

    Attributes:
        id: Integration UUID
        project_id: Associated project UUID
        repository_owner: GitHub username or organization
        repository_name: Repository name
        repository_url: Full repository URL
        default_branch: Default branch name
        token_expires_at: Token expiration timestamp
        installation_id: GitHub App installation ID
        auto_create_pr: Auto-create PR setting
        auto_link_tasks: Auto-link tasks setting
        require_review: Review requirement setting
        branch_protection_enabled: Branch protection status
        webhook_url: Registered webhook URL
        webhook_events: Subscribed webhook events
        is_active: Whether integration is active
        last_sync_at: Last sync timestamp
        sync_error: Last sync error message
        connection_status: Connection state
        total_prs: Total PRs tracked
        merged_prs: Merged PRs count
        closed_prs: Closed PRs count
        webhook_events_received: Webhook events received count
        created_by_user_id: Creator user UUID
        created_at: Creation timestamp
        updated_at: Last update timestamp
    """

    id: UUID = Field(description="Integration UUID")
    project_id: UUID = Field(description="Associated project UUID")
    repository_owner: str = Field(description="GitHub username or organization")
    repository_name: str = Field(description="Repository name")
    repository_url: str = Field(description="Full repository URL")
    default_branch: str = Field(description="Default branch name")
    token_expires_at: datetime | None = Field(
        default=None,
        description="Token expiration timestamp",
    )
    installation_id: int | None = Field(
        default=None,
        description="GitHub App installation ID",
    )
    auto_create_pr: bool = Field(description="Auto-create PR setting")
    auto_link_tasks: bool = Field(description="Auto-link tasks setting")
    require_review: bool = Field(description="Review requirement setting")
    branch_protection_enabled: bool = Field(description="Branch protection status")
    webhook_url: str | None = Field(default=None, description="Registered webhook URL")
    webhook_events: list[str] | None = Field(
        default=None,
        description="Subscribed webhook events",
    )
    is_active: bool = Field(description="Whether integration is active")
    last_sync_at: datetime | None = Field(
        default=None,
        description="Last sync timestamp",
    )
    sync_error: str | None = Field(default=None, description="Last sync error message")
    connection_status: str = Field(description="Connection state")
    total_prs: int = Field(description="Total PRs tracked")
    merged_prs: int = Field(description="Merged PRs count")
    closed_prs: int = Field(description="Closed PRs count")
    webhook_events_received: int = Field(description="Webhook events received count")
    created_by_user_id: UUID = Field(description="Creator user UUID")
    created_at: datetime = Field(description="Creation timestamp")
    updated_at: datetime = Field(description="Last update timestamp")

    @computed_field
    @property
    def repository_full_name(self) -> str:
        """Computed field for owner/repo format."""
        return f"{self.repository_owner}/{self.repository_name}"

    model_config = ConfigDict(
        from_attributes=True,
        json_encoders={
            datetime: lambda v: v.isoformat(),
            UUID: lambda v: str(v),
        },
    )


class GitHubIntegrationListResponse(BaseModel):
    """Response model for list of GitHub integrations."""

    integrations: list[GitHubIntegrationResponse] = Field(
        description="List of GitHub integrations"
    )
    total_count: int = Field(description="Total number of integrations")

    model_config = ConfigDict(
        json_encoders={
            datetime: lambda v: v.isoformat(),
            UUID: lambda v: str(v),
        }
    )


class PullRequestResponse(BaseModel):
    """
    Response schema for pull request.

    Attributes:
        id: PR UUID
        github_integration_id: GitHub integration UUID
        project_id: Project UUID
        pr_number: GitHub PR number
        github_pr_id: GitHub's internal PR ID
        title: PR title
        description: PR description
        state: PR state
        head_branch: Source branch
        base_branch: Target branch
        head_sha: Latest commit SHA
        author_github_username: Author's GitHub username
        author_user_id: Mapped Ardha user UUID
        is_draft: Draft status
        mergeable: Mergeable status
        merged: Merge status
        merged_at: Merge timestamp
        merged_by_github_username: User who merged
        closed_at: Close timestamp
        review_status: Review state
        reviews_count: Total reviews
        approvals_count: Approval count
        checks_status: CI/CD checks status
        checks_count: Total checks
        required_checks_passed: Required checks passed
        additions: Lines added
        deletions: Lines deleted
        changed_files: Files changed
        commits_count: Commits count
        html_url: GitHub PR web URL
        api_url: GitHub API URL
        linked_task_ids: Linked task UUIDs
        closes_task_ids: Tasks to close
        created_at: Creation timestamp
        updated_at: Last update timestamp
        synced_at: Last sync timestamp
    """

    id: UUID = Field(description="PR UUID")
    github_integration_id: UUID = Field(description="GitHub integration UUID")
    project_id: UUID = Field(description="Project UUID")
    pr_number: int = Field(description="GitHub PR number")
    github_pr_id: int = Field(description="GitHub's internal PR ID")
    title: str = Field(description="PR title")
    description: str | None = Field(default=None, description="PR description")
    state: str = Field(description="PR state")
    head_branch: str = Field(description="Source branch")
    base_branch: str = Field(description="Target branch")
    head_sha: str = Field(description="Latest commit SHA")
    author_github_username: str = Field(description="Author's GitHub username")
    author_user_id: UUID | None = Field(default=None, description="Mapped Ardha user UUID")
    is_draft: bool = Field(description="Draft status")
    mergeable: bool | None = Field(default=None, description="Mergeable status")
    merged: bool = Field(description="Merge status")
    merged_at: datetime | None = Field(default=None, description="Merge timestamp")
    merged_by_github_username: str | None = Field(
        default=None,
        description="User who merged",
    )
    closed_at: datetime | None = Field(default=None, description="Close timestamp")
    review_status: str = Field(description="Review state")
    reviews_count: int = Field(description="Total reviews")
    approvals_count: int = Field(description="Approval count")
    checks_status: str = Field(description="CI/CD checks status")
    checks_count: int = Field(description="Total checks")
    required_checks_passed: bool = Field(description="Required checks passed")
    additions: int = Field(description="Lines added")
    deletions: int = Field(description="Lines deleted")
    changed_files: int = Field(description="Files changed")
    commits_count: int = Field(description="Commits count")
    html_url: str = Field(description="GitHub PR web URL")
    api_url: str = Field(description="GitHub API URL")
    linked_task_ids: list[str] | None = Field(default=None, description="Linked task UUIDs")
    closes_task_ids: list[str] | None = Field(default=None, description="Tasks to close")
    created_at: datetime = Field(description="Creation timestamp")
    updated_at: datetime = Field(description="Last update timestamp")
    synced_at: datetime = Field(description="Last sync timestamp")

    @computed_field
    @property
    def is_mergeable_computed(self) -> bool:
        """Computed field for mergeable status."""
        return self.mergeable is True

    @computed_field
    @property
    def is_approved_computed(self) -> bool:
        """Computed field for approved status."""
        return self.review_status == "approved"

    model_config = ConfigDict(
        from_attributes=True,
        json_encoders={
            datetime: lambda v: v.isoformat(),
            UUID: lambda v: str(v),
        },
    )


class PullRequestListResponse(BaseModel):
    """Response model for list of pull requests."""

    pull_requests: list[PullRequestResponse] = Field(description="List of pull requests")
    total_count: int = Field(description="Total number of pull requests")

    model_config = ConfigDict(
        json_encoders={
            datetime: lambda v: v.isoformat(),
            UUID: lambda v: str(v),
        }
    )


class GitHubWebhookResponse(BaseModel):
    """
    Response schema for webhook delivery.

    Excludes full payload for performance.

    Attributes:
        id: Webhook delivery UUID
        github_integration_id: GitHub integration UUID
        delivery_id: GitHub's delivery UUID
        event_type: Type of webhook event
        action: Event action
        payload_size: Payload size in bytes
        status: Processing status
        processed_at: Processing timestamp
        error_message: Processing error message
        retry_count: Retry attempt count
        signature_verified: Whether signature verified
        pr_number: Related PR number
        commit_sha: Related commit SHA
        related_entity_type: Related entity type
        related_entity_id: Ardha entity UUID
        received_at: Receipt timestamp
        processed_by: Processing worker/service
        created_at: Creation timestamp
        updated_at: Last update timestamp
    """

    id: UUID = Field(description="Webhook delivery UUID")
    github_integration_id: UUID = Field(description="GitHub integration UUID")
    delivery_id: str = Field(description="GitHub's delivery UUID")
    event_type: str = Field(description="Type of webhook event")
    action: str | None = Field(default=None, description="Event action")
    payload_size: int = Field(description="Payload size in bytes")
    status: str = Field(description="Processing status")
    processed_at: datetime | None = Field(default=None, description="Processing timestamp")
    error_message: str | None = Field(default=None, description="Processing error message")
    retry_count: int = Field(description="Retry attempt count")
    signature_verified: bool = Field(description="Whether signature verified")
    pr_number: int | None = Field(default=None, description="Related PR number")
    commit_sha: str | None = Field(default=None, description="Related commit SHA")
    related_entity_type: str | None = Field(default=None, description="Related entity type")
    related_entity_id: UUID | None = Field(default=None, description="Ardha entity UUID")
    received_at: datetime = Field(description="Receipt timestamp")
    processed_by: str | None = Field(default=None, description="Processing worker/service")
    created_at: datetime = Field(description="Creation timestamp")
    updated_at: datetime = Field(description="Last update timestamp")

    model_config = ConfigDict(
        from_attributes=True,
        json_encoders={
            datetime: lambda v: v.isoformat(),
            UUID: lambda v: str(v),
        },
    )


class GitHubWebhookListResponse(BaseModel):
    """Response model for list of webhook deliveries."""

    webhooks: list[GitHubWebhookResponse] = Field(description="List of webhook deliveries")
    total_count: int = Field(description="Total number of webhooks")

    model_config = ConfigDict(
        json_encoders={
            datetime: lambda v: v.isoformat(),
            UUID: lambda v: str(v),
        }
    )


class GitHubConnectionStatusResponse(BaseModel):
    """Response schema for checking GitHub connection status."""

    is_connected: bool = Field(description="Whether integration is connected")
    connection_status: str = Field(description="Connection state")
    repository_full_name: str = Field(description="Repository in owner/repo format")
    last_sync_at: datetime | None = Field(default=None, description="Last sync timestamp")
    sync_error: str | None = Field(default=None, description="Last sync error")
    total_prs: int = Field(description="Total PRs tracked")
    webhook_events_received: int = Field(description="Webhook events received")

    model_config = ConfigDict(
        json_encoders={
            datetime: lambda v: v.isoformat(),
        }
    )