"""
Integration tests for task management flow.

Tests the complete task lifecycle including creation, status updates,
dependencies, tags, and various view modes.
"""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_create_and_manage_tasks(
    client: AsyncClient,
    test_user: dict,
    test_project: dict,
) -> None:
    """Test complete task lifecycle."""
    project_id = test_project["id"]
    
    # Create task
    response = await client.post(
        f"/api/v1/tasks/projects/{project_id}/tasks",
        headers={"Authorization": f"Bearer {test_user['token']}"},
        json={
            "title": "Implement feature X",
            "description": "Add new authentication feature",
            "priority": "high",
            "complexity": "medium",
        },
    )
    assert response.status_code == 201
    task = response.json()
    assert "identifier" in task
    # Identifier is based on project slug (test-project -> TES-001)
    assert "-" in task["identifier"]
    assert task["title"] == "Implement feature X"
    assert task["status"] == "todo"
    assert task["priority"] == "high"
    task_id = task["id"]
    
    # Update task status to in_progress
    response = await client.patch(
        f"/api/v1/tasks/{task_id}/status",
        headers={"Authorization": f"Bearer {test_user['token']}"},
        json={"status": "in_progress"},
    )
    assert response.status_code == 200
    updated_task = response.json()
    assert updated_task["status"] == "in_progress"
    assert updated_task["started_at"] is not None
    
    # Assign task to user
    response = await client.post(
        f"/api/v1/tasks/{task_id}/assign",
        headers={"Authorization": f"Bearer {test_user['token']}"},
        json={"assignee_id": test_user["user"]["id"]},
    )
    assert response.status_code == 200
    assert response.json()["assignee_id"] is not None
    
    # Get task by identifier
    response = await client.get(
        f"/api/v1/tasks/identifier/{project_id}/{task['identifier']}",
        headers={"Authorization": f"Bearer {test_user['token']}"},
    )
    assert response.status_code == 200
    assert response.json()["id"] == task_id
    
    # List tasks (board view)
    response = await client.get(
        f"/api/v1/tasks/projects/{project_id}/tasks/board",
        headers={"Authorization": f"Bearer {test_user['token']}"},
    )
    assert response.status_code == 200
    board_data = response.json()
    assert "counts" in board_data
    assert board_data["counts"]["in_progress"] == 1
    
    # Update status to in_review, then done (valid transitions)
    response = await client.patch(
        f"/api/v1/tasks/{task_id}/status",
        headers={"Authorization": f"Bearer {test_user['token']}"},
        json={"status": "in_review"},
    )
    assert response.status_code == 200
    
    response = await client.patch(
        f"/api/v1/tasks/{task_id}/status",
        headers={"Authorization": f"Bearer {test_user['token']}"},
        json={"status": "done"},
    )
    assert response.status_code == 200
    assert response.json()["completed_at"] is not None


@pytest.mark.asyncio
async def test_task_dependencies(
    client: AsyncClient,
    test_user: dict,
    test_project: dict,
) -> None:
    """Test task dependency management."""
    project_id = test_project["id"]
    
    # Create task A (blocking task)
    response = await client.post(
        f"/api/v1/tasks/projects/{project_id}/tasks",
        headers={"Authorization": f"Bearer {test_user['token']}"},
        json={"title": "Task A - Setup Database"},
    )
    assert response.status_code == 201
    task_a = response.json()
    task_a_id = task_a["id"]
    
    # Create task B (dependent task)
    response = await client.post(
        f"/api/v1/tasks/projects/{project_id}/tasks",
        headers={"Authorization": f"Bearer {test_user['token']}"},
        json={"title": "Task B - Create API"},
    )
    assert response.status_code == 201
    task_b = response.json()
    task_b_id = task_b["id"]
    
    # Create task C (another dependent)
    response = await client.post(
        f"/api/v1/tasks/projects/{project_id}/tasks",
        headers={"Authorization": f"Bearer {test_user['token']}"},
        json={"title": "Task C - Write Tests"},
    )
    assert response.status_code == 201
    task_c = response.json()
    task_c_id = task_c["id"]
    
    # Add dependency: B depends on A
    response = await client.post(
        f"/api/v1/tasks/{task_b_id}/dependencies",
        headers={"Authorization": f"Bearer {test_user['token']}"},
        json={"depends_on_task_id": task_a_id},
    )
    assert response.status_code == 201
    
    # Add dependency: C depends on B
    response = await client.post(
        f"/api/v1/tasks/{task_c_id}/dependencies",
        headers={"Authorization": f"Bearer {test_user['token']}"},
        json={"depends_on_task_id": task_b_id},
    )
    assert response.status_code == 201
    
    # List dependencies for task B
    response = await client.get(
        f"/api/v1/tasks/{task_b_id}/dependencies",
        headers={"Authorization": f"Bearer {test_user['token']}"},
    )
    assert response.status_code == 200
    dependencies = response.json()
    assert len(dependencies) == 1
    assert dependencies[0]["depends_on_task_id"] == task_a_id
    
    # Attempt to create circular dependency (C → A → B → C)
    # This should fail
    response = await client.post(
        f"/api/v1/tasks/{task_a_id}/dependencies",
        headers={"Authorization": f"Bearer {test_user['token']}"},
        json={"depends_on_task_id": task_c_id},
    )
    assert response.status_code == 400
    assert "circular" in response.json()["detail"].lower()
    
    # Remove dependency
    response = await client.delete(
        f"/api/v1/tasks/{task_b_id}/dependencies/{task_a_id}",
        headers={"Authorization": f"Bearer {test_user['token']}"},
    )
    assert response.status_code == 200
    
    # Verify dependency removed
    response = await client.get(
        f"/api/v1/tasks/{task_b_id}/dependencies",
        headers={"Authorization": f"Bearer {test_user['token']}"},
    )
    assert response.status_code == 200
    assert len(response.json()) == 0


@pytest.mark.asyncio
async def test_task_views(
    client: AsyncClient,
    test_user: dict,
    test_project: dict,
) -> None:
    """Test different task view modes (board, calendar, timeline)."""
    project_id = test_project["id"]
    
    # Create tasks with different statuses
    statuses = ["todo", "in_progress", "in_review", "done"]
    for i, status in enumerate(statuses):
        response = await client.post(
            f"/api/v1/tasks/projects/{project_id}/tasks",
            headers={"Authorization": f"Bearer {test_user['token']}"},
            json={
                "title": f"Task {i+1}",
                "status": status,
            },
        )
        assert response.status_code == 201
    
    # Test board view
    response = await client.get(
        f"/api/v1/tasks/projects/{project_id}/tasks/board",
        headers={"Authorization": f"Bearer {test_user['token']}"},
    )
    assert response.status_code == 200
    board = response.json()
    assert board["counts"]["todo"] == 1
    assert board["counts"]["in_progress"] == 1
    assert board["counts"]["in_review"] == 1
    assert board["counts"]["done"] == 1
    
    # Test calendar view
    response = await client.get(
        f"/api/v1/tasks/projects/{project_id}/tasks/calendar",
        headers={"Authorization": f"Bearer {test_user['token']}"},
    )
    assert response.status_code == 200
    
    # Test timeline view
    response = await client.get(
        f"/api/v1/tasks/projects/{project_id}/tasks/timeline",
        headers={"Authorization": f"Bearer {test_user['token']}"},
    )
    assert response.status_code == 200