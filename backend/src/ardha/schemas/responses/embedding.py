"""
Embedding service response schemas.

This module provides Pydantic schemas for embedding service API responses,
including embedding results, service information, and error responses.
"""

from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel, ConfigDict, Field


class EmbeddingResponse(BaseModel):
    """Response schema for single text embedding."""
    
    model_config = ConfigDict(
        protected_namespaces=(),  # Allow model_ fields without warnings
        validate_assignment=True,
        extra="forbid",
        json_schema_extra={
            "example": {
                "embedding": [0.1234, -0.5678, 0.9012, "..."],
                "dimension": 384,
                "model_name": "sentence-transformers/all-MiniLM-L6-v2",
                "text_length": 45,
                "processing_time_ms": 12.5,
                "cached": False,
                "pool_cached": False,
            }
        }
    )
    
    embedding: List[float] = Field(
        ...,
        description="Generated embedding vector"
    )
    dimension: int = Field(
        ...,
        description="Embedding dimension"
    )
    model_name: str = Field(
        ...,
        description="Model used for embedding generation"
    )
    text_length: int = Field(
        ...,
        description="Length of input text"
    )
    processing_time_ms: float = Field(
        ...,
        description="Processing time in milliseconds"
    )
    cached: bool = Field(
        ...,
        description="Whether result was retrieved from Redis cache"
    )
    pool_cached: bool = Field(
        default=False,
        description="Whether result was retrieved from in-memory pool"
    )


class BatchEmbeddingResponse(BaseModel):
    """Response schema for batch text embedding."""
    
    model_config = ConfigDict(
        protected_namespaces=(),  # Allow model_ fields without warnings
        validate_assignment=True,
        extra="forbid",
        json_schema_extra={
            "example": {
                "embeddings": [
                    [0.1234, -0.5678, 0.9012, "..."],
                    [0.2345, -0.6789, 0.0123, "..."],
                    [0.3456, -0.7890, 0.1234, "..."],
                ],
                "dimension": 384,
                "model_name": "sentence-transformers/all-MiniLM-L6-v2",
                "total_texts": 3,
                "processed_texts": 3,
                "redis_cached_count": 1,
                "pool_cached_count": 0,
                "batch_size": 32,
                "total_processing_time_ms": 35.2,
                "average_time_per_text_ms": 11.7,
                "smart_batching_used": True,
            }
        }
    )
    
    embeddings: List[List[float]] = Field(
        ...,
        description="Generated embedding vectors"
    )
    dimension: int = Field(
        ...,
        description="Embedding dimension"
    )
    model_name: str = Field(
        ...,
        description="Model used for embedding generation"
    )
    total_texts: int = Field(
        ...,
        description="Total number of input texts"
    )
    processed_texts: int = Field(
        ...,
        description="Number of texts successfully processed"
    )
    redis_cached_count: int = Field(
        ...,
        description="Number of results retrieved from Redis cache"
    )
    pool_cached_count: int = Field(
        default=0,
        description="Number of results retrieved from in-memory pool"
    )
    batch_size: int = Field(
        ...,
        description="Batch size used for processing"
    )
    total_processing_time_ms: float = Field(
        ...,
        description="Total processing time in milliseconds"
    )
    average_time_per_text_ms: float = Field(
        ...,
        description="Average processing time per text in milliseconds"
    )
    smart_batching_used: bool = Field(
        default=False,
        description="Whether smart batching optimization was used"
    )


