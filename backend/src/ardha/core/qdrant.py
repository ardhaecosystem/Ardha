"""
Qdrant vector database client implementation.

This module provides a production-ready async client for Qdrant vector database
with collection management, embedding operations, and search capabilities.
"""

import asyncio
import logging
from typing import Any, Dict, List, Optional, Union
from uuid import UUID

from qdrant_client import AsyncQdrantClient, models
from qdrant_client.http.exceptions import UnexpectedResponse
from qdrant_client.http.models import Distance, FieldCondition, Filter, MatchValue, VectorParams
from sentence_transformers import SentenceTransformer

from ..core.config import get_settings

logger = logging.getLogger(__name__)


class QdrantError(Exception):
    """Base exception for Qdrant operations."""

    def __init__(self, message: str, error_type: str = "qdrant_error", code: Optional[str] = None):
        super().__init__(message)
        self.message = message
        self.error_type = error_type
        self.code = code


class CollectionNotFoundError(QdrantError):
    """Raised when collection is not found."""

    pass


class EmbeddingError(QdrantError):
    """Raised when embedding generation fails."""

    pass


class QdrantService:
    """
    Production-ready Qdrant service with collection management and search.

    Handles vector storage, retrieval, and similarity search for AI memory
    and context management. Supports multiple collections for different
    data types (chats, projects, code, etc.).

    Attributes:
        client: Async Qdrant client
        embedding_model: Sentence transformer for embeddings
        settings: Application configuration
    """

    def __init__(self, url: Optional[str] = None, api_key: Optional[str] = None):
        """
        Initialize Qdrant service with connection and embedding model.

        Args:
            url: Qdrant server URL (from config if not provided)
            api_key: Qdrant API key (if required)
        """
        settings = get_settings()

        self.url = url or settings.qdrant.url
        self.collection_prefix = settings.qdrant.collection_prefix

        # Initialize async client
        self.client = AsyncQdrantClient(
            url=self.url,
            timeout=30,
        )

        # Initialize embedding model (all-MiniLM-L6-v2 is fast and effective)
        try:
            self.embedding_model = SentenceTransformer("all-MiniLM-L6-v2")
            self.embedding_dim = self.embedding_model.get_sentence_embedding_dimension()
            logger.info(f"Initialized embedding model with dimension {self.embedding_dim}")
        except Exception as e:
            logger.error(f"Failed to initialize embedding model: {e}")
            raise EmbeddingError(f"Embedding model initialization failed: {e}")

        logger.info(f"Qdrant service initialized with URL: {self.url}")

    async def __aenter__(self) -> "QdrantService":
        """Async context manager entry."""
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Async context manager exit."""
        await self.close()

    async def close(self) -> None:
        """Close the Qdrant client."""
        await self.client.close()

    def _get_collection_name(
        self, collection_type: str, identifier: Optional[Union[str, UUID]] = None
    ) -> str:
        """
        Generate collection name with prefix and identifier.

        Args:
            collection_type: Type of collection (chats, projects, code, etc.)
            identifier: Optional identifier for specific collection

        Returns:
            Full collection name with prefix
        """
        if identifier:
            return f"{self.collection_prefix}_{collection_type}_{identifier}"
        return f"{self.collection_prefix}_{collection_type}"

    async def create_collection(
        self,
        collection_type: str,
        identifier: Optional[Union[str, UUID]] = None,
        vector_size: Optional[int] = None,
        distance: Distance = Distance.COSINE,
    ) -> bool:
        """
        Create a new collection for vector storage.

        Args:
            collection_type: Type of collection (chats, projects, code, etc.)
            identifier: Optional identifier for specific collection
            vector_size: Vector dimension size (uses embedding model size if not provided)
            distance: Distance metric for similarity search

        Returns:
            True if collection created successfully, False if already exists

        Raises:
            QdrantError: If collection creation fails
        """
        collection_name = self._get_collection_name(collection_type, identifier)
        # Ensure vector_size is not None
        if vector_size is None:
            vector_size = self.embedding_dim

        try:
            # Check if collection already exists
            collections = await self.client.get_collections()
            existing_names = [col.name for col in collections.collections]

            if collection_name in existing_names:
                logger.info(f"Collection {collection_name} already exists")
                return False

            # Create collection
            await self.client.create_collection(
                collection_name=collection_name,
                vectors_config=VectorParams(
                    size=vector_size,  # type: ignore  # vector_size is guaranteed to be int after the check above
                    distance=distance,
                ),
                # Enable payload indexing for metadata
                optimizers_config=models.OptimizersConfigDiff(
                    default_segment_number=2,
                    max_segment_size=200000,
                    memmap_threshold=50000,
                ),
                replication_factor=1,
                write_consistency_factor=1,
                on_disk_payload=True,
            )

            logger.info(f"Created collection {collection_name} with vector size {vector_size}")
            return True

        except UnexpectedResponse as e:
            logger.error(f"Failed to create collection {collection_name}: {e}")
            raise QdrantError(f"Collection creation failed: {e}", error_type="creation_error")
        except Exception as e:
            logger.error(f"Unexpected error creating collection {collection_name}: {e}")
            raise QdrantError(f"Unexpected error: {e}", error_type="unexpected_error")

    async def delete_collection(
        self, collection_type: str, identifier: Optional[Union[str, UUID]] = None
    ) -> bool:
        """
        Delete a collection.

        Args:
            collection_type: Type of collection
            identifier: Optional identifier for specific collection

        Returns:
            True if collection deleted successfully, False if didn't exist

        Raises:
            QdrantError: If deletion fails
        """
        collection_name = self._get_collection_name(collection_type, identifier)

        try:
            await self.client.delete_collection(collection_name)
            logger.info(f"Deleted collection {collection_name}")
            return True

        except UnexpectedResponse as e:
            if "not found" in str(e).lower():
                logger.info(f"Collection {collection_name} not found")
                return False
            logger.error(f"Failed to delete collection {collection_name}: {e}")
            raise QdrantError(f"Collection deletion failed: {e}", error_type="deletion_error")
        except Exception as e:
            logger.error(f"Unexpected error deleting collection {collection_name}: {e}")
            raise QdrantError(f"Unexpected error: {e}", error_type="unexpected_error")

    async def collection_exists(
        self, collection_type: str, identifier: Optional[Union[str, UUID]] = None
    ) -> bool:
        """
        Check if a collection exists.

        Args:
            collection_type: Type of collection
            identifier: Optional identifier for specific collection

        Returns:
            True if collection exists, False otherwise
        """
        collection_name = self._get_collection_name(collection_type, identifier)

        try:
            collections = await self.client.get_collections()
            existing_names = [col.name for col in collections.collections]
            return collection_name in existing_names

        except Exception as e:
            logger.error(f"Error checking collection existence {collection_name}: {e}")
            return False

    def _generate_embedding(self, text: str) -> List[float]:
        """
        Generate embedding for text using sentence transformer.

        Args:
            text: Text to embed

        Returns:
            List of embedding values

        Raises:
            EmbeddingError: If embedding generation fails
        """
        try:
            # Clean and prepare text
            if not text or not text.strip():
                raise EmbeddingError("Cannot embed empty text")

            # Generate embedding
            embedding = self.embedding_model.encode(
                text.strip(),
                convert_to_numpy=True,
                normalize_embeddings=True,  # Important for cosine similarity
            )

            # Convert to list of floats
            import numpy as np

            if isinstance(embedding, np.ndarray):
                return embedding.tolist()  # type: ignore
            else:
                # Handle case where embedding is already a list or other iterable
                return [float(x) for x in embedding]  # type: ignore

        except Exception as e:
            logger.error(f"Failed to generate embedding: {e}")
            raise EmbeddingError(f"Embedding generation failed: {e}")

    async def upsert_vectors(
        self,
        collection_type: str,
        points: List[Dict[str, Any]],
        identifier: Optional[Union[str, UUID]] = None,
    ) -> bool:
        """
        Upsert vectors into collection.

        Args:
            collection_type: Type of collection
            points: List of points with id, text, and metadata
            identifier: Optional identifier for specific collection

        Returns:
            True if upsert successful

        Raises:
            QdrantError: If upsert fails
            EmbeddingError: If embedding generation fails
        """
        collection_name = self._get_collection_name(collection_type, identifier)

        # Check collection exists
        if not await self.collection_exists(collection_type, identifier):
            await self.create_collection(collection_type, identifier)

        try:
            # Prepare points with embeddings
            qdrant_points = []
            for point in points:
                # Generate embedding
                embedding = self._generate_embedding(point["text"])

                # Create Qdrant point
                qdrant_point = models.PointStruct(
                    id=point["id"],
                    vector=embedding,
                    payload={
                        "text": point["text"],
                        "metadata": point.get("metadata", {}),
                        "created_at": point.get("created_at"),
                    },
                )
                qdrant_points.append(qdrant_point)

            # Batch upsert
            await self.client.upsert(
                collection_name=collection_name,
                points=qdrant_points,
            )

            logger.info(f"Upserted {len(points)} vectors to {collection_name}")
            return True

        except Exception as e:
            logger.error(f"Failed to upsert vectors to {collection_name}: {e}")
            raise QdrantError(f"Vector upsert failed: {e}", error_type="upsert_error")

    async def search_similar(
        self,
        collection_type: str,
        query_text: str,
        limit: int = 10,
        score_threshold: float = 0.7,
        identifier: Optional[Union[str, UUID]] = None,
        filter_conditions: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Search for similar vectors in collection.

        Args:
            collection_type: Type of collection
            query_text: Text to search for
            limit: Maximum number of results
            score_threshold: Minimum similarity score
            identifier: Optional identifier for specific collection
            filter_conditions: Optional metadata filters

        Returns:
            List of similar points with scores and metadata

        Raises:
            CollectionNotFoundError: If collection doesn't exist
            QdrantError: If search fails
            EmbeddingError: If query embedding fails
        """
        collection_name = self._get_collection_name(collection_type, identifier)

        # Check collection exists
        if not await self.collection_exists(collection_type, identifier):
            raise CollectionNotFoundError(f"Collection {collection_name} not found")

        try:
            # Generate query embedding
            query_embedding = self._generate_embedding(query_text)

            # Build filter if provided
            search_filter = None
            if filter_conditions:
                conditions = []
                for key, value in filter_conditions.items():
                    conditions.append(
                        FieldCondition(
                            key=f"metadata.{key}",
                            match=MatchValue(value=value),
                        )
                    )
                if conditions:
                    search_filter = Filter(must=conditions)  # type: ignore

            # Search
            search_result = await self.client.search(
                collection_name=collection_name,
                query_vector=query_embedding,
                query_filter=search_filter,
                limit=limit,
                score_threshold=score_threshold,
                with_payload=True,
                with_vectors=False,  # Don't return vectors to save bandwidth
            )

            # Format results
            results = []
            for scored_point in search_result:
                payload = scored_point.payload or {}
                results.append(
                    {
                        "id": scored_point.id,
                        "score": scored_point.score,
                        "text": payload.get("text", ""),
                        "metadata": payload.get("metadata", {}),
                        "created_at": payload.get("created_at"),
                    }
                )

            logger.info(f"Found {len(results)} similar vectors in {collection_name}")
            return results

        except Exception as e:
            logger.error(f"Failed to search in {collection_name}: {e}")
            raise QdrantError(f"Vector search failed: {e}", error_type="search_error")

    async def get_collection_info(
        self, collection_type: str, identifier: Optional[Union[str, UUID]] = None
    ) -> Dict[str, Any]:
        """
        Get information about a collection.

        Args:
            collection_type: Type of collection
            identifier: Optional identifier for specific collection

        Returns:
            Collection information

        Raises:
            CollectionNotFoundError: If collection doesn't exist
            QdrantError: If info retrieval fails
        """
        collection_name = self._get_collection_name(collection_type, identifier)

        try:
            info = await self.client.get_collection(collection_name)

            return {
                "name": collection_name,
                "vectors_count": getattr(info, "vectors_count", 0),
                "indexed_vectors_count": getattr(info, "indexed_vectors_count", 0),
                "points_count": getattr(info, "points_count", 0),
                "segments_count": getattr(info, "segments_count", 0),
                "disk_data_size": getattr(info, "disk_data_size", 0),
                "ram_data_size": getattr(info, "ram_data_size", 0),
                "config": {
                    "vector_size": getattr(getattr(info, "config", {}), "params", {})
                    .get("vectors", {})
                    .get("size", 0),
                    "distance": (
                        getattr(getattr(info, "config", {}), "params", {})
                        .get("vectors", {})
                        .get("distance", {})
                        .value
                        if hasattr(
                            getattr(getattr(info, "config", {}), "params", {})
                            .get("vectors", {})
                            .get("distance", {}),
                            "value",
                        )
                        else None
                    ),
                },
            }

        except UnexpectedResponse as e:
            if "not found" in str(e).lower():
                raise CollectionNotFoundError(f"Collection {collection_name} not found")
            raise QdrantError(f"Failed to get collection info: {e}", error_type="info_error")
        except Exception as e:
            raise QdrantError(f"Unexpected error: {e}", error_type="unexpected_error")

    async def delete_points(
        self,
        collection_type: str,
        point_ids: List[Union[str, int, UUID]],
        identifier: Optional[Union[str, UUID]] = None,
    ) -> bool:
        """
        Delete specific points from collection.

        Args:
            collection_type: Type of collection
            point_ids: List of point IDs to delete
            identifier: Optional identifier for specific collection

        Returns:
            True if deletion successful

        Raises:
            CollectionNotFoundError: If collection doesn't exist
            QdrantError: If deletion fails
        """
        collection_name = self._get_collection_name(collection_type, identifier)

        # Check collection exists
        if not await self.collection_exists(collection_type, identifier):
            raise CollectionNotFoundError(f"Collection {collection_name} not found")

        try:
            await self.client.delete(
                collection_name=collection_name,
                points_selector=models.PointIdsList(points=[str(pid) for pid in point_ids]),
            )

            logger.info(f"Deleted {len(point_ids)} points from {collection_name}")
            return True

        except Exception as e:
            logger.error(f"Failed to delete points from {collection_name}: {e}")
            raise QdrantError(f"Point deletion failed: {e}", error_type="deletion_error")

    async def health_check(self) -> Dict[str, Any]:
        """
        Perform health check on Qdrant service.

        Returns:
            Health check results
        """
        try:
            # Try to get collections list
            collections = await self.client.get_collections()

            return {
                "status": "healthy",
                "service_accessible": True,
                "collections_count": len(collections.collections),
                "embedding_model": "all-MiniLM-L6-v2",
                "embedding_dimension": self.embedding_dim,
                "timestamp": asyncio.get_event_loop().time(),
            }

        except Exception as e:
            return {
                "status": "unhealthy",
                "service_accessible": False,
                "error": str(e),
                "timestamp": asyncio.get_event_loop().time(),
            }

    async def get_all_points(
        self,
        collection_type: str,
        identifier: Optional[Union[str, UUID]] = None,
        limit: int = 1000,
    ) -> List[Dict[str, Any]]:
        """
        Get all points from a collection (for cleanup operations).

        Args:
            collection_type: Type of collection
            identifier: Optional identifier for specific collection
            limit: Maximum number of points to return

        Returns:
            List of point dictionaries with IDs and metadata
        """
        collection_name = self._get_collection_name(collection_type, identifier)

        try:
            # Use scroll to get all points
            points = []
            scroll_result = await self.client.scroll(
                collection_name=collection_name,
                scroll_filter=None,
                limit=limit,
                with_payload=True,
                with_vectors=False,
            )

            for point in scroll_result[0]:  # scroll_result returns (points, next_page_offset)
                points.append(
                    {
                        "id": point.id,
                        "payload": point.payload or {},
                    }
                )

            return points

        except Exception as e:
            logger.error(f"Failed to get points from {collection_name}: {e}")
            raise QdrantError(f"Failed to get points: {e}", error_type="get_points_error")

    async def optimize_collection(
        self,
        collection_type: str,
        identifier: Optional[Union[str, UUID]] = None,
    ) -> bool:
        """
        Optimize a collection for better performance.

        Args:
            collection_type: Type of collection
            identifier: Optional identifier for specific collection

        Returns:
            True if optimization successful
        """
        collection_name = self._get_collection_name(collection_type, identifier)

        try:
            # Trigger optimization by updating collection config
            await self.client.update_collection(
                collection_name=collection_name,
                optimizer_config=models.OptimizersConfigDiff(
                    default_segment_number=2,
                    max_segment_size=200000,
                    memmap_threshold=50000,
                    indexing_threshold=20000,
                ),
            )

            logger.info(f"Optimized collection {collection_name}")
            return True

        except Exception as e:
            logger.error(f"Failed to optimize collection {collection_name}: {e}")
            raise QdrantError(
                f"Collection optimization failed: {e}", error_type="optimization_error"
            )


# Global service instance
_qdrant_service: Optional[QdrantService] = None


def get_qdrant_service() -> QdrantService:
    """
    Get cached Qdrant service instance.

    Returns:
        QdrantService instance
    """
    global _qdrant_service
    if _qdrant_service is None:
        _qdrant_service = QdrantService()
    return _qdrant_service


async def init_qdrant_collections() -> None:
    """
    Initialize default Qdrant collections for the application.

    Creates standard collections for chats, projects, and code if they don't exist.
    """
    service = get_qdrant_service()

    # Standard collection types
    collection_types = ["chats", "projects", "code", "documentation"]

    for collection_type in collection_types:
        try:
            if not await service.collection_exists(collection_type):
                await service.create_collection(collection_type)
                logger.info(f"Initialized default collection: {collection_type}")
            else:
                logger.info(f"Collection already exists: {collection_type}")
        except Exception as e:
            logger.error(f"Failed to initialize collection {collection_type}: {e}")
