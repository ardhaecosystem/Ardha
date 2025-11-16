"""
Pydantic schemas for File model.

This module defines request and response schemas for file operations.
"""

from datetime import datetime
from enum import Enum
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator


class FileType(str, Enum):
    """File type classification."""

    CODE = "code"
    DOC = "doc"
    CONFIG = "config"
    TEST = "test"
    ASSET = "asset"
    OTHER = "other"


class ChangeType(str, Enum):
    """Git file change type."""

    ADDED = "added"
    MODIFIED = "modified"
    DELETED = "deleted"
    RENAMED = "renamed"


# ============= Request Schemas =============


class FileBase(BaseModel):
    """Base file schema with common fields."""

    path: str = Field(
        ..., min_length=1, max_length=1024, description="Relative path from project root"
    )
    name: str = Field(..., min_length=1, max_length=255, description="Filename only")
    extension: str | None = Field(None, max_length=50, description="File extension (e.g., '.py')")
    file_type: FileType = Field(FileType.OTHER, description="File classification")
    language: str | None = Field(None, max_length=50, description="Detected programming language")
    size_bytes: int = Field(0, ge=0, description="File size in bytes")
    is_binary: bool = Field(False, description="Whether file is binary")
    encoding: str = Field("utf-8", max_length=50, description="Text encoding")


class FileCreate(FileBase):
    """Schema for creating a new file."""

    content: str | None = Field(None, description="File content for text files <1MB")

    @field_validator("path")
    @classmethod
    def validate_path_format(cls, v: str) -> str:
        """Validate path format."""
        if v.startswith("/") or v.startswith("\\"):
            raise ValueError("Path must be relative (no leading slash)")
        if ".." in v:
            raise ValueError("Path cannot contain '..' (parent directory references)")
        return v.strip()

    @field_validator("size_bytes")
    @classmethod
    def validate_size_limit(cls, v: int) -> int:
        """Validate file size limit."""
        # 10MB max for database storage
        if v > 10 * 1024 * 1024:
            raise ValueError("File size cannot exceed 10MB for database storage")
        return v

    @field_validator("extension")
    @classmethod
    def validate_extension_format(cls, v: str | None) -> str | None:
        """Ensure extension starts with dot."""
        if v is None:
            return v
        if not v.startswith("."):
            return f".{v}"
        return v.lower()


class FileUpdate(BaseModel):
    """Schema for updating a file."""

    path: str | None = Field(None, min_length=1, max_length=1024)
    name: str | None = Field(None, min_length=1, max_length=255)
    extension: str | None = Field(None, max_length=50)
    file_type: FileType | None = None
    content: str | None = None
    language: str | None = Field(None, max_length=50)
    size_bytes: int | None = Field(None, ge=0)
    is_binary: bool | None = None
    encoding: str | None = Field(None, max_length=50)

    @field_validator("path")
    @classmethod
    def validate_path_format(cls, v: str | None) -> str | None:
        """Validate path format."""
        if v is None:
            return v
        if v.startswith("/") or v.startswith("\\"):
            raise ValueError("Path must be relative (no leading slash)")
        if ".." in v:
            raise ValueError("Path cannot contain '..' (parent directory references)")
        return v.strip()


# ============= Response Schemas =============


class FileResponse(FileBase):
    """Schema for file response."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    project_id: UUID
    content_hash: str | None = None
    last_commit_sha: str | None = None
    last_commit_message: str | None = None
    last_modified_by_user_id: UUID | None = None
    last_modified_by_name: str | None = Field(None, description="Name of user who last modified")
    last_modified_at: datetime | None = None
    is_deleted: bool = False
    deleted_at: datetime | None = None
    created_at: datetime
    updated_at: datetime

    # Computed fields
    file_url: str | None = Field(None, description="URL to view file in UI")
    download_url: str | None = Field(None, description="URL to download file")


class FileWithContent(FileResponse):
    """Schema for file response with full content."""

    content: str | None = Field(None, description="Full file content")


class FileListResponse(BaseModel):
    """Schema for paginated file list."""

    model_config = ConfigDict(from_attributes=True)

    files: list[FileResponse]
    total: int = Field(..., description="Total number of files")
    page: int = Field(1, ge=1, description="Current page number")
    page_size: int = Field(10, ge=1, le=100, description="Items per page")
    has_next: bool = Field(False, description="Whether there are more pages")


class FileTreeNode(BaseModel):
    """Schema for file tree visualization."""

    name: str
    path: str
    type: str = Field(..., description="'file' or 'directory'")
    extension: str | None = None
    file_type: FileType | None = None
    language: str | None = None
    size_bytes: int | None = None
    children: list["FileTreeNode"] | None = Field(None, description="Child nodes for directories")


class FileChangeStats(BaseModel):
    """Schema for file change statistics."""

    model_config = ConfigDict(from_attributes=True)

    file_id: UUID
    path: str
    change_type: ChangeType
    old_path: str | None = None
    insertions: int = 0
    deletions: int = 0


class FileSearchRequest(BaseModel):
    """Schema for file search request."""

    query: str = Field(..., min_length=1, description="Search query")
    file_types: list[FileType] | None = Field(None, description="Filter by file types")
    languages: list[str] | None = Field(None, description="Filter by programming languages")
    extensions: list[str] | None = Field(None, description="Filter by file extensions")
    include_deleted: bool = Field(False, description="Include soft-deleted files")
    page: int = Field(1, ge=1)
    page_size: int = Field(20, ge=1, le=100)


class FileSearchResponse(BaseModel):
    """Schema for file search response."""

    files: list[FileResponse]
    total: int
    query: str
    page: int
    page_size: int
    has_next: bool
