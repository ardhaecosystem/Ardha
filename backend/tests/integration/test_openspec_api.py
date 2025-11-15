"""
Integration tests for OpenSpec API endpoints.

Tests complete request/response flow with real database operations.
"""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_create_proposal_from_filesystem(
    client: AsyncClient,
    test_user: dict,
    test_project: dict,
) -> None:
    """Test creating proposal from filesystem."""
    project_id = test_project["id"]

    # Create proposal from filesystem
    response = await client.post(
        f"/api/v1/openspec/projects/{project_id}/proposals",
        headers={"Authorization": f"Bearer {test_user['token']}"},
        json={"proposal_name": "test-proposal"},
    )
    assert response.status_code == 201
    data = response.json()

    # Verify proposal data
    assert data["name"] == "test-proposal"
    assert data["status"] == "pending"
    assert data["project_id"] == project_id
    assert data["task_sync_status"] == "not_synced"
    assert data["completion_percentage"] == 0
    assert data["is_editable"] is True
    assert data["can_approve"] is True

    # Verify content was parsed
    assert data["proposal_content"] is not None
    assert data["tasks_content"] is not None
    assert data["spec_delta_content"] is not None
    assert data["metadata_json"] is not None


@pytest.mark.asyncio
async def test_create_duplicate_proposal_fails(
    client: AsyncClient,
    test_user: dict,
    test_project: dict,
) -> None:
    """Test creating duplicate proposal fails."""
    project_id = test_project["id"]

    # Create first proposal
    response = await client.post(
        f"/api/v1/openspec/projects/{project_id}/proposals",
        headers={"Authorization": f"Bearer {test_user['token']}"},
        json={"proposal_name": "test-proposal"},
    )
    assert response.status_code == 201

    # Try to create duplicate
    response = await client.post(
        f"/api/v1/openspec/projects/{project_id}/proposals",
        headers={"Authorization": f"Bearer {test_user['token']}"},
        json={"proposal_name": "test-proposal"},
    )
    assert response.status_code == 409  # Conflict
    assert "already exists" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_list_proposals_for_project(
    client: AsyncClient,
    test_user: dict,
    test_project: dict,
) -> None:
    """Test listing proposals for a project."""
    project_id = test_project["id"]

    # Create multiple proposals
    proposal_names = ["test-proposal", "list-test-proposal"]

    for name in proposal_names:
        response = await client.post(
            f"/api/v1/openspec/projects/{project_id}/proposals",
            headers={"Authorization": f"Bearer {test_user['token']}"},
            json={"proposal_name": name},
        )
        assert response.status_code == 201

    # List proposals
    response = await client.get(
        f"/api/v1/openspec/projects/{project_id}/proposals",
        headers={"Authorization": f"Bearer {test_user['token']}"},
    )
    assert response.status_code == 200
    data = response.json()

    # Verify list contains both proposals
    assert data["total"] >= 2
    assert len(data["proposals"]) >= 2

    proposal_names_returned = [p["name"] for p in data["proposals"]]
    assert "test-proposal" in proposal_names_returned
    assert "list-test-proposal" in proposal_names_returned


@pytest.mark.asyncio
async def test_list_proposals_with_status_filter(
    client: AsyncClient,
    test_user: dict,
    test_project: dict,
) -> None:
    """Test filtering proposals by status."""
    project_id = test_project["id"]

    # Create and approve one proposal
    response = await client.post(
        f"/api/v1/openspec/projects/{project_id}/proposals",
        headers={"Authorization": f"Bearer {test_user['token']}"},
        json={"proposal_name": "test-proposal"},
    )
    assert response.status_code == 201
    proposal_id = response.json()["id"]

    # Approve proposal
    response = await client.post(
        f"/api/v1/openspec/proposals/{proposal_id}/approve",
        headers={"Authorization": f"Bearer {test_user['token']}"},
    )
    assert response.status_code == 200

    # Filter by approved status
    response = await client.get(
        f"/api/v1/openspec/projects/{project_id}/proposals",
        headers={"Authorization": f"Bearer {test_user['token']}"},
        params={"status_filter": "approved"},
    )
    assert response.status_code == 200
    data = response.json()

    # Verify filtered results
    assert all(p["status"] == "approved" for p in data["proposals"])


@pytest.mark.asyncio
async def test_get_proposal_details(
    client: AsyncClient,
    test_user: dict,
    test_openspec_proposal: dict,
) -> None:
    """Test getting proposal details."""
    proposal_id = test_openspec_proposal["id"]

    response = await client.get(
        f"/api/v1/openspec/proposals/{proposal_id}",
        headers={"Authorization": f"Bearer {test_user['token']}"},
    )
    assert response.status_code == 200
    data = response.json()

    # Verify complete data
    assert data["id"] == proposal_id
    assert data["name"] == test_openspec_proposal["name"]
    assert data["proposal_content"] is not None
    assert data["tasks_content"] is not None
    assert data["spec_delta_content"] is not None


