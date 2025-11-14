"""
Memory service with local semantic search capabilities.

This module provides a production-ready memory service using local embeddings
and Qdrant vector database for semantic search, context management, and
knowledge graph operations.

Cost: $0.00 (completely free local embeddings!)
Features: Semantic search, context assembly, importance scoring, memory ingestion
"""

import asyncio
import hashlib
import json
import logging
import time
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple, Union
from uuid import UUID, uuid4

from qdrant_client.http.models import Distance, VectorParams

from ..core.config import get_settings
from ..core.qdrant import QdrantService, get_qdrant_service
from ..models.memory import Memory, MemoryType, SourceType
from ..repositories.memory_repository import MemoryRepository
from ..services.chat_service import ChatService
from ..services.embedding_service import LocalEmbeddingService, get_embedding_service

logger = logging.getLogger(__name__)


class MemoryServiceError(Exception):
    """Base exception for memory service operations."""

    def __init__(self, message: str, error_type: str = "memory_service_error"):
        super().__init__(message)
        self.message = message
        self.error_type = error_type


class MemoryCreationError(MemoryServiceError):
    """Raised when memory creation fails."""

    pass


class SemanticSearchError(MemoryServiceError):
    """Raised when semantic search fails."""

    pass


class ContextAssemblyError(MemoryServiceError):
    """Raised when context assembly fails."""

    pass


class MemoryIngestionError(MemoryServiceError):
    """Raised when memory ingestion fails."""

    pass


