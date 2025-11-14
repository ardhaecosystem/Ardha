"""
Embedding service request schemas.

This module provides Pydantic schemas for embedding service API requests,
including single text embedding and batch embedding requests.
"""

from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator


class EmbeddingRequest(BaseModel):
    """Request schema for single text embedding."""

    model_config = ConfigDict(
        protected_namespaces=(),  # Allow model_ fields without warnings
        validate_assignment=True,
        extra="forbid",
        json_schema_extra={
            "example": {
                "text": "This is a sample text for embedding generation.",
                "normalize": True,
                "use_cache": True,
            }
        },
    )

    text: str = Field(
        ..., min_length=1, max_length=8192, description="Text to generate embedding for"
    )
    normalize: Optional[bool] = Field(
        default=None,
        description="Whether to normalize embedding (uses service default if not specified)",
    )
    use_cache: Optional[bool] = Field(
        default=None, description="Whether to use cache (uses service default if not specified)"
    )

    @field_validator("text")
    @classmethod
    def validate_text(cls, v: str) -> str:
        """Validate text is not empty or just whitespace."""
        if not v or not v.strip():
            raise ValueError("Text cannot be empty or whitespace only")
        return v.strip()


class BatchEmbeddingRequest(BaseModel):
    """Request schema for batch text embedding."""

    model_config = ConfigDict(
        protected_namespaces=(),  # Allow model_ fields without warnings
        validate_assignment=True,
        extra="forbid",
        json_schema_extra={
            "example": {
                "texts": [
                    "First sample text for embedding.",
                    "Second sample text for embedding.",
                    "Third sample text for embedding.",
                ],
                "batch_size": 32,
                "normalize": True,
                "use_cache": True,
                "show_progress": False,
            }
        },
    )

    texts: List[str] = Field(
        ..., min_length=1, max_length=128, description="List of texts to generate embeddings for"
    )
    batch_size: Optional[int] = Field(
        default=None,
        ge=1,
        le=256,
        description="Batch size for processing (uses service default if not specified)",
    )
    normalize: Optional[bool] = Field(
        default=None,
        description="Whether to normalize embeddings (uses service default if not specified)",
    )
    use_cache: Optional[bool] = Field(
        default=None, description="Whether to use cache (uses service default if not specified)"
    )
    show_progress: Optional[bool] = Field(
        default=False, description="Whether to show progress logging"
    )

    @field_validator("texts")
    @classmethod
    def validate_texts(cls, v: List[str]) -> List[str]:
        """Validate all texts are not empty or just whitespace."""
        validated_texts = []
        for i, text in enumerate(v):
            if not text or not text.strip():
                raise ValueError(f"Text at index {i} cannot be empty or whitespace only")
            validated_texts.append(text.strip())
        return validated_texts

    @field_validator("batch_size")
    @classmethod
    def validate_batch_size(cls, v: Optional[int], info) -> Optional[int]:
        """Validate batch size is reasonable for the number of texts."""
        if v is not None:
            texts = info.data.get("texts", [])
            if v > len(texts):
                raise ValueError(
                    f"Batch size ({v}) cannot be greater than number of texts ({len(texts)})"
                )
        return v


class SimilaritySearchRequest(BaseModel):
    """Request schema for similarity search using embeddings."""

    model_config = ConfigDict(
        protected_namespaces=(),  # Allow model_ fields without warnings
        validate_assignment=True,
        extra="forbid",
        json_schema_extra={
            "example": {
                "query_text": "Find similar conversations about project planning",
                "collection_type": "chats",
                "limit": 10,
                "score_threshold": 0.7,
                "filter_conditions": {
                    "user_id": "123e4567-e89b-12d3-a456-426614174000",
                    "project_id": "456e7890-e12b-34d5-a678-123456789012",
                },
            }
        },
    )

    query_text: str = Field(
        ...,
        min_length=1,
        max_length=8192,
        description="Query text to search for similar embeddings",
    )
    collection_type: str = Field(
        default="chats", description="Collection type to search in (chats, projects, code, etc.)"
    )
    limit: int = Field(default=10, ge=1, le=100, description="Maximum number of results to return")
    score_threshold: float = Field(
        default=0.7, ge=0.0, le=1.0, description="Minimum similarity score threshold"
    )
    filter_conditions: Optional[dict] = Field(
        default=None, description="Optional metadata filter conditions"
    )

    @field_validator("query_text")
    @classmethod
    def validate_query_text(cls, v: str) -> str:
        """Validate query text is not empty or just whitespace."""
        if not v or not v.strip():
            raise ValueError("Query text cannot be empty or whitespace only")
        return v.strip()

    @field_validator("collection_type")
    @classmethod
    def validate_collection_type(cls, v: str) -> str:
        """Validate collection type."""
        allowed_types = ["chats", "projects", "code", "documentation", "workflows", "artifacts"]
        if v not in allowed_types:
            raise ValueError(
                f"Collection type '{v}' is not allowed. "
                f"Allowed types: {', '.join(allowed_types)}"
            )
        return v


class CacheManagementRequest(BaseModel):
    """Request schema for cache management operations."""

    model_config = ConfigDict(
        protected_namespaces=(),  # Allow model_ fields without warnings
        validate_assignment=True,
        extra="forbid",
        json_schema_extra={
            "example": {
                "operation": "clear",
                "collection_type": "chats",
            }
        },
    )

    operation: str = Field(..., description="Cache operation: clear, info, stats")
    collection_type: Optional[str] = Field(
        default=None,
        description="Optional collection type to target (if not specified, applies to all)",
    )

    @field_validator("operation")
    @classmethod
    def validate_operation(cls, v: str) -> str:
        """Validate cache operation."""
        allowed_operations = ["clear", "info", "stats"]
        if v not in allowed_operations:
            raise ValueError(
                f"Operation '{v}' is not allowed. "
                f"Allowed operations: {', '.join(allowed_operations)}"
            )
        return v


class EmbeddingHealthRequest(BaseModel):
    """Request schema for embedding service health check."""

    model_config = ConfigDict(
        protected_namespaces=(),  # Allow model_ fields without warnings
        validate_assignment=True,
        extra="forbid",
        json_schema_extra={
            "example": {
                "include_model_test": True,
                "include_cache_test": True,
            }
        },
    )

    include_model_test: bool = Field(
        default=True, description="Whether to include model test in health check"
    )
    include_cache_test: bool = Field(
        default=True, description="Whether to include cache test in health check"
    )
