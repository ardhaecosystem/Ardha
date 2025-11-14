"""
Memory response schemas for API serialization.

This module provides Pydantic schemas for memory-related API responses
including memory objects, search results, and context assemblies.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class MemoryResponse(BaseModel):
    """
    Memory object response schema.

    Represents a memory record with all metadata and relationships.
    """

    model_config = ConfigDict(from_attributes=True)

    id: UUID = Field(..., description="Memory unique identifier")
    user_id: UUID = Field(..., description="Owner user ID")
    project_id: Optional[UUID] = Field(None, description="Associated project ID")
    content: str = Field(..., description="Full memory content")
    summary: str = Field(..., description="Brief summary (max 200 chars)")
    qdrant_collection: str = Field(..., description="Qdrant collection name")
    qdrant_point_id: str = Field(..., description="Qdrant point ID")
    embedding_model: str = Field(..., description="Embedding model used")
    memory_type: str = Field(..., description="Type of memory")
    source_type: str = Field(..., description="Source type")
    source_id: Optional[UUID] = Field(None, description="Source record ID")
    importance: int = Field(..., ge=1, le=10, description="Importance score (1-10)")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence score (0.0-1.0)")
    access_count: int = Field(..., ge=0, description="Number of times accessed")
    last_accessed: Optional[datetime] = Field(None, description="Last access timestamp")
    tags: Dict[str, Any] = Field(default_factory=dict, description="Tags dictionary")
    extra_metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")
    expires_at: Optional[datetime] = Field(None, description="Expiration timestamp")
    is_archived: bool = Field(..., description="Whether memory is archived")


class MemorySearchResult(BaseModel):
    """
    Memory search result with similarity score.

    Represents a memory found through semantic search with its relevance score.
    """

    memory: MemoryResponse = Field(..., description="Memory object")
    similarity_score: float = Field(..., ge=0.0, le=1.0, description="Similarity score (0.0-1.0)")
    relevance_rank: int = Field(..., ge=1, description="Rank in search results")


class MemorySearchResponse(BaseModel):
    """
    Memory search response schema.

    Contains search results with metadata about the search operation.
    """

    query: str = Field(..., description="Search query used")
    total_results: int = Field(..., ge=0, description="Total number of results")
    results: List[MemorySearchResult] = Field(..., description="Search results")
    search_time_ms: Optional[float] = Field(None, description="Search time in milliseconds")
    collections_searched: List[str] = Field(
        default_factory=list, description="Collections searched"
    )
    filters_applied: Dict[str, Any] = Field(default_factory=dict, description="Filters applied")


class MemoryContextResponse(BaseModel):
    """
    Memory context assembly response.

    Represents assembled context for chat continuation or other operations.
    """

    chat_id: UUID = Field(..., description="Chat ID context was assembled for")
    context_string: str = Field(..., description="Assembled context text")
    token_count: int = Field(..., ge=0, description="Estimated token count")
    memory_count: int = Field(..., ge=0, description="Number of memories used")
    recent_message_count: int = Field(..., ge=0, description="Number of recent messages used")
    assembly_time_ms: Optional[float] = Field(
        None, description="Context assembly time in milliseconds"
    )
    relevance_threshold: float = Field(..., ge=0.0, le=1.0, description="Relevance threshold used")


class MemoryCreationResponse(BaseModel):
    """
    Memory creation response schema.

    Response after successful memory creation with metadata.
    """

    memory: MemoryResponse = Field(..., description="Created memory object")
    embedding_generated: bool = Field(..., description="Whether embedding was generated")
    vector_stored: bool = Field(..., description="Whether vector was stored in Qdrant")
    creation_time_ms: Optional[float] = Field(None, description="Creation time in milliseconds")
    collection_used: str = Field(..., description="Qdrant collection used")


class MemoryIngestionResponse(BaseModel):
    """
    Memory ingestion response schema.

    Response after ingesting memories from chat or other sources.
    """

    source_id: UUID = Field(..., description="Source ID (chat, workflow, etc.)")
    source_type: str = Field(..., description="Source type")
    memories_created: List[MemoryResponse] = Field(..., description="Created memories")
    total_memories: int = Field(..., ge=0, description="Total number of memories created")
    ingestion_time_ms: Optional[float] = Field(None, description="Ingestion time in milliseconds")
    segments_processed: int = Field(..., ge=0, description="Number of segments processed")
    relationships_created: int = Field(
        ..., ge=0, description="Number of memory relationships created"
    )


class MemoryStatsResponse(BaseModel):
    """
    Memory statistics response schema.

    Contains user memory statistics and system information.
    """

    user_id: UUID = Field(..., description="User ID stats are for")
    total_memories: int = Field(..., ge=0, description="Total memories for user")
    important_memories: int = Field(..., ge=0, description="Important memories (score >= 7)")
    recent_memories: int = Field(..., ge=0, description="Recent memories (last 24 hours)")
    collections: List[str] = Field(..., description="Available collections")
    embedding_model: str = Field(..., description="Embedding model used")
    embedding_dimension: int = Field(..., ge=1, description="Embedding vector dimension")
    last_updated: datetime = Field(..., description="When stats were last updated")


class MemoryCollectionResponse(BaseModel):
    """
    Memory collection information response.

    Contains information about a specific memory collection.
    """

    collection_name: str = Field(..., description="Collection name")
    memory_type: str = Field(..., description="Memory type stored in collection")
    vector_count: int = Field(..., ge=0, description="Number of vectors in collection")
    points_count: int = Field(..., ge=0, description="Number of points in collection")
    disk_size_bytes: int = Field(..., ge=0, description="Disk size in bytes")
    created_at: Optional[datetime] = Field(None, description="Collection creation time")
    last_indexed: Optional[datetime] = Field(None, description="Last indexing time")
    is_active: bool = Field(..., description="Whether collection is active")


class MemoryLinkResponse(BaseModel):
    """
    Memory link/relationship response schema.

    Represents a relationship between two memories.
    """

    model_config = ConfigDict(from_attributes=True)

    id: UUID = Field(..., description="Link unique identifier")
    memory_from_id: UUID = Field(..., description="Source memory ID")
    memory_to_id: UUID = Field(..., description="Target memory ID")
    relationship_type: str = Field(..., description="Type of relationship")
    strength: float = Field(..., ge=0.0, le=1.0, description="Relationship strength")
    created_at: datetime = Field(..., description="Link creation timestamp")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Link metadata")


class MemoryWithLinksResponse(MemoryResponse):
    """
    Memory response with included links.

    Extends MemoryResponse to include relationship information.
    """

    links_from: List[MemoryLinkResponse] = Field(
        default_factory=list, description="Links from this memory"
    )
    links_to: List[MemoryLinkResponse] = Field(
        default_factory=list, description="Links to this memory"
    )
    related_memories: List[MemoryResponse] = Field(
        default_factory=list, description="Related memories"
    )


class MemoryBatchResponse(BaseModel):
    """
    Batch memory operation response.

    Response for batch operations on multiple memories.
    """

    operation: str = Field(..., description="Operation performed")
    total_processed: int = Field(..., ge=0, description="Total items processed")
    successful: int = Field(..., ge=0, description="Successful operations")
    failed: int = Field(..., ge=0, description="Failed operations")
    errors: List[str] = Field(default_factory=list, description="Error messages")
    processing_time_ms: Optional[float] = Field(None, description="Processing time in milliseconds")
    results: List[MemoryResponse] = Field(default_factory=list, description="Operation results")


class MemoryHealthResponse(BaseModel):
    """
    Memory service health check response.

    Contains health status of memory service components.
    """

    status: str = Field(..., description="Overall health status")
    embedding_service: Dict[str, Any] = Field(..., description="Embedding service health")
    qdrant_service: Dict[str, Any] = Field(..., description="Qdrant service health")
    collections_status: Dict[str, Any] = Field(..., description="Collections status")
    cache_status: Dict[str, Any] = Field(..., description="Cache status")
    timestamp: datetime = Field(..., description="Health check timestamp")


class MemoryExportResponse(BaseModel):
    """
    Memory export response.

    Response for memory export operations.
    """

    export_id: UUID = Field(..., description="Export operation ID")
    format: str = Field(..., description="Export format (json, csv, etc.)")
    total_memories: int = Field(..., ge=0, description="Total memories exported")
    file_size_bytes: int = Field(..., ge=0, description="Export file size")
    download_url: Optional[str] = Field(None, description="Download URL if available")
    expires_at: Optional[datetime] = Field(None, description="Export expiration time")
    created_at: datetime = Field(..., description="Export creation time")


class MemoryImportResponse(BaseModel):
    """
    Memory import response.

    Response for memory import operations.
    """

    import_id: UUID = Field(..., description="Import operation ID")
    source_format: str = Field(..., description="Source format")
    total_records: int = Field(..., ge=0, description="Total records in import")
    imported: int = Field(..., ge=0, description="Successfully imported records")
    failed: int = Field(..., ge=0, description="Failed imports")
    duplicates: int = Field(..., ge=0, description="Duplicate records found")
    errors: List[str] = Field(default_factory=list, description="Import errors")
    processing_time_ms: Optional[float] = Field(None, description="Processing time in milliseconds")
    created_at: datetime = Field(..., description="Import creation time")
