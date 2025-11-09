"""
Integration tests for project management flow.

Tests the complete project lifecycle including creation, listing,
updates, member management, and permissions.
"""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_create_and_list_projects(client: AsyncClient, test_user: dict) -> None:
    """Test creating and listing projects."""
    # Create first project
    response = await client.post(
        "/api/v1/projects",
        headers={"Authorization": f"Bearer {test_user['token']}"},
        json={
            "name": "Test Project Alpha",
            "description": "First test project",
            "visibility": "private",
            "tech_stack": ["Python", "FastAPI"],
        },
    )
    assert response.status_code == 201
    project1 = response.json()
    assert project1["name"] == "Test Project Alpha"
    assert project1["slug"] == "test-project-alpha"
    assert project1["visibility"] == "private"
    assert "Python" in project1["tech_stack"]
    
    # Create second project
    response = await client.post(
        "/api/v1/projects",
        headers={"Authorization": f"Bearer {test_user['token']}"},
        json={
            "name": "Test Project Beta",
            "description": "Second test project",
            "visibility": "public",
        },
    )
    assert response.status_code == 201
    project2 = response.json()
    assert project2["name"] == "Test Project Beta"
    
    # List all projects
    response = await client.get(
        "/api/v1/projects",
        headers={"Authorization": f"Bearer {test_user['token']}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 2
    assert len(data["projects"]) == 2
    
    # Verify both projects in list
    project_names = [p["name"] for p in data["projects"]]
    assert "Test Project Alpha" in project_names
    assert "Test Project Beta" in project_names


@pytest.mark.asyncio
async def test_project_permissions(client: AsyncClient, test_user: dict) -> None:
    """Test project role-based permissions."""
    # Create project (user becomes owner)
    response = await client.post(
        "/api/v1/projects",
        headers={"Authorization": f"Bearer {test_user['token']}"},
        json={
            "name": "Permission Test Project",
            "description": "Testing permissions",
        },
    )
    assert response.status_code == 201
    project = response.json()
    project_id = project["id"]
    
    # Update project (should succeed as owner)
    response = await client.patch(
        f"/api/v1/projects/{project_id}",
        headers={"Authorization": f"Bearer {test_user['token']}"},
        json={"description": "Updated description by owner"},
    )
    assert response.status_code == 200
    assert response.json()["description"] == "Updated description by owner"
    
    # Archive project (should succeed as owner)
    response = await client.post(
        f"/api/v1/projects/{project_id}/archive",
        headers={"Authorization": f"Bearer {test_user['token']}"},
    )
    assert response.status_code == 200
    assert "archived successfully" in response.json()["message"].lower()
    
    # Verify archived project not in default list
    response = await client.get(
        "/api/v1/projects",
        headers={"Authorization": f"Bearer {test_user['token']}"},
    )
    assert response.status_code == 200
    # Should not include archived project by default
    project_ids = [p["id"] for p in response.json()["projects"]]
    assert project_id not in project_ids


@pytest.mark.asyncio
async def test_project_member_management(client: AsyncClient, test_user: dict) -> None:
    """Test adding and managing project members."""
    # Create second user
    response = await client.post(
        "/api/v1/auth/register",
        json={
            "email": "member@example.com",
            "username": "memberuser",
            "password": "Member123!@#",
            "full_name": "Member User",
        },
    )
    assert response.status_code == 201
    member_user = response.json()
    member_id = member_user["id"]
    
    # Create project
    response = await client.post(
        "/api/v1/projects",
        headers={"Authorization": f"Bearer {test_user['token']}"},
        json={"name": "Team Project"},
    )
    assert response.status_code == 201
    project_id = response.json()["id"]
    
    # Add member to project
    response = await client.post(
        f"/api/v1/projects/{project_id}/members",
        headers={"Authorization": f"Bearer {test_user['token']}"},
        json={
            "user_id": member_id,
            "role": "member",
        },
    )
    assert response.status_code == 201
    
    # List project members
    response = await client.get(
        f"/api/v1/projects/{project_id}/members",
        headers={"Authorization": f"Bearer {test_user['token']}"},
    )
    assert response.status_code == 200
    members = response.json()
    assert len(members) == 2  # Owner + added member
    
    # Verify member roles
    member_roles = {m["user_id"]: m["role"] for m in members}
    assert member_roles[test_user["user"]["id"]] == "owner"
    assert member_roles[member_id] == "member"
    
    # Update member role
    response = await client.patch(
        f"/api/v1/projects/{project_id}/members/{member_id}",
        headers={"Authorization": f"Bearer {test_user['token']}"},
        json={"role": "admin"},
    )
    assert response.status_code == 200
    assert response.json()["role"] == "admin"
    
    # Remove member
    response = await client.delete(
        f"/api/v1/projects/{project_id}/members/{member_id}",
        headers={"Authorization": f"Bearer {test_user['token']}"},
    )
    assert response.status_code == 200
    
    # Verify member removed
    response = await client.get(
        f"/api/v1/projects/{project_id}/members",
        headers={"Authorization": f"Bearer {test_user['token']}"},
    )
    assert response.status_code == 200
    assert len(response.json()) == 1  # Only owner remains