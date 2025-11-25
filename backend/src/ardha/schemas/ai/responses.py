"""
AI response schemas for OpenRouter integration.

This module defines Pydantic models for AI responses,
including completion results, streaming data,
usage statistics, and error information.
"""

from enum import Enum
from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel, Field


class FinishReason(str, Enum):
    """Reason why completion finished."""

    STOP = "stop"
    LENGTH = "length"
    CONTENT_FILTER = "content_filter"
    TOOL_CALLS = "tool_calls"
    ERROR = "error"


class UsageInfo(BaseModel):
    """Token usage information for a completion."""

    prompt_tokens: int = Field(description="Number of tokens in the prompt")
    completion_tokens: int = Field(description="Number of tokens in the completion")
    total_tokens: int = Field(description="Total tokens used")

    @property
    def cost(self) -> float:
        """Calculate cost based on model pricing."""
        # This will be populated by the client
        return 0.0


class Choice(BaseModel):
    """A single choice in a completion response."""

    index: int = Field(description="Index of this choice")
    message: Dict[str, Any] = Field(description="Message content")
    finish_reason: Optional[FinishReason] = Field(
        default=None, description="Why this choice finished"
    )
    logprobs: Optional[Dict[str, Any]] = Field(default=None, description="Log probabilities")

    @property
    def content(self) -> str:
        """Get message content as string."""
        return self.message.get("content", "")

    @property
    def role(self) -> str:
        """Get message role."""
        return self.message.get("role", "assistant")


class CompletionResponse(BaseModel):
    """Response from a completion request."""

    id: str = Field(description="Unique identifier for this completion")
    object: str = Field(default="chat.completion", description="Object type")
    created: int = Field(description="Unix timestamp of creation")
    model: str = Field(description="Model used for completion")
    choices: List[Choice] = Field(description="List of completion choices")
    usage: Optional[UsageInfo] = Field(default=None, description="Token usage information")
    system_fingerprint: Optional[str] = Field(
        default=None, description="System fingerprint for reproducibility"
    )

    @property
    def first_choice(self) -> Optional[Choice]:
        """Get the first (usually only) choice."""
        return self.choices[0] if self.choices else None

    @property
    def content(self) -> str:
        """Get the content of the first choice."""
        return self.first_choice.content if self.first_choice else ""


class StreamingChunk(BaseModel):
    """A single chunk in a streaming response."""

    id: str = Field(description="Chunk identifier")
    object: str = Field(default="chat.completion.chunk", description="Object type")
    created: int = Field(description="Unix timestamp of creation")
    model: str = Field(description="Model used for completion")
    choices: List[Dict[str, Any]] = Field(description="List of streaming choices")

    @property
    def delta(self) -> Dict[str, Any]:
        """Get the delta content from the first choice."""
        if not self.choices:
            return {}
        return self.choices[0].get("delta", {})

    @property
    def content(self) -> str:
        """Get the content delta from this chunk."""
        return self.delta.get("content", "")

    @property
    def finish_reason(self) -> Optional[str]:
        """Get the finish reason from this chunk."""
        return self.delta.get("finish_reason")

    @property
    def is_complete(self) -> bool:
        """Check if this chunk indicates completion is finished."""
        return self.finish_reason is not None


class TokenCountResponse(BaseModel):
    """Response from token counting request."""

    model: str = Field(description="Model used for tokenization")
    text: Optional[str] = Field(default=None, description="Original text (if provided)")
    messages: Optional[List[Dict[str, Any]]] = Field(
        default=None, description="Original messages (if provided)"
    )
    token_count: int = Field(description="Total number of tokens")
    tokens: List[str] = Field(description="List of individual tokens")
    characters: int = Field(description="Number of characters")

    cost_estimate: float = Field(default=0.0, description="Cost estimate for this token count")


