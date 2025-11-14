"""
Chat service for AI-powered conversations.

This module provides business logic for chat operations including
message handling, AI integration via OpenRouter, and cost tracking.
"""

import logging
from datetime import date
from decimal import Decimal
from typing import AsyncGenerator, Dict, List, Optional
from uuid import UUID

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from ardha.core.openrouter import CircuitBreakerOpenError, OpenRouterError
from ardha.models.ai_usage import AIOperation
from ardha.models.chat import Chat, ChatMode
from ardha.models.message import Message, MessageRole
from ardha.repositories.ai_usage_repository import AIUsageRepository
from ardha.repositories.chat_repository import ChatRepository
from ardha.repositories.message_repository import MessageRepository
from ardha.repositories.project_repository import ProjectRepository
from ardha.services.project_service import InsufficientPermissionsError, ProjectService

logger = logging.getLogger(__name__)

# System message templates for different AI modes
SYSTEM_MESSAGES = {
    ChatMode.RESEARCH: """You are a research assistant. Your role is to help users conduct
    thorough research, analyze information, and provide well-structured insights. You should:
- Ask clarifying questions to understand research needs
- Provide comprehensive, evidence-based responses
- Cite sources and reference materials when relevant
- Suggest additional research directions
- Maintain objectivity and avoid bias
- Structure information clearly with headings and bullet points""",
    ChatMode.ARCHITECT: """You are a software architect. Your role is to help design
    robust, scalable systems and make architectural decisions. You should:
- Analyze requirements and constraints thoroughly
- Consider scalability, performance, and maintainability
- Suggest appropriate technologies and patterns
- Identify potential risks and trade-offs
- Provide clear architectural diagrams and explanations
- Consider security, reliability, and cost implications
- Recommend best practices and industry standards""",
    ChatMode.IMPLEMENT: """You are an expert developer. Your role is to help write
    high-quality, production-ready code. You should:
- Write clean, well-documented, and maintainable code
- Follow established patterns and best practices
- Consider error handling and edge cases
- Optimize for performance and readability
- Include relevant tests when appropriate
- Explain complex logic and design decisions
- Suggest improvements and optimizations""",
    ChatMode.DEBUG: """You are a debugging expert. Your role is to help identify, analyze,
    and resolve issues in code and systems. You should:
- Systematically analyze problems and symptoms
- Identify root causes and contributing factors
- Provide step-by-step debugging approaches
- Suggest diagnostic tools and techniques
- Explain technical concepts clearly
- Recommend preventive measures
- Help verify fixes and solutions""",
    ChatMode.CHAT: """You are a helpful AI assistant. Your role is to provide accurate, thoughtful, and useful responses to user questions. You should:
- Understand the user's intent and context
- Provide clear, concise, and accurate information
- Ask follow-up questions when needed
- Admit uncertainty and suggest verification
- Maintain a helpful and professional tone
- Structure responses for maximum clarity""",
}


class ChatNotFoundError(Exception):
    """Raised when chat is not found."""

    pass


class InsufficientChatPermissionsError(Exception):
    """Raised when user lacks permissions for chat operations."""

    pass


class ChatBudgetExceededError(Exception):
    """Raised when chat budget is exceeded."""

    pass


class InvalidChatModeError(Exception):
    """Raised when invalid chat mode is provided."""

    pass


