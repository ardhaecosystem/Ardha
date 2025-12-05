"""
Chat API routes for Ardha application.

This module provides REST API endpoints for chat operations including
creating chats, sending messages, retrieving history, and managing chats.
"""

import logging
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from ardha.core.database import get_db
from ardha.core.rate_limit import check_chat_rate_limit
from ardha.core.security import get_current_user
from ardha.models.user import User
from ardha.schemas.requests.chat import CreateChatRequest, MessageSendRequest
from ardha.schemas.responses.chat import ChatResponse, ChatSummaryResponse, MessageResponse
from ardha.services.chat_service import (
    ChatBudgetExceededError,
    ChatNotFoundError,
    ChatService,
    InsufficientChatPermissionsError,
    InvalidChatModeError,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/chats", tags=["chats"])


@router.post("/", response_model=ChatResponse)
async def create_chat(
    request: CreateChatRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ChatResponse:
    """
    Create a new chat session.

    Creates a new chat with the specified mode and optional project association.
    Adds a system message based on the chat mode.

    Args:
        request: Chat creation request with mode and optional project_id
        current_user: Authenticated user making the request
        db: Database session

    Returns:
        Created chat information

    Raises:
        400: Invalid chat mode or insufficient permissions
        404: Project not found
        500: Database error
    """
    logger.info(f"Creating chat for user {current_user.id} with mode {request.mode}")

    try:
        chat_service = ChatService(db)
        chat = await chat_service.create_chat(
            user_id=current_user.id,
            mode=request.mode,
            project_id=request.project_id,
        )

        return ChatResponse(
            id=chat.id,
            title=chat.title,
            mode=chat.mode.value if hasattr(chat.mode, "value") else chat.mode,
            created_at=chat.created_at,
            updated_at=chat.updated_at,
            is_archived=chat.is_archived,
            project_id=chat.project_id,
            total_tokens=chat.total_tokens,
            total_cost=float(chat.total_cost),
        )

    except InvalidChatModeError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except InsufficientChatPermissionsError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except Exception as e:
        logger.error(f"Error creating chat: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/{chat_id}/messages")
async def send_message(
    chat_id: UUID,
    request: MessageSendRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    _: None = Depends(check_chat_rate_limit),
) -> StreamingResponse:
    """
    Send a message and stream AI response.

    Adds user message to chat and streams AI response in real-time.
    Supports different AI models and tracks tokens/cost.

    Args:
        chat_id: UUID of chat
        request: Message send request with content and model
        current_user: Authenticated user making the request
        db: Database session

    Returns:
        Streaming response with AI-generated content

    Raises:
        400: Invalid request data
        403: Insufficient permissions or budget exceeded
        404: Chat not found
        500: Database or AI service error
    """
    logger.info(
        f"[ROUTE] Sending message to chat {chat_id} from user {current_user.id}, model: {request.model}"
    )

    try:
        chat_service = ChatService(db)

        async def generate_response():
            logger.info(f"[ROUTE] Starting stream generation for chat {chat_id}")
            chunk_count = 0
            try:
                async for chunk in chat_service.send_message(
                    chat_id=chat_id,
                    user_id=current_user.id,
                    content=request.content,
                    model=request.model,
                ):
                    chunk_count += 1
                    logger.debug(
                        f"[ROUTE] Yielding chunk #{chunk_count}: {chunk[:50] if len(chunk) > 50 else chunk}"
                    )
                    yield f"data: {chunk}\n\n"
                logger.info(f"[ROUTE] Stream completed, total chunks: {chunk_count}")
                yield "data: [DONE]\n\n"
            except Exception as e:
                logger.error(f"[ROUTE] Error in stream generation: {e}", exc_info=True)
                yield f'data: {{"error": "{str(e)}"}}\n\n'
                yield "data: [DONE]\n\n"

        return StreamingResponse(
            generate_response(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "Access-Control-Allow-Origin": "*",
            },
        )

    except (ChatNotFoundError, InsufficientChatPermissionsError, ChatBudgetExceededError) as e:
        logger.error(f"[ROUTE] Permissions/budget error: {e}")
        raise HTTPException(
            status_code=(
                403
                if isinstance(e, (InsufficientChatPermissionsError, ChatBudgetExceededError))
                else 404
            ),
            detail=str(e),
        )
    except Exception as e:
        logger.error(f"[ROUTE] Error sending message: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/{chat_id}/history", response_model=List[MessageResponse])
async def get_chat_history(
    chat_id: UUID,
    skip: int = Query(0, ge=0, description="Number of messages to skip"),
    limit: int = Query(100, ge=1, le=100, description="Maximum number of messages to return"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> List[MessageResponse]:
    """
    Get paginated chat history.

    Returns messages for a specific chat with pagination.
    Verifies user owns the chat before returning history.

    Args:
        chat_id: UUID of chat
        skip: Number of messages to skip (pagination)
        limit: Maximum number of messages to return
        current_user: Authenticated user making the request
        db: Database session

    Returns:
        List of messages in chronological order

    Raises:
        400: Invalid pagination parameters
        403: Insufficient permissions
        404: Chat not found
        500: Database error
    """
    logger.info(f"Getting history for chat {chat_id} for user {current_user.id}")

    try:
        chat_service = ChatService(db)
        messages = await chat_service.get_chat_history(
            chat_id=chat_id,
            user_id=current_user.id,
            skip=skip,
            limit=limit,
        )

        return [
            MessageResponse(
                id=msg.id,
                role=(
                    msg.role.value if hasattr(msg.role, "value") else msg.role
                ),  # Handle both enum and string
                content=msg.content,
                created_at=msg.created_at,
                ai_model=msg.model_used,  # Use ai_model field name (matches MessageResponse schema)
                tokens_input=msg.tokens_input,
                tokens_output=msg.tokens_output,
                cost=float(msg.cost) if msg.cost else None,
                message_metadata=msg.message_metadata,
            )
            for msg in messages
        ]

    except (ChatNotFoundError, InsufficientChatPermissionsError) as e:
        raise HTTPException(
            status_code=403 if isinstance(e, InsufficientChatPermissionsError) else 404,
            detail=str(e),
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error getting chat history: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/", response_model=List[ChatResponse])
async def get_user_chats(
    project_id: Optional[UUID] = Query(None, description="Filter by project ID"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> List[ChatResponse]:
    """
    Get user's chats, optionally filtered by project.

    Returns non-archived chats for the authenticated user.
    Can be filtered to a specific project.

    Args:
        project_id: Optional UUID to filter by project
        current_user: Authenticated user making the request
        db: Database session

    Returns:
        List of chats ordered by most recent first

    Raises:
        500: Database error
    """
    logger.info(f"Getting chats for user {current_user.id}, project filter: {project_id}")

    try:
        chat_service = ChatService(db)
        chats = await chat_service.get_user_chats(
            user_id=current_user.id,
            project_id=project_id,
        )

        return [
            ChatResponse(
                id=chat.id,
                title=chat.title,
                mode=chat.mode.value if hasattr(chat.mode, "value") else chat.mode,
                created_at=chat.created_at,
                updated_at=chat.updated_at,
                is_archived=chat.is_archived,
                project_id=chat.project_id,
                total_tokens=chat.total_tokens,
                total_cost=float(chat.total_cost),
            )
            for chat in chats
        ]

    except Exception as e:
        logger.error(f"Error getting user chats: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/{chat_id}", response_model=ChatSummaryResponse)
async def get_chat_summary(
    chat_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ChatSummaryResponse:
    """
    Get comprehensive chat summary.

    Returns detailed information about a chat including
    message counts, token statistics, and recent messages.

    Args:
        chat_id: UUID of chat
        current_user: Authenticated user making the request
        db: Database session

    Returns:
        Comprehensive chat summary

    Raises:
        403: Insufficient permissions
        404: Chat not found
        500: Database error
    """
    logger.info(f"Getting summary for chat {chat_id} for user {current_user.id}")

    try:
        chat_service = ChatService(db)
        summary = await chat_service.get_chat_summary(
            chat_id=chat_id,
            user_id=current_user.id,
        )

        return ChatSummaryResponse(**summary)

    except (ChatNotFoundError, InsufficientChatPermissionsError) as e:
        raise HTTPException(
            status_code=403 if isinstance(e, InsufficientChatPermissionsError) else 404,
            detail=str(e),
        )
    except Exception as e:
        logger.error(f"Error getting chat summary: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/{chat_id}/archive", response_model=ChatResponse)
async def archive_chat(
    chat_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ChatResponse:
    """
    Archive a chat (soft delete).

    Archives a chat to hide it from default views.
    Chat data is preserved and can be restored later.

    Args:
        chat_id: UUID of chat to archive
        current_user: Authenticated user making the request
        db: Database session

    Returns:
        Updated chat information with is_archived=True

    Raises:
        403: Insufficient permissions
        404: Chat not found
        500: Database error
    """
    logger.info(f"Archiving chat {chat_id} for user {current_user.id}")

    try:
        chat_service = ChatService(db)
        chat = await chat_service.archive_chat(
            chat_id=chat_id,
            user_id=current_user.id,
        )

        return ChatResponse(
            id=chat.id,
            title=chat.title,
            mode=chat.mode.value if hasattr(chat.mode, "value") else chat.mode,
            created_at=chat.created_at,
            updated_at=chat.updated_at,
            is_archived=chat.is_archived,
            project_id=chat.project_id,
            total_tokens=chat.total_tokens,
            total_cost=float(chat.total_cost),
        )

    except (ChatNotFoundError, InsufficientChatPermissionsError) as e:
        raise HTTPException(
            status_code=403 if isinstance(e, InsufficientChatPermissionsError) else 404,
            detail=str(e),
        )
    except Exception as e:
        logger.error(f"Error archiving chat: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@router.delete("/{chat_id}")
async def delete_chat(
    chat_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    """
    Delete a chat (hard delete).

    Permanently removes chat and all associated messages.
    Use archive_chat() for soft delete to preserve data.

    Args:
        chat_id: UUID of chat to delete
        current_user: Authenticated user making request
        db: Database session

    Returns:
        204 No Content on successful deletion

    Raises:
        403: Insufficient permissions
        404: Chat not found
        500: Database error
    """
    logger.info(f"Deleting chat {chat_id} for user {current_user.id}")

    try:
        chat_service = ChatService(db)

        # Verify ownership first
        chat = await chat_service.chat_repo.get_by_id(chat_id)
        if not chat:
            raise HTTPException(status_code=404, detail="Chat not found")

        if chat.user_id != current_user.id:
            raise HTTPException(status_code=403, detail="Insufficient permissions")

        # Delete the chat (cascade will delete messages)
        await chat_service.chat_repo.delete(chat_id)

        return None

    except HTTPException:
        # Re-raise HTTP exceptions as-is
        raise
    except Exception as e:
        logger.error(f"Error deleting chat: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")
