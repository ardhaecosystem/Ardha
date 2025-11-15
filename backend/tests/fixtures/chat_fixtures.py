"""
Chat-specific test fixtures.

This module provides fixtures for chat-related tests including
sample chats, messages, and mock responses.
"""

from datetime import datetime
from decimal import Decimal
from unittest.mock import MagicMock
from uuid import uuid4

import pytest

from ardha.models.chat import Chat, ChatMode
from ardha.models.message import Message, MessageRole
from ardha.models.project import Project
from ardha.models.user import User


@pytest.fixture
async def sample_chat(test_db):
    """
    Create a sample chat with messages for testing.

    Returns:
        Chat object with associated messages
    """
    # Create user
    user = User(
        id=uuid4(),
        email="test@example.com",
        username="testuser",
        full_name="Test User",
        hashed_password="hashed_password",
        is_active=True,
        is_verified=True,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )
    test_db.add(user)
    await test_db.flush()

    # Create project (optional)
    project = Project(
        id=uuid4(),
        name="Test Project",
        description="A test project",
        visibility="private",
        owner_id=user.id,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )
    test_db.add(project)
    await test_db.flush()

    # Create chat
    chat = Chat(
        id=uuid4(),
        user_id=user.id,
        mode=ChatMode.RESEARCH.value,
        project_id=project.id,
        title="Sample Research Chat",
        total_tokens=150,
        total_cost=Decimal("0.75"),
        is_archived=False,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )
    test_db.add(chat)
    await test_db.flush()

    # Create system message
    system_message = Message(
        id=uuid4(),
        chat_id=chat.id,
        role=MessageRole.SYSTEM,
        content="You are a research assistant. Your role is to help users conduct thorough research...",
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )
    test_db.add(system_message)

    # Create user message
    user_message = Message(
        id=uuid4(),
        chat_id=chat.id,
        role=MessageRole.USER,
        content="What are the latest developments in quantum computing?",
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )
    test_db.add(user_message)

    # Create assistant message
    assistant_message = Message(
        id=uuid4(),
        chat_id=chat.id,
        role=MessageRole.ASSISTANT,
        content="Recent developments in quantum computing include breakthroughs in quantum error correction...",
        model_used="gpt-4",
        tokens_input=25,
        tokens_output=125,
        cost=0.75,
        message_metadata={"streamed": True},
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )
    test_db.add(assistant_message)

    await test_db.commit()

    # Load relationships
    await test_db.refresh(chat)

    return chat


