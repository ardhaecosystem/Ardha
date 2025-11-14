"""
Unit tests for local embedding service.

This module provides comprehensive tests for the LocalEmbeddingService
including model loading, embedding generation, caching, and batch processing.
"""

import asyncio
import json
import time
from typing import List
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import redis.asyncio as redis

from ardha.services.embedding_service import (
    CacheError,
    EmbeddingError,
    LocalEmbeddingService,
    ModelLoadError,
    get_embedding_service,
    init_embedding_service,
)


@pytest.fixture
async def mock_redis():
    """Mock Redis client for testing."""
    mock_client = AsyncMock(spec=redis.Redis)
    mock_client.ping.return_value = True
    mock_client.get.return_value = None
    mock_client.setex.return_value = True
    mock_client.keys.return_value = []
    mock_client.delete.return_value = 0
    return mock_client


@pytest.fixture
async def embedding_service(mock_redis):
    """Create embedding service instance for testing."""
    service = LocalEmbeddingService()
    service.redis_client = mock_redis
    return service


@pytest.fixture
def sample_texts():
    """Sample texts for testing."""
    return [
        "This is a simple test sentence.",
        "Another sentence for testing embeddings.",
        "Machine learning is fascinating.",
        "Natural language processing with transformers.",
        "Vector representations capture semantic meaning.",
    ]