class SimilaritySearchResponse(BaseModel):
    """Response schema for similarity search results."""
    
    model_config = ConfigDict(
        protected_namespaces=(),  # Allow model_ fields without warnings
        validate_assignment=True,
        extra="forbid",
        json_schema_extra={
            "example": {
                "query_text": "Find similar conversations about project planning",
                "results": [
                    {
                        "id": "123e4567-e89b-12d3-a456-426614174000",
                        "score": 0.89,
                        "text": "Let's discuss the project planning approach",
                        "metadata": {"user_id": "user123", "created_at": "2025-01-01T10:00:00Z"},
                    },
                    {
                        "id": "456e7890-e12b-34d5-a678-123456789012",
                        "score": 0.85,
                        "text": "Project planning timeline and milestones",
                        "metadata": {"user_id": "user456", "created_at": "2025-01-02T14:30:00Z"},
                    },
                ],
                "total_results": 2,
                "collection_type": "chats",
                "score_threshold": 0.7,
                "processing_time_ms": 45.8,
            }
        }
    )
    
    query_text: str = Field(
        ...,
        description="Original query text"
    )
    results: List[Dict[str, Any]] = Field(
        ...,
        description="Similarity search results"
    )
    total_results: int = Field(
        ...,
        description="Total number of results found"
    )
    collection_type: str = Field(
        ...,
        description="Collection type searched"
    )
    score_threshold: float = Field(
        ...,
        description="Score threshold used for search"
    )
    processing_time_ms: float = Field(
        ...,
        description="Search processing time in milliseconds"
    )


class EmbeddingServiceInfo(BaseModel):
    """Response schema for embedding service information with advanced metrics."""
    
    model_config = ConfigDict(
        protected_namespaces=(),  # Allow model_ fields without warnings
        validate_assignment=True,
        extra="forbid",
        json_schema_extra={
            "example": {
                "model_name": "sentence-transformers/all-MiniLM-L6-v2",
                "dimension": 384,
                "model_loaded": True,
                "cache_enabled": True,
                "cache_ttl": 86400,
                "total_embeddings": 1250,
                "redis_cache_hits": 890,
                "redis_cache_misses": 360,
                "redis_cache_hit_rate": 0.712,
                "pool_hits": 450,
                "pool_misses": 800,
                "pool_hit_rate": 0.36,
                "pool_size": 156,
                "pool_max_size": 1000,
                "average_time_ms": 15.3,
                "smart_batching_enabled": True,
                "embedding_pool_enabled": True,
            }
        }
    )
    
    model_name: str = Field(
        ...,
        description="Model name being used"
    )
    dimension: int = Field(
        ...,
        description="Embedding dimension"
    )
    model_loaded: bool = Field(
        ...,
        description="Whether model is loaded"
    )
    cache_enabled: bool = Field(
        ...,
        description="Whether Redis caching is enabled"
    )
    cache_ttl: int = Field(
        ...,
        description="Cache TTL in seconds"
    )
    total_embeddings: int = Field(
        ...,
        description="Total embeddings generated"
    )
    redis_cache_hits: int = Field(
        ...,
        description="Number of Redis cache hits"
    )
    redis_cache_misses: int = Field(
        ...,
        description="Number of Redis cache misses"
    )
    redis_cache_hit_rate: float = Field(
        ...,
        description="Redis cache hit rate (0.0 to 1.0)"
    )
    pool_hits: int = Field(
        default=0,
        description="Number of in-memory pool hits"
    )
    pool_misses: int = Field(
        default=0,
        description="Number of in-memory pool misses"
    )
    pool_hit_rate: float = Field(
        default=0.0,
        description="In-memory pool hit rate (0.0 to 1.0)"
    )
    pool_size: int = Field(
        default=0,
        description="Current in-memory pool size"
    )
    pool_max_size: int = Field(
        default=0,
        description="Maximum in-memory pool size"
    )
    average_time_ms: float = Field(
        ...,
        description="Average processing time in milliseconds"
    )
    smart_batching_enabled: bool = Field(
        default=False,
        description="Whether smart batching is enabled"
    )
    embedding_pool_enabled: bool = Field(
        default=False,
        description="Whether embedding pool is enabled"
    )


