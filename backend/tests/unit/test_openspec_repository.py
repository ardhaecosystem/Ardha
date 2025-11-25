"""
Unit tests for OpenSpec repository layer.

This module tests all OpenSpecRepository methods with comprehensive coverage
including success cases, error handling, and edge cases.
"""

from datetime import UTC, datetime
from uuid import uuid4

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from ardha.models.openspec import OpenSpecProposal
from ardha.models.task import Task
from ardha.repositories.openspec import OpenSpecRepository

# ============= CRUD Tests =============


@pytest.mark.asyncio
async def test_create_proposal(test_db: AsyncSession, sample_proposal_data):
    """Test successful proposal creation."""
    repo = OpenSpecRepository(test_db)
    proposal = OpenSpecProposal(**sample_proposal_data)

    created = await repo.create(proposal)

    assert created.id is not None
    assert created.name == sample_proposal_data["name"]
    assert created.status == "pending"
    assert created.project_id == sample_proposal_data["project_id"]
    assert created.created_by_user_id == sample_proposal_data["created_by_user_id"]
    assert created.proposal_content == sample_proposal_data["proposal_content"]
    assert created.completion_percentage == 0
    assert created.task_sync_status == "not_synced"


@pytest.mark.asyncio
async def test_create_duplicate_name_fails(test_db: AsyncSession, sample_proposal_data):
    """Test that creating duplicate proposal name in same project fails."""
    repo = OpenSpecRepository(test_db)

    # Create first proposal
    proposal1 = OpenSpecProposal(**sample_proposal_data)
    await repo.create(proposal1)
    await test_db.commit()

    # Try to create duplicate
    proposal2_data = sample_proposal_data.copy()
    proposal2 = OpenSpecProposal(**proposal2_data)

    with pytest.raises(IntegrityError):
        await repo.create(proposal2)


@pytest.mark.asyncio
async def test_get_by_id_success(test_db: AsyncSession, sample_proposal_data):
    """Test retrieving proposal by ID."""
    repo = OpenSpecRepository(test_db)

    # Create proposal
    proposal = OpenSpecProposal(**sample_proposal_data)
    await repo.create(proposal)
    await test_db.commit()

    # Retrieve by ID
    retrieved = await repo.get_by_id(proposal.id)

    assert retrieved is not None
    assert retrieved.id == proposal.id
    assert retrieved.name == proposal.name
    assert retrieved.project_id == proposal.project_id


@pytest.mark.asyncio
async def test_get_by_id_not_found(test_db: AsyncSession):
    """Test retrieving non-existent proposal returns None."""
    repo = OpenSpecRepository(test_db)

    non_existent_id = uuid4()
    retrieved = await repo.get_by_id(non_existent_id)

    assert retrieved is None


@pytest.mark.asyncio
async def test_get_by_name_success(test_db: AsyncSession, sample_proposal_data):
    """Test retrieving proposal by project ID and name."""
    repo = OpenSpecRepository(test_db)

    # Create proposal
    proposal = OpenSpecProposal(**sample_proposal_data)
    await repo.create(proposal)
    await test_db.commit()

    # Retrieve by name
    retrieved = await repo.get_by_name(proposal.project_id, sample_proposal_data["name"])

    assert retrieved is not None
    assert retrieved.id == proposal.id
    assert retrieved.name == sample_proposal_data["name"]


@pytest.mark.asyncio
async def test_get_by_name_case_insensitive(test_db: AsyncSession, sample_proposal_data):
    """Test that get_by_name is case-insensitive."""
    repo = OpenSpecRepository(test_db)

    # Create proposal with lowercase name
    sample_proposal_data["name"] = "user-auth-system"
    proposal = OpenSpecProposal(**sample_proposal_data)
    await repo.create(proposal)
    await test_db.commit()

    # Try to retrieve with different case
    retrieved = await repo.get_by_name(proposal.project_id, "USER-AUTH-SYSTEM")

    assert retrieved is not None
    assert retrieved.id == proposal.id