class TestLocalEmbeddingService:
    """Test cases for LocalEmbeddingService."""

    def test_service_initialization(self, embedding_service):
        """Test service initialization."""
        assert embedding_service.model_name == "sentence-transformers/all-MiniLM-L6-v2"
        assert embedding_service.dimension == 384
        assert embedding_service.model is None  # Not loaded yet
        assert embedding_service.cache_ttl == 86400
        assert embedding_service.cache_prefix == "embeddings:"
        assert embedding_service._total_embeddings == 0
        assert embedding_service._cache_hits == 0
        assert embedding_service._cache_misses == 0

    @pytest.mark.asyncio
    async def test_redis_connection_parsing(self):
        """Test Redis URL parsing for different formats."""
        # Test different URL formats
        test_cases = [
            ("redis://localhost:6379/0", ("localhost", 6379, 0)),
            ("redis://127.0.0.1:6380/1", ("127.0.0.1", 6380, 1)),
            ("redis://redis-server:6379/2", ("redis-server", 6379, 2)),
        ]

        for url, expected in test_cases:
            mock_redis = AsyncMock(spec=redis.Redis)
            mock_redis.ping.return_value = True

            service = LocalEmbeddingService()
            service.settings.redis.url = url

            with patch("redis.asyncio.Redis", return_value=mock_redis):
                await service._initialize_redis()

                # Verify Redis was called with correct parameters
                mock_redis.assert_called()
                call_kwargs = mock_redis.call_args[1]
                assert call_kwargs["host"] == expected[0]
                assert call_kwargs["port"] == expected[1]
                assert call_kwargs["db"] == expected[2]

    @pytest.mark.asyncio
    async def test_model_loading(self, embedding_service):
        """Test model loading functionality."""
        with patch("sentence_transformers.SentenceTransformer") as mock_transformer:
            mock_model = MagicMock()
            mock_model.get_sentence_embedding_dimension.return_value = 384
            mock_transformer.return_value = mock_model

            # Load model
            await embedding_service.load_model()

            # Verify model was loaded
            assert embedding_service.model is mock_model
            mock_transformer.assert_called_once_with("sentence-transformers/all-MiniLM-L6-v2")

    @pytest.mark.asyncio
    async def test_model_loading_thread_safety(self, embedding_service):
        """Test that model loading is thread-safe."""
        with patch("sentence_transformers.SentenceTransformer") as mock_transformer:
            mock_model = MagicMock()
            mock_model.get_sentence_embedding_dimension.return_value = 384
            mock_transformer.return_value = mock_model

            # Simulate concurrent loading
            tasks = [embedding_service.load_model() for _ in range(5)]

            await asyncio.gather(*tasks)

            # Verify model was loaded only once
            mock_transformer.assert_called_once()
            assert embedding_service.model is mock_model

    @pytest.mark.asyncio
    async def test_model_loading_error(self, embedding_service):
        """Test model loading error handling."""
        with patch(
            "sentence_transformers.SentenceTransformer", side_effect=Exception("Model load failed")
        ):
            with pytest.raises(ModelLoadError, match="Model loading failed"):
                await embedding_service.load_model()

    @pytest.mark.asyncio
    async def test_generate_embedding(self, embedding_service, sample_texts):
        """Test single embedding generation."""
        # Mock model
        mock_model = MagicMock()
        mock_embedding = [0.1, 0.2, 0.3, 0.4] * 96  # 384 dimensions
        mock_model.encode.return_value = mock_embedding
        embedding_service.model = mock_model

        # Generate embedding
        text = sample_texts[0]
        result = await embedding_service.generate_embedding(text)

        # Verify result
        assert isinstance(result, list)
        assert len(result) == 384
        assert all(isinstance(x, float) for x in result)

        # Verify model was called correctly
        mock_model.encode.assert_called_once_with(
            text.strip(),
            convert_to_numpy=True,
            normalize_embeddings=True,
        )

        # Verify metrics updated
        assert embedding_service._total_embeddings == 1
        assert embedding_service._total_time > 0

    @pytest.mark.asyncio
    async def test_generate_embedding_empty_text(self, embedding_service):
        """Test embedding generation with empty text."""
        with pytest.raises(EmbeddingError, match="Cannot embed empty text"):
            await embedding_service.generate_embedding("")

        with pytest.raises(EmbeddingError, match="Cannot embed empty text"):
            await embedding_service.generate_embedding("   ")

    @pytest.mark.asyncio
    async def test_generate_embedding_with_cache(self, embedding_service, sample_texts):
        """Test embedding generation with caching."""
        text = sample_texts[0]
        cache_key = embedding_service._generate_cache_key(text)

        # Mock cache hit
        cached_embedding = [0.5, 0.6, 0.7, 0.8] * 96
        embedding_service.redis_client.get.return_value = json.dumps(cached_embedding)

        # Mock model to prevent real loading
        mock_model = MagicMock()
        embedding_service.model = mock_model

        # Generate embedding (should use cache)
        result = await embedding_service.generate_embedding(text)

        # Verify cache was used
        assert result == cached_embedding
        embedding_service.redis_client.get.assert_called_once_with(cache_key)
        embedding_service.redis_client.setex.assert_not_called()

        # Verify cache metrics
        assert embedding_service._cache_hits == 1
        assert embedding_service._cache_misses == 0

    @pytest.mark.asyncio
    async def test_generate_embedding_cache_miss(self, embedding_service, sample_texts):
        """Test embedding generation with cache miss."""
        text = sample_texts[0]
        cache_key = embedding_service._generate_cache_key(text)

        # Mock model
        mock_model = MagicMock()
        mock_embedding = [0.1, 0.2, 0.3, 0.4] * 96
        mock_model.encode.return_value = mock_embedding
        embedding_service.model = mock_model

        # Mock cache miss
        embedding_service.redis_client.get.return_value = None

        # Generate embedding
        result = await embedding_service.generate_embedding(text)

        # Verify cache was set
        embedding_service.redis_client.setex.assert_called_once_with(
            cache_key, embedding_service.cache_ttl, json.dumps(result)
        )

        # Verify cache metrics
        assert embedding_service._cache_hits == 0
        assert embedding_service._cache_misses == 1

    @pytest.mark.asyncio
    async def test_generate_batch_embeddings(self, embedding_service, sample_texts):
        """Test batch embedding generation."""
        # Mock model
        mock_model = MagicMock()
        mock_embeddings = [
            [0.1, 0.2, 0.3, 0.4] * 96,  # First embedding
            [0.5, 0.6, 0.7, 0.8] * 96,  # Second embedding
            [0.9, 1.0, 1.1, 1.2] * 96,  # Third embedding
        ]
        mock_model.encode.return_value = mock_embeddings
        embedding_service.model = mock_model

        # Generate batch embeddings
        texts = sample_texts[:3]
        results = await embedding_service.generate_batch_embeddings(texts)

        # Verify results
        assert isinstance(results, list)
        assert len(results) == 3
        assert all(isinstance(embedding, list) for embedding in results)
        assert all(len(embedding) == 384 for embedding in results)

        # Verify metrics updated
        assert embedding_service._total_embeddings == 3

    @pytest.mark.asyncio
    async def test_generate_batch_embeddings_with_cache(self, embedding_service, sample_texts):
        """Test batch embedding generation with mixed cache hits/misses."""
        texts = sample_texts[:3]

        # Mock partial cache hits
        cached_embedding = [0.5, 0.6, 0.7, 0.8] * 96
        embedding_service.redis_client.get.side_effect = [
            json.dumps(cached_embedding),  # First text cached
            None,  # Second text not cached
            None,  # Third text not cached
        ]

        # Mock model for uncached texts
        mock_model = MagicMock()
        mock_embeddings = [
            [0.1, 0.2, 0.3, 0.4] * 96,  # Second embedding
            [0.9, 1.0, 1.1, 1.2] * 96,  # Third embedding
        ]
        mock_model.encode.return_value = mock_embeddings
        embedding_service.model = mock_model

        # Generate batch embeddings
        results = await embedding_service.generate_batch_embeddings(texts)

        # Verify results
        assert len(results) == 3
        assert results[0] == cached_embedding  # From cache
        assert results[1] == mock_embeddings[0]  # From model
        assert results[2] == mock_embeddings[1]  # From model

        # Verify cache metrics
        assert embedding_service._cache_hits == 1
        assert embedding_service._cache_misses == 2

    @pytest.mark.asyncio
    async def test_generate_batch_embeddings_empty_input(self, embedding_service):
        """Test batch embedding generation with empty input."""
        result = await embedding_service.generate_batch_embeddings([])
        assert result == []

    @pytest.mark.asyncio
    async def test_generate_batch_embeddings_all_empty(self, embedding_service):
        """Test batch embedding generation with all empty texts."""
        texts = ["", "   ", ""]
        result = await embedding_service.generate_batch_embeddings(texts)
        assert result == [[], [], []]

    @pytest.mark.asyncio
    async def test_cache_key_generation(self, embedding_service):
        """Test cache key generation."""
        text = "This is a test sentence"
        cache_key = embedding_service._generate_cache_key(text)

        # Verify key format
        assert cache_key.startswith("embeddings:")
        assert len(cache_key) == len("embeddings:") + 64  # SHA-256 hash

        # Verify consistency
        cache_key2 = embedding_service._generate_cache_key(text)
        assert cache_key == cache_key2

        # Verify uniqueness for different texts
        different_text = "This is a different sentence"
        cache_key3 = embedding_service._generate_cache_key(different_text)
        assert cache_key != cache_key3

    @pytest.mark.asyncio
    async def test_get_embedding_info(self, embedding_service):
        """Test embedding service information retrieval."""
        # Set some metrics
        embedding_service._total_embeddings = 100
        embedding_service._cache_hits = 70
        embedding_service._cache_misses = 30
        embedding_service._total_time = 1500.0

        # Get info
        info = await embedding_service.get_embedding_info()

        # Verify info structure
        assert "model_name" in info
        assert "dimension" in info
        assert "model_loaded" in info
        assert "cache_enabled" in info
        assert "cache_ttl" in info
        assert "total_embeddings" in info
        assert "cache_hits" in info
        assert "cache_misses" in info
        assert "cache_hit_rate" in info
        assert "average_time" in info

        # Verify values
        assert info["model_name"] == "sentence-transformers/all-MiniLM-L6-v2"
        assert info["dimension"] == 384
        assert info["total_embeddings"] == 100
        assert info["cache_hit_rate"] == 0.7  # 70/100
        assert info["average_time"] == 15.0  # 1500/100

    @pytest.mark.asyncio
    async def test_health_check_healthy(self, embedding_service):
        """Test health check when service is healthy."""
        # Mock model loaded
        embedding_service.model = MagicMock()

        # Mock Redis ping
        embedding_service.redis_client.ping.return_value = True

        # Mock successful embedding generation
        with patch.object(embedding_service, "generate_embedding", return_value=[0.1, 0.2, 0.3]):
            result = await embedding_service.health_check()

            # Verify health status
            assert result["status"] == "healthy"
            assert result["model_status"] == "loaded"
            assert result["cache_status"] == "healthy"
            assert result["generation_status"] == "working"

    @pytest.mark.asyncio
    async def test_health_check_degraded(self, embedding_service):
        """Test health check when service is degraded."""
        # Mock model not loaded
        embedding_service.model = None

        result = await embedding_service.health_check()

        # Verify degraded status
        assert result["status"] == "degraded"
        assert result["model_status"] == "not_loaded"

    @pytest.mark.asyncio
    async def test_health_check_unhealthy(self, embedding_service):
        """Test health check when service is unhealthy."""
        # Mock model loaded
        embedding_service.model = MagicMock()

        # Mock error during health check
        with patch.object(
            embedding_service, "generate_embedding", side_effect=Exception("Test error")
        ):
            result = await embedding_service.health_check()

            # Verify unhealthy status
            assert result["status"] == "unhealthy"
            assert "error" in result

    @pytest.mark.asyncio
    async def test_clear_cache(self, embedding_service):
        """Test cache clearing functionality."""
        # Mock cache keys
        mock_keys = ["embeddings:key1", "embeddings:key2", "embeddings:key3"]
        embedding_service.redis_client.keys.return_value = mock_keys
        embedding_service.redis_client.delete.return_value = 3

        # Clear cache
        result = await embedding_service.clear_cache()

        # Verify cache was cleared
        assert result is True
        embedding_service.redis_client.keys.assert_called_once_with("embeddings:*")
        embedding_service.redis_client.delete.assert_called_once_with(*mock_keys)

        # Verify metrics reset
        assert embedding_service._cache_hits == 0
        assert embedding_service._cache_misses == 0

    @pytest.mark.asyncio
    async def test_clear_cache_no_redis(self, embedding_service):
        """Test cache clearing when Redis is not available."""
        embedding_service.redis_client = None

        result = await embedding_service.clear_cache()

        # Verify operation failed gracefully
        assert result is False

    @pytest.mark.asyncio
    async def test_context_manager(self):
        """Test async context manager functionality."""
        mock_redis = AsyncMock(spec=redis.Redis)
        mock_redis.ping.return_value = True

        with patch("redis.asyncio.Redis", return_value=mock_redis):
            async with LocalEmbeddingService() as service:
                assert service.redis_client is mock_redis
                mock_redis.ping.assert_called_once()

    @pytest.mark.asyncio
    async def test_cache_error_handling(self, embedding_service, sample_texts):
        """Test cache error handling."""
        text = sample_texts[0]

        # Mock Redis error
        embedding_service.redis_client.get.side_effect = Exception("Redis error")

        # Mock model
        mock_model = MagicMock()
        mock_embedding = [0.1, 0.2, 0.3, 0.4] * 96
        mock_model.encode.return_value = mock_embedding
        embedding_service.model = mock_model

        # Generate embedding (should handle cache error gracefully)
        result = await embedding_service.generate_embedding(text)

        # Verify embedding was generated despite cache error
        assert result == mock_embedding
        assert embedding_service._cache_misses == 1


