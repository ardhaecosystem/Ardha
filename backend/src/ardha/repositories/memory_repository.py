"""
Memory repository for data access abstraction.

This module provides repository pattern implementation for Memory and MemoryLink models,
handling all database operations related to context management and knowledge graphs.
"""

import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
from uuid import UUID

from sqlalchemy import and_, or_, select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ardha.models.memory import Memory, MemoryLink, MemoryType, RelationshipType, SourceType

logger = logging.getLogger(__name__)


class MemoryRepository:
    """
    Repository for Memory model database operations.

    Provides data access methods for memory-related operations including
    CRUD operations, pagination, vector search integration, and knowledge
    graph relationship management. Follows the repository pattern to
    abstract database implementation details from business logic.

    Attributes:
        db: SQLAlchemy async session for database operations
    """

    def __init__(self, db: AsyncSession) -> None:
        """
        Initialize the MemoryRepository with a database session.

        Args:
            db: SQLAlchemy async session for database operations
        """
        self.db = db

    # CRUD Operations

    async def create(
        self,
        user_id: UUID,
        content: str,
        summary: str,
        qdrant_collection: str,
        qdrant_point_id: str,
        memory_type: str,
        source_type: str,
        project_id: Optional[UUID] = None,
        source_id: Optional[UUID] = None,
        embedding_model: str = "all-MiniLM-L6-v2",
        importance: int = 5,
        confidence: float = 0.8,
        tags: Optional[Dict[str, Any]] = None,
        extra_metadata: Optional[Dict[str, Any]] = None,
        expires_at: Optional[datetime] = None,
    ) -> Memory:
        """
        Create a new memory record.

        Args:
            user_id: UUID of user creating the memory
            content: Full text content of the memory
            summary: Brief summary (max 200 chars)
            qdrant_collection: Name of Qdrant collection
            qdrant_point_id: Point ID in Qdrant
            memory_type: Type of memory (conversation, workflow, document, entity, fact)
            source_type: Source type (chat, workflow, manual, api)
            project_id: Optional UUID of associated project
            source_id: Optional UUID of source record
            embedding_model: Name of embedding model used
            importance: Importance score (1-10)
            confidence: Confidence score (0.0-1.0)
            tags: Optional JSON dictionary for tags
            extra_metadata: Optional JSON dictionary for additional metadata
            expires_at: Optional expiration timestamp

        Returns:
            Created Memory object with generated ID and timestamps

        Raises:
            ValueError: If required fields are invalid
            IntegrityError: If foreign key constraint violated
            SQLAlchemyError: If database operation fails
        """
        try:
            # Validate required fields
            if not content or not content.strip():
                raise ValueError("content cannot be empty")
            if not summary or len(summary) > 200:
                raise ValueError("summary must be 1-200 characters")
            if memory_type not in [
                MemoryType.CONVERSATION,
                MemoryType.WORKFLOW,
                MemoryType.DOCUMENT,
                MemoryType.ENTITY,
                MemoryType.FACT,
            ]:
                raise ValueError(f"Invalid memory_type: {memory_type}")
            if source_type not in [
                SourceType.CHAT,
                SourceType.WORKFLOW,
                SourceType.MANUAL,
                SourceType.API,
            ]:
                raise ValueError(f"Invalid source_type: {source_type}")
            if not (1 <= importance <= 10):
                raise ValueError("importance must be between 1 and 10")
            if not (0.0 <= confidence <= 1.0):
                raise ValueError("confidence must be between 0.0 and 1.0")

            memory = Memory(
                user_id=user_id,
                project_id=project_id,
                content=content.strip(),
                summary=summary.strip(),
                qdrant_collection=qdrant_collection,
                qdrant_point_id=qdrant_point_id,
                embedding_model=embedding_model,
                memory_type=memory_type,
                source_type=source_type,
                source_id=source_id,
                importance=importance,
                confidence=confidence,
                tags=tags or {},
                extra_metadata=extra_metadata or {},
                expires_at=expires_at,
            )

            self.db.add(memory)
            await self.db.flush()
            await self.db.refresh(memory)

            logger.info(f"Created memory {memory.id} for user {user_id} with type {memory_type}")
            return memory
        except IntegrityError as e:
            logger.warning(f"Integrity error creating memory: {e}")
            raise
        except SQLAlchemyError as e:
            logger.error(f"Error creating memory: {e}", exc_info=True)
            raise

    async def get_by_id(self, memory_id: UUID) -> Optional[Memory]:
        """
        Fetch a memory by its UUID.

        Args:
            memory_id: UUID of memory to fetch

        Returns:
            Memory object if found, None otherwise

        Raises:
            SQLAlchemyError: If database query fails
        """
        try:
            stmt = (
                select(Memory)
                .options(
                    selectinload(Memory.user),
                    selectinload(Memory.project),
                    selectinload(Memory.links_from),
                    selectinload(Memory.links_to),
                )
                .where(Memory.id == memory_id)
            )
            result = await self.db.execute(stmt)
            return result.scalar_one_or_none()
        except SQLAlchemyError as e:
            logger.error(f"Error fetching memory by id {memory_id}: {e}", exc_info=True)
            raise

    async def update(self, memory_id: UUID, **kwargs) -> Optional[Memory]:
        """
        Update a memory record.

        Args:
            memory_id: UUID of memory to update
            **kwargs: Fields to update

        Returns:
            Updated Memory object if found, None otherwise

        Raises:
            ValueError: If invalid fields provided
            SQLAlchemyError: If database operation fails
        """
        try:
            memory = await self.get_by_id(memory_id)
            if not memory:
                logger.warning(f"Cannot update: memory {memory_id} not found")
                return None

            # Update allowed fields
            allowed_fields = {
                "content",
                "summary",
                "importance",
                "confidence",
                "tags",
                "extra_metadata",
                "expires_at",
                "is_archived",
            }

            for field, value in kwargs.items():
                if field not in allowed_fields:
                    raise ValueError(f"Cannot update field: {field}")

                # Validate field values
                if field == "content" and (not value or not value.strip()):
                    raise ValueError("content cannot be empty")
                elif field == "summary" and (not value or len(value) > 200):
                    raise ValueError("summary must be 1-200 characters")
                elif field == "importance" and not (1 <= value <= 10):
                    raise ValueError("importance must be between 1 and 10")
                elif field == "confidence" and not (0.0 <= value <= 1.0):
                    raise ValueError("confidence must be between 0.0 and 1.0")

                setattr(memory, field, value)

            await self.db.flush()
            await self.db.refresh(memory)

            logger.info(f"Updated memory {memory_id}")
            return memory
        except SQLAlchemyError as e:
            logger.error(f"Error updating memory {memory_id}: {e}", exc_info=True)
            raise

    async def delete(self, memory_id: UUID) -> None:
        """
        Hard delete a memory and all associated links.

        Args:
            memory_id: UUID of memory to delete

        Raises:
            SQLAlchemyError: If database operation fails
        """
        try:
            memory = await self.get_by_id(memory_id)
            if not memory:
                logger.warning(f"Cannot delete: memory {memory_id} not found")
                return

            await self.db.delete(memory)
            await self.db.flush()

            logger.info(f"Hard deleted memory {memory_id}")
        except SQLAlchemyError as e:
            logger.error(f"Error deleting memory {memory_id}: {e}", exc_info=True)
            raise

    async def archive(self, memory_id: UUID) -> Optional[Memory]:
        """
        Archive a memory (soft delete).

        Args:
            memory_id: UUID of memory to archive

        Returns:
            Updated Memory object if found, None otherwise

        Raises:
            SQLAlchemyError: If database operation fails
        """
        try:
            memory = await self.get_by_id(memory_id)
            if not memory:
                logger.warning(f"Cannot archive: memory {memory_id} not found")
                return None

            memory.is_archived = True
            await self.db.flush()
            await self.db.refresh(memory)

            logger.info(f"Archived memory {memory_id}")
            return memory
        except SQLAlchemyError as e:
            logger.error(f"Error archiving memory {memory_id}: {e}", exc_info=True)
            raise

    # Query Methods

    async def get_by_user(
        self,
        user_id: UUID,
        memory_type: Optional[str] = None,
        skip: int = 0,
        limit: int = 20,
        include_archived: bool = False,
    ) -> List[Memory]:
        """
        Fetch memories owned by a specific user.

        Args:
            user_id: UUID of memory owner
            memory_type: Optional filter by memory type
            skip: Number of records to skip (for pagination)
            limit: Maximum number of records to return (capped at 100)
            include_archived: Whether to include archived memories

        Returns:
            List of Memory objects

        Raises:
            ValueError: If skip or limit are invalid
            SQLAlchemyError: If database query fails
        """
        if skip < 0:
            raise ValueError("skip must be non-negative")
        if limit <= 0 or limit > 100:
            raise ValueError("limit must be between 1 and 100")

        try:
            stmt = select(Memory).where(Memory.user_id == user_id)

            # Filter by memory type if specified
            if memory_type:
                stmt = stmt.where(Memory.memory_type == memory_type)

            # Filter out archived memories by default
            if not include_archived:
                stmt = stmt.where(Memory.is_archived == False)

            # Order by most recent first
            stmt = stmt.order_by(Memory.created_at.desc())

            # Apply pagination
            stmt = stmt.offset(skip).limit(limit)

            result = await self.db.execute(stmt)
            return list(result.scalars().all())
        except SQLAlchemyError as e:
            logger.error(f"Error fetching memories by user {user_id}: {e}", exc_info=True)
            raise

    async def get_by_project(
        self,
        project_id: UUID,
        skip: int = 0,
        limit: int = 20,
        include_archived: bool = False,
    ) -> List[Memory]:
        """
        Fetch memories associated with a specific project.

        Args:
            project_id: UUID of project
            skip: Number of records to skip (for pagination)
            limit: Maximum number of records to return (capped at 100)
            include_archived: Whether to include archived memories

        Returns:
            List of Memory objects

        Raises:
            ValueError: If skip or limit are invalid
            SQLAlchemyError: If database query fails
        """
        if skip < 0:
            raise ValueError("skip must be non-negative")
        if limit <= 0 or limit > 100:
            raise ValueError("limit must be between 1 and 100")

        try:
            stmt = select(Memory).where(Memory.project_id == project_id)

            # Filter out archived memories by default
            if not include_archived:
                stmt = stmt.where(Memory.is_archived == False)

            # Order by importance first, then by created_at
            stmt = stmt.order_by(Memory.importance.desc(), Memory.created_at.desc())

            # Apply pagination
            stmt = stmt.offset(skip).limit(limit)

            result = await self.db.execute(stmt)
            return list(result.scalars().all())
        except SQLAlchemyError as e:
            logger.error(f"Error fetching memories by project {project_id}: {e}", exc_info=True)
            raise

    async def get_recent(
        self,
        user_id: UUID,
        hours: int = 24,
        limit: int = 50,
    ) -> List[Memory]:
        """
        Fetch recent memories for a user.

        Args:
            user_id: UUID of user
            hours: Number of hours to look back (default: 24)
            limit: Maximum number of records to return (capped at 100)

        Returns:
            List of Memory objects

        Raises:
            ValueError: If hours or limit are invalid
            SQLAlchemyError: If database query fails
        """
        if hours <= 0:
            raise ValueError("hours must be positive")
        if limit <= 0 or limit > 100:
            raise ValueError("limit must be between 1 and 100")

        try:
            cutoff_time = datetime.utcnow() - timedelta(hours=hours)

            stmt = (
                select(Memory)
                .where(
                    and_(
                        Memory.user_id == user_id,
                        Memory.created_at >= cutoff_time,
                        Memory.is_archived == False,
                    )
                )
                .order_by(Memory.created_at.desc())
                .limit(limit)
            )

            result = await self.db.execute(stmt)
            return list(result.scalars().all())
        except SQLAlchemyError as e:
            logger.error(f"Error fetching recent memories for user {user_id}: {e}", exc_info=True)
            raise

    async def get_important(
        self,
        user_id: UUID,
        min_importance: int = 7,
        limit: int = 10,
    ) -> List[Memory]:
        """
        Fetch important memories for a user.

        Args:
            user_id: UUID of user
            min_importance: Minimum importance score (default: 7)
            limit: Maximum number of records to return (capped at 100)

        Returns:
            List of Memory objects

        Raises:
            ValueError: If min_importance or limit are invalid
            SQLAlchemyError: If database query fails
        """
        if not (1 <= min_importance <= 10):
            raise ValueError("min_importance must be between 1 and 10")
        if limit <= 0 or limit > 100:
            raise ValueError("limit must be between 1 and 100")

        try:
            stmt = (
                select(Memory)
                .where(
                    and_(
                        Memory.user_id == user_id,
                        Memory.importance >= min_importance,
                        Memory.is_archived == False,
                    )
                )
                .order_by(Memory.importance.desc(), Memory.last_accessed.desc())
                .limit(limit)
            )

            result = await self.db.execute(stmt)
            return list(result.scalars().all())
        except SQLAlchemyError as e:
            logger.error(
                f"Error fetching important memories for user {user_id}: {e}", exc_info=True
            )
            raise

    async def search_by_tags(
        self,
        user_id: UUID,
        tags: List[str],
    ) -> List[Memory]:
        """
        Search memories by tags.

        Args:
            user_id: UUID of user
            tags: List of tags to search for

        Returns:
            List of Memory objects

        Raises:
            ValueError: If tags list is empty
            SQLAlchemyError: If database query fails
        """
        if not tags:
            raise ValueError("tags list cannot be empty")

        try:
            # Build JSON query for tags containment
            tag_conditions = []
            for tag in tags:
                tag_conditions.append(Memory.tags[tag].isnot(None))

            stmt = (
                select(Memory)
                .where(
                    and_(
                        Memory.user_id == user_id, Memory.is_archived == False, or_(*tag_conditions)
                    )
                )
                .order_by(Memory.importance.desc(), Memory.created_at.desc())
            )

            result = await self.db.execute(stmt)
            return list(result.scalars().all())
        except SQLAlchemyError as e:
            logger.error(f"Error searching memories by tags for user {user_id}: {e}", exc_info=True)
            raise

    # Memory Management Methods

    async def increment_access_count(self, memory_id: UUID) -> Optional[Memory]:
        """
        Increment access count and update last_accessed timestamp.

        Args:
            memory_id: UUID of memory to update

        Returns:
            Updated Memory object if found, None otherwise

        Raises:
            SQLAlchemyError: If database operation fails
        """
        try:
            memory = await self.get_by_id(memory_id)
            if not memory:
                logger.warning(f"Cannot increment access: memory {memory_id} not found")
                return None

            memory.access_count += 1
            memory.last_accessed = datetime.utcnow()

            await self.db.flush()
            await self.db.refresh(memory)

            logger.info(f"Incremented access count for memory {memory_id}")
            return memory
        except SQLAlchemyError as e:
            logger.error(
                f"Error incrementing access count for memory {memory_id}: {e}", exc_info=True
            )
            raise

    async def update_importance(self, memory_id: UUID, importance: int) -> Optional[Memory]:
        """
        Update memory importance score.

        Args:
            memory_id: UUID of memory to update
            importance: New importance score (1-10)

        Returns:
            Updated Memory object if found, None otherwise

        Raises:
            ValueError: If importance is invalid
            SQLAlchemyError: If database operation fails
        """
        if not (1 <= importance <= 10):
            raise ValueError("importance must be between 1 and 10")

        try:
            memory = await self.get_by_id(memory_id)
            if not memory:
                logger.warning(f"Cannot update importance: memory {memory_id} not found")
                return None

            memory.importance = importance
            await self.db.flush()
            await self.db.refresh(memory)

            logger.info(f"Updated importance for memory {memory_id} to {importance}")
            return memory
        except SQLAlchemyError as e:
            logger.error(f"Error updating importance for memory {memory_id}: {e}", exc_info=True)
            raise

    async def expire_old_memories(self, hours: int = 24) -> int:
        """
        Delete expired memories.

        Args:
            hours: Number of hours to look back for expired memories

        Returns:
            Number of memories deleted

        Raises:
            ValueError: If hours is invalid
            SQLAlchemyError: If database operation fails
        """
        if hours <= 0:
            raise ValueError("hours must be positive")

        try:
            cutoff_time = datetime.utcnow() - timedelta(hours=hours)

            stmt = select(Memory).where(
                and_(Memory.expires_at <= cutoff_time, Memory.expires_at.isnot(None))
            )

            result = await self.db.execute(stmt)
            memories_to_delete = list(result.scalars().all())

            deleted_count = 0
            for memory in memories_to_delete:
                await self.db.delete(memory)
                deleted_count += 1

            await self.db.flush()

            logger.info(f"Deleted {deleted_count} expired memories")
            return deleted_count
        except SQLAlchemyError as e:
            logger.error(f"Error expiring old memories: {e}", exc_info=True)
            raise

    async def get_expiring_soon(self, hours: int = 24) -> List[Memory]:
        """
        Get memories that will expire soon.

        Args:
            hours: Number of hours to look ahead

        Returns:
            List of Memory objects

        Raises:
            ValueError: If hours is invalid
            SQLAlchemyError: If database query fails
        """
        if hours <= 0:
            raise ValueError("hours must be positive")

        try:
            cutoff_time = datetime.utcnow() + timedelta(hours=hours)

            stmt = (
                select(Memory)
                .where(
                    and_(
                        Memory.expires_at <= cutoff_time,
                        Memory.expires_at > datetime.utcnow(),
                        Memory.is_archived == False,
                    )
                )
                .order_by(Memory.expires_at.asc())
            )

            result = await self.db.execute(stmt)
            return list(result.scalars().all())
        except SQLAlchemyError as e:
            logger.error(f"Error getting expiring memories: {e}", exc_info=True)
            raise

    async def get_by_source(
        self,
        source_type: str,
        source_id: UUID,
    ) -> List[Memory]:
        """
        Get memories by source.

        Args:
            source_type: Source type (chat, workflow, manual, api)
            source_id: UUID of source record

        Returns:
            List of Memory objects

        Raises:
            ValueError: If source_type is invalid
            SQLAlchemyError: If database query fails
        """
        if source_type not in [
            SourceType.CHAT,
            SourceType.WORKFLOW,
            SourceType.MANUAL,
            SourceType.API,
        ]:
            raise ValueError(f"Invalid source_type: {source_type}")

        try:
            stmt = (
                select(Memory)
                .where(
                    and_(
                        Memory.source_type == source_type,
                        Memory.source_id == source_id,
                        not Memory.is_archived,
                    )
                )
                .order_by(Memory.created_at.desc())
            )

            result = await self.db.execute(stmt)
            return list(result.scalars().all())
        except SQLAlchemyError as e:
            logger.error(
                f"Error getting memories by source {source_type}:{source_id}: {e}", exc_info=True
            )
            raise

    # Relationship Methods

    async def create_link(
        self,
        from_id: UUID,
        to_id: UUID,
        relationship_type: str,
        strength: float = 0.5,
    ) -> MemoryLink:
        """
        Create a link between two memories.

        Args:
            from_id: UUID of source memory
            to_id: UUID of target memory
            relationship_type: Type of relationship (related_to, depends_on, contradicts, supports)
            strength: Strength of relationship (0.0-1.0)

        Returns:
            Created MemoryLink object

        Raises:
            ValueError: If parameters are invalid
            IntegrityError: If foreign key constraint violated
            SQLAlchemyError: If database operation fails
        """
        try:
            # Validate parameters
            if from_id == to_id:
                raise ValueError("Cannot link memory to itself")
            if relationship_type not in [
                RelationshipType.RELATED_TO,
                RelationshipType.DEPENDS_ON,
                RelationshipType.CONTRADICTS,
                RelationshipType.SUPPORTS,
            ]:
                raise ValueError(f"Invalid relationship_type: {relationship_type}")
            if not (0.0 <= strength <= 1.0):
                raise ValueError("strength must be between 0.0 and 1.0")

            # Check if memories exist
            from_memory = await self.get_by_id(from_id)
            to_memory = await self.get_by_id(to_id)

            if not from_memory:
                raise ValueError(f"Source memory {from_id} not found")
            if not to_memory:
                raise ValueError(f"Target memory {to_id} not found")

            link = MemoryLink(
                memory_from_id=from_id,
                memory_to_id=to_id,
                relationship_type=relationship_type,
                strength=strength,
            )

            self.db.add(link)
            await self.db.flush()
            await self.db.refresh(link)

            logger.info(f"Created link from {from_id} to {to_id} with type {relationship_type}")
            return link
        except IntegrityError as e:
            logger.warning(f"Integrity error creating memory link: {e}")
            raise
        except SQLAlchemyError as e:
            logger.error(f"Error creating memory link: {e}", exc_info=True)
            raise

    async def get_related_memories(
        self,
        memory_id: UUID,
        relationship_type: Optional[str] = None,
        min_strength: float = 0.3,
    ) -> List[Memory]:
        """
        Get memories related to a specific memory.

        Args:
            memory_id: UUID of memory to find relations for
            relationship_type: Optional filter by relationship type
            min_strength: Minimum relationship strength

        Returns:
            List of related Memory objects

        Raises:
            ValueError: If parameters are invalid
            SQLAlchemyError: If database query fails
        """
        if not (0.0 <= min_strength <= 1.0):
            raise ValueError("min_strength must be between 0.0 and 1.0")
        if relationship_type and relationship_type not in [
            RelationshipType.RELATED_TO,
            RelationshipType.DEPENDS_ON,
            RelationshipType.CONTRADICTS,
            RelationshipType.SUPPORTS,
        ]:
            raise ValueError(f"Invalid relationship_type: {relationship_type}")

        try:
            # Build query for both outgoing and incoming links
            base_conditions = [
                MemoryLink.strength >= min_strength,
                or_(MemoryLink.memory_from_id == memory_id, MemoryLink.memory_to_id == memory_id),
            ]

            if relationship_type:
                base_conditions.append(MemoryLink.relationship_type == relationship_type)

            stmt = select(MemoryLink).where(and_(*base_conditions))

            result = await self.db.execute(stmt)
            links = list(result.scalars().all())

            # Extract related memory IDs
            related_ids = set()
            for link in links:
                if link.memory_from_id == memory_id:
                    related_ids.add(link.memory_to_id)
                else:
                    related_ids.add(link.memory_from_id)

            # Fetch related memories
            if related_ids:
                stmt = select(Memory).where(Memory.id.in_(related_ids))
                result = await self.db.execute(stmt)
                return list(result.scalars().all())

            return []
        except SQLAlchemyError as e:
            logger.error(f"Error getting related memories for {memory_id}: {e}", exc_info=True)
            raise

    async def delete_link(self, link_id: UUID) -> None:
        """
        Delete a memory link.

        Args:
            link_id: UUID of link to delete

        Raises:
            SQLAlchemyError: If database operation fails
        """
        try:
            stmt = select(MemoryLink).where(MemoryLink.id == link_id)
            result = await self.db.execute(stmt)
            link = result.scalar_one_or_none()

            if not link:
                logger.warning(f"Cannot delete link: link {link_id} not found")
                return

            await self.db.delete(link)
            await self.db.flush()

            logger.info(f"Deleted memory link {link_id}")
        except SQLAlchemyError as e:
            logger.error(f"Error deleting memory link {link_id}: {e}", exc_info=True)
            raise

    async def get_memory_graph(
        self,
        memory_id: UUID,
        depth: int = 2,
    ) -> Dict[str, Any]:
        """
        Get memory graph starting from a specific memory.

        Args:
            memory_id: UUID of starting memory
            depth: Maximum depth of graph traversal

        Returns:
            Dictionary representing the memory graph

        Raises:
            ValueError: If depth is invalid
            SQLAlchemyError: If database operation fails
        """
        if depth < 1 or depth > 3:
            raise ValueError("depth must be between 1 and 3")

        try:
            # This is a simplified implementation
            # In a production system, you might want to use a graph database
            # or implement a more efficient traversal algorithm

            graph = {"nodes": {}, "edges": [], "starting_memory": str(memory_id)}

            # Get the starting memory
            start_memory = await self.get_by_id(memory_id)
            if not start_memory:
                return graph

            graph["nodes"][str(memory_id)] = {  # type: ignore
                "id": str(memory_id),
                "summary": start_memory.summary,
                "memory_type": start_memory.memory_type,
                "importance": start_memory.importance,
            }

            # Get related memories recursively
            visited = {memory_id}
            current_level = {memory_id}

            for level in range(depth):
                next_level = set()

                for current_id in current_level:
                    related_memories = await self.get_related_memories(current_id)

                    for related_memory in related_memories:
                        if related_memory.id not in visited:
                            visited.add(related_memory.id)
                            next_level.add(related_memory.id)

                            graph["nodes"][str(related_memory.id)] = {  # type: ignore
                                "id": str(related_memory.id),
                                "summary": related_memory.summary,
                                "memory_type": related_memory.memory_type,
                                "importance": related_memory.importance,
                            }

                            # Add edge (simplified - in practice you'd get actual link details)
                            graph["edges"].append(
                                {
                                    "from": str(current_id),
                                    "to": str(related_memory.id),
                                    "relationship_type": "related_to",  # Simplified
                                    "strength": 0.5,  # Simplified
                                }
                            )

                current_level = next_level
                if not current_level:
                    break

            return graph
        except SQLAlchemyError as e:
            logger.error(f"Error getting memory graph for {memory_id}: {e}", exc_info=True)
            raise
