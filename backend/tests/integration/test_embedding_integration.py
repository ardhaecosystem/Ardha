"""
Integration tests for embedding service.

This module provides integration tests for the embedding service
including Redis caching and batch processing performance.
"""

import asyncio
import time
from typing import List

import pytest

from ardha.services.embedding_service import LocalEmbeddingService, get_embedding_service


class TestEmbeddingServiceIntegration:
    """Integration tests for embedding service."""
    
    @pytest.mark.asyncio
    async def test_real_embedding_generation(self):
        """Test real embedding generation with the actual model."""
        service = LocalEmbeddingService()
        
        # Load the real model
        await service.load_model()
        assert service.model is not None
        
        # Generate embedding for real text
        text = "This is a test sentence for embedding generation."
        start_time = time.time()
        
        embedding = await service.generate_embedding(text)
        
        processing_time = time.time() - start_time
        
        # Verify embedding properties
        assert isinstance(embedding, list)
        assert len(embedding) == 384  # all-MiniLM-L6-v2 dimension
        assert all(isinstance(x, float) for x in embedding)
        assert all(-1.0 <= x <= 1.0 for x in embedding)  # Normalized embeddings
        
        # Verify performance (should be reasonably fast)
        assert processing_time < 5.0  # Should complete within 5 seconds
        
        # Verify metrics updated
        assert service._total_embeddings == 1
        assert service._total_time > 0
    
    @pytest.mark.asyncio
    async def test_batch_embedding_performance(self):
        """Test batch embedding processing performance."""
        service = LocalEmbeddingService()
        
        # Load the real model
        await service.load_model()
        
        # Prepare test texts
        texts = [
            f"This is test sentence number {i} for batch processing."
            for i in range(10)
        ]
        
        # Test batch processing
        start_time = time.time()
        
        embeddings = await service.generate_batch_embeddings(texts)
        
        processing_time = time.time() - start_time
        
        # Verify results
        assert isinstance(embeddings, list)
        assert len(embeddings) == len(texts)
        
        # Verify each embedding
        for i, embedding in enumerate(embeddings):
            assert isinstance(embedding, list)
            assert len(embedding) == 384
            assert all(isinstance(x, float) for x in embedding)
        
        # Verify batch performance (should be faster than individual processing)
        average_time_per_embedding = processing_time / len(texts)
        assert average_time_per_embedding < 2.0  # Should be under 2 seconds per embedding
        
        # Verify metrics updated
        assert service._total_embeddings >= len(texts)
    
    @pytest.mark.asyncio
    async def test_embedding_consistency(self):
        """Test that embeddings are consistent for the same input."""
        service = LocalEmbeddingService()
        
        # Load the real model
        await service.load_model()
        
        # Generate embedding twice for the same text
        text = "Consistency test sentence."
        embedding1 = await service.generate_embedding(text)
        embedding2 = await service.generate_embedding(text)
        
        # Verify embeddings are identical (or very close due to floating point)
        assert len(embedding1) == len(embedding2) == 384
        
        # Check similarity (should be very high for identical inputs)
        similarity = sum(a * b for a, b in zip(embedding1, embedding2))
        assert similarity > 0.999  # Should be nearly identical
    
    @pytest.mark.asyncio
    async def test_different_text_embeddings(self):
        """Test that different texts produce different embeddings."""
        service = LocalEmbeddingService()
        
        # Load the real model
        await service.load_model()
        
        # Generate embeddings for different texts
        text1 = "This is about machine learning."
        text2 = "This is about cooking recipes."
        
        embedding1 = await service.generate_embedding(text1)
        embedding2 = await service.generate_embedding(text2)
        
        # Verify embeddings are different
        similarity = sum(a * b for a, b in zip(embedding1, embedding2))
        assert similarity < 0.9  # Should be significantly different
    
    @pytest.mark.asyncio
    async def test_service_info_and_health(self):
        """Test service information and health check."""
        service = LocalEmbeddingService()
        
        # Load model
        await service.load_model()
        
        # Test service info
        info = await service.get_embedding_info()
        
        assert info["model_name"] == "sentence-transformers/all-MiniLM-L6-v2"
        assert info["dimension"] == 384
        assert info["model_loaded"] is True
        assert info["total_embeddings"] >= 0
        assert "cache_hit_rate" in info
        assert "average_time" in info
        
        # Test health check
        health = await service.health_check()
        
        assert health["status"] in ["healthy", "degraded"]
        assert health["model_status"] == "loaded"
        assert health["model_name"] == "sentence-transformers/all-MiniLM-L6-v2"
        assert health["dimension"] == 384
    
    @pytest.mark.asyncio
    async def test_singleton_service(self):
        """Test that the global service singleton works correctly."""
        # Get service instances
        service1 = get_embedding_service()
        service2 = get_embedding_service()
        
        # Verify they are the same instance
        assert service1 is service2
        
        # Load model on one instance
        await service1.load_model()
        
        # Verify both instances have the model loaded
        assert service1.model is not None
        assert service2.model is not None
        assert service1.model is service2.model
    
    @pytest.mark.asyncio
    async def test_error_handling(self):
        """Test error handling for edge cases."""
        service = LocalEmbeddingService()
        
        # Load model
        await service.load_model()
        
        # Test empty text
        with pytest.raises(Exception):  # Should raise EmbeddingError
            await service.generate_embedding("")
        
        # Test very long text (should still work but might be slow)
        long_text = "This is a very long sentence. " * 100
        embedding = await service.generate_embedding(long_text)
        assert len(embedding) == 384
    
    @pytest.mark.asyncio
    async def test_memory_usage(self):
        """Test that memory usage is reasonable for batch processing."""
        service = LocalEmbeddingService()
        
        # Load model
        await service.load_model()
        
        # Process a larger batch
        texts = [
            f"Test sentence {i} for memory usage testing."
            for i in range(50)
        ]
        
        # Generate embeddings
        embeddings = await service.generate_batch_embeddings(texts)
        
        # Verify all embeddings were generated
        assert len(embeddings) == 50
        assert all(len(emb) == 384 for emb in embeddings)
        
        # Verify service metrics
        assert service._total_embeddings >= 50


class TestEmbeddingConfigurationIntegration:
    """Integration tests for embedding configuration."""
    
    def test_default_configuration(self):
        """Test default configuration values."""
        from ardha.core.embedding_config import get_embedding_settings
        
        settings = get_embedding_settings()
        
        # Verify default values
        assert settings.model_name == "sentence-transformers/all-MiniLM-L6-v2"
        assert settings.model_dimension == 384
        assert settings.enable_redis_cache is True
        assert settings.cache_ttl_seconds == 86400
        assert settings.default_batch_size == 32
        assert settings.max_batch_size == 128
        assert settings.normalize_embeddings is True
        
        # Test helper methods
        model_info = settings.get_model_info()
        assert model_info["name"] == settings.model_name
        assert model_info["dimension"] == settings.model_dimension
        
        cache_info = settings.get_cache_info()
        assert cache_info["enabled"] == settings.enable_redis_cache
        assert cache_info["ttl_seconds"] == settings.cache_ttl_seconds


if __name__ == "__main__":
    pytest.main([__file__])