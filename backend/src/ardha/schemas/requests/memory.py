"""
Memory request schemas for API validation.

This module defines Pydantic models for memory-related API requests,
including memory creation, updating, searching, and ingestion.
"""

from typing import Any, Dict, List, Literal, Optional
from uuid import UUID

from pydantic import BaseModel, Field, field_validator


class CreateMemoryRequest(BaseModel):
    """Request model for creating a new memory."""

    content: str = Field(..., min_length=1, max_length=10000, description="Memory content")
    memory_type: Literal["conversation", "workflow", "document", "entity", "fact"] = Field(
        ..., description="Type of memory"
    )
    project_id: Optional[UUID] = Field(None, description="Associated project ID")
    importance: int = Field(default=5, ge=1, le=10, description="Importance score (1-10)")
    tags: Optional[List[str]] = Field(default=None, description="Memory tags")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata")

    @field_validator("tags")
    @classmethod
    def validate_tags(cls, v: Optional[List[str]]) -> Optional[List[str]]:
        """Validate and normalize tags."""
        if v:
            if len(v) > 10:
                raise ValueError("Maximum 10 tags allowed")
            # Ensure tags are lowercase and unique
            return list(set(tag.lower().strip() for tag in v))
        return v


class UpdateMemoryRequest(BaseModel):
    """Request model for updating an existing memory."""

    content: Optional[str] = Field(
        None, min_length=1, max_length=10000, description="Memory content"
    )
    importance: Optional[int] = Field(None, ge=1, le=10, description="Importance score (1-10)")
    tags: Optional[List[str]] = Field(None, description="Memory tags")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata")

    @field_validator("tags")
    @classmethod
    def validate_tags(cls, v: Optional[List[str]]) -> Optional[List[str]]:
        """Validate and normalize tags."""
        if v:
            if len(v) > 10:
                raise ValueError("Maximum 10 tags allowed")
            return list(set(tag.lower().strip() for tag in v))
        return v


class SearchMemoryRequest(BaseModel):
    """Request model for semantic memory search."""

    query: str = Field(..., min_length=1, max_length=500, description="Search query")
    memory_type: Optional[str] = Field(None, description="Filter by memory type")
    project_id: Optional[UUID] = Field(None, description="Filter by project ID")
    limit: int = Field(default=10, ge=1, le=50, description="Maximum results")
    min_score: float = Field(default=0.5, ge=0.0, le=1.0, description="Minimum similarity score")


class IngestChatRequest(BaseModel):
    """Request model for ingesting memories from chat."""

    min_importance: int = Field(default=6, ge=1, le=10, description="Minimum importance score")
    extract_entities: bool = Field(default=True, description="Whether to extract entities")


class GetContextRequest(BaseModel):
    """Request model for getting chat context."""

    max_tokens: int = Field(default=2000, ge=500, le=8000, description="Maximum token budget")
    relevance_threshold: float = Field(
        default=0.6, ge=0.0, le=1.0, description="Minimum relevance score"
    )


class IngestWorkflowRequest(BaseModel):
    """Request model for ingesting memories from workflow."""

    extract_outputs: bool = Field(default=True, description="Whether to extract workflow outputs")
    extract_decisions: bool = Field(default=True, description="Whether to extract decisions")
    importance_override: Optional[int] = Field(
        None, ge=1, le=10, description="Override importance score"
    )


class GetRelatedMemoriesRequest(BaseModel):
    """Request model for getting related memories."""

    depth: int = Field(default=2, ge=1, le=3, description="Relationship depth")
    min_strength: float = Field(
        default=0.3, ge=0.0, le=1.0, description="Minimum relationship strength"
    )
    include_links: bool = Field(default=True, description="Whether to include relationship links")


class ArchiveMemoryRequest(BaseModel):
    """Request model for archiving a memory."""

    reason: Optional[str] = Field(None, max_length=500, description="Archive reason")
    retain_context: bool = Field(default=True, description="Whether to retain for context search")


class BatchMemoryOperationRequest(BaseModel):
    """Request model for batch memory operations."""

    memory_ids: List[UUID] = Field(..., description="Memory IDs to operate on")
    operation: Literal["archive", "delete", "update_importance"] = Field(
        ..., description="Operation type"
    )
    operation_params: Optional[Dict[str, Any]] = Field(
        None, description="Operation-specific parameters"
    )

    @field_validator("memory_ids")
    @classmethod
    def validate_memory_ids(cls, v: List[UUID]) -> List[UUID]:
        """Validate memory IDs list."""
        if len(v) == 0:
            raise ValueError("At least one memory ID is required")
        if len(v) > 100:
            raise ValueError("Maximum 100 memory IDs allowed")
        return v


class ExportMemoriesRequest(BaseModel):
    """Request model for exporting memories."""

    format: Literal["json", "csv", "markdown"] = Field(default="json", description="Export format")
    memory_type: Optional[str] = Field(None, description="Filter by memory type")
    project_id: Optional[UUID] = Field(None, description="Filter by project ID")
    date_from: Optional[str] = Field(None, description="ISO date string (from)")
    date_to: Optional[str] = Field(None, description="ISO date string (to)")
    include_metadata: bool = Field(default=True, description="Whether to include metadata")
