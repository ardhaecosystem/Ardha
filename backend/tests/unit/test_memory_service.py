"""
Unit tests for Memory Service.

Tests the core functionality of the memory service including
memory creation, semantic search, context assembly, and ingestion.
"""

from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID, uuid4

import pytest

from ardha.models.memory import Memory, MemoryType, SourceType
from ardha.repositories.memory_repository import MemoryRepository
from ardha.services.chat_service import ChatService
from ardha.services.embedding_service import LocalEmbeddingService
from ardha.services.memory_service import (
    ContextAssemblyError,
    MemoryCreationError,
    MemoryIngestionError,
    MemoryService,
    SemanticSearchError,
)
from ardha.services.semantic_search_service import SemanticSearchService


@pytest.fixture
def mock_memory_repository():
    """Create a mock memory repository."""
    repo = AsyncMock(spec=MemoryRepository)
    return repo


@pytest.fixture
def mock_embedding_service():
    """Create a mock embedding service."""
    service = AsyncMock(spec=LocalEmbeddingService)
    service.generate_embedding.return_value = [0.1] * 384  # Mock embedding
    return service


@pytest.fixture
def mock_qdrant_service():
    """Create a mock Qdrant service."""
    service = AsyncMock()
    service.collection_exists.return_value = True
    service.upsert_vectors.return_value = None
    service.search_similar.return_value = [
        {
            "id": "test-point-id",
            "score": 0.8,
            "text": "test content",
            "metadata": {"user_id": str(uuid4())},
        }
    ]
    return service


@pytest.fixture
def mock_chat_service():
    """Create a mock chat service."""
    service = AsyncMock(spec=ChatService)
    service.get_chat_history.return_value = []
    return service


@pytest.fixture
def memory_service(
    mock_memory_repository, mock_embedding_service, mock_qdrant_service, mock_chat_service
):
    """Create a memory service with mocked dependencies."""
    return MemoryService(
        memory_repository=mock_memory_repository,
        embedding_service=mock_embedding_service,
        qdrant_service=mock_qdrant_service,
        chat_service=mock_chat_service,
    )


@pytest.fixture
def sample_user_id():
    """Sample user ID for testing."""
    return uuid4()


@pytest.fixture
def sample_project_id():
    """Sample project ID for testing."""
    return uuid4()


@pytest.fixture
def sample_memory():
    """Sample memory object for testing."""
    return Memory(
        id=uuid4(),
        user_id=uuid4(),
        project_id=uuid4(),
        content="This is a test memory content",
        summary="Test memory summary",
        qdrant_collection="test_collection",
        qdrant_point_id="test-point-id",
        embedding_model="all-MiniLM-L6-v2",
        memory_type=MemoryType.CONVERSATION,
        source_type=SourceType.MANUAL,
        source_id=None,
        importance=5,
        confidence=0.8,
        access_count=0,
        last_accessed=None,
        tags={"tags": ["test"]},
        extra_metadata={},
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
        expires_at=None,
        is_archived=False,
    )


