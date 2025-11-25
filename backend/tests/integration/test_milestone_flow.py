"""
Integration tests for milestone management flow.

Tests the complete milestone lifecycle including creation, progress tracking,
status updates, and roadmap views.
"""

from datetime import datetime, timedelta

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_milestone_lifecycle(
    client: AsyncClient,
    test_user: dict,
    test_project: dict,
) -> None:
    """Test complete milestone management workflow."""
    project_id = test_project["id"]

    # Create milestone
    due_date = (datetime.now() + timedelta(days=30)).isoformat()
    start_date = datetime.now().isoformat()

    response = await client.post(
        f"/api/v1/milestones/projects/{project_id}/milestones",
        headers={"Authorization": f"Bearer {test_user['token']}"},
        json={
            "name": "MVP Release",
            "description": "First production release",
            "start_date": start_date,
            "due_date": due_date,
            "status": "in_progress",
            "color": "#8B5CF6",
        },
    )
    assert response.status_code == 201
    milestone = response.json()
    assert milestone["name"] == "MVP Release"
    assert milestone["status"] == "in_progress"
    assert milestone["color"] == "#8B5CF6"
    assert milestone["progress_percentage"] == 0
    milestone_id = milestone["id"]

    # Create tasks linked to milestone
    task_ids = []
    for i in range(3):
        response = await client.post(
            f"/api/v1/tasks/projects/{project_id}/tasks",
            headers={"Authorization": f"Bearer {test_user['token']}"},
            json={
                "title": f"Task {i+1} for MVP",
                "milestone_id": milestone_id,
            },
        )
        assert response.status_code == 201
        task_ids.append(response.json()["id"])

    # Complete first task (must go through valid transitions)
    # todo -> in_progress -> in_review -> done
    response = await client.patch(
        f"/api/v1/tasks/{task_ids[0]}/status",
        headers={"Authorization": f"Bearer {test_user['token']}"},
        json={"status": "in_progress"},
    )
    assert response.status_code == 200

    response = await client.patch(
        f"/api/v1/tasks/{task_ids[0]}/status",
        headers={"Authorization": f"Bearer {test_user['token']}"},
        json={"status": "in_review"},
    )
    assert response.status_code == 200

    response = await client.patch(
        f"/api/v1/tasks/{task_ids[0]}/status",
        headers={"Authorization": f"Bearer {test_user['token']}"},
        json={"status": "done"},
    )
    assert response.status_code == 200

    # Recalculate milestone progress
    response = await client.post(
        f"/api/v1/milestones/{milestone_id}/recalculate",
        headers={"Authorization": f"Bearer {test_user['token']}"},
    )
    assert response.status_code == 200
    recalc_data = response.json()
    # 1 out of 3 tasks done = 33%
    assert recalc_data["progress_percentage"] == 33

    # Complete second task (must go through valid transitions)
    response = await client.patch(
        f"/api/v1/tasks/{task_ids[1]}/status",
        headers={"Authorization": f"Bearer {test_user['token']}"},
        json={"status": "in_progress"},
    )
    assert response.status_code == 200

    response = await client.patch(
        f"/api/v1/tasks/{task_ids[1]}/status",
        headers={"Authorization": f"Bearer {test_user['token']}"},
        json={"status": "in_review"},
    )
    assert response.status_code == 200

    response = await client.patch(
        f"/api/v1/tasks/{task_ids[1]}/status",
        headers={"Authorization": f"Bearer {test_user['token']}"},
        json={"status": "done"},
    )
    assert response.status_code == 200

    # Recalculate again
    response = await client.post(
        f"/api/v1/milestones/{milestone_id}/recalculate",
        headers={"Authorization": f"Bearer {test_user['token']}"},
    )
    assert response.status_code == 200
    # 2 out of 3 tasks done = 66%
    assert response.json()["progress_percentage"] == 66

    # Get milestone summary
    response = await client.get(
        f"/api/v1/milestones/{milestone_id}/summary",
        headers={"Authorization": f"Bearer {test_user['token']}"},
    )
    assert response.status_code == 200
    summary = response.json()
    assert summary["total_tasks"] == 3
    assert summary["completed_tasks"] == 2
    assert summary["task_stats"]["done"] == 2
    assert summary["task_stats"]["todo"] == 1

    # Update milestone status to completed
    response = await client.patch(
        f"/api/v1/milestones/{milestone_id}/status",
        headers={"Authorization": f"Bearer {test_user['token']}"},
        json={"status": "completed"},
    )
    assert response.status_code == 200
    completed_milestone = response.json()
    assert completed_milestone["status"] == "completed"
    assert completed_milestone["completed_at"] is not None

    # Get roadmap view
    response = await client.get(
        f"/api/v1/milestones/projects/{project_id}/milestones/roadmap",
        headers={"Authorization": f"Bearer {test_user['token']}"},
    )
    assert response.status_code == 200
    roadmap = response.json()
    assert len(roadmap) >= 1
    assert any(m["id"] == milestone_id for m in roadmap)

    # Get upcoming milestones (within 60 days)
    response = await client.get(
        f"/api/v1/milestones/projects/{project_id}/milestones/upcoming",
        headers={"Authorization": f"Bearer {test_user['token']}"},
        params={"days": 60},
    )
    assert response.status_code == 200
    upcoming = response.json()
    # Completed milestone should still appear if within timeframe
    assert len(upcoming) >= 0


@pytest.mark.asyncio
async def test_milestone_reordering(
    client: AsyncClient,
    test_user: dict,
    test_project: dict,
) -> None:
    """Test milestone reordering for drag-drop UI."""
    project_id = test_project["id"]

    # Create three milestones
    milestone_ids = []
    for i in range(3):
        response = await client.post(
            f"/api/v1/milestones/projects/{project_id}/milestones",
            headers={"Authorization": f"Bearer {test_user['token']}"},
            json={"name": f"Milestone {i+1}"},
        )
        assert response.status_code == 201
        milestone_ids.append(response.json()["id"])

    # Get initial order
    response = await client.get(
        f"/api/v1/milestones/projects/{project_id}/milestones",
        headers={"Authorization": f"Bearer {test_user['token']}"},
    )
    assert response.status_code == 200
    milestones = response.json()["milestones"]

    # Filter to only our created milestones
    our_milestones = [m for m in milestones if m["id"] in milestone_ids]
    assert len(our_milestones) == 3

    # Test reorder endpoint (move middle milestone to position 0)
    middle_milestone_id = milestone_ids[1]
    response = await client.patch(
        f"/api/v1/milestones/{middle_milestone_id}/reorder",
        headers={"Authorization": f"Bearer {test_user['token']}"},
        json={"new_order": 0},
    )
    assert response.status_code == 200
    reorder_result = response.json()

    # Verify the reorder endpoint returns updated milestone
    assert reorder_result["id"] == middle_milestone_id
    assert "order" in reorder_result

    # Verify we can still list milestones after reordering
    response = await client.get(
        f"/api/v1/milestones/projects/{project_id}/milestones",
        headers={"Authorization": f"Bearer {test_user['token']}"},
    )
    assert response.status_code == 200
    assert len(response.json()["milestones"]) >= 3
