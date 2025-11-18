"""
GitCommit model for tracking git commit history.

This module defines the GitCommit model for tracking git commits with:
- Full commit metadata (SHA, author, message, timestamp)
- Task linking via commit message parsing
- File change statistics
- Branch tracking and merge detection
- User mapping from git author to Ardha user
"""

import re
from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import (
    JSON,
    Boolean,
    CheckConstraint,
    Column,
    DateTime,
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
    from ardha.models.file import File
    from ardha.models.github_integration import PullRequest
    from ardha.models.project import Project
    from ardha.models.task import Task
    from ardha.models.user import User


# Association table for file-commit many-to-many relationship
file_commits = Table(
    "file_commits",
    Base.metadata,
    Column(
        "file_id",
        PG_UUID(as_uuid=True),
        ForeignKey("files.id", ondelete="CASCADE"),
        primary_key=True,
    ),
    Column(
        "commit_id",
        PG_UUID(as_uuid=True),
        ForeignKey("git_commits.id", ondelete="CASCADE"),
        primary_key=True,
    ),
    Column(
        "change_type",
        String(20),
        nullable=False,
        comment="Type of change: added, modified, deleted, renamed",
    ),
    Column(
        "old_path",
        String(1024),
        nullable=True,
        comment="Original path for renamed files",
    ),
    Column(
        "insertions",
        Integer,
        nullable=False,
        default=0,
        comment="Lines added in this file",
    ),
    Column(
        "deletions",
        Integer,
        nullable=False,
        default=0,
        comment="Lines removed in this file",
    ),
    Index("ix_file_commits_commit", "commit_id"),
    Index("ix_file_commits_change_type", "change_type"),
)


# Association table for task-commit many-to-many relationship
task_commits = Table(
    "task_commits",
    Base.metadata,
    Column(
        "task_id",
        PG_UUID(as_uuid=True),
        ForeignKey("tasks.id", ondelete="CASCADE"),
        primary_key=True,
    ),
    Column(
        "commit_id",
        PG_UUID(as_uuid=True),
        ForeignKey("git_commits.id", ondelete="CASCADE"),
        primary_key=True,
    ),
    Column(
        "linked_at",
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        comment="When this link was created",
    ),
    Column(
        "link_type",
        String(20),
        nullable=False,
        comment="Type of link: mentioned, closes, fixes, implements",
    ),
)


class GitCommit(Base, BaseModel):
    """
    GitCommit model for tracking git commit history.

    Tracks complete git commit metadata with:
    - Full commit information (SHA, author, message)
    - Task linking from commit message parsing
    - File change statistics
    - Branch tracking
    - User mapping from git author to Ardha user

    Attributes:
        project_id: Project this commit belongs to
        sha: Full git commit hash (40 chars)
        short_sha: Short commit hash (first 7 chars)
        message: Full commit message
        author_name: Git author name
        author_email: Git author email
        committed_at: Git commit timestamp
        pushed_at: When commit was pushed to remote
        branch: Branch name when committed
        is_merge: Whether this is a merge commit
        parent_shas: List of parent commit SHAs
        files_changed: Number of files changed
        insertions: Total lines added
        deletions: Total lines deleted
        linked_task_ids: Task IDs extracted from message
        closes_task_ids: Tasks that are closed by this commit
        ardha_user_id: Mapped Ardha user from git author
        synced_at: Last sync with git repository
    """

    __tablename__ = "git_commits"

    # ============= Core Commit Information =============

    project_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Project this commit belongs to",
    )

    sha: Mapped[str] = mapped_column(
        String(40),
        nullable=False,
        comment="Full git commit hash (40 chars)",
    )

    short_sha: Mapped[str] = mapped_column(
        String(7),
        nullable=False,
        comment="Short commit hash (first 7 chars)",
    )

    message: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        comment="Full commit message",
    )

    # ============= Author Information =============

    author_name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        comment="Git author name",
    )

    author_email: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        index=True,
        comment="Git author email",
    )

    # ============= Timestamps =============

    committed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        index=True,
        comment="Git commit timestamp",
    )

    pushed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="When pushed to remote",
    )

    # ============= Branch Information =============

    branch: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        index=True,
        comment="Branch name when committed",
    )

    is_merge: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        comment="Whether this is a merge commit",
    )

    parent_shas: Mapped[list[str] | None] = mapped_column(
        JSON,
        nullable=True,
        comment="List of parent commit SHAs",
    )

    # ============= Statistics =============

    files_changed: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        comment="Number of files changed",
    )

    insertions: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        comment="Total lines added",
    )

    deletions: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        comment="Total lines deleted",
    )

    # ============= Task Linking =============

    linked_task_ids: Mapped[list[str] | None] = mapped_column(
        JSON,
        nullable=True,
        comment="List of task IDs extracted from message (e.g., ['TAS-001', 'TAS-002'])",
    )

    closes_task_ids: Mapped[list[str] | None] = mapped_column(
        JSON,
        nullable=True,
        comment="Tasks that are closed by this commit",
    )

    # ============= User Mapping =============

    ardha_user_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        comment="Mapped Ardha user from git author",
    )

    # ============= Sync Metadata =============

    synced_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="Last sync with git repository",
    )

    # Audit fields (created_at, updated_at) inherited from BaseModel

    # ============= Relationships =============

    project: Mapped["Project"] = relationship(
        "Project",
        back_populates="git_commits",
    )

    ardha_user: Mapped["User | None"] = relationship(
        "User",
        foreign_keys=[ardha_user_id],
        back_populates="git_commits",
    )

    linked_tasks: Mapped[list["Task"]] = relationship(
        "Task",
        secondary=task_commits,
        back_populates="related_commits",
    )

    files: Mapped[list["File"]] = relationship(
        "File",
        secondary=file_commits,
        back_populates="commits",
    )

    pull_requests: Mapped[list["PullRequest"]] = relationship(
        "PullRequest",
        secondary="pr_commits",
        back_populates="commits",
    )

    # ============= Constraints & Indexes =============

    __table_args__ = (
        # Unique SHA within project
        UniqueConstraint("project_id", "sha", name="uq_commit_project_sha"),
        # Composite indexes for common queries
        Index("ix_commit_project_branch", "project_id", "branch"),
        Index("ix_commit_committed_at", "committed_at", postgresql_ops={"committed_at": "DESC"}),
        # Check constraints
        CheckConstraint("files_changed >= 0", name="ck_commit_files_changed"),
        CheckConstraint("insertions >= 0", name="ck_commit_insertions"),
        CheckConstraint("deletions >= 0", name="ck_commit_deletions"),
    )

    def __repr__(self) -> str:
        """String representation of GitCommit."""
        message_preview = self.message[:50] + "..." if len(self.message) > 50 else self.message
        return (
            f"<GitCommit(id={self.id}, "
            f"short_sha='{self.short_sha}', "
            f"message='{message_preview}')>"
        )

    def to_dict(self) -> dict:
        """
        Serialize commit to dictionary.

        Returns:
            Dictionary with all commit attributes
        """
        return {
            "id": str(self.id),
            "project_id": str(self.project_id),
            "sha": self.sha,
            "short_sha": self.short_sha,
            "message": self.message,
            "author_name": self.author_name,
            "author_email": self.author_email,
            "committed_at": self.committed_at.isoformat() if self.committed_at else None,
            "pushed_at": self.pushed_at.isoformat() if self.pushed_at else None,
            "branch": self.branch,
            "is_merge": self.is_merge,
            "parent_shas": self.parent_shas,
            "files_changed": self.files_changed,
            "insertions": self.insertions,
            "deletions": self.deletions,
            "linked_task_ids": self.linked_task_ids,
            "closes_task_ids": self.closes_task_ids,
            "ardha_user_id": str(self.ardha_user_id) if self.ardha_user_id else None,
            "synced_at": self.synced_at.isoformat() if self.synced_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

    def extract_task_ids(self) -> list[str]:
        """
        Parse task IDs from commit message.

        Supports formats:
        - TAS-001, TAS-002 (Ardha task identifiers)
        - #123, #456 (GitHub issue numbers)
        - ARD-001, TASK-001 (custom project prefixes)

        Returns:
            List of extracted task IDs
        """
        if not self.message:
            return []

        # Pattern matches:
        # - TAS-001, ARD-001, TASK-001 (letters-number format)
        # - #123 (GitHub issue format)
        pattern = r"(?:[A-Z]+-\d+|#\d+)"
        matches = re.findall(pattern, self.message, re.IGNORECASE)

        # Deduplicate while preserving order
        seen = set()
        task_ids = []
        for match in matches:
            match_upper = match.upper()
            if match_upper not in seen:
                seen.add(match_upper)
                task_ids.append(match_upper)

        return task_ids

    def extract_closing_keywords(self) -> list[str]:
        """
        Find task IDs with closing keywords in commit message.

        Looks for patterns like:
        - "closes TAS-001"
        - "fixes #123"
        - "resolves ARD-001"

        Returns:
            List of task IDs that should be closed
        """
        if not self.message:
            return []

        # Keywords that indicate task completion
        closing_keywords = [
            "close",
            "closes",
            "closed",
            "fix",
            "fixes",
            "fixed",
            "resolve",
            "resolves",
            "resolved",
            "complete",
            "completes",
            "completed",
        ]

        # Build pattern: (close|closes|...) (TAS-001|#123)
        keyword_pattern = "|".join(closing_keywords)
        task_pattern = r"(?:[A-Z]+-\d+|#\d+)"
        pattern = rf"(?:{keyword_pattern})\s+({task_pattern})"

        matches = re.findall(pattern, self.message, re.IGNORECASE)

        # Deduplicate
        seen = set()
        closing_ids = []
        for match in matches:
            match_upper = match.upper()
            if match_upper not in seen:
                seen.add(match_upper)
                closing_ids.append(match_upper)

        return closing_ids

    def link_to_tasks(self) -> tuple[list[str], list[str]]:
        """
        Extract both mentioned and closing task IDs from commit message.

        Returns:
            Tuple of (all_task_ids, closing_task_ids)
        """
        all_ids = self.extract_task_ids()
        closing_ids = self.extract_closing_keywords()

        return (all_ids, closing_ids)

    def get_files_changed(self) -> list[str]:
        """
        Get list of file paths changed in this commit.

        Note: This requires the files relationship to be loaded.
        Returns empty list if relationship not loaded.

        Returns:
            List of file paths
        """
        try:
            return [file.path for file in self.files]
        except Exception:
            # Relationship not loaded
            return []
