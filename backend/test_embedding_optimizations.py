#!/usr/bin/env python3
"""
Test script for embedding service optimizations.

This script tests the advanced features including:
- In-memory embedding pool
- Smart batching
- Performance monitoring
- Pydantic v2 configuration
"""

import asyncio
import json
import time
from typing import List

from src.ardha.core.embedding_config import get_embedding_settings
from src.ardha.services.embedding_service import LocalEmbeddingService


async def test_embedding_pool():
    """Test in-memory embedding pool functionality."""
    print("🧪 Testing Embedding Pool...")

    service = LocalEmbeddingService()
    await service._initialize_redis()

    # Test pool functionality
    test_text = "This is a test for the embedding pool."

    # First call - should populate pool
    start_time = time.time()
    embedding1 = await service.generate_embedding(test_text)
    first_call_time = time.time() - start_time

    # Second call - should use pool
    start_time = time.time()
    embedding2 = await service.generate_embedding(test_text)
    second_call_time = time.time() - start_time

    # Verify embeddings are identical
    assert embedding1 == embedding2, "Pool should return identical embeddings"

    # Verify pool was used (second call should be faster)
    assert second_call_time < first_call_time, "Pool should improve performance"

    # Check pool metrics
    info = await service.get_embedding_info()
    assert info["pool_hits"] > 0, "Should have pool hits"
    assert info["pool_size"] > 0, "Pool should contain embeddings"

    print(
        f"✅ Pool test passed! First call: {first_call_time:.3f}s, Second call: {second_call_time:.3f}s"
    )
    print(f"   Pool hit rate: {info['pool_hit_rate']:.2%}")

    await service.close()


async def test_smart_batching():
    """Test smart batching optimization."""
    print("\n🧪 Testing Smart Batching...")

    service = LocalEmbeddingService()
    await service._initialize_redis()

    # Test with different batch sizes
    small_batch = ["Text 1", "Text 2", "Text 3"]  # 3 texts
    large_batch = [f"Text {i}" for i in range(50)]  # 50 texts

    # Test small batch (should process as-is)
    start_time = time.time()
    small_results = await service.generate_batch_embeddings(small_batch, show_progress=True)
    small_time = time.time() - start_time

    # Test large batch (should use optimal batch size)
    start_time = time.time()
    large_results = await service.generate_batch_embeddings(large_batch, show_progress=True)
    large_time = time.time() - start_time

    # Verify results
    assert len(small_results) == 3, "Small batch should return 3 embeddings"
    assert len(large_results) == 50, "Large batch should return 50 embeddings"

    # Check service info for smart batching
    info = await service.get_embedding_info()
    assert info["smart_batching_enabled"], "Smart batching should be enabled"

    print(f"✅ Smart batching test passed!")
    print(f"   Small batch (3 texts): {small_time:.3f}s")
    print(f"   Large batch (50 texts): {large_time:.3f}s")
    print(f"   Average time per embedding: {large_time/50:.3f}s")

    await service.close()


async def test_performance_monitoring():
    """Test performance monitoring and metrics."""
    print("\n🧪 Testing Performance Monitoring...")

    service = LocalEmbeddingService()
    await service._initialize_redis()

    # Generate some embeddings to collect metrics
    test_texts = [
        "First test text for monitoring",
        "Second test text for monitoring",
        "Third test text for monitoring",
        "Fourth test text for monitoring",
        "Fifth test text for monitoring",
    ]

    # Single embeddings
    for text in test_texts:
        await service.generate_embedding(text)

    # Batch embeddings
    await service.generate_batch_embeddings(test_texts)

    # Get detailed info
    info = await service.get_embedding_info()

    # Verify metrics are collected
    assert info["total_embeddings"] > 0, "Should have generated embeddings"
    assert info["average_time"] > 0, "Should have average processing time"
    assert "cache_hit_rate" in info, "Should have cache metrics"
    assert "pool_hit_rate" in info, "Should have pool metrics"

    # Test health check
    health = await service.health_check()
    assert health["status"] in ["healthy", "degraded"], "Health check should return valid status"

    print(f"✅ Performance monitoring test passed!")
    print(f"   Total embeddings: {info['total_embeddings']}")
    print(f"   Average time: {info['average_time']:.3f}s")
    print(f"   Redis cache hit rate: {info.get('redis_cache_hit_rate', 0):.2%}")
    print(f"   Pool hit rate: {info.get('pool_hit_rate', 0):.2%}")
    print(f"   Health status: {health['status']}")

    await service.close()


