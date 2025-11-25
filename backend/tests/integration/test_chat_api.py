"""
Integration tests for Chat API endpoints.

This module tests the complete chat system including API endpoints,
WebSocket streaming, authentication, and database interactions.
"""

import json
from decimal import Decimal
from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
class TestChatAPI:
    """Test suite for Chat API endpoints."""

    async def test_create_chat_endpoint(self, client: AsyncClient, test_user: dict):
        """Test chat creation via API endpoint."""
        # Arrange
        headers = {"Authorization": f"Bearer {test_user['token']}"}
        chat_data = {
            "mode": "research",
            "project_id": None,
        }

        # Act
        response = await client.post(
            "/api/v1/chats",
            headers=headers,
            json=chat_data,
        )

        # Assert
        assert response.status_code == 201
        data = response.json()
        assert "id" in data
        assert data["mode"] == "research"
        assert data["title"] == "New Chat"
        assert data["user_id"] == test_user["user"]["id"]
        assert data["is_archived"] is False
        assert data["total_tokens"] == 0
        assert data["total_cost"] == 0.0

    async def test_create_chat_with_project(
        self, client: AsyncClient, test_user: dict, test_project: dict
    ):
        """Test chat creation with project association."""
        # Arrange
        headers = {"Authorization": f"Bearer {test_user['token']}"}
        chat_data = {
            "mode": "architect",
            "project_id": test_project["id"],
        }

        # Act
        response = await client.post(
            "/api/v1/chats",
            headers=headers,
            json=chat_data,
        )

        # Assert
        assert response.status_code == 201
        data = response.json()
        assert data["mode"] == "architect"
        assert data["project_id"] == test_project["id"]

    async def test_create_chat_invalid_mode(self, client: AsyncClient, test_user: dict):
        """Test chat creation with invalid mode."""
        # Arrange
        headers = {"Authorization": f"Bearer {test_user['token']}"}
        chat_data = {
            "mode": "invalid_mode",
            "project_id": None,
        }

        # Act
        response = await client.post(
            "/api/v1/chats",
            headers=headers,
            json=chat_data,
        )

        # Assert
        assert response.status_code == 422
        assert "Invalid mode" in response.json()["detail"]

    async def test_create_chat_unauthorized(self, client: AsyncClient):
        """Test chat creation without authentication."""
        # Arrange
        chat_data = {
            "mode": "research",
            "project_id": None,
        }

        # Act
        response = await client.post(
            "/api/v1/chats",
            json=chat_data,
        )

        # Assert
        assert response.status_code == 401

    async def test_list_chats_endpoint(self, client: AsyncClient, test_user: dict):
        """Test listing user chats via API endpoint."""
        # Arrange
        headers = {"Authorization": f"Bearer {test_user['token']}"}

        # Create some chats first
        for mode in ["research", "architect", "chat"]:
            await client.post(
                "/api/v1/chats",
                headers=headers,
                json={"mode": mode, "project_id": None},
            )

        # Act
        response = await client.get(
            "/api/v1/chats",
            headers=headers,
        )

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert len(data) >= 3
        assert all("id" in chat for chat in data)
        assert all("mode" in chat for chat in data)
        assert all("title" in chat for chat in data)

    async def test_list_chats_with_project_filter(
        self, client: AsyncClient, test_user: dict, test_project: dict
    ):
        """Test listing chats filtered by project."""
        # Arrange
        headers = {"Authorization": f"Bearer {test_user['token']}"}

        # Create chat with project
        await client.post(
            "/api/v1/chats",
            headers=headers,
            json={"mode": "research", "project_id": test_project["id"]},
        )

        # Create chat without project
        await client.post(
            "/api/v1/chats",
            headers=headers,
            json={"mode": "chat", "project_id": None},
        )

        # Act - Filter by project
        response = await client.get(
            f"/api/v1/chats?project_id={test_project['id']}",
            headers=headers,
        )

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["project_id"] == test_project["id"]

    async def test_list_chats_with_pagination(self, client: AsyncClient, test_user: dict):
        """Test listing chats with pagination."""
        # Arrange
        headers = {"Authorization": f"Bearer {test_user['token']}"}

        # Create multiple chats
        for i in range(5):
            await client.post(
                "/api/v1/chats",
                headers=headers,
                json={"mode": "chat", "project_id": None},
            )

        # Act - Get first page
        response = await client.get(
            "/api/v1/chats?skip=0&limit=3",
            headers=headers,
        )

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 3

        # Act - Get second page
        response = await client.get(
            "/api/v1/chats?skip=3&limit=3",
            headers=headers,
        )

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2  # Remaining chats

    @patch("ardha.services.chat_service.OpenRouterClient")
    async def test_send_message_endpoint(
        self, mock_openrouter_class, client: AsyncClient, test_user: dict
    ):
        """Test sending message via API endpoint."""
        # Arrange
        headers = {"Authorization": f"Bearer {test_user['token']}"}

        # Create chat
        chat_response = await client.post(
            "/api/v1/chats",
            headers=headers,
            json={"mode": "chat", "project_id": None},
        )
        chat_id = chat_response.json()["id"]

        # Mock OpenRouter response
        mock_client = AsyncMock()
        mock_openrouter_class.return_value = mock_client

        mock_chunks = [
            {"content": "Hello! "},
            {"content": "How can I help you today?"},
        ]
        mock_client.stream.return_value.__aiter__.return_value = mock_chunks

        # Mock model info for cost calculation
        with patch("ardha.services.chat_service.get_model") as mock_get_model:
            mock_model = AsyncMock()
            mock_model.calculate_cost.return_value = Decimal("0.05")
            mock_get_model.return_value = mock_model

            # Act
            response = await client.post(
                f"/api/v1/chats/{chat_id}/messages",
                headers=headers,
                json={
                    "content": "Hello, how are you?",
                    "model": "gpt-3.5-turbo",
                },
            )

            # Assert
            assert response.status_code == 200
            data = response.json()
            assert "message" in data
            assert data["message"]["role"] == "assistant"
            assert "Hello! How can I help you today?" in data["message"]["content"]
            assert data["message"]["model_used"] == "gpt-3.5-turbo"

    async def test_send_message_chat_not_found(self, client: AsyncClient, test_user: dict):
        """Test sending message to non-existent chat."""
        # Arrange
        headers = {"Authorization": f"Bearer {test_user['token']}"}
        non_existent_id = uuid4()

        # Act
        response = await client.post(
            f"/api/v1/chats/{non_existent_id}/messages",
            headers=headers,
            json={
                "content": "Hello",
                "model": "gpt-3.5-turbo",
            },
        )

        # Assert
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

    async def test_send_message_unauthorized(self, client: AsyncClient, test_user: dict):
        """Test sending message without authentication."""
        # Arrange
        chat_id = uuid4()

        # Act
        response = await client.post(
            f"/api/v1/chats/{chat_id}/messages",
            json={
                "content": "Hello",
                "model": "gpt-3.5-turbo",
            },
        )

        # Assert
        assert response.status_code == 401

    @pytest.mark.skip(
        reason="WebSocket testing requires httpx-ws or Starlette TestClient. httpx.AsyncClient does not support websocket_connect()."
    )
    async def test_websocket_streaming(self, client: AsyncClient, test_user: dict):
        """Test WebSocket streaming for chat messages.

        TODO: Implement WebSocket testing using one of:
        1. httpx-ws extension: pip install httpx-ws
        2. Starlette TestClient (synchronous): from starlette.testclient import TestClient
        3. websockets library directly: pip install websockets

        Current issue: httpx.AsyncClient does not have websocket_connect() method.
        """
        # Arrange
        headers = {"Authorization": f"Bearer {test_user['token']}"}

        # Create chat
        chat_response = await client.post(
            "/api/v1/chats",
            headers=headers,
            json={"mode": "chat", "project_id": None},
        )
        chat_id = chat_response.json()["id"]

        # Mock OpenRouter response
        with patch("ardha.services.chat_service.OpenRouterClient") as mock_openrouter:
            mock_client = AsyncMock()
            mock_openrouter.return_value = mock_client

            mock_chunks = [
                {"content": "Streaming "},
                {"content": "response "},
                {"content": "test"},
            ]
            mock_client.stream.return_value.__aiter__.return_value = mock_chunks

            with patch("ardha.services.chat_service.get_model") as mock_get_model:
                mock_model = AsyncMock()
                mock_model.calculate_cost.return_value = Decimal("0.03")
                mock_get_model.return_value = mock_model

                # TODO: Replace with proper WebSocket testing
                # Example with httpx-ws:
                # async with httpx_ws.aconnect_ws(
                #     f"ws://test/api/v1/chats/{chat_id}/ws?token={test_user['token']}",
                #     client=client
                # ) as websocket:
                #     await websocket.send_json({"content": "Test", "model": "gpt-3.5-turbo"})
                #     response = await websocket.receive_json()

                pass  # Skipped until proper WebSocket testing is implemented

    @pytest.mark.skip(
        reason="WebSocket testing requires httpx-ws or Starlette TestClient. httpx.AsyncClient does not support websocket_connect()."
    )
    async def test_websocket_unauthorized(self, client: AsyncClient):
        """Test WebSocket connection without authentication.

        TODO: Implement WebSocket testing - see test_websocket_streaming for details.
        """
        # Arrange
        chat_id = uuid4()

        # TODO: Replace with proper WebSocket testing
        pass  # Skipped until proper WebSocket testing is implemented

    @pytest.mark.skip(
        reason="WebSocket testing requires httpx-ws or Starlette TestClient. httpx.AsyncClient does not support websocket_connect()."
    )
    async def test_websocket_invalid_token(self, client: AsyncClient):
        """Test WebSocket connection with invalid token.

        TODO: Implement WebSocket testing - see test_websocket_streaming for details.
        """
        # Arrange
        chat_id = uuid4()
        invalid_token = "invalid_token"

        # TODO: Replace with proper WebSocket testing
        pass  # Skipped until proper WebSocket testing is implemented

    async def test_get_chat_history_endpoint(self, client: AsyncClient, test_user: dict):
        """Test retrieving chat history via API endpoint."""
        # Arrange
        headers = {"Authorization": f"Bearer {test_user['token']}"}

        # Create chat
        chat_response = await client.post(
            "/api/v1/chats",
            headers=headers,
            json={"mode": "chat", "project_id": None},
        )
        chat_id = chat_response.json()["id"]

        # Send a message (mocked)
        with patch("ardha.services.chat_service.OpenRouterClient") as mock_openrouter:
            mock_client = AsyncMock()
            mock_openrouter.return_value = mock_client
            mock_client.stream.return_value.__aiter__.return_value = [{"content": "Test response"}]

            with patch("ardha.services.chat_service.get_model") as mock_get_model:
                mock_model = AsyncMock()
                mock_model.calculate_cost.return_value = Decimal("0.02")
                mock_get_model.return_value = mock_model

                await client.post(
                    f"/api/v1/chats/{chat_id}/messages",
                    headers=headers,
                    json={
                        "content": "Hello",
                        "model": "gpt-3.5-turbo",
                    },
                )

        # Act - Get chat history
        response = await client.get(
            f"/api/v1/chats/{chat_id}/messages",
            headers=headers,
        )

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert len(data) >= 2  # System + User + Assistant

        # Check message roles
        roles = [msg["role"] for msg in data]
        assert "system" in roles
        assert "user" in roles
        assert "assistant" in roles

    async def test_get_chat_history_with_pagination(self, client: AsyncClient, test_user: dict):
        """Test retrieving chat history with pagination."""
        # Arrange
        headers = {"Authorization": f"Bearer {test_user['token']}"}

        # Create chat
        chat_response = await client.post(
            "/api/v1/chats",
            headers=headers,
            json={"mode": "chat", "project_id": None},
        )
        chat_id = chat_response.json()["id"]

        # Act - Get paginated history
        response = await client.get(
            f"/api/v1/chats/{chat_id}/messages?skip=0&limit=1",
            headers=headers,
        )

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1  # Only system message (first message)

    async def test_archive_chat_endpoint(self, client: AsyncClient, test_user: dict):
        """Test chat archival via API endpoint."""
        # Arrange
        headers = {"Authorization": f"Bearer {test_user['token']}"}

        # Create chat
        chat_response = await client.post(
            "/api/v1/chats",
            headers=headers,
            json={"mode": "chat", "project_id": None},
        )
        chat_id = chat_response.json()["id"]

        # Act - Archive chat
        response = await client.post(
            f"/api/v1/chats/{chat_id}/archive",
            headers=headers,
        )

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["is_archived"] is True

        # Verify chat is excluded from default list
        list_response = await client.get(
            "/api/v1/chats",
            headers=headers,
        )
        chats = list_response.json()
        archived_chat = next((c for c in chats if c["id"] == chat_id), None)
        assert archived_chat is None

    async def test_archive_chat_not_found(self, client: AsyncClient, test_user: dict):
        """Test archiving non-existent chat."""
        # Arrange
        headers = {"Authorization": f"Bearer {test_user['token']}"}
        non_existent_id = uuid4()

        # Act
        response = await client.post(
            f"/api/v1/chats/{non_existent_id}/archive",
            headers=headers,
        )

        # Assert
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

    async def test_get_chat_summary_endpoint(self, client: AsyncClient, test_user: dict):
        """Test retrieving chat summary via API endpoint."""
        # Arrange
        headers = {"Authorization": f"Bearer {test_user['token']}"}

        # Create chat
        chat_response = await client.post(
            "/api/v1/chats",
            headers=headers,
            json={"mode": "research", "project_id": None},
        )
        chat_id = chat_response.json()["id"]

        # Act - Get chat summary
        response = await client.get(
            f"/api/v1/chats/{chat_id}/summary",
            headers=headers,
        )

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert "chat" in data
        assert "message_stats" in data
        assert "recent_messages" in data

        chat_info = data["chat"]
        assert chat_info["id"] == chat_id
        assert chat_info["mode"] == "research"
        assert chat_info["total_tokens"] == 0  # No messages sent yet

    async def test_authentication_required(self, client: AsyncClient):
        """Test that authentication is required for all chat endpoints."""
        chat_id = uuid4()

        # Test various endpoints without authentication
        endpoints = [
            ("GET", "/api/v1/chats"),
            ("POST", "/api/v1/chats"),
            ("GET", f"/api/v1/chats/{chat_id}/messages"),
            ("POST", f"/api/v1/chats/{chat_id}/messages"),
            ("POST", f"/api/v1/chats/{chat_id}/archive"),
            ("GET", f"/api/v1/chats/{chat_id}/summary"),
        ]

        for method, endpoint in endpoints:
            # Act
            if method == "GET":
                response = await client.get(endpoint)
            else:
                response = await client.post(endpoint, json={})

            # Assert
            assert response.status_code == 401

    async def test_chat_permission_enforcement_api(self, client: AsyncClient, test_user: dict):
        """Test that API enforces chat permissions correctly."""
        # Arrange
        headers = {"Authorization": f"Bearer {test_user['token']}"}

        # Create chat for test user
        chat_response = await client.post(
            "/api/v1/chats",
            headers=headers,
            json={"mode": "chat", "project_id": None},
        )
        chat_id = chat_response.json()["id"]

        # Create another user and get their token
        register_response = await client.post(
            "/api/v1/auth/register",
            json={
                "email": "other@example.com",
                "username": "otheruser",
                "password": "Test123!@#",
                "full_name": "Other User",
            },
        )

        login_response = await client.post(
            "/api/v1/auth/login",
            data={
                "username": "other@example.com",
                "password": "Test123!@#",
            },
        )
        other_token = login_response.json()["access_token"]
        other_headers = {"Authorization": f"Bearer {other_token}"}

        # Act & Assert - Other user cannot access first user's chat
        endpoints = [
            ("GET", f"/api/v1/chats/{chat_id}/messages"),
            (
                "POST",
                f"/api/v1/chats/{chat_id}/messages",
                {"content": "Hello", "model": "gpt-3.5-turbo"},
            ),
            ("POST", f"/api/v1/chats/{chat_id}/archive"),
            ("GET", f"/api/v1/chats/{chat_id}/summary"),
        ]

        for method, endpoint in endpoints:
            if isinstance(endpoint, tuple):
                endpoint, data = endpoint
            else:
                data = None

            if method == "GET":
                response = await client.get(endpoint, headers=other_headers)
            else:
                response = await client.post(endpoint, headers=other_headers, json=data or {})

            assert response.status_code == 403 or response.status_code == 404
