"""
Test fixtures for notification system.

This module provides reusable test fixtures for notification API testing including:
- Sample notifications (single and batch)
- Notification preferences
- Mock email service
- WebSocket test utilities
"""

from datetime import datetime, timezone
from typing import Dict, List
from uuid import uuid4

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from ardha.models.notification import Notification
from ardha.models.notification_preference import NotificationPreference

# ============= Notification Fixtures =============


@pytest_asyncio.fixture
async def test_notification(
    test_db: AsyncSession,
    test_user: dict,
) -> Notification:
    """
    Create a single test notification.

    Args:
        test_db: Test database session
        test_user: Test user fixture (dict from conftest)

    Returns:
        Notification instance with standard test data
    """
    from uuid import UUID

    user_id = UUID(test_user["user"]["id"])

    notification = Notification(
        id=uuid4(),
        user_id=user_id,
        type="task_assigned",
        title="Test Notification",
        message="This is a test notification message",
        data={"task_id": str(uuid4()), "task_title": "Test Task"},
        link_type="task",
        link_id=uuid4(),
        is_read=False,
        created_at=datetime.now(timezone.utc),
    )

    test_db.add(notification)
    await test_db.commit()
    await test_db.refresh(notification)

    return notification


@pytest_asyncio.fixture
async def test_notifications_batch(
    test_db: AsyncSession,
    test_user: dict,
) -> List[Notification]:
    """
    Create batch of notifications for pagination testing.

    Creates 5 notifications:
    - 3 unread (task_assigned, mention, project_invite)
    - 2 read (task_completed, system)

    Args:
        test_db: Test database session
        test_user: Test user fixture (dict from conftest)

    Returns:
        List of 5 Notification instances
    """
    from uuid import UUID

    user_id = UUID(test_user["user"]["id"])
    notifications = []

    # Unread notifications
    for i, notif_type in enumerate(["task_assigned", "mention", "project_invite"]):
        notification = Notification(
            id=uuid4(),
            user_id=user_id,
            type=notif_type,
            title=f"Test Notification {i + 1}",
            message=f"Test message for {notif_type}",
            data={"index": i},
            is_read=False,
            created_at=datetime.now(timezone.utc),
        )
        test_db.add(notification)
        notifications.append(notification)

    # Read notifications
    for i, notif_type in enumerate(["task_completed", "system"], start=3):
        notification = Notification(
            id=uuid4(),
            user_id=user_id,
            type=notif_type,
            title=f"Test Notification {i + 1}",
            message=f"Test message for {notif_type}",
            data={"index": i},
            is_read=True,
            read_at=datetime.now(timezone.utc),
            created_at=datetime.now(timezone.utc),
        )
        test_db.add(notification)
        notifications.append(notification)

    await test_db.commit()

    # Refresh all notifications
    for notification in notifications:
        await test_db.refresh(notification)

    return notifications


@pytest_asyncio.fixture
async def test_notification_preferences(
    test_db: AsyncSession,
    test_user: dict,
) -> NotificationPreference:
    """
    Create test notification preferences with default settings.

    Args:
        test_db: Test database session
        test_user: Test user fixture (dict from conftest)

    Returns:
        NotificationPreference instance with default settings
    """
    from uuid import UUID

    user_id = UUID(test_user["user"]["id"])

    preferences = NotificationPreference(
        id=uuid4(),
        user_id=user_id,
        email_enabled=True,
        push_enabled=True,
        task_assigned=True,
        task_completed=True,
        task_overdue=True,
        mentions=True,
        project_invites=True,
        database_updates=True,
        system_notifications=True,
        email_frequency="instant",
        quiet_hours_start=None,
        quiet_hours_end=None,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )

    test_db.add(preferences)
    await test_db.commit()
    await test_db.refresh(preferences)

    return preferences


