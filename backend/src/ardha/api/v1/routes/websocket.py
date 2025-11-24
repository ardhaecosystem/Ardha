"""
WebSocket API routes for real-time notifications.

This module provides WebSocket endpoints for real-time communication including:
- Real-time notification delivery
- Ping/pong keepalive mechanism
- JWT token authentication
- Connection management and cleanup
"""

import logging
from uuid import UUID

from fastapi import APIRouter, Depends, Query, WebSocket, WebSocketDisconnect
from sqlalchemy.ext.asyncio import AsyncSession

from ardha.core.database import get_db
from ardha.core.security import decode_token
from ardha.core.websocket_manager import get_websocket_manager

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ws", tags=["websocket"])


# ============= WebSocket Endpoints =============


@router.websocket("/notifications")
async def notification_websocket(
    websocket: WebSocket,
    token: str = Query(..., description="JWT authentication token"),
    db: AsyncSession = Depends(get_db),
):
    """
    WebSocket endpoint for real-time notifications.

    Authentication:
        token: JWT token as query parameter (e.g., ?token=eyJ...)

    Message Types Received:
        - {"type": "ping"} → responds with {"type": "pong"}

    Message Types Sent:
        - {"type": "notification", "data": {...}} - New notification
        - {"type": "system", "data": {...}} - System message
        - {"type": "error", "data": {...}} - Error message

    Connection Flow:
        1. Validate JWT token
        2. Accept WebSocket connection
        3. Register with WebSocketManager
        4. Listen for incoming messages
        5. Handle ping/pong for keepalive
        6. Disconnect and cleanup on close

    Args:
        websocket: FastAPI WebSocket connection
        token: JWT authentication token
        db: Database session (for future use if needed)

    Raises:
        WebSocketDisconnect: When connection is closed
    """
    ws_manager = get_websocket_manager()
    user_id = None

    try:
        # Step 1: Validate JWT token
        try:
            payload = decode_token(token)
            user_id = UUID(payload.get("sub"))

            if not user_id:
                await websocket.close(code=1008, reason="Invalid token: missing user ID")
                return

        except Exception as e:
            logger.warning(f"WebSocket authentication failed: {e}")
            await websocket.close(code=1008, reason="Authentication failed")
            return

        # Step 2-3: Accept connection and register with manager
        await ws_manager.connect(websocket, user_id)

        logger.info(f"User {user_id} connected to notification WebSocket")

        # Step 4: Listen for messages
        try:
            while True:
                # Receive message from client
                data = await websocket.receive_json()

                # Handle ping/pong for keepalive
                if data.get("type") == "ping":
                    await websocket.send_json({"type": "pong"})
                    logger.debug(f"Responded to ping from user {user_id}")

                # Log any other message types (for debugging)
                else:
                    logger.debug(f"Received message from user {user_id}: {data.get('type')}")

        except WebSocketDisconnect:
            logger.info(f"User {user_id} disconnected from notification WebSocket")

    except Exception as e:
        logger.error(f"WebSocket error for user {user_id}: {e}", exc_info=True)

        # Try to send error message if connection still open
        try:
            await websocket.send_json(
                {
                    "type": "error",
                    "data": {
                        "message": "An error occurred",
                        "details": str(e),
                    },
                }
            )
        except Exception:
            pass  # Connection likely already closed

    finally:
        # Step 6: Cleanup
        if user_id:
            await ws_manager.disconnect(websocket, user_id)
            logger.info(f"Cleaned up WebSocket connection for user {user_id}")
