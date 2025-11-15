"""
Unit tests for Chat service.

This module tests all business logic operations for chat management,
including AI integration, permissions, and cost tracking.
"""

from datetime import date
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from sqlalchemy.exc import SQLAlchemyError

from ardha.models.ai_usage import AIOperation, AIUsage
from ardha.models.chat import Chat, ChatMode
from ardha.models.message import Message, MessageRole
from ardha.services.chat_service import (
    ChatBudgetExceededError,
    ChatNotFoundError,
    ChatService,
    InsufficientChatPermissionsError,
    InvalidChatModeError,
)


@pytest.mark.asyncio
class TestChatService:
    """Test suite for ChatService class."""

    async def test_create_chat_with_valid_user(self, test_db):
        """Test successful chat creation with valid user."""
        # Arrange
        service = ChatService(test_db)
        user_id = uuid4()
        mode = ChatMode.RESEARCH.value
        project_id = None

        # Act
        chat = await service.create_chat(
            user_id=user_id,
            mode=mode,
            project_id=project_id,
        )

        # Assert
        assert chat is not None
        assert chat.user_id == user_id
        assert chat.mode == mode
        assert chat.project_id == project_id
        assert chat.title == "New Chat"

        # Verify system message was created
        messages = await service.message_repo.get_by_chat(chat.id, 0, 10)
        assert len(messages) == 1
        assert messages[0].role == MessageRole.SYSTEM
        assert "research assistant" in messages[0].content.lower()

    async def test_create_chat_with_project_access(self, test_db):
        """Test chat creation with project access verification."""
        # Arrange
        service = ChatService(test_db)
        user_id = uuid4()
        mode = ChatMode.ARCHITECT.value
        project_id = uuid4()

        # Mock project service to allow access
        service.project_service.check_permission = AsyncMock(return_value=True)

        # Act
        chat = await service.create_chat(
            user_id=user_id,
            mode=mode,
            project_id=project_id,
        )

        # Assert
        assert chat is not None
        assert chat.project_id == project_id
        assert chat.mode == mode

        # Verify system message for architect mode
        messages = await service.message_repo.get_by_chat(chat.id, 0, 10)
        assert len(messages) == 1
        assert "software architect" in messages[0].content.lower()

    async def test_create_chat_invalid_mode(self, test_db):
        """Test chat creation with invalid mode."""
        # Arrange
        service = ChatService(test_db)
        user_id = uuid4()
        invalid_mode = "invalid_mode"

        # Act & Assert
        with pytest.raises(InvalidChatModeError, match="Invalid mode: invalid_mode"):
            await service.create_chat(
                user_id=user_id,
                mode=invalid_mode,
            )

    async def test_create_chat_project_access_denied(self, test_db):
        """Test chat creation when user lacks project access."""
        # Arrange
        service = ChatService(test_db)
        user_id = uuid4()
        mode = ChatMode.RESEARCH.value
        project_id = uuid4()

        # Mock project service to deny access
        from ardha.services.project_service import InsufficientPermissionsError

        service.project_service.check_permission = AsyncMock(
            side_effect=InsufficientPermissionsError("Access denied")
        )

        # Act & Assert
        with pytest.raises(InsufficientPermissionsError):
            await service.create_chat(
                user_id=user_id,
                mode=mode,
                project_id=project_id,
            )

    @patch("ardha.services.chat_service.OpenRouterClient")
    async def test_send_message_streams_response(self, mock_openrouter_class, test_db):
        """Test message sending with streaming response."""
        # Arrange
        service = ChatService(test_db)
        user_id = uuid4()

        # Create chat
        chat = await service.create_chat(user_id=user_id, mode=ChatMode.CHAT.value)

        # Mock OpenRouter client
        mock_client = AsyncMock()
        mock_openrouter_class.return_value = mock_client

        # Mock streaming response
        mock_chunks = [
            MagicMock(content="Hello "),
            MagicMock(content="there! "),
            MagicMock(content="How "),
            MagicMock(content="can "),
            MagicMock(content="I "),
            MagicMock(content="help "),
            MagicMock(content="you?"),
        ]
        mock_client.stream.return_value.__aiter__.return_value = mock_chunks

        # Mock model info for cost calculation
        with patch("ardha.services.chat_service.get_model") as mock_get_model:
            mock_model = MagicMock()
            mock_model.calculate_cost.return_value = Decimal("0.10")
            mock_get_model.return_value = mock_model

            # Act
            response_chunks = []
            async for chunk in service.send_message(
                chat_id=chat.id,
                user_id=user_id,
                content="Hello, how are you?",
                model="gpt-3.5-turbo",
            ):
                response_chunks.append(chunk)

            # Assert
            assert "".join(response_chunks) == "Hello there! How can I help you?"

            # Verify user message was saved
            messages = await service.message_repo.get_by_chat(chat.id, 0, 10)
            assert len(messages) >= 2  # System + User + Assistant

            user_messages = [m for m in messages if m.role == MessageRole.USER]
            assert len(user_messages) == 1
            assert user_messages[0].content == "Hello, how are you?"

            # Verify assistant response was saved
            assistant_messages = [m for m in messages if m.role == MessageRole.ASSISTANT]
            assert len(assistant_messages) == 1
            assert assistant_messages[0].content == "".join(response_chunks)
            assert assistant_messages[0].model_used == "gpt-3.5-turbo"
            assert (
                assistant_messages[0].tokens_output is not None
                and assistant_messages[0].tokens_output > 0
            )
            assert assistant_messages[0].cost is not None and assistant_messages[0].cost > 0

    @patch("ardha.services.chat_service.OpenRouterClient")
    async def test_send_message_openrouter_error(self, mock_openrouter_class, test_db):
        """Test message sending when OpenRouter fails."""
        # Arrange
        service = ChatService(test_db)
        user_id = uuid4()

        # Create chat
        chat = await service.create_chat(user_id=user_id, mode=ChatMode.CHAT.value)

        # Mock OpenRouter client to raise error
        mock_client = AsyncMock()
        mock_openrouter_class.return_value = mock_client
        from ardha.core.openrouter import OpenRouterError

        mock_client.stream.side_effect = OpenRouterError("API Error")

        # Act
        response_chunks = []
        async for chunk in service.send_message(
            chat_id=chat.id,
            user_id=user_id,
            content="Hello",
            model="gpt-3.5-turbo",
        ):
            response_chunks.append(chunk)

        # Assert
        assert len(response_chunks) == 1
        assert "encountered an error" in response_chunks[0]

        # Verify error message was saved
        messages = await service.message_repo.get_by_chat(chat.id, 0, 10)
        assistant_messages = [m for m in messages if m.role == MessageRole.ASSISTANT]
        assert len(assistant_messages) == 1
        assert "encountered an error" in assistant_messages[0].content

    async def test_send_message_chat_not_found(self, test_db):
        """Test message sending to non-existent chat."""
        # Arrange
        service = ChatService(test_db)
        user_id = uuid4()
        non_existent_chat_id = uuid4()

        # Act & Assert
        with pytest.raises(ChatNotFoundError, match="Chat .* not found"):
            async for _ in service.send_message(
                chat_id=non_existent_chat_id,
                user_id=user_id,
                content="Hello",
                model="gpt-3.5-turbo",
            ):
                pass  # Should not reach here

    async def test_chat_permission_enforcement(self, test_db):
        """Test that chat permissions are properly enforced."""
        # Arrange
        service = ChatService(test_db)
        user_id = uuid4()
        other_user_id = uuid4()

        # Create chat for user_id
        chat = await service.create_chat(user_id=user_id, mode=ChatMode.CHAT.value)

        # Act & Assert - Other user cannot access chat
        with pytest.raises(InsufficientChatPermissionsError):
            async for _ in service.send_message(
                chat_id=chat.id,
                user_id=other_user_id,  # Different user
                content="Hello",
                model="gpt-3.5-turbo",
            ):
                pass

        # Act & Assert - Other user cannot get chat history
        with pytest.raises(InsufficientChatPermissionsError):
            await service.get_chat_history(
                chat_id=chat.id,
                user_id=other_user_id,
            )

        # Act & Assert - Other user cannot archive chat
        with pytest.raises(InsufficientChatPermissionsError):
            await service.archive_chat(
                chat_id=chat.id,
                user_id=other_user_id,
            )

        # Act & Assert - Other user cannot get chat summary
        with pytest.raises(InsufficientChatPermissionsError):
            await service.get_chat_summary(
                chat_id=chat.id,
                user_id=other_user_id,
            )

    async def test_token_budget_warning(self, test_db):
        """Test budget warning at 90% threshold."""
        # Arrange
        service = ChatService(test_db)
        user_id = uuid4()

        # Create chat
        chat = await service.create_chat(user_id=user_id, mode=ChatMode.CHAT.value)

        # Mock AI usage to return high usage (90% of budget)
        mock_usage = MagicMock()
        mock_usage.cost = Decimal("1.80")  # 90% of $2.00 budget
        service.ai_usage_repo.get_daily_usage = AsyncMock(return_value=[mock_usage])

        # Mock OpenRouter to avoid actual API calls
        with patch("ardha.services.chat_service.OpenRouterClient") as mock_openrouter:
            mock_client = AsyncMock()
            mock_openrouter.return_value = mock_client
            mock_client.stream.return_value.__aiter__.return_value = []

            # Act - Should not raise error but should log warning
            async for _ in service.send_message(
                chat_id=chat.id,
                user_id=user_id,
                content="Hello",
                model="gpt-3.5-turbo",
            ):
                pass  # Should complete without error

    async def test_token_budget_exceeded(self, test_db):
        """Test budget blocking at 100% threshold."""
        # Arrange
        service = ChatService(test_db)
        user_id = uuid4()

        # Create chat
        chat = await service.create_chat(user_id=user_id, mode=ChatMode.CHAT.value)

        # Mock AI usage to return exceeded usage
        mock_usage = MagicMock()
        mock_usage.cost = Decimal("2.50")  # Exceeds $2.00 budget
        service.ai_usage_repo.get_daily_usage = AsyncMock(return_value=[mock_usage])

        # Act & Assert
        with pytest.raises(ChatBudgetExceededError, match="Daily AI budget"):
            async for _ in service.send_message(
                chat_id=chat.id,
                user_id=user_id,
                content="Hello",
                model="gpt-3.5-turbo",
            ):
                pass  # Should not reach here

    @patch("ardha.services.chat_service.OpenRouterClient")
    async def test_cost_calculation_accuracy(self, mock_openrouter_class, test_db):
        """Test accurate cost calculation for different models."""
        # Arrange
        service = ChatService(test_db)
        user_id = uuid4()

        # Create chat
        chat = await service.create_chat(user_id=user_id, mode=ChatMode.CHAT.value)

        # Mock OpenRouter client
        mock_client = AsyncMock()
        mock_openrouter_class.return_value = mock_client

        # Mock response with known length (100 characters = ~25 tokens)
        response_content = "x" * 100
        mock_chunk = MagicMock(content=response_content)
        mock_client.stream.return_value.__aiter__.return_value = [mock_chunk]

        # Test different models with different pricing
        test_cases = [
            ("gpt-3.5-turbo", Decimal("0.10")),  # Cheaper model
            ("gpt-4", Decimal("0.30")),  # More expensive model
        ]

        for model, expected_cost in test_cases:
            # Mock model info
            with patch("ardha.services.chat_service.get_model") as mock_get_model:
                mock_model = MagicMock()
                mock_model.calculate_cost.return_value = expected_cost
                mock_get_model.return_value = mock_model

                # Act
                async for _ in service.send_message(
                    chat_id=chat.id,
                    user_id=user_id,
                    content="Test message",
                    model=model,
                ):
                    pass  # Consume the stream

                # Assert - Check AI usage was tracked with correct cost
                usage_records = await service.ai_usage_repo.get_daily_usage(user_id, date.today())
                latest_usage = usage_records[-1]  # Get the most recent
                assert latest_usage.cost == expected_cost
                assert latest_usage.model_name == model

    async def test_system_message_by_mode(self, test_db):
        """Test that correct system message is used for each mode."""
        # Arrange
        service = ChatService(test_db)
        user_id = uuid4()

        # Test each mode
        mode_tests = [
            (ChatMode.RESEARCH, "research assistant"),
            (ChatMode.ARCHITECT, "software architect"),
            (ChatMode.IMPLEMENT, "expert developer"),
            (ChatMode.DEBUG, "debugging expert"),
            (ChatMode.CHAT, "helpful AI assistant"),
        ]

        for mode, expected_phrase in mode_tests:
            # Act
            chat = await service.create_chat(
                user_id=user_id,
                mode=mode.value,
            )

            # Assert
            messages = await service.message_repo.get_by_chat(chat.id, 0, 10)
            assert len(messages) == 1
            assert messages[0].role == MessageRole.SYSTEM
            assert expected_phrase in messages[0].content.lower()

    async def test_get_chat_history_success(self, test_db):
        """Test successful chat history retrieval."""
        # Arrange
        service = ChatService(test_db)
        user_id = uuid4()

        # Create chat
        chat = await service.create_chat(user_id=user_id, mode=ChatMode.CHAT.value)

        # Add some messages
        await service.message_repo.create(
            chat_id=chat.id,
            role=MessageRole.USER,
            content="Hello",
        )
        await service.message_repo.create(
            chat_id=chat.id,
            role=MessageRole.ASSISTANT,
            content="Hi there!",
        )

        # Act
        history = await service.get_chat_history(
            chat_id=chat.id,
            user_id=user_id,
        )

        # Assert
        assert len(history) >= 3  # System + User + Assistant
        roles = [msg.role for msg in history]
        assert MessageRole.SYSTEM in roles
        assert MessageRole.USER in roles
        assert MessageRole.ASSISTANT in roles

    async def test_get_user_chats_success(self, test_db):
        """Test successful user chats retrieval."""
        # Arrange
        service = ChatService(test_db)
        user_id = uuid4()
        project_id = uuid4()

        # Mock project permission check
        service.project_service.check_permission = AsyncMock(return_value=True)

        # Create chats
        chat1 = await service.create_chat(user_id=user_id, mode=ChatMode.CHAT.value)
        chat2 = await service.create_chat(
            user_id=user_id,
            mode=ChatMode.RESEARCH.value,
            project_id=project_id,
        )

        # Act - Get all user chats
        all_chats = await service.get_user_chats(user_id=user_id)

        # Act - Get project-specific chats
        project_chats = await service.get_user_chats(
            user_id=user_id,
            project_id=project_id,
        )

        # Assert
        assert len(all_chats) == 2
        assert len(project_chats) == 1
        assert project_chats[0].id == chat2.id

    async def test_archive_chat_success(self, test_db):
        """Test successful chat archival."""
        # Arrange
        service = ChatService(test_db)
        user_id = uuid4()

        # Create chat
        chat = await service.create_chat(user_id=user_id, mode=ChatMode.CHAT.value)

        # Act
        archived_chat = await service.archive_chat(
            chat_id=chat.id,
            user_id=user_id,
        )

        # Assert
        assert archived_chat is not None
        assert archived_chat.is_archived is True

        # Verify chat is excluded from default queries
        user_chats = await service.get_user_chats(user_id=user_id)
        assert chat not in user_chats

    async def test_get_chat_summary_success(self, test_db):
        """Test successful chat summary retrieval."""
        # Arrange
        service = ChatService(test_db)
        user_id = uuid4()

        # Create chat with some activity
        chat = await service.create_chat(user_id=user_id, mode=ChatMode.CHAT.value)

        # Add messages and update tokens
        await service.message_repo.create(
            chat_id=chat.id,
            role=MessageRole.USER,
            content="Hello",
        )
        await service.chat_repo.update_tokens(chat.id, 10, Decimal("0.05"))

        # Act
        summary = await service.get_chat_summary(
            chat_id=chat.id,
            user_id=user_id,
        )

        # Assert
        assert "chat" in summary
        assert "message_stats" in summary
        assert "recent_messages" in summary

        chat_info = summary["chat"]
        assert chat_info["id"] == chat.id
        assert chat_info["mode"] == chat.mode.value
        assert chat_info["total_tokens"] == 10
        assert chat_info["total_cost"] == 0.05

        assert len(summary["recent_messages"]) >= 1  # At least system message
