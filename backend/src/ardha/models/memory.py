"""
Memory models for Ardha application.

This module defines the Memory and MemoryLink models for context management
and knowledge graph functionality. Memories store various types of information
with vector embeddings for semantic search and relationships for knowledge graphs.
"""

from datetime import datetime
from typing import TYPE_CHECKING, Optional
from uuid import UUID

from sqlalchemy import JSON, Boolean, DateTime, Float, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ardha.models.base import Base, BaseModel

if TYPE_CHECKING:
    from ardha.models.project import Project
    from ardha.models.user import User


class MemoryType(str):
    """Memory type enumeration for different kinds of stored information."""

    CONVERSATION = "conversation"
    WORKFLOW = "workflow"
    DOCUMENT = "document"
    ENTITY = "entity"
    FACT = "fact"


class SourceType(str):
    """Source type enumeration for where memories originated."""

    CHAT = "chat"
    WORKFLOW = "workflow"
    MANUAL = "manual"
    API = "api"


class RelationshipType(str):
    """Relationship type enumeration for memory links."""

    RELATED_TO = "related_to"
    DEPENDS_ON = "depends_on"
    CONTRADICTS = "contradicts"
    SUPPORTS = "supports"


class Memory(BaseModel, Base):
    """
    Memory model for storing contextual information with vector embeddings.

    Memories store various types of information (conversations, workflows, documents,
    entities, facts) with associated vector embeddings for semantic search. They
    support quality metrics, lifecycle management, and knowledge graph relationships.

    Attributes:
        user_id: UUID of the user who owns this memory
        project_id: UUID of associated project (nullable for personal memories)
        content: Full text content of the memory
        summary: Brief summary (max 200 chars)
        qdrant_collection: Name of Qdrant collection for vector storage
        qdrant_point_id: Point ID in Qdrant vector database
        embedding_model: Name of embedding model used (default: all-MiniLM-L6-v2)
        memory_type: Type of memory (conversation, workflow, document, entity, fact)
        source_type: Source where memory originated (chat, workflow, manual, api)
        source_id: Optional UUID of the source record
        importance: Importance score (1-10, default: 5)
        confidence: Confidence score (0.0-1.0, default: 0.8)
        access_count: Number of times this memory was accessed
        last_accessed: Timestamp of last access
        expires_at: Optional expiration timestamp
        is_archived: Whether memory is archived (soft delete)
        tags: Optional JSON dictionary for tags
        metadata: Optional JSON dictionary for additional metadata
        user: Relationship to User who owns the memory
        project: Relationship to associated Project
        links_from: Relationship to MemoryLink where this is the source
        links_to: Relationship to MemoryLink where this is the target
    """

    __tablename__ = "memories"

    # Ownership
    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="UUID of the user who owns this memory",
    )

    project_id: Mapped[Optional[UUID]] = mapped_column(
        ForeignKey("projects.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        comment="UUID of associated project (nullable for personal memories)",
    )

    # Content
    content: Mapped[str] = mapped_column(
        Text, nullable=False, comment="Full text content of the memory"
    )

    summary: Mapped[str] = mapped_column(
        String(200), nullable=False, comment="Brief summary of the memory content"
    )

    # Vector storage
    qdrant_collection: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
        comment="Name of Qdrant collection for vector storage",
    )

    qdrant_point_id: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        unique=True,
        index=True,
        comment="Point ID in Qdrant vector database",
    )

    embedding_model: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        default="all-MiniLM-L6-v2",
        comment="Name of embedding model used",
    )

    # Classification
    memory_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
        comment="Type of memory (conversation, workflow, document, entity, fact)",
    )

    source_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
        comment="Source where memory originated (chat, workflow, manual, api)",
    )

    source_id: Mapped[Optional[UUID]] = mapped_column(
        nullable=True, index=True, comment="Optional UUID of the source record"
    )

    # Quality metrics
    importance: Mapped[int] = mapped_column(
        Integer, nullable=False, default=5, index=True, comment="Importance score (1-10)"
    )

    confidence: Mapped[float] = mapped_column(
        Float, nullable=False, default=0.8, comment="Confidence score (0.0-1.0)"
    )

    access_count: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, comment="Number of times this memory was accessed"
    )

    # Lifecycle
    last_accessed: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=datetime.utcnow,
        index=True,
        comment="Timestamp of last access",
    )

    expires_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True, index=True, comment="Optional expiration timestamp"
    )

    is_archived: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        index=True,
        comment="Whether memory is archived (soft delete)",
    )

    # Metadata
    tags: Mapped[Optional[dict]] = mapped_column(
        JSON, nullable=True, comment="Optional JSON dictionary for tags"
    )

    extra_metadata: Mapped[Optional[dict]] = mapped_column(
        JSON, nullable=True, comment="Optional JSON dictionary for additional metadata"
    )

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="memories", lazy="select")

    project: Mapped[Optional["Project"]] = relationship(
        "Project", back_populates="memories", lazy="select"
    )

    links_from: Mapped[list["MemoryLink"]] = relationship(
        "MemoryLink",
        foreign_keys="MemoryLink.memory_from_id",
        back_populates="memory_from",
        cascade="all, delete-orphan",
        lazy="select",
    )

    links_to: Mapped[list["MemoryLink"]] = relationship(
        "MemoryLink",
        foreign_keys="MemoryLink.memory_to_id",
        back_populates="memory_to",
        cascade="all, delete-orphan",
        lazy="select",
    )

    def __repr__(self) -> str:
        """String representation for debugging."""
        return (
            f"<Memory(id={self.id}, "
            f"type='{self.memory_type}', "
            f"user_id={self.user_id}, "
            f"project_id={self.project_id}, "
            f"importance={self.importance}, "
            f"is_archived={self.is_archived})>"
        )


