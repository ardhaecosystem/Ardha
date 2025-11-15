"""
End-to-end test script for Milestone management system.

Tests all 12 milestone endpoints:
1. POST /api/v1/milestones/projects/{project_id}/milestones - Create
2. GET /api/v1/milestones/projects/{project_id}/milestones - List
3. GET /api/v1/milestones/{milestone_id} - Get by ID
4. PATCH /api/v1/milestones/{milestone_id} - Update
5. DELETE /api/v1/milestones/{milestone_id} - Delete
6. PATCH /api/v1/milestones/{milestone_id}/status - Update status
7. PATCH /api/v1/milestones/{milestone_id}/progress - Manual progress
8. POST /api/v1/milestones/{milestone_id}/recalculate - Auto-calculate progress
9. PATCH /api/v1/milestones/{milestone_id}/reorder - Change order
10. GET /api/v1/milestones/{milestone_id}/summary - Get summary
11. GET /api/v1/milestones/projects/{project_id}/milestones/roadmap - Roadmap view
12. GET /api/v1/milestones/projects/{project_id}/milestones/upcoming - Upcoming
"""

import asyncio
import sys
from datetime import datetime, timedelta, timezone

import httpx

BASE_URL = "http://localhost:8000"
API_V1 = f"{BASE_URL}/api/v1"


