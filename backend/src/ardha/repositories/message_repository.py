"""
Message repository for data access abstraction.

This module provides repository pattern implementation for Message model,
handling all database operations related to individual chat messages.
"""

import logging
from uuid import UUID
from typing import List, Dict

from sqlalchemy import select, func, and_
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ardha.models.message import Message, MessageRole

logger = logging.getLogger(__name__)


class MessageRepository:
    """
    Repository for Message model database operations.
    
    Provides data access methods for message-related operations including
    CRUD operations, pagination, and token statistics. Follows the 
    repository pattern to abstract database implementation details from business logic.
    
    Attributes:
        db: SQLAlchemy async session for database operations
    """
    
    def __init__(self, db: AsyncSession) -> None:
        """
        Initialize the MessageRepository with a database session.
        
        Args:
            db: SQLAlchemy async session for database operations
        """
        self.db = db
    
    async def get_by_chat(
        self,
        chat_id: UUID,
        skip: int = 0,
        limit: int = 100,
    ) -> List[Message]:
        """
        Fetch messages for a specific chat.
        
        Args:
            chat_id: UUID of chat to fetch messages from
            skip: Number of records to skip (for pagination)
            limit: Maximum number of records to return (capped at 100)
            
        Returns:
            List of Message objects in chronological order
            
        Raises:
            ValueError: If skip or limit are invalid
            SQLAlchemyError: If database query fails
        """
        if skip < 0:
            raise ValueError("skip must be non-negative")
        if limit <= 0 or limit > 100:
            raise ValueError("limit must be between 1 and 100")
        
        try:
            stmt = (
                select(Message)
                .where(Message.chat_id == chat_id)
                .order_by(Message.created_at.asc())
                .offset(skip)
                .limit(limit)
            )
            
            result = await self.db.execute(stmt)
            return list(result.scalars().all())
        except SQLAlchemyError as e:
            logger.error(f"Error fetching messages by chat {chat_id}: {e}", exc_info=True)
            raise
    
    async def get_last_n_messages(self, chat_id: UUID, n: int) -> List[Message]:
        """
        Get the last N messages from a chat.
        
        Args:
            chat_id: UUID of chat
            n: Number of recent messages to fetch (max 100)
            
        Returns:
            List of Message objects in chronological order
            
        Raises:
            ValueError: If n is invalid
            SQLAlchemyError: If database query fails
        """
        if n <= 0 or n > 100:
            raise ValueError("n must be between 1 and 100")
        
        try:
            # Get total count first
            count_stmt = select(func.count(Message.id)).where(Message.chat_id == chat_id)
            count_result = await self.db.execute(count_stmt)
            total_count = count_result.scalar()
            
            # Calculate skip to get last N messages
            total_count = total_count if total_count is not None else 0
            skip = max(0, total_count - n)
            
            stmt = (
                select(Message)
                .where(Message.chat_id == chat_id)
                .order_by(Message.created_at.asc())
                .offset(skip)
                .limit(n)
            )
            
            result = await self.db.execute(stmt)
            return list(result.scalars().all())
        except SQLAlchemyError as e:
            logger.error(f"Error fetching last {n} messages for chat {chat_id}: {e}", exc_info=True)
            raise
    
    async def create(
        self,
        chat_id: UUID,
        role: str,
        content: str,
        model_used: str | None = None,
        tokens_input: int | None = None,
        tokens_output: int | None = None,
        cost: float | None = None,
        message_metadata: Dict | None = None,
    ) -> Message:
        """
        Create a new message in a chat.
        
        Args:
            chat_id: UUID of parent chat
            role: Message role (user, assistant, system)
            content: Message content
            model_used: AI model name (for assistant messages)
            tokens_input: Input tokens (for AI messages)
            tokens_output: Output tokens (for AI messages)
            cost: Cost of message (for AI messages)
            message_metadata: Additional metadata as JSON
            
        Returns:
            Created Message object with generated ID and timestamp
            
        Raises:
            ValueError: If role is invalid or required fields are missing
            IntegrityError: If foreign key constraint violated
            SQLAlchemyError: If database operation fails
        """
        try:
            # Validate role
            if role not in [r.value for r in MessageRole]:
                raise ValueError(f"Invalid role: {role}. Must be one of: {[r.value for r in MessageRole]}")
            
            if not content or content.strip() == "":
                raise ValueError("content cannot be empty")
            
            from decimal import Decimal
            
            message = Message(
                chat_id=chat_id,
                role=role,
                content=content.strip(),
                model_used=model_used,
                tokens_input=tokens_input,
                tokens_output=tokens_output,
                cost=Decimal(str(cost)) if cost is not None else None,
                message_metadata=message_metadata or {},
            )
            
            self.db.add(message)
            await self.db.flush()
            await self.db.refresh(message)
            
            logger.info(f"Created message in chat {chat_id} with role {role}")
            return message
        except IntegrityError as e:
            logger.warning(f"Integrity error creating message: {e}")
            raise
        except SQLAlchemyError as e:
            logger.error(f"Error creating message: {e}", exc_info=True)
            raise
    
    async def bulk_create(self, messages: List[Dict]) -> List[Message]:
        """
        Create multiple messages in a single operation.
        
        Args:
            messages: List of message dictionaries with required fields
            
        Returns:
            List of created Message objects
            
        Raises:
            ValueError: If messages list is empty or contains invalid data
            IntegrityError: If foreign key constraint violated
            SQLAlchemyError: If database operation fails
        """
        if not messages:
            raise ValueError("messages list cannot be empty")
        
        if len(messages) > 100:
            raise ValueError("cannot create more than 100 messages at once")
        
        try:
            from decimal import Decimal
            
            message_objects = []
            for msg_data in messages:
                # Validate required fields
                if 'chat_id' not in msg_data or 'role' not in msg_data or 'content' not in msg_data:
                    raise ValueError("Each message must have chat_id, role, and content")
                
                # Validate role
                role = msg_data['role']
                if role not in [r.value for r in MessageRole]:
                    raise ValueError(f"Invalid role: {role}. Must be one of: {[r.value for r in MessageRole]}")
                
                message_obj = Message(
                    chat_id=msg_data['chat_id'],
                    role=role,
                    content=msg_data['content'].strip(),
                    model_used=msg_data.get('model_used'),
                    tokens_input=msg_data.get('tokens_input'),
                    tokens_output=msg_data.get('tokens_output'),
                    cost=Decimal(str(msg_data.get('cost'))) if msg_data.get('cost') is not None else None,
                    message_metadata=msg_data.get('message_metadata', {}),
                )
                message_objects.append(message_obj)
            
            self.db.add_all(message_objects)
            await self.db.flush()
            
            # Refresh all objects to get their IDs
            for message_obj in message_objects:
                await self.db.refresh(message_obj)
            
            logger.info(f"Created {len(message_objects)} messages in bulk")
            return message_objects
        except IntegrityError as e:
            logger.warning(f"Integrity error in bulk message creation: {e}")
            raise
        except SQLAlchemyError as e:
            logger.error(f"Error in bulk message creation: {e}", exc_info=True)
            raise
    
    async def get_token_stats(self, chat_id: UUID) -> Dict[str, int]:
        """
        Get token statistics for a chat.
        
        Args:
            chat_id: UUID of chat
            
        Returns:
            Dictionary with token statistics:
            - total_input_tokens: Sum of input tokens
            - total_output_tokens: Sum of output tokens
            - message_count: Total number of messages
            - assistant_messages: Number of assistant messages
            
        Raises:
            SQLAlchemyError: If database query fails
        """
        try:
            # Get token aggregates
            token_stmt = (
                select(
                    func.coalesce(func.sum(Message.tokens_input), 0).label('total_input_tokens'),
                    func.coalesce(func.sum(Message.tokens_output), 0).label('total_output_tokens'),
                    func.count(Message.id).label('message_count'),
                    func.sum(func.case((Message.role == MessageRole.ASSISTANT, 1), else_=0)).label('assistant_messages'),
                )
                .where(Message.chat_id == chat_id)
            )
            
            result = await self.db.execute(token_stmt)
            row = result.first()
            
            if row is None:
                return {
                    'total_input_tokens': 0,
                    'total_output_tokens': 0,
                    'message_count': 0,
                    'assistant_messages': 0,
                }
            
            return {
                'total_input_tokens': row.total_input_tokens or 0,
                'total_output_tokens': row.total_output_tokens or 0,
                'message_count': row.message_count or 0,
                'assistant_messages': row.assistant_messages or 0,
            }
        except SQLAlchemyError as e:
            logger.error(f"Error getting token stats for chat {chat_id}: {e}", exc_info=True)
            raise
    
    async def get_message_count(self, chat_id: UUID) -> int:
        """
        Get total count of messages in a chat.
        
        Args:
            chat_id: UUID of chat
            
        Returns:
            Total count of messages
            
        Raises:
            SQLAlchemyError: If database query fails
        """
        try:
            stmt = select(func.count(Message.id)).where(Message.chat_id == chat_id)
            result = await self.db.execute(stmt)
            count = result.scalar()
            return count if count is not None else 0
        except SQLAlchemyError as e:
            logger.error(f"Error counting messages for chat {chat_id}: {e}", exc_info=True)
            raise
    
    async def delete_chat_messages(self, chat_id: UUID) -> int:
        """
        Delete all messages in a chat.
        
        Args:
            chat_id: UUID of chat
            
        Returns:
            Number of messages deleted
            
        Raises:
            SQLAlchemyError: If database operation fails
        """
        try:
            # Get count first
            count_stmt = select(func.count(Message.id)).where(Message.chat_id == chat_id)
            count_result = await self.db.execute(count_stmt)
            count = count_result.scalar()
            
            # Delete all messages
            delete_stmt = select(Message).where(Message.chat_id == chat_id)
            result = await self.db.execute(delete_stmt)
            messages = result.scalars().all()
            
            for message in messages:
                await self.db.delete(message)
            
            await self.db.flush()
            
            logger.info(f"Deleted {count} messages from chat {chat_id}")
            return count if count is not None else 0
        except SQLAlchemyError as e:
            logger.error(f"Error deleting messages for chat {chat_id}: {e}", exc_info=True)
            raise