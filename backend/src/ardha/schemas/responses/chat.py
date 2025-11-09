"""
Chat response schemas for API responses.

This module defines Pydantic models for chat-related API responses,
including chat information, messages, and summaries.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID
from pydantic import BaseModel, Field


class ChatResponse(BaseModel):
    """Response model for chat information."""
    
    id: UUID = Field(description="Chat UUID")
    title: str = Field(description="Chat title")
    mode: str = Field(description="Chat mode (research, architect, implement, debug, chat)")
    created_at: datetime = Field(description="Chat creation timestamp")
    updated_at: datetime = Field(description="Last update timestamp")
    is_archived: bool = Field(description="Whether chat is archived")
    project_id: Optional[UUID] = Field(default=None, description="Associated project ID")
    total_tokens: int = Field(description="Total tokens used in chat")
    total_cost: float = Field(description="Total cost of chat in USD")
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat(),
            UUID: lambda v: str(v),
        }


class MessageResponse(BaseModel):
    """Response model for chat message."""
    
    id: UUID = Field(description="Message UUID")
    role: str = Field(description="Message role (system, user, assistant, tool)")
    content: str = Field(description="Message content")
    created_at: datetime = Field(description="Message creation timestamp")
    model_used: Optional[str] = Field(default=None, description="AI model used for assistant messages")
    tokens_input: Optional[int] = Field(default=None, description="Input tokens used")
    tokens_output: Optional[int] = Field(default=None, description="Output tokens used")
    cost: Optional[float] = Field(default=None, description="Cost of this message in USD")
    message_metadata: Optional[Dict[str, Any]] = Field(default=None, description="Additional message metadata")
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat(),
            UUID: lambda v: str(v),
        }


class MessageStats(BaseModel):
    """Statistics for messages in a chat."""
    
    total_messages: int = Field(description="Total number of messages")
    user_messages: int = Field(description="Number of user messages")
    assistant_messages: int = Field(description="Number of assistant messages")
    system_messages: int = Field(description="Number of system messages")
    total_tokens: int = Field(description="Total tokens across all messages")
    total_cost: float = Field(description="Total cost across all messages in USD")


class RecentMessage(BaseModel):
    """Simplified message for recent messages list."""
    
    id: UUID = Field(description="Message UUID")
    role: str = Field(description="Message role")
    content: str = Field(description="Message content (truncated)")
    created_at: datetime = Field(description="Message creation timestamp")
    model_used: Optional[str] = Field(default=None, description="AI model used")
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat(),
            UUID: lambda v: str(v),
        }


class ChatSummaryResponse(BaseModel):
    """Comprehensive chat summary response."""
    
    chat: ChatResponse = Field(description="Chat information")
    message_stats: MessageStats = Field(description="Message statistics")
    recent_messages: List[RecentMessage] = Field(description="Recent messages (last 5)")
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat(),
            UUID: lambda v: str(v),
        }


class ChatListResponse(BaseModel):
    """Response model for list of chats."""
    
    chats: List[ChatResponse] = Field(description="List of chats")
    total_count: int = Field(description="Total number of chats")
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat(),
            UUID: lambda v: str(v),
        }


class MessageListResponse(BaseModel):
    """Response model for list of messages."""
    
    messages: List[MessageResponse] = Field(description="List of messages")
    total_count: int = Field(description="Total number of messages")
    has_more: bool = Field(description="Whether there are more messages")
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat(),
            UUID: lambda v: str(v),
        }