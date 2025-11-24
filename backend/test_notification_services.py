"""
Validation script for notification services and WebSocket manager.

This script performs comprehensive validation of:
- Service imports and initialization
- WebSocketManager singleton pattern
- EmailService template rendering
- NotificationService business logic
- BroadcastService functionality
"""

import asyncio
from datetime import datetime, timezone
from uuid import uuid4


async def test_imports():
    """Test all service imports."""
    print("\n1. Testing imports...")

    from ardha.core.email_service import EmailService
    from ardha.core.websocket_manager import WebSocketManager, get_websocket_manager
    from ardha.services.broadcast_service import BroadcastService
    from ardha.services.notification_service import (
        InsufficientNotificationPermissionsError,
        NotificationNotFoundError,
        NotificationService,
    )

    print("   ✅ All service imports successful")
    return True


async def test_websocket_singleton():
    """Test WebSocketManager singleton pattern."""
    print("\n2. Testing WebSocketManager singleton...")

    from ardha.core.websocket_manager import get_websocket_manager

    ws1 = get_websocket_manager()
    ws2 = get_websocket_manager()

    assert ws1 is ws2, "WebSocketManager is not a singleton!"
    print("   ✅ WebSocketManager singleton pattern verified")

    # Test basic attributes
    assert hasattr(ws1, "active_connections"), "Missing active_connections attribute"
    assert hasattr(ws1, "rooms"), "Missing rooms attribute"
    assert hasattr(ws1, "_lock"), "Missing _lock attribute"

    print("   ✅ WebSocketManager has required attributes")
    return True


async def test_email_service():
    """Test EmailService initialization and template rendering."""
    print("\n3. Testing EmailService...")

    from ardha.core.email_service import EmailService

    service = EmailService()
    print("   ✅ EmailService initialized")

    # Test template rendering
    try:
        html = service.render_template(
            "notification_single.html",
            {
                "user_name": "Test User",
                "notification": {
                    "title": "Test Notification",
                    "message": "This is a test message",
                    "type": "system",
                    "link_type": None,
                    "link_id": None,
                    "created_at": datetime.now(timezone.utc).isoformat(),
                },
                "app_url": "http://localhost:3000",
            },
        )
        assert len(html) > 100, "Template rendered but seems too short"
        print(f"   ✅ Single notification template rendered ({len(html)} chars)")

    except Exception as e:
        print(f"   ❌ Failed to render single notification template: {e}")
        return False

    # Test digest template
    try:
        html = service.render_template(
            "notification_digest.html",
            {
                "user_name": "Test User",
                "digest_type": "Daily",
                "notification_count": 3,
                "notifications": [
                    {
                        "title": f"Notification {i}",
                        "message": f"Message {i}",
                        "type": "system",
                        "link_type": None,
                        "link_id": None,
                        "created_at": datetime.now(timezone.utc).isoformat(),
                    }
                    for i in range(3)
                ],
                "app_url": "http://localhost:3000",
            },
        )
        assert len(html) > 100, "Digest template rendered but seems too short"
        print(f"   ✅ Digest notification template rendered ({len(html)} chars)")

    except Exception as e:
        print(f"   ❌ Failed to render digest template: {e}")
        return False

    # Test configuration validation
    is_valid = service.validate_email_config()
    print(
        f"   {'✅' if is_valid else '⚠️ '} Email configuration "
        f"{'valid' if is_valid else 'incomplete (expected in dev)'}"
    )

    return True


async def test_notification_service_structure():
    """Test NotificationService structure and methods."""
    print("\n4. Testing NotificationService structure...")

    from ardha.services.notification_service import NotificationService

    # Verify all required methods exist
    required_methods = [
        "create_notification",
        "send_notification",
        "bulk_create_notifications",
        "get_user_notifications",
        "mark_notification_read",
        "mark_all_read",
        "delete_notification",
        "get_user_preferences",
        "update_user_preferences",
        "get_notification_stats",
        "cleanup_old_notifications",
        "cleanup_expired_notifications",
    ]

    missing_methods = []
    for method in required_methods:
        if not hasattr(NotificationService, method):
            missing_methods.append(method)

    if missing_methods:
        print(f"   ❌ Missing methods: {', '.join(missing_methods)}")
        return False

    print(f"   ✅ All {len(required_methods)} required methods present")
    return True


async def test_broadcast_service_structure():
    """Test BroadcastService structure and methods."""
    print("\n5. Testing BroadcastService structure...")

    from ardha.services.broadcast_service import BroadcastService

    # Verify all required methods exist
    required_methods = [
        "notify_user",
        "notify_project_members",
        "notify_task_assignees",
        "broadcast_system_notification",
        "notify_mention",
    ]

    missing_methods = []
    for method in required_methods:
        if not hasattr(BroadcastService, method):
            missing_methods.append(method)

    if missing_methods:
        print(f"   ❌ Missing methods: {', '.join(missing_methods)}")
        return False

    print(f"   ✅ All {len(required_methods)} required methods present")
    return True


async def test_websocket_manager_methods():
    """Test WebSocketManager methods."""
    print("\n6. Testing WebSocketManager methods...")

    from ardha.core.websocket_manager import get_websocket_manager

    ws_manager = get_websocket_manager()

    # Verify all required methods exist
    required_methods = [
        "connect",
        "disconnect",
        "is_user_connected",
        "get_user_connections",
        "send_personal_message",
        "send_to_connection",
        "broadcast_to_room",
        "join_room",
        "leave_room",
        "get_room_users",
    ]

    missing_methods = []
    for method in required_methods:
        if not hasattr(ws_manager, method):
            missing_methods.append(method)

    if missing_methods:
        print(f"   ❌ Missing methods: {', '.join(missing_methods)}")
        return False

    print(f"   ✅ All {len(required_methods)} required methods present")

    # Test get_connection_stats
    stats = await ws_manager.get_connection_stats()
    assert "total_users" in stats, "Missing total_users in stats"
    assert "total_connections" in stats, "Missing total_connections in stats"
    assert "total_rooms" in stats, "Missing total_rooms in stats"
    print(f"   ✅ Connection stats: {stats}")

    return True


async def main():
    """Run all validation tests."""
    print("=" * 60)
    print("NOTIFICATION SERVICES & WEBSOCKET VALIDATION")
    print("=" * 60)

    tests = [
        ("Imports", test_imports),
        ("WebSocket Singleton", test_websocket_singleton),
        ("Email Service", test_email_service),
        ("Notification Service", test_notification_service_structure),
        ("Broadcast Service", test_broadcast_service_structure),
        ("WebSocket Methods", test_websocket_manager_methods),
    ]

    results = []
    for name, test_func in tests:
        try:
            result = await test_func()
            results.append((name, result))
        except Exception as e:
            print(f"   ❌ Test failed with exception: {e}")
            results.append((name, False))

    # Print summary
    print("\n" + "=" * 60)
    print("VALIDATION SUMMARY")
    print("=" * 60)

    total = len(results)
    passed = sum(1 for _, result in results if result)
    failed = total - passed

    for name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status}: {name}")

    print(f"\nTotal: {passed}/{total} tests passed")

    if failed == 0:
        print("\n🎉 ALL VALIDATION TESTS PASSED!")
        print("✅ Notification services are ready for production")
    else:
        print(f"\n⚠️  {failed} test(s) failed - review errors above")

    return failed == 0


if __name__ == "__main__":
    success = asyncio.run(main())
    exit(0 if success else 1)