@pytest.mark.asyncio
async def test_get_by_name_not_found(test_db: AsyncSession):
    """Test retrieving non-existent proposal by name returns None."""
    repo = OpenSpecRepository(test_db)

    project_id = uuid4()
    retrieved = await repo.get_by_name(project_id, "non-existent")

    assert retrieved is None


@pytest.mark.asyncio
async def test_update_proposal(test_db: AsyncSession, sample_proposal_data):
    """Test updating proposal fields."""
    repo = OpenSpecRepository(test_db)

    # Create proposal
    proposal = OpenSpecProposal(**sample_proposal_data)
    await repo.create(proposal)
    await test_db.commit()

    # Update fields
    update_data = {
        "proposal_content": "# Updated Content\nNew summary",
        "completion_percentage": 50,
    }
    updated = await repo.update(proposal.id, update_data)

    assert updated is not None
    assert updated.proposal_content == update_data["proposal_content"]
    assert updated.completion_percentage == 50
    assert updated.updated_at > proposal.created_at


@pytest.mark.asyncio
async def test_update_nonexistent(test_db: AsyncSession):
    """Test updating non-existent proposal returns None."""
    repo = OpenSpecRepository(test_db)

    non_existent_id = uuid4()
    updated = await repo.update(non_existent_id, {"status": "approved"})

    assert updated is None


@pytest.mark.asyncio
async def test_delete_proposal(test_db: AsyncSession, sample_proposal_data):
    """Test deleting proposal."""
    repo = OpenSpecRepository(test_db)

    # Create proposal
    proposal = OpenSpecProposal(**sample_proposal_data)
    await repo.create(proposal)
    await test_db.commit()

    # Delete proposal
    deleted = await repo.delete(proposal.id)
    assert deleted is True

    # Verify deleted
    retrieved = await repo.get_by_id(proposal.id)
    assert retrieved is None


@pytest.mark.asyncio
async def test_delete_nonexistent(test_db: AsyncSession):
    """Test deleting non-existent proposal returns False."""
    repo = OpenSpecRepository(test_db)

    non_existent_id = uuid4()
    deleted = await repo.delete(non_existent_id)

    assert deleted is False


# ============= List/Filter Tests =============


@pytest.mark.asyncio
async def test_list_by_project(test_db: AsyncSession, sample_proposals_batch):
    """Test listing proposals by project."""
    repo = OpenSpecRepository(test_db)

    # Create multiple proposals
    project_id = sample_proposals_batch[0]["project_id"]
    for data in sample_proposals_batch:
        proposal = OpenSpecProposal(**data)
        await repo.create(proposal)
    await test_db.commit()

    # List all proposals for project
    proposals = await repo.list_by_project(project_id)

    assert len(proposals) == 5
    assert all(p.project_id == project_id for p in proposals)
    # Should be ordered by created_at DESC
    assert proposals[0].created_at >= proposals[-1].created_at


@pytest.mark.asyncio
async def test_list_by_project_with_status_filter(test_db: AsyncSession, sample_proposals_batch):
    """Test listing proposals with status filter."""
    repo = OpenSpecRepository(test_db)

    # Create multiple proposals
    project_id = sample_proposals_batch[0]["project_id"]
    for data in sample_proposals_batch:
        proposal = OpenSpecProposal(**data)
        await repo.create(proposal)
    await test_db.commit()

    # Filter by status
    pending = await repo.list_by_project(project_id, status="pending")
    approved = await repo.list_by_project(project_id, status="approved")
    archived = await repo.list_by_project(project_id, status="archived")

    assert len(pending) == 1
    assert len(approved) == 1
    assert len(archived) == 1
    assert all(p.status == "pending" for p in pending)
    assert all(p.status == "approved" for p in approved)
    assert all(p.status == "archived" for p in archived)