class EmbeddingHealthResponse(BaseModel):
    """Response schema for embedding service health check."""
    
    status: str = Field(
        ...,
        description="Overall health status (healthy, degraded, unhealthy)"
    )
    model_status: str = Field(
        ...,
        description="Model status (loaded, not_loaded, error)"
    )
    cache_status: str = Field(
        ...,
        description="Cache status (healthy, unhealthy, disconnected)"
    )
    generation_status: str = Field(
        ...,
        description="Embedding generation status (working, failed)"
    )
    model_name: str = Field(
        ...,
        description="Model name"
    )
    dimension: int = Field(
        ...,
        description="Embedding dimension"
    )
    timestamp: float = Field(
        ...,
        description="Health check timestamp"
    )
    error: Optional[str] = Field(
        default=None,
        description="Error message if status is unhealthy"
    )
    
    class Config:
        """Pydantic configuration."""
        json_schema_extra = {
            "example": {
                "status": "healthy",
                "model_status": "loaded",
                "cache_status": "healthy",
                "generation_status": "working",
                "model_name": "sentence-transformers/all-MiniLM-L6-v2",
                "dimension": 384,
                "timestamp": 1705123456.789,
                "error": None,
            }
        }


class CacheManagementResponse(BaseModel):
    """Response schema for cache management operations."""
    
    operation: str = Field(
        ...,
        description="Cache operation performed"
    )
    success: bool = Field(
        ...,
        description="Whether operation was successful"
    )
    message: str = Field(
        ...,
        description="Operation result message"
    )
    collection_type: Optional[str] = Field(
        default=None,
        description="Collection type targeted (if applicable)"
    )
    cache_stats: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Cache statistics (for info/stats operations)"
    )
    timestamp: float = Field(
        ...,
        description="Operation timestamp"
    )
    
    class Config:
        """Pydantic configuration."""
        json_schema_extra = {
            "example": {
                "operation": "clear",
                "success": True,
                "message": "Cleared 150 embeddings from cache",
                "collection_type": "chats",
                "cache_stats": None,
                "timestamp": 1705123456.789,
            }
        }


class EmbeddingErrorResponse(BaseModel):
    """Response schema for embedding service errors."""
    
    error: str = Field(
        ...,
        description="Error type"
    )
    message: str = Field(
        ...,
        description="Error message"
    )
    details: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Additional error details"
    )
    timestamp: float = Field(
        ...,
        description="Error timestamp"
    )
    
    class Config:
        """Pydantic configuration."""
        json_schema_extra = {
            "example": {
                "error": "EmbeddingError",
                "message": "Failed to generate embedding: Model not loaded",
                "details": {
                    "model_name": "sentence-transformers/all-MiniLM-L6-v2",
                    "text_length": 45,
                },
                "timestamp": 1705123456.789,
            }
        }


class EmbeddingMetricsResponse(BaseModel):
    """Response schema for embedding service metrics."""
    
    total_embeddings: int = Field(
        ...,
        description="Total embeddings generated"
    )
    total_processing_time_ms: float = Field(
        ...,
        description="Total processing time in milliseconds"
    )
    average_time_ms: float = Field(
        ...,
        description="Average processing time per embedding"
    )
    cache_stats: Dict[str, Union[int, float]] = Field(
        ...,
        description="Cache statistics"
    )
    model_info: Dict[str, Any] = Field(
        ...,
        description="Model information"
    )
    performance_stats: Dict[str, Any] = Field(
        ...,
        description="Performance statistics"
    )
    timestamp: float = Field(
        ...,
        description="Metrics timestamp"
    )
    
    class Config:
        """Pydantic configuration."""
        json_schema_extra = {
            "example": {
                "total_embeddings": 1250,
                "total_processing_time_ms": 19125.0,
                "average_time_ms": 15.3,
                "cache_stats": {
                    "hits": 890,
                    "misses": 360,
                    "hit_rate": 0.712,
                },
                "model_info": {
                    "name": "sentence-transformers/all-MiniLM-L6-v2",
                    "dimension": 384,
                    "loaded": True,
                },
                "performance_stats": {
                    "batch_size_avg": 28.5,
                    "concurrent_requests_avg": 3.2,
                },
                "timestamp": 1705123456.789,
            }
        }