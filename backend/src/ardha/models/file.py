"""
File model for project file management.

This module defines the File model for tracking project files with:
- Git integration and change tracking
- Content storage for text files (<1MB)
- Language detection and binary file support
- SHA-256 hashing for change detection
- Last modified metadata from git commits
"""

from datetime import datetime
from hashlib import sha256
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ardha.models.base import Base, BaseModel

if TYPE_CHECKING:
    from ardha.models.git_commit import GitCommit
    from ardha.models.project import Project
    from ardha.models.user import User


class File(Base, BaseModel):
    """
    File model for tracking project files.

    Tracks both metadata and content (for small text files) with:
    - Git integration (last commit info)
    - Content hashing for change detection
    - Language detection from file extension
    - Binary vs text file classification
    - Soft delete support

    Attributes:
        path: Relative path from project root (e.g., "src/main.py")
        name: Filename only (e.g., "main.py")
        extension: File extension (e.g., ".py", ".md", ".json")
        file_type: Classification (code, doc, config, test, asset, other)
        content: Full content for text files <1MB
        content_hash: SHA-256 hash for change detection
        size_bytes: File size in bytes
        encoding: Text encoding (default: utf-8)
        last_commit_sha: Git commit hash that last modified this file
        last_commit_message: Commit message from last modification
        last_modified_by_user_id: Ardha user who made the last commit
        last_modified_at: Timestamp from git commit
        language: Detected programming language
        is_binary: Whether file is binary (not text)
        is_deleted: Soft delete flag
        deleted_at: Timestamp when soft deleted
    """

    __tablename__ = "files"

    # ============= Identity & Organization =============

    project_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Project this file belongs to",
    )

    path: Mapped[str] = mapped_column(
        String(1024),
        nullable=False,
        comment="Relative path from project root (e.g., 'src/main.py')",
    )

    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        comment="Filename only (e.g., 'main.py')",
    )

    extension: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
        index=True,
        comment="File extension (e.g., '.py', '.md', '.json')",
    )

    file_type: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="other",
        index=True,
        comment="Classification: code, doc, config, test, asset, other",
    )

    # ============= Content Storage =============

    content: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="Full content for text files <1MB, null for larger/binary files",
    )

    content_hash: Mapped[str | None] = mapped_column(
        String(64),
        nullable=True,
        comment="SHA-256 hash of content for change detection",
    )

    size_bytes: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        comment="File size in bytes",
    )

    encoding: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="utf-8",
        comment="Text encoding (default: utf-8)",
    )

    # ============= Git Integration =============

    last_commit_sha: Mapped[str | None] = mapped_column(
        String(40),
        nullable=True,
        comment="Full git commit hash that last modified this file",
    )

    last_commit_message: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
        comment="Commit message from last modification",
    )

    last_modified_by_user_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        comment="Ardha user who made the last commit",
    )

    last_modified_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        index=True,
        comment="Timestamp from git commit",
    )

    # ============= Language Detection =============

    language: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
        index=True,
        comment="Detected programming language (e.g., 'python', 'javascript')",
    )

    is_binary: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        comment="Whether file is binary (not text)",
    )

    # ============= Soft Delete =============

    is_deleted: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        index=True,
        comment="Soft delete flag",
    )

    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="Timestamp when soft deleted",
    )

    # Audit fields (created_at, updated_at) inherited from BaseModel

    # ============= Relationships =============

    project: Mapped["Project"] = relationship(
        "Project",
        back_populates="files",
    )

    last_modified_by: Mapped["User | None"] = relationship(
        "User",
        foreign_keys=[last_modified_by_user_id],
        back_populates="modified_files",
    )

    commits: Mapped[list["GitCommit"]] = relationship(
        "GitCommit",
        secondary="file_commits",
        back_populates="files",
    )

    # ============= Constraints & Indexes =============

    __table_args__ = (
        # Unique path within project
        UniqueConstraint("project_id", "path", name="uq_file_project_path"),
        # Composite indexes for common queries
        Index("ix_file_project_type", "project_id", "file_type"),
        Index(
            "ix_file_last_modified", "last_modified_at", postgresql_ops={"last_modified_at": "DESC"}
        ),
        # Check constraints
        CheckConstraint("size_bytes >= 0", name="ck_file_size_bytes"),
        CheckConstraint(
            "file_type IN ('code', 'doc', 'config', 'test', 'asset', 'other')",
            name="ck_file_type",
        ),
    )

    def __repr__(self) -> str:
        """String representation of File."""
        return f"<File(id={self.id}, " f"project_id={self.project_id}, " f"path='{self.path}')>"

    def to_dict(self) -> dict:
        """
        Serialize file to dictionary.

        Returns:
            Dictionary with all file attributes
        """
        return {
            "id": str(self.id),
            "project_id": str(self.project_id),
            "path": self.path,
            "name": self.name,
            "extension": self.extension,
            "file_type": self.file_type,
            "content_hash": self.content_hash,
            "size_bytes": self.size_bytes,
            "encoding": self.encoding,
            "last_commit_sha": self.last_commit_sha,
            "last_commit_message": self.last_commit_message,
            "last_modified_by_user_id": (
                str(self.last_modified_by_user_id) if self.last_modified_by_user_id else None
            ),
            "last_modified_at": (
                self.last_modified_at.isoformat() if self.last_modified_at else None
            ),
            "language": self.language,
            "is_binary": self.is_binary,
            "is_deleted": self.is_deleted,
            "deleted_at": self.deleted_at.isoformat() if self.deleted_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

    def get_file_extension(self) -> str | None:
        """
        Extract file extension from path.

        Returns:
            File extension with leading dot (e.g., '.py') or None
        """
        if "." not in self.path:
            return None
        return "." + self.path.rsplit(".", 1)[-1].lower()

    def detect_language(self) -> str | None:
        """
        Simple language detection from file extension.

        Returns:
            Detected language name or None
        """
        if not self.extension:
            return None

        # Language mapping
        language_map = {
            ".py": "python",
            ".js": "javascript",
            ".jsx": "javascript",
            ".ts": "typescript",
            ".tsx": "typescript",
            ".java": "java",
            ".cpp": "cpp",
            ".c": "c",
            ".h": "c",
            ".hpp": "cpp",
            ".cs": "csharp",
            ".go": "go",
            ".rs": "rust",
            ".rb": "ruby",
            ".php": "php",
            ".swift": "swift",
            ".kt": "kotlin",
            ".scala": "scala",
            ".md": "markdown",
            ".html": "html",
            ".css": "css",
            ".scss": "scss",
            ".sass": "sass",
            ".json": "json",
            ".xml": "xml",
            ".yaml": "yaml",
            ".yml": "yaml",
            ".toml": "toml",
            ".ini": "ini",
            ".sql": "sql",
            ".sh": "bash",
            ".bash": "bash",
            ".zsh": "zsh",
            ".fish": "fish",
            ".ps1": "powershell",
            ".r": "r",
            ".m": "matlab",
            ".dart": "dart",
            ".ex": "elixir",
            ".exs": "elixir",
        }

        return language_map.get(self.extension.lower())

    def is_text_file(self) -> bool:
        """
        Check if file is text (not binary).

        Returns:
            True if file is text, False if binary
        """
        return not self.is_binary

    def update_from_git(
        self,
        commit_sha: str,
        commit_message: str,
        author_user_id: UUID | None,
        committed_at: datetime,
    ) -> None:
        """
        Update file metadata from git commit information.

        Args:
            commit_sha: Full git commit hash
            commit_message: Commit message
            author_user_id: Ardha user ID who made the commit
            committed_at: Git commit timestamp
        """
        self.last_commit_sha = commit_sha
        self.last_commit_message = commit_message[:500] if commit_message else None
        self.last_modified_by_user_id = author_user_id
        self.last_modified_at = committed_at

    @staticmethod
    def calculate_content_hash(content: str) -> str:
        """
        Calculate SHA-256 hash of file content.

        Args:
            content: File content string

        Returns:
            Hex-encoded SHA-256 hash
        """
        return sha256(content.encode("utf-8")).hexdigest()
