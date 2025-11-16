"""
Integration tests for File API.

Tests the complete file management flow including creation,
listing, content management, and permissions.
"""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_create_file(client: AsyncClient, test_user: dict) -> None:
    """Test creating a new file."""
    # Create project first
    response = await client.post(
        "/api/v1/projects",
        headers={"Authorization": f"Bearer {test_user['token']}"},
        json={
            "name": "File Test Project",
            "description": "Project for file testing",
        },
    )
    assert response.status_code == 201
    project = response.json()
    project_id = project["id"]

    # Create file
    response = await client.post(
        "/api/v1/files",
        headers={"Authorization": f"Bearer {test_user['token']}"},
        json={
            "project_id": project_id,
            "path": "src/main.py",
            "content": "print('Hello, World!')\n",
            "commit": False,
        },
    )
    assert response.status_code == 201
    file_data = response.json()
    assert file_data["path"] == "src/main.py"
    assert file_data["file_type"] == "code"
    assert file_data["size_bytes"] > 0
    assert file_data["project_id"] == project_id


@pytest.mark.asyncio
async def test_get_file_details(client: AsyncClient, test_user: dict) -> None:
    """Test getting file details."""
    # Create project and file
    response = await client.post(
        "/api/v1/projects",
        headers={"Authorization": f"Bearer {test_user['token']}"},
        json={"name": "File Details Test"},
    )
    assert response.status_code == 201
    project_id = response.json()["id"]

    response = await client.post(
        "/api/v1/files",
        headers={"Authorization": f"Bearer {test_user['token']}"},
        json={
            "project_id": project_id,
            "path": "README.md",
            "content": "# Test Project\n\nThis is a test.",
        },
    )
    assert response.status_code == 201
    file_id = response.json()["id"]

    # Get file details
    response = await client.get(
        f"/api/v1/files/{file_id}",
        headers={"Authorization": f"Bearer {test_user['token']}"},
    )
    assert response.status_code == 200
    file_data = response.json()
    assert file_data["path"] == "README.md"
    assert file_data["file_type"] == "doc"
    assert file_data["project_id"] == project_id


@pytest.mark.asyncio
async def test_get_file_content(client: AsyncClient, test_user: dict) -> None:
    """Test getting file with content."""
    # Create project and file
    response = await client.post(
        "/api/v1/projects",
        headers={"Authorization": f"Bearer {test_user['token']}"},
        json={"name": "File Content Test"},
    )
    assert response.status_code == 201
    project_id = response.json()["id"]

    content = "def hello():\n    return 'Hello, World!'\n"
    response = await client.post(
        "/api/v1/files",
        headers={"Authorization": f"Bearer {test_user['token']}"},
        json={
            "project_id": project_id,
            "path": "src/hello.py",
            "content": content,
        },
    )
    assert response.status_code == 201
    file_id = response.json()["id"]

    # Get file with content
    response = await client.get(
        f"/api/v1/files/{file_id}/content",
        headers={"Authorization": f"Bearer {test_user['token']}"},
    )
    assert response.status_code == 200
    file_data = response.json()
    assert file_data["content"] == content
    assert file_data["path"] == "src/hello.py"


@pytest.mark.asyncio
async def test_update_file_content(client: AsyncClient, test_user: dict) -> None:
    """Test updating file content."""
    # Create project and file
    response = await client.post(
        "/api/v1/projects",
        headers={"Authorization": f"Bearer {test_user['token']}"},
        json={"name": "File Update Test"},
    )
    assert response.status_code == 201
    project_id = response.json()["id"]

    response = await client.post(
        "/api/v1/files",
        headers={"Authorization": f"Bearer {test_user['token']}"},
        json={
            "project_id": project_id,
            "path": "config.json",
            "content": '{"name": "test", "version": "1.0"}',
        },
    )
    assert response.status_code == 201
    file_id = response.json()["id"]

    # Update file content
    new_content = '{"name": "test", "version": "2.0", "debug": true}'
    response = await client.patch(
        f"/api/v1/files/{file_id}",
        headers={"Authorization": f"Bearer {test_user['token']}"},
        json={
            "content": new_content,
            "commit": False,
        },
    )
    assert response.status_code == 200
    file_data = response.json()
    assert file_data["size_bytes"] > 0

    # Verify content updated
    response = await client.get(
        f"/api/v1/files/{file_id}/content",
        headers={"Authorization": f"Bearer {test_user['token']}"},
    )
    assert response.status_code == 200
    assert response.json()["content"] == new_content


@pytest.mark.asyncio
async def test_rename_file(client: AsyncClient, test_user: dict) -> None:
    """Test renaming a file."""
    # Create project and file
    response = await client.post(
        "/api/v1/projects",
        headers={"Authorization": f"Bearer {test_user['token']}"},
        json={"name": "File Rename Test"},
    )
    assert response.status_code == 201
    project_id = response.json()["id"]

    response = await client.post(
        "/api/v1/files",
        headers={"Authorization": f"Bearer {test_user['token']}"},
        json={
            "project_id": project_id,
            "path": "old_name.txt",
            "content": "This file will be renamed",
        },
    )
    assert response.status_code == 201
    file_id = response.json()["id"]

    # Rename file
    response = await client.patch(
        f"/api/v1/files/{file_id}/rename",
        headers={"Authorization": f"Bearer {test_user['token']}"},
        json={
            "new_path": "new_name.txt",
            "commit": False,
        },
    )
    assert response.status_code == 200
    file_data = response.json()
    assert file_data["path"] == "new_name.txt"


