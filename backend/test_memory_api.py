"""
Test script for Memory API endpoints.

This script validates the memory API implementation by testing
the endpoint definitions and request/response schemas.
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))


def test_imports():
    """Test that all memory API modules can be imported."""
    try:
        # Test request schemas
        from ardha.schemas.requests.memory import (
            CreateMemoryRequest,
            IngestChatRequest,
            SearchMemoryRequest,
            UpdateMemoryRequest,
        )

        print("✅ Memory request schemas imported successfully")

        # Test response schemas
        from ardha.schemas.responses.memory import (
            MemoryCreationResponse,
            MemoryResponse,
            MemorySearchResponse,
            MemoryStatsResponse,
        )

        print("✅ Memory response schemas imported successfully")

        # Test API routes
        from ardha.api.v1.routes.memories import router
        print("✅ Memory API routes imported successfully")

        # Test main app includes memory router
        from ardha.main import app

        routes = [getattr(route, "path", str(route)) for route in app.routes]
        memory_routes = [r for r in routes if "memories" in r]

        if memory_routes:
            print(f"✅ Memory routes found in main app: {memory_routes}")
        else:
            print("❌ No memory routes found in main app")
            return False

        return True

    except ImportError as e:
        print(f"❌ Import error: {e}")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False


def test_request_schemas():
    """Test memory request schema validation."""
    try:
        from ardha.schemas.requests.memory import CreateMemoryRequest

        # Test valid request
        CreateMemoryRequest(
            content="Test memory content",
            memory_type="fact",
            importance=8,
            tags=["test", "validation"],
            project_id=None,
            metadata=None,
        )
        print("✅ Valid CreateMemoryRequest created successfully")

        # Test tag validation
        request_with_tags = CreateMemoryRequest(
            content="Test memory with tags",
            memory_type="conversation",
            tags=["TAG1", "tag2", "TAG3"],  # Should be normalized to lowercase
            project_id=None,
            metadata=None,
        )
        expected_tags = {"tag1", "tag2", "tag3"}
        actual_tags = set(request_with_tags.tags or [])

        if actual_tags == expected_tags:
            print("✅ Tag validation and normalization working correctly")
        else:
            print(f"❌ Tag validation failed. Expected: {expected_tags}, Got: {actual_tags}")
            return False

        return True

    except Exception as e:
        print(f"❌ Request schema validation error: {e}")
        return False


def test_endpoint_definitions():
    """Test that all required endpoints are defined."""
    try:
        from fastapi.routing import APIRoute

        from ardha.api.v1.routes.memories import router

        # Expected endpoints
        expected_endpoints = {
            "POST /memories": "create_memory",
            "GET /memories/search": "search_memories",
            "GET /memories": "list_memories",
            "GET /memories/{memory_id}": "get_memory",
            "PATCH /memories/{memory_id}": "update_memory",
            "DELETE /memories/{memory_id}": "delete_memory",
            "POST /memories/{memory_id}/archive": "archive_memory",
            "GET /memories/{memory_id}/related": "get_related_memories",
            "POST /memories/ingest/chat/{chat_id}": "ingest_chat_memories",
            "POST /memories/ingest/workflow/{workflow_id}": "ingest_workflow_memory",
            "GET /memories/context/chat/{chat_id}": "get_chat_context",
            "GET /memories/stats": "get_memory_stats",
        }

        actual_endpoints = {}
        for route in router.routes:
            if isinstance(route, APIRoute):
                methods = list(route.methods)
                if methods:
                    method = methods[0]  # Take first method
                    path = route.path
                    key = f"{method} {path}"
                    actual_endpoints[key] = route.endpoint.__name__

        # Check endpoints
        missing_endpoints = []
        for expected_key, expected_name in expected_endpoints.items():
            if expected_key in actual_endpoints:
                actual_name = actual_endpoints[expected_key]
                if actual_name == expected_name:
                    print(f"✅ {expected_key} -> {expected_name}")
                else:
                    print(f"⚠️  {expected_key} -> {actual_name} (expected {expected_name})")
            else:
                missing_endpoints.append(expected_key)
                print(f"❌ Missing endpoint: {expected_key}")

        if missing_endpoints:
            print(f"❌ {len(missing_endpoints)} endpoints missing")
            return False
        else:
            print(f"✅ All {len(expected_endpoints)} endpoints defined")
            return True

    except Exception as e:
        print(f"❌ Endpoint definition test error: {e}")
        return False


def main():
    """Run all tests."""
    print("🧪 Testing Memory API Implementation\n")

    tests = [
        ("Import Test", test_imports),
        ("Request Schema Test", test_request_schemas),
        ("Endpoint Definition Test", test_endpoint_definitions),
    ]

    passed = 0
    total = len(tests)

    for test_name, test_func in tests:
        print(f"\n--- {test_name} ---")
        if test_func():
            passed += 1
            print(f"✅ {test_name} PASSED")
        else:
            print(f"❌ {test_name} FAILED")

    print(f"\n--- Test Summary ---")
    print(f"Passed: {passed}/{total}")

    if passed == total:
        print("🎉 All tests passed! Memory API implementation is ready.")
        return True
    else:
        print("⚠️  Some tests failed. Please review the implementation.")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
