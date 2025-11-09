"""
Unit tests for Chat repository.

This module tests all data access operations for the Chat model,
ensuring proper error handling, validation, and database interactions.
"""

import pytest
from uuid import uuid4
from decimal import Decimal
from datetime import datetime

from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from ardha.models.chat import Chat, ChatMode
from ardha.repositories.chat_repository import ChatRepository


@pytest.mark.asyncio
class TestChatRepository:
    """Test suite for ChatRepository class."""
    
    async def test_create_chat_success(self, test_db):
        """Test successful chat creation."""
        # Arrange
        repo = ChatRepository(test_db)
        user_id = uuid4()
        mode = ChatMode.RESEARCH.value
        project_id = uuid4()
        
        # Act
        chat = await repo.create(
            user_id=user_id,
            mode=mode,
            project_id=project_id,
            title="Test Chat"
        )
        
        # Assert
        assert chat is not None
        assert chat.user_id == user_id
        assert chat.mode == mode
        assert chat.project_id == project_id
        assert chat.title == "Test Chat"
        assert chat.total_tokens == 0
        assert chat.total_cost == Decimal("0.00")
        assert chat.is_archived is False
        assert chat.id is not None
        assert chat.created_at is not None
        assert chat.updated_at is not None
    
    async def test_create_chat_without_project(self, test_db):
        """Test successful chat creation without project."""
        # Arrange
        repo = ChatRepository(test_db)
        user_id = uuid4()
        mode = ChatMode.CHAT.value
        
        # Act
        chat = await repo.create(
            user_id=user_id,
            mode=mode,
            project_id=None,
        )
        
        # Assert
        assert chat is not None
        assert chat.user_id == user_id
        assert chat.mode == mode
        assert chat.project_id is None
        assert chat.title == "New Chat"  # Default title
    
    async def test_create_chat_invalid_mode(self, test_db):
        """Test chat creation with invalid mode."""
        # Arrange
        repo = ChatRepository(test_db)
        user_id = uuid4()
        invalid_mode = "invalid_mode"
        
        # Act & Assert
        with pytest.raises(ValueError, match="Invalid mode: invalid_mode"):
            await repo.create(
                user_id=user_id,
                mode=invalid_mode,
            )
    
    async def test_get_by_id_success(self, test_db):
        """Test successful chat retrieval by ID."""
        # Arrange
        repo = ChatRepository(test_db)
        user_id = uuid4()
        created_chat = await repo.create(
            user_id=user_id,
            mode=ChatMode.RESEARCH.value,
        )
        
        # Act
        retrieved_chat = await repo.get_by_id(created_chat.id)
        
        # Assert
        assert retrieved_chat is not None
        assert retrieved_chat.id == created_chat.id
        assert retrieved_chat.user_id == user_id
        assert retrieved_chat.mode == ChatMode.RESEARCH.value
    
    async def test_get_by_id_not_found(self, test_db):
        """Test chat retrieval with non-existent ID."""
        # Arrange
        repo = ChatRepository(test_db)
        non_existent_id = uuid4()
        
        # Act
        chat = await repo.get_by_id(non_existent_id)
        
        # Assert
        assert chat is None
    
    async def test_get_by_user_success(self, test_db):
        """Test successful user chats retrieval."""
        # Arrange
        repo = ChatRepository(test_db)
        user_id = uuid4()
        
        # Create multiple chats
        chat1 = await repo.create(user_id=user_id, mode=ChatMode.RESEARCH.value)
        chat2 = await repo.create(user_id=user_id, mode=ChatMode.CHAT.value)
        chat3 = await repo.create(user_id=user_id, mode=ChatMode.IMPLEMENT.value)
        
        # Archive one chat to test filtering
        await repo.archive(chat3.id)
        
        # Act
        chats = await repo.get_by_user(user_id, skip=0, limit=10)
        
        # Assert
        assert len(chats) == 2  # Only non-archived chats
        assert all(chat.user_id == user_id for chat in chats)
        assert chat3 not in chats  # Archived chat excluded
    
    async def test_get_by_user_with_pagination(self, test_db):
        """Test user chats retrieval with pagination."""
        # Arrange
        repo = ChatRepository(test_db)
        user_id = uuid4()
        
        # Create 5 chats
        for i in range(5):
            await repo.create(user_id=user_id, mode=ChatMode.CHAT.value)
        
        # Act - Get second page with 2 items
        chats = await repo.get_by_user(user_id, skip=2, limit=2)
        
        # Assert
        assert len(chats) == 2
        # Should be ordered by created_at desc (most recent first)
        assert chats[0].created_at >= chats[1].created_at
    
    async def test_get_by_user_invalid_pagination(self, test_db):
        """Test user chats retrieval with invalid pagination."""
        # Arrange
        repo = ChatRepository(test_db)
        user_id = uuid4()
        
        # Act & Assert - Negative skip
        with pytest.raises(ValueError, match="skip must be non-negative"):
            await repo.get_by_user(user_id, skip=-1)
        
        # Act & Assert - Invalid limit (too low)
        with pytest.raises(ValueError, match="limit must be between 1 and 100"):
            await repo.get_by_user(user_id, limit=0)
        
        # Act & Assert - Invalid limit (too high)
        with pytest.raises(ValueError, match="limit must be between 1 and 100"):
            await repo.get_by_user(user_id, limit=101)
    
    async def test_get_by_project_success(self, test_db):
        """Test successful project chats retrieval."""
        # Arrange
        repo = ChatRepository(test_db)
        user_id = uuid4()
        project_id = uuid4()
        
        # Create chats for project
        chat1 = await repo.create(user_id=user_id, mode=ChatMode.RESEARCH.value, project_id=project_id)
        chat2 = await repo.create(user_id=user_id, mode=ChatMode.CHAT.value, project_id=project_id)
        
        # Create chat for different project (should not be included)
        await repo.create(user_id=user_id, mode=ChatMode.IMPLEMENT.value, project_id=uuid4())
        
        # Act
        chats = await repo.get_by_project(project_id, skip=0, limit=10)
        
        # Assert
        assert len(chats) == 2
        assert all(chat.project_id == project_id for chat in chats)
    
    async def test_update_title_success(self, test_db):
        """Test successful chat title update."""
        # Arrange
        repo = ChatRepository(test_db)
        user_id = uuid4()
        chat = await repo.create(user_id=user_id, mode=ChatMode.RESEARCH.value)
        new_title = "Updated Chat Title"
        
        # Act
        updated_chat = await repo.update_title(chat.id, new_title)
        
        # Assert
        assert updated_chat is not None
        assert updated_chat.title == new_title
        assert updated_chat.updated_at > chat.updated_at
    
    async def test_update_title_not_found(self, test_db):
        """Test title update for non-existent chat."""
        # Arrange
        repo = ChatRepository(test_db)
        non_existent_id = uuid4()
        
        # Act
        result = await repo.update_title(non_existent_id, "New Title")
        
        # Assert
        assert result is None
    
    async def test_update_title_empty(self, test_db):
        """Test title update with empty title."""
        # Arrange
        repo = ChatRepository(test_db)
        user_id = uuid4()
        chat = await repo.create(user_id=user_id, mode=ChatMode.RESEARCH.value)
        
        # Act & Assert
        with pytest.raises(ValueError, match="title cannot be empty"):
            await repo.update_title(chat.id, "")
        
        with pytest.raises(ValueError, match="title cannot be empty"):
            await repo.update_title(chat.id, "   ")
    
    async def test_update_title_too_long(self, test_db):
        """Test title update with too long title."""
        # Arrange
        repo = ChatRepository(test_db)
        user_id = uuid4()
        chat = await repo.create(user_id=user_id, mode=ChatMode.RESEARCH.value)
        long_title = "x" * 201  # 201 characters
        
        # Act & Assert
        with pytest.raises(ValueError, match="title cannot exceed 200 characters"):
            await repo.update_title(chat.id, long_title)
    
    async def test_update_tokens_success(self, test_db):
        """Test successful token and cost update."""
        # Arrange
        repo = ChatRepository(test_db)
        user_id = uuid4()
        chat = await repo.create(user_id=user_id, mode=ChatMode.RESEARCH.value)
        additional_tokens = 100
        additional_cost = Decimal("0.50")
        
        # Act
        updated_chat = await repo.update_tokens(chat.id, additional_tokens, additional_cost)
        
        # Assert
        assert updated_chat is not None
        assert updated_chat.total_tokens == additional_tokens
        assert updated_chat.total_cost == additional_cost
        assert updated_chat.updated_at > chat.updated_at
    
    async def test_update_tokens_not_found(self, test_db):
        """Test token update for non-existent chat."""
        # Arrange
        repo = ChatRepository(test_db)
        non_existent_id = uuid4()
        
        # Act
        result = await repo.update_tokens(non_existent_id, 100, Decimal("0.50"))
        
        # Assert
        assert result is None
    
    async def test_update_tokens_negative_values(self, test_db):
        """Test token update with negative values."""
        # Arrange
        repo = ChatRepository(test_db)
        user_id = uuid4()
        chat = await repo.create(user_id=user_id, mode=ChatMode.RESEARCH.value)
        
        # Act & Assert - Negative tokens
        with pytest.raises(ValueError, match="tokens must be non-negative"):
            await repo.update_tokens(chat.id, -10, Decimal("0.50"))
        
        # Act & Assert - Negative cost
        with pytest.raises(ValueError, match="cost must be non-negative"):
            await repo.update_tokens(chat.id, 100, Decimal("-0.50"))
    
    async def test_archive_success(self, test_db):
        """Test successful chat archival."""
        # Arrange
        repo = ChatRepository(test_db)
        user_id = uuid4()
        chat = await repo.create(user_id=user_id, mode=ChatMode.RESEARCH.value)
        
        # Act
        archived_chat = await repo.archive(chat.id)
        
        # Assert
        assert archived_chat is not None
        assert archived_chat.is_archived is True
        assert archived_chat.updated_at > chat.updated_at
    
    async def test_archive_not_found(self, test_db):
        """Test archival of non-existent chat."""
        # Arrange
        repo = ChatRepository(test_db)
        non_existent_id = uuid4()
        
        # Act
        result = await repo.archive(non_existent_id)
        
        # Assert
        assert result is None
    
    async def test_delete_success(self, test_db):
        """Test successful chat deletion."""
        # Arrange
        repo = ChatRepository(test_db)
        user_id = uuid4()
        chat = await repo.create(user_id=user_id, mode=ChatMode.RESEARCH.value)
        chat_id = chat.id
        
        # Act
        await repo.delete(chat_id)
        
        # Assert - Chat should be deleted
        deleted_chat = await repo.get_by_id(chat_id)
        assert deleted_chat is None
    
    async def test_delete_not_found(self, test_db):
        """Test deletion of non-existent chat (should not raise error)."""
        # Arrange
        repo = ChatRepository(test_db)
        non_existent_id = uuid4()
        
        # Act & Assert - Should not raise error
        await repo.delete(non_existent_id)  # Should complete without error
    
    async def test_get_user_chat_count(self, test_db):
        """Test getting user chat count."""
        # Arrange
        repo = ChatRepository(test_db)
        user_id = uuid4()
        
        # Create 3 chats
        for i in range(3):
            await repo.create(user_id=user_id, mode=ChatMode.CHAT.value)
        
        # Archive one chat
        chats = await repo.get_by_user(user_id)
        await repo.archive(chats[0].id)
        
        # Act
        count = await repo.get_user_chat_count(user_id)
        archived_count = await repo.get_user_chat_count(user_id, include_archived=True)
        
        # Assert
        assert count == 2  # Only non-archived
        assert archived_count == 3  # Including archived
    
    async def test_get_project_chat_count(self, test_db):
        """Test getting project chat count."""
        # Arrange
        repo = ChatRepository(test_db)
        user_id = uuid4()
        project_id = uuid4()
        
        # Create 2 chats for project
        for i in range(2):
            await repo.create(user_id=user_id, mode=ChatMode.CHAT.value, project_id=project_id)
        
        # Act
        count = await repo.get_project_chat_count(project_id)
        
        # Assert
        assert count == 2
    
    async def test_get_project_chat_count_empty(self, test_db):
        """Test getting chat count for project with no chats."""
        # Arrange
        repo = ChatRepository(test_db)
        project_id = uuid4()
        
        # Act
        count = await repo.get_project_chat_count(project_id)
        
        # Assert
        assert count == 0