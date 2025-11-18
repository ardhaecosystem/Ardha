"""
GitHub Integration request schemas for API validation.

This module defines Pydantic models for validating GitHub integration requests.
"""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field, field_validator


class GitHubIntegrationCreateRequest(BaseModel):
    """
    Request schema for creating a GitHub integration.

    Attributes:
        repository_owner: GitHub username or organization name
        repository_name: Repository name
        repository_url: Full GitHub repository URL
        access_token: Plain text OAuth token (will be encrypted)
        default_branch: Default branch name (default: main)
        auto_create_pr: Automatically create PRs from commits
        auto_link_tasks: Automatically link tasks from commit messages
        require_review: Enforce PR review requirements
        webhook_secret: Optional webhook secret for signature verification
    """

    repository_owner: str = Field(
        ...,
        min_length=1,
        max_length=255,
        description="GitHub username or organization name",
    )
    repository_name: str = Field(
        ...,
        min_length=1,
        max_length=255,
        description="Repository name",
    )
    repository_url: str = Field(
        ...,
        min_length=1,
        max_length=512,
        description="Full GitHub repository URL",
    )
    access_token: str = Field(
        ...,
        min_length=1,
        description="GitHub OAuth access token (will be encrypted)",
    )
    default_branch: str = Field(
        default="main",
        max_length=255,
        description="Default branch name",
    )
    auto_create_pr: bool = Field(
        default=False,
        description="Automatically create PRs from commits",
    )
    auto_link_tasks: bool = Field(
        default=True,
        description="Automatically link tasks from commit messages",
    )
    require_review: bool = Field(
        default=True,
        description="Enforce PR review requirements",
    )
    webhook_secret: str | None = Field(
        default=None,
        max_length=255,
        description="Webhook secret for signature verification",
    )

    @field_validator("repository_url")
    @classmethod
    def validate_repository_url(cls, v: str) -> str:
        """Validate GitHub repository URL format."""
        v = v.strip()
        if not v.startswith(("https://github.com/", "http://github.com/")):
            raise ValueError("Repository URL must be a valid GitHub URL")
        return v

    @field_validator("repository_owner", "repository_name")
    @classmethod
    def validate_repository_field(cls, v: str) -> str:
        """Validate repository owner and name."""
        v = v.strip()
        if not v:
            raise ValueError("Field cannot be empty or whitespace")
        # GitHub allows alphanumeric, hyphens, and underscores
        if not all(c.isalnum() or c in ("-", "_", ".") for c in v):
            raise ValueError("Invalid characters in repository identifier")
        return v


class GitHubIntegrationUpdateRequest(BaseModel):
    """
    Request schema for updating GitHub integration.

    All fields are optional. Only provided fields will be updated.
    Note: Cannot update project_id (immutable).

    Attributes:
        default_branch: New default branch name
        auto_create_pr: Update auto-create PR setting
        auto_link_tasks: Update auto-link tasks setting
        require_review: Update review requirement setting
        branch_protection_enabled: Update branch protection status
        webhook_secret: New webhook secret
        webhook_events: New list of webhook events
        is_active: Activate/deactivate integration
    """

    default_branch: str | None = Field(
        None,
        max_length=255,
        description="Default branch name",
    )
    auto_create_pr: bool | None = Field(
        None,
        description="Automatically create PRs from commits",
    )
    auto_link_tasks: bool | None = Field(
        None,
        description="Automatically link tasks from commit messages",
    )
    require_review: bool | None = Field(
        None,
        description="Enforce PR review requirements",
    )
    branch_protection_enabled: bool | None = Field(
        None,
        description="Enable branch protection",
    )
    webhook_secret: str | None = Field(
        None,
        max_length=255,
        description="Webhook secret for signature verification",
    )
    webhook_events: list[str] | None = Field(
        None,
        description="List of webhook events to subscribe to",
    )
    is_active: bool | None = Field(
        None,
        description="Activate or deactivate integration",
    )


class GitHubTokenRefreshRequest(BaseModel):
    """
    Request schema for refreshing GitHub OAuth token.

    Attributes:
        access_token: New access token
        refresh_token: New refresh token (optional)
        expires_at: Token expiration timestamp (optional)
    """

    access_token: str = Field(
        ...,
        min_length=1,
        description="New GitHub OAuth access token",
    )
    refresh_token: str | None = Field(
        default=None,
        description="New refresh token",
    )
    expires_at: datetime | None = Field(
        default=None,
        description="Token expiration timestamp",
    )


