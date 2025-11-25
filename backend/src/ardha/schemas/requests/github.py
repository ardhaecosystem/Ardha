"""
GitHub API request schemas for input validation.

This module defines Pydantic models for validating GitHub integration
and pull request API requests.
"""

from typing import List, Optional

from pydantic import BaseModel, Field, field_validator


class CreateGitHubIntegrationRequest(BaseModel):
    """Request schema for creating GitHub integration."""

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
    access_token: str = Field(
        ...,
        min_length=1,
        description="GitHub personal access token or OAuth token",
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
    configuration: Optional[dict] = Field(
        default=None,
        description="Additional configuration options",
    )

    @field_validator("repository_owner", "repository_name")
    @classmethod
    def validate_no_whitespace(cls, v: str) -> str:
        """Ensure no leading/trailing whitespace."""
        if v != v.strip():
            raise ValueError("Repository owner/name cannot have leading/trailing whitespace")
        return v.strip()


class UpdateGitHubIntegrationRequest(BaseModel):
    """Request schema for updating GitHub integration."""

    access_token: Optional[str] = Field(
        default=None,
        min_length=1,
        description="New GitHub access token",
    )
    auto_create_pr: Optional[bool] = Field(
        default=None,
        description="Update auto-create PR setting",
    )
    auto_link_tasks: Optional[bool] = Field(
        default=None,
        description="Update auto-link tasks setting",
    )
    require_review: Optional[bool] = Field(
        default=None,
        description="Update review requirement setting",
    )
    is_active: Optional[bool] = Field(
        default=None,
        description="Activate or deactivate integration",
    )


class SetupWebhookRequest(BaseModel):
    """Request schema for setting up GitHub webhook."""

    webhook_url: str = Field(
        ...,
        min_length=1,
        max_length=512,
        description="Webhook callback URL",
    )
    events: List[str] = Field(
        default=["pull_request", "push", "pull_request_review", "check_suite"],
        description="Webhook events to subscribe to",
    )

    @field_validator("webhook_url")
    @classmethod
    def validate_url(cls, v: str) -> str:
        """Ensure webhook URL is valid."""
        if not v.startswith(("http://", "https://")):
            raise ValueError("Webhook URL must start with http:// or https://")
        return v

    @field_validator("events")
    @classmethod
    def validate_events(cls, v: List[str]) -> List[str]:
        """Ensure events list is not empty."""
        if not v:
            raise ValueError("Must specify at least one webhook event")
        return v


class CreatePullRequestRequest(BaseModel):
    """Request schema for creating pull request."""

    title: str = Field(
        ...,
        min_length=1,
        max_length=500,
        description="PR title",
    )
    body: str = Field(
        default="",
        description="PR description/body",
    )
    head_branch: str = Field(
        ...,
        min_length=1,
        max_length=255,
        description="Source branch with changes",
    )
    base_branch: Optional[str] = Field(
        default=None,
        max_length=255,
        description="Target branch (defaults to repository default branch)",
    )
    draft: bool = Field(
        default=False,
        description="Create as draft PR",
    )
    linked_task_ids: Optional[List[str]] = Field(
        default=None,
        description="Task UUIDs to link to this PR",
    )

    @field_validator("title")
    @classmethod
    def validate_title(cls, v: str) -> str:
        """Ensure title has no leading/trailing whitespace."""
        if v != v.strip():
            raise ValueError("PR title cannot have leading/trailing whitespace")
        return v.strip()


class MergePRRequest(BaseModel):
    """Request schema for merging pull request."""

    merge_method: str = Field(
        default="merge",
        description="Merge method: merge, squash, or rebase",
    )
    commit_message: Optional[str] = Field(
        default=None,
        max_length=1000,
        description="Optional merge commit message",
    )

    @field_validator("merge_method")
    @classmethod
    def validate_merge_method(cls, v: str) -> str:
        """Ensure merge method is valid."""
        if v not in ("merge", "squash", "rebase"):
            raise ValueError("Merge method must be 'merge', 'squash', or 'rebase'")
        return v


class SyncPullRequestsRequest(BaseModel):
    """Request schema for syncing pull requests from GitHub."""

    full_sync: bool = Field(
        default=False,
        description="If True, sync all PRs; if False, sync only recent",
    )
