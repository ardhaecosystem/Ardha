"""
WebSocket routes for real-time chat streaming.

This module provides WebSocket endpoints for real-time chat interactions,
including authentication, message handling, and streaming responses.
"""

import json
import logging
from typing import Dict, Optional, Set
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, WebSocket, WebSocketDisconnect
from sqlalchemy.ext.asyncio import AsyncSession

from ardha.core.database import get_db
from ardha.core.security import verify_token
from ardha.models.user import User
from ardha.services.chat_service import (
    ChatBudgetExceededError,
    ChatNotFoundError,
    ChatService,
    InsufficientChatPermissionsError,
)

logger = logging.getLogger(__name__)

router = APIRouter()

# Store active WebSocket connections
active_connections: Dict[UUID, Set[WebSocket]] = {}


class WebSocketManager:
    """Manages WebSocket connections for chat rooms."""

    @staticmethod
    async def connect(websocket: WebSocket, chat_id: UUID) -> None:
        """Connect a WebSocket to a chat room."""
        await websocket.accept()

        if chat_id not in active_connections:
            active_connections[chat_id] = set()

        active_connections[chat_id].add(websocket)
        logger.info(
            f"WebSocket connected to chat {chat_id}. Total connections: {len(active_connections[chat_id])}"
        )

    @staticmethod
    async def disconnect(websocket: WebSocket, chat_id: UUID) -> None:
        """Disconnect a WebSocket from a chat room."""
        if chat_id in active_connections:
            active_connections[chat_id].discard(websocket)

            # Clean up empty chat rooms
            if not active_connections[chat_id]:
                del active_connections[chat_id]

        logger.info(f"WebSocket disconnected from chat {chat_id}")

    @staticmethod
    async def send_personal_message(message: str, websocket: WebSocket) -> None:
        """Send a message to a specific WebSocket."""
        try:
            await websocket.send_text(message)
        except Exception as e:
            logger.error(f"Error sending personal message: {e}")

    @staticmethod
    async def broadcast_to_chat(
        message: str, chat_id: UUID, exclude_websocket: Optional[WebSocket] = None
    ) -> None:
        """Broadcast a message to all connections in a chat room."""
        if chat_id not in active_connections:
            return

        disconnected = set()
        for connection in active_connections[chat_id]:
            if connection == exclude_websocket:
                continue

            try:
                await connection.send_text(message)
            except Exception as e:
                logger.error(f"Error broadcasting to connection: {e}")
                disconnected.add(connection)

        # Remove disconnected connections
        for connection in disconnected:
            active_connections[chat_id].discard(connection)