class PullRequestCreateRequest(BaseModel):
    """
    Request schema for creating a PR record from GitHub API data.

    Attributes:
        pr_number: GitHub PR number
        github_pr_id: GitHub's internal PR ID
        title: PR title
        description: PR description
        state: PR state (open, closed, merged, draft)
        head_branch: Source branch
        base_branch: Target branch
        head_sha: Latest commit SHA
        author_github_username: PR author's GitHub username
        html_url: GitHub PR web URL
        api_url: GitHub API URL
    """

    pr_number: int = Field(
        ...,
        gt=0,
        description="GitHub PR number",
    )
    github_pr_id: int = Field(
        ...,
        description="GitHub's internal PR ID",
    )
    title: str = Field(
        ...,
        min_length=1,
        max_length=500,
        description="PR title",
    )
    description: str | None = Field(
        default=None,
        description="PR description/body",
    )
    state: str = Field(
        default="open",
        pattern="^(open|closed|merged|draft)$",
        description="PR state",
    )
    head_branch: str = Field(
        ...,
        min_length=1,
        max_length=255,
        description="Source branch",
    )
    base_branch: str = Field(
        ...,
        min_length=1,
        max_length=255,
        description="Target branch",
    )
    head_sha: str = Field(
        ...,
        min_length=40,
        max_length=40,
        description="Latest commit SHA (40 characters)",
    )
    author_github_username: str = Field(
        ...,
        min_length=1,
        max_length=255,
        description="PR author's GitHub username",
    )
    html_url: str = Field(
        ...,
        min_length=1,
        max_length=512,
        description="GitHub PR web URL",
    )
    api_url: str = Field(
        ...,
        min_length=1,
        max_length=512,
        description="GitHub API URL for this PR",
    )

    @field_validator("head_sha")
    @classmethod
    def validate_sha(cls, v: str) -> str:
        """Validate commit SHA format (40 hex characters)."""
        v = v.strip().lower()
        if len(v) != 40:
            raise ValueError("SHA must be exactly 40 characters")
        if not all(c in "0123456789abcdef" for c in v):
            raise ValueError("SHA must contain only hexadecimal characters")
        return v


class PullRequestUpdateRequest(BaseModel):
    """
    Request schema for updating PR from GitHub API data.

    All fields are optional. Only provided fields will be updated.

    Attributes:
        title: New PR title
        description: New PR description
        state: New PR state
        head_sha: New latest commit SHA
        is_draft: Update draft status
        mergeable: Update mergeable status
        merged: Update merge status
        review_status: New review status
        checks_status: New checks status
        additions: Lines added count
        deletions: Lines deleted count
        changed_files: Files changed count
        commits_count: Commits count
    """

    title: str | None = Field(None, min_length=1, max_length=500, description="PR title")
    description: str | None = Field(None, description="PR description")
    state: str | None = Field(
        None,
        pattern="^(open|closed|merged|draft)$",
        description="PR state",
    )
    head_sha: str | None = Field(
        None,
        min_length=40,
        max_length=40,
        description="Latest commit SHA",
    )
    is_draft: bool | None = Field(None, description="Draft status")
    mergeable: bool | None = Field(None, description="Mergeable status")
    merged: bool | None = Field(None, description="Merge status")
    review_status: str | None = Field(
        None,
        pattern="^(pending|approved|changes_requested|dismissed)$",
        description="Review status",
    )
    checks_status: str | None = Field(
        None,
        pattern="^(pending|success|failure|error|cancelled)$",
        description="CI/CD checks status",
    )
    additions: int | None = Field(None, ge=0, description="Lines added")
    deletions: int | None = Field(None, ge=0, description="Lines deleted")
    changed_files: int | None = Field(None, ge=0, description="Files changed")
    commits_count: int | None = Field(None, ge=0, description="Commits count")


class GitHubWebhookRequest(BaseModel):
    """
    Request schema for receiving GitHub webhook.

    Attributes:
        event_type: Type of webhook event
        action: Event action
        payload: Full webhook payload
        signature: X-Hub-Signature-256 header value
        delivery_id: GitHub's delivery UUID
    """

    event_type: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="Type of webhook event",
    )
    action: str | None = Field(
        default=None,
        max_length=100,
        description="Event action",
    )
    payload: dict = Field(
        ...,
        description="Full webhook payload",
    )
    signature: str | None = Field(
        default=None,
        max_length=255,
        description="X-Hub-Signature-256 header value",
    )
    delivery_id: str = Field(
        ...,
        min_length=1,
        max_length=255,
        description="GitHub's delivery UUID",
    )


class PRTaskLinkRequest(BaseModel):
    """
    Request schema for linking tasks to a PR.

    Attributes:
        task_ids: List of task UUIDs to link
        link_type: Type of link (mentioned, implements, closes, related)
    """

    task_ids: list[UUID] = Field(
        ...,
        min_length=1,
        description="List of task UUIDs to link",
    )
    link_type: str = Field(
        default="mentioned",
        pattern="^(mentioned|implements|closes|related)$",
        description="Type of link",
    )
