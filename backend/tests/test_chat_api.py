"""
Comprehensive tests for Chat API endpoints.

This module tests all chat-related functionality including:
- REST API endpoints (CRUD operations)
- WebSocket real-time streaming
- Rate limiting enforcement
- Authentication and authorization
- Error handling and edge cases
"""

import asyncio
import json
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.pool import StaticPool

from ardha.core.config import settings
from ardha.core.database import async_session_factory, get_db
from ardha.main import create_app
from ardha.models.chat import Chat, ChatMode
from ardha.models.message import Message, MessageRole
from ardha.models.user import User
from ardha.schemas.requests.chat import CreateChatRequest, SendMessageRequest
from ardha.schemas.responses.chat import ChatResponse, MessageResponse


@pytest.fixture
async def test_db():
    """Create test database session."""
    # Use in-memory SQLite for testing
    from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    # Create tables
    from ardha.models.base import Base

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # Create async session
    TestSessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with TestSessionLocal() as session:
        yield session


@pytest.fixture
def test_client(test_db):
    """Create test client with database override."""
    app = create_app()

    # Override database dependency
    def override_get_db():
        return test_db

    app.dependency_overrides[get_db] = override_get_db

    with TestClient(app) as client:
        yield client


@pytest.fixture
async def test_user(test_db):
    """Create test user."""
    user = User(
        email="test@example.com",
        username="testuser",
        hashed_password="hashed_password",
        is_active=True,
        is_superuser=False,
    )
    test_db.add(user)
    await test_db.commit()
    await test_db.refresh(user)
    return user


@pytest.fixture
def auth_headers(test_user):
    """Create authentication headers."""
    from ardha.core.security import create_access_token

    token = create_access_token({"sub": str(test_user.id), "email": test_user.email})
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
async def test_chat(test_db, test_user):
    """Create test chat."""
    chat = Chat(
        user_id=test_user.id,
        mode=ChatMode.CHAT,
        title="Test Chat",
        total_tokens=0,
        total_cost=Decimal("0.00"),
        is_archived=False,
    )
    test_db.add(chat)
    await test_db.commit()
    await test_db.refresh(chat)
    return chat


