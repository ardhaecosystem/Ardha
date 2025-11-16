"""
Response schemas for File operations.

This module defines Pydantic schemas for file-related API responses.
"""

from datetime import datetime
from uuid import UUID
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field

from ardha.schemas.file import FileResponse, FileWithContent, FileListResponse


class FileWithContentResponse(FileWithContent):
    """Schema for file response with full content."""
    
    model_config = ConfigDict(from_attributes=True)


class FileHistoryResponse(BaseModel):
    """Schema for file history response."""
    
    model_config = ConfigDict(from_attributes=True)
    
    id: UUID
    sha: str
    short_sha: str
    message: str
    author_name: str
    author_email: str
    committed_at: datetime
    change_type: str = Field(..., description="Type of change: added, modified, deleted, renamed")
    insertions: int = 0
    deletions: int = 0
    time_ago: Optional[str] = Field(None, description="Human-readable time since commit")


class FileSearchResponse(BaseModel):
    """Schema for file search response."""
    
    files: list[FileResponse]
    total: int
    query: str
    page: int
    page_size: int
    has_next: bool


class FileStatsResponse(BaseModel):
    """Schema for file statistics response."""
    
    total_files: int
    total_size_bytes: int
    file_types: dict[str, int]
    languages: dict[str, int]
    most_recent_file: Optional[FileResponse] = None
    largest_file: Optional[FileResponse] = None


class FileSyncResponse(BaseModel):
    """Schema for file sync response."""
    
    synced_count: int
    new_files: int
    updated_files: int
    deleted_files: int
    errors: list[str] = Field(default_factory=list)


class FileOperationResponse(BaseModel):
    """Schema for file operation responses (create, update, delete, rename)."""
    
    success: bool = True
    message: str
    file: Optional[FileResponse] = None
    commit_sha: Optional[str] = None
    errors: list[str] = Field(default_factory=list)