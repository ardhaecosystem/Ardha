"""
Test script for ChatService functionality.

This script tests the chat service with OpenRouter integration
to verify all components work correctly.
"""

import asyncio
import logging
from uuid import uuid4

from ardha.core.database import get_db
from ardha.services.chat_service import ChatService

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def test_chat_service():
    """Test ChatService with OpenRouter integration."""
    
    async for db in get_db():
        chat_service = ChatService(db)
        
        # Test 1: Create a chat
        print("🧪 Test 1: Creating chat...")
        try:
            user_id = uuid4()
            chat = await chat_service.create_chat(
                user_id=user_id,
                mode="chat",
                project_id=None,
            )
            print(f"✅ Chat created: {chat.id} (mode: {chat.mode})")
        except Exception as e:
            print(f"❌ Failed to create chat: {e}")
            return
        
        # Test 2: Send a message
        print("\n🧪 Test 2: Sending message...")
        try:
            response_chunks = []
            async for chunk in chat_service.send_message(
                chat_id=chat.id,
                user_id=user_id,
                content="Hello! Can you explain what Ardha is in one sentence?",
                model="z-ai/glm-4.6",  # Use a free/cheap model for testing
            ):
                response_chunks.append(chunk)
                print(f"📝 Chunk: {chunk[:50]}...")
            
            full_response = "".join(response_chunks)
            print(f"✅ Full response: {full_response}")
        except Exception as e:
            print(f"❌ Failed to send message: {e}")
            return
        
        # Test 3: Get chat history
        print("\n🧪 Test 3: Getting chat history...")
        try:
            messages = await chat_service.get_chat_history(
                chat_id=chat.id,
                user_id=user_id,
                skip=0,
                limit=10,
            )
            print(f"✅ Retrieved {len(messages)} messages")
            for i, msg in enumerate(messages):
                print(f"  {i+1}. {msg.role.value}: {msg.content[:50]}...")
        except Exception as e:
            print(f"❌ Failed to get history: {e}")
        
        # Test 4: Get chat summary
        print("\n🧪 Test 4: Getting chat summary...")
        try:
            summary = await chat_service.get_chat_summary(
                chat_id=chat.id,
                user_id=user_id,
            )
            print(f"✅ Chat summary: {summary['chat']['title']}")
            print(f"   Total tokens: {summary['chat']['total_tokens']}")
            print(f"   Total cost: ${summary['chat']['total_cost']}")
        except Exception as e:
            print(f"❌ Failed to get summary: {e}")
        
        # Test 5: Archive chat
        print("\n🧪 Test 5: Archiving chat...")
        try:
            archived_chat = await chat_service.archive_chat(
                chat_id=chat.id,
                user_id=user_id,
            )
            print(f"✅ Chat archived: {archived_chat.is_archived}")
        except Exception as e:
            print(f"❌ Failed to archive chat: {e}")
        
        print("\n🎉 All tests completed!")


async def test_openrouter_directly():
    """Test OpenRouter client directly."""
    print("\n🔧 Testing OpenRouter client directly...")
    
    try:
        from ardha.core.openrouter import OpenRouterClient
        from ardha.schemas.ai.requests import StreamingRequest, ChatMessage, MessageRole
        
        client = OpenRouterClient()
        
        # Test streaming
        request = StreamingRequest(
            model="z-ai/glm-4.6",
            messages=[
                ChatMessage(role=MessageRole.USER, content="What is 2+2?")
            ],
            temperature=0.7,
            max_tokens=100,
        )
        
        print("📡 Streaming response:")
        async for chunk in client.stream(request):
            print(f"   {chunk.content}")
        
        print("✅ OpenRouter streaming test successful")
        
    except Exception as e:
        print(f"❌ OpenRouter test failed: {e}")


async def main():
    """Run all tests."""
    print("🚀 Starting ChatService integration tests...\n")
    
    # Test OpenRouter directly first
    await test_openrouter_directly()
    
    # Test full ChatService
    await test_chat_service()


if __name__ == "__main__":
    asyncio.run(main())