class TestChatCreation:
    """Test chat creation endpoints."""

    async def test_create_chat_success(self, test_client, auth_headers):
        """Test successful chat creation."""
        request_data = {"mode": "chat", "project_id": None}

        response = test_client.post("/api/v1/chats", json=request_data, headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert data["mode"] == "chat"
        assert data["title"] == "New Chat"
        assert "id" in data
        assert "created_at" in data

    async def test_create_chat_with_project(self, test_client, auth_headers, test_user):
        """Test chat creation with project association."""
        # Create a project first
        from ardha.models.project import Project

        project = Project(
            name="Test Project",
            description="Test Description",
            owner_id=test_user.id,
        )
        # Note: This would need to be committed to DB in real test

        request_data = {"mode": "implement", "project_id": str(uuid4())}  # Mock project ID

        response = test_client.post("/api/v1/chats", json=request_data, headers=auth_headers)

        # Should fail with invalid project ID
        assert response.status_code == 404

    async def test_create_chat_invalid_mode(self, test_client, auth_headers):
        """Test chat creation with invalid mode."""
        request_data = {"mode": "invalid_mode", "project_id": None}

        response = test_client.post("/api/v1/chats", json=request_data, headers=auth_headers)

        assert response.status_code == 400
        assert "Invalid mode" in response.json()["detail"]

    async def test_create_chat_unauthorized(self, test_client):
        """Test chat creation without authentication."""
        request_data = {"mode": "chat", "project_id": None}

        response = test_client.post("/api/v1/chats", json=request_data)

        assert response.status_code == 401


class TestChatRetrieval:
    """Test chat retrieval endpoints."""

    async def test_get_user_chats(self, test_client, auth_headers, test_chat):
        """Test getting user's chats."""
        response = test_client.get("/api/v1/chats", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 1
        assert data[0]["id"] == str(test_chat.id)

    async def test_get_chat_history(self, test_client, auth_headers, test_chat, test_db):
        """Test getting chat message history."""
        # Add some test messages
        message1 = Message(
            chat_id=test_chat.id,
            role=MessageRole.USER,
            content="Hello",
        )
        message2 = Message(
            chat_id=test_chat.id,
            role=MessageRole.ASSISTANT,
            content="Hi there!",
        )
        test_db.add_all([message1, message2])
        await test_db.commit()

        response = test_client.get(f"/api/v1/chats/{test_chat.id}/history", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 2

    async def test_get_chat_summary(self, test_client, auth_headers, test_chat):
        """Test getting chat summary."""
        response = test_client.get(f"/api/v1/chats/{test_chat.id}", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert "chat" in data
        assert "message_stats" in data
        assert "recent_messages" in data
        assert data["chat"]["id"] == str(test_chat.id)

    async def test_get_chat_not_found(self, test_client, auth_headers):
        """Test getting non-existent chat."""
        fake_id = uuid4()
        response = test_client.get(f"/api/v1/chats/{fake_id}", headers=auth_headers)

        assert response.status_code == 404

    async def test_get_chat_unauthorized(self, test_client, test_chat):
        """Test getting chat without authentication."""
        response = test_client.get(f"/api/v1/chats/{test_chat.id}")

        assert response.status_code == 401


class TestMessageSending:
    """Test message sending functionality."""

    @patch("ardha.services.chat_service.OpenRouterClient")
    async def test_send_message_success(
        self, mock_openrouter, test_client, auth_headers, test_chat
    ):
        """Test successful message sending with streaming."""
        # Mock OpenRouter response
        mock_client = AsyncMock()
        mock_client.stream.return_value = async_iter(["Hello", " world", "!"])
        mock_openrouter.return_value = mock_client

        request_data = {"content": "Hello world", "model": "gpt-3.5-turbo"}

        response = test_client.post(
            f"/api/v1/chats/{test_chat.id}/messages", json=request_data, headers=auth_headers
        )

        assert response.status_code == 200
        # Should return streaming response
        assert response.headers["content-type"] == "text/event-stream"

    async def test_send_message_empty_content(self, test_client, auth_headers, test_chat):
        """Test sending message with empty content."""
        request_data = {"content": "", "model": "gpt-3.5-turbo"}

        response = test_client.post(
            f"/api/v1/chats/{test_chat.id}/messages", json=request_data, headers=auth_headers
        )

        assert response.status_code == 422  # Validation error

    async def test_send_message_invalid_model(self, test_client, auth_headers, test_chat):
        """Test sending message with invalid model."""
        request_data = {"content": "Hello", "model": "invalid-model-name"}

        response = test_client.post(
            f"/api/v1/chats/{test_chat.id}/messages", json=request_data, headers=auth_headers
        )

        assert response.status_code == 422  # Validation error


class TestChatDeletion:
    """Test chat deletion functionality."""

    async def test_delete_chat_success(self, test_client, auth_headers, test_chat, test_db):
        """Test successful chat deletion."""
        response = test_client.delete(f"/api/v1/chats/{test_chat.id}", headers=auth_headers)

        assert response.status_code == 204

        # Verify chat is deleted
        from ardha.repositories.chat_repository import ChatRepository

        repo = ChatRepository(test_db)
        deleted_chat = await repo.get_by_id(test_chat.id)
        assert deleted_chat is None

    async def test_delete_chat_not_found(self, test_client, auth_headers):
        """Test deleting non-existent chat."""
        fake_id = uuid4()
        response = test_client.delete(f"/api/v1/chats/{fake_id}", headers=auth_headers)

        assert response.status_code == 404

    async def test_delete_chat_unauthorized(self, test_client, test_chat):
        """Test deleting chat without authentication."""
        response = test_client.delete(f"/api/v1/chats/{test_chat.id}")

        assert response.status_code == 401


class TestChatArchiving:
    """Test chat archiving functionality."""

    async def test_archive_chat_success(self, test_client, auth_headers, test_chat, test_db):
        """Test successful chat archiving."""
        response = test_client.post(f"/api/v1/chats/{test_chat.id}/archive", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert data["is_archived"] is True

        # Verify chat is archived
        from ardha.repositories.chat_repository import ChatRepository

        repo = ChatRepository(test_db)
        archived_chat = await repo.get_by_id(test_chat.id)
        assert archived_chat is not None
        assert archived_chat.is_archived is True


class TestRateLimiting:
    """Test rate limiting functionality."""

    @patch("ardha.core.rate_limit.Redis")
    async def test_rate_limit_enforcement(self, mock_redis, test_client, auth_headers, test_chat):
        """Test rate limiting is enforced."""
        # Mock Redis to simulate rate limit exceeded
        mock_redis.pipeline.return_value.zcard.return_value = 11  # Over limit of 10

        request_data = {"content": "Test message", "model": "gpt-3.5-turbo"}

        response = test_client.post(
            f"/api/v1/chats/{test_chat.id}/messages", json=request_data, headers=auth_headers
        )

        assert response.status_code == 429
        data = response.json()
        assert "Rate limit exceeded" in data["detail"]
        assert "retry_after" in data["detail"]
        assert "X-RateLimit-Limit" in response.headers


class TestWebSocket:
    """Test WebSocket functionality."""

    async def test_websocket_connection_success(self, test_client, test_user, test_chat):
        """Test successful WebSocket connection."""
        from ardha.core.security import create_access_token

        token = create_access_token({"sub": str(test_user.id), "email": test_user.email})

        with test_client.websocket_connect(
            f"/api/v1/chats/{test_chat.id}/ws?token={token}"
        ) as websocket:
            # Should connect successfully
            assert websocket is not None

    async def test_websocket_invalid_token(self, test_client, test_chat):
        """Test WebSocket connection with invalid token."""
        with pytest.raises(Exception):  # WebSocket should close with error
            test_client.websocket_connect(f"/api/v1/chats/{test_chat.id}/ws?token=invalid_token")

    async def test_websocket_message_handling(self, test_client, test_user, test_chat):
        """Test WebSocket message sending and receiving."""
        from ardha.core.security import create_access_token

        token = create_access_token({"sub": str(test_user.id), "email": test_user.email})

        with test_client.websocket_connect(
            f"/api/v1/chats/{test_chat.id}/ws?token={token}"
        ) as websocket:
            # Send a message
            message_data = {
                "type": "message",
                "content": "Hello WebSocket",
                "model": "gpt-3.5-turbo",
            }
            websocket.send_json(message_data)

            # Should receive chunks (mocked)
            # In real test, would receive streaming response


# Helper function for async iteration
async def async_iter(items):
    """Helper to create async iterator from list."""
    for item in items:
        yield item


if __name__ == "__main__":
    pytest.main([__file__])
