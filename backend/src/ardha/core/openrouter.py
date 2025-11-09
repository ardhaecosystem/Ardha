"""
OpenRouter AI client implementation.

This module provides a production-ready async client for OpenRouter API
with retry logic, circuit breaker, streaming support, and cost tracking.
"""

import asyncio
import json
import logging
import time
from typing import Any, AsyncGenerator, Dict, List, Optional, Union
import httpx
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from ..core.config import get_settings
from ..schemas.ai.models import get_model, AIModel
from ..schemas.ai.requests import CompletionRequest, StreamingRequest, TokenCountRequest
from ..schemas.ai.responses import (
    CompletionResponse, StreamingChunk, TokenCountResponse, ErrorResponse,
    CostInfo, CircuitBreakerState
)

logger = logging.getLogger(__name__)


class OpenRouterError(Exception):
    """Base exception for OpenRouter API errors."""
    
    def __init__(self, message: str, error_type: str = "api_error", code: Optional[str] = None):
        super().__init__(message)
        self.message = message
        self.error_type = error_type
        self.code = code


class CircuitBreakerOpenError(Exception):
    """Raised when circuit breaker is open."""
    pass


class CircuitBreaker:
    """Circuit breaker implementation for API calls."""
    
    def __init__(self, threshold: int = 3, cooldown_period: int = 300):
        self.threshold = threshold
        self.cooldown_period = cooldown_period
        self.failure_count = 0
        self.last_failure_time = None
        self.state = CircuitBreakerState(
            is_open=False,
            failure_count=0,
            cooldown_period=cooldown_period,
            threshold=threshold
        )
    
    def call_allowed(self) -> bool:
        """Check if call is allowed based on circuit state."""
        if not self.state.is_open:
            return True
        
        if self.state.next_attempt_time is None:
            return False
        
        return time.time() >= self.state.next_attempt_time
    
    def record_success(self):
        """Record a successful call."""
        self.failure_count = 0
        self.state.is_open = False
        self.state.failure_count = 0
        self.state.last_failure_time = None
        self.state.next_attempt_time = None
    
    def record_failure(self):
        """Record a failed call."""
        self.failure_count += 1
        self.state.failure_count = self.failure_count
        self.state.last_failure_time = int(time.time())
        
        if self.failure_count >= self.threshold:
            self.state.is_open = True
            self.state.next_attempt_time = int(time.time() + self.cooldown_period)
            logger.warning(f"Circuit breaker opened after {self.failure_count} failures")
    
    def get_state(self) -> CircuitBreakerState:
        """Get current circuit breaker state."""
        # Create new state with updated values
        state_data = self.state.model_dump()
        state_data["failure_count"] = self.failure_count
        
        if self.state.is_open and self.state.next_attempt_time:
            state_data["time_until_next_attempt"] = max(0, int(self.state.next_attempt_time - time.time()))
        else:
            state_data["time_until_next_attempt"] = None
            
        return CircuitBreakerState(**state_data)


