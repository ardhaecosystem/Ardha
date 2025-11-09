"""
Chat request schemas for API validation.

This module defines Pydantic models for chat-related API requests,
including chat creation and message sending.
"""

from typing import Optional
from uuid import UUID
from pydantic import BaseModel, Field, field_validator


class ChatCreateRequest(BaseModel):
    """Request model for creating a new chat."""
    
    mode: str = Field(
        description="Chat mode (research, architect, implement, debug, chat)",
        pattern="^(research|architect|implement|debug|chat)$"
    )
    project_id: Optional[UUID] = Field(
        default=None,
        description="Optional project ID to associate chat with"
    )
    
    @field_validator("mode")
    @classmethod
    def validate_mode(cls, v: str) -> str:
        """Validate chat mode is supported."""
        valid_modes = ["research", "architect", "implement", "debug", "chat"]
        if v not in valid_modes:
            raise ValueError(f"Invalid mode: {v}. Must be one of: {valid_modes}")
        return v


class MessageSendRequest(BaseModel):
    """Request model for sending a message to chat."""
    
    content: str = Field(
        min_length=1,
        max_length=10000,
        description="Message content to send"
    )
    model: str = Field(
        description="AI model to use for response",
        pattern="^[a-zA-Z0-9_/-]+$"
    )
    
    @field_validator("content")
    @classmethod
    def validate_content(cls, v: str) -> str:
        """Validate message content is not empty."""
        if not v or not v.strip():
            raise ValueError("Message content cannot be empty")
        return v.strip()
    
    @field_validator("model")
    @classmethod
    def validate_model(cls, v: str) -> str:
        """Validate model is supported."""
        from ..ai.models import get_model
        model = get_model(v)
        if not model:
            raise ValueError(f"Unsupported model: {v}")
        return v