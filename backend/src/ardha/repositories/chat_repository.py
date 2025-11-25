"""
Chat repository for data access abstraction.

This module provides repository pattern implementation for Chat model,
handling all database operations related to chat conversations and sessions.
"""

import logging
from datetime import datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import and_, func, or_, select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ardha.models.chat import Chat, ChatMode

logger = logging.getLogger(__name__)


class ChatRepository:
    """
    Repository for Chat model database operations.

    Provides data access methods for chat-related operations including
    CRUD operations, pagination, token tracking, and archival.
    Follows the repository pattern to abstract database implementation
    details from business logic.

    Attributes:
        db: SQLAlchemy async session for database operations
    """

    def __init__(self, db: AsyncSession) -> None:
        """
        Initialize the ChatRepository with a database session.

        Args:
            db: SQLAlchemy async session for database operations
        """
        self.db = db

    async def get_by_id(self, chat_id: UUID) -> Chat | None:
        """
        Fetch a chat by its UUID.

        Args:
            chat_id: UUID of chat to fetch

        Returns:
            Chat object if found, None otherwise

        Raises:
            SQLAlchemyError: If database query fails
        """
        try:
            stmt = (
                select(Chat)
                .options(
                    selectinload(Chat.user), selectinload(Chat.project), selectinload(Chat.messages)
                )
                .where(Chat.id == chat_id)
            )
            result = await self.db.execute(stmt)
            return result.scalar_one_or_none()
        except SQLAlchemyError as e:
            logger.error(f"Error fetching chat by id {chat_id}: {e}", exc_info=True)
            raise

    async def get_by_user(
        self,
        user_id: UUID,
        skip: int = 0,
        limit: int = 100,
        include_archived: bool = False,
    ) -> list[Chat]:
        """
        Fetch chats owned by a specific user.

        Args:
            user_id: UUID of chat owner
            skip: Number of records to skip (for pagination)
            limit: Maximum number of records to return (capped at 100)
            include_archived: Whether to include archived chats

        Returns:
            List of Chat objects

        Raises:
            ValueError: If skip or limit are invalid
            SQLAlchemyError: If database query fails
        """
        if skip < 0:
            raise ValueError("skip must be non-negative")
        if limit <= 0 or limit > 100:
            raise ValueError("limit must be between 1 and 100")

        try:
            stmt = select(Chat).where(Chat.user_id == user_id)

            # Filter out archived chats by default
            if not include_archived:
                stmt = stmt.where(Chat.is_archived == False)

            # Order by most recent first
            stmt = stmt.order_by(Chat.created_at.desc())

            # Apply pagination
            stmt = stmt.offset(skip).limit(limit)

            result = await self.db.execute(stmt)
            return list(result.scalars().all())
        except SQLAlchemyError as e:
            logger.error(f"Error fetching chats by user {user_id}: {e}", exc_info=True)
            raise

    async def get_by_project(
        self,
        project_id: UUID,
        skip: int = 0,
        limit: int = 100,
        include_archived: bool = False,
    ) -> list[Chat]:
        """
        Fetch chats associated with a specific project.

        Args:
            project_id: UUID of project
            skip: Number of records to skip (for pagination)
            limit: Maximum number of records to return (capped at 100)
            include_archived: Whether to include archived chats

        Returns:
            List of Chat objects

        Raises:
            ValueError: If skip or limit are invalid
            SQLAlchemyError: If database query fails
        """
        if skip < 0:
            raise ValueError("skip must be non-negative")
        if limit <= 0 or limit > 100:
            raise ValueError("limit must be between 1 and 100")

        try:
            stmt = select(Chat).where(Chat.project_id == project_id)

            # Filter out archived chats by default
            if not include_archived:
                stmt = stmt.where(Chat.is_archived == False)

            # Order by most recent first
            stmt = stmt.order_by(Chat.created_at.desc())

            # Apply pagination
            stmt = stmt.offset(skip).limit(limit)

            result = await self.db.execute(stmt)
            return list(result.scalars().all())
        except SQLAlchemyError as e:
            logger.error(f"Error fetching chats by project {project_id}: {e}", exc_info=True)
            raise

    async def create(
        self,
        user_id: UUID,
        mode: str,
        project_id: UUID | None = None,
        title: str | None = None,
    ) -> Chat:
        """
        Create a new chat session.

        Args:
            user_id: UUID of user creating the chat
            mode: Chat mode (research, architect, implement, debug, chat)
            project_id: UUID of associated project (optional for personal chats)
            title: Optional title (auto-generated if not provided)

        Returns:
            Created Chat object with generated ID and timestamps

        Raises:
            ValueError: If mode is invalid or user_id is missing
            IntegrityError: If foreign key constraint violated
            SQLAlchemyError: If database operation fails
        """
        try:
            # Validate mode
            if mode not in [m.value for m in ChatMode]:
                raise ValueError(
                    f"Invalid mode: {mode}. Must be one of: {[m.value for m in ChatMode]}"
                )

            # Generate title from first message if not provided
            if not title:
                title = "New Chat"

            chat = Chat(
                user_id=user_id,
                mode=mode,
                project_id=project_id,
                title=title,
                total_tokens=0,
                total_cost=Decimal("0.00"),
            )

            self.db.add(chat)
            await self.db.flush()
            await self.db.refresh(chat)

            logger.info(f"Created chat {chat.id} for user {user_id} with mode {mode}")
            return chat
        except IntegrityError as e:
            logger.warning(f"Integrity error creating chat: {e}")
            raise
        except SQLAlchemyError as e:
            logger.error(f"Error creating chat: {e}", exc_info=True)
            raise

    async def update_title(self, chat_id: UUID, title: str) -> Chat | None:
        """
        Update chat title.

        Args:
            chat_id: UUID of chat to update
            title: New title for the chat

        Returns:
            Updated Chat object if found, None if chat doesn't exist

        Raises:
            ValueError: If title is empty or too long
            SQLAlchemyError: If database operation fails
        """
        if not title or title.strip() == "":
            raise ValueError("title cannot be empty")
        if len(title) > 200:
            raise ValueError("title cannot exceed 200 characters")

        try:
            chat = await self.get_by_id(chat_id)
            if not chat:
                logger.warning(f"Cannot update title: chat {chat_id} not found")
                return None

            chat.title = title.strip()
            await self.db.flush()
            await self.db.refresh(chat)

            logger.info(f"Updated title for chat {chat_id}")
            return chat
        except SQLAlchemyError as e:
            logger.error(f"Error updating chat title {chat_id}: {e}", exc_info=True)
            raise

    async def update_tokens(
        self,
        chat_id: UUID,
        tokens: int,
        cost: Decimal,
    ) -> Chat | None:
        """
        Update token count and cost for a chat.

        Args:
            chat_id: UUID of chat to update
            tokens: Additional tokens to add to total
            cost: Additional cost to add to total

        Returns:
            Updated Chat object if found, None if chat doesn't exist

        Raises:
            ValueError: If tokens or cost are negative
            SQLAlchemyError: If database operation fails
        """
        if tokens < 0:
            raise ValueError("tokens must be non-negative")
        if cost < 0:
            raise ValueError("cost must be non-negative")

        try:
            chat = await self.get_by_id(chat_id)
            if not chat:
                logger.warning(f"Cannot update tokens: chat {chat_id} not found")
                return None

            chat.total_tokens += tokens
            chat.total_cost += cost
            await self.db.flush()
            await self.db.refresh(chat)

            logger.info(f"Updated tokens for chat {chat_id}: +{tokens} tokens, +{cost} cost")
            return chat
        except SQLAlchemyError as e:
            logger.error(f"Error updating chat tokens {chat_id}: {e}", exc_info=True)
            raise

    async def archive(self, chat_id: UUID) -> Chat | None:
        """
        Archive a chat (soft delete).

        Sets is_archived to True. Archived chats are excluded from
        default queries but can be restored.

        Args:
            chat_id: UUID of chat to archive

        Returns:
            Updated Chat object if found, None if chat doesn't exist

        Raises:
            SQLAlchemyError: If database operation fails
        """
        try:
            chat = await self.get_by_id(chat_id)
            if not chat:
                logger.warning(f"Cannot archive: chat {chat_id} not found")
                return None

            chat.is_archived = True
            await self.db.flush()
            await self.db.refresh(chat)

            logger.info(f"Archived chat {chat_id}")
            return chat
        except SQLAlchemyError as e:
            logger.error(f"Error archiving chat {chat_id}: {e}", exc_info=True)
            raise

    async def delete(self, chat_id: UUID) -> None:
        """
        Hard delete a chat and all associated messages.

        Permanently removes chat and all Message records (cascade delete).
        Use archive() for soft delete to preserve data.

        Args:
            chat_id: UUID of chat to delete

        Raises:
            SQLAlchemyError: If database operation fails
        """
        try:
            chat = await self.get_by_id(chat_id)
            if not chat:
                logger.warning(f"Cannot delete: chat {chat_id} not found")
                return

            await self.db.delete(chat)
            await self.db.flush()

            logger.info(f"Hard deleted chat {chat_id}")
        except SQLAlchemyError as e:
            logger.error(f"Error deleting chat {chat_id}: {e}", exc_info=True)
            raise

    async def get_user_chat_count(self, user_id: UUID, include_archived: bool = False) -> int:
        """
        Get total count of chats for a user.

        Args:
            user_id: UUID of user
            include_archived: Whether to include archived chats

        Returns:
            Total count of chats

        Raises:
            SQLAlchemyError: If database query fails
        """
        try:
            stmt = select(func.count(Chat.id)).where(Chat.user_id == user_id)

            if not include_archived:
                stmt = stmt.where(Chat.is_archived == False)

            result = await self.db.execute(stmt)
            count = result.scalar()
            return count if count is not None else 0
        except SQLAlchemyError as e:
            logger.error(f"Error counting chats for user {user_id}: {e}", exc_info=True)
            raise

    async def get_project_chat_count(self, project_id: UUID, include_archived: bool = False) -> int:
        """
        Get total count of chats for a project.

        Args:
            project_id: UUID of project
            include_archived: Whether to include archived chats

        Returns:
            Total count of chats

        Raises:
            SQLAlchemyError: If database query fails
        """
        try:
            stmt = select(func.count(Chat.id)).where(Chat.project_id == project_id)

            if not include_archived:
                stmt = stmt.where(Chat.is_archived == False)

            result = await self.db.execute(stmt)
            count = result.scalar()
            return count if count is not None else 0
        except SQLAlchemyError as e:
            logger.error(f"Error counting chats for project {project_id}: {e}", exc_info=True)
            raise