@pytest.mark.asyncio
async def test_list_by_project_pagination(test_db: AsyncSession, sample_proposals_batch):
    """Test pagination in list_by_project."""
    repo = OpenSpecRepository(test_db)

    # Create multiple proposals
    project_id = sample_proposals_batch[0]["project_id"]
    for data in sample_proposals_batch:
        proposal = OpenSpecProposal(**data)
        await repo.create(proposal)
    await test_db.commit()

    # Test pagination
    page1 = await repo.list_by_project(project_id, skip=0, limit=2)
    page2 = await repo.list_by_project(project_id, skip=2, limit=2)

    assert len(page1) == 2
    assert len(page2) == 2
    # Ensure different results
    assert page1[0].id != page2[0].id


@pytest.mark.asyncio
async def test_list_by_project_invalid_pagination(test_db: AsyncSession):
    """Test that invalid pagination parameters raise ValueError."""
    repo = OpenSpecRepository(test_db)
    project_id = uuid4()

    # Test negative skip
    with pytest.raises(ValueError, match="skip must be >= 0"):
        await repo.list_by_project(project_id, skip=-1)

    # Test limit too small
    with pytest.raises(ValueError, match="limit must be between 1 and 100"):
        await repo.list_by_project(project_id, limit=0)

    # Test limit too large
    with pytest.raises(ValueError, match="limit must be between 1 and 100"):
        await repo.list_by_project(project_id, limit=101)


@pytest.mark.asyncio
async def test_list_by_user(test_db: AsyncSession, sample_proposals_batch):
    """Test listing proposals by user."""
    repo = OpenSpecRepository(test_db)

    # Create multiple proposals (all from same user)
    user_id = sample_proposals_batch[0]["created_by_user_id"]
    for data in sample_proposals_batch:
        proposal = OpenSpecProposal(**data)
        await repo.create(proposal)
    await test_db.commit()

    # List all proposals by user
    proposals = await repo.list_by_user(user_id)

    assert len(proposals) == 5
    assert all(p.created_by_user_id == user_id for p in proposals)


@pytest.mark.asyncio
async def test_count_by_project(test_db: AsyncSession, sample_proposals_batch):
    """Test counting proposals by project."""
    repo = OpenSpecRepository(test_db)

    # Create multiple proposals
    project_id = sample_proposals_batch[0]["project_id"]
    for data in sample_proposals_batch:
        proposal = OpenSpecProposal(**data)
        await repo.create(proposal)
    await test_db.commit()

    # Count all
    total = await repo.count_by_project(project_id)
    assert total == 5

    # Count by status
    pending_count = await repo.count_by_project(project_id, status="pending")
    approved_count = await repo.count_by_project(project_id, status="approved")

    assert pending_count == 1
    assert approved_count == 1


# ============= Status Management Tests =============


@pytest.mark.asyncio
async def test_update_status_to_approved(test_db: AsyncSession, sample_proposal_data):
    """Test updating status to approved sets timestamps."""
    repo = OpenSpecRepository(test_db)

    # Create proposal
    proposal = OpenSpecProposal(**sample_proposal_data)
    await repo.create(proposal)
    await test_db.commit()

    # Update to approved (use same user as creator to avoid foreign key issues)
    updated = await repo.update_status(proposal.id, "approved", proposal.created_by_user_id)

    assert updated is not None
    assert updated.status == "approved"
    assert updated.approved_by_user_id == proposal.created_by_user_id
    assert updated.approved_at is not None
    assert updated.approved_at.tzinfo is not None  # Timezone-aware


@pytest.mark.asyncio
async def test_update_status_to_archived(test_db: AsyncSession, sample_proposal_data):
    """Test updating status to archived sets archived_at timestamp."""
    repo = OpenSpecRepository(test_db)

    # Create proposal
    proposal = OpenSpecProposal(**sample_proposal_data)
    await repo.create(proposal)
    await test_db.commit()

    # Update to archived
    updated = await repo.update_status(proposal.id, "archived")

    assert updated is not None
    assert updated.status == "archived"
    assert updated.archived_at is not None
    assert updated.archived_at.tzinfo is not None  # Timezone-aware