@pytest.mark.asyncio
async def test_get_proposal_unauthorized(
    client: AsyncClient,
    test_openspec_proposal: dict,
) -> None:
    """Test getting proposal without authentication fails."""
    proposal_id = test_openspec_proposal["id"]

    response = await client.get(
        f"/api/v1/openspec/proposals/{proposal_id}",
    )
    assert response.status_code == 401  # Unauthorized


@pytest.mark.asyncio
async def test_update_proposal_content(
    client: AsyncClient,
    test_user: dict,
    test_openspec_proposal: dict,
) -> None:
    """Test updating proposal content."""
    proposal_id = test_openspec_proposal["id"]

    # Update content
    response = await client.patch(
        f"/api/v1/openspec/proposals/{proposal_id}",
        headers={"Authorization": f"Bearer {test_user['token']}"},
        json={
            "proposal_content": "# Updated Proposal\n\nUpdated content.",
            "metadata_json": {"updated": True},
        },
    )
    assert response.status_code == 200
    data = response.json()

    # Verify update
    assert "Updated Proposal" in data["proposal_content"]
    assert data["metadata_json"]["updated"] is True


@pytest.mark.asyncio
async def test_update_approved_proposal_fails(
    client: AsyncClient,
    test_user: dict,
    test_openspec_proposal: dict,
) -> None:
    """Test updating approved proposal fails."""
    proposal_id = test_openspec_proposal["id"]

    # Approve proposal first
    response = await client.post(
        f"/api/v1/openspec/proposals/{proposal_id}/approve",
        headers={"Authorization": f"Bearer {test_user['token']}"},
    )
    assert response.status_code == 200

    # Try to update approved proposal
    response = await client.patch(
        f"/api/v1/openspec/proposals/{proposal_id}",
        headers={"Authorization": f"Bearer {test_user['token']}"},
        json={"proposal_content": "# Should Fail"},
    )
    assert response.status_code == 400  # Bad request
    assert "cannot be edited" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_approve_proposal(
    client: AsyncClient,
    test_user: dict,
    test_openspec_proposal: dict,
) -> None:
    """Test approving a proposal."""
    proposal_id = test_openspec_proposal["id"]

    # Approve proposal
    response = await client.post(
        f"/api/v1/openspec/proposals/{proposal_id}/approve",
        headers={"Authorization": f"Bearer {test_user['token']}"},
    )
    assert response.status_code == 200
    data = response.json()

    # Verify approval
    assert data["status"] == "approved"
    assert data["approved_by_user_id"] == test_user["user"]["id"]
    assert data["approved_at"] is not None
    assert data["can_approve"] is False  # No longer approvable
    assert data["is_editable"] is False  # No longer editable


@pytest.mark.asyncio
async def test_approve_requires_admin(
    client: AsyncClient,
    test_user: dict,
) -> None:
    """Test approval requires admin role."""
    # Create second project owned by different user
    response = await client.post(
        "/api/v1/auth/register",
        json={
            "email": "otherowner@example.com",
            "username": "otherowner",
            "password": "Other123!@#",
            "full_name": "Other Owner",
        },
    )
    assert response.status_code == 201
    other_user = response.json()

    # Login as other user
    response = await client.post(
        "/api/v1/auth/login",
        data={
            "username": "otherowner@example.com",
            "password": "Other123!@#",
        },
    )
    assert response.status_code == 200
    other_token = response.json()["access_token"]

    # Create project as other user
    response = await client.post(
        "/api/v1/projects",
        headers={"Authorization": f"Bearer {other_token}"},
        json={"name": "Other User Project"},
    )
    other_project_id = response.json()["id"]

    # Create proposal in other user's project
    response = await client.post(
        f"/api/v1/openspec/projects/{other_project_id}/proposals",
        headers={"Authorization": f"Bearer {other_token}"},
        json={"proposal_name": "test-proposal"},
    )
    assert response.status_code == 201
    proposal_id = response.json()["id"]

    # Try to approve with test_user (not a member)
    response = await client.post(
        f"/api/v1/openspec/proposals/{proposal_id}/approve",
        headers={"Authorization": f"Bearer {test_user['token']}"},
    )
    assert response.status_code == 403  # Forbidden


