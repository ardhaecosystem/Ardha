"""
WebSocket connection manager for real-time notifications.

This module provides a singleton WebSocketManager class that handles:
- WebSocket connection pooling per user
- Room-based broadcasting (user rooms, project rooms)
- Thread-safe connection management
- Real-time message delivery
"""

import asyncio
import json
import logging
from typing import Any, Dict, List, Optional, Set
from uuid import UUID

from fastapi import WebSocket, WebSocketDisconnect

logger = logging.getLogger(__name__)


class WebSocketManager:
    """
    Manage WebSocket connections for real-time updates.

    Implements singleton pattern to ensure single instance manages
    all connections. Provides user-based connection pooling and
    room-based broadcasting for group notifications.

    Attributes:
        active_connections: Dict mapping user_id to list of WebSocket connections
        rooms: Dict mapping room_id to set of user_ids
        _lock: Async lock for thread-safe operations
    """

    _instance: Optional["WebSocketManager"] = None
    _initialized: bool = False

    def __new__(cls) -> "WebSocketManager":
        """
        Ensure only one instance exists (singleton pattern).

        Returns:
            The singleton WebSocketManager instance
        """
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self) -> None:
        """Initialize WebSocketManager with connection pools and rooms."""
        if self._initialized:
            return

        # Connection pool: user_id -> [WebSocket connections]
        self.active_connections: Dict[UUID, List[WebSocket]] = {}

        # Room management: room_id -> {user_ids}
        self.rooms: Dict[str, Set[UUID]] = {}

        # Lock for thread-safe operations
        self._lock: asyncio.Lock = asyncio.Lock()

        self._initialized = True
        logger.info("WebSocketManager initialized as singleton")

    # ============= Connection Management =============

    async def connect(self, websocket: WebSocket, user_id: UUID) -> None:
        """
        Accept WebSocket connection and add to pool.

        Args:
            websocket: FastAPI WebSocket instance
            user_id: UUID of user connecting

        Raises:
            RuntimeError: If WebSocket already accepted
        """
        try:
            await websocket.accept()

            async with self._lock:
                # Initialize user's connection list if first connection
                if user_id not in self.active_connections:
                    self.active_connections[user_id] = []

                # Add connection to pool
                self.active_connections[user_id].append(websocket)

                # Auto-join user's personal room
                room_id = f"user:{user_id}"
                await self._join_room_unsafe(user_id, room_id)

            # Send connection confirmation
            await self.send_to_connection(
                websocket,
                {
                    "type": "system",
                    "data": {
                        "message": "Connected successfully",
                        "user_id": str(user_id),
                        "timestamp": self._get_timestamp(),
                    },
                },
            )

            connection_count = len(self.active_connections[user_id])
            logger.info(
                f"User {user_id} connected via WebSocket "
                f"(total connections: {connection_count})"
            )

        except Exception as e:
            logger.error(f"Error accepting WebSocket connection for user {user_id}: {e}")
            raise

    async def disconnect(self, websocket: WebSocket, user_id: UUID) -> None:
        """
        Remove WebSocket connection from pool.

        Args:
            websocket: FastAPI WebSocket instance to remove
            user_id: UUID of user disconnecting
        """
        async with self._lock:
            if user_id in self.active_connections:
                # Remove specific connection
                if websocket in self.active_connections[user_id]:
                    self.active_connections[user_id].remove(websocket)

                # If no more connections, remove user from pool and all rooms
                if not self.active_connections[user_id]:
                    del self.active_connections[user_id]

                    # Remove from all rooms
                    for room_id in list(self.rooms.keys()):
                        if user_id in self.rooms[room_id]:
                            self.rooms[room_id].discard(user_id)
                            # Remove empty rooms
                            if not self.rooms[room_id]:
                                del self.rooms[room_id]

        # Close connection gracefully
        try:
            await websocket.close()
        except Exception as e:
            logger.debug(f"Error closing WebSocket for user {user_id}: {e}")

        remaining_connections = len(self.active_connections.get(user_id, []))
        logger.info(
            f"User {user_id} disconnected from WebSocket "
            f"(remaining connections: {remaining_connections})"
        )

    async def is_user_connected(self, user_id: UUID) -> bool:
        """
        Check if user has any active connections.

        Args:
            user_id: UUID of user to check

        Returns:
            True if user has at least one active connection
        """
        async with self._lock:
            return user_id in self.active_connections and len(self.active_connections[user_id]) > 0

    async def get_user_connections(self, user_id: UUID) -> List[WebSocket]:
        """
        Get all active connections for user.

        Args:
            user_id: UUID of user

        Returns:
            List of WebSocket connections (empty if user not connected)
        """
        async with self._lock:
            return self.active_connections.get(user_id, []).copy()

    # ============= Messaging =============

    async def send_personal_message(self, user_id: UUID, message: Dict[str, Any]) -> bool:
        """
        Send message to specific user (all their connections).

        Args:
            user_id: UUID of user to send message to
            message: Message data dictionary

        Returns:
            True if message sent to at least one connection, False otherwise
        """
        connections = await self.get_user_connections(user_id)

        if not connections:
            logger.debug(f"User {user_id} has no active connections")
            return False

        success_count = 0
        for ws in connections:
            if await self.send_to_connection(ws, message):
                success_count += 1

        logger.debug(
            f"Sent personal message to user {user_id}: "
            f"{success_count}/{len(connections)} successful"
        )

        return success_count > 0

    async def send_to_connection(self, websocket: WebSocket, message: Dict[str, Any]) -> bool:
        """
        Send message to specific WebSocket connection.

        Args:
            websocket: WebSocket connection
            message: Message data dictionary

        Returns:
            True if message sent successfully, False otherwise
        """
        try:
            # Serialize message to JSON
            message_json = json.dumps(message, default=str)
            await websocket.send_text(message_json)
            return True

        except WebSocketDisconnect:
            logger.debug("WebSocket disconnected during send")
            return False

        except Exception as e:
            logger.error(f"Error sending WebSocket message: {e}")
            return False

    async def broadcast_to_room(
        self, room_id: str, message: Dict[str, Any], exclude_user: Optional[UUID] = None
    ) -> int:
        """
        Broadcast message to all users in room.

        Args:
            room_id: Room identifier
            message: Message data dictionary
            exclude_user: Optional user_id to exclude from broadcast

        Returns:
            Number of users successfully reached
        """
        users_in_room = await self.get_room_users(room_id)

        if not users_in_room:
            logger.debug(f"Room {room_id} has no users")
            return 0

        success_count = 0
        for user_id in users_in_room:
            if exclude_user and user_id == exclude_user:
                continue

            if await self.send_personal_message(user_id, message):
                success_count += 1

        logger.debug(
            f"Broadcast to room {room_id}: " f"{success_count}/{len(users_in_room)} users reached"
        )

        return success_count

    # ============= Room Management =============

    async def join_room(self, user_id: UUID, room_id: str) -> None:
        """
        Add user to room.

        Args:
            user_id: UUID of user
            room_id: Room identifier (e.g., "project:uuid", "user:uuid")
        """
        async with self._lock:
            await self._join_room_unsafe(user_id, room_id)

    async def _join_room_unsafe(self, user_id: UUID, room_id: str) -> None:
        """
        Add user to room without lock (internal use only).

        Args:
            user_id: UUID of user
            room_id: Room identifier
        """
        if room_id not in self.rooms:
            self.rooms[room_id] = set()

        self.rooms[room_id].add(user_id)
        logger.debug(f"User {user_id} joined room {room_id}")

    async def leave_room(self, user_id: UUID, room_id: str) -> None:
        """
        Remove user from room.

        Args:
            user_id: UUID of user
            room_id: Room identifier
        """
        async with self._lock:
            if room_id in self.rooms:
                self.rooms[room_id].discard(user_id)

                # Remove empty rooms
                if not self.rooms[room_id]:
                    del self.rooms[room_id]

                logger.debug(f"User {user_id} left room {room_id}")

    async def get_room_users(self, room_id: str) -> Set[UUID]:
        """
        Get all user IDs in room.

        Args:
            room_id: Room identifier

        Returns:
            Set of user UUIDs in room (empty set if room doesn't exist)
        """
        async with self._lock:
            return self.rooms.get(room_id, set()).copy()

    # ============= Utility Methods =============

    def _get_timestamp(self) -> str:
        """
        Get current timestamp in ISO format.

        Returns:
            ISO formatted timestamp string
        """
        from datetime import datetime, timezone

        return datetime.now(timezone.utc).isoformat()

    async def get_connection_stats(self) -> Dict[str, Any]:
        """
        Get connection statistics.

        Returns:
            Dictionary with connection stats
        """
        async with self._lock:
            return {
                "total_users": len(self.active_connections),
                "total_connections": sum(len(conns) for conns in self.active_connections.values()),
                "total_rooms": len(self.rooms),
                "users_per_room": {room_id: len(users) for room_id, users in self.rooms.items()},
            }


# ============= Singleton Access =============

_manager_instance: Optional[WebSocketManager] = None


def get_websocket_manager() -> WebSocketManager:
    """
    Get WebSocketManager singleton instance.

    Returns:
        The singleton WebSocketManager instance
    """
    global _manager_instance
    if _manager_instance is None:
        _manager_instance = WebSocketManager()
    return _manager_instance