@pytest.mark.asyncio
async def test_get_active_proposals(test_db: AsyncSession, sample_proposals_batch):
    """Test getting active proposals (excludes archived and completed)."""
    repo = OpenSpecRepository(test_db)

    # Create multiple proposals with different statuses
    project_id = sample_proposals_batch[0]["project_id"]
    for data in sample_proposals_batch:
        proposal = OpenSpecProposal(**data)
        await repo.create(proposal)
    await test_db.commit()

    # Get active proposals
    active = await repo.get_active_proposals(project_id)

    # Should exclude archived (1) and include all others (4)
    # But sample_proposals_batch has: pending, approved, in_progress, archived, rejected
    # Active should be: pending, approved, in_progress, rejected (4 total)
    assert len(active) == 4
    assert all(p.status not in ["archived", "completed"] for p in active)


# ============= Content Update Tests =============


@pytest.mark.asyncio
async def test_update_content_partial(test_db: AsyncSession, sample_proposal_data):
    """Test partial content update (only some fields)."""
    repo = OpenSpecRepository(test_db)

    # Create proposal
    proposal = OpenSpecProposal(**sample_proposal_data)
    await repo.create(proposal)
    await test_db.commit()

    original_tasks = proposal.tasks_content

    # Update only proposal content
    new_proposal_content = "# Updated Proposal\n## New Summary"
    updated = await repo.update_content(proposal.id, proposal_content=new_proposal_content)

    assert updated is not None
    assert updated.proposal_content == new_proposal_content
    assert updated.tasks_content == original_tasks  # Unchanged
    assert updated.task_sync_status == "not_synced"  # Unchanged (tasks not modified)


@pytest.mark.asyncio
async def test_update_content_resets_sync_status(test_db: AsyncSession, sample_proposal_data):
    """Test that updating tasks_content resets sync status."""
    repo = OpenSpecRepository(test_db)

    # Create proposal with synced status
    sample_proposal_data["task_sync_status"] = "synced"
    proposal = OpenSpecProposal(**sample_proposal_data)
    await repo.create(proposal)
    await test_db.commit()

    assert proposal.task_sync_status == "synced"

    # Update tasks content
    new_tasks = "# Updated Tasks\n## TAS-001: New Task"
    updated = await repo.update_content(proposal.id, tasks_content=new_tasks)

    assert updated is not None
    assert updated.tasks_content == new_tasks
    assert updated.task_sync_status == "not_synced"  # Reset!


@pytest.mark.asyncio
async def test_update_content_no_change_preserves_sync(test_db: AsyncSession, sample_proposal_data):
    """Test that updating non-task content preserves sync status."""
    repo = OpenSpecRepository(test_db)

    # Create proposal with synced status
    sample_proposal_data["task_sync_status"] = "synced"
    proposal = OpenSpecProposal(**sample_proposal_data)
    await repo.create(proposal)
    await test_db.commit()

    # Update only proposal content (not tasks)
    updated = await repo.update_content(proposal.id, proposal_content="# Updated Proposal")

    assert updated is not None
    assert updated.task_sync_status == "synced"  # Preserved!


# ============= Sync Status Tests =============


@pytest.mark.asyncio
async def test_update_sync_status_success(test_db: AsyncSession, sample_proposal_data):
    """Test updating sync status."""
    repo = OpenSpecRepository(test_db)

    # Create proposal
    proposal = OpenSpecProposal(**sample_proposal_data)
    await repo.create(proposal)
    await test_db.commit()

    # Update to syncing
    updated = await repo.update_sync_status(proposal.id, "syncing")

    assert updated is not None
    assert updated.task_sync_status == "syncing"
    assert updated.last_sync_at is not None
    assert updated.sync_error_message is None