class MemoryService:
    """
    Production-ready memory service with local semantic search.

    Provides memory creation, semantic search, context assembly, and
    automated ingestion capabilities using local embeddings (FREE!)
    and Qdrant vector database.

    Attributes:
        memory_repository: Repository for database operations
        embedding_service: Local embedding service (all-MiniLM-L6-v2)
        qdrant_service: Qdrant vector database service
        chat_service: Chat service for context extraction
    """

    def __init__(
        self,
        memory_repository: MemoryRepository,
        embedding_service: Optional[LocalEmbeddingService] = None,
        qdrant_service: Optional[QdrantService] = None,
        chat_service: Optional[ChatService] = None,
    ):
        """
        Initialize memory service with dependencies.

        Args:
            memory_repository: Repository for database operations
            embedding_service: Local embedding service (injected if not provided)
            qdrant_service: Qdrant service (injected if not provided)
            chat_service: Chat service (injected if not provided)
        """
        self.memory_repository = memory_repository
        self.embedding_service = embedding_service or get_embedding_service()
        self.qdrant_service = qdrant_service or get_qdrant_service()
        self.chat_service = chat_service

        # Collection mapping for different memory types
        self.collection_mapping = {
            MemoryType.CONVERSATION: "chat_memories",
            MemoryType.WORKFLOW: "workflow_memories",
            MemoryType.DOCUMENT: "document_memories",
            MemoryType.ENTITY: "entity_memories",
            MemoryType.FACT: "fact_memories",
        }

        # Default collection for unknown types
        self.default_collection = "general_memories"

        logger.info("MemoryService initialized with local embeddings")

    def _get_collection_name(self, memory_type: str) -> str:
        """
        Map memory type to Qdrant collection name.

        Args:
            memory_type: Type of memory

        Returns:
            Collection name for the memory type
        """
        return self.collection_mapping.get(memory_type, self.default_collection)

    def _get_search_collections(self, memory_type: Optional[str] = None) -> List[str]:
        """
        Get list of collections to search based on memory type filter.

        Args:
            memory_type: Optional memory type filter

        Returns:
            List of collection names to search
        """
        if memory_type:
            collection = self._get_collection_name(memory_type)
            return [collection]

        # Return all collections for comprehensive search
        return list(set(self.collection_mapping.values()) | {self.default_collection})

    def _generate_summary(self, content: str, max_length: int = 200) -> str:
        """
        Generate summary for memory content.

        Args:
            content: Full content to summarize
            max_length: Maximum summary length

        Returns:
            Summary string
        """
        if not content:
            return ""

        # Simple truncation for now - can be enhanced with AI summarization
        content = content.strip()
        if len(content) <= max_length:
            return content

        # Truncate at word boundary
        truncated = content[:max_length].rsplit(" ", 1)[0]
        return truncated + "..."

    def _extract_topics(self, messages: List[Dict[str, Any]]) -> List[str]:
        """
        Extract key topics from chat messages.

        Args:
            messages: List of chat messages

        Returns:
            List of topic strings
        """
        topics = []

        # Simple topic extraction based on message content
        # In production, this could use NLP techniques
        for message in messages:
            content = message.get("content", "").lower()

            # Extract potential keywords/phrases
            words = content.split()
            for word in words:
                # Filter out common words and short words
                if len(word) > 4 and word not in [
                    "that",
                    "this",
                    "with",
                    "from",
                    "they",
                    "have",
                    "been",
                ]:
                    if word not in topics:
                        topics.append(word)

            # Limit number of topics
            if len(topics) >= 10:
                break

        return topics[:5]  # Return top 5 topics

    def _deduplicate_memories(
        self, memories_with_scores: List[Tuple[Memory, float]]
    ) -> List[Tuple[Memory, float]]:
        """
        Deduplicate memories by ID.

        Args:
            memories_with_scores: List of (memory, score) tuples

        Returns:
            Deduplicated list
        """
        seen_ids = set()
        deduplicated = []

        for memory, score in memories_with_scores:
            if memory.id not in seen_ids:
                seen_ids.add(memory.id)
                deduplicated.append((memory, score))

        return deduplicated

    def _build_context_string(
        self,
        recent_messages: List[Dict[str, Any]],
        memories: List[Tuple[Memory, float]],
        max_tokens: int = 2000,
    ) -> str:
        """
        Build context string from messages and memories.

        Args:
            recent_messages: List of recent chat messages
            memories: List of relevant memories with scores
            max_tokens: Maximum token budget

        Returns:
            Formatted context string
        """
        context_parts = []

        # Add recent messages (short-term context)
        if recent_messages:
            context_parts.append("## Recent Messages")
            for message in recent_messages[-5:]:  # Last 5 messages
                role = message.get("role", "unknown")
                content = message.get("content", "")[:200]  # Truncate long messages
                context_parts.append(f"{role.title()}: {content}")

        # Add relevant memories (long-term context)
        if memories:
            context_parts.append("\n## Relevant Memories")
            for memory, score in memories[:10]:  # Top 10 memories
                context_parts.append(
                    f"[{memory.memory_type.title()}] {memory.summary} "
                    f"(importance: {memory.importance}, relevance: {score:.2f})"
                )

        # Join and truncate to token budget
        full_context = "\n".join(context_parts)

        # Simple token estimation (4 chars ≈ 1 token)
        estimated_tokens = len(full_context) // 4
        if estimated_tokens > max_tokens:
            # Truncate proportionally
            ratio = max_tokens / estimated_tokens
            max_chars = int(len(full_context) * ratio * 0.9)  # 90% to be safe
            truncated = full_context[:max_chars].rsplit("\n", 1)[0]
            return truncated + "\n... (context truncated)"

        return full_context

    def calculate_importance(
        self,
        content: str,
        source_type: str,
        access_count: int = 0,
        has_user_approval: bool = False,
    ) -> int:
        """
        Calculate memory importance score (1-10).

        Args:
            content: Memory content
            source_type: Source type (manual, workflow, chat, api)
            access_count: Number of times accessed
            has_user_approval: Whether user explicitly approved

        Returns:
            Importance score (1-10)
        """
        score = 5  # Base score

        # Source type boost
        if source_type == SourceType.MANUAL:
            score += 3  # User explicitly saved this
        elif source_type == SourceType.WORKFLOW:
            score += 2  # Workflow output is important
        elif source_type == SourceType.CHAT:
            score += 1  # Chat might be important

        # Content length (longer = more detailed)
        if len(content) > 1000:
            score += 1
        elif len(content) > 500:
            score += 0.5

        # Access patterns
        if access_count > 10:
            score += 2
        elif access_count > 5:
            score += 1
        elif access_count > 2:
            score += 0.5

        # User approval
        if has_user_approval:
            score += 2

        # Cap at 10
        return min(int(score), 10)

    async def initialize_collections(self) -> None:
        """
        Create Qdrant collections if they don't exist.

        Raises:
            MemoryServiceError: If collection initialization fails
        """
        try:
            collections = list(set(self.collection_mapping.values()) | {self.default_collection})

            for collection in collections:
                if not await self.qdrant_service.collection_exists(collection):
                    await self.qdrant_service.create_collection(
                        collection_type=collection,
                        vector_size=384,  # all-MiniLM-L6-v2 dimension
                        distance=Distance.COSINE,
                    )
                    logger.info(f"Created collection: {collection}")
                else:
                    logger.info(f"Collection already exists: {collection}")

            logger.info("All memory collections initialized")

        except Exception as e:
            logger.error(f"Failed to initialize collections: {e}")
            raise MemoryServiceError(f"Collection initialization failed: {e}")

    async def create_memory(
        self,
        user_id: UUID,
        content: str,
        memory_type: str,
        project_id: Optional[UUID] = None,
        source_type: str = "manual",
        source_id: Optional[UUID] = None,
        importance: int = 5,
        tags: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Memory:
        """
        Create memory with local embedding generation.

        Args:
            user_id: UUID of user creating the memory
            content: Full text content of the memory
            memory_type: Type of memory (conversation, workflow, document, entity, fact)
            project_id: Optional UUID of associated project
            source_type: Source type (chat, workflow, manual, api)
            source_id: Optional UUID of source record
            importance: Importance score (1-10)
            tags: Optional list of tags
            metadata: Optional metadata dictionary

        Returns:
            Created Memory object

        Raises:
            MemoryCreationError: If memory creation fails
        """
        try:
            # Validate inputs
            if not content or not content.strip():
                raise MemoryCreationError("Content cannot be empty")

            if memory_type not in self.collection_mapping and memory_type not in [
                self.default_collection
            ]:
                logger.warning(f"Unknown memory type: {memory_type}, using default collection")

            # Generate local embedding (zero cost!)
            embedding = await self.embedding_service.generate_embedding(content)

            # Determine Qdrant collection
            collection = self._get_collection_name(memory_type)

            # Store in Qdrant
            point_id = str(uuid4())
            await self.qdrant_service.upsert_vectors(
                collection_type=collection,
                points=[
                    {
                        "id": point_id,
                        "text": content[:500],  # Store truncated for search
                        "metadata": {
                            "user_id": str(user_id),
                            "project_id": str(project_id) if project_id else None,
                            "memory_type": memory_type,
                            "source_type": source_type,
                            "created_at": datetime.utcnow().isoformat(),
                            **(metadata or {}),
                        },
                    }
                ],
            )

            # Calculate importance if not provided
            if importance <= 0:
                importance = self.calculate_importance(content, source_type)

            # Store in PostgreSQL
            memory = await self.memory_repository.create(
                user_id=user_id,
                content=content,
                summary=self._generate_summary(content),
                qdrant_collection=collection,
                qdrant_point_id=point_id,
                memory_type=memory_type,
                source_type=source_type,
                project_id=project_id,
                source_id=source_id,
                importance=importance,
                tags={"tags": tags} if tags else None,
                extra_metadata=metadata,
            )

            logger.info(f"Created memory {memory.id} in collection {collection}")
            return memory

        except Exception as e:
            logger.error(f"Failed to create memory: {e}")
            raise MemoryCreationError(f"Memory creation failed: {e}")

    async def search_semantic(
        self,
        user_id: UUID,
        query: str,
        limit: int = 10,
        project_id: Optional[UUID] = None,
        memory_type: Optional[str] = None,
        min_score: float = 0.5,
    ) -> List[Tuple[Memory, float]]:
        """
        Semantic search using local embeddings.

        Args:
            user_id: UUID of user searching
            query: Search query text
            limit: Maximum number of results
            project_id: Optional project filter
            memory_type: Optional memory type filter
            min_score: Minimum similarity score

        Returns:
            List of (Memory, similarity_score) tuples

        Raises:
            SemanticSearchError: If search fails
        """
        try:
            # Generate query embedding locally (FREE!)
            await self.embedding_service.generate_embedding(query)

            # Determine collection(s) to search
            collections = self._get_search_collections(memory_type)

            # Search Qdrant
            all_results = []
            for collection in collections:
                try:
                    # Build filter conditions
                    filter_conditions = {"user_id": str(user_id)}

                    if project_id:
                        filter_conditions["project_id"] = str(project_id)

                    results = await self.qdrant_service.search_similar(
                        collection_type=collection,
                        query_text=query,
                        limit=limit * 2,  # Get more for filtering
                        score_threshold=min_score,
                        filter_conditions=filter_conditions,
                    )

                    all_results.extend(results)

                except Exception as e:
                    logger.warning(f"Search failed for collection {collection}: {e}")
                    continue

            # Sort by score and get top N
            all_results.sort(key=lambda x: x.get("score", 0), reverse=True)
            top_results = all_results[:limit]

            # Load Memory objects from PostgreSQL
            memories_with_scores = []
            for result in top_results:
                try:
                    # Find memory by Qdrant point ID
                    memories = await self.memory_repository.get_by_source(
                        source_type="qdrant",
                        source_id=(
                            UUID(result["id"])
                            if result["id"]
                            else UUID("00000000-0000-0000-0000-000000000000")
                        ),
                    )

                    if memories:
                        memory = memories[0]  # Take first match
                        # Increment access count
                        await self.memory_repository.increment_access_count(memory.id)
                        memories_with_scores.append((memory, result["score"]))

                except Exception as e:
                    logger.warning(f"Failed to load memory for result {result.get('id')}: {e}")
                    continue

            logger.info(
                f"Semantic search found {len(memories_with_scores)} results for user {user_id}"
            )
            return memories_with_scores

        except Exception as e:
            logger.error(f"Semantic search failed: {e}")
            raise SemanticSearchError(f"Semantic search failed: {e}")

    async def get_context_for_chat(
        self,
        chat_id: UUID,
        user_id: UUID,
        max_tokens: int = 2000,
        relevance_threshold: float = 0.6,
    ) -> str:
        """
        Assemble relevant context for chat continuation.

        Args:
            chat_id: UUID of chat
            user_id: UUID of user
            max_tokens: Maximum token budget
            relevance_threshold: Minimum relevance score

        Returns:
            Formatted context string

        Raises:
            ContextAssemblyError: If context assembly fails
        """
        try:
            # Get recent chat messages
            recent_messages = []
            if self.chat_service:
                try:
                    # Get chat history (last 10 messages)
                    message_history = await self.chat_service.get_chat_history(
                        chat_id=chat_id, user_id=user_id, skip=0, limit=10
                    )
                    # Convert to expected format
                    recent_messages = [
                        {
                            "role": msg.role.value,
                            "content": msg.content,
                            "created_at": msg.created_at.isoformat(),
                            "id": str(msg.id),
                        }
                        for msg in message_history
                    ]
                except Exception as e:
                    logger.warning(f"Failed to get chat history for {chat_id}: {e}")

            # Extract key topics from recent messages
            topics = self._extract_topics(recent_messages)

            # Search for relevant memories
            relevant_memories = []
            for topic in topics[:3]:  # Search top 3 topics
                try:
                    results = await self.search_semantic(
                        user_id=user_id, query=topic, limit=3, min_score=relevance_threshold
                    )
                    relevant_memories.extend(results)
                except Exception as e:
                    logger.warning(f"Topic search failed for '{topic}': {e}")
                    continue

            # Deduplicate and sort by importance and relevance
            unique_memories = self._deduplicate_memories(relevant_memories)
            unique_memories.sort(key=lambda x: (x[0].importance, x[1]), reverse=True)

            # Build context string within token budget
            context = self._build_context_string(
                recent_messages=recent_messages, memories=unique_memories, max_tokens=max_tokens
            )

            logger.info(
                f"Assembled context for chat {chat_id} with {len(unique_memories)} memories"
            )
            return context

        except Exception as e:
            logger.error(f"Context assembly failed: {e}")
            raise ContextAssemblyError(f"Context assembly failed: {e}")

    async def ingest_from_chat(
        self,
        chat_id: UUID,
        user_id: UUID,
        min_importance: int = 6,
    ) -> List[Memory]:
        """
        Extract important information from chat and create memories.

        Args:
            chat_id: UUID of chat to ingest
            user_id: UUID of chat owner
            min_importance: Minimum importance score for memory creation

        Returns:
            List of created memories

        Raises:
            MemoryIngestionError: If ingestion fails
        """
        try:
            # Get chat messages
            messages = []
            if self.chat_service:
                try:
                    # Get all chat messages
                    message_history = await self.chat_service.get_chat_history(
                        chat_id=chat_id,
                        user_id=user_id,
                        skip=0,
                        limit=1000,  # Get many messages for ingestion
                    )
                    # Convert to expected format
                    messages = [
                        {
                            "role": msg.role.value,
                            "content": msg.content,
                            "created_at": msg.created_at.isoformat(),
                            "id": str(msg.id),
                        }
                        for msg in message_history
                    ]
                except Exception as e:
                    logger.warning(f"Failed to get chat messages for {chat_id}: {e}")

            if not messages:
                logger.warning(f"No messages found for chat {chat_id}")
                return []

            # Extract important segments using AI
            important_segments = await self._extract_important_segments(messages, min_importance)

            # Create memories
            created_memories = []
            for segment in important_segments:
                try:
                    memory = await self.create_memory(
                        user_id=user_id,
                        content=segment["content"],
                        memory_type="conversation",
                        source_type="chat",
                        source_id=chat_id,
                        importance=segment["importance"],
                        tags=segment.get("tags"),
                        metadata={
                            "chat_id": str(chat_id),
                            "message_ids": segment.get("message_ids", []),
                        },
                    )
                    created_memories.append(memory)

                except Exception as e:
                    logger.warning(f"Failed to create memory for segment: {e}")
                    continue

            # Create relationships between related memories
            if len(created_memories) > 1:
                await self._link_related_memories(created_memories)

            logger.info(f"Ingested {len(created_memories)} memories from chat {chat_id}")
            return created_memories

        except Exception as e:
            logger.error(f"Memory ingestion failed: {e}")
            raise MemoryIngestionError(f"Memory ingestion failed: {e}")

    async def _extract_important_segments(
        self,
        messages: List[Dict[str, Any]],
        min_importance: int = 6,
    ) -> List[Dict[str, Any]]:
        """
        Extract important segments from chat messages using AI.

        Args:
            messages: List of chat messages
            min_importance: Minimum importance score

        Returns:
            List of important segments with metadata
        """
        # This is a simplified implementation
        # In production, this would use AI to identify important content

        important_segments = []

        # Group messages by topic/time
        message_groups = self._group_messages(messages)

        for group in message_groups:
            # Calculate importance based on various factors
            importance = self._calculate_segment_importance(group)

            if importance >= min_importance:
                segment = {
                    "content": self._concatenate_messages(group),
                    "importance": importance,
                    "message_ids": [msg.get("id") for msg in group],
                    "tags": self._extract_segment_tags(group),
                }
                important_segments.append(segment)

        return important_segments

    def _group_messages(self, messages: List[Dict[str, Any]]) -> List[List[Dict[str, Any]]]:
        """
        Group related messages together.

        Args:
            messages: List of messages

        Returns:
            List of message groups
        """
        # Simple grouping by time and topic
        # In production, this would use more sophisticated clustering

        groups = []
        current_group = []

        for i, message in enumerate(messages):
            if not current_group:
                current_group.append(message)
            else:
                # Check if this message is related to the current group
                last_message = current_group[-1]
                time_diff = self._get_time_difference(message, last_message)

                if time_diff < timedelta(minutes=5):  # Within 5 minutes
                    current_group.append(message)
                else:
                    # Start new group
                    if current_group:
                        groups.append(current_group)
                    current_group = [message]

        # Add final group
        if current_group:
            groups.append(current_group)

        return groups

    def _calculate_segment_importance(self, messages: List[Dict[str, Any]]) -> int:
        """
        Calculate importance score for a message segment.

        Args:
            messages: List of messages in the segment

        Returns:
            Importance score (1-10)
        """
        score = 5  # Base score

        # Length factor
        total_content = " ".join([msg.get("content", "") for msg in messages])
        if len(total_content) > 500:
            score += 1
        elif len(total_content) > 1000:
            score += 2

        # User messages are more important
        user_messages = [msg for msg in messages if msg.get("role") == "user"]
        if len(user_messages) > len(messages) / 2:
            score += 1

        # Question/answer patterns
        has_question = any("?" in msg.get("content", "") for msg in messages)
        if has_question:
            score += 1

        # Decision words
        decision_words = ["decide", "choose", "will", "should", "going to", "plan"]
        content_lower = total_content.lower()
        if any(word in content_lower for word in decision_words):
            score += 2

        return min(score, 10)

    def _concatenate_messages(self, messages: List[Dict[str, Any]]) -> str:
        """
        Concatenate messages into a single string.

        Args:
            messages: List of messages

        Returns:
            Concatenated content
        """
        parts = []
        for message in messages:
            role = message.get("role", "unknown")
            content = message.get("content", "")
            parts.append(f"[{role}]: {content}")

        return " ".join(parts)

    def _extract_segment_tags(self, messages: List[Dict[str, Any]]) -> List[str]:
        """
        Extract tags from message segment.

        Args:
            messages: List of messages

        Returns:
            List of tags
        """
        tags = []
        content = " ".join([msg.get("content", "") for msg in messages]).lower()

        # Simple tag extraction based on keywords
        tag_keywords = {
            "decision": ["decide", "choose", "will", "should"],
            "question": ["?", "how", "what", "why", "when"],
            "technical": ["code", "function", "api", "database"],
            "planning": ["plan", "schedule", "timeline", "deadline"],
        }

        for tag, keywords in tag_keywords.items():
            if any(keyword in content for keyword in keywords):
                tags.append(tag)

        return tags[:5]  # Limit to 5 tags

    def _get_time_difference(self, msg1: Dict[str, Any], msg2: Dict[str, Any]) -> timedelta:
        """
        Get time difference between two messages.

        Args:
            msg1: First message
            msg2: Second message

        Returns:
            Time difference
        """
        time1 = msg1.get("created_at")
        time2 = msg2.get("created_at")

        if time1 and time2:
            try:
                dt1 = datetime.fromisoformat(time1.replace("Z", "+00:00"))
                dt2 = datetime.fromisoformat(time2.replace("Z", "+00:00"))
                return abs(dt1 - dt2)
            except Exception:
                pass

        return timedelta(0)

    async def _link_related_memories(self, memories: List[Memory]) -> None:
        """
        Create relationships between related memories.

        Args:
            memories: List of memories to link
        """
        # Simple linking based on similarity and time
        # In production, this would use more sophisticated relationship detection

        for i, memory1 in enumerate(memories):
            for memory2 in memories[i + 1 :]:
                try:
                    # Calculate similarity based on content
                    similarity = await self._calculate_memory_similarity(memory1, memory2)

                    if similarity > 0.7:  # High similarity threshold
                        await self.memory_repository.create_link(
                            from_id=memory1.id,
                            to_id=memory2.id,
                            relationship_type="related_to",
                            strength=similarity,
                        )

                except Exception as e:
                    logger.warning(f"Failed to link memories {memory1.id} and {memory2.id}: {e}")
                    continue

    async def _calculate_memory_similarity(self, memory1: Memory, memory2: Memory) -> float:
        """
        Calculate similarity between two memories.

        Args:
            memory1: First memory
            memory2: Second memory

        Returns:
            Similarity score (0.0-1.0)
        """
        # Simple similarity calculation based on content overlap
        # In production, this would use embedding similarity

        content1 = memory1.content.lower()
        content2 = memory2.content.lower()

        # Calculate word overlap
        words1 = set(content1.split())
        words2 = set(content2.split())

        if not words1 or not words2:
            return 0.0

        intersection = words1.intersection(words2)
        union = words1.union(words2)

        return len(intersection) / len(union)

    async def get_memory_stats(self, user_id: UUID) -> Dict[str, Any]:
        """
        Get memory statistics for a user.

        Args:
            user_id: UUID of user

        Returns:
            Dictionary with memory statistics
        """
        try:
            # Get total memories
            total_memories = len(await self.memory_repository.get_by_user(user_id, limit=100))

            # Get important memories
            important_memories = len(await self.memory_repository.get_important(user_id, limit=100))

            # Get recent memories
            recent_memories = len(
                await self.memory_repository.get_recent(user_id, hours=24, limit=100)
            )

            return {
                "total_memories": total_memories,
                "important_memories": important_memories,
                "recent_memories": recent_memories,
                "collections": list(self.collection_mapping.values()),
                "embedding_model": "all-MiniLM-L6-v2",
                "embedding_dimension": 384,
            }

        except Exception as e:
            logger.error(f"Failed to get memory stats: {e}")
            return {
                "total_memories": 0,
                "important_memories": 0,
                "recent_memories": 0,
                "error": str(e),
            }
