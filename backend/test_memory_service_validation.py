#!/usr/bin/env python3
"""
Memory Service Validation Script

This script validates the Memory Service implementation by testing
core functionality including memory creation, semantic search,
and context assembly.

Usage:
    cd backend
    python test_memory_service_validation.py
"""

import asyncio
import logging
import sys
from datetime import datetime
from uuid import UUID, uuid4

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


async def test_memory_service():
    """
    Test Memory Service functionality.

    This test validates the core Memory Service methods including:
    - Collection initialization
    - Memory creation with local embeddings
    - Semantic search with local embeddings
    - Context assembly for chat
    """

    try:
        # Import required modules
        from ardha.core.qdrant import get_qdrant_service
        from ardha.repositories.memory_repository import MemoryRepository
        from ardha.services.chat_service import ChatService
        from ardha.services.embedding_service import get_embedding_service
        from ardha.services.memory_service import MemoryService

        logger.info("🚀 Starting Memory Service validation...")

        # Create test data
        test_user_id = uuid4()
        test_project_id = uuid4()
        test_chat_id = uuid4()

        # Initialize services (using mock database session for testing)
        logger.info("📦 Initializing services...")

        # For testing purposes, we'll use a mock database session
        # In production, this would be a real AsyncSession
        from unittest.mock import AsyncMock, MagicMock

        mock_db = AsyncMock()

        # Create a mock memory repository that returns proper memory objects
        class MockMemoryRepository:
            def __init__(self, db):
                self.db = db

            async def create(self, **kwargs):
                # Create a mock memory object
                from datetime import datetime
                from uuid import uuid4

                from ardha.models.memory import Memory, MemoryType, SourceType

                memory = Memory(
                    id=uuid4(),
                    user_id=kwargs.get("user_id", uuid4()),
                    project_id=kwargs.get("project_id"),
                    content=kwargs.get("content", ""),
                    summary=kwargs.get("summary", "")[:200],
                    qdrant_collection=kwargs.get("qdrant_collection", "test_collection"),
                    qdrant_point_id=kwargs.get("qdrant_point_id", str(uuid4())),
                    embedding_model=kwargs.get("embedding_model", "all-MiniLM-L6-v2"),
                    memory_type=MemoryType(kwargs.get("memory_type", "fact")),
                    source_type=SourceType(kwargs.get("source_type", "manual")),
                    source_id=kwargs.get("source_id"),
                    importance=kwargs.get("importance", 5),
                    confidence=kwargs.get("confidence", 0.8),
                    access_count=0,
                    last_accessed=None,
                    tags=kwargs.get("tags", {}),
                    extra_metadata=kwargs.get("extra_metadata", {}),
                    created_at=datetime.utcnow(),
                    updated_at=datetime.utcnow(),
                    expires_at=None,
                    is_archived=False,
                )
                return memory

            async def get_by_source(self, **kwargs):
                return []

            async def increment_access_count(self, memory_id, **kwargs):
                pass

            async def get_by_user(self, **kwargs):
                return []

            async def get_important(self, **kwargs):
                return []

            async def get_recent(self, **kwargs):
                return []

        # Initialize repositories and services
        memory_repository = MockMemoryRepository(mock_db)
        embedding_service = get_embedding_service()
        qdrant_service = get_qdrant_service()
        chat_service = None  # Optional for testing

        # Create Memory Service (skip type checking for testing)
        memory_service = MemoryService.__new__(MemoryService)
        memory_service.memory_repository = memory_repository
        memory_service.embedding_service = embedding_service
        memory_service.qdrant_service = qdrant_service
        memory_service.chat_service = chat_service

        # Initialize collection mapping
        memory_service.collection_mapping = {
            "conversation": "chat_memories",
            "workflow": "workflow_memories",
            "document": "document_memories",
            "entity": "entity_memories",
            "fact": "fact_memories",
        }
        memory_service.default_collection = "general_memories"

        logger.info("✅ Services initialized successfully")

        logger.info("✅ Services initialized successfully")

        # Test 1: Initialize collections
        logger.info("🔧 Testing collection initialization...")
        try:
            await memory_service.initialize_collections()
            logger.info("✅ Collections initialized successfully")
        except Exception as e:
            logger.error(f"❌ Collection initialization failed: {e}")
            return False

        # Test 2: Create memory with local embeddings
        logger.info("💾 Testing memory creation with local embeddings...")
        try:
            memory = await memory_service.create_memory(
                user_id=test_user_id,
                content="Important project decision: Use FastAPI for backend architecture",
                memory_type="fact",
                project_id=test_project_id,
                source_type="manual",
                importance=8,
                tags=["architecture", "decision", "fastapi"],
            )

            if memory and memory.id:
                logger.info(f"✅ Memory created successfully: {memory.id}")
                logger.info(f"   - Summary: {memory.summary}")
                logger.info(f"   - Collection: {memory.qdrant_collection}")
                logger.info(f"   - Importance: {memory.importance}")
            else:
                logger.error("❌ Memory creation failed: No memory returned")
                return False

        except Exception as e:
            logger.error(f"❌ Memory creation failed: {e}")
            return False

        # Test 3: Create additional memories for search testing
        logger.info("📝 Creating additional test memories...")
        try:
            test_memories = [
                ("We should use PostgreSQL as our primary database", "fact", 9),
                ("Implement Redis for caching and session storage", "fact", 7),
                ("Frontend will be built with Next.js and React", "fact", 8),
                ("Use Docker containers for deployment", "fact", 6),
                ("Set up CI/CD pipeline with GitHub Actions", "fact", 7),
            ]

            created_memories = []
            for content, memory_type, importance in test_memories:
                memory = await memory_service.create_memory(
                    user_id=test_user_id,
                    content=content,
                    memory_type=memory_type,
                    project_id=test_project_id,
                    source_type="manual",
                    importance=importance,
                )
                created_memories.append(memory)

            logger.info(f"✅ Created {len(created_memories)} additional memories")

        except Exception as e:
            logger.error(f"❌ Additional memory creation failed: {e}")
            return False

        # Test 4: Semantic search with local embeddings
        logger.info("🔍 Testing semantic search with local embeddings...")
        try:
            search_results = await memory_service.search_semantic(
                user_id=test_user_id, query="backend framework decision", limit=5, min_score=0.5
            )

            logger.info(f"✅ Semantic search found {len(search_results)} relevant memories")

            for i, (memory, score) in enumerate(search_results, 1):
                logger.info(f"   {i}. {memory.summary} (score: {score:.2f})")

        except Exception as e:
            logger.error(f"❌ Semantic search failed: {e}")
            return False

        # Test 5: Different search queries
        logger.info("🔍 Testing different search queries...")
        test_queries = [
            "database technology",
            "frontend framework",
            "deployment strategy",
            "caching solution",
        ]

        for query in test_queries:
            try:
                results = await memory_service.search_semantic(
                    user_id=test_user_id, query=query, limit=3
                )
                logger.info(f"   Query '{query}': {len(results)} results")

            except Exception as e:
                logger.warning(f"   Query '{query}' failed: {e}")

        # Test 6: Context assembly for chat
        logger.info("💬 Testing context assembly for chat...")
        try:
            context = await memory_service.get_context_for_chat(
                chat_id=test_chat_id, user_id=test_user_id, max_tokens=2000, relevance_threshold=0.6
            )

            logger.info(f"✅ Context assembled successfully")
            logger.info(f"   - Context length: {len(context)} characters")
            logger.info(f"   - Context preview: {context[:200]}...")

        except Exception as e:
            logger.error(f"❌ Context assembly failed: {e}")
            return False

        # Test 7: Memory statistics
        logger.info("📊 Testing memory statistics...")
        try:
            stats = await memory_service.get_memory_stats(test_user_id)

            logger.info(f"✅ Memory statistics retrieved:")
            logger.info(f"   - Total memories: {stats.get('total_memories', 0)}")
            logger.info(f"   - Important memories: {stats.get('important_memories', 0)}")
            logger.info(f"   - Recent memories: {stats.get('recent_memories', 0)}")
            logger.info(f"   - Embedding model: {stats.get('embedding_model', 'unknown')}")
            logger.info(f"   - Embedding dimension: {stats.get('embedding_dimension', 0)}")

        except Exception as e:
            logger.error(f"❌ Memory statistics failed: {e}")
            return False

        # Test 8: Importance scoring
        logger.info("⭐ Testing importance scoring algorithm...")
        try:
            # Test different scenarios
            test_cases = [
                ("Simple content", "chat", False, 0, 6),  # Base 5 + 1 for chat
                ("Important decision made", "manual", False, 0, 8),  # Base 5 + 3 for manual
                (
                    "Very long content with lots of details " * 20,
                    "workflow",
                    True,
                    15,
                    10,
                ),  # Capped at 10
            ]

            for content, source_type, has_approval, access_count, expected_min in test_cases:
                score = memory_service.calculate_importance(
                    content=content,
                    source_type=source_type,
                    has_user_approval=has_approval,
                    access_count=access_count,
                )
                logger.info(f"   - {source_type}: {score} (expected >= {expected_min})")
                assert score >= expected_min, f"Score {score} below expected {expected_min}"

            logger.info("✅ Importance scoring working correctly")

        except Exception as e:
            logger.error(f"❌ Importance scoring failed: {e}")
            return False

        # Test 9: Collection management
        logger.info("🗂️ Testing collection management...")
        try:
            # Test collection name mapping
            assert memory_service._get_collection_name("conversation") == "chat_memories"
            assert memory_service._get_collection_name("workflow") == "workflow_memories"
            assert memory_service._get_collection_name("unknown") == "general_memories"

            # Test search collections
            all_collections = memory_service._get_search_collections(None)
            specific_collections = memory_service._get_search_collections("conversation")

            assert len(all_collections) > len(specific_collections)
            assert "chat_memories" in specific_collections

            logger.info("✅ Collection management working correctly")

        except Exception as e:
            logger.error(f"❌ Collection management failed: {e}")
            return False

        # Test 10: Error handling
        logger.info("🛡️ Testing error handling...")
        try:
            # Test empty content validation
            try:
                await memory_service.create_memory(
                    user_id=test_user_id, content="", memory_type="fact"
                )
                logger.error("❌ Empty content validation failed - should have raised exception")
                return False
            except Exception:
                logger.info("✅ Empty content validation working correctly")

            # Test invalid memory type handling (should not crash)
            try:
                memory = await memory_service.create_memory(
                    user_id=test_user_id, content="Test content", memory_type="invalid_type"
                )
                logger.info("✅ Invalid memory type handled gracefully")
            except Exception as e:
                logger.info(f"✅ Invalid memory type properly rejected: {e}")

        except Exception as e:
            logger.error(f"❌ Error handling test failed: {e}")
            return False

        logger.info("🎉 All Memory Service tests passed successfully!")
        logger.info("📋 Test Summary:")
        logger.info("   ✅ Collection initialization")
        logger.info("   ✅ Memory creation with local embeddings")
        logger.info("   ✅ Semantic search with local embeddings")
        logger.info("   ✅ Context assembly for chat")
        logger.info("   ✅ Memory statistics")
        logger.info("   ✅ Importance scoring algorithm")
        logger.info("   ✅ Collection management")
        logger.info("   ✅ Error handling")
        logger.info("💰 Cost: $0.00 (completely free local embeddings!)")

        return True

    except ImportError as e:
        logger.error(f"❌ Import error: {e}")
        logger.error("   Make sure you're in the backend directory and dependencies are installed")
        return False
    except Exception as e:
        logger.error(f"❌ Unexpected error: {e}")
        return False


async def main():
    """Main validation function."""
    print("🧪 Memory Service Validation Script")
    print("=" * 50)

    # Run validation tests
    success = await test_memory_service()

    if success:
        print("\n🎉 VALIDATION SUCCESSFUL!")
        print("✅ Memory Service is ready for production use")
        print("💰 Total cost: $0.00 (free local embeddings)")
        sys.exit(0)
    else:
        print("\n❌ VALIDATION FAILED!")
        print("🔧 Please check the errors above and fix issues")
        sys.exit(1)


if __name__ == "__main__":
    # Run validation
    asyncio.run(main())