@pytest.mark.asyncio
async def test_update_sync_status_with_error(test_db: AsyncSession, sample_proposal_data):
    """Test updating sync status with error message."""
    repo = OpenSpecRepository(test_db)

    # Create proposal
    proposal = OpenSpecProposal(**sample_proposal_data)
    await repo.create(proposal)
    await test_db.commit()

    # Update to sync_failed with error
    error_msg = "Failed to parse tasks.md: Invalid format at line 42"
    updated = await repo.update_sync_status(proposal.id, "sync_failed", error_message=error_msg)

    assert updated is not None
    assert updated.task_sync_status == "sync_failed"
    assert updated.sync_error_message == error_msg
    assert updated.last_sync_at is not None


@pytest.mark.asyncio
async def test_update_sync_status_clears_error_on_success(
    test_db: AsyncSession, sample_proposal_data
):
    """Test that successful sync clears previous error message."""
    repo = OpenSpecRepository(test_db)

    # Create proposal with error
    sample_proposal_data["task_sync_status"] = "sync_failed"
    sample_proposal_data["sync_error_message"] = "Previous error"
    proposal = OpenSpecProposal(**sample_proposal_data)
    await repo.create(proposal)
    await test_db.commit()

    assert proposal.sync_error_message == "Previous error"

    # Update to synced (should clear error)
    updated = await repo.update_sync_status(proposal.id, "synced")

    assert updated is not None
    assert updated.task_sync_status == "synced"
    assert updated.sync_error_message is None  # Cleared!


@pytest.mark.asyncio
async def test_calculate_completion_with_tasks(test_db: AsyncSession, sample_proposal_data):
    """Test completion calculation with linked tasks."""
    repo = OpenSpecRepository(test_db)

    # Create proposal
    proposal = OpenSpecProposal(**sample_proposal_data)
    await repo.create(proposal)
    await test_db.commit()

    # Create 3 tasks, 2 completed
    task1 = Task(
        project_id=proposal.project_id,
        identifier="TAS-001",
        title="Task 1",
        status="done",
        created_by_id=proposal.created_by_user_id,
        openspec_proposal_id=proposal.id,
    )
    task2 = Task(
        project_id=proposal.project_id,
        identifier="TAS-002",
        title="Task 2",
        status="done",
        created_by_id=proposal.created_by_user_id,
        openspec_proposal_id=proposal.id,
    )
    task3 = Task(
        project_id=proposal.project_id,
        identifier="TAS-003",
        title="Task 3",
        status="in_progress",
        created_by_id=proposal.created_by_user_id,
        openspec_proposal_id=proposal.id,
    )

    test_db.add_all([task1, task2, task3])
    await test_db.commit()

    # Calculate completion
    completion = await repo.calculate_completion(proposal.id)

    # 2 out of 3 = 66%
    assert completion == 66

    # Verify proposal updated
    updated_proposal = await repo.get_by_id(proposal.id)
    assert updated_proposal is not None
    assert updated_proposal.completion_percentage == 66


@pytest.mark.asyncio
async def test_calculate_completion_no_tasks(test_db: AsyncSession, sample_proposal_data):
    """Test completion calculation with no tasks returns 0."""
    repo = OpenSpecRepository(test_db)

    # Create proposal without tasks
    proposal = OpenSpecProposal(**sample_proposal_data)
    await repo.create(proposal)
    await test_db.commit()

    # Calculate completion
    completion = await repo.calculate_completion(proposal.id)

    assert completion == 0

    # Verify proposal updated
    updated_proposal = await repo.get_by_id(proposal.id)
    assert updated_proposal is not None
    assert updated_proposal.completion_percentage == 0


