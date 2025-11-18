"""
GitHub Integration models for repository management.

This module defines models for GitHub integration including:
- GitHubIntegration: OAuth configuration and repository connection
- PullRequest: PR lifecycle tracking and task linking
"""

import hashlib
import hmac
from datetime import datetime, timezone
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import (
    JSON,
    BigInteger,
    Boolean,
    CheckConstraint,
    Column,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    String,
    Table,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from ardha.models.base import Base, BaseModel

if TYPE_CHECKING:
    from ardha.models.git_commit import GitCommit
    from ardha.models.github_webhook import GitHubWebhookDelivery
    from ardha.models.project import Project
    from ardha.models.task import Task
    from ardha.models.user import User


# Association table for pull request to task many-to-many relationship
pr_tasks = Table(
    "pr_tasks",
    Base.metadata,
    Column(
        "pr_id",
        PG_UUID(as_uuid=True),
        ForeignKey("pull_requests.id", ondelete="CASCADE"),
        primary_key=True,
    ),
    Column(
        "task_id",
        PG_UUID(as_uuid=True),
        ForeignKey("tasks.id", ondelete="CASCADE"),
        primary_key=True,
    ),
    Column(
        "link_type",
        String(20),
        nullable=False,
        comment="Type of link: mentioned, implements, closes, related",
    ),
    Column(
        "linked_at",
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        comment="When this link was created",
    ),
    Column(
        "linked_from",
        String(50),
        nullable=False,
        comment="Source of link: commit_message, pr_description, pr_comment",
    ),
    Index("ix_pr_tasks_pr", "pr_id"),
    Index("ix_pr_tasks_task", "task_id"),
    Index("ix_pr_tasks_link_type", "link_type"),
)


# Association table for pull request to commit many-to-many relationship
pr_commits = Table(
    "pr_commits",
    Base.metadata,
    Column(
        "pr_id",
        PG_UUID(as_uuid=True),
        ForeignKey("pull_requests.id", ondelete="CASCADE"),
        primary_key=True,
    ),
    Column(
        "commit_id",
        PG_UUID(as_uuid=True),
        ForeignKey("git_commits.id", ondelete="CASCADE"),
        primary_key=True,
    ),
    Column(
        "position",
        Integer,
        nullable=False,
        default=0,
        comment="Order of this commit in the PR",
    ),
    Column(
        "added_at",
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        comment="When this commit was added to the PR",
    ),
    Index("ix_pr_commits_pr", "pr_id"),
    Index("ix_pr_commits_commit", "commit_id"),
    Index("ix_pr_commits_position", "position"),
)


class GitHubIntegration(Base, BaseModel):
    """
    GitHub Integration model for OAuth configuration and repository management.

    Represents a one-to-one connection between an Ardha project and a GitHub
    repository, including OAuth credentials, webhook configuration, and sync status.

    Attributes:
        project_id: Foreign key to associated project (unique)
        repository_owner: GitHub username or organization name
        repository_name: Repository name
        repository_url: Full GitHub repository URL
        default_branch: Default branch name (usually 'main')
        access_token_encrypted: Encrypted OAuth access token
        token_expires_at: Token expiration timestamp
        refresh_token_encrypted: Encrypted refresh token
        installation_id: GitHub App installation ID
        auto_create_pr: Automatically create PRs from commits
        auto_link_tasks: Automatically link tasks from commit messages
        require_review: Enforce PR review requirements
        branch_protection_enabled: Branch protection status
        webhook_secret: Secret for webhook signature verification
        webhook_url: Registered webhook URL
        webhook_events: List of subscribed webhook events
        is_active: Whether integration is active
        last_sync_at: Last successful sync timestamp
        sync_error: Last sync error message
        connection_status: Connection state
        total_prs: Total pull requests tracked
        merged_prs: Merged pull request count
        closed_prs: Closed pull request count
        webhook_events_received: Webhook events received count
        created_by_user_id: User who created integration
    """

    __tablename__ = "github_integrations"

    # ============= Core Repository Information =============

    project_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
        comment="Foreign key to associated project (one-to-one)",
    )

    repository_owner: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        index=True,
        comment="GitHub username or organization name",
    )

    repository_name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        index=True,
        comment="Repository name",
    )

    repository_url: Mapped[str] = mapped_column(
        String(512),
        nullable=False,
        comment="Full GitHub repository URL",
    )

    default_branch: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        default="main",
        comment="Default branch name",
    )

    # ============= Authentication Fields =============

    access_token_encrypted: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        comment="Encrypted OAuth access token",
    )

    token_expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="OAuth token expiration timestamp",
    )

    refresh_token_encrypted: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="Encrypted refresh token for token renewal",
    )

    installation_id: Mapped[int | None] = mapped_column(
        BigInteger,
        nullable=True,
        index=True,
        comment="GitHub App installation ID (if using GitHub Apps)",
    )

    # ============= Configuration Fields =============

    auto_create_pr: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        comment="Automatically create PRs from commits",
    )

    auto_link_tasks: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        comment="Automatically link tasks from commit messages",
    )

    require_review: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        comment="Enforce PR review requirements",
    )

    branch_protection_enabled: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        comment="Whether branch protection is enabled",
    )

    # ============= Webhook Configuration =============

    webhook_secret: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        comment="Secret for webhook signature verification",
    )

    webhook_url: Mapped[str | None] = mapped_column(
        String(512),
        nullable=True,
        comment="Registered webhook URL",
    )

    webhook_events: Mapped[list[str] | None] = mapped_column(
        JSON,
        nullable=True,
        comment="List of subscribed webhook events",
    )

    # ============= Status Fields =============

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        index=True,
        comment="Whether integration is active",
    )

    last_sync_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="Last successful sync timestamp",
    )

    sync_error: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="Last sync error message",
    )

    connection_status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="disconnected",
        index=True,
        comment="Connection state: connected, disconnected, error, unauthorized",
    )

    # ============= Statistics Fields =============

    total_prs: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        comment="Total pull requests tracked",
    )

    merged_prs: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        comment="Merged pull request count",
    )

    closed_prs: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        comment="Closed pull request count",
    )

    webhook_events_received: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        comment="Total webhook events received",
    )

    # ============= Audit Fields =============

    created_by_user_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="User who created this integration",
    )

    # created_at and updated_at inherited from BaseModel

    # ============= Relationships =============

    project: Mapped["Project"] = relationship(
        "Project",
        back_populates="github_integration",
    )

    created_by: Mapped["User"] = relationship(
        "User",
        foreign_keys=[created_by_user_id],
    )

    pull_requests: Mapped[list["PullRequest"]] = relationship(
        "PullRequest",
        back_populates="github_integration",
        cascade="all, delete-orphan",
        lazy="select",
    )

    webhook_deliveries: Mapped[list["GitHubWebhookDelivery"]] = relationship(
        "GitHubWebhookDelivery",
        back_populates="github_integration",
        cascade="all, delete-orphan",
        lazy="select",
    )

    # ============= Constraints & Indexes =============

    __table_args__ = (
        # Unique constraint: one integration per project
        UniqueConstraint("project_id", name="uq_github_integration_project"),
        # Index for repository lookup
        Index("ix_github_integration_repository", "repository_owner", "repository_name"),
        # Index for status queries
        Index("ix_github_integration_status", "connection_status"),
        # Check constraints
        CheckConstraint(
            "connection_status IN ('connected', 'disconnected', 'error', 'unauthorized')",
            name="ck_github_integration_connection_status",
        ),
        CheckConstraint(
            "total_prs >= 0",
            name="ck_github_integration_total_prs",
        ),
        CheckConstraint(
            "merged_prs >= 0",
            name="ck_github_integration_merged_prs",
        ),
        CheckConstraint(
            "closed_prs >= 0",
            name="ck_github_integration_closed_prs",
        ),
        CheckConstraint(
            "webhook_events_received >= 0",
            name="ck_github_integration_webhook_events_received",
        ),
    )

    # ============= Methods =============

    def __repr__(self) -> str:
        """String representation for debugging."""
        return (
            f"<GitHubIntegration(id={self.id}, "
            f"repository='{self.repository_owner}/{self.repository_name}', "
            f"connection_status='{self.connection_status}')>"
        )

    def to_dict(self) -> dict:
        """
        Serialize integration to dictionary.

        Excludes encrypted tokens for security.

        Returns:
            Dictionary with all non-sensitive attributes
        """
        return {
            "id": str(self.id),
            "project_id": str(self.project_id),
            "repository_owner": self.repository_owner,
            "repository_name": self.repository_name,
            "repository_url": self.repository_url,
            "default_branch": self.default_branch,
            "token_expires_at": self.token_expires_at.isoformat() if self.token_expires_at else None,
            "installation_id": self.installation_id,
            "auto_create_pr": self.auto_create_pr,
            "auto_link_tasks": self.auto_link_tasks,
            "require_review": self.require_review,
            "branch_protection_enabled": self.branch_protection_enabled,
            "webhook_url": self.webhook_url,
            "webhook_events": self.webhook_events,
            "is_active": self.is_active,
            "last_sync_at": self.last_sync_at.isoformat() if self.last_sync_at else None,
            "sync_error": self.sync_error,
            "connection_status": self.connection_status,
            "total_prs": self.total_prs,
            "merged_prs": self.merged_prs,
            "closed_prs": self.closed_prs,
            "webhook_events_received": self.webhook_events_received,
            "created_by_user_id": str(self.created_by_user_id),
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

    def get_repository_full_name(self) -> str:
        """
        Get repository name in GitHub's owner/repo format.

        Returns:
            Repository full name (e.g., 'octocat/hello-world')
        """
        return f"{self.repository_owner}/{self.repository_name}"

    def is_connected(self) -> bool:
        """
        Check if integration is currently connected.

        Returns:
            True if connection_status is 'connected', False otherwise
        """
        return self.connection_status == "connected"

    def validate_webhook_signature(self, payload: str, signature: str) -> bool:
        """
        Validate webhook signature from GitHub.

        Uses HMAC-SHA256 to verify webhook authenticity.

        Args:
            payload: Raw webhook payload string
            signature: X-Hub-Signature-256 header value

        Returns:
            True if signature is valid, False otherwise
        """
        if not self.webhook_secret:
            return False

        # GitHub sends signature as 'sha256=<hash>'
        if not signature.startswith("sha256="):
            return False

        expected_signature = signature[7:]  # Remove 'sha256=' prefix

        # Compute HMAC-SHA256
        mac = hmac.new(
            self.webhook_secret.encode("utf-8"),
            msg=payload.encode("utf-8"),
            digestmod=hashlib.sha256,
        )
        computed_signature = mac.hexdigest()

        # Constant-time comparison
        return hmac.compare_digest(computed_signature, expected_signature)

    def encrypt_token(self, token: str) -> str:
        """
        Encrypt OAuth token for secure storage.

        Note: This is a placeholder. In production, use proper encryption
        like Fernet (cryptography library) or AWS KMS.

        Args:
            token: Plain text token

        Returns:
            Encrypted token string
        """
        # TODO: Implement proper encryption in production
        # For now, return as-is (will implement in security service)
        return token

    def decrypt_token(self) -> str:
        """
        Decrypt OAuth token for API calls.

        Note: This is a placeholder. In production, use proper decryption.

        Returns:
            Decrypted token string
        """
        # TODO: Implement proper decryption in production
        # For now, return as-is (will implement in security service)
        return self.access_token_encrypted


class PullRequest(Base, BaseModel):
    """
    Pull Request model for tracking GitHub PR lifecycle.

    Tracks complete PR information including:
    - PR metadata (number, title, description, state)
    - Branch information (head, base, SHA)
    - Author and reviewer information
    - Review and CI/CD status
    - Change statistics
    - Task linking for workflow automation

    Attributes:
        github_integration_id: Foreign key to GitHub integration
        project_id: Foreign key to project
        pr_number: GitHub PR number
        github_pr_id: GitHub's internal PR ID
        title: PR title
        description: PR description
        state: PR state (open, closed, merged, draft)
        head_branch: Source branch
        base_branch: Target branch
        head_sha: Latest commit SHA in PR
        author_github_username: PR author's GitHub username
        author_user_id: Mapped Ardha user ID
        is_draft: Whether PR is in draft state
        mergeable: Whether PR can be merged
        merged: Whether PR has been merged
        merged_at: Merge timestamp
        merged_by_github_username: User who merged the PR
        closed_at: Close timestamp
        review_status: Review state
        reviews_count: Total review count
        approvals_count: Approval count
        checks_status: CI/CD checks status
        checks_count: Total checks count
        required_checks_passed: Whether required checks passed
        additions: Lines added
        deletions: Lines deleted
        changed_files: Files changed count
        commits_count: Commits in PR
        html_url: GitHub PR web URL
        api_url: GitHub API URL
        linked_task_ids: Task UUIDs mentioned in PR
        closes_task_ids: Tasks closed when PR merges
        synced_at: Last sync with Ardha
    """

    __tablename__ = "pull_requests"

    # ============= Identity =============

    github_integration_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("github_integrations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Foreign key to GitHub integration",
    )

    project_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Foreign key to project",
    )

    pr_number: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        index=True,
        comment="GitHub PR number",
    )

    github_pr_id: Mapped[int] = mapped_column(
        BigInteger,
        nullable=False,
        index=True,
        comment="GitHub's internal PR ID",
    )

    # ============= Core Information =============

    title: Mapped[str] = mapped_column(
        String(500),
        nullable=False,
        comment="PR title",
    )

    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="PR description/body",
    )

    state: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="open",
        index=True,
        comment="PR state: open, closed, merged, draft",
    )

    # ============= Branch Information =============

    head_branch: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        index=True,
        comment="Source branch (e.g., 'feature/new-feature')",
    )

    base_branch: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        index=True,
        comment="Target branch (usually 'main')",
    )

    head_sha: Mapped[str] = mapped_column(
        String(40),
        nullable=False,
        index=True,
        comment="Latest commit SHA in PR",
    )

    # ============= Author Information =============

    author_github_username: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        index=True,
        comment="PR author's GitHub username",
    )

    author_user_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        comment="Mapped Ardha user ID",
    )

    # ============= Status Fields =============

    is_draft: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        index=True,
        comment="Whether PR is in draft state",
    )

    mergeable: Mapped[bool | None] = mapped_column(
        Boolean,
        nullable=True,
        comment="Whether PR can be merged (null if not computed)",
    )

    merged: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        index=True,
        comment="Whether PR has been merged",
    )

    merged_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="Merge timestamp",
    )

    merged_by_github_username: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        comment="GitHub username who merged the PR",
    )

    closed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="Close timestamp",
    )

    # ============= Review Information =============

    review_status: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        default="pending",
        index=True,
        comment="Review state: pending, approved, changes_requested, dismissed",
    )

    reviews_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        comment="Total review count",
    )

    approvals_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        comment="Approval count",
    )

    # ============= CI/CD Status =============

    checks_status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="pending",
        index=True,
        comment="CI/CD checks status: pending, success, failure, error, cancelled",
    )

    checks_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        comment="Total checks count",
    )

    required_checks_passed: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        comment="Whether all required checks passed",
    )

    # ============= Change Statistics =============

    additions: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        comment="Lines added",
    )

    deletions: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        comment="Lines deleted",
    )

    changed_files: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        comment="Files changed count",
    )

    commits_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        comment="Commits in PR",
    )

    # ============= URLs =============

    html_url: Mapped[str] = mapped_column(
        String(512),
        nullable=False,
        comment="GitHub PR web URL",
    )

    api_url: Mapped[str] = mapped_column(
        String(512),
        nullable=False,
        comment="GitHub API URL for this PR",
    )

    # ============= Task Linking =============

    linked_task_ids: Mapped[list[str] | None] = mapped_column(
        JSON,
        nullable=True,
        comment="List of task UUIDs mentioned in PR",
    )

    closes_task_ids: Mapped[list[str] | None] = mapped_column(
        JSON,
        nullable=True,
        comment="Tasks that will close when PR merges",
    )

    # ============= Timestamps =============

    # GitHub timestamps (from API)
    # created_at and updated_at are from GitHub API, stored via BaseModel

    synced_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        comment="Last sync with Ardha database",
    )

    # ============= Relationships =============

    github_integration: Mapped["GitHubIntegration"] = relationship(
        "GitHubIntegration",
        back_populates="pull_requests",
    )

    project: Mapped["Project"] = relationship(
        "Project",
        back_populates="pull_requests",
    )

    author_user: Mapped["User | None"] = relationship(
        "User",
        foreign_keys=[author_user_id],
        back_populates="authored_pull_requests",
    )

    linked_tasks: Mapped[list["Task"]] = relationship(
        "Task",
        secondary=pr_tasks,
        back_populates="pull_requests",
    )

    commits: Mapped[list["GitCommit"]] = relationship(
        "GitCommit",
        secondary=pr_commits,
        back_populates="pull_requests",
    )

    # ============= Constraints & Indexes =============

    __table_args__ = (
        # Unique constraint: one PR per integration
        UniqueConstraint(
            "github_integration_id",
            "pr_number",
            name="uq_pr_integration_number",
        ),
        # Index for project queries
        Index("ix_pr_project", "project_id"),
        # Index for state queries
        Index("ix_pr_state", "state"),
        # Index for author queries
        Index("ix_pr_author", "author_user_id"),
        # Index for chronological queries
        Index("ix_pr_created", "created_at", postgresql_ops={"created_at": "DESC"}),
        # Index for draft filtering
        Index("ix_pr_draft", "is_draft"),
        # Index for merged filtering
        Index("ix_pr_merged", "merged"),
        # Check constraints
        CheckConstraint(
            "state IN ('open', 'closed', 'merged', 'draft')",
            name="ck_pr_state",
        ),
        CheckConstraint(
            "review_status IN ('pending', 'approved', 'changes_requested', 'dismissed')",
            name="ck_pr_review_status",
        ),
        CheckConstraint(
            "checks_status IN ('pending', 'success', 'failure', 'error', 'cancelled')",
            name="ck_pr_checks_status",
        ),
        CheckConstraint(
            "pr_number > 0",
            name="ck_pr_number",
        ),
        CheckConstraint(
            "additions >= 0",
            name="ck_pr_additions",
        ),
        CheckConstraint(
            "deletions >= 0",
            name="ck_pr_deletions",
        ),
        CheckConstraint(
            "changed_files >= 0",
            name="ck_pr_changed_files",
        ),
        CheckConstraint(
            "commits_count >= 0",
            name="ck_pr_commits_count",
        ),
        CheckConstraint(
            "reviews_count >= 0",
            name="ck_pr_reviews_count",
        ),
        CheckConstraint(
            "approvals_count >= 0",
            name="ck_pr_approvals_count",
        ),
        CheckConstraint(
            "checks_count >= 0",
            name="ck_pr_checks_count",
        ),
    )

    # ============= Methods =============

    def __repr__(self) -> str:
        """String representation for debugging."""
        title_preview = self.title[:50] + "..." if len(self.title) > 50 else self.title
        return (
            f"<PullRequest(id={self.id}, "
            f"pr_number={self.pr_number}, "
            f"title='{title_preview}', "
            f"state='{self.state}')>"
        )

    def to_dict(self) -> dict:
        """
        Serialize PR to dictionary.

        Returns:
            Dictionary with all PR attributes
        """
        return {
            "id": str(self.id),
            "github_integration_id": str(self.github_integration_id),
            "project_id": str(self.project_id),
            "pr_number": self.pr_number,
            "github_pr_id": self.github_pr_id,
            "title": self.title,
            "description": self.description,
            "state": self.state,
            "head_branch": self.head_branch,
            "base_branch": self.base_branch,
            "head_sha": self.head_sha,
            "author_github_username": self.author_github_username,
            "author_user_id": str(self.author_user_id) if self.author_user_id else None,
            "is_draft": self.is_draft,
            "mergeable": self.mergeable,
            "merged": self.merged,
            "merged_at": self.merged_at.isoformat() if self.merged_at else None,
            "merged_by_github_username": self.merged_by_github_username,
            "closed_at": self.closed_at.isoformat() if self.closed_at else None,
            "review_status": self.review_status,
            "reviews_count": self.reviews_count,
            "approvals_count": self.approvals_count,
            "checks_status": self.checks_status,
            "checks_count": self.checks_count,
            "required_checks_passed": self.required_checks_passed,
            "additions": self.additions,
            "deletions": self.deletions,
            "changed_files": self.changed_files,
            "commits_count": self.commits_count,
            "html_url": self.html_url,
            "api_url": self.api_url,
            "linked_task_ids": self.linked_task_ids,
            "closes_task_ids": self.closes_task_ids,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "synced_at": self.synced_at.isoformat() if self.synced_at else None,
        }

    def get_pr_url(self) -> str:
        """
        Get GitHub PR web URL.

        Returns:
            HTML URL for viewing PR on GitHub
        """
        return self.html_url

    def is_mergeable(self) -> bool:
        """
        Check if PR can be merged.

        Returns:
            True if PR is mergeable, False otherwise
        """
        return self.mergeable is True

    def is_approved(self) -> bool:
        """
        Check if PR has sufficient approvals.

        Returns:
            True if review_status is 'approved', False otherwise
        """
        return self.review_status == "approved"

    def update_from_github(self, pr_data: dict) -> None:
        """
        Update PR fields from GitHub API response.

        Args:
            pr_data: Dictionary from GitHub API pull request endpoint
        """
        # Core fields
        if "title" in pr_data:
            self.title = pr_data["title"]
        if "body" in pr_data:
            self.description = pr_data["body"]
        if "state" in pr_data:
            self.state = pr_data["state"]

        # Branch information
        if "head" in pr_data:
            self.head_branch = pr_data["head"].get("ref", self.head_branch)
            self.head_sha = pr_data["head"].get("sha", self.head_sha)
        if "base" in pr_data:
            self.base_branch = pr_data["base"].get("ref", self.base_branch)

        # Status fields
        if "draft" in pr_data:
            self.is_draft = pr_data["draft"]
        if "mergeable" in pr_data:
            self.mergeable = pr_data["mergeable"]
        if "merged" in pr_data:
            self.merged = pr_data["merged"]
        if "merged_at" in pr_data and pr_data["merged_at"]:
            self.merged_at = datetime.fromisoformat(
                pr_data["merged_at"].replace("Z", "+00:00")
            )
        if "closed_at" in pr_data and pr_data["closed_at"]:
            self.closed_at = datetime.fromisoformat(
                pr_data["closed_at"].replace("Z", "+00:00")
            )

        # Change statistics
        if "additions" in pr_data:
            self.additions = pr_data["additions"]
        if "deletions" in pr_data:
            self.deletions = pr_data["deletions"]
        if "changed_files" in pr_data:
            self.changed_files = pr_data["changed_files"]
        if "commits" in pr_data:
            self.commits_count = pr_data["commits"]

        # URLs
        if "html_url" in pr_data:
            self.html_url = pr_data["html_url"]
        if "url" in pr_data:
            self.api_url = pr_data["url"]

        # Update sync timestamp
        self.synced_at = datetime.now(timezone.utc)