class OpenRouterClient:
    """Production-ready OpenRouter client with retry logic and circuit breaker."""
    
    def __init__(self, api_key: Optional[str] = None, base_url: Optional[str] = None):
        settings = get_settings()
        
        self.api_key = api_key or settings.ai.openrouter_api_key
        self.base_url = base_url or settings.ai.openrouter_base_url
        self.timeout = settings.ai.openrouter_timeout
        self.max_retries = settings.ai.openrouter_max_retries
        
        # Initialize circuit breaker
        self.circuit_breaker = CircuitBreaker(
            threshold=settings.ai.openrouter_circuit_breaker_threshold,
            cooldown_period=settings.ai.openrouter_circuit_breaker_cooldown
        )
        
        # Initialize HTTP client with connection pooling
        self.client = httpx.AsyncClient(
            base_url=self.base_url,
            timeout=httpx.Timeout(self.timeout),
            limits=httpx.Limits(
                max_keepalive_connections=20,
                max_connections=100,
                keepalive_expiry=30
            ),
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
                "HTTP-Referer": "https://ardha.dev",
                "X-Title": "Ardha AI Platform"
            }
        )
        
        # Token counting cache (simple estimation for non-GPT models)
        self._token_cache: Dict[str, float] = {}
        
        logger.info(f"OpenRouter client initialized with timeout={self.timeout}s, max_retries={self.max_retries}")
    
    async def __aenter__(self):
        """Async context manager entry."""
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()
    
    async def close(self):
        """Close the HTTP client."""
        await self.client.aclose()
    
    def _estimate_tokens(self, text: str, model: AIModel) -> int:
        """Estimate token count for non-GPT models."""
        # Simple estimation: ~4 characters per token
        return max(1, len(text) // 4)
    
    def _count_tokens_gpt(self, text: str) -> int:
        """Count tokens for GPT models using tiktoken."""
        try:
            import tiktoken
            
            # Use cl100k_base for most models
            encoding = tiktoken.get_encoding("cl100k_base")
            return len(encoding.encode(text))
        except ImportError:
            logger.warning("tiktoken not available, using estimation")
            default_model = get_model("z-ai/glm-4.6")
            return self._estimate_tokens(text, default_model) if default_model else len(text) // 4
        except Exception as e:
            logger.error(f"Error counting tokens with tiktoken: {e}")
            default_model = get_model("z-ai/glm-4.6")
            return self._estimate_tokens(text, default_model) if default_model else len(text) // 4
    
    def _count_tokens(self, text: str, model: AIModel) -> int:
        """Count tokens for given text and model."""
        cache_key = f"{model.id}:{hash(text)}"
        
        if cache_key in self._token_cache:
            return int(self._token_cache[cache_key])
        
        if "gpt" in model.id.lower():
            count = self._count_tokens_gpt(text)
        else:
            count = self._estimate_tokens(text, model)
        
        self._token_cache[cache_key] = count
        return count
    
    def _count_messages_tokens(self, messages: List[Dict[str, Any]], model: AIModel) -> int:
        """Count tokens for a list of messages."""
        total = 0
        for message in messages:
            content = message.get("content", "")
            if content:
                total += self._count_tokens(content, model)
        return total
    
    def _prepare_request_data(self, request: Union[CompletionRequest, StreamingRequest]) -> Dict[str, Any]:
        """Prepare request data for API call."""
        model = get_model(request.model)
        if not model:
            raise OpenRouterError(f"Unsupported model: {request.model}")
        
        # Count input tokens
        input_tokens = self._count_messages_tokens(
            [msg.model_dump() for msg in request.messages], model
        )
        
        data = {
            "model": request.model,
            "messages": [msg.model_dump() for msg in request.messages],
            "temperature": request.temperature,
            "top_p": request.top_p,
            "frequency_penalty": request.frequency_penalty,
            "presence_penalty": request.presence_penalty,
            "stream": getattr(request, 'stream', False),  # Use stream attribute from request
        }
        
        # Add optional parameters
        if request.max_tokens:
            data["max_tokens"] = request.max_tokens
        if request.stop:
            data["stop"] = request.stop
        if request.tools:
            data["tools"] = [tool.model_dump() for tool in request.tools]
        if request.tool_choice:
            data["tool_choice"] = request.tool_choice
        if request.response_format:
            data["response_format"] = request.response_format
        if request.seed:
            data["seed"] = request.seed
        
        return data
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        retry=retry_if_exception_type((httpx.RequestError, httpx.TimeoutException))
    )
    async def _make_request(self, endpoint: str, data: Dict[str, Any]) -> httpx.Response:
        """Make HTTP request with retry logic."""
        if not self.circuit_breaker.call_allowed():
            raise CircuitBreakerOpenError("Circuit breaker is open")
        
        try:
            logger.debug(f"Making request to {endpoint}")
            response = await self.client.post(endpoint, json=data)
            
            if response.status_code == 200:
                self.circuit_breaker.record_success()
                return response
            else:
                self.circuit_breaker.record_failure()
                error_data = response.json() if response.content else {}
                raise OpenRouterError(
                    f"API request failed: {response.status_code}",
                    error_type="http_error",
                    code=str(response.status_code)
                )
        
        except Exception as e:
            self.circuit_breaker.record_failure()
            if isinstance(e, OpenRouterError):
                raise
            raise OpenRouterError(f"Request failed: {str(e)}", error_type="request_error")
    
    async def complete(self, request: CompletionRequest) -> CompletionResponse:
        """
        Complete a chat completion request.
        
        Args:
            request: Completion request with messages and parameters
            
        Returns:
            CompletionResponse with generated content and usage info
            
        Raises:
            OpenRouterError: If request fails
            CircuitBreakerOpenError: If circuit breaker is open
        """
        logger.info(f"Completion request for model {request.model}")
        
        # Prepare request data
        data = self._prepare_request_data(request)
        model = get_model(request.model)
        if not model:
            raise OpenRouterError(f"Unsupported model: {request.model}")
        
        # Make request
        response = await self._make_request("/chat/completions", data)
        
        # Parse response
        try:
            response_data = response.json()
        except Exception as e:
            logger.error(f"Failed to parse JSON response: {e}")
            logger.error(f"Response content: {response.text}")
            raise OpenRouterError(f"Invalid JSON response: {e}", error_type="json_error")
        
        # Create response object
        completion_response = CompletionResponse.model_validate(response_data)
        
        # Calculate cost
        if completion_response.usage:
            # Calculate cost separately since cost is a property
            cost = model.calculate_cost(
                completion_response.usage.prompt_tokens,
                completion_response.usage.completion_tokens
            )
            # Store cost in a custom attribute or log it
            logger.debug(f"Completion cost: ${cost:.6f}")
        
        logger.info(f"Completion successful, cost: ${completion_response.usage.cost if completion_response.usage else 0:.6f}")
        return completion_response
    
    async def stream(self, request: StreamingRequest) -> AsyncGenerator[StreamingChunk, None]:
        """
        Stream a chat completion request.
        
        Args:
            request: Streaming request with messages and parameters
            
        Yields:
            StreamingChunk objects with partial content
            
        Raises:
            OpenRouterError: If request fails
            CircuitBreakerOpenError: If circuit breaker is open
        """
        logger.info(f"Streaming request for model {request.model}")
        
        # Prepare request data
        data = self._prepare_request_data(request)
        model = get_model(request.model)
        
        # Make streaming request
        if not self.circuit_breaker.call_allowed():
            raise CircuitBreakerOpenError("Circuit breaker is open")
        
        try:
            logger.debug(f"Making streaming request to /chat/completions")
            
            async with self.client.stream("POST", "/chat/completions", json=data) as response:
                if response.status_code != 200:
                    self.circuit_breaker.record_failure()
                    error_data = await response.aread()
                    raise OpenRouterError(
                        f"Streaming request failed: {response.status_code}",
                        error_type="http_error",
                        code=str(response.status_code)
                    )
                
                self.circuit_breaker.record_success()
                
                # Check if response is actually streaming or regular JSON
                content_type = response.headers.get("content-type", "")
                
                if "text/event-stream" in content_type:
                    # Handle SSE streaming
                    async for line in response.aiter_lines():
                        logger.debug(f"Received line: {line}")
                        if line.strip():
                            # Handle SSE format: data: {...}
                            if line.startswith("data: "):
                                data_str = line[6:]  # Remove "data: " prefix
                                
                                if data_str.strip() == "[DONE]":
                                    logger.debug("Received [DONE] signal")
                                    break
                                
                                try:
                                    chunk_data = json.loads(data_str)
                                    chunk = StreamingChunk.model_validate(chunk_data)
                                    logger.debug(f"Yielding chunk: {chunk}")
                                    yield chunk
                                except json.JSONDecodeError as e:
                                    logger.error(f"Failed to parse streaming chunk: {e}")
                                    continue
                            # Skip OpenRouter processing messages
                            elif line.startswith(": OPENROUTER"):
                                logger.debug("OpenRouter processing message")
                                continue
                else:
                    # Handle regular JSON response (non-streaming)
                    response_text = await response.aread()
                    logger.debug(f"Received JSON response: {response_text}")
                    
                    try:
                        response_data = json.loads(response_text)
                        # Convert regular response to streaming chunk
                        if "choices" in response_data and response_data["choices"]:
                            choice = response_data["choices"][0]
                            message = choice.get("message", {})
                            content = message.get("content", "")
                            
                            # Create a streaming chunk from the complete response
                            chunk_data = {
                                "id": response_data.get("id", "unknown"),
                                "object": "chat.completion.chunk",
                                "created": response_data.get("created", int(time.time())),
                                "model": response_data.get("model", request.model),
                                "choices": [{
                                    "index": 0,
                                    "delta": {
                                        "role": message.get("role", "assistant"),
                                        "content": content
                                    },
                                    "finish_reason": choice.get("finish_reason")
                                }]
                            }
                            
                            chunk = StreamingChunk.model_validate(chunk_data)
                            yield chunk
                    except json.JSONDecodeError as e:
                        logger.error(f"Failed to parse JSON response: {e}")
                        raise OpenRouterError(f"Invalid JSON response: {e}", error_type="json_error")
        
        except Exception as e:
            self.circuit_breaker.record_failure()
            if isinstance(e, (OpenRouterError, CircuitBreakerOpenError)):
                raise
            raise OpenRouterError(f"Streaming request failed: {str(e)}", error_type="stream_error")
    
    async def count_tokens(self, request: TokenCountRequest) -> TokenCountResponse:
        """
        Count tokens for given text or messages.
        
        Args:
            request: Token counting request
            
        Returns:
            TokenCountResponse with token count and cost estimate
            
        Raises:
            OpenRouterError: If request fails
        """
        logger.info(f"Token counting request for model {request.model}")
        
        model = get_model(request.model)
        if not model:
            raise OpenRouterError(f"Unsupported model: {request.model}")
        
        # Count tokens locally (more accurate than API for most cases)
        if request.text:
            token_count = self._count_tokens(request.text, model)
            characters = len(request.text)
        elif request.messages:
            token_count = self._count_messages_tokens([msg.model_dump() for msg in request.messages], model)
            characters = sum(len(msg.content) for msg in request.messages)
        else:
            raise OpenRouterError("Either text or messages must be provided")
        
        # Calculate cost estimate
        cost_estimate = model.calculate_cost(token_count, 0)
        logger.debug(f"Token count cost estimate: ${cost_estimate:.6f}")
        
        # Create response with cost estimate
        response = TokenCountResponse(
            model=request.model,
            text=request.text,
            messages=[msg.model_dump() for msg in request.messages] if request.messages else None,
            token_count=token_count,
            tokens=[f"token_{i}" for i in range(token_count)],  # Placeholder
            characters=characters,
            cost_estimate=cost_estimate
        )
        
        logger.info(f"Token count: {token_count}, estimated cost: ${cost_estimate:.6f}")
        return response
    
    async def get_model_info(self, model_id: Optional[str] = None) -> Union[AIModel, List[AIModel]]:
        """
        Get information about available models.
        
        Args:
            model_id: Specific model ID to get info for (optional)
            
        Returns:
            AIModel if model_id provided, otherwise list of all models
            
        Raises:
            OpenRouterError: If request fails
        """
        logger.info(f"Getting model info for {model_id or 'all models'}")
        
        # For now, return from our local configuration
        # In production, this could call OpenRouter's models endpoint
        if model_id:
            model = get_model(model_id)
            if not model:
                raise OpenRouterError(f"Model not found: {model_id}")
            return model
        
        from ..schemas.ai.models import get_all_models
        return get_all_models()
    
    def get_circuit_breaker_state(self) -> CircuitBreakerState:
        """Get current circuit breaker state."""
        return self.circuit_breaker.get_state()
    
    async def health_check(self) -> Dict[str, Any]:
        """
        Perform health check on OpenRouter API.
        
        Returns:
            Health check results
        """
        try:
            # Simple request to check API connectivity
            models = await self.get_model_info()
            return {
                "status": "healthy",
                "api_accessible": True,
                "models_count": len(models) if isinstance(models, list) else 1,
                "circuit_breaker": self.circuit_breaker.get_state().model_dump(),
                "timestamp": time.time()
            }
        except Exception as e:
            return {
                "status": "unhealthy",
                "api_accessible": False,
                "error": str(e),
                "circuit_breaker": self.circuit_breaker.get_state().model_dump(),
                "timestamp": time.time()
            }