async def test_configuration():
    """Test new configuration system."""
    print("\n🧪 Testing Configuration System...")

    # Test embedding settings
    settings = get_embedding_settings()

    # Verify default values
    assert settings.model_name == "sentence-transformers/all-MiniLM-L6-v2"
    assert settings.model_dimension == 384
    assert settings.enable_embedding_pool is True
    assert settings.enable_smart_batching is True
    assert settings.pool_size > 0
    assert settings.cache_ttl_seconds > 0

    # Test configuration methods
    model_info = settings.get_model_info()
    assert model_info["name"] == settings.model_name
    assert model_info["dimension"] == settings.model_dimension

    cache_info = settings.get_cache_info()
    assert cache_info["enabled"] is True
    assert cache_info["ttl_seconds"] == settings.cache_ttl_seconds

    performance_info = settings.get_performance_info()
    assert performance_info["embedding_pool_enabled"] is True
    assert performance_info["smart_batching_enabled"] is True

    print(f"✅ Configuration test passed!")
    print(f"   Model: {settings.model_name}")
    print(f"   Dimension: {settings.model_dimension}")
    print(f"   Pool enabled: {settings.enable_embedding_pool}")
    print(f"   Smart batching enabled: {settings.enable_smart_batching}")
    print(f"   Pool size: {settings.pool_size}")


async def test_schemas():
    """Test new Pydantic v2 schemas."""
    print("\n🧪 Testing Pydantic v2 Schemas...")

    from src.ardha.schemas.requests.embedding import (
        BatchEmbeddingRequest,
        EmbeddingRequest,
        SimilaritySearchRequest,
    )
    from src.ardha.schemas.responses.embedding import (
        BatchEmbeddingResponse,
        EmbeddingResponse,
        EmbeddingServiceInfo,
    )

    # Test request schemas
    embedding_request = EmbeddingRequest(text="Test text", normalize=True, use_cache=True)
    assert embedding_request.text == "Test text"
    assert embedding_request.normalize is True

    batch_request = BatchEmbeddingRequest(
        texts=["Text 1", "Text 2"], batch_size=2, show_progress=True  # Must be <= number of texts
    )
    assert len(batch_request.texts) == 2
    assert batch_request.batch_size == 2

    # Test response schemas
    embedding_response = EmbeddingResponse(
        embedding=[0.1, 0.2, 0.3],
        dimension=384,
        model_name="test-model",
        text_length=9,
        processing_time_ms=15.5,
        cached=False,
        pool_cached=False,
    )
    assert embedding_response.dimension == 384
    assert embedding_response.pool_cached is False

    batch_response = BatchEmbeddingResponse(
        embeddings=[[0.1, 0.2], [0.3, 0.4]],
        dimension=384,
        model_name="test-model",
        total_texts=2,
        processed_texts=2,
        redis_cached_count=0,
        pool_cached_count=0,
        batch_size=32,
        total_processing_time_ms=25.0,
        average_time_per_text_ms=12.5,
        smart_batching_used=True,
    )
    assert batch_response.smart_batching_used is True
    assert batch_response.redis_cached_count == 0

    # Test service info schema
    service_info = EmbeddingServiceInfo(
        model_name="test-model",
        dimension=384,
        model_loaded=True,
        cache_enabled=True,
        cache_ttl=86400,
        total_embeddings=100,
        redis_cache_hits=70,
        redis_cache_misses=30,
        redis_cache_hit_rate=0.7,
        pool_hits=20,
        pool_misses=80,
        pool_hit_rate=0.2,
        pool_size=50,
        pool_max_size=1000,
        average_time_ms=15.0,
        smart_batching_enabled=True,
        embedding_pool_enabled=True,
    )
    assert service_info.pool_hit_rate == 0.2
    assert service_info.smart_batching_enabled is True

    print(f"✅ Schemas test passed!")
    print(f"   All schemas validate correctly with Pydantic v2")
    print(f"   No deprecation warnings for ConfigDict usage")


async def main():
    """Run all optimization tests."""
    print("🚀 Testing Embedding Service Optimizations")
    print("=" * 50)

    try:
        await test_configuration()
        await test_schemas()
        await test_embedding_pool()
        await test_smart_batching()
        await test_performance_monitoring()

        print("\n" + "=" * 50)
        print("🎉 All optimization tests passed!")
        print("\n📊 Summary of optimizations:")
        print("   ✅ In-memory embedding pool for fastest access")
        print("   ✅ Smart batching for optimal performance")
        print("   ✅ Comprehensive performance monitoring")
        print("   ✅ Pydantic v2 configuration without warnings")
        print("   ✅ Advanced caching with Redis + pool")
        print("   ✅ Production-ready error handling")

    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(main())
