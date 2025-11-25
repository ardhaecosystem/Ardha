"""
AI request schemas for OpenRouter integration.

This module defines Pydantic models for AI requests,
including message formats, completion parameters,
and streaming configurations.
"""

from enum import Enum
from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel, Field, field_validator


class MessageRole(str, Enum):
    """Message roles in AI conversations."""

    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"
    TOOL = "tool"


class ChatMessage(BaseModel):
    """A chat message in the conversation."""

    role: MessageRole = Field(description="Role of the message sender")
    content: str = Field(description="Content of the message")
    name: Optional[str] = Field(
        default=None, description="Name of the message sender (for tool messages)"
    )
    tool_calls: Optional[List[Dict[str, Any]]] = Field(
        default=None, description="Tool calls made by the assistant"
    )
    tool_call_id: Optional[str] = Field(
        default=None, description="Tool call ID (for tool messages)"
    )

    @field_validator("content")
    @classmethod
    def validate_content(cls, v: str) -> str:
        """Validate message content is not empty."""
        if not v or not v.strip():
            raise ValueError("Message content cannot be empty")
        return v.strip()


class FunctionDefinition(BaseModel):
    """Definition of a function that can be called by the AI."""

    name: str = Field(description="Name of the function")
    description: str = Field(description="Description of what the function does")
    parameters: Dict[str, Any] = Field(description="JSON schema for function parameters")


class ToolDefinition(BaseModel):
    """Tool definition for function calling."""

    type: str = Field(default="function", description="Type of tool (currently only 'function')")
    function: FunctionDefinition = Field(description="Function definition")


class CompletionRequest(BaseModel):
    """Request for AI completion."""

    model: str = Field(description="Model ID to use for completion")
    messages: List[ChatMessage] = Field(description="List of messages in the conversation")
    max_tokens: Optional[int] = Field(
        default=None, ge=1, le=32768, description="Maximum tokens to generate"
    )
    temperature: float = Field(default=0.7, ge=0.0, le=2.0, description="Sampling temperature")
    top_p: float = Field(default=1.0, ge=0.0, le=1.0, description="Nucleus sampling parameter")
    frequency_penalty: float = Field(default=0.0, ge=-2.0, le=2.0, description="Frequency penalty")
    presence_penalty: float = Field(default=0.0, ge=-2.0, le=2.0, description="Presence penalty")
    stop: Optional[Union[str, List[str]]] = Field(default=None, description="Stop sequences")
    stream: bool = Field(default=False, description="Whether to stream the response")
    tools: Optional[List[ToolDefinition]] = Field(
        default=None, description="Tools available to the AI"
    )
    tool_choice: Optional[Union[str, Dict[str, Any]]] = Field(
        default=None, description="Tool choice strategy"
    )
    response_format: Optional[Dict[str, str]] = Field(
        default=None, description="Response format (e.g., JSON mode)"
    )
    seed: Optional[int] = Field(
        default=None, ge=0, description="Random seed for reproducible results"
    )

    @field_validator("messages")
    @classmethod
    def validate_messages(cls, v: List[ChatMessage]) -> List[ChatMessage]:
        """Validate messages list is not empty and has proper format."""
        if not v:
            raise ValueError("Messages list cannot be empty")

        # Check if first message is from user or system
        if v[0].role not in [MessageRole.SYSTEM, MessageRole.USER]:
            raise ValueError("First message must be from user or system")

        # Check for consecutive messages from same role (except tool messages)
        for i in range(1, len(v)):
            if (
                v[i].role == v[i - 1].role
                and v[i].role not in [MessageRole.TOOL]
                and v[i - 1].role not in [MessageRole.TOOL]
            ):
                raise ValueError(f"Consecutive messages from {v[i].role} role are not allowed")

        return v

    @field_validator("model")
    @classmethod
    def validate_model(cls, v: str) -> str:
        """Validate model ID is supported."""
        from .models import get_model

        model = get_model(v)
        if not model:
            raise ValueError(f"Unsupported model: {v}")
        return v


class StreamingRequest(BaseModel):
    """Request for streaming AI completion."""

    model: str = Field(description="Model ID to use for completion")
    messages: List[ChatMessage] = Field(description="List of messages in the conversation")
    max_tokens: Optional[int] = Field(
        default=None, ge=1, le=32768, description="Maximum tokens to generate"
    )
    temperature: float = Field(default=0.7, ge=0.0, le=2.0, description="Sampling temperature")
    top_p: float = Field(default=1.0, ge=0.0, le=1.0, description="Nucleus sampling parameter")
    frequency_penalty: float = Field(default=0.0, ge=-2.0, le=2.0, description="Frequency penalty")
    presence_penalty: float = Field(default=0.0, ge=-2.0, le=2.0, description="Presence penalty")
    stop: Optional[Union[str, List[str]]] = Field(default=None, description="Stop sequences")
    tools: Optional[List[ToolDefinition]] = Field(
        default=None, description="Tools available to the AI"
    )
    tool_choice: Optional[Union[str, Dict[str, Any]]] = Field(
        default=None, description="Tool choice strategy"
    )
    response_format: Optional[Dict[str, str]] = Field(
        default=None, description="Response format (e.g., JSON mode)"
    )
    seed: Optional[int] = Field(
        default=None, ge=0, description="Random seed for reproducible results"
    )


class TokenCountRequest(BaseModel):
    """Request for token counting."""

    model: str = Field(description="Model ID for tokenization")
    text: str = Field(description="Text to count tokens for")
    messages: Optional[List[ChatMessage]] = Field(
        default=None, description="Messages to count tokens for"
    )

    @field_validator("text", "messages")
    @classmethod
    def validate_content(cls, v: Any, field) -> Any:
        """Validate that either text or messages is provided."""
        # This will be called twice, once for text and once for messages
        # We'll handle the validation in the model validator below
        return v

    @field_validator("messages")
    @classmethod
    def validate_messages_or_text(
        cls, v: Optional[List[ChatMessage]], info
    ) -> Optional[List[ChatMessage]]:
        """Validate that either text or messages is provided."""
        values = info.data
        if not v and not values.get("text"):
            raise ValueError("Either text or messages must be provided")
        if v and values.get("text"):
            raise ValueError("Cannot provide both text and messages")
        return v


class ModelInfoRequest(BaseModel):
    """Request for model information."""

    model: Optional[str] = Field(default=None, description="Specific model ID to get info for")
    list_all: bool = Field(default=False, description="Whether to list all available models")
    tier: Optional[str] = Field(default=None, description="Filter models by tier")
    provider: Optional[str] = Field(default=None, description="Filter models by provider")
