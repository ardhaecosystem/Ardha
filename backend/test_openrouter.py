#!/usr/bin/env python3
"""
Simple test script to demonstrate OpenRouter AI integration.

This script tests all major features:
- Model information retrieval
- Token counting with cost estimation
- Non-streaming completion
- Streaming completion
- Health check
- Circuit breaker functionality
"""

import asyncio
import logging
from ardha.core.openrouter import OpenRouterClient
from ardha.schemas.ai.requests import CompletionRequest, StreamingRequest, TokenCountRequest, ChatMessage, MessageRole

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')


async def main():
    """Run comprehensive OpenRouter tests."""
    print("🚀 Testing OpenRouter AI Integration")
    print("=" * 50)
    
    try:
        async with OpenRouterClient() as client:
            
            # Test 1: Get model information
            print("\n📋 Test 1: Model Information")
            models = await client.get_model_info()
            print(f"✅ Available models: {len(models) if isinstance(models, list) else 1}")
            
            # Test 2: Token counting
            print("\n🔢 Test 2: Token Counting")
            token_request = TokenCountRequest(
                model='google/gemini-2.5-flash-lite',
                text='Hello! This is a test message for token counting.'
            )
            token_response = await client.count_tokens(token_request)
            print(f"✅ Tokens: {token_response.token_count}")
            print(f"✅ Characters: {token_response.characters}")
            print(f"✅ Cost estimate: ${token_response.cost_estimate:.6f}")
            
            # Test 3: Non-streaming completion
            print("\n💬 Test 3: Non-Streaming Completion")
            completion_request = CompletionRequest(
                model='google/gemini-2.5-flash-lite',
                messages=[ChatMessage(role=MessageRole.USER, content='What is 2+2?')]
            )
            completion_response = await client.complete(completion_request)
            print(f"✅ Response: {completion_response.content}")
            print(f"✅ Model: {completion_response.model}")
            print(f"✅ Usage: {completion_response.usage}")
            
            # Test 4: Streaming completion
            print("\n🌊 Test 4: Streaming Completion")
            stream_request = StreamingRequest(
                model='google/gemini-2.5-flash-lite',
                messages=[ChatMessage(role=MessageRole.USER, content='Tell me a joke')]
            )
            
            print("📡 Streaming response:")
            full_response = ""
            chunk_count = 0
            async for chunk in client.stream(stream_request):
                chunk_count += 1
                if chunk.content:
                    print(chunk.content, end='', flush=True)
                    full_response += chunk.content
            
            print(f"\n✅ Total chunks: {chunk_count}")
            print(f"✅ Full response: {full_response}")
            
            # Test 5: Health check
            print("\n🏥 Test 5: Health Check")
            health = await client.health_check()
            print(f"✅ Status: {health['status']}")
            print(f"✅ API accessible: {health['api_accessible']}")
            print(f"✅ Circuit breaker: {health['circuit_breaker']}")
            
            # Test 6: Circuit breaker state
            print("\n⚡ Test 6: Circuit Breaker State")
            cb_state = client.get_circuit_breaker_state()
            print(f"✅ Circuit breaker open: {cb_state.is_open}")
            print(f"✅ Failure count: {cb_state.failure_count}")
            print(f"✅ Time until next attempt: {cb_state.time_until_next_attempt}")
            
            print("\n🎉 All tests completed successfully!")
            
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        return 1
    
    return 0


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    exit(exit_code)