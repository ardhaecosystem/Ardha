"""
Unit tests for local embedding service.

Tests the all-MiniLM-L6-v2 local embedding model with caching,
batch processing, and performance optimizations.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import numpy as np
import pytest

from ardha.services.embedding_service import EmbeddingError, LocalEmbeddingService, ModelLoadError


@pytest.mark.asyncio
class TestLocalEmbeddingService:
    """Test local embedding service with all-MiniLM-L6-v2"""

    async def test_model_info(self):
        """Test model information"""
        service = LocalEmbeddingService()
        info = await service.get_embedding_info()

        assert info["model_name"] == "sentence-transformers/all-MiniLM-L6-v2"
        assert info["dimensions"] == 384
        assert info["cost_per_embedding"] == 0.0
        assert info["provider"] == "local"

    async def test_generate_embedding_success(self, mock_local_embedding):
        """Test single embedding generation"""
        service = LocalEmbeddingService()

        # Mock the model loading and encoding
        with (
            patch.object(service, "load_model", new=AsyncMock()),
            patch("sentence_transformers.SentenceTransformer") as mock_model,
        ):

            mock_model_instance = MagicMock()
            mock_model_instance.encode.return_value = np.array(mock_local_embedding)
            mock_model.return_value = mock_model_instance
            mock_model_instance.get_sentence_embedding_dimension.return_value = 384

            text = "This is a test sentence for embedding"
            embedding = await service.generate_embedding(text)

            assert len(embedding) == 384
            assert all(isinstance(x, float) for x in embedding)
            mock_model_instance.encode.assert_called_once()

    async def test_generate_embeddings_batch(self, mock_embedding_batch):
        """Test batch embedding generation"""
        service = LocalEmbeddingService()

        # Mock the model loading and encoding
        with (
            patch.object(service, "load_model", new=AsyncMock()),
            patch("sentence_transformers.SentenceTransformer") as mock_model,
        ):

            mock_model_instance = MagicMock()
            mock_model_instance.encode.return_value = np.array(mock_embedding_batch)
            mock_model.return_value = mock_model_instance
            mock_model_instance.get_sentence_embedding_dimension.return_value = 384

            texts = [f"Test sentence {i}" for i in range(5)]
            embeddings = await service.generate_batch_embeddings(texts)

            assert len(embeddings) == 5
            assert all(len(emb) == 384 for emb in embeddings)

    async def test_embedding_caching(self, mock_redis, mock_local_embedding):
        """Test Redis caching of embeddings"""
        service = LocalEmbeddingService()
        service.redis_client = mock_redis

        # Mock cache miss first, then hit
        mock_redis.get.side_effect = [None, mock_local_embedding]

        with (
            patch.object(service, "load_model", new=AsyncMock()),
            patch("sentence_transformers.SentenceTransformer") as mock_model,
        ):

            mock_model_instance = MagicMock()
            mock_model_instance.encode.return_value = np.array(mock_local_embedding)
            mock_model.return_value = mock_model_instance
            mock_model_instance.get_sentence_embedding_dimension.return_value = 384

            text = "Cache this embedding"

            # First call - generates and caches
            embedding1 = await service.generate_embedding(text)

            # Second call - retrieves from cache
            embedding2 = await service.generate_embedding(text)

            assert embedding1 == embedding2
            # Verify Redis was called
            assert mock_redis.get.called
            assert mock_redis.setex.called

    async def test_in_memory_pool_caching(self, mock_local_embedding):
        """Test in-memory pool caching"""
        service = LocalEmbeddingService()
        service.settings.enable_embedding_pool = True

        with (
            patch.object(service, "load_model", new=AsyncMock()),
            patch("sentence_transformers.SentenceTransformer") as mock_model,
        ):

            mock_model_instance = MagicMock()
            mock_model_instance.encode.return_value = np.array(mock_local_embedding)
            mock_model.return_value = mock_model_instance
            mock_model_instance.get_sentence_embedding_dimension.return_value = 384

            text = "Pool this embedding"

            # First call - generates and pools
            embedding1 = await service.generate_embedding(text)

            # Second call - retrieves from pool
            embedding2 = await service.generate_embedding(text)

            assert embedding1 == embedding2
            assert service._pool_hits == 1

    async def test_text_truncation(self):
        """Test long text handling (service handles truncation internally)"""
        service = LocalEmbeddingService()
        long_text = " ".join(["word"] * 1000)  # Very long text

        # Service should handle long text without error
        with (
            patch.object(service, "load_model", new=AsyncMock()),
            patch("sentence_transformers.SentenceTransformer") as mock_model,
        ):

            mock_model_instance = MagicMock()
            mock_model_instance.encode.return_value = np.array([0.1] * 384)
            mock_model.return_value = mock_model_instance
            mock_model_instance.get_sentence_embedding_dimension.return_value = 384

            embedding = await service.generate_embedding(long_text)
            assert len(embedding) == 384

    async def test_empty_text_handling(self):
        """Test handling of empty text"""
        service = LocalEmbeddingService()

        with pytest.raises(EmbeddingError, match="Cannot embed empty text"):
            await service.generate_embedding("")

    async def test_model_loading_failure(self):
        """Test model loading failure"""
        service = LocalEmbeddingService()

        with patch("sentence_transformers.SentenceTransformer") as mock_model:
            mock_model.side_effect = Exception("Model loading failed")

            with pytest.raises(ModelLoadError, match="Model loading failed"):
                await service.load_model()

    async def test_cache_error_handling(self, mock_redis):
        """Test cache error handling"""
        service = LocalEmbeddingService()
        service.redis_client = mock_redis
        mock_redis.get.side_effect = Exception("Redis error")

        with (
            patch.object(service, "load_model", new=AsyncMock()),
            patch("sentence_transformers.SentenceTransformer") as mock_model,
        ):

            mock_model_instance = MagicMock()
            mock_model_instance.encode.return_value = np.array([0.1] * 384)
            mock_model.return_value = mock_model_instance
            mock_model_instance.get_sentence_embedding_dimension.return_value = 384

            # Should still work even if cache fails
            embedding = await service.generate_embedding("test")
            assert len(embedding) == 384

    async def test_smart_batching(self):
        """Test smart batch size optimization"""
        service = LocalEmbeddingService()
        service.settings.enable_smart_batching = True
        service.settings.smart_batch_threshold = 10
        service.settings.default_batch_size = 32
        service.settings.max_batch_size = 64

        # Small batch - should return as-is
        assert service._optimize_batch_size(5) == 5

        # Medium batch - should use default
        assert service._optimize_batch_size(20) == 32

        # Large batch - should use max
        assert service._optimize_batch_size(100) == 64

    async def test_health_check(self, mock_redis, mock_local_embedding):
        """Test health check functionality"""
        service = LocalEmbeddingService()
        service.redis_client = mock_redis
        service.model = MagicMock()

        with patch.object(service, "generate_embedding", return_value=mock_local_embedding):
            health = await service.health_check()

            assert health["status"] == "healthy"
            assert health["model_status"] == "loaded"
            assert health["generation_status"] == "working"
            assert health["model_name"] == "sentence-transformers/all-MiniLM-L6-v2"

    async def test_health_check_degraded(self, mock_redis):
        """Test health check when model not loaded"""
        service = LocalEmbeddingService()
        service.redis_client = mock_redis
        service.model = None

        health = await service.health_check()

        assert health["status"] == "degraded"
        assert health["model_status"] == "not_loaded"

    async def test_clear_cache(self, mock_redis):
        """Test cache clearing functionality"""
        service = LocalEmbeddingService()
        service.redis_client = mock_redis
        mock_redis.keys.return_value = ["key1", "key2", "key3"]

        result = await service.clear_cache()

        assert result is True
        mock_redis.delete.assert_called_once_with("key1", "key2", "key3")

    async def test_clear_cache_no_redis(self):
        """Test cache clearing when Redis not available"""
        service = LocalEmbeddingService()
        service.redis_client = None

        result = await service.clear_cache()

        assert result is False

    async def test_performance_metrics(self, mock_local_embedding):
        """Test performance metrics tracking"""
        service = LocalEmbeddingService()

        with (
            patch.object(service, "load_model", new=AsyncMock()),
            patch("sentence_transformers.SentenceTransformer") as mock_model,
        ):

            mock_model_instance = MagicMock()
            mock_model_instance.encode.return_value = np.array(mock_local_embedding)
            mock_model.return_value = mock_model_instance
            mock_model_instance.get_sentence_embedding_dimension.return_value = 384

            # Generate some embeddings
            await service.generate_embedding("test1")
            await service.generate_embedding("test2")

            info = await service.get_embedding_info()

            assert info["total_embeddings"] == 2
            assert info["cache_misses"] == 2  # No cache in this test
            assert info["average_time"] > 0

    async def test_batch_with_empty_texts(self):
        """Test batch processing with empty texts"""
        service = LocalEmbeddingService()

        # Empty list should return empty list
        result = await service.generate_batch_embeddings([])
        assert result == []

        # List with empty strings should handle gracefully
        with patch.object(service, "load_model", new=AsyncMock()):
            result = await service.generate_batch_embeddings(["", "test", ""])
            assert len(result) == 3
            assert result[0] == []  # Empty string -> empty embedding
            assert result[2] == []  # Empty string -> empty embedding

    async def test_cache_key_generation(self):
        """Test cache key generation"""
        service = LocalEmbeddingService()
        service.settings.cache_prefix = "test:"

        text = "Test text for caching"
        key1 = service._generate_cache_key(text)
        key2 = service._generate_cache_key(text)

        # Same text should generate same key
        assert key1 == key2
        assert key1.startswith("test:")

        # Different text should generate different key
        key3 = service._generate_cache_key("Different text")
        assert key2 != key3

    async def test_pool_lru_eviction(self, mock_local_embedding):
        """Test in-memory pool LRU eviction"""
        service = LocalEmbeddingService()
        service.settings.enable_embedding_pool = True
        service._pool_max_size = 2  # Very small pool for testing

        with (
            patch.object(service, "load_model", new=AsyncMock()),
            patch("sentence_transformers.SentenceTransformer") as mock_model,
        ):

            mock_model_instance = MagicMock()
            mock_model_instance.encode.return_value = np.array(mock_local_embedding)
            mock_model.return_value = mock_model_instance
            mock_model_instance.get_sentence_embedding_dimension.return_value = 384

            # Fill pool beyond capacity
            await service.generate_embedding("text1")
            await service.generate_embedding("text2")
            await service.generate_embedding("text3")

            # Pool should be at max size
            assert len(service._embedding_pool) == 2
            assert service._pool_misses == 3  # All missed pool
