"""
Chat model for Ardha application.

This module defines the Chat model representing conversation sessions in Ardha.
Chats can be project-specific or personal, with different AI modes for various purposes.
"""

from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import JSON, Boolean, ForeignKey, Index, Integer, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ardha.models.base import Base, BaseModel

if TYPE_CHECKING:
    from ardha.models.message import Message
    from ardha.models.project import Project
    from ardha.models.user import User


class ChatMode(str, Enum):
    """Chat mode enumeration for different AI interaction types."""

    RESEARCH = "research"
    ARCHITECT = "architect"
    IMPLEMENT = "implement"
    DEBUG = "debug"
    CHAT = "chat"


class Chat(BaseModel, Base):
    """
    Chat model representing conversation sessions.

    Chats are the top-level container for conversations between users and AI.
    They can be associated with projects or be personal chats, and support
    different AI modes for various use cases.

    Attributes:
        title: Auto-generated chat title from first message (max 200 chars)
        mode: AI interaction mode (research, architect, implement, debug, chat)
        context: JSON object storing conversation context and state
        total_tokens: Cumulative token count for the entire chat
        total_cost: Cumulative cost for the entire chat (6 decimal places)
        is_archived: Whether chat is archived (hidden from default views)
        project: Associated project (nullable for personal chats)
        user: User who owns the chat
        messages: All messages in this chat (chronological order)
    """

    __tablename__ = "chats"

    # Core fields
    title: Mapped[str] = mapped_column(
        String(200), nullable=False, comment="Auto-generated chat title from first message"
    )

    mode: Mapped[ChatMode] = mapped_column(
        String(20), nullable=False, default=ChatMode.CHAT, comment="AI interaction mode"
    )

    # Context and tracking
    context: Mapped[dict] = mapped_column(
        JSON, default=dict, nullable=False, comment="Conversation context and state"
    )

    total_tokens: Mapped[int] = mapped_column(
        Integer, default=0, nullable=False, comment="Cumulative token count for the entire chat"
    )

    total_cost: Mapped[Decimal] = mapped_column(
        Numeric(10, 6),
        default=Decimal("0.00"),
        nullable=False,
        comment="Cumulative cost for the entire chat",
    )

    # Archive
    is_archived: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False, index=True, comment="Whether chat is archived"
    )

    # Foreign keys
    project_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("projects.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        comment="UUID of associated project (nullable for personal chats)",
    )

    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="UUID of user who owns the chat",
    )

    # Relationships
    project: Mapped["Project"] = relationship("Project", back_populates="chats", lazy="select")

    user: Mapped["User"] = relationship("User", back_populates="chats", lazy="select")

    messages: Mapped[list["Message"]] = relationship(
        "Message",
        back_populates="chat",
        cascade="all, delete-orphan",
        lazy="select",
        order_by="Message.created_at",
    )

    def __repr__(self) -> str:
        """String representation for debugging."""
        return (
            f"<Chat(id={self.id}, "
            f"title='{self.title}', "
            f"mode='{self.mode.value}', "
            f"user_id={self.user_id}, "
            f"project_id={self.project_id}, "
            f"is_archived={self.is_archived})>"
        )


# Indexes for query performance
Index("ix_chats_user_id_created_at", Chat.user_id, Chat.created_at.desc())
Index("ix_chats_project_id_created_at", Chat.project_id, Chat.created_at.desc())