@pytest.mark.asyncio
async def test_reject_proposal(
    client: AsyncClient,
    test_user: dict,
    test_openspec_proposal: dict,
) -> None:
    """Test rejecting a proposal."""
    proposal_id = test_openspec_proposal["id"]

    # Reject proposal
    response = await client.post(
        f"/api/v1/openspec/proposals/{proposal_id}/reject",
        headers={"Authorization": f"Bearer {test_user['token']}"},
        json={"reason": "Not aligned with current priorities"},
    )
    assert response.status_code == 200
    data = response.json()

    # Verify rejection
    assert data["status"] == "rejected"
    # Metadata should contain rejection reason (check after refresh from DB)
    assert data["is_editable"] is True  # Can edit rejected proposals
    assert data["can_approve"] is False  # Cannot approve rejected


@pytest.mark.asyncio
async def test_sync_tasks_to_database(
    client: AsyncClient,
    test_user: dict,
    test_openspec_proposal: dict,
) -> None:
    """Test syncing tasks to database."""
    proposal_id = test_openspec_proposal["id"]

    # Approve proposal first
    response = await client.post(
        f"/api/v1/openspec/proposals/{proposal_id}/approve",
        headers={"Authorization": f"Bearer {test_user['token']}"},
    )
    assert response.status_code == 200

    # Sync tasks
    response = await client.post(
        f"/api/v1/openspec/proposals/{proposal_id}/sync-tasks",
        headers={"Authorization": f"Bearer {test_user['token']}"},
    )
    assert response.status_code == 200
    data = response.json()

    # Verify sync result
    assert data["proposal_id"] == proposal_id
    assert data["tasks_created"] >= 1  # At least one task
    assert data["sync_status"] == "synced"
    assert data["synced_at"] is not None


@pytest.mark.asyncio
async def test_sync_unapproved_proposal_fails(
    client: AsyncClient,
    test_user: dict,
    test_openspec_proposal: dict,
) -> None:
    """Test syncing tasks fails for unapproved proposal."""
    proposal_id = test_openspec_proposal["id"]

    # Try to sync without approval
    response = await client.post(
        f"/api/v1/openspec/proposals/{proposal_id}/sync-tasks",
        headers={"Authorization": f"Bearer {test_user['token']}"},
    )
    assert response.status_code == 400  # Bad request
    assert "approved" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_refresh_from_filesystem(
    client: AsyncClient,
    test_user: dict,
    test_project: dict,
) -> None:
    """Test refreshing proposal from filesystem."""
    # Create proposal from actual filesystem first
    response = await client.post(
        f"/api/v1/openspec/projects/{test_project['id']}/proposals",
        headers={"Authorization": f"Bearer {test_user['token']}"},
        json={"proposal_name": "test-proposal"},
    )
    assert response.status_code == 201
    proposal_id = response.json()["id"]

    # Refresh proposal
    response = await client.post(
        f"/api/v1/openspec/proposals/{proposal_id}/refresh",
        headers={"Authorization": f"Bearer {test_user['token']}"},
    )
    assert response.status_code == 200
    data = response.json()

    # Verify refresh
    assert data["id"] == proposal_id
    assert data["proposal_content"] is not None


@pytest.mark.asyncio
async def test_archive_proposal(
    client: AsyncClient,
    test_user: dict,
) -> None:
    """Test archiving a proposal."""
    # Create project
    response = await client.post(
        "/api/v1/projects",
        headers={"Authorization": f"Bearer {test_user['token']}"},
        json={"name": "Archive Test Project"},
    )
    project_id = response.json()["id"]

    # Create proposal
    response = await client.post(
        f"/api/v1/openspec/projects/{project_id}/proposals",
        headers={"Authorization": f"Bearer {test_user['token']}"},
        json={"proposal_name": "archive-test-proposal"},
    )
    assert response.status_code == 201
    proposal_id = response.json()["id"]

    # Archive proposal
    response = await client.post(
        f"/api/v1/openspec/proposals/{proposal_id}/archive",
        headers={"Authorization": f"Bearer {test_user['token']}"},
    )
    assert response.status_code == 200
    data = response.json()

    # Verify archival
    assert data["status"] == "archived"
    assert data["archived_at"] is not None