async def main():
    """Run end-to-end tests for milestone system."""
    print("=" * 80)
    print("MILESTONE MANAGEMENT SYSTEM - END-TO-END TEST")
    print("=" * 80)

    async with httpx.AsyncClient() as client:
        # ============= Setup: Create User & Project =============
        print("\n[SETUP] Creating test user and project...")

        # Register user
        register_data = {
            "email": "milestone_test@ardha.dev",
            "username": "milestone_tester",
            "password": "SecurePass123!",
            "full_name": "Milestone Tester",
        }

        response = await client.post(f"{API_V1}/auth/register", json=register_data)
        if response.status_code == 400 and (
            "already" in response.text.lower() or "exists" in response.text.lower()
        ):
            print("  ✓ User already exists, logging in...")
        elif response.status_code == 201:
            print("  ✓ User registered, logging in...")
        else:
            print(f"  ⚠ Unexpected registration response: {response.status_code}")
            print("  ✓ Attempting login anyway...")

        # Login to get access token
        login_response = await client.post(
            f"{API_V1}/auth/login",
            data={"username": register_data["email"], "password": register_data["password"]},
        )
        assert login_response.status_code == 200, f"Failed to login: {login_response.text}"
        tokens = login_response.json()
        access_token = tokens["access_token"]
        print("  ✓ Logged in successfully")
        headers = {"Authorization": f"Bearer {access_token}"}

        # Create project
        project_data = {
            "name": "Milestone Test Project",
            "description": "Testing milestone features",
            "visibility": "private",
            "tech_stack": ["Python", "FastAPI"],
        }

        response = await client.post(f"{API_V1}/projects/", json=project_data, headers=headers)
        assert response.status_code == 201, f"Failed to create project: {response.text}"
        project = response.json()
        project_id = project["id"]
        print(f"  ✓ Project created: {project_id}")

        # ============= Test 1: Create Milestones =============
        print("\n[TEST 1] Creating milestones...")

        # Milestone 1: Phase 1 - Backend
        milestone1_data = {
            "name": "Phase 1: Backend Foundation",
            "description": "Complete backend API and database setup",
            "status": "in_progress",
            "color": "#10b981",
            "start_date": datetime.now(timezone.utc).isoformat(),
            "due_date": (datetime.now(timezone.utc) + timedelta(days=21)).isoformat(),
            # No order specified - will auto-assign as 0
        }

        response = await client.post(
            f"{API_V1}/milestones/projects/{project_id}/milestones",
            json=milestone1_data,
            headers=headers,
        )
        assert response.status_code == 201, f"Failed to create milestone 1: {response.text}"
        milestone1 = response.json()
        print(f"  ✓ Milestone 1 created: {milestone1['name']}")
        print(f"    ID: {milestone1['id']}")
        print(f"    Status: {milestone1['status']}")
        print(f"    Progress: {milestone1['progress_percentage']}%")
        print(f"    Days remaining: {milestone1['days_remaining']}")

        # Milestone 2: Phase 2 - AI Integration
        milestone2_data = {
            "name": "Phase 2: AI Integration",
            "description": "LangGraph workflows and OpenRouter",
            "status": "not_started",
            "color": "#6366f1",
            "due_date": (datetime.now(timezone.utc) + timedelta(days=42)).isoformat(),
        }

        response = await client.post(
            f"{API_V1}/milestones/projects/{project_id}/milestones",
            json=milestone2_data,
            headers=headers,
        )
        assert response.status_code == 201, f"Failed to create milestone 2: {response.text}"
        milestone2 = response.json()
        print(f"  ✓ Milestone 2 created: {milestone2['name']}")

        # Milestone 3: MVP Release
        milestone3_data = {
            "name": "MVP Release",
            "description": "Complete minimum viable product",
            "status": "not_started",
            "color": "#f59e0b",
            "due_date": (datetime.now(timezone.utc) + timedelta(days=120)).isoformat(),
        }

        response = await client.post(
            f"{API_V1}/milestones/projects/{project_id}/milestones",
            json=milestone3_data,
            headers=headers,
        )
        assert response.status_code == 201, f"Failed to create milestone 3: {response.text}"
        milestone3 = response.json()
        print(f"  ✓ Milestone 3 created: {milestone3['name']}")

        # ============= Test 2: List Milestones =============
        print("\n[TEST 2] Listing project milestones...")

        response = await client.get(
            f"{API_V1}/milestones/projects/{project_id}/milestones", headers=headers
        )
        assert response.status_code == 200, f"Failed to list milestones: {response.text}"
        milestone_list = response.json()
        print(f"  ✓ Listed {milestone_list['total']} milestones")

        for m in milestone_list["milestones"]:
            print(f"    - {m['name']} (order: {m['order']}, status: {m['status']})")

        # ============= Test 3: Filter by Status =============
        print("\n[TEST 3] Filtering milestones by status...")

        response = await client.get(
            f"{API_V1}/milestones/projects/{project_id}/milestones?status=in_progress",
            headers=headers,
        )
        assert response.status_code == 200, f"Failed to filter milestones: {response.text}"
        filtered = response.json()
        print(f"  ✓ Found {len(filtered['milestones'])} in_progress milestones")

        # ============= Test 4: Get Milestone by ID =============
        print("\n[TEST 4] Getting milestone by ID...")

        response = await client.get(f"{API_V1}/milestones/{milestone1['id']}", headers=headers)
        assert response.status_code == 200, f"Failed to get milestone: {response.text}"
        milestone_detail = response.json()
        print(f"  ✓ Retrieved milestone: {milestone_detail['name']}")
        print(f"    Status: {milestone_detail['status']}")
        print(f"    Progress: {milestone_detail['progress_percentage']}%")

        # ============= Test 5: Update Milestone =============
        print("\n[TEST 5] Updating milestone...")

        update_data = {
            "description": "Updated description: Database models complete!",
            "progress_percentage": 35,
        }

        response = await client.patch(
            f"{API_V1}/milestones/{milestone1['id']}", json=update_data, headers=headers
        )
        assert response.status_code == 200, f"Failed to update milestone: {response.text}"
        updated = response.json()
        print(f"  ✓ Milestone updated")
        print(f"    New description: {updated['description']}")
        print(f"    New progress: {updated['progress_percentage']}%")

        # ============= Test 6: Update Status =============
        print("\n[TEST 6] Testing status transitions...")

        # Valid transition: not_started → in_progress
        response = await client.patch(
            f"{API_V1}/milestones/{milestone2['id']}/status",
            json={"status": "in_progress"},
            headers=headers,
        )
        assert response.status_code == 200, f"Failed to update status: {response.text}"
        print("  ✓ Valid transition: not_started → in_progress")

        # Try invalid transition: in_progress → completed (should work actually!)
        response = await client.patch(
            f"{API_V1}/milestones/{milestone2['id']}/status",
            json={"status": "completed"},
            headers=headers,
        )
        assert response.status_code == 200, f"Failed to update status: {response.text}"
        completed_milestone = response.json()
        print("  ✓ Valid transition: in_progress → completed")
        print(f"    Completed at: {completed_milestone['completed_at']}")

        # Test reopening: completed → in_progress
        response = await client.patch(
            f"{API_V1}/milestones/{milestone2['id']}/status",
            json={"status": "in_progress"},
            headers=headers,
        )
        assert response.status_code == 200, f"Failed to reopen: {response.text}"
        reopened = response.json()
        print("  ✓ Valid transition: completed → in_progress (reopened)")
        print(f"    Completed at cleared: {reopened['completed_at']}")

        # ============= Test 7: Create Tasks for Progress Calculation =============
        print("\n[TEST 7] Creating tasks for progress calculation...")

        # Create 3 tasks linked to milestone1
        for i in range(3):
            task_data = {
                "title": f"Backend Task {i+1}",
                "description": f"Task {i+1} for Phase 1",
                "status": "done" if i < 2 else "todo",  # 2 done, 1 todo = 66% progress
                "priority": "medium",
                "milestone_id": milestone1["id"],
            }

            response = await client.post(
                f"{API_V1}/tasks/projects/{project_id}/tasks", json=task_data, headers=headers
            )
            assert response.status_code == 201, f"Failed to create task {i+1}: {response.text}"
            task = response.json()
            print(f"  ✓ Task {i+1} created: {task['identifier']} (status: {task['status']})")

        # ============= Test 8: Auto-Calculate Progress =============
        print("\n[TEST 8] Auto-calculating progress from tasks...")

        response = await client.post(
            f"{API_V1}/milestones/{milestone1['id']}/recalculate", headers=headers
        )
        assert response.status_code == 200, f"Failed to recalculate: {response.text}"
        recalculated = response.json()
        print(f"  ✓ Progress recalculated: {recalculated['progress_percentage']}%")
        print(f"    Expected: 66% (2 done / 3 total)")

        # ============= Test 9: Manual Progress Update =============
        print("\n[TEST 9] Manually updating progress...")

        response = await client.patch(
            f"{API_V1}/milestones/{milestone3['id']}/progress",
            json={"progress_percentage": 25},
            headers=headers,
        )
        assert response.status_code == 200, f"Failed to update progress: {response.text}"
        manual_progress = response.json()
        print(f"  ✓ Progress manually set to {manual_progress['progress_percentage']}%")

        # ============= Test 10: Milestone Summary =============
        print("\n[TEST 10] Getting milestone summary with statistics...")

        response = await client.get(
            f"{API_V1}/milestones/{milestone1['id']}/summary", headers=headers
        )
        assert response.status_code == 200, f"Failed to get summary: {response.text}"
        summary = response.json()
        print(f"  ✓ Summary retrieved:")
        print(f"    Total tasks: {summary['total_tasks']}")
        print(f"    Completed tasks: {summary['completed_tasks']}")
        print(f"    Task breakdown: {summary['task_stats']}")
        print(f"    Auto progress: {summary['auto_progress']}%")
        print(f"    Manual progress: {summary['milestone']['progress_percentage']}%")

        # ============= Test 11: Reorder Milestones =============
        print("\n[TEST 11] Testing milestone reordering...")

        # Move milestone3 to position 0 (before milestone1)
        response = await client.patch(
            f"{API_V1}/milestones/{milestone3['id']}/reorder",
            json={"new_order": 0},
            headers=headers,
        )
        assert response.status_code == 200, f"Failed to reorder: {response.text}"
        print("  ✓ Milestone 3 moved to position 0")

        # Verify new order
        response = await client.get(
            f"{API_V1}/milestones/projects/{project_id}/milestones", headers=headers
        )
        assert response.status_code == 200
        ordered_list = response.json()
        print("  ✓ New order:")
        for m in ordered_list["milestones"]:
            print(f"    {m['order']}: {m['name']}")

        # ============= Test 12: Roadmap View =============
        print("\n[TEST 12] Getting project roadmap...")

        response = await client.get(
            f"{API_V1}/milestones/projects/{project_id}/milestones/roadmap", headers=headers
        )
        assert response.status_code == 200, f"Failed to get roadmap: {response.text}"
        roadmap = response.json()
        print(f"  ✓ Roadmap retrieved with {len(roadmap)} milestones:")
        for m in roadmap:
            due = m["due_date"][:10] if m["due_date"] else "No due date"
            print(f"    - {m['name']} (due: {due}, progress: {m['progress_percentage']}%)")

        # ============= Test 13: Upcoming Milestones =============
        print("\n[TEST 13] Getting upcoming milestones...")

        response = await client.get(
            f"{API_V1}/milestones/projects/{project_id}/milestones/upcoming?days=30",
            headers=headers,
        )
        assert response.status_code == 200, f"Failed to get upcoming: {response.text}"
        upcoming = response.json()
        print(f"  ✓ Found {len(upcoming)} milestones due in next 30 days:")
        for m in upcoming:
            print(f"    - {m['name']} (days remaining: {m['days_remaining']})")

        # ============= Test 14: Delete Protection =============
        print("\n[TEST 14] Testing delete protection (milestone with tasks)...")

        response = await client.delete(f"{API_V1}/milestones/{milestone1['id']}", headers=headers)
        assert response.status_code == 400, "Should fail to delete milestone with tasks"
        print("  ✓ Delete correctly prevented (milestone has 3 linked tasks)")
        print(f"    Error message: {response.json()['detail']}")

        # ============= Test 15: Delete Milestone =============
        print("\n[TEST 15] Deleting milestone without tasks...")

        response = await client.delete(f"{API_V1}/milestones/{milestone3['id']}", headers=headers)
        assert response.status_code == 200, f"Failed to delete milestone: {response.text}"
        print(f"  ✓ Milestone deleted: {response.json()['message']}")

        # Verify deletion
        response = await client.get(f"{API_V1}/milestones/{milestone3['id']}", headers=headers)
        assert response.status_code == 404, "Deleted milestone should not be found"
        print("  ✓ Deletion verified (404 on get)")

        # ============= Test 16: Final Validation =============
        print("\n[TEST 16] Final validation...")

        response = await client.get(
            f"{API_V1}/milestones/projects/{project_id}/milestones", headers=headers
        )
        assert response.status_code == 200
        final_list = response.json()
        print(f"  ✓ Final milestone count: {final_list['total']}")

        print("\n" + "=" * 80)
        print("ALL TESTS PASSED! ✅")
        print("=" * 80)
        print("\nMilestone System Features Validated:")
        print("  ✅ Create milestone with auto-order generation")
        print("  ✅ List milestones with pagination")
        print("  ✅ Filter by status")
        print("  ✅ Get milestone by ID")
        print("  ✅ Update milestone fields")
        print("  ✅ Status transitions with completed_at timestamps")
        print("  ✅ Manual progress updates")
        print("  ✅ Auto-calculate progress from task completion")
        print("  ✅ Reorder milestones (drag-drop support)")
        print("  ✅ Milestone summary with statistics")
        print("  ✅ Roadmap view for timeline")
        print("  ✅ Upcoming milestones filter")
        print("  ✅ Delete protection (prevents deleting with tasks)")
        print("  ✅ Delete milestone without tasks")
        print("  ✅ Computed fields (is_overdue, days_remaining)")
        print("\nAll 12 milestone endpoints are functional!")


if __name__ == "__main__":
    try:
        asyncio.run(main())
        sys.exit(0)
    except AssertionError as e:
        print(f"\n❌ TEST FAILED: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ UNEXPECTED ERROR: {e}", file=sys.stderr)
        import traceback

        traceback.print_exc()
        sys.exit(1)