@pytest.mark.asyncio
async def test_delete_file(client: AsyncClient, test_user: dict) -> None:
    """Test deleting a file."""
    # Create project and file
    response = await client.post(
        "/api/v1/projects",
        headers={"Authorization": f"Bearer {test_user['token']}"},
        json={"name": "File Delete Test"},
    )
    assert response.status_code == 201
    project_id = response.json()["id"]

    response = await client.post(
        "/api/v1/files",
        headers={"Authorization": f"Bearer {test_user['token']}"},
        json={
            "project_id": project_id,
            "path": "temp.txt",
            "content": "Temporary file",
        },
    )
    assert response.status_code == 201
    file_id = response.json()["id"]

    # Delete file
    response = await client.delete(
        f"/api/v1/files/{file_id}",
        headers={"Authorization": f"Bearer {test_user['token']}"},
        params={"commit": False},
    )
    assert response.status_code == 200
    result = response.json()
    assert result["success"] is True


@pytest.mark.asyncio
async def test_list_project_files(client: AsyncClient, test_user: dict) -> None:
    """Test listing files in a project."""
    # Create project
    response = await client.post(
        "/api/v1/projects",
        headers={"Authorization": f"Bearer {test_user['token']}"},
        json={"name": "File List Test"},
    )
    assert response.status_code == 201
    project_id = response.json()["id"]

    # Create multiple files
    files_to_create = [
        ("src/main.py", "print('Hello')", "code"),
        ("README.md", "# Project", "doc"),
        ("config.yaml", "debug: true", "config"),
    ]

    for path, content, expected_type in files_to_create:
        response = await client.post(
            "/api/v1/files",
            headers={"Authorization": f"Bearer {test_user['token']}"},
            json={
                "project_id": project_id,
                "path": path,
                "content": content,
            },
        )
        assert response.status_code == 201

    # List all files
    response = await client.get(
        f"/api/v1/files/projects/{project_id}/files",
        headers={"Authorization": f"Bearer {test_user['token']}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 3
    assert len(data["files"]) == 3

    # Filter by file type
    response = await client.get(
        f"/api/v1/files/projects/{project_id}/files",
        headers={"Authorization": f"Bearer {test_user['token']}"},
        params={"file_type": "code"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 1
    assert data["files"][0]["file_type"] == "code"


@pytest.mark.asyncio
async def test_file_permissions(client: AsyncClient, test_user: dict) -> None:
    """Test file access permissions."""
    # Create second user and get token
    response = await client.post(
        "/api/v1/auth/register",
        json={
            "email": "fileuser@example.com",
            "username": "fileuser",
            "password": "FileUser123!@#",
            "full_name": "File User",
        },
    )
    assert response.status_code == 201
    other_user_data = response.json()

    # Login other user to get token
    response = await client.post(
        "/api/v1/auth/login",
        data={
            "username": "fileuser@example.com",
            "password": "FileUser123!@#",
        },
    )
    assert response.status_code == 200
    other_user_token = response.json()["access_token"]

    # Create project with first user
    response = await client.post(
        "/api/v1/projects",
        headers={"Authorization": f"Bearer {test_user['token']}"},
        json={"name": "File Permission Test"},
    )
    assert response.status_code == 201
    project_id = response.json()["id"]

    # Create file with first user
    response = await client.post(
        "/api/v1/files",
        headers={"Authorization": f"Bearer {test_user['token']}"},
        json={
            "project_id": project_id,
            "path": "secret.txt",
            "content": "Secret content",
        },
    )
    assert response.status_code == 201
    file_id = response.json()["id"]

    # Other user should not be able to access file (not a project member)
    response = await client.get(
        f"/api/v1/files/{file_id}",
        headers={"Authorization": f"Bearer {other_user_token}"},
    )
    assert response.status_code == 403

    # Add other user as project member
    response = await client.post(
        f"/api/v1/projects/{project_id}/members",
        headers={"Authorization": f"Bearer {test_user['token']}"},
        json={
            "user_id": other_user_data["id"],
            "role": "viewer",
        },
    )
    assert response.status_code == 201

    # Now other user should be able to access file
    response = await client.get(
        f"/api/v1/files/{file_id}",
        headers={"Authorization": f"Bearer {other_user_token}"},
    )
    assert response.status_code == 200

    # But viewer should not be able to update file
    response = await client.patch(
        f"/api/v1/files/{file_id}",
        headers={"Authorization": f"Bearer {other_user_token}"},
        json={"content": "Hacked content"},
    )
    assert response.status_code == 403