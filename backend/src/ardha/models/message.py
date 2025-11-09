"""
Message model for Ardha application.

This module defines the Message model representing individual messages in chat conversations.
Messages support user, assistant, and system roles with detailed AI metadata.
"""

from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING
from uuid import UUID
from enum import Enum

from sqlalchemy import ForeignKey, String, Text, Integer, Numeric, JSON, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ardha.models.base import Base, BaseModel

if TYPE_CHECKING:
    from ardha.models.chat import Chat
    from ardha.models.user import User


class MessageRole(str, Enum):
    """Message role enumeration for different message types."""
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


class Message(BaseModel, Base):
    """
    Message model representing individual chat messages.
    
    Messages are the atomic units of conversation, supporting user,
    assistant, and system roles with comprehensive AI metadata.
    
    Attributes:
        role: Message role (user, assistant, system)
        content: Message content (unlimited text)
        model_used: AI model name used for assistant messages
        tokens_input: Input tokens for AI-generated messages
        tokens_output: Output tokens for AI-generated messages
        cost: Cost for AI-generated messages (6 decimal places)
        metadata: JSON for tool calls, reasoning, and other AI data
        chat: Parent chat conversation
    """
    
    __tablename__ = "messages"
    
    # Core fields
    role: Mapped[MessageRole] = mapped_column(
        String(10),
        nullable=False,
        comment="Message role (user, assistant, system)"
    )
    
    content: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        comment="Message content"
    )
    
    # AI metadata (nullable for user/system messages)
    model_used: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
        comment="AI model name used for assistant messages"
    )
    
    tokens_input: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
        comment="Input tokens for AI-generated messages"
    )
    
    tokens_output: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
        comment="Output tokens for AI-generated messages"
    )
    
    cost: Mapped[Decimal | None] = mapped_column(
        Numeric(10, 6),
        nullable=True,
        comment="Cost for AI-generated messages"
    )
    
    # Additional metadata
    message_metadata: Mapped[dict] = mapped_column(
        JSON,
        default=dict,
        nullable=False,
        comment="JSON for tool calls, reasoning, and other AI data"
    )
    
    # Foreign key
    chat_id: Mapped[UUID] = mapped_column(
        ForeignKey("chats.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="UUID of parent chat conversation"
    )
    
    # Relationships
    chat: Mapped["Chat"] = relationship(
        "Chat",
        back_populates="messages",
        lazy="select"
    )
    
    def __repr__(self) -> str:
        """String representation for debugging."""
        return (
            f"<Message(id={self.id}, "
            f"role='{self.role.value}', "
            f"chat_id={self.chat_id}, "
            f"model_used='{self.model_used}', "
            f"tokens_input={self.tokens_input}, "
            f"tokens_output={self.tokens_output})>"
        )


# Index for query performance
Index("ix_messages_chat_id_created_at", Message.chat_id, Message.created_at.asc())