class TestMemoryService:
    """Test cases for MemoryService class."""

    @pytest.mark.asyncio
    async def test_initialization(self, memory_service):
        """Test memory service initialization."""
        assert memory_service.memory_repository is not None
        assert memory_service.embedding_service is not None
        assert memory_service.qdrant_service is not None
        assert memory_service.chat_service is not None

        # Check collection mapping
        assert "conversation" in memory_service.collection_mapping
        assert "workflow" in memory_service.collection_mapping
        assert memory_service.default_collection == "general_memories"

    @pytest.mark.asyncio
    async def test_get_collection_name(self, memory_service):
        """Test collection name mapping."""
        assert memory_service._get_collection_name("conversation") == "chat_memories"
        assert memory_service._get_collection_name("workflow") == "workflow_memories"
        assert memory_service._get_collection_name("unknown") == "general_memories"

    @pytest.mark.asyncio
    async def test_get_search_collections(self, memory_service):
        """Test search collections determination."""
        # With specific memory type
        collections = memory_service._get_search_collections("conversation")
        assert "chat_memories" in collections
        assert len(collections) == 1

        # Without memory type (all collections)
        collections = memory_service._get_search_collections(None)
        assert len(collections) > 1
        assert "chat_memories" in collections
        assert "workflow_memories" in collections

    @pytest.mark.asyncio
    async def test_generate_summary(self, memory_service):
        """Test summary generation."""
        # Short content
        short_content = "Short content"
        summary = memory_service._generate_summary(short_content)
        assert summary == short_content

        # Long content
        long_content = "This is a very long content that should be truncated " * 10
        summary = memory_service._generate_summary(long_content, max_length=50)
        assert len(summary) <= 50
        assert summary.endswith("...")

    @pytest.mark.asyncio
    async def test_calculate_importance(self, memory_service):
        """Test importance score calculation."""
        # Manual source
        score = memory_service.calculate_importance(
            content="test content", source_type=SourceType.MANUAL
        )
        assert score >= 8  # Base 5 + 3 for manual

        # Workflow source with long content
        score = memory_service.calculate_importance(
            content="This is a very long content " * 100, source_type=SourceType.WORKFLOW
        )
        assert score >= 8  # Base 5 + 2 for workflow + 1 for length

        # Chat source with user approval
        score = memory_service.calculate_importance(
            content="test content", source_type=SourceType.CHAT, has_user_approval=True
        )
        assert score >= 8  # Base 5 + 1 for chat + 2 for approval

        # Score should be capped at 10
        score = memory_service.calculate_importance(
            content="very long content " * 200,
            source_type=SourceType.MANUAL,
            access_count=20,
            has_user_approval=True,
        )
        assert score == 10

    @pytest.mark.asyncio
    async def test_create_memory_success(
        self,
        memory_service,
        mock_memory_repository,
        mock_embedding_service,
        mock_qdrant_service,
        sample_user_id,
        sample_project_id,
        sample_memory,
    ):
        """Test successful memory creation."""
        # Setup mocks
        mock_memory_repository.create.return_value = sample_memory

        # Create memory
        result = await memory_service.create_memory(
            user_id=sample_user_id,
            content="Test memory content",
            memory_type="conversation",
            project_id=sample_project_id,
            source_type="manual",
            importance=5,
            tags=["test"],
        )

        # Verify result
        assert result == sample_memory

        # Verify embedding was generated
        mock_embedding_service.generate_embedding.assert_called_once_with("Test memory content")

        # Verify vector was stored
        mock_qdrant_service.upsert_vectors.assert_called_once()

        # Verify memory was stored in database
        mock_memory_repository.create.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_memory_empty_content(self, memory_service, sample_user_id):
        """Test memory creation with empty content."""
        with pytest.raises(MemoryCreationError, match="Content cannot be empty"):
            await memory_service.create_memory(
                user_id=sample_user_id, content="", memory_type="conversation"
            )

    @pytest.mark.asyncio
    async def test_create_memory_embedding_failure(
        self, memory_service, mock_embedding_service, sample_user_id
    ):
        """Test memory creation with embedding failure."""
        # Setup mock to raise exception
        mock_embedding_service.generate_embedding.side_effect = Exception("Embedding failed")

        with pytest.raises(MemoryCreationError, match="Memory creation failed"):
            await memory_service.create_memory(
                user_id=sample_user_id, content="Test content", memory_type="conversation"
            )

    @pytest.mark.asyncio
    async def test_search_semantic_success(
        self,
        memory_service,
        mock_memory_repository,
        mock_embedding_service,
        mock_qdrant_service,
        sample_user_id,
        sample_memory,
    ):
        """Test successful semantic search."""
        # Setup mocks
        mock_memory_repository.get_by_source.return_value = [sample_memory]

        # Perform search
        results = await memory_service.search_semantic(
            user_id=sample_user_id, query="test query", limit=10
        )

        # Verify results
        assert len(results) == 1
        memory, score = results[0]
        assert memory == sample_memory
        assert score == 0.8

        # Verify embedding was generated
        mock_embedding_service.generate_embedding.assert_called_once_with("test query")

        # Verify search was performed
        mock_qdrant_service.search_similar.assert_called()

        # Verify access count was incremented
        mock_memory_repository.increment_access_count.assert_called_once_with(sample_memory.id)

    @pytest.mark.asyncio
    async def test_search_semantic_with_filters(
        self, memory_service, mock_qdrant_service, sample_user_id, sample_project_id
    ):
        """Test semantic search with filters."""
        # Setup mock
        mock_qdrant_service.search_similar.return_value = []

        # Perform search with filters
        await memory_service.search_semantic(
            user_id=sample_user_id,
            query="test query",
            project_id=sample_project_id,
            memory_type="conversation",
            min_score=0.7,
        )

        # Verify search was called with correct parameters
        mock_qdrant_service.search_similar.assert_called()

        # Check the call arguments
        call_args = mock_qdrant_service.search_similar.call_args
        assert call_args[1]["score_threshold"] == 0.7

    @pytest.mark.asyncio
    async def test_get_context_for_chat_success(
        self, memory_service, mock_chat_service, sample_user_id
    ):
        """Test successful context assembly for chat."""
        # Setup mock chat messages
        chat_id = uuid4()
        mock_messages = [
            MagicMock(
                role=MagicMock(value="user"),
                content="Hello, how are you?",
                created_at=datetime.utcnow(),
                id=uuid4(),
            ),
            MagicMock(
                role=MagicMock(value="assistant"),
                content="I'm doing well, thank you!",
                created_at=datetime.utcnow(),
                id=uuid4(),
            ),
        ]
        mock_chat_service.get_chat_history.return_value = mock_messages

        # Mock semantic search to return empty results
        with patch.object(memory_service, "search_semantic", return_value=[]):
            context = await memory_service.get_context_for_chat(
                chat_id=chat_id, user_id=sample_user_id, max_tokens=2000
            )

        # Verify context contains recent messages
        assert "Recent Messages" in context
        assert "Hello, how are you?" in context
        assert "I'm doing well, thank you!" in context

    @pytest.mark.asyncio
    async def test_get_context_for_chat_with_memories(
        self, memory_service, mock_chat_service, sample_user_id, sample_memory
    ):
        """Test context assembly with relevant memories."""
        # Setup mocks
        chat_id = uuid4()
        mock_chat_service.get_chat_history.return_value = []

        # Mock semantic search to return memories
        with patch.object(memory_service, "search_semantic", return_value=[(sample_memory, 0.8)]):
            context = await memory_service.get_context_for_chat(
                chat_id=chat_id, user_id=sample_user_id, max_tokens=2000
            )

        # Verify context contains memories
        assert "Relevant Memories" in context
        assert sample_memory.summary in context

    @pytest.mark.asyncio
    async def test_ingest_from_chat_success(
        self,
        memory_service,
        mock_chat_service,
        mock_memory_repository,
        sample_user_id,
        sample_memory,
    ):
        """Test successful memory ingestion from chat."""
        # Setup mocks
        chat_id = uuid4()
        mock_messages = [
            MagicMock(
                role=MagicMock(value="user"),
                content="This is an important decision about our project",
                created_at=datetime.utcnow(),
                id=uuid4(),
            )
        ]
        mock_chat_service.get_chat_history.return_value = mock_messages
        mock_memory_repository.create.return_value = sample_memory

        # Mock important segment extraction
        with patch.object(
            memory_service,
            "_extract_important_segments",
            return_value=[
                {
                    "content": "important decision about our project",
                    "importance": 7,
                    "message_ids": [str(mock_messages[0].id)],
                    "tags": ["decision", "planning"],
                }
            ],
        ):
            with patch.object(memory_service, "_link_related_memories", return_value=None):
                results = await memory_service.ingest_from_chat(
                    chat_id=chat_id, user_id=sample_user_id, min_importance=6
                )

        # Verify results
        assert len(results) == 1
        assert results[0] == sample_memory

        # Verify chat history was retrieved
        mock_chat_service.get_chat_history.assert_called_once()

    @pytest.mark.asyncio
    async def test_ingest_from_chat_no_messages(
        self, memory_service, mock_chat_service, sample_user_id
    ):
        """Test ingestion from chat with no messages."""
        # Setup mock
        chat_id = uuid4()
        mock_chat_service.get_chat_history.return_value = []

        # Perform ingestion
        results = await memory_service.ingest_from_chat(chat_id=chat_id, user_id=sample_user_id)

        # Verify no results
        assert len(results) == 0

    @pytest.mark.asyncio
    async def test_extract_topics(self, memory_service):
        """Test topic extraction from messages."""
        messages = [
            {"content": "We need to decide on the architecture for our new system"},
            {"content": "The database design should be scalable and efficient"},
            {"content": "Let's implement this using microservices pattern"},
        ]

        topics = memory_service._extract_topics(messages)

        # Verify topics were extracted
        assert len(topics) > 0
        assert any("architecture" in topic.lower() for topic in topics)
        assert any("database" in topic.lower() for topic in topics)

    @pytest.mark.asyncio
    async def test_deduplicate_memories(self, memory_service, sample_memory):
        """Test memory deduplication."""
        # Create duplicate memories
        duplicate_list = [
            (sample_memory, 0.8),
            (sample_memory, 0.7),  # Same memory ID
            (
                Memory(
                    id=uuid4(),
                    content="different",
                    summary="diff",
                    qdrant_collection="test",
                    qdrant_point_id="test2",
                    embedding_model="test",
                    memory_type=MemoryType.CONVERSATION,
                    source_type=SourceType.MANUAL,
                    importance=5,
                    confidence=0.8,
                    access_count=0,
                    tags={},
                    extra_metadata={},
                    created_at=datetime.utcnow(),
                    updated_at=datetime.utcnow(),
                    user_id=uuid4(),
                ),
                0.6,
            ),
        ]

        deduplicated = memory_service._deduplicate_memories(duplicate_list)

        # Verify duplicates were removed
        assert len(deduplicated) == 2
        assert deduplicated[0][0].id == sample_memory.id
        assert deduplicated[1][0].id != sample_memory.id

    @pytest.mark.asyncio
    async def test_get_memory_stats(self, memory_service, mock_memory_repository, sample_user_id):
        """Test memory statistics retrieval."""
        # Setup mocks
        mock_memory_repository.get_by_user.return_value = [MagicMock()] * 10
        mock_memory_repository.get_important.return_value = [MagicMock()] * 5
        mock_memory_repository.get_recent.return_value = [MagicMock()] * 3

        # Get stats
        stats = await memory_service.get_memory_stats(sample_user_id)

        # Verify stats
        assert stats["total_memories"] == 10
        assert stats["important_memories"] == 5
        assert stats["recent_memories"] == 3
        assert "collections" in stats
        assert stats["embedding_model"] == "all-MiniLM-L6-v2"
        assert stats["embedding_dimension"] == 384

    @pytest.mark.asyncio
    async def test_initialize_collections(self, memory_service, mock_qdrant_service):
        """Test collection initialization."""
        # Setup mock
        mock_qdrant_service.collection_exists.return_value = False

        # Initialize collections
        await memory_service.initialize_collections()

        # Verify collections were created
        assert mock_qdrant_service.create_collection.call_count > 0

    @pytest.mark.asyncio
    async def test_group_messages(self, memory_service):
        """Test message grouping."""
        now = datetime.utcnow()
        messages = [
            {"content": "Hello", "created_at": now.isoformat()},
            {"content": "How are you?", "created_at": (now + timedelta(minutes=2)).isoformat()},
            {"content": "I'm fine", "created_at": (now + timedelta(minutes=10)).isoformat()},
        ]

        groups = memory_service._group_messages(messages)

        # Verify grouping
        assert len(groups) == 2  # First two messages grouped, third separate
        assert len(groups[0]) == 2
        assert len(groups[1]) == 1

    @pytest.mark.asyncio
    async def test_calculate_segment_importance(self, memory_service):
        """Test segment importance calculation."""
        # High importance segment
        important_messages = [
            {"role": "user", "content": "We need to decide on the architecture"},
            {"role": "assistant", "content": "Let me help you choose the best approach"},
        ]

        importance = memory_service._calculate_segment_importance(important_messages)
        assert importance >= 6  # Should be high due to decision words

        # Low importance segment
        low_importance_messages = [
            {"role": "user", "content": "hi"},
            {"role": "assistant", "content": "hello"},
        ]

        importance = memory_service._calculate_segment_importance(low_importance_messages)
        assert importance < 6  # Should be lower


class TestMemoryServiceIntegration:
    """Integration tests for MemoryService with real dependencies."""

    @pytest.mark.asyncio
    async def test_memory_service_integration(self):
        """Test memory service with real dependencies (if available)."""
        # This test would require real database and Qdrant connections
        # For now, we'll skip it as it requires external services
        pytest.skip("Integration test requires real database and Qdrant connections")