@pytest.fixture
async def sample_chats_batch(test_db):
    """
    Create multiple sample chats for pagination testing.

    Returns:
        List of Chat objects
    """
    # Create user
    user = User(
        id=uuid4(),
        email="batch@example.com",
        username="batchuser",
        full_name="Batch User",
        hashed_password="hashed_password",
        is_active=True,
        is_verified=True,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )
    test_db.add(user)
    await test_db.flush()

    chats = []
    modes = [
        ChatMode.RESEARCH,
        ChatMode.ARCHITECT,
        ChatMode.IMPLEMENT,
        ChatMode.DEBUG,
        ChatMode.CHAT,
    ]

    for i, mode in enumerate(modes):
        chat = Chat(
            id=uuid4(),
            user_id=user.id,
            mode=mode.value,
            project_id=None,
            title=f"Chat {i+1}: {mode.value.title()} Mode",
            total_tokens=50 * (i + 1),
            total_cost=Decimal(str(0.25 * (i + 1))),
            is_archived=(i >= 3),  # Last 2 are archived
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        test_db.add(chat)
        chats.append(chat)

        # Add system message
        system_message = Message(
            id=uuid4(),
            chat_id=chat.id,
            role=MessageRole.SYSTEM,
            content=f"System message for {mode.value} mode",
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        test_db.add(system_message)

    await test_db.commit()

    # Load relationships
    for chat in chats:
        await test_db.refresh(chat)

    return chats


@pytest.fixture
def mock_openrouter_response():
    """
    Mock OpenRouter API response for testing.

    Returns:
        MagicMock configured to simulate OpenRouter streaming response
    """
    # Create mock response chunks
    chunks = [
        "Quantum computing has seen several ",
        "significant breakthroughs in recent months. ",
        "Researchers at major institutions have ",
        "demonstrated improved quantum error correction ",
        "and increased qubit stability. ",
        "These advances bring practical quantum ",
        "applications closer to reality.",
    ]

    # Create mock chunk objects
    mock_chunks = []
    for i, content in enumerate(chunks):
        chunk = MagicMock()
        chunk.content = content
        chunk.index = i
        mock_chunks.append(chunk)

    return mock_chunks


@pytest.fixture
def mock_openrouter_error_response():
    """
    Mock OpenRouter error response for testing error handling.

    Returns:
        OpenRouterError instance for testing
    """
    from ardha.core.openrouter import OpenRouterError

    # Create a real OpenRouterError instance instead of mocking it
    # This is type-safe and behaves exactly like a real exception
    error = OpenRouterError(
        message="Rate limit exceeded", error_type="rate_limit_error", code="429"
    )

    return error


@pytest.fixture
async def websocket_connection_helper():
    """
    Helper fixture for WebSocket connection testing.

    Returns:
        Dictionary with WebSocket test utilities
    """

    class WebSocketHelper:
        def __init__(self):
            self.messages = []
            self.connections = []

        async def mock_connect(self, websocket, chat_id):
            """Mock WebSocket connection."""
            self.connections.append((websocket, chat_id))
            return True

        async def mock_disconnect(self, websocket):
            """Mock WebSocket disconnection."""
            self.connections = [(ws, cid) for ws, cid in self.connections if ws != websocket]

        async def mock_send_message(self, websocket, message):
            """Mock sending message through WebSocket."""
            self.messages.append(message)
            return True

        def get_messages(self):
            """Get all sent messages."""
            return self.messages

        def get_connection_count(self):
            """Get number of active connections."""
            return len(self.connections)

        def clear_messages(self):
            """Clear message history."""
            self.messages.clear()

    return WebSocketHelper()


@pytest.fixture
async def chat_with_project(test_db):
    """
    Create a chat associated with a project for testing project-specific features.

    Returns:
        Tuple of (Chat, Project, User)
    """
    # Create user
    user = User(
        id=uuid4(),
        email="project@example.com",
        username="projectuser",
        full_name="Project User",
        hashed_password="hashed_password",
        is_active=True,
        is_verified=True,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )
    test_db.add(user)
    await test_db.flush()

    # Create project
    project = Project(
        id=uuid4(),
        name="AI Research Project",
        description="A project for AI research and development",
        visibility="private",
        owner_id=user.id,
        tech_stack=["Python", "FastAPI", "React"],
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )
    test_db.add(project)
    await test_db.flush()

    # Create chat
    chat = Chat(
        id=uuid4(),
        user_id=user.id,
        mode=ChatMode.ARCHITECT.value,
        project_id=project.id,
        title="Architecture Discussion",
        total_tokens=200,
        total_cost=Decimal("1.00"),
        is_archived=False,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )
    test_db.add(chat)
    await test_db.flush()

    # Add messages
    system_message = Message(
        id=uuid4(),
        chat_id=chat.id,
        role=MessageRole.SYSTEM,
        content="You are a software architect. Your role is to help design robust, scalable systems...",
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )
    test_db.add(system_message)

    user_message = Message(
        id=uuid4(),
        chat_id=chat.id,
        role=MessageRole.USER,
        content="How should we design the microservices architecture for this project?",
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )
    test_db.add(user_message)

    await test_db.commit()

    # Load relationships
    await test_db.refresh(chat)
    await test_db.refresh(project)
    await test_db.refresh(user)

    return chat, project, user


@pytest.fixture
def mock_model_pricing():
    """
    Mock model pricing information for cost calculation tests.

    Returns:
        Dictionary with model pricing data
    """
    return {
        "gpt-3.5-turbo": {
            "input_cost_per_token": Decimal("0.0000015"),  # $1.50 per 1M tokens
            "output_cost_per_token": Decimal("0.000002"),  # $2.00 per 1M tokens
        },
        "gpt-4": {
            "input_cost_per_token": Decimal("0.00003"),  # $30.00 per 1M tokens
            "output_cost_per_token": Decimal("0.00006"),  # $60.00 per 1M tokens
        },
        "claude-3-sonnet": {
            "input_cost_per_token": Decimal("0.000015"),  # $15.00 per 1M tokens
            "output_cost_per_token": Decimal("0.000075"),  # $75.00 per 1M tokens
        },
    }


@pytest.fixture
async def archived_chat(test_db):
    """
    Create an archived chat for testing archival functionality.

    Returns:
        Archived Chat object
    """
    # Create user
    user = User(
        id=uuid4(),
        email="archived@example.com",
        username="archiveduser",
        full_name="Archived User",
        hashed_password="hashed_password",
        is_active=True,
        is_verified=True,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )
    test_db.add(user)
    await test_db.flush()

    # Create archived chat
    chat = Chat(
        id=uuid4(),
        user_id=user.id,
        mode=ChatMode.CHAT.value,
        project_id=None,
        title="Archived Chat",
        total_tokens=50,
        total_cost=Decimal("0.25"),
        is_archived=True,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )
    test_db.add(chat)
    await test_db.flush()

    # Add system message
    system_message = Message(
        id=uuid4(),
        chat_id=chat.id,
        role=MessageRole.SYSTEM,
        content="You are a helpful AI assistant...",
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )
    test_db.add(system_message)

    await test_db.commit()
    await test_db.refresh(chat)

    return chat