@pytest_asyncio.fixture
async def test_unread_notifications(
    test_db: AsyncSession,
    test_user: dict,
) -> List[Notification]:
    """
    Create batch of unread notifications only.

    Creates 3 unread notifications of different types.

    Args:
        test_db: Test database session
        test_user: Test user fixture (dict from conftest)

    Returns:
        List of 3 unread Notification instances
    """
    from uuid import UUID

    user_id = UUID(test_user["user"]["id"])
    notifications = []

    for i, notif_type in enumerate(["task_assigned", "mention", "task_overdue"]):
        notification = Notification(
            id=uuid4(),
            user_id=user_id,
            type=notif_type,
            title=f"Unread Notification {i + 1}",
            message=f"Unread test message for {notif_type}",
            data={"index": i, "status": "unread"},
            is_read=False,
            created_at=datetime.now(timezone.utc),
        )
        test_db.add(notification)
        notifications.append(notification)

    await test_db.commit()

    for notification in notifications:
        await test_db.refresh(notification)

    return notifications


@pytest_asyncio.fixture
async def test_read_notifications(
    test_db: AsyncSession,
    test_user: dict,
) -> List[Notification]:
    """
    Create batch of read notifications only.

    Creates 2 read notifications of different types.

    Args:
        test_db: Test database session
        test_user: Test user fixture (dict from conftest)

    Returns:
        List of 2 read Notification instances
    """
    from uuid import UUID

    user_id = UUID(test_user["user"]["id"])
    notifications = []

    for i, notif_type in enumerate(["task_completed", "system"]):
        notification = Notification(
            id=uuid4(),
            user_id=user_id,
            type=notif_type,
            title=f"Read Notification {i + 1}",
            message=f"Read test message for {notif_type}",
            data={"index": i, "status": "read"},
            is_read=True,
            read_at=datetime.now(timezone.utc),
            created_at=datetime.now(timezone.utc),
        )
        test_db.add(notification)
        notifications.append(notification)

    await test_db.commit()

    for notification in notifications:
        await test_db.refresh(notification)

    return notifications


@pytest.fixture
def notification_service(test_db: AsyncSession):
    """
    Get NotificationService instance for testing.

    Args:
        test_db: Test database session

    Returns:
        NotificationService instance configured with test database
    """
    from ardha.services.notification_service import NotificationService

    return NotificationService(test_db)


@pytest.fixture
def mock_email_service(monkeypatch):
    """
    Mock EmailService for testing without sending real emails.

    Uses monkeypatch to replace email sending methods with mocks
    that return success without actually sending emails.

    Args:
        monkeypatch: Pytest monkeypatch fixture

    Returns:
        Mock EmailService that returns True for all operations
    """
    from unittest.mock import AsyncMock, MagicMock

    from ardha.core.email_service import EmailService

    # Create mock instance
    mock_service = MagicMock(spec=EmailService)

    # Mock async methods to return success
    mock_service.send_notification_email = AsyncMock(return_value=True)
    mock_service.send_digest_email = AsyncMock(return_value=True)

    # Patch the EmailService class
    monkeypatch.setattr(
        "ardha.services.notification_service.EmailService",
        lambda: mock_service,
    )

    return mock_service


@pytest.fixture
async def websocket_client():
    """
    Create WebSocket test client helper.

    Provides utilities for WebSocket testing including:
    - Connection management
    - Message sending/receiving
    - Authentication token handling

    Returns:
        WebSocketTestClient instance for testing WebSocket endpoints
    """

    class WebSocketTestClient:
        """Helper class for WebSocket testing."""

        def __init__(self):
            self.websocket = None
            self.connected = False
            self.received_messages = []

        async def connect(self, client, url: str, token: str):
            """
            Connect to WebSocket endpoint.

            Args:
                client: FastAPI test client
                url: WebSocket URL
                token: JWT authentication token
            """
            self.websocket = client.websocket_connect(f"{url}?token={token}")
            self.connected = True
            return self.websocket

        async def send_json(self, data: Dict):
            """
            Send JSON message to WebSocket.

            Args:
                data: Message data to send
            """
            if not self.websocket:
                raise RuntimeError("Not connected")

            await self.websocket.send_json(data)

        async def receive_json(self) -> Dict:
            """
            Receive JSON message from WebSocket.

            Returns:
                Received message data
            """
            if not self.websocket:
                raise RuntimeError("Not connected")

            message = await self.websocket.receive_json()
            self.received_messages.append(message)
            return message

        async def close(self):
            """Close WebSocket connection."""
            if self.websocket and self.connected:
                await self.websocket.close()
                self.connected = False

    return WebSocketTestClient()
