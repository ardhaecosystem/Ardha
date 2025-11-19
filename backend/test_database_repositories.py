"""
Validation test script for database repositories.

Tests repository initialization, imports, and basic functionality.
"""

import asyncio
import sys
from pathlib import Path
from uuid import uuid4

# Add backend/src to path
backend_path = Path(__file__).parent / "src"
sys.path.insert(0, str(backend_path))


async def test_imports():
    """Test that all repository classes can be imported."""
    print("\n🔍 Testing Repository Imports...")
    
    try:
        from ardha.repositories import (
            DatabaseRepository,
            DatabasePropertyRepository,
            DatabaseEntryRepository,
        )
        print("✅ All database repository classes imported successfully")
        return True
    except ImportError as e:
        print(f"❌ Import failed: {e}")
        return False


async def test_repository_initialization():
    """Test repository initialization with mock session."""
    print("\n🔍 Testing Repository Initialization...")
    
    try:
        from unittest.mock import AsyncMock, MagicMock
        from ardha.repositories import (
            DatabaseRepository,
            DatabasePropertyRepository,
            DatabaseEntryRepository,
        )
        
        # Create mock session
        mock_session = AsyncMock()
        mock_session.execute = AsyncMock()
        mock_session.flush = AsyncMock()
        mock_session.refresh = AsyncMock()
        mock_session.add = MagicMock()
        mock_session.delete = AsyncMock()
        
        # Initialize repositories
        db_repo = DatabaseRepository(mock_session)
        prop_repo = DatabasePropertyRepository(mock_session)
        entry_repo = DatabaseEntryRepository(mock_session)
        
        assert db_repo.db == mock_session
        assert prop_repo.db == mock_session
        assert entry_repo.db == mock_session
        
        print("✅ All repositories initialized correctly")
        return True
    except Exception as e:
        print(f"❌ Initialization failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_method_counts():
    """Test that all required methods exist."""
    print("\n🔍 Testing Method Counts...")
    
    try:
        from ardha.repositories import (
            DatabaseRepository,
            DatabasePropertyRepository,
            DatabaseEntryRepository,
        )
        
        # DatabaseRepository should have 15 methods
        db_methods = [
            "create", "get_by_id", "get_by_project", "list_templates",
            "get_template_instances", "update", "archive", "delete",
            "count_by_project", "search_by_name", "duplicate",
            "get_entry_count", "get_with_stats", "reorder_positions",
            "get_by_name"
        ]
        
        for method in db_methods:
            assert hasattr(DatabaseRepository, method), f"Missing method: {method}"
        print(f"✅ DatabaseRepository has all {len(db_methods)} required methods")
        
        # DatabasePropertyRepository should have 12 methods
        prop_methods = [
            "create", "get_by_id", "get_by_database", "update", "delete",
            "reorder", "get_by_type", "get_formula_properties",
            "get_rollup_properties", "get_relation_properties",
            "get_required_properties", "count_by_database"
        ]
        
        for method in prop_methods:
            assert hasattr(DatabasePropertyRepository, method), f"Missing method: {method}"
        print(f"✅ DatabasePropertyRepository has all {len(prop_methods)} required methods")
        
        # DatabaseEntryRepository should have 18 methods
        entry_methods = [
            "create", "get_by_id", "get_by_database", "count_by_database",
            "update", "archive", "delete", "bulk_create", "bulk_update",
            "bulk_delete", "get_value", "set_value",
            "get_entries_by_property_value", "reorder_entries",
            "get_created_by_user", "get_recently_updated",
            "duplicate_entry", "search_entries"
        ]
        
        for method in entry_methods:
            assert hasattr(DatabaseEntryRepository, method), f"Missing method: {method}"
        print(f"✅ DatabaseEntryRepository has all {len(entry_methods)} required methods")
        
        return True
    except AssertionError as e:
        print(f"❌ Method check failed: {e}")
        return False
    except Exception as e:
        print(f"❌ Method count test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_type_hints():
    """Test that methods have proper type hints."""
    print("\n🔍 Testing Type Hints...")
    
    try:
        from ardha.repositories import (
            DatabaseRepository,
            DatabasePropertyRepository,
            DatabaseEntryRepository,
        )
        import inspect
        from typing import get_type_hints
        
        # Check a few key methods for type hints
        test_cases = [
            (DatabaseRepository, "create"),
            (DatabaseRepository, "get_by_id"),
            (DatabaseRepository, "get_with_stats"),
            (DatabasePropertyRepository, "get_by_type"),
            (DatabasePropertyRepository, "reorder"),
            (DatabaseEntryRepository, "get_by_database"),
            (DatabaseEntryRepository, "bulk_create"),
            (DatabaseEntryRepository, "set_value"),
        ]
        
        for repo_class, method_name in test_cases:
            method = getattr(repo_class, method_name)
            hints = get_type_hints(method)
            assert "return" in hints, f"{repo_class.__name__}.{method_name} missing return type"
        
        print("✅ All tested methods have proper type hints")
        return True
    except Exception as e:
        print(f"❌ Type hint test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_model_references():
    """Test that model references are correct."""
    print("\n🔍 Testing Model References...")
    
    try:
        from ardha.models.database import Database
        from ardha.models.database_property import DatabaseProperty
        from ardha.models.database_entry import DatabaseEntry
        from ardha.models.database_entry_value import DatabaseEntryValue
        
        print("✅ All database models imported successfully")
        
        # Check model relationships exist
        assert hasattr(Database, "properties"), "Database missing properties relationship"
        assert hasattr(Database, "views"), "Database missing views relationship"
        assert hasattr(Database, "entries"), "Database missing entries relationship"
        assert hasattr(DatabaseProperty, "database"), "DatabaseProperty missing database relationship"
        assert hasattr(DatabaseEntry, "values"), "DatabaseEntry missing values relationship"
        assert hasattr(DatabaseEntryValue, "entry"), "DatabaseEntryValue missing entry relationship"
        assert hasattr(DatabaseEntryValue, "property"), "DatabaseEntryValue missing property relationship"
        
        print("✅ All model relationships verified")
        return True
    except Exception as e:
        print(f"❌ Model reference test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_async_patterns():
    """Test that all methods are async and follow patterns."""
    print("\n🔍 Testing Async Patterns...")
    
    try:
        from ardha.repositories import (
            DatabaseRepository,
            DatabasePropertyRepository,
            DatabaseEntryRepository,
        )
        import inspect
        
        # Check that all public methods are async
        for repo_class in [DatabaseRepository, DatabasePropertyRepository, DatabaseEntryRepository]:
            for name, method in inspect.getmembers(repo_class, predicate=inspect.isfunction):
                if not name.startswith("_") and name != "__init__":
                    assert inspect.iscoroutinefunction(method), \
                        f"{repo_class.__name__}.{name} is not async"
        
        print("✅ All public methods are properly async")
        return True
    except AssertionError as e:
        print(f"❌ Async pattern check failed: {e}")
        return False
    except Exception as e:
        print(f"❌ Async pattern test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    """Run all validation tests."""
    print("=" * 60)
    print("DATABASE REPOSITORY VALIDATION TESTS")
    print("=" * 60)
    
    results = []
    
    # Run tests
    results.append(("Imports", await test_imports()))
    results.append(("Initialization", await test_repository_initialization()))
    results.append(("Method Counts", await test_method_counts()))
    results.append(("Type Hints", await test_type_hints()))
    results.append(("Model References", await test_model_references()))
    results.append(("Async Patterns", await test_async_patterns()))
    
    # Summary
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASSED" if result else "❌ FAILED"
        print(f"{test_name:.<40} {status}")
    
    print(f"\nOverall: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 ALL TESTS PASSED! Database repositories are ready for service layer.")
    else:
        print(f"\n⚠️  {total - passed} test(s) failed. Review errors above.")
    
    return passed == total


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)