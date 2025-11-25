"""
Integration tests for memory API endpoints.

Tests the complete memory system including API routes, service layer,
and database operations.
"""

from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
class TestMemoryAPI:
    """Test memory API endpoints"""

    async def test_create_memory_endpoint(self, test_client, test_user, mock_local_embedding):
        """Test POST /api/v1/memories endpoint"""
        # Mock embedding service
        with patch("ardha.services.memory_service.get_embedding_service") as mock_embedding:
            mock_service = AsyncMock()
            mock_service.generate_embedding.return_value = mock_local_embedding
            mock_embedding.return_value = mock_service

            # Mock Qdrant service
            with patch("ardha.services.memory_service.get_qdrant_service") as mock_qdrant:
                mock_qdrant_service = AsyncMock()
                mock_qdrant_service.upsert_vectors.return_value = None
                mock_qdrant_service.collection_exists.return_value = True
                mock_qdrant.return_value = mock_qdrant_service

                # Test data
                memory_data = {
                    "content": "Test memory content for API",
                    "memory_type": "fact",
                    "source_type": "manual",
                    "importance": 7,
                    "tags": ["test", "api"],
                }

                response = await test_client.post(
                    "/api/v1/memories",
                    json=memory_data,
                    headers={"Authorization": f"Bearer {test_user['token']}"},
                )

                assert response.status_code == 201
                data = response.json()
                memory_response = data["memory"]  # Memory is nested under "memory" key
                assert memory_response["content"] == memory_data["content"]
                assert memory_response["memory_type"] == memory_data["memory_type"]
                assert memory_response["importance"] == memory_data["importance"]
                assert "id" in memory_response  # Check ID is present in memory object

    async def test_get_memories_endpoint(self, test_client, test_user, sample_memories_batch):
        """Test GET /api/v1/memories endpoint"""
        # Add memories to database
        from ardha.core.database import get_db

        async for db in get_db():
            for memory in sample_memories_batch:
                db.add(memory)
            await db.commit()
            break

        response = await test_client.get(
            "/api/v1/memories", headers={"Authorization": f"Bearer {test_user['token']}"}
        )

        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "total" in data
        assert isinstance(data["items"], list)

    async def test_get_memory_by_id_endpoint(self, test_client, test_user, sample_memory):
        """Test GET /api/v1/memories/{memory_id} endpoint"""
        # Add memory to database
        from ardha.core.database import get_db

        async for db in get_db():
            db.add(sample_memory)
            await db.commit()
            break

        response = await test_client.get(
            f"/api/v1/memories/{sample_memory.id}",
            headers={"Authorization": f"Bearer {test_user.id}"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == str(sample_memory.id)
        assert data["content"] == sample_memory.content

    async def test_get_memory_by_id_not_found(self, test_client, test_user):
        """Test GET /api/v1/memories/{memory_id} with non-existent ID"""
        fake_id = uuid4()

        response = await test_client.get(
            f"/api/v1/memories/{fake_id}", headers={"Authorization": f"Bearer {test_user['token']}"}
        )

        assert response.status_code == 404

    async def test_update_memory_endpoint(self, test_client, test_user, sample_memory):
        """Test PUT /api/v1/memories/{memory_id} endpoint"""
        # Add memory to database
        from ardha.core.database import get_db

        async for db in get_db():
            db.add(sample_memory)
            await db.commit()
            break

        update_data = {"content": "Updated memory content", "importance": 9}

        response = await test_client.put(
            f"/api/v1/memories/{sample_memory.id}",
            json=update_data,
            headers={"Authorization": f"Bearer {test_user['token']}"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["content"] == update_data["content"]
        assert data["importance"] == update_data["importance"]

    async def test_delete_memory_endpoint(self, test_client, test_user, sample_memory):
        """Test DELETE /api/v1/memories/{memory_id} endpoint"""
        # Add memory to database
        from ardha.core.database import get_db

        async for db in get_db():
            db.add(sample_memory)
            await db.commit()
            break

        response = await test_client.delete(
            f"/api/v1/memories/{sample_memory.id}",
            headers={"Authorization": f"Bearer {test_user.id}"},
        )

        assert response.status_code == 204

        # Verify memory is deleted
        get_response = await test_client.get(
            f"/api/v1/memories/{sample_memory.id}",
            headers={"Authorization": f"Bearer {test_user['token']}"},
        )
        assert get_response.status_code == 404

    async def test_search_memories_endpoint(
        self, test_client, test_user, mock_qdrant_search_results
    ):
        """Test GET /api/v1/memories/search endpoint"""
        # Mock Qdrant service
        with patch("ardha.services.memory_service.get_qdrant_service") as mock_qdrant:
            mock_qdrant_service = AsyncMock()
            mock_qdrant_service.search_similar.return_value = mock_qdrant_search_results
            mock_qdrant_service.collection_exists.return_value = True
            mock_qdrant.return_value = mock_qdrant_service

            # Mock embedding service
            with patch("ardha.services.memory_service.get_embedding_service") as mock_embedding:
                mock_service = AsyncMock()
                mock_service.generate_embedding.return_value = [0.1] * 384
                mock_embedding.return_value = mock_service

                response = await test_client.get(
                    "/api/v1/memories/search?query=test search&limit=5",
                    headers={"Authorization": f"Bearer {test_user['token']}"},
                )

                assert response.status_code == 200
                data = response.json()
                assert "results" in data
                assert isinstance(data["results"], list)

    async def test_get_memory_stats_endpoint(self, test_client, test_user, sample_memories_batch):
        """Test GET /api/v1/memories/stats endpoint"""
        # Add memories to database
        from ardha.core.database import get_db

        async for db in get_db():
            for memory in sample_memories_batch:
                db.add(memory)
            await db.commit()
            break

        response = await test_client.get(
            "/api/v1/memories/stats", headers={"Authorization": f"Bearer {test_user.id}"}
        )

        assert response.status_code == 200
        data = response.json()
        assert "total_memories" in data
        assert "important_memories" in data
        assert "recent_memories" in data

    async def test_create_memory_link_endpoint(self, test_client, test_user, sample_memories_batch):
        """Test POST /api/v1/memories/links endpoint"""
        # Add memories to database
        from ardha.core.database import get_db

        async for db in get_db():
            for memory in sample_memories_batch:
                db.add(memory)
            await db.commit()
            break

        link_data = {
            "from_id": str(sample_memories_batch[0].id),
            "to_id": str(sample_memories_batch[1].id),
            "relationship_type": "related_to",
            "strength": 0.8,
        }

        response = await test_client.post(
            "/api/v1/memories/links",
            json=link_data,
            headers={"Authorization": f"Bearer {test_user['token']}"},
        )

        assert response.status_code == 201
        data = response.json()
        assert data["relationship_type"] == link_data["relationship_type"]
        assert data["strength"] == link_data["strength"]

    async def test_get_related_memories_endpoint(
        self, test_client, test_user, sample_memories_batch, sample_memory_links
    ):
        """Test GET /api/v1/memories/{memory_id}/related endpoint"""
        # Add memories and links to database
        from ardha.core.database import get_db

        async for db in get_db():
            for memory in sample_memories_batch:
                db.add(memory)
            for link in sample_memory_links:
                db.add(link)
            await db.commit()
            break

        response = await test_client.get(
            f"/api/v1/memories/{sample_memories_batch[0].id}/related",
            headers={"Authorization": f"Bearer {test_user['token']}"},
        )

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    async def test_ingest_from_chat_endpoint(self, test_client, test_user, sample_chat_messages):
        """Test POST /api/v1/memories/ingest/chat endpoint"""
        # Mock chat service
        with patch("ardha.services.memory_service.ChatService") as mock_chat_service:
            mock_service = AsyncMock()
            mock_service.get_chat_history.return_value = sample_chat_messages
            mock_chat_service.return_value = mock_service

            # Mock embedding and Qdrant services
            with patch("ardha.services.memory_service.get_embedding_service") as mock_embedding:
                mock_emb_service = AsyncMock()
                mock_emb_service.generate_embedding.return_value = [0.1] * 384
                mock_embedding.return_value = mock_emb_service

                with patch("ardha.services.memory_service.get_qdrant_service") as mock_qdrant:
                    mock_qdrant_service = AsyncMock()
                    mock_qdrant_service.upsert_vectors.return_value = None
                    mock_qdrant_service.collection_exists.return_value = True
                    mock_qdrant.return_value = mock_qdrant_service

                    ingest_data = {"chat_id": str(uuid4()), "min_importance": 6}

                    response = await test_client.post(
                        "/api/v1/memories/ingest/chat",
                        json=ingest_data,
                        headers={"Authorization": f"Bearer {test_user['token']}"},
                    )

                    assert response.status_code == 200
                    data = response.json()
                    assert "ingested_count" in data
                    assert isinstance(data["ingested_count"], int)

    async def test_ingest_from_workflow_endpoint(self, test_client, test_user, completed_workflow):
        """Test POST /api/v1/memories/ingest/workflow endpoint"""
        # Mock embedding and Qdrant services
        with patch("ardha.services.memory_service.get_embedding_service") as mock_embedding:
            mock_emb_service = AsyncMock()
            mock_emb_service.generate_embedding.return_value = [0.1] * 384
            mock_embedding.return_value = mock_emb_service

            with patch("ardha.services.memory_service.get_qdrant_service") as mock_qdrant:
                mock_qdrant_service = AsyncMock()
                mock_qdrant_service.upsert_vectors.return_value = None
                mock_qdrant_service.collection_exists.return_value = True
                mock_qdrant.return_value = mock_qdrant_service

                ingest_data = {"workflow_id": str(completed_workflow.id)}

                response = await test_client.post(
                    "/api/v1/memories/ingest/workflow",
                    json=ingest_data,
                    headers={"Authorization": f"Bearer {test_user['token']}"},
                )

                assert response.status_code == 200
                data = response.json()
                assert "id" in data
                assert data["memory_type"] == "workflow"

    async def test_get_context_for_chat_endpoint(
        self, test_client, test_user, sample_chat_messages
    ):
        """Test GET /api/v1/memories/context/{chat_id} endpoint"""
        # Mock chat service
        with patch("ardha.services.memory_service.ChatService") as mock_chat_service:
            mock_service = AsyncMock()
            mock_service.get_chat_history.return_value = sample_chat_messages
            mock_chat_service.return_value = mock_service

            # Mock embedding and Qdrant services
            with patch("ardha.services.memory_service.get_embedding_service") as mock_embedding:
                mock_emb_service = AsyncMock()
                mock_emb_service.generate_embedding.return_value = [0.1] * 384
                mock_embedding.return_value = mock_emb_service

                with patch("ardha.services.memory_service.get_qdrant_service") as mock_qdrant:
                    mock_qdrant_service = AsyncMock()
                    mock_qdrant_service.search_similar.return_value = []
                    mock_qdrant_service.collection_exists.return_value = True
                    mock_qdrant.return_value = mock_qdrant_service

                    chat_id = uuid4()

                    response = await test_client.get(
                        f"/api/v1/memories/context/{chat_id}",
                        headers={"Authorization": f"Bearer {test_user['token']}"},
                    )

                    assert response.status_code == 200
                    data = response.json()
                    assert "context" in data
                    assert isinstance(data["context"], str)

    async def test_memory_pagination(self, test_client, test_user, sample_memories_batch):
        """Test memory list pagination"""
        # Add memories to database
        from ardha.core.database import get_db

        async for db in get_db():
            for memory in sample_memories_batch:
                db.add(memory)
            await db.commit()
            break

        # Test first page
        response = await test_client.get(
            "/api/v1/memories?skip=0&limit=2", headers={"Authorization": f"Bearer {test_user.id}"}
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) <= 2

        # Test second page
        response = await test_client.get(
            "/api/v1/memories?skip=2&limit=2",
            headers={"Authorization": f"Bearer {test_user['token']}"},
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) <= 2

    async def test_memory_filtering_by_type(self, test_client, test_user, sample_memories_batch):
        """Test filtering memories by type"""
        # Add memories to database
        from ardha.core.database import get_db

        async for db in get_db():
            for memory in sample_memories_batch:
                db.add(memory)
            await db.commit()
            break

        response = await test_client.get(
            "/api/v1/memories?memory_type=fact",
            headers={"Authorization": f"Bearer {test_user['token']}"},
        )

        assert response.status_code == 200
        data = response.json()
        # All returned memories should be of type 'fact'
        for memory in data["items"]:
            assert memory["memory_type"] == "fact"

    async def test_memory_filtering_by_project(
        self, test_client, test_user, sample_project, sample_memories_batch
    ):
        """Test filtering memories by project"""
        # Update memories to have project_id
        for memory in sample_memories_batch:
            memory.project_id = sample_project.id

        # Add memories to database
        from ardha.core.database import get_db

        async for db in get_db():
            db.add(sample_project)
            for memory in sample_memories_batch:
                db.add(memory)
            await db.commit()
            break

        response = await test_client.get(
            f"/api/v1/memories?project_id={sample_project.id}",
            headers={"Authorization": f"Bearer {test_user['token']}"},
        )

        assert response.status_code == 200
        data = response.json()
        # All returned memories should belong to the project
        for memory in data["items"]:
            assert memory["project_id"] == str(sample_project.id)

    async def test_unauthorized_access(self, test_client):
        """Test API access without authorization"""
        # Create a new client without auth headers
        from httpx import ASGITransport, AsyncClient

        from ardha.main import app

        unauthorized_client = AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        )

        response = await unauthorized_client.get("/api/v1/memories")
        assert response.status_code == 401

        # Test POST without auth using same unauthorized client
        response = await unauthorized_client.post("/api/v1/memories", json={})
        assert response.status_code == 401

    async def test_invalid_memory_data(self, test_client, test_user):
        """Test API with invalid memory data"""
        invalid_data = {
            "content": "",  # Empty content
            "memory_type": "invalid_type",
            "importance": 15,  # Invalid importance
        }

        response = await test_client.post(
            "/api/v1/memories",
            json=invalid_data,
            headers={"Authorization": f"Bearer {test_user['token']}"},
        )

        assert response.status_code == 422  # Validation error

    async def test_memory_link_validation(self, test_client, test_user, sample_memories_batch):
        """Test memory link creation validation"""
        # Add memories to database
        from ardha.core.database import get_db

        async for db in get_db():
            for memory in sample_memories_batch:
                db.add(memory)
            await db.commit()
            break

        # Test invalid link (same memory)
        invalid_link_data = {
            "from_id": str(sample_memories_batch[0].id),
            "to_id": str(sample_memories_batch[0].id),  # Same memory
            "relationship_type": "related_to",
            "strength": 0.8,
        }

        response = await test_client.post(
            "/api/v1/memories/links",
            json=invalid_link_data,
            headers={"Authorization": f"Bearer {test_user.id}"},
        )

        assert response.status_code == 400  # Bad request

    async def test_search_with_filters(self, test_client, test_user, mock_qdrant_search_results):
        """Test semantic search with filters"""
        # Mock Qdrant service
        with patch("ardha.services.memory_service.get_qdrant_service") as mock_qdrant:
            mock_qdrant_service = AsyncMock()
            mock_qdrant_service.search_similar.return_value = mock_qdrant_search_results
            mock_qdrant_service.collection_exists.return_value = True
            mock_qdrant.return_value = mock_qdrant_service

            # Mock embedding service
            with patch("ardha.services.memory_service.get_embedding_service") as mock_embedding:
                mock_service = AsyncMock()
                mock_service.generate_embedding.return_value = [0.1] * 384
                mock_embedding.return_value = mock_service

                response = await test_client.get(
                    "/api/v1/memories/search?query=test&memory_type=fact&min_score=0.7&limit=5",
                    headers={"Authorization": f"Bearer {test_user['token']}"},
                )

                assert response.status_code == 200
                data = response.json()
                assert "results" in data

    async def test_memory_export_endpoint(self, test_client, test_user, sample_memories_batch):
        """Test GET /api/v1/memories/export endpoint"""
        # Add memories to database
        from ardha.core.database import get_db

        async for db in get_db():
            for memory in sample_memories_batch:
                db.add(memory)
            await db.commit()
            break

        response = await test_client.get(
            "/api/v1/memories/export", headers={"Authorization": f"Bearer {test_user['token']}"}
        )

        assert response.status_code == 200
        data = response.json()
        assert "memories" in data
        assert "exported_at" in data
        assert isinstance(data["memories"], list)

    async def test_memory_import_endpoint(self, test_client, test_user):
        """Test POST /api/v1/memories/import endpoint"""
        # Mock embedding and Qdrant services
        with patch("ardha.services.memory_service.get_embedding_service") as mock_embedding:
            mock_emb_service = AsyncMock()
            mock_emb_service.generate_embedding.return_value = [0.1] * 384
            mock_embedding.return_value = mock_emb_service

            with patch("ardha.services.memory_service.get_qdrant_service") as mock_qdrant:
                mock_qdrant_service = AsyncMock()
                mock_qdrant_service.upsert_vectors.return_value = None
                mock_qdrant_service.collection_exists.return_value = True
                mock_qdrant.return_value = mock_qdrant_service

                import_data = {
                    "memories": [
                        {
                            "content": "Imported memory 1",
                            "memory_type": "fact",
                            "source_type": "manual",
                            "importance": 7,
                        },
                        {
                            "content": "Imported memory 2",
                            "memory_type": "conversation",
                            "source_type": "chat",
                            "importance": 6,
                        },
                    ]
                }

                response = await test_client.post(
                    "/api/v1/memories/import",
                    json=import_data,
                    headers={"Authorization": f"Bearer {test_user['token']}"},
                )

                assert response.status_code == 200
                data = response.json()
                assert "imported_count" in data
                assert data["imported_count"] == 2

    async def test_memory_health_endpoint(self, test_client, test_user):
        """Test GET /api/v1/memories/health endpoint"""
        response = await test_client.get(
            "/api/v1/memories/health", headers={"Authorization": f"Bearer {test_user['token']}"}
        )

        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert "collections" in data
        assert "embedding_service" in data