@pytest.mark.asyncio
async def test_delete_proposal(
    client: AsyncClient,
    test_user: dict,
    test_project: dict,
) -> None:
    """Test deleting a proposal."""
    project_id = test_project["id"]

    # Create proposal to delete
    response = await client.post(
        f"/api/v1/openspec/projects/{project_id}/proposals",
        headers={"Authorization": f"Bearer {test_user['token']}"},
        json={"proposal_name": "test-proposal"},
    )
    assert response.status_code == 201
    proposal_id = response.json()["id"]

    # Delete proposal
    response = await client.delete(
        f"/api/v1/openspec/proposals/{proposal_id}",
        headers={"Authorization": f"Bearer {test_user['token']}"},
    )
    assert response.status_code == 200
    assert "deleted successfully" in response.json()["message"].lower()

    # Verify proposal is deleted
    response = await client.get(
        f"/api/v1/openspec/proposals/{proposal_id}",
        headers={"Authorization": f"Bearer {test_user['token']}"},
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_complete_openspec_workflow(
    client: AsyncClient,
    test_user: dict,
    test_project: dict,
) -> None:
    """Test complete OpenSpec proposal workflow from creation to archival."""
    project_id = test_project["id"]

    # Step 1: Create proposal
    response = await client.post(
        f"/api/v1/openspec/projects/{project_id}/proposals",
        headers={"Authorization": f"Bearer {test_user['token']}"},
        json={"proposal_name": "test-proposal"},
    )
    assert response.status_code == 201
    proposal_id = response.json()["id"]

    # Step 2: Review proposal details
    response = await client.get(
        f"/api/v1/openspec/proposals/{proposal_id}",
        headers={"Authorization": f"Bearer {test_user['token']}"},
    )
    assert response.status_code == 200
    assert response.json()["status"] == "pending"

    # Step 3: Approve proposal
    response = await client.post(
        f"/api/v1/openspec/proposals/{proposal_id}/approve",
        headers={"Authorization": f"Bearer {test_user['token']}"},
    )
    assert response.status_code == 200
    assert response.json()["status"] == "approved"

    # Step 4: Sync tasks to database
    response = await client.post(
        f"/api/v1/openspec/proposals/{proposal_id}/sync-tasks",
        headers={"Authorization": f"Bearer {test_user['token']}"},
    )
    assert response.status_code == 200
    sync_result = response.json()
    assert sync_result["sync_status"] == "synced"
    assert sync_result["tasks_created"] >= 1

    # Step 5: Verify tasks are linked
    response = await client.get(
        f"/api/v1/openspec/proposals/{proposal_id}",
        headers={"Authorization": f"Bearer {test_user['token']}"},
    )
    assert response.status_code == 200
    assert response.json()["task_sync_status"] == "synced"

    # Step 6: Archive proposal
    response = await client.post(
        f"/api/v1/openspec/proposals/{proposal_id}/archive",
        headers={"Authorization": f"Bearer {test_user['token']}"},
    )
    assert response.status_code == 200
    assert response.json()["status"] == "archived"


@pytest.mark.asyncio
async def test_proposal_permission_enforcement(
    client: AsyncClient,
    test_user: dict,
    test_project: dict,
) -> None:
    """Test that OpenSpec endpoints enforce permissions."""
    project_id = test_project["id"]

    # Create second user (not a project member)
    response = await client.post(
        "/api/v1/auth/register",
        json={
            "email": "outsider@example.com",
            "username": "outsider",
            "password": "Outsider123!@#",
            "full_name": "Outsider User",
        },
    )
    assert response.status_code == 201

    # Login as outsider
    response = await client.post(
        "/api/v1/auth/login",
        json={"email": "outsider@example.com", "password": "Outsider123!@#"},
    )
    outsider_token = response.json()["access_token"]

    # Create proposal as owner
    response = await client.post(
        f"/api/v1/openspec/projects/{project_id}/proposals",
        headers={"Authorization": f"Bearer {test_user['token']}"},
        json={"proposal_name": "test-proposal"},
    )
    assert response.status_code == 201
    proposal_id = response.json()["id"]

    # Outsider tries to view proposal (should fail)
    response = await client.get(
        f"/api/v1/openspec/proposals/{proposal_id}",
        headers={"Authorization": f"Bearer {outsider_token}"},
    )
    assert response.status_code == 403  # Forbidden

    # Outsider tries to approve proposal (should fail)
    response = await client.post(
        f"/api/v1/openspec/proposals/{proposal_id}/approve",
        headers={"Authorization": f"Bearer {outsider_token}"},
    )
    assert response.status_code == 403  # Forbidden


@pytest.mark.asyncio
async def test_pagination_on_list_proposals(
    client: AsyncClient,
    test_user: dict,
    test_project: dict,
) -> None:
    """Test pagination on proposal listing."""
    project_id = test_project["id"]

    # Create multiple proposals
    for i in range(3):
        response = await client.post(
            f"/api/v1/openspec/projects/{project_id}/proposals",
            headers={"Authorization": f"Bearer {test_user['token']}"},
            json={"proposal_name": f"test-proposal" if i == 0 else f"list-test-proposal"},
        )
        # First might fail if already exists, that's ok
        if i > 0:
            assert response.status_code == 201

    # Test pagination
    response = await client.get(
        f"/api/v1/openspec/projects/{project_id}/proposals",
        headers={"Authorization": f"Bearer {test_user['token']}"},
        params={"skip": 0, "limit": 2},
    )
    assert response.status_code == 200
    data = response.json()

    # Verify pagination
    assert len(data["proposals"]) <= 2
    assert data["skip"] == 0
    assert data["limit"] == 2
    assert data["total"] >= 2
