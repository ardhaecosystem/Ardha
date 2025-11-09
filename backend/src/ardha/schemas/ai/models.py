"""
AI model definitions and pricing configuration.

This module defines supported AI models, their pricing,
and configuration for the OpenRouter integration.
"""

from enum import Enum
from typing import Dict, Optional
from pydantic import BaseModel, Field


class ModelProvider(str, Enum):
    """AI model providers."""
    ANTHROPIC = "anthropic"
    Z_AI = "z-ai"
    X_AI = "x-ai"
    GOOGLE = "google"


class ModelTier(str, Enum):
    """Model pricing tiers."""
    FREE = "free"
    BASIC = "basic"
    STANDARD = "standard"
    PREMIUM = "premium"


class AIModel(BaseModel):
    """AI model configuration with pricing."""
    
    id: str = Field(description="OpenRouter model ID")
    name: str = Field(description="Display name for the model")
    provider: ModelProvider = Field(description="Model provider")
    tier: ModelTier = Field(description="Pricing tier")
    max_input_tokens: int = Field(description="Maximum input tokens")
    max_output_tokens: int = Field(description="Maximum output tokens")
    input_cost_per_million: float = Field(description="Cost per 1M input tokens in USD")
    output_cost_per_million: float = Field(description="Cost per 1M output tokens in USD")
    supports_streaming: bool = Field(default=True, description="Whether model supports streaming")
    supports_function_calling: bool = Field(default=False, description="Whether model supports function calling")
    context_window: int = Field(description="Context window size in tokens")
    description: Optional[str] = Field(default=None, description="Model description")
    
    @property
    def input_cost_per_token(self) -> float:
        """Cost per input token."""
        return self.input_cost_per_million / 1_000_000
    
    @property
    def output_cost_per_token(self) -> float:
        """Cost per output token."""
        return self.output_cost_per_million / 1_000_000
    
    def calculate_cost(self, input_tokens: int, output_tokens: int) -> float:
        """Calculate total cost for given token usage."""
        input_cost = (input_tokens / 1_000_000) * self.input_cost_per_million
        output_cost = (output_tokens / 1_000_000) * self.output_cost_per_million
        return input_cost + output_cost


# Supported models configuration
SUPPORTED_MODELS: Dict[str, AIModel] = {
    # Anthropic Claude
    "anthropic/claude-sonnet-4.5": AIModel(
        id="anthropic/claude-sonnet-4.5",
        name="Claude Sonnet 4.5",
        provider=ModelProvider.ANTHROPIC,
        tier=ModelTier.PREMIUM,
        max_input_tokens=200_000,
        max_output_tokens=8192,
        input_cost_per_million=3.00,
        output_cost_per_million=15.00,
        supports_streaming=True,
        supports_function_calling=True,
        context_window=200_000,
        description="Most capable model for complex tasks, architecture decisions, and code reviews."
    ),
    
    # Z AI GLM
    "z-ai/glm-4.6": AIModel(
        id="z-ai/glm-4.6",
        name="GLM 4.6",
        provider=ModelProvider.Z_AI,
        tier=ModelTier.STANDARD,
        max_input_tokens=128_000,
        max_output_tokens=4096,
        input_cost_per_million=0.50,
        output_cost_per_million=1.50,
        supports_streaming=True,
        supports_function_calling=True,
        context_window=128_000,
        description="Cost-effective model for feature implementation and bug fixes."
    ),
    
    # X AI Grok
    "x-ai/grok-code-fast-1": AIModel(
        id="x-ai/grok-code-fast-1",
        name="Grok Code Fast 1",
        provider=ModelProvider.X_AI,
        tier=ModelTier.BASIC,
        max_input_tokens=131_072,
        max_output_tokens=4096,
        input_cost_per_million=0.30,
        output_cost_per_million=0.90,
        supports_streaming=True,
        supports_function_calling=False,
        context_window=131_072,
        description="Fast, budget-friendly model for simple tasks and quick fixes."
    ),
    
    # Google Gemini
    "google/gemini-2.5-flash-lite": AIModel(
        id="google/gemini-2.5-flash-lite",
        name="Gemini 2.5 Flash Lite",
        provider=ModelProvider.GOOGLE,
        tier=ModelTier.FREE,
        max_input_tokens=1_048_576,
        max_output_tokens=8192,
        input_cost_per_million=0.075,
        output_cost_per_million=0.30,
        supports_streaming=True,
        supports_function_calling=True,
        context_window=1_048_576,
        description="Free tier model for documentation, comments, and simple queries."
    ),
}


def get_model(model_id: str) -> Optional[AIModel]:
    """Get model configuration by ID."""
    return SUPPORTED_MODELS.get(model_id)


def get_models_by_tier(tier: ModelTier) -> list[AIModel]:
    """Get all models in a specific pricing tier."""
    return [model for model in SUPPORTED_MODELS.values() if model.tier == tier]


def get_models_by_provider(provider: ModelProvider) -> list[AIModel]:
    """Get all models from a specific provider."""
    return [model for model in SUPPORTED_MODELS.values() if model.provider == provider]


def get_all_models() -> list[AIModel]:
    """Get all supported models."""
    return list(SUPPORTED_MODELS.values())


# Model routing recommendations based on task complexity
ROUTING_RECOMMENDATIONS = {
    "simple": ["x-ai/grok-code-fast-1", "google/gemini-2.5-flash-lite"],
    "medium": ["z-ai/glm-4.6", "google/gemini-2.5-flash-lite"],
    "complex": ["anthropic/claude-sonnet-4.5", "z-ai/glm-4.6"],
    "architecture": ["anthropic/claude-sonnet-4.5"],
    "documentation": ["google/gemini-2.5-flash-lite", "x-ai/grok-code-fast-1"],
    "debugging": ["z-ai/glm-4.6", "x-ai/grok-code-fast-1"],
}


def recommend_model(task_type: str, budget_conscious: bool = False) -> Optional[AIModel]:
    """Recommend a model based on task type and budget preference."""
    models = ROUTING_RECOMMENDATIONS.get(task_type, ["z-ai/glm-4.6"])
    
    if budget_conscious:
        # Prefer cheaper models
        for model_id in models:
            model = get_model(model_id)
            if model and model.tier in [ModelTier.FREE, ModelTier.BASIC]:
                return model
    
    # Return first available model
    for model_id in models:
        model = get_model(model_id)
        if model:
            return model
    
    return get_model("z-ai/glm-4.6")  # Default fallback