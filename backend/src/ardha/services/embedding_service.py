"""
Local embedding service using sentence-transformers.

This module provides a production-ready local embedding service using
all-MiniLM-L6-v2 model with Redis caching, batch processing, and
thread-safe model loading with advanced performance optimizations.

Cost: $0.00 (completely free!)
Model: all-MiniLM-L6-v2 (384 dimensions, MIT license)
"""

import asyncio
import hashlib
import json
import logging
import time
from collections import OrderedDict
from typing import Any, Dict, List, Optional, Union
from uuid import UUID

import numpy as np
import redis.asyncio as redis
from sentence_transformers import SentenceTransformer

from ..core.config import get_settings
from ..core.embedding_config import get_embedding_settings

logger = logging.getLogger(__name__)


class EmbeddingError(Exception):
    """Base exception for embedding operations."""
    
    def __init__(self, message: str, error_type: str = "embedding_error"):
        super().__init__(message)
        self.message = message
        self.error_type = error_type


class ModelLoadError(EmbeddingError):
    """Raised when model loading fails."""
    pass


class CacheError(EmbeddingError):
    """Raised when cache operations fail."""
    pass


class LocalEmbeddingService:
    """
    Local embedding service using sentence-transformers.
    Model: all-MiniLM-L6-v2 (384 dimensions, MIT license)
    Cost: $0.00 (completely free!)
    
    Features:
    - Thread-safe model loading with lazy initialization
    - Redis caching with 24-hour TTL
    - Batch processing for efficiency
    - Support for multiple text lengths
    - Zero API costs (100% local)
    
    Attributes:
        model_name: Sentence transformer model name
        dimension: Embedding dimension (384 for all-MiniLM-L6-v2)
        model: Loaded sentence transformer model (lazy loaded)
        redis_client: Redis client for caching
        _model_lock: Async lock for thread-safe model loading
    """
    
    def __init__(self):
        """Initialize embedding service with advanced optimizations."""
        self.settings = get_embedding_settings()
        
        # Model configuration
        self.model_name = self.settings.model_name
        self.dimension = self.settings.model_dimension
        self.model = None  # Lazy load
        self._model_lock = asyncio.Lock()
        
        # Redis configuration
        self.redis_client: Optional[redis.Redis] = None
        self.cache_ttl = self.settings.cache_ttl_seconds
        self.cache_prefix = self.settings.cache_prefix
        
        # Advanced performance features
        self._embedding_pool: OrderedDict[str, List[float]] = OrderedDict()
        self._pool_max_size = self.settings.pool_size
        
        # Performance metrics
        self._cache_hits = 0
        self._cache_misses = 0
        self._total_embeddings = 0
        self._total_time = 0.0
        self._pool_hits = 0
        self._pool_misses = 0
        
        logger.info(f"LocalEmbeddingService initialized with model: {self.model_name}")
        logger.info(f"Advanced features: Pool={self.settings.enable_embedding_pool}, Smart batching={self.settings.enable_smart_batching}")
    
    async def __aenter__(self) -> "LocalEmbeddingService":
        """Async context manager entry."""
        await self._initialize_redis()
        return self
    
    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Async context manager exit."""
        await self.close()
    
    async def close(self) -> None:
        """Close Redis connection."""
        if self.redis_client:
            await self.redis_client.close()
            logger.info("Redis connection closed")
    
    async def _initialize_redis(self) -> None:
        """Initialize Redis connection for caching."""
        if not self.settings.enable_redis_cache:
            return
            
        try:
            # Parse Redis URL to get connection parameters
            import urllib.parse
            parsed_url = urllib.parse.urlparse(self.settings.redis_url)
            
            # Extract connection details
            host = parsed_url.hostname or "localhost"
            port = parsed_url.port or 6379
            db = int(parsed_url.path.lstrip('/')) if parsed_url.path else 0
            
            self.redis_client = redis.Redis(
                host=host,
                port=port,
                db=db,
                decode_responses=True,
                socket_connect_timeout=5,
                socket_timeout=5,
            )
            
            # Test connection
            await self.redis_client.ping()
            logger.info(f"Redis connection established for embedding cache at {host}:{port}/{db}")
            
        except Exception as e:
            logger.warning(f"Failed to connect to Redis for caching: {e}")
            self.redis_client = None
    
    def _get_from_pool(self, text: str) -> Optional[List[float]]:
        """Get embedding from in-memory pool (fastest cache)."""
        if not self.settings.enable_embedding_pool:
            return None
            
        cache_key = self._generate_cache_key(text)
        if cache_key in self._embedding_pool:
            # Move to end (LRU)
            self._embedding_pool.move_to_end(cache_key)
            self._pool_hits += 1
            return self._embedding_pool[cache_key]
        
        self._pool_misses += 1
        return None
    
    def _add_to_pool(self, text: str, embedding: List[float]) -> None:
        """Add embedding to in-memory pool."""
        if not self.settings.enable_embedding_pool:
            return
            
        cache_key = self._generate_cache_key(text)
        
        # Remove oldest if pool is full
        if len(self._embedding_pool) >= self._pool_max_size:
            self._embedding_pool.popitem(last=False)
        
        self._embedding_pool[cache_key] = embedding
    
    def _optimize_batch_size(self, num_texts: int) -> int:
        """Optimize batch size based on input and smart batching settings."""
        if not self.settings.enable_smart_batching:
            return min(num_texts, self.settings.default_batch_size)
        
        # Smart batching logic
        if num_texts <= self.settings.smart_batch_threshold:
            return num_texts  # Process small batches as-is
        elif num_texts <= self.settings.default_batch_size:
            return self.settings.default_batch_size
        else:
            # For large batches, use optimal size
            return min(num_texts, self.settings.max_batch_size)
    
    async def load_model(self) -> None:
        """
        Load model once and reuse (thread-safe).
        
        Raises:
            ModelLoadError: If model loading fails
        """
        if self.model is None:
            async with self._model_lock:
                if self.model is None:
                    try:
                        logger.info(f"Loading embedding model: {self.model_name}")
                        start_time = time.time()
                        
                        # Load model (this is the expensive operation)
                        self.model = SentenceTransformer(self.model_name)
                        
                        # Verify dimension
                        actual_dim = self.model.get_sentence_embedding_dimension()
                        if actual_dim != self.dimension:
                            logger.warning(
                                f"Model dimension mismatch: expected {self.dimension}, got {actual_dim}"
                            )
                            self.dimension = actual_dim
                        
                        load_time = time.time() - start_time
                        logger.info(f"Model loaded successfully in {load_time:.2f}s")
                        
                    except Exception as e:
                        logger.error(f"Failed to load embedding model: {e}")
                        raise ModelLoadError(f"Model loading failed: {e}")
    
    def _generate_cache_key(self, text: str) -> str:
        """
        Generate cache key for text.
        
        Args:
            text: Text to generate key for
            
        Returns:
            Cache key string
        """
        # Use SHA-256 hash of text for cache key
        text_hash = hashlib.sha256(text.encode('utf-8')).hexdigest()
        return f"{self.cache_prefix}{text_hash}"
    
    async def _get_from_cache(self, cache_key: str) -> Optional[List[float]]:
        """
        Get embedding from Redis cache.
        
        Args:
            cache_key: Cache key
            
        Returns:
            Cached embedding or None if not found
        """
        if not self.redis_client:
            return None
        
        try:
            cached_data = await self.redis_client.get(cache_key)
            if cached_data:
                embedding = json.loads(cached_data)
                self._cache_hits += 1
                return embedding
            else:
                self._cache_misses += 1
                return None
                
        except Exception as e:
            logger.warning(f"Cache get error for key {cache_key}: {e}")
            self._cache_misses += 1
            return None
    
    async def _set_cache(self, cache_key: str, embedding: List[float]) -> None:
        """
        Set embedding in Redis cache.
        
        Args:
            cache_key: Cache key
            embedding: Embedding to cache
        """
        if not self.redis_client:
            return
        
        try:
            # Convert embedding to JSON string
            embedding_json = json.dumps(embedding)
            
            # Set with TTL
            await self.redis_client.setex(cache_key, self.cache_ttl, embedding_json)
            
        except Exception as e:
            logger.warning(f"Cache set error for key {cache_key}: {e}")
    
    async def generate_embedding(self, text: str) -> List[float]:
        """
        Generate embedding for single text with caching.
        
        Args:
            text: Text to embed
            
        Returns:
            Embedding vector as list of floats
            
        Raises:
            EmbeddingError: If embedding generation fails
        """
        if not text or not text.strip():
            raise EmbeddingError("Cannot embed empty text")
        
        text = text.strip()
        
        # Check in-memory pool first (fastest)
        pooled_embedding = self._get_from_pool(text)
        if pooled_embedding:
            return pooled_embedding
        
        # Check Redis cache
        cache_key = self._generate_cache_key(text)
        cached_embedding = await self._get_from_cache(cache_key)
        if cached_embedding:
            self._cache_hits += 1
            # Add to pool for faster future access
            self._add_to_pool(text, cached_embedding)
            return cached_embedding
        
        # Ensure model is loaded
        await self.load_model()
        
        try:
            start_time = time.time()
            
            # Generate embedding (model is guaranteed to be loaded after await load_model())
            embedding = self.model.encode(  # type: ignore
                text.strip(),
                convert_to_numpy=True,
                normalize_embeddings=True,  # Important for cosine similarity
            )
            
            # Convert to list of floats
            if isinstance(embedding, np.ndarray):
                embedding_list = embedding.tolist()
            else:
                embedding_list = [float(x) for x in embedding]
            
            # Cache in both places
            await self._set_cache(cache_key, embedding_list)
            self._add_to_pool(text, embedding_list)
            
            # Update metrics
            self._cache_misses += 1
            self._total_embeddings += 1
            self._total_time += time.time() - start_time
            
            return embedding_list
            
        except Exception as e:
            logger.error(f"Failed to generate embedding: {e}")
            raise EmbeddingError(f"Embedding generation failed: {e}")
    
    async def generate_batch_embeddings(
        self,
        texts: List[str],
        batch_size: Optional[int] = None,
        show_progress: bool = False,
    ) -> List[List[float]]:
        """
        Generate embeddings for multiple texts with batch processing.
        
        Args:
            texts: List of texts to embed
            batch_size: Batch size for processing (default: 32)
            show_progress: Whether to log progress (default: False)
            
        Returns:
            List of embedding vectors
            
        Raises:
            EmbeddingError: If batch embedding generation fails
        """
        if not texts:
            return []
        
        # Filter out empty texts
        valid_texts = []
        text_indices = []
        
        for i, text in enumerate(texts):
            if text and text.strip():
                valid_texts.append(text.strip())
                text_indices.append(i)
        
        if not valid_texts:
            return [[] for _ in texts]  # Return empty list for each input
        
        # Ensure model is loaded
        await self.load_model()
        
        # Optimize batch size
        optimal_batch_size = self._optimize_batch_size(len(valid_texts))
        batch_size = batch_size or optimal_batch_size
        batch_size = min(batch_size, self.settings.max_batch_size)
        
        try:
            start_time = time.time()
            all_embeddings = [None] * len(texts)  # Pre-allocate result list
            
            # Process in batches
            total_batches = (len(valid_texts) + batch_size - 1) // batch_size
            
            for batch_idx in range(total_batches):
                start_idx = batch_idx * batch_size
                end_idx = min(start_idx + batch_size, len(valid_texts))
                batch_texts = valid_texts[start_idx:end_idx]
                
                # Check cache for batch texts
                batch_embeddings = []
                cache_keys = []
                uncached_texts = []
                uncached_indices = []
                
                for i, text in enumerate(batch_texts):
                    # Check in-memory pool first
                    pooled_embedding = self._get_from_pool(text)
                    if pooled_embedding:
                        batch_embeddings.append(pooled_embedding)
                        cache_keys.append(None)  # No cache key needed
                        continue
                    
                    # Check Redis cache
                    cache_key = self._generate_cache_key(text)
                    cache_keys.append(cache_key)
                    cached_embedding = await self._get_from_cache(cache_key)
                    
                    if cached_embedding:
                        batch_embeddings.append(cached_embedding)
                        self._cache_hits += 1
                        # Add to pool
                        self._add_to_pool(text, cached_embedding)
                    else:
                        batch_embeddings.append(None)
                        uncached_texts.append(text)
                        uncached_indices.append(i)
                        self._cache_misses += 1
                
                # Generate embeddings for uncached texts
                if uncached_texts:
                    try:
                        uncached_embeddings = self.model.encode(  # type: ignore
                            uncached_texts,
                            convert_to_numpy=True,
                            normalize_embeddings=True,
                            batch_size=len(uncached_texts),  # Process all uncached at once
                        )
                        
                        # Convert to list and cache
                        for j, (text, embedding) in enumerate(zip(uncached_texts, uncached_embeddings)):
                            if isinstance(embedding, np.ndarray):
                                embedding_list = embedding.tolist()
                            else:
                                embedding_list = [float(x) for x in embedding]
                            
                            # Cache the result
                            original_idx = uncached_indices[j]
                            batch_embeddings[original_idx] = embedding_list
                            await self._set_cache(cache_keys[original_idx], embedding_list)
                            self._add_to_pool(text, embedding_list)
                            
                    except Exception as e:
                        logger.error(f"Failed to generate batch embeddings: {e}")
                        raise EmbeddingError(f"Batch embedding generation failed: {e}")
                
                # Store batch results
                for i, embedding in enumerate(batch_embeddings):
                    original_text_idx = text_indices[start_idx + i]
                    all_embeddings[original_text_idx] = embedding or []
                
                # Progress logging
                if show_progress and batch_idx % max(1, total_batches // 10) == 0:
                    progress = (batch_idx + 1) / total_batches * 100
                    logger.info(f"Batch embedding progress: {progress:.1f}%")
            
            # Update metrics
            self._total_embeddings += len(valid_texts)
            self._total_time += time.time() - start_time
            
            # Fill remaining empty texts with empty embeddings
            for i, embedding in enumerate(all_embeddings):
                if embedding is None:
                    all_embeddings[i] = []  # type: ignore
            
            return [embedding or [] for embedding in all_embeddings]  # type: ignore
            
        except Exception as e:
            logger.error(f"Failed to generate batch embeddings: {e}")
            raise EmbeddingError(f"Batch embedding generation failed: {e}")
    
    async def get_embedding_info(self) -> Dict[str, Any]:
        """
        Get detailed information about the embedding service.
        
        Returns:
            Dictionary with service information
        """
        total_cache_requests = self._cache_hits + self._cache_misses
        total_pool_requests = self._pool_hits + self._pool_misses
        
        return {
            "model_name": self.model_name,
            "dimension": self.dimension,
            "model_loaded": self.model is not None,
            "cache_enabled": self.redis_client is not None,
            "cache_ttl": self.cache_ttl,
            "total_embeddings": self._total_embeddings,
            "cache_hits": self._cache_hits,
            "cache_misses": self._cache_misses,
            "cache_hit_rate": (
                self._cache_hits / total_cache_requests
                if total_cache_requests > 0 else 0.0
            ),
            "pool_hits": self._pool_hits,
            "pool_misses": self._pool_misses,
            "pool_hit_rate": (
                self._pool_hits / total_pool_requests
                if total_pool_requests > 0 else 0.0
            ),
            "pool_size": len(self._embedding_pool),
            "pool_max_size": self._pool_max_size,
            "average_time": (
                self._total_time / self._total_embeddings
                if self._total_embeddings > 0 else 0.0
            ),
            "smart_batching_enabled": self.settings.enable_smart_batching,
            "embedding_pool_enabled": self.settings.enable_embedding_pool,
        }
    
    async def health_check(self) -> Dict[str, Any]:
        """
        Perform health check on embedding service.
        
        Returns:
            Health check results
        """
        try:
            # Test model loading
            model_status = "loaded" if self.model is not None else "not_loaded"
            
            # Test cache connection
            cache_status = "connected" if self.redis_client else "disconnected"
            if self.redis_client:
                try:
                    await self.redis_client.ping()
                    cache_status = "healthy"
                except Exception:
                    cache_status = "unhealthy"
            
            # Test embedding generation
            test_embedding = None
            try:
                test_embedding = await self.generate_embedding("test")
                generation_status = "working" if test_embedding else "failed"
            except Exception as e:
                generation_status = f"failed: {str(e)}"
            
            return {
                "status": "healthy" if (
                    model_status == "loaded" and 
                    generation_status == "working"
                ) else "degraded",
                "model_status": model_status,
                "cache_status": cache_status,
                "generation_status": generation_status,
                "model_name": self.model_name,
                "dimension": self.dimension,
                "timestamp": time.time(),
            }
            
        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e),
                "timestamp": time.time(),
            }
    
    async def clear_cache(self) -> bool:
        """
        Clear all embeddings from cache.
        
        Returns:
            True if cache cleared successfully
        """
        if not self.redis_client:
            logger.warning("No Redis connection available for cache clearing")
            return False
        
        try:
            # Get all keys with our prefix
            keys = await self.redis_client.keys(f"{self.cache_prefix}*")
            
            if keys:
                # Delete all keys
                await self.redis_client.delete(*keys)
                logger.info(f"Cleared {len(keys)} embeddings from cache")
            
            # Reset metrics
            self._cache_hits = 0
            self._cache_misses = 0
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to clear cache: {e}")
            return False


# Global service instance
_embedding_service: Optional[LocalEmbeddingService] = None


def get_embedding_service() -> LocalEmbeddingService:
    """
    Get cached embedding service instance.
    
    Returns:
        LocalEmbeddingService instance
    """
    global _embedding_service
    if _embedding_service is None:
        _embedding_service = LocalEmbeddingService()
    return _embedding_service


async def init_embedding_service() -> LocalEmbeddingService:
    """
    Initialize embedding service with Redis connection.
    
    Returns:
        Initialized LocalEmbeddingService instance
    """
    service = get_embedding_service()
    async with service:
        # This will initialize Redis connection
        pass
    return service