@router.websocket("/chats/{chat_id}/ws")
async def chat_websocket(
    websocket: WebSocket,
    chat_id: UUID,
    token: str = Query(..., description="JWT authentication token"),
    db: AsyncSession = Depends(get_db),
) -> None:
    """
    WebSocket endpoint for real-time chat streaming.

    Provides real-time bidirectional communication for chat sessions.
    Authenticates via JWT token query parameter.

    Args:
        websocket: WebSocket connection instance
        chat_id: UUID of chat to connect to
        token: JWT authentication token
        db: Database session

    WebSocket Messages:
        Receive: {"type": "message", "content": "...", "model": "..."}
        Send: {"type": "chunk", "content": "..."}
        Send: {"type": "done", "message_id": "...", "tokens": ..., "cost": ...}
        Send: {"type": "error", "message": "..."}

    Raises:
        403: Invalid token or insufficient permissions
        404: Chat not found
        500: Server error
    """
    logger.info(f"WebSocket connection attempt to chat {chat_id}")

    try:
        # Authenticate token
        payload = verify_token(token)
        if not payload:
            await websocket.close(code=4003, reason="Invalid authentication token")
            return

        # Initialize chat service
        chat_service = ChatService(db)

        # Extract user ID from token
        try:
            from uuid import UUID

            user_id = UUID(payload.get("sub"))
        except (ValueError, TypeError):
            await websocket.close(code=4003, reason="Invalid token format")
            return

        # Verify chat exists and user has access
        chat = await chat_service.chat_repo.get_by_id(chat_id)
        if not chat:
            await websocket.close(code=4004, reason="Chat not found")
            return

        if chat.user_id != user_id:
            await websocket.close(code=4003, reason="Insufficient permissions")
            return

        # Connect to chat room
        await WebSocketManager.connect(websocket, chat_id)

        try:
            while True:
                # Receive message from client
                data = await websocket.receive_text()

                try:
                    message = json.loads(data)
                    message_type = message.get("type")

                    if message_type == "message":
                        content = message.get("content", "").strip()
                        model = message.get("model", "").strip()

                        # Validate message
                        if not content:
                            error_msg = json.dumps(
                                {"type": "error", "message": "Message content cannot be empty"}
                            )
                            await WebSocketManager.send_personal_message(error_msg, websocket)
                            continue

                        if not model:
                            error_msg = json.dumps(
                                {"type": "error", "message": "Model is required"}
                            )
                            await WebSocketManager.send_personal_message(error_msg, websocket)
                            continue

                        # Send user message confirmation
                        confirmation = json.dumps(
                            {
                                "type": "message_received",
                                "content": content,
                                "timestamp": str(
                                    websocket.scope.get("state", {}).get("receive_time", "")
                                ),
                            }
                        )
                        await WebSocketManager.send_personal_message(confirmation, websocket)

                        # Stream AI response
                        try:
                            full_response = ""
                            message_id = None
                            total_tokens = 0
                            total_cost = 0.0

                            async for chunk in chat_service.send_message(
                                chat_id=chat_id,
                                user_id=user_id,
                                content=content,
                                model=model,
                            ):
                                # Send chunk to all connections in chat room
                                chunk_msg = json.dumps({"type": "chunk", "content": chunk})
                                await WebSocketManager.broadcast_to_chat(
                                    chunk_msg, chat_id, websocket
                                )
                                full_response += chunk

                            # Send completion message
                            completion_msg = json.dumps(
                                {
                                    "type": "done",
                                    "message_id": str(message_id) if message_id else None,
                                    "tokens": total_tokens,
                                    "cost": total_cost,
                                }
                            )
                            await WebSocketManager.broadcast_to_chat(completion_msg, chat_id)

                        except (ChatNotFoundError, InsufficientChatPermissionsError) as e:
                            error_msg = json.dumps({"type": "error", "message": str(e)})
                            await WebSocketManager.send_personal_message(error_msg, websocket)

                        except ChatBudgetExceededError as e:
                            error_msg = json.dumps({"type": "error", "message": str(e)})
                            await WebSocketManager.send_personal_message(error_msg, websocket)

                        except Exception as e:
                            logger.error(f"Error processing message: {e}", exc_info=True)
                            error_msg = json.dumps(
                                {"type": "error", "message": "Internal server error"}
                            )
                            await WebSocketManager.send_personal_message(error_msg, websocket)

                    else:
                        # Unknown message type
                        error_msg = json.dumps(
                            {"type": "error", "message": f"Unknown message type: {message_type}"}
                        )
                        await WebSocketManager.send_personal_message(error_msg, websocket)

                except json.JSONDecodeError:
                    error_msg = json.dumps({"type": "error", "message": "Invalid JSON format"})
                    await WebSocketManager.send_personal_message(error_msg, websocket)

                except Exception as e:
                    logger.error(f"Error processing WebSocket message: {e}", exc_info=True)
                    error_msg = json.dumps({"type": "error", "message": "Error processing message"})
                    await WebSocketManager.send_personal_message(error_msg, websocket)

        except WebSocketDisconnect:
            logger.info(f"WebSocket disconnected from chat {chat_id}")
        finally:
            await WebSocketManager.disconnect(websocket, chat_id)

    except Exception as e:
        logger.error(f"WebSocket error for chat {chat_id}: {e}", exc_info=True)
        try:
            await websocket.close(code=5000, reason="Internal server error")
        except:
            pass
