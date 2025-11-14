"""
Test fixtures for memory system testing.

Provides mock data and fixtures for testing memory operations with local embeddings.
"""

from datetime import datetime, timedelta
from typing import List
from uuid import uuid4

import numpy as np
import pytest

from ardha.models.chat import Chat
from ardha.models.memory import Memory, MemoryLink
from ardha.models.project import Project
from ardha.models.user import User


@pytest.fixture
def mock_local_embedding():
    """Mock embedding from all-MiniLM-L6-v2 (384 dimensions)"""
    return np.random.rand(384).tolist()


@pytest.fixture
def mock_embedding_batch():
    """Mock batch of embeddings"""
    return [np.random.rand(384).tolist() for _ in range(5)]


@pytest.fixture
def test_user():
    """Create test user fixture"""
    return User(
        id=uuid4(),
        email="test@example.com",
        username="testuser",
        full_name="Test User",
        is_active=True,
        is_verified=True,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )


@pytest.fixture
def test_project(test_user):
    """Create test project fixture"""
    return Project(
        id=uuid4(),
        name="Test Project",
        description="A test project for memory testing",
        owner_id=test_user.id,
        status="active",
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )


@pytest.fixture
def test_chat(test_user):
    """Create test chat fixture"""
    return Chat(
        id=uuid4(),
        user_id=test_user.id,
        title="Test Chat",
        status="active",
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )


@pytest.fixture
def sample_memory(test_user, test_project):
    """Create sample memory for testing"""
    return Memory(
        id=uuid4(),
        user_id=test_user.id,
        project_id=test_project.id,
        content="Team decided to use PostgreSQL for the database",
        summary="Database decision: PostgreSQL",
        qdrant_collection="fact_memories",
        qdrant_point_id=str(uuid4()),
        embedding_model="all-MiniLM-L6-v2",
        memory_type="fact",
        source_type="manual",
        importance=8,
        confidence=0.9,
        access_count=0,
        last_accessed=datetime.utcnow(),
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )


@pytest.fixture
def sample_memories_batch(test_user, test_project):
    """Create batch of memories for testing"""
    memories = []
    memory_types = ["conversation", "workflow", "fact", "entity"]

    for i, mem_type in enumerate(memory_types):
        memory = Memory(
            id=uuid4(),
            user_id=test_user.id,
            project_id=test_project.id if i % 2 == 0 else None,
            content=f"Test memory content {i}",
            summary=f"Summary {i}",
            qdrant_collection=f"{mem_type}_memories",
            qdrant_point_id=str(uuid4()),
            embedding_model="all-MiniLM-L6-v2",
            memory_type=mem_type,
            source_type="manual",
            importance=5 + i,
            confidence=0.8,
            access_count=i,
            last_accessed=datetime.utcnow() - timedelta(days=i),
            created_at=datetime.utcnow() - timedelta(days=i),
            updated_at=datetime.utcnow(),
        )
        memories.append(memory)

    return memories


@pytest.fixture
def sample_memory_links(sample_memories_batch):
    """Create memory relationship links"""
    links = []
    for i in range(len(sample_memories_batch) - 1):
        link = MemoryLink(
            id=uuid4(),
            memory_from_id=sample_memories_batch[i].id,
            memory_to_id=sample_memories_batch[i + 1].id,
            relationship_type="related_to",
            strength=0.7,
            created_at=datetime.utcnow(),
        )
        links.append(link)
    return links


@pytest.fixture
def mock_qdrant_search_results(sample_memories_batch, mock_embedding_batch):
    """Mock Qdrant search results"""
    from qdrant_client.models import ScoredPoint

    results = []
    for i, memory in enumerate(sample_memories_batch[:3]):
        result = ScoredPoint(
            id=memory.qdrant_point_id,
            version=1,
            score=0.9 - (i * 0.1),
            payload={
                "user_id": str(memory.user_id),
                "content": memory.content[:500],
                "memory_type": memory.memory_type,
            },
            vector=mock_embedding_batch[i],
        )
        results.append(result)

    return results


@pytest.fixture
async def mock_embedding_service(monkeypatch, mock_local_embedding):
    """Mock embedding service for testing"""
    from ardha.services.embedding_service import LocalEmbeddingService

    async def mock_generate_embedding(self, text: str):
        return mock_local_embedding

    async def mock_generate_batch(self, texts: List[str], batch_size: int = 32):
        return [mock_local_embedding for _ in texts]

    monkeypatch.setattr(LocalEmbeddingService, "generate_embedding", mock_generate_embedding)
    monkeypatch.setattr(LocalEmbeddingService, "generate_embeddings_batch", mock_generate_batch)


@pytest.fixture
def mock_redis():
    """Mock Redis client for testing"""
    from unittest.mock import AsyncMock, MagicMock


    redis_mock = MagicMock()
    redis_mock.get = AsyncMock(return_value=None)
    redis_mock.setex = AsyncMock()
    redis_mock.ping = AsyncMock(return_value=True)
    redis_mock.keys = AsyncMock(return_value=[])
    redis_mock.delete = AsyncMock()
    redis_mock.close = AsyncMock()

    return redis_mock


@pytest.fixture
def mock_qdrant():
    """Mock Qdrant service for testing"""
    from unittest.mock import AsyncMock, MagicMock

    qdrant_mock = MagicMock()
    qdrant_mock.collection_exists = AsyncMock(return_value=True)
    qdrant_mock.create_collection = AsyncMock()
    qdrant_mock.upsert_vectors = AsyncMock()
    qdrant_mock.search_similar = AsyncMock(return_value=[])
    qdrant_mock.delete_points = AsyncMock()
    qdrant_mock.get_all_points = AsyncMock(return_value=[])
    qdrant_mock.optimize_collection = AsyncMock()

    return qdrant_mock


@pytest.fixture
def completed_workflow():
    """Create a mock completed workflow for testing"""
    return {
        "id": uuid4(),
        "workflow_type": "research",
        "status": "completed",
        "input_data": {"query": "test research"},
        "output_data": {"results": "test results"},
        "started_at": datetime.utcnow() - timedelta(hours=1),
        "completed_at": datetime.utcnow(),
    }
