"""
Chat request schemas for API validation.

This module defines Pydantic models for chat-related API requests,
including chat creation and message sending.
"""

from typing import Optional
from uuid import UUID
from pydantic import BaseModel, Field, field_validator


from typing import Literal

class CreateChatRequest(BaseModel):
    """Request model for creating a new chat."""
    
    mode: Literal["research", "architect", "implement", "debug", "chat"] = Field(
        description="Chat mode (research, architect, implement, debug, chat)"
    )
    project_id: Optional[UUID] = Field(
        default=None,
        description="Optional project ID to associate chat with"
    )


class SendMessageRequest(BaseModel):
    """Request model for sending a message to chat."""
    
    content: str = Field(
        ...,
        min_length=1,
        max_length=50000,
        description="Message content to send"
    )
    model: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="AI model to use for response"
    )
    
    @field_validator("content")
    @classmethod
    def validate_content(cls, v: str) -> str:
        """Validate message content is not empty."""
        if not v or not v.strip():
            raise ValueError("Message content cannot be empty")
        return v.strip()


# Keep backward compatibility
ChatCreateRequest = CreateChatRequest
MessageSendRequest = SendMessageRequest