class ChatService:
    """
    Service for chat management and AI integration.

    Handles chat creation, message processing, AI interactions via OpenRouter,
    cost tracking, and permission enforcement. Integrates with project
    management for project-specific chats.

    Attributes:
        db: SQLAlchemy async session
        chat_repo: Chat repository for data access
        message_repo: Message repository for data access
        ai_usage_repo: AI usage repository for tracking
        project_service: Project service for permission checks
    """

    def __init__(self, db: AsyncSession) -> None:
        """
        Initialize ChatService with database session and repositories.

        Args:
            db: SQLAlchemy async session for database operations
        """
        self.db = db
        self.chat_repo = ChatRepository(db)
        self.message_repo = MessageRepository(db)
        self.ai_usage_repo = AIUsageRepository(db)
        self.project_repo = ProjectRepository(db)
        self.project_service = ProjectService(db)

    async def create_chat(
        self,
        user_id: UUID,
        mode: str,
        project_id: Optional[UUID] = None,
    ) -> Chat:
        """
        Create a new chat session.

        Validates user has access to project (if project_id), creates chat
        with initial system message based on mode, and generates title.

        Args:
            user_id: UUID of user creating chat
            mode: Chat mode (research, architect, implement, debug, chat)
            project_id: UUID of associated project (optional for personal chats)

        Returns:
            Created Chat object with system message and auto-generated title

        Raises:
            InvalidChatModeError: If mode is invalid
            InsufficientPermissionsError: If user lacks project access
            ProjectNotFoundError: If project doesn't exist
            SQLAlchemyError: If database operation fails
        """
        logger.info(f"Creating chat for user {user_id} with mode {mode}")

        # Validate mode
        try:
            chat_mode = ChatMode(mode)
        except ValueError:
            raise InvalidChatModeError(
                f"Invalid mode: {mode}. Must be one of: {[m.value for m in ChatMode]}"
            )

        # Check project permissions if project_id provided
        if project_id:
            if not await self.project_service.check_permission(project_id, user_id, "viewer"):
                raise InsufficientPermissionsError(
                    f"User {user_id} lacks access to project {project_id}"
                )

        try:
            # Create chat with temporary title
            chat = await self.chat_repo.create(
                user_id=user_id,
                mode=mode,
                project_id=project_id,
                title="New Chat",  # Will be updated after first message
            )

            # Add system message
            system_message = SYSTEM_MESSAGES[chat_mode]
            await self.message_repo.create(
                chat_id=chat.id,
                role=MessageRole.SYSTEM,
                content=system_message,
            )

            logger.info(f"Created chat {chat.id} with mode {mode}")
            return chat

        except SQLAlchemyError as e:
            logger.error(f"Error creating chat: {e}", exc_info=True)
            raise

    async def send_message(
        self,
        chat_id: UUID,
        user_id: UUID,
        content: str,
        model: str,
    ) -> AsyncGenerator[str, None]:
        """
        Send a message and stream AI response.

        Verifies user owns chat, adds user message, prepares context,
        calls OpenRouter with streaming, yields chunks, and saves response.

        Args:
            chat_id: UUID of chat
            user_id: UUID of user sending message
            content: Message content
            model: AI model to use for response

        Yields:
            Response chunks as they arrive from OpenRouter

        Raises:
            ChatNotFoundError: If chat doesn't exist
            InsufficientChatPermissionsError: If user doesn't own chat
            ChatBudgetExceededError: If chat budget exceeded
            OpenRouterError: If AI service fails
            SQLAlchemyError: If database operation fails
        """
        logger.info(f"Sending message to chat {chat_id} from user {user_id}")

        # Verify chat ownership
        chat = await self.chat_repo.get_by_id(chat_id)
        if not chat:
            raise ChatNotFoundError(f"Chat {chat_id} not found")

        if chat.user_id != user_id:
            raise InsufficientChatPermissionsError(f"User {user_id} does not own chat {chat_id}")

        # Check budget (90% warning, 100% block)
        await self._check_chat_budget(chat)

        try:
            # Add user message
            await self.message_repo.create(
                chat_id=chat_id,
                role=MessageRole.USER,
                content=content,
            )

            # Generate title from first user message if still "New Chat"
            if chat.title == "New Chat":
                title = content[:50] + ("..." if len(content) > 50 else "")
                await self.chat_repo.update_title(chat_id, title)
                chat.title = title

            # Prepare context (last 20 messages)
            context_messages = await self.message_repo.get_last_n_messages(chat_id, 20)

            # Convert to OpenRouter format
            messages = [
                {"role": msg.role.value, "content": msg.content} for msg in context_messages
            ]

            # Import OpenRouter client here to avoid circular imports
            from ardha.core.openrouter import OpenRouterClient

            openrouter = OpenRouterClient()

            # Stream response from OpenRouter
            full_response = ""
            total_tokens_input = 0
            total_tokens_output = 0
            total_cost = Decimal("0.00")

            try:
                # Create streaming request
                from ardha.schemas.ai.requests import ChatMessage as AIChatMessage
                from ardha.schemas.ai.requests import MessageRole as AIMessageRole
                from ardha.schemas.ai.requests import StreamingRequest

                streaming_request = StreamingRequest(
                    model=model,
                    messages=[
                        AIChatMessage(role=AIMessageRole(msg["role"]), content=msg["content"])
                        for msg in messages
                    ],
                    temperature=0.7,
                    max_tokens=4000,
                )

                async for chunk in openrouter.stream(streaming_request):
                    if chunk.content:
                        full_response += chunk.content
                        yield chunk.content

            except (OpenRouterError, CircuitBreakerOpenError) as e:
                logger.error(f"OpenRouter error for chat {chat_id}: {e}")
                # Save error message as assistant response
                error_content = f"I apologize, but I encountered an error: {str(e)}"
                await self.message_repo.create(
                    chat_id=chat_id,
                    role=MessageRole.ASSISTANT,
                    content=error_content,
                    model_used=model,
                    tokens_input=0,
                    tokens_output=0,
                    cost=float(Decimal("0.00")),
                    message_metadata={"error": str(e)},
                )
                yield error_content
                return

            # Calculate estimated tokens and cost after streaming
            if full_response:
                # Simple estimation: ~4 characters per token
                estimated_output_tokens = max(1, len(full_response) // 4)
                # Get model info for cost calculation
                from ardha.schemas.ai.models import get_model

                model_info = get_model(model)
                if model_info:
                    estimated_cost = model_info.calculate_cost(0, estimated_output_tokens)
                    total_tokens_output = estimated_output_tokens
                    total_cost = Decimal(str(estimated_cost))

            # Save complete assistant response
            await self.message_repo.create(
                chat_id=chat_id,
                role=MessageRole.ASSISTANT,
                content=full_response,
                model_used=model,
                tokens_input=total_tokens_input,
                tokens_output=total_tokens_output,
                cost=float(total_cost),
                message_metadata={"streamed": True},
            )

            # Update chat token counts and cost
            total_tokens = total_tokens_input + total_tokens_output
            await self.chat_repo.update_tokens(chat_id, total_tokens, total_cost)

            # Log to AI usage table
            await self.ai_usage_repo.create(
                user_id=user_id,
                model_name=model,
                operation=AIOperation.CHAT.value,
                tokens_input=total_tokens_input,
                tokens_output=total_tokens_output,
                cost=total_cost,
                project_id=chat.project_id,
            )

            # Trigger memory ingestion for important chats (10+ messages)
            message_count = await self.message_repo.get_message_count(chat_id)
            if message_count >= 10:
                try:
                    # Import here to avoid circular imports
                    from ardha.core.celery_app import celery_app

                    # Trigger background job
                    celery_app.send_task(
                        "ardha.jobs.memory_jobs.ingest_chat_memories",
                        args=[str(chat_id), str(user_id)],
                    )
                    logger.info(f"Triggered memory ingestion for chat {chat_id}")
                except Exception as e:
                    logger.warning(f"Failed to trigger memory ingestion: {e}")

            logger.info(
                f"Completed message in chat {chat_id}: "
                f"{total_tokens} tokens, ${total_cost} cost"
            )

        except SQLAlchemyError as e:
            logger.error(f"Error sending message to chat {chat_id}: {e}", exc_info=True)
            raise

    async def get_chat_history(
        self,
        chat_id: UUID,
        user_id: UUID,
        skip: int = 0,
        limit: int = 100,
    ) -> List[Message]:
        """
        Get paginated chat history.

        Verifies user owns chat and returns paginated messages.

        Args:
            chat_id: UUID of chat
            user_id: UUID of user requesting history
            skip: Number of records to skip (pagination)
            limit: Maximum number of records to return

        Returns:
            List of Message objects in chronological order

        Raises:
            ChatNotFoundError: If chat doesn't exist
            InsufficientChatPermissionsError: If user doesn't own chat
            ValueError: If skip or limit are invalid
            SQLAlchemyError: If database operation fails
        """
        # Verify chat ownership
        chat = await self.chat_repo.get_by_id(chat_id)
        if not chat:
            raise ChatNotFoundError(f"Chat {chat_id} not found")

        if chat.user_id != user_id:
            raise InsufficientChatPermissionsError(f"User {user_id} does not own chat {chat_id}")

        return await self.message_repo.get_by_chat(chat_id, skip, limit)

    async def get_user_chats(
        self,
        user_id: UUID,
        project_id: Optional[UUID] = None,
    ) -> List[Chat]:
        """
        Get user's chats, optionally filtered by project.

        Returns non-archived chats for user, optionally filtered
        to a specific project.

        Args:
            user_id: UUID of user
            project_id: Optional UUID to filter by project

        Returns:
            List of Chat objects ordered by most recent first

        Raises:
            SQLAlchemyError: If database operation fails
        """
        if project_id:
            # Verify user has access to project
            if not await self.project_service.check_permission(project_id, user_id, "viewer"):
                logger.warning(f"User {user_id} lacks access to project {project_id}")
                return []

            # Get chats for specific project
            return await self.chat_repo.get_by_project(
                project_id=project_id,
                include_archived=False,
            )
        else:
            # Get all user chats
            return await self.chat_repo.get_by_user(
                user_id=user_id,
                include_archived=False,
            )

    async def archive_chat(self, chat_id: UUID, user_id: UUID) -> Chat:
        """
        Archive a chat (soft delete).

        Verifies ownership and archives chat to hide from default views.

        Args:
            chat_id: UUID of chat to archive
            user_id: UUID of user archiving chat

        Returns:
            Updated Chat object with is_archived=True

        Raises:
            ChatNotFoundError: If chat doesn't exist
            InsufficientChatPermissionsError: If user doesn't own chat
            SQLAlchemyError: If database operation fails
        """
        # Verify chat ownership
        chat = await self.chat_repo.get_by_id(chat_id)
        if not chat:
            raise ChatNotFoundError(f"Chat {chat_id} not found")

        if chat.user_id != user_id:
            raise InsufficientChatPermissionsError(f"User {user_id} does not own chat {chat_id}")

        logger.info(f"Archiving chat {chat_id}")
        archived_chat = await self.chat_repo.archive(chat_id)
        if archived_chat is None:
            raise ChatNotFoundError(f"Chat {chat_id} not found")
        return archived_chat

    async def get_chat_summary(self, chat_id: UUID, user_id: UUID) -> Dict:
        """
        Get comprehensive chat summary.

        Returns chat details including message counts, token stats,
        cost information, and recent messages.

        Args:
            chat_id: UUID of chat
            user_id: UUID of user requesting summary

        Returns:
            Dictionary with chat summary information

        Raises:
            ChatNotFoundError: If chat doesn't exist
            InsufficientChatPermissionsError: If user doesn't own chat
            SQLAlchemyError: If database operation fails
        """
        # Verify chat ownership
        chat = await self.chat_repo.get_by_id(chat_id)
        if not chat:
            raise ChatNotFoundError(f"Chat {chat_id} not found")

        if chat.user_id != user_id:
            raise InsufficientChatPermissionsError(f"User {user_id} does not own chat {chat_id}")

        # Get token statistics
        token_stats = await self.message_repo.get_token_stats(chat_id)

        # Get recent messages (last 5)
        recent_messages = await self.message_repo.get_last_n_messages(chat_id, 5)

        return {
            "chat": {
                "id": chat.id,
                "title": chat.title,
                "mode": chat.mode.value,
                "created_at": chat.created_at,
                "updated_at": chat.updated_at,
                "is_archived": chat.is_archived,
                "project_id": chat.project_id,
                "total_tokens": chat.total_tokens,
                "total_cost": float(chat.total_cost),
            },
            "message_stats": token_stats,
            "recent_messages": [
                {
                    "id": msg.id,
                    "role": msg.role.value,
                    "content": msg.content[:200] + ("..." if len(msg.content) > 200 else ""),
                    "created_at": msg.created_at,
                    "model_used": msg.model_used,
                }
                for msg in recent_messages
            ],
        }

    async def _check_chat_budget(self, chat: Chat) -> None:
        """
        Check if chat is within budget limits.

        Implements budget checking with warnings at 90% and blocking at 100%.
        Uses daily budget limits from configuration.

        Args:
            chat: Chat object to check budget for

        Raises:
            ChatBudgetExceededError: If budget exceeded
        """
        # Note: get_settings imported but not used - available for future budget config

        # Get today's usage for user
        today = date.today()
        daily_usage = await self.ai_usage_repo.get_daily_usage(chat.user_id, today)
        daily_total = sum(usage.cost for usage in daily_usage)

        # Check against daily budget
        # For now, use a default daily budget of $2.00
        # TODO: Add ai_budget_daily to settings when needed
        daily_budget = Decimal("2.00")

        if daily_total >= daily_budget:
            raise ChatBudgetExceededError(
                f"Daily AI budget of ${daily_budget} exceeded. " f"Current usage: ${daily_total}"
            )

        # Warning at 90%
        warning_threshold = daily_budget * Decimal("0.9")
        if daily_total >= warning_threshold:
            logger.warning(
                f"Chat {chat.id} approaching budget limit: "
                f"${daily_total}/${daily_budget} ({(daily_total/daily_budget)*100:.1f}%)"
            )
