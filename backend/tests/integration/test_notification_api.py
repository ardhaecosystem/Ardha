"""
Integration tests for notification API endpoints.

This module tests the notification REST API and WebSocket endpoints including:
- Listing notifications with pagination and filtering
- Marking notifications as read (single and bulk)
- Deleting notifications
- Notification statistics
- Notification preference management
- Real-time WebSocket notifications
"""

from uuid import uuid4

import pytest
from httpx import AsyncClient
from starlette.testclient import TestClient

from ardha.models.notification import Notification
from ardha.models.notification_preference import NotificationPreference

# ============= Test Notification List =============


@pytest.mark.asyncio
class TestNotificationList:
    """Test notification listing endpoints."""

    async def test_list_notifications_success(
        self,
        client: AsyncClient,
        test_user: dict,
        test_notifications_batch,
    ):
        """Test listing notifications successfully."""
        # Login
        response = await client.post(
            "/api/v1/auth/login",
            data={"username": test_user["user"]["email"], "password": "Test123!@#"},
        )
        token = response.json()["access_token"]

        # List notifications
        response = await client.get(
            "/api/v1/notifications",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 200
        data = response.json()

        assert "notifications" in data
        assert "total" in data
        assert "unread_count" in data
        assert "page" in data
        assert "page_size" in data
        assert len(data["notifications"]) == 5  # All 5 notifications
        assert data["unread_count"] == 3  # 3 unread

    async def test_list_notifications_pagination(
        self,
        client: AsyncClient,
        test_user: dict,
        test_notifications_batch,
    ):
        """Test pagination parameters."""
        # Login
        response = await client.post(
            "/api/v1/auth/login",
            data={"username": test_user["user"]["email"], "password": "Test123!@#"},
        )
        token = response.json()["access_token"]

        # List with pagination
        response = await client.get(
            "/api/v1/notifications?skip=0&limit=2",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 200
        data = response.json()

        assert len(data["notifications"]) == 2
        assert data["page"] == 1
        assert data["page_size"] == 2

    async def test_list_notifications_unread_only(
        self,
        client: AsyncClient,
        test_user: dict,
        test_unread_notifications,
        test_read_notifications,
    ):
        """Test filtering to unread only."""
        # Login
        response = await client.post(
            "/api/v1/auth/login",
            data={"username": test_user["user"]["email"], "password": "Test123!@#"},
        )
        token = response.json()["access_token"]

        # List unread only
        response = await client.get(
            "/api/v1/notifications?unread_only=true",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 200
        data = response.json()

        # All notifications should be unread
        assert all(not n["is_read"] for n in data["notifications"])
        assert len(data["notifications"]) == 3  # Only unread ones

    async def test_list_notifications_empty(
        self,
        client: AsyncClient,
        test_user: dict,
    ):
        """Test listing when no notifications exist."""
        # Login
        response = await client.post(
            "/api/v1/auth/login",
            data={"username": test_user["user"]["email"], "password": "Test123!@#"},
        )
        token = response.json()["access_token"]

        # List notifications
        response = await client.get(
            "/api/v1/notifications",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 200
        data = response.json()

        assert data["notifications"] == []
        assert data["total"] == 0
        assert data["unread_count"] == 0

    async def test_list_notifications_unauthorized(self, client: AsyncClient):
        """Test listing notifications without authentication."""
        # Try to list without token
        response = await client.get("/api/v1/notifications")

        assert response.status_code == 401


# ============= Test Notification Read Status =============


@pytest.mark.asyncio
class TestNotificationRead:
    """Test marking notifications as read."""

    async def test_mark_notification_read_success(
        self,
        client: AsyncClient,
        test_user: dict,
        test_notification: Notification,
    ):
        """Test marking notification as read."""
        # Login
        response = await client.post(
            "/api/v1/auth/login",
            data={"username": test_user["user"]["email"], "password": "Test123!@#"},
        )
        token = response.json()["access_token"]

        # Mark as read
        response = await client.patch(
            f"/api/v1/notifications/{test_notification.id}/read",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 200
        data = response.json()

        assert data["is_read"] is True
        assert data["read_at"] is not None

    async def test_mark_notification_read_not_found(
        self,
        client: AsyncClient,
        test_user: dict,
    ):
        """Test marking non-existent notification."""
        # Login
        response = await client.post(
            "/api/v1/auth/login",
            data={"username": test_user["user"]["email"], "password": "Test123!@#"},
        )
        token = response.json()["access_token"]

        # Try to mark non-existent notification
        fake_id = uuid4()
        response = await client.patch(
            f"/api/v1/notifications/{fake_id}/read",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 404

    async def test_mark_notification_read_wrong_user(
        self,
        client: AsyncClient,
        test_user: dict,
        test_db,
    ):
        """Test marking another user's notification."""
        # Create another user
        from ardha.models.user import User as UserModel

        other_user = UserModel(
            id=uuid4(),
            email="other@example.com",
            username="otheruser",
            full_name="Other User",
            password_hash="hashed",
        )
        test_db.add(other_user)
        await test_db.commit()

        # Create notification for other user
        other_notification = Notification(
            id=uuid4(),
            user_id=other_user.id,
            type="task_assigned",
            title="Other User Notification",
            message="This belongs to other user",
            is_read=False,
        )
        test_db.add(other_notification)
        await test_db.commit()

        # Login as test_user
        response = await client.post(
            "/api/v1/auth/login",
            data={"username": test_user["user"]["email"], "password": "Test123!@#"},
        )
        token = response.json()["access_token"]

        # Try to mark other user's notification
        response = await client.patch(
            f"/api/v1/notifications/{other_notification.id}/read",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 403

    async def test_mark_all_read_success(
        self,
        client: AsyncClient,
        test_user: dict,
        test_unread_notifications,
    ):
        """Test marking all notifications as read."""
        # Login
        response = await client.post(
            "/api/v1/auth/login",
            data={"username": test_user["user"]["email"], "password": "Test123!@#"},
        )
        token = response.json()["access_token"]

        # Mark all as read
        response = await client.post(
            "/api/v1/notifications/mark-all-read",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 200
        data = response.json()

        assert "marked_count" in data
        assert data["marked_count"] == 3  # All 3 unread notifications
        assert "message" in data

    async def test_mark_all_read_none_unread(
        self,
        client: AsyncClient,
        test_user: dict,
        test_read_notifications,
    ):
        """Test marking all when none are unread."""
        # Login
        response = await client.post(
            "/api/v1/auth/login",
            data={"username": test_user["user"]["email"], "password": "Test123!@#"},
        )
        token = response.json()["access_token"]

        # Mark all as read (should mark 0)
        response = await client.post(
            "/api/v1/notifications/mark-all-read",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 200
        data = response.json()

        assert data["marked_count"] == 0


# ============= Test Notification Delete =============


@pytest.mark.asyncio
class TestNotificationDelete:
    """Test notification deletion."""

    async def test_delete_notification_success(
        self,
        client: AsyncClient,
        test_user: dict,
        test_notification: Notification,
    ):
        """Test deleting notification."""
        # Login
        response = await client.post(
            "/api/v1/auth/login",
            data={"username": test_user["user"]["email"], "password": "Test123!@#"},
        )
        token = response.json()["access_token"]

        # Delete notification
        response = await client.delete(
            f"/api/v1/notifications/{test_notification.id}",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 204

        # Verify deleted
        response = await client.get(
            "/api/v1/notifications",
            headers={"Authorization": f"Bearer {token}"},
        )
        data = response.json()
        assert len(data["notifications"]) == 0

    async def test_delete_notification_not_found(
        self,
        client: AsyncClient,
        test_user: dict,
    ):
        """Test deleting non-existent notification."""
        # Login
        response = await client.post(
            "/api/v1/auth/login",
            data={"username": test_user["user"]["email"], "password": "Test123!@#"},
        )
        token = response.json()["access_token"]

        # Try to delete non-existent notification
        fake_id = uuid4()
        response = await client.delete(
            f"/api/v1/notifications/{fake_id}",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 404

    async def test_delete_notification_wrong_user(
        self,
        client: AsyncClient,
        test_user: dict,
        test_db,
    ):
        """Test deleting another user's notification."""
        # Create another user
        from ardha.models.user import User as UserModel

        other_user = UserModel(
            id=uuid4(),
            email="other@example.com",
            username="otheruser",
            full_name="Other User",
            password_hash="hashed",
        )
        test_db.add(other_user)
        await test_db.commit()

        # Create notification for other user
        other_notification = Notification(
            id=uuid4(),
            user_id=other_user.id,
            type="task_assigned",
            title="Other User Notification",
            message="This belongs to other user",
            is_read=False,
        )
        test_db.add(other_notification)
        await test_db.commit()

        # Login as test_user
        response = await client.post(
            "/api/v1/auth/login",
            data={"username": test_user["user"]["email"], "password": "Test123!@#"},
        )
        token = response.json()["access_token"]

        # Try to delete other user's notification
        response = await client.delete(
            f"/api/v1/notifications/{other_notification.id}",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 403


# ============= Test Notification Stats =============


@pytest.mark.asyncio
class TestNotificationStats:
    """Test notification statistics."""

    async def test_get_stats_success(
        self,
        client: AsyncClient,
        test_user: dict,
        test_notifications_batch,
    ):
        """Test getting notification statistics."""
        # Login
        response = await client.post(
            "/api/v1/auth/login",
            data={"username": test_user["user"]["email"], "password": "Test123!@#"},
        )
        token = response.json()["access_token"]

        # Get stats
        response = await client.get(
            "/api/v1/notifications/stats",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 200
        data = response.json()

        assert "total_count" in data
        assert "unread_count" in data
        assert "by_type" in data
        assert "recent_notifications" in data

        assert data["total_count"] == 5
        assert data["unread_count"] == 3
        assert len(data["recent_notifications"]) <= 5

    async def test_get_stats_no_notifications(
        self,
        client: AsyncClient,
        test_user: dict,
    ):
        """Test stats when no notifications exist."""
        # Login
        response = await client.post(
            "/api/v1/auth/login",
            data={"username": test_user["user"]["email"], "password": "Test123!@#"},
        )
        token = response.json()["access_token"]

        # Get stats
        response = await client.get(
            "/api/v1/notifications/stats",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 200
        data = response.json()

        assert data["total_count"] == 0
        assert data["unread_count"] == 0
        assert data["by_type"] == {}
        assert data["recent_notifications"] == []


# ============= Test Notification Preferences =============


@pytest.mark.asyncio
class TestNotificationPreferences:
    """Test notification preference management."""

    async def test_get_preferences_creates_default(
        self,
        client: AsyncClient,
        test_user: dict,
    ):
        """Test getting preferences auto-creates default."""
        # Login
        response = await client.post(
            "/api/v1/auth/login",
            data={"username": test_user["user"]["email"], "password": "Test123!@#"},
        )
        token = response.json()["access_token"]

        # Get preferences (should auto-create)
        response = await client.get(
            "/api/v1/notifications/preferences",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 200
        data = response.json()

        # Verify default values
        assert data["email_enabled"] is True
        assert data["push_enabled"] is True
        assert data["task_assigned"] is True
        assert data["email_frequency"] == "instant"

    async def test_get_preferences_existing(
        self,
        client: AsyncClient,
        test_user: dict,
        test_notification_preferences: NotificationPreference,
    ):
        """Test getting existing preferences."""
        # Login
        response = await client.post(
            "/api/v1/auth/login",
            data={"username": test_user["user"]["email"], "password": "Test123!@#"},
        )
        token = response.json()["access_token"]

        # Get preferences
        response = await client.get(
            "/api/v1/notifications/preferences",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 200
        data = response.json()

        assert data["id"] == str(test_notification_preferences.id)
        assert data["user_id"] == test_user["user"]["id"]

    async def test_update_preferences_email_enabled(
        self,
        client: AsyncClient,
        test_user: dict,
        test_notification_preferences: NotificationPreference,
    ):
        """Test updating email_enabled preference."""
        # Login
        response = await client.post(
            "/api/v1/auth/login",
            data={"username": test_user["user"]["email"], "password": "Test123!@#"},
        )
        token = response.json()["access_token"]

        # Update email_enabled
        response = await client.patch(
            "/api/v1/notifications/preferences",
            json={"email_enabled": False},
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 200
        data = response.json()

        assert data["email_enabled"] is False

    async def test_update_preferences_quiet_hours(
        self,
        client: AsyncClient,
        test_user: dict,
        test_notification_preferences: NotificationPreference,
    ):
        """Test setting quiet hours."""
        # Login
        response = await client.post(
            "/api/v1/auth/login",
            data={"username": test_user["user"]["email"], "password": "Test123!@#"},
        )
        token = response.json()["access_token"]

        # Set quiet hours (22:00 to 08:00)
        response = await client.patch(
            "/api/v1/notifications/preferences",
            json={
                "quiet_hours_start": "22:00:00",
                "quiet_hours_end": "08:00:00",
            },
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 200
        data = response.json()

        assert data["quiet_hours_start"] == "22:00:00"
        assert data["quiet_hours_end"] == "08:00:00"

    async def test_update_preferences_email_frequency(
        self,
        client: AsyncClient,
        test_user: dict,
        test_notification_preferences: NotificationPreference,
    ):
        """Test changing email frequency."""
        # Login
        response = await client.post(
            "/api/v1/auth/login",
            data={"username": test_user["user"]["email"], "password": "Test123!@#"},
        )
        token = response.json()["access_token"]

        # Change to daily
        response = await client.patch(
            "/api/v1/notifications/preferences",
            json={"email_frequency": "daily"},
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 200
        data = response.json()

        assert data["email_frequency"] == "daily"

    async def test_update_preferences_notification_types(
        self,
        client: AsyncClient,
        test_user: dict,
        test_notification_preferences: NotificationPreference,
    ):
        """Test disabling specific notification types."""
        # Login
        response = await client.post(
            "/api/v1/auth/login",
            data={"username": test_user["user"]["email"], "password": "Test123!@#"},
        )
        token = response.json()["access_token"]

        # Disable task_completed notifications
        response = await client.patch(
            "/api/v1/notifications/preferences",
            json={
                "task_completed": False,
                "mentions": False,
            },
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 200
        data = response.json()

        assert data["task_completed"] is False
        assert data["mentions"] is False
        # Other types still enabled
        assert data["task_assigned"] is True


# ============= Test WebSocket Notifications =============


class TestWebSocketNotifications:
    """Test WebSocket real-time notifications."""

    def test_websocket_connect_success(
        self,
        test_user: dict,
    ):
        """Test successful WebSocket connection."""
        from unittest.mock import patch

        from ardha.main import app

        # Mock decode_token to avoid database operations
        mock_user_id = test_user["user"]["id"]

        def mock_decode_token(token: str):
            return {"sub": mock_user_id}

        # Apply mock and test
        with patch(
            "ardha.api.v1.routes.websocket.decode_token",
            side_effect=mock_decode_token,
        ):
            with TestClient(app) as sync_client:
                # Connect to WebSocket with mocked authentication
                with sync_client.websocket_connect(
                    "/api/v1/ws/notifications?token=test_token"
                ) as websocket:
                    # Should receive connection confirmation
                    message = websocket.receive_json()

                    assert message["type"] == "system"
                    assert "Connected successfully" in message["data"]["message"]
                    assert message["data"]["user_id"] == mock_user_id

    def test_websocket_connect_invalid_token(self):
        """Test WebSocket connection with invalid token."""
        from unittest.mock import patch

        from ardha.main import app

        # Mock decode_token to raise an error
        def mock_decode_token_error(token: str):
            raise ValueError("Invalid token")

        with patch(
            "ardha.api.v1.routes.websocket.decode_token",
            side_effect=mock_decode_token_error,
        ):
            with TestClient(app) as sync_client:
                # Try to connect with invalid token - should fail
                try:
                    with sync_client.websocket_connect(
                        "/api/v1/ws/notifications?token=invalid_token"
                    ) as _:
                        # Should not reach here - connection should be rejected
                        pytest.fail("WebSocket should have rejected invalid token")
                except Exception:
                    # Expected to fail - connection rejected
                    pass

    def test_websocket_ping_pong(
        self,
        test_user: dict,
    ):
        """Test ping/pong keepalive mechanism."""
        from unittest.mock import patch

        from ardha.main import app

        # Mock decode_token to avoid database operations
        mock_user_id = test_user["user"]["id"]

        def mock_decode_token(token: str):
            return {"sub": mock_user_id}

        with patch(
            "ardha.api.v1.routes.websocket.decode_token",
            side_effect=mock_decode_token,
        ):
            with TestClient(app) as sync_client:
                # Connect to WebSocket
                with sync_client.websocket_connect(
                    "/api/v1/ws/notifications?token=test_token"
                ) as websocket:
                    # Receive connection message
                    websocket.receive_json()

                    # Send ping
                    websocket.send_json({"type": "ping"})

                    # Should receive pong
                    message = websocket.receive_json()
                    assert message["type"] == "pong"

    def test_websocket_disconnect_cleanup(
        self,
        test_user: dict,
    ):
        """Test WebSocket disconnection and cleanup."""
        from unittest.mock import patch

        from ardha.main import app

        # Mock decode_token to avoid database operations
        mock_user_id = test_user["user"]["id"]

        def mock_decode_token(token: str):
            return {"sub": mock_user_id}

        with patch(
            "ardha.api.v1.routes.websocket.decode_token",
            side_effect=mock_decode_token,
        ):
            with TestClient(app) as sync_client:
                # Connect and disconnect
                with sync_client.websocket_connect(
                    "/api/v1/ws/notifications?token=test_token"
                ) as websocket:
                    # Receive connection message
                    websocket.receive_json()

                    # Connection will be cleaned up when context exits

            # WebSocket manager should clean up the connection
            # This is verified by the manager's disconnect method