class TestGlobalServiceFunctions:
    """Test cases for global service functions."""

    def test_get_embedding_service_singleton(self):
        """Test that get_embedding_service returns singleton instance."""
        service1 = get_embedding_service()
        service2 = get_embedding_service()

        assert service1 is service2
        assert isinstance(service1, LocalEmbeddingService)

    @pytest.mark.asyncio
    async def test_init_embedding_service(self):
        """Test embedding service initialization."""
        with patch("ardha.services.embedding_service.get_embedding_service") as mock_get_service:
            mock_service = MagicMock()
            mock_get_service.return_value = mock_service

            result = await init_embedding_service()

            # Verify service was returned
            assert result is mock_service
            mock_get_service.assert_called_once()


class TestEmbeddingServiceIntegration:
    """Integration tests for embedding service (with real dependencies)."""

    @pytest.mark.asyncio
    async def test_real_model_loading(self):
        """Test real model loading (may be slow, use with caution)."""
        pytest.skip("Skip real model loading in unit tests - use integration tests")

    @pytest.mark.asyncio
    async def test_real_embedding_generation(self):
        """Test real embedding generation (may be slow, use with caution)."""
        pytest.skip("Skip real embedding generation in unit tests - use integration tests")


if __name__ == "__main__":
    pytest.main([__file__])
