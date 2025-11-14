"""
Embedding service configuration settings.

This module provides Pydantic settings for the local embedding service
using sentence-transformers all-MiniLM-L6-v2 model.
"""

from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator


class EmbeddingSettings(BaseModel):
    """Local embedding service configuration settings."""

    model_config = ConfigDict(
        protected_namespaces=(),  # Allow model_ fields without warnings
        validate_assignment=True,
        extra="forbid",
    )

    # Model configuration
    model_name: str = Field(
        default="sentence-transformers/all-MiniLM-L6-v2",
        description="Sentence transformer model name for embeddings",
    )
    model_dimension: int = Field(
        default=384, ge=1, le=4096, description="Embedding dimension (384 for all-MiniLM-L6-v2)"
    )
    model_cache_dir: Optional[str] = Field(
        default=None,
        description="Directory to cache downloaded models (default: ~/.cache/torch/sentence_transformers)",
    )

    # Caching configuration
    enable_redis_cache: bool = Field(
        default=True, description="Enable Redis caching for embeddings"
    )
    redis_url: str = Field(default="redis://localhost:6379/0", description="Redis connection URL")
    cache_ttl_seconds: int = Field(
        default=86400,  # 24 hours
        ge=60,  # 1 minute minimum
        le=604800,  # 7 days maximum
        description="Cache TTL in seconds for embeddings",
    )
    cache_prefix: str = Field(
        default="embeddings:", description="Redis key prefix for embedding cache"
    )

    # Performance configuration
    default_batch_size: int = Field(
        default=32, ge=1, le=256, description="Default batch size for embedding generation"
    )
    max_batch_size: int = Field(
        default=128, ge=1, le=512, description="Maximum batch size for embedding generation"
    )
    normalize_embeddings: bool = Field(
        default=True,
        description="Whether to normalize embeddings (important for cosine similarity)",
    )

    # Resource limits
    max_text_length: int = Field(
        default=8192, ge=1, le=65536, description="Maximum text length in characters"
    )
    max_concurrent_requests: int = Field(
        default=10, ge=1, le=100, description="Maximum concurrent embedding requests"
    )

    # Monitoring and metrics
    enable_metrics: bool = Field(default=True, description="Enable performance metrics collection")
    metrics_retention_hours: int = Field(
        default=168,  # 7 days
        ge=1,
        le=720,  # 30 days
        description="Retention period for metrics in hours",
    )

    # Advanced performance settings
    enable_model_warmup: bool = Field(
        default=True, description="Whether to warm up the model on first load"
    )
    enable_embedding_pool: bool = Field(
        default=True, description="Whether to use embedding pooling for performance"
    )
    pool_size: int = Field(
        default=1000,
        ge=100,
        le=10000,
        description="Size of embedding pool for frequently used texts",
    )
    enable_compression: bool = Field(
        default=False, description="Whether to compress cached embeddings"
    )
    compression_threshold: int = Field(
        default=100, ge=10, le=1000, description="Minimum batch size to enable compression"
    )
    enable_smart_batching: bool = Field(
        default=True, description="Whether to use smart batching for optimal performance"
    )
    smart_batch_threshold: int = Field(
        default=16, ge=4, le=64, description="Threshold for smart batching optimization"
    )

    @field_validator("model_name")
    @classmethod
    def validate_model_name(cls, v: str) -> str:
        """Validate model name is a supported sentence transformer."""
        # List of supported models (can be extended)
        supported_models = [
            "sentence-transformers/all-MiniLM-L6-v2",
            "sentence-transformers/all-mpnet-base-v2",
            "sentence-transformers/multi-qa-mpnet-base-dot-v1",
            "sentence-transformers/paraphrase-mpnet-base-v2",
        ]

        if v not in supported_models:
            raise ValueError(
                f"Model '{v}' is not supported. " f"Supported models: {', '.join(supported_models)}"
            )

        return v

    @field_validator("model_dimension")
    @classmethod
    def validate_model_dimension(cls, v: int, info) -> int:
        """Validate model dimension matches the selected model."""
        # Known dimensions for supported models
        model_dimensions = {
            "sentence-transformers/all-MiniLM-L6-v2": 384,
            "sentence-transformers/all-mpnet-base-v2": 768,
            "sentence-transformers/multi-qa-mpnet-base-dot-v1": 768,
            "sentence-transformers/paraphrase-mpnet-base-v2": 768,
        }

        model_name = info.data.get("model_name")
        if model_name and model_name in model_dimensions:
            expected_dim = model_dimensions[model_name]
            if v != expected_dim:
                raise ValueError(
                    f"Model dimension {v} does not match expected dimension "
                    f"{expected_dim} for model '{model_name}'"
                )

        return v

    @field_validator("max_batch_size")
    @classmethod
    def validate_max_batch_size(cls, v: int, info) -> int:
        """Validate max_batch_size is >= default_batch_size."""
        default_batch_size = info.data.get("default_batch_size", 32)
        if v < default_batch_size:
            raise ValueError(
                f"max_batch_size ({v}) must be >= default_batch_size ({default_batch_size})"
            )
        return v

    @field_validator("cache_prefix")
    @classmethod
    def validate_cache_prefix(cls, v: str) -> str:
        """Validate cache prefix format."""
        if not v.endswith(":"):
            raise ValueError("cache_prefix must end with ':'")
        return v

    def get_model_info(self) -> dict:
        """Get information about the configured model."""
        return {
            "name": self.model_name,
            "dimension": self.model_dimension,
            "cache_dir": self.model_cache_dir,
            "normalize": self.normalize_embeddings,
        }

    def get_cache_info(self) -> dict:
        """Get information about caching configuration."""
        return {
            "enabled": self.enable_redis_cache,
            "ttl_seconds": self.cache_ttl_seconds,
            "prefix": self.cache_prefix,
        }

    def get_performance_info(self) -> dict:
        """Get information about performance configuration."""
        return {
            "default_batch_size": self.default_batch_size,
            "max_batch_size": self.max_batch_size,
            "max_text_length": self.max_text_length,
            "max_concurrent_requests": self.max_concurrent_requests,
            "normalize_embeddings": self.normalize_embeddings,
            "embedding_pool_enabled": self.enable_embedding_pool,
            "smart_batching_enabled": self.enable_smart_batching,
            "pool_size": self.pool_size,
            "smart_batch_threshold": self.smart_batch_threshold,
            "model_warmup_enabled": self.enable_model_warmup,
            "compression_enabled": self.enable_compression,
            "compression_threshold": self.compression_threshold,
        }

    def get_metrics_info(self) -> dict:
        """Get information about metrics configuration."""
        return {
            "enabled": self.enable_metrics,
            "retention_hours": self.metrics_retention_hours,
        }


# Default embedding settings instance
DEFAULT_EMBEDDING_SETTINGS = EmbeddingSettings()


def get_embedding_settings() -> EmbeddingSettings:
    """
    Get default embedding settings.

    Returns:
        EmbeddingSettings: Default embedding configuration
    """
    return DEFAULT_EMBEDDING_SETTINGS
