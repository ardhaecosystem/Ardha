"""
Request schemas for File operations.

This module defines Pydantic schemas for file-related API requests.
"""

from uuid import UUID

from pydantic import BaseModel, Field, field_validator

from ardha.schemas.file import FileType


class CreateFileRequest(BaseModel):
    """Schema for creating a new file."""

    project_id: UUID = Field(..., description="Project UUID")
    path: str = Field(
        ..., min_length=1, max_length=1024, description="Relative path from project root"
    )
    content: str = Field(..., description="File content")
    commit: bool = Field(False, description="Whether to commit the file creation")
    commit_message: str | None = Field(None, description="Custom commit message if committing")

    @field_validator("path")
    @classmethod
    def validate_path_format(cls, v: str) -> str:
        """Validate path format."""
        if v.startswith("/") or v.startswith("\\"):
            raise ValueError("Path must be relative (no leading slash)")
        if ".." in v:
            raise ValueError("Path cannot contain '..' (parent directory references)")
        return v.strip()


class UpdateFileContentRequest(BaseModel):
    """Schema for updating file content."""

    content: str = Field(..., description="New file content")
    commit: bool = Field(False, description="Whether to commit the changes")
    commit_message: str | None = Field(None, description="Custom commit message if committing")


class RenameFileRequest(BaseModel):
    """Schema for renaming a file."""

    new_path: str = Field(..., min_length=1, max_length=1024, description="New file path")
    commit: bool = Field(False, description="Whether to commit the rename")
    commit_message: str | None = Field(None, description="Custom commit message if committing")

    @field_validator("new_path")
    @classmethod
    def validate_path_format(cls, v: str) -> str:
        """Validate path format."""
        if v.startswith("/") or v.startswith("\\"):
            raise ValueError("Path must be relative (no leading slash)")
        if ".." in v:
            raise ValueError("Path cannot contain '..' (parent directory references)")
        return v.strip()


class DeleteFileRequest(BaseModel):
    """Schema for deleting a file."""

    commit: bool = Field(False, description="Whether to commit the deletion")
    commit_message: str | None = Field(None, description="Custom commit message if committing")


class FileListRequest(BaseModel):
    """Schema for listing files with filters."""

    directory: str | None = Field(None, description="Filter by directory path")
    file_type: FileType | None = Field(None, description="Filter by file type")
    search: str | None = Field(None, min_length=1, description="Search in file names")
    include_deleted: bool = Field(False, description="Include soft-deleted files")
    page: int = Field(1, ge=1, description="Page number")
    page_size: int = Field(50, ge=1, le=100, description="Items per page")


class FileSearchRequest(BaseModel):
    """Schema for searching files."""

    query: str = Field(..., min_length=1, description="Search query")
    search_content: bool = Field(False, description="Search in file content as well")
    file_types: list[FileType] | None = Field(None, description="Filter by file types")
    page: int = Field(1, ge=1, description="Page number")
    page_size: int = Field(20, ge=1, le=100, description="Items per page")


class GetFileContentRequest(BaseModel):
    """Schema for getting file content."""

    ref: str = Field("HEAD", description="Git reference (commit SHA, branch, tag)")
