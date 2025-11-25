"""
Semantic search service for Qdrant operations.

This module provides a helper service for Qdrant vector database operations
including semantic search, hybrid search, and filtering capabilities.

Cost: $0.00 (uses local embeddings)
Features: Vector search, hybrid search, filtering, ranking
"""

import logging
from typing import Any, Dict, List, Optional
from uuid import UUID

from ..core.qdrant import QdrantService, get_qdrant_service
from ..services.embedding_service import LocalEmbeddingService, get_embedding_service

# Type alias for search results
SearchResult = Dict[str, Any]

logger = logging.getLogger(__name__)


class SemanticSearchError(Exception):
    """Base exception for semantic search operations."""

    def __init__(self, message: str, error_type: str = "semantic_search_error"):
        super().__init__(message)
        self.message = message
        self.error_type = error_type


class SemanticSearchService:
    """
    Helper service for Qdrant vector search operations.

    Provides semantic search, hybrid search, and advanced filtering
    capabilities for memory and context retrieval.

    Attributes:
        qdrant_service: Qdrant vector database service
        embedding_service: Local embedding service
    """

    def __init__(
        self,
        qdrant_service: Optional[QdrantService] = None,
        embedding_service: Optional[LocalEmbeddingService] = None,
    ):
        """
        Initialize semantic search service.

        Args:
            qdrant_service: Qdrant service (injected if not provided)
            embedding_service: Local embedding service (injected if not provided)
        """
        self.qdrant_service = qdrant_service or get_qdrant_service()
        self.embedding_service = embedding_service or get_embedding_service()

        logger.info("SemanticSearchService initialized")

    async def search_similar(
        self,
        collection: str,
        query_vector: List[float],
        limit: int = 10,
        filter_conditions: Optional[Dict[str, Any]] = None,
        score_threshold: float = 0.5,
    ) -> List[SearchResult]:
        """
        Search with optional filtering.

        Args:
            collection: Collection name to search
            query_vector: Query embedding vector
            limit: Maximum number of results
            filter_conditions: Optional metadata filters
            score_threshold: Minimum similarity score

        Returns:
            List of scored points

        Raises:
            SemanticSearchError: If search fails
        """
        try:
            # Check if collection exists
            if not await self.qdrant_service.collection_exists(collection):
                logger.warning(f"Collection {collection} does not exist")
                return []

            # Perform search
            results = await self.qdrant_service.search_similar(
                collection_type=collection,
                query_text="",  # Not used when we have vector
                limit=limit,
                score_threshold=score_threshold,
                filter_conditions=filter_conditions,
            )

            logger.info(f"Found {len(results)} similar vectors in {collection}")
            return results  # QdrantService returns List[Dict], not ScoredPoint

        except Exception as e:
            logger.error(f"Similar search failed in {collection}: {e}")
            raise SemanticSearchError(f"Similar search failed: {e}")

    async def hybrid_search(
        self,
        collection: str,
        query_text: str,
        keywords: List[str],
        limit: int = 10,
        score_threshold: float = 0.5,
    ) -> List[SearchResult]:
        """
        Combine vector search with keyword filtering.

        Args:
            collection: Collection name to search
            query_text: Query text for embedding generation
            keywords: List of keywords to filter by
            limit: Maximum number of results
            score_threshold: Minimum similarity score

        Returns:
            List of scored points filtered by keywords

        Raises:
            SemanticSearchError: If hybrid search fails
        """
        try:
            # Generate query embedding
            query_embedding = await self.embedding_service.generate_embedding(query_text)

            # Perform vector search
            vector_results = await self.search_similar(
                collection=collection,
                query_vector=query_embedding,
                limit=limit * 2,  # Get more for filtering
                score_threshold=score_threshold,
            )

            # Filter by keywords in payload
            filtered_results = []
            for result in vector_results:
                content = result.get("text", "").lower()

                # Check if any keyword matches
                keyword_match = any(keyword.lower() in content for keyword in keywords)

                if keyword_match:
                    filtered_results.append(result)

            # Sort by score and limit results
            filtered_results.sort(key=lambda x: x.score, reverse=True)

            logger.info(f"Hybrid search found {len(filtered_results)} results in {collection}")
            return filtered_results[:limit]

        except Exception as e:
            logger.error(f"Hybrid search failed in {collection}: {e}")
            raise SemanticSearchError(f"Hybrid search failed: {e}")

    async def search_by_metadata(
        self,
        collection: str,
        query_text: str,
        metadata_filters: Dict[str, Any],
        limit: int = 10,
        score_threshold: float = 0.5,
    ) -> List[SearchResult]:
        """
        Search with metadata filtering.

        Args:
            collection: Collection name to search
            query_text: Query text for embedding generation
            metadata_filters: Dictionary of metadata filters
            limit: Maximum number of results
            score_threshold: Minimum similarity score

        Returns:
            List of scored points filtered by metadata

        Raises:
            SemanticSearchError: If metadata search fails
        """
        try:
            # Generate query embedding
            query_embedding = await self.embedding_service.generate_embedding(query_text)

            # Perform search with metadata filters
            results = await self.search_similar(
                collection=collection,
                query_vector=query_embedding,
                limit=limit,
                filter_conditions=metadata_filters,
                score_threshold=score_threshold,
            )

            logger.info(f"Metadata search found {len(results)} results in {collection}")
            return results

        except Exception as e:
            logger.error(f"Metadata search failed in {collection}: {e}")
            raise SemanticSearchError(f"Metadata search failed: {e}")

    async def multi_collection_search(
        self,
        collections: List[str],
        query_text: str,
        limit_per_collection: int = 5,
        total_limit: int = 20,
        score_threshold: float = 0.5,
    ) -> Dict[str, List[SearchResult]]:
        """
        Search across multiple collections.

        Args:
            collections: List of collection names to search
            query_text: Query text for embedding generation
            limit_per_collection: Maximum results per collection
            total_limit: Maximum total results across all collections
            score_threshold: Minimum similarity score

        Returns:
            Dictionary mapping collection names to results

        Raises:
            SemanticSearchError: If multi-collection search fails
        """
        try:
            # Generate query embedding once
            query_embedding = await self.embedding_service.generate_embedding(query_text)

            # Search each collection
            all_results = {}
            total_results = 0

            for collection in collections:
                try:
                    # Calculate remaining limit
                    remaining_limit = min(limit_per_collection, total_limit - total_results)

                    if remaining_limit <= 0:
                        break

                    # Search collection
                    results = await self.search_similar(
                        collection=collection,
                        query_vector=query_embedding,
                        limit=remaining_limit,
                        score_threshold=score_threshold,
                    )

                    all_results[collection] = results
                    total_results += len(results)

                except Exception as e:
                    logger.warning(f"Search failed for collection {collection}: {e}")
                    all_results[collection] = []
                    continue

            logger.info(f"Multi-collection search found {total_results} total results")
            return all_results

        except Exception as e:
            logger.error(f"Multi-collection search failed: {e}")
            raise SemanticSearchError(f"Multi-collection search failed: {e}")

    async def find_similar_memories(
        self,
        memory_id: UUID,
        collection: str,
        limit: int = 10,
        score_threshold: float = 0.7,
    ) -> List[SearchResult]:
        """
        Find memories similar to a specific memory.

        Args:
            memory_id: UUID of memory to find similar ones for
            collection: Collection name to search
            limit: Maximum number of results
            score_threshold: Minimum similarity score

        Returns:
            List of similar memories

        Raises:
            SemanticSearchError: If similarity search fails
        """
        try:
            # Get the original memory vector
            # This would require getting the vector from Qdrant first
            # For now, we'll use a placeholder implementation

            # In a real implementation, you would:
            # 1. Get the memory's vector from Qdrant using its point ID
            # 2. Use that vector to search for similar vectors

            logger.warning("find_similar_memories needs implementation with Qdrant point retrieval")
            return []

        except Exception as e:
            logger.error(f"Similar memories search failed: {e}")
            raise SemanticSearchError(f"Similar memories search failed: {e}")

    async def rank_results_by_importance(
        self,
        results: List[SearchResult],
        importance_weights: Optional[Dict[str, float]] = None,
    ) -> List[SearchResult]:
        """
        Re-rank search results by importance factors.

        Args:
            results: List of search results to rank
            importance_weights: Optional weights for different factors

        Returns:
            Re-ranked list of results
        """
        try:
            # Default importance weights
            default_weights = {
                "similarity_score": 0.7,
                "recency": 0.2,
                "access_count": 0.1,
            }

            weights = importance_weights or default_weights

            # Calculate composite scores
            scored_results = []
            for result in results:
                composite_score = 0.0

                # Similarity score (already available)
                composite_score += result.get("score", 0) * weights["similarity_score"]

                # Recency bonus (more recent = higher score)
                created_at = result.get("metadata", {}).get("created_at")
                if created_at:
                    try:
                        from datetime import datetime

                        creation_time = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
                        days_old = (datetime.utcnow() - creation_time).days
                        recency_bonus = max(0, 1 - days_old / 365)  # Decay over year
                        composite_score += recency_bonus * weights["recency"]
                    except Exception:
                        pass

                # Access count bonus (if available)
                access_count = result.get("metadata", {}).get("access_count", 0)
                access_bonus = min(1.0, access_count / 10)  # Cap at 10 accesses
                composite_score += access_bonus * weights["access_count"]

                # Store composite score
                result["composite_score"] = composite_score
                scored_results.append(result)

            # Sort by composite score
            scored_results.sort(key=lambda x: x.get("composite_score", 0), reverse=True)

            logger.info(f"Ranked {len(scored_results)} results by importance")
            return scored_results

        except Exception as e:
            logger.error(f"Result ranking failed: {e}")
            # Return original results if ranking fails
            return results

    async def get_search_statistics(
        self,
        collection: str,
    ) -> Dict[str, Any]:
        """
        Get search statistics for a collection.

        Args:
            collection: Collection name

        Returns:
            Dictionary with search statistics
        """
        try:
            # Get collection info
            collection_info = await self.qdrant_service.get_collection_info(collection)

            # Get embedding service info
            embedding_info = await self.embedding_service.get_embedding_info()

            return {
                "collection": {
                    "name": collection,
                    "vectors_count": collection_info.get("vectors_count", 0),
                    "points_count": collection_info.get("points_count", 0),
                    "disk_data_size": collection_info.get("disk_data_size", 0),
                },
                "embedding": {
                    "model_name": embedding_info.get("model_name"),
                    "dimension": embedding_info.get("dimension"),
                    "cache_hit_rate": embedding_info.get("cache_hit_rate", 0),
                },
                "search_capabilities": {
                    "semantic_search": True,
                    "hybrid_search": True,
                    "metadata_filtering": True,
                    "multi_collection_search": True,
                },
            }

        except Exception as e:
            logger.error(f"Failed to get search statistics for {collection}: {e}")
            return {
                "collection": {"name": collection, "error": str(e)},
                "embedding": {"error": str(e)},
                "search_capabilities": {"error": str(e)},
            }