class MemoryLink(BaseModel, Base):
    """
    MemoryLink model for knowledge graph relationships between memories.

    MemoryLinks create a knowledge graph by establishing relationships
    between memories with different relationship types and strength scores.

    Attributes:
        memory_from_id: UUID of the source memory
        memory_to_id: UUID of the target memory
        relationship_type: Type of relationship (related_to, depends_on, contradicts, supports)
        strength: Strength of relationship (0.0-1.0, default: 0.5)
        memory_from: Relationship to source Memory
        memory_to: Relationship to target Memory
    """

    __tablename__ = "memory_links"

    # Relationships
    memory_from_id: Mapped[UUID] = mapped_column(
        ForeignKey("memories.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="UUID of the source memory",
    )

    memory_to_id: Mapped[UUID] = mapped_column(
        ForeignKey("memories.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="UUID of the target memory",
    )

    # Relationship details
    relationship_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
        comment="Type of relationship (related_to, depends_on, contradicts, supports)",
    )

    strength: Mapped[float] = mapped_column(
        Float, nullable=False, default=0.5, comment="Strength of relationship (0.0-1.0)"
    )

    # Relationships
    memory_from: Mapped["Memory"] = relationship(
        "Memory", foreign_keys=[memory_from_id], back_populates="links_from", lazy="select"
    )

    memory_to: Mapped["Memory"] = relationship(
        "Memory", foreign_keys=[memory_to_id], back_populates="links_to", lazy="select"
    )

    def __repr__(self) -> str:
        """String representation for debugging."""
        return (
            f"<MemoryLink(id={self.id}, "
            f"from_id={self.memory_from_id}, "
            f"to_id={self.memory_to_id}, "
            f"type='{self.relationship_type}', "
            f"strength={self.strength})>"
        )


# Indexes for query performance
Index("ix_memory_user_created", Memory.user_id, Memory.created_at.desc())
Index("ix_memory_project_importance", Memory.project_id, Memory.importance.desc())
Index("ix_memory_type_user", Memory.memory_type, Memory.user_id)
Index("ix_memory_expires", Memory.expires_at)
Index("ix_memory_qdrant_point", Memory.qdrant_point_id)
Index("ix_memory_link_from_to", MemoryLink.memory_from_id, MemoryLink.memory_to_id)