@pytest.mark.asyncio
async def test_calculate_completion_all_tasks_done(test_db: AsyncSession, sample_proposal_data):
    """Test completion calculation with all tasks completed."""
    repo = OpenSpecRepository(test_db)

    # Create proposal
    proposal = OpenSpecProposal(**sample_proposal_data)
    await repo.create(proposal)
    await test_db.commit()

    # Create 2 completed tasks
    task1 = Task(
        project_id=proposal.project_id,
        identifier="TAS-001",
        title="Task 1",
        status="done",
        created_by_id=proposal.created_by_user_id,
        openspec_proposal_id=proposal.id,
    )
    task2 = Task(
        project_id=proposal.project_id,
        identifier="TAS-002",
        title="Task 2",
        status="done",
        created_by_id=proposal.created_by_user_id,
        openspec_proposal_id=proposal.id,
    )

    test_db.add_all([task1, task2])
    await test_db.commit()

    # Calculate completion
    completion = await repo.calculate_completion(proposal.id)

    assert completion == 100


@pytest.mark.asyncio
async def test_list_by_user_with_status(test_db: AsyncSession):
    """Test listing user's proposals with status filter."""
    from ardha.models.project import Project
    from ardha.models.user import User

    repo = OpenSpecRepository(test_db)

    # Create user and project first (to satisfy foreign keys)
    user_id = uuid4()
    project_id = uuid4()

    user = User(
        id=user_id,
        email="test@example.com",
        username="testuser",
        full_name="Test User",
        password_hash="hashed",
    )
    project = Project(
        id=project_id,
        name="Test Project",
        slug="test-project",
        owner_id=user_id,
        visibility="private",
    )
    test_db.add(user)
    test_db.add(project)
    await test_db.flush()

    # Create proposals with different statuses
    proposal1 = OpenSpecProposal(
        project_id=project_id,
        name="proposal-1",
        directory_path="openspec/changes/proposal-1",
        status="pending",
        created_by_user_id=user_id,
    )
    proposal2 = OpenSpecProposal(
        project_id=project_id,
        name="proposal-2",
        directory_path="openspec/changes/proposal-2",
        status="approved",
        created_by_user_id=user_id,
    )

    await repo.create(proposal1)
    await repo.create(proposal2)
    await test_db.commit()

    # Filter by status
    pending = await repo.list_by_user(user_id, status="pending")
    approved = await repo.list_by_user(user_id, status="approved")

    assert len(pending) == 1
    assert len(approved) == 1
    assert pending[0].status == "pending"
    assert approved[0].status == "approved"


@pytest.mark.asyncio
async def test_count_by_project_empty(test_db: AsyncSession):
    """Test counting proposals for project with no proposals."""
    repo = OpenSpecRepository(test_db)

    project_id = uuid4()
    count = await repo.count_by_project(project_id)

    assert count == 0


@pytest.mark.asyncio
async def test_get_active_proposals_empty(test_db: AsyncSession):
    """Test getting active proposals when none exist."""
    repo = OpenSpecRepository(test_db)

    project_id = uuid4()
    active = await repo.get_active_proposals(project_id)

    assert active == []


@pytest.mark.asyncio
async def test_update_content_not_found(test_db: AsyncSession):
    """Test updating content for non-existent proposal returns None."""
    repo = OpenSpecRepository(test_db)

    non_existent_id = uuid4()
    updated = await repo.update_content(non_existent_id, proposal_content="Updated")

    assert updated is None


@pytest.mark.asyncio
async def test_update_sync_status_not_found(test_db: AsyncSession):
    """Test updating sync status for non-existent proposal returns None."""
    repo = OpenSpecRepository(test_db)

    non_existent_id = uuid4()
    updated = await repo.update_sync_status(non_existent_id, "synced")

    assert updated is None


@pytest.mark.asyncio
async def test_calculate_completion_not_found(test_db: AsyncSession):
    """Test calculating completion for non-existent proposal returns 0."""
    repo = OpenSpecRepository(test_db)

    non_existent_id = uuid4()
    completion = await repo.calculate_completion(non_existent_id)

    assert completion == 0