class ModelInfo(BaseModel):
    """Information about an AI model."""

    id: str = Field(description="Model identifier")
    name: str = Field(description="Display name")
    provider: str = Field(description="Model provider")
    tier: str = Field(description="Pricing tier")
    max_input_tokens: int = Field(description="Maximum input tokens")
    max_output_tokens: int = Field(description="Maximum output tokens")
    input_cost_per_million: float = Field(description="Cost per 1M input tokens")
    output_cost_per_million: float = Field(description="Cost per 1M output tokens")
    supports_streaming: bool = Field(description="Whether model supports streaming")
    supports_function_calling: bool = Field(description="Whether model supports function calling")
    context_window: int = Field(description="Context window size")
    description: Optional[str] = Field(default=None, description="Model description")

    @property
    def input_cost_per_token(self) -> float:
        """Cost per input token."""
        return self.input_cost_per_million / 1_000_000

    @property
    def output_cost_per_token(self) -> float:
        """Cost per output token."""
        return self.output_cost_per_million / 1_000_000


class ErrorResponse(BaseModel):
    """Error response from OpenRouter API."""

    error: Dict[str, Any] = Field(description="Error details")

    @property
    def message(self) -> str:
        """Get error message."""
        return self.error.get("message", "Unknown error")

    @property
    def type(self) -> str:
        """Get error type."""
        return self.error.get("type", "unknown")

    @property
    def code(self) -> Optional[str]:
        """Get error code."""
        return self.error.get("code")

    @property
    def is_rate_limit(self) -> bool:
        """Check if this is a rate limit error."""
        return self.type in ["rate_limit_exceeded", "too_many_requests"]

    @property
    def is_timeout(self) -> bool:
        """Check if this is a timeout error."""
        return self.type in ["timeout", "request_timeout"]

    @property
    def is_auth_error(self) -> bool:
        """Check if this is an authentication error."""
        return self.type in ["authentication_error", "invalid_api_key"]


class CostInfo(BaseModel):
    """Cost information for a request."""

    model: str = Field(description="Model used")
    input_tokens: int = Field(description="Input tokens used")
    output_tokens: int = Field(description="Output tokens used")
    input_cost: float = Field(description="Cost for input tokens")
    output_cost: float = Field(description="Cost for output tokens")
    total_cost: float = Field(description="Total cost")
    currency: str = Field(default="USD", description="Currency code")

    @classmethod
    def from_usage(
        cls, model: str, usage: UsageInfo, input_cost_per_token: float, output_cost_per_token: float
    ) -> "CostInfo":
        """Create CostInfo from UsageInfo and pricing."""
        input_cost = usage.prompt_tokens * input_cost_per_token
        output_cost = usage.completion_tokens * output_cost_per_token
        total_cost = input_cost + output_cost

        return cls(
            model=model,
            input_tokens=usage.prompt_tokens,
            output_tokens=usage.completion_tokens,
            input_cost=input_cost,
            output_cost=output_cost,
            total_cost=total_cost,
        )


class CircuitBreakerState(BaseModel):
    """Circuit breaker state information."""

    is_open: bool = Field(description="Whether circuit breaker is open")
    failure_count: int = Field(description="Current failure count")
    last_failure_time: Optional[int] = Field(
        default=None, description="Unix timestamp of last failure"
    )
    next_attempt_time: Optional[int] = Field(
        default=None, description="Unix timestamp when next attempt is allowed"
    )
    cooldown_period: int = Field(description="Cooldown period in seconds")
    threshold: int = Field(description="Failure threshold for opening circuit")

    @property
    def should_allow_request(self) -> bool:
        """Check if request should be allowed."""
        if not self.is_open:
            return True

        if self.next_attempt_time is None:
            return False

        import time

        return time.time() >= self.next_attempt_time

    @property
    def time_until_next_attempt(self) -> Optional[int]:
        """Seconds until next attempt is allowed."""
        if not self.is_open or self.next_attempt_time is None:
            return None

        import time

        remaining = self.next_attempt_time - time.time()
        return max(0, int(remaining))
