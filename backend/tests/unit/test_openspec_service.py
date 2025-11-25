"""
Unit tests for OpenSpec service layer.

Tests business logic in isolation with mocked dependencies.
"""

import json
from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, Mock, patch
from uuid import uuid4

import pytest
from sqlalchemy.exc import IntegrityError

from ardha.models.openspec import OpenSpecProposal
from ardha.schemas.openspec.parsed import ParsedMetadata, ParsedProposal, ParsedTask
from ardha.services.openspec_service import (
    InsufficientOpenSpecPermissionsError,
    OpenSpecProposalExistsError,
    OpenSpecProposalNotFoundError,
    OpenSpecService,
    ProposalNotApprovableError,
    ProposalNotEditableError,
    TaskSyncError,
)

# ============= Fixtures =============


@pytest.fixture
def mock_openspec_repo():
    """Mock OpenSpecRepository."""
    return AsyncMock()


@pytest.fixture
def mock_parser():
    """Mock OpenSpecParserService."""
    parser = MagicMock()
    parser.archive_dir = Path("/tmp/archive")
    return parser


@pytest.fixture
def mock_task_service():
    """Mock TaskService."""
    return AsyncMock()


@pytest.fixture
def mock_project_service():
    """Mock ProjectService."""
    return AsyncMock()


@pytest.fixture
def mock_db():
    """Mock database session."""
    db = AsyncMock()
    db.flush = AsyncMock()
    db.refresh = AsyncMock()
    db.commit = AsyncMock()
    db.rollback = AsyncMock()
    return db


@pytest.fixture
def openspec_service(
    mock_openspec_repo,
    mock_parser,
    mock_task_service,
    mock_project_service,
    mock_db,
):
    """Create OpenSpecService with mocked dependencies."""
    return OpenSpecService(
        openspec_repo=mock_openspec_repo,
        parser=mock_parser,
        task_service=mock_task_service,
        project_service=mock_project_service,
        db=mock_db,
    )


@pytest.fixture
def sample_proposal():
    """Sample OpenSpecProposal for testing (Mock, not real model)."""
    proposal = Mock()
    proposal.id = uuid4()
    proposal.project_id = uuid4()
    proposal.name = "test-proposal"
    proposal.directory_path = "/openspec/changes/test-proposal"
    proposal.status = "pending"
    proposal.created_by_user_id = uuid4()
    proposal.proposal_content = "# Test Proposal\n\nThis is a test."
    proposal.tasks_content = "## TAS-001: Test Task"
    proposal.spec_delta_content = "# Changes\n\nTest changes."
    proposal.metadata_json = {"proposal_id": "test-001"}
    proposal.task_sync_status = "not_synced"
    proposal.completion_percentage = 0
    proposal.is_editable = True
    proposal.can_approve = True
    proposal.tasks = []

    # Add created_by relationship
    proposal.created_by = Mock()
    proposal.created_by.username = "testuser"
    proposal.created_by.full_name = "Test User"

    return proposal


@pytest.fixture
def sample_parsed_proposal():
    """Sample ParsedProposal for filesystem parsing."""
    metadata = ParsedMetadata(
        proposal_id="test-001",
        title="Test Proposal",
        author="testuser",
        created_at=datetime.now(UTC),
        raw_json={},
    )

    return ParsedProposal(
        name="test-proposal",
        directory_path="/openspec/changes/test-proposal",
        proposal_content="# Test Proposal\n\nThis is a test.",
        tasks_content="## TAS-001: Test Task",
        spec_delta_content="# Changes\n\nTest changes.",
        metadata=metadata,
        files_found=["proposal.md", "tasks.md", "spec-delta.md", "metadata.json"],
    )


# ============= Test Cases =============


@pytest.mark.asyncio
async def test_create_from_filesystem_success(
    openspec_service,
    mock_openspec_repo,
    mock_parser,
    mock_project_service,
    sample_parsed_proposal,
    sample_proposal,
):
    """Test successful proposal creation from filesystem."""
    # Setup
    project_id = uuid4()
    user_id = uuid4()

    mock_project_service.check_permission = AsyncMock(return_value=True)
    mock_openspec_repo.get_by_name = AsyncMock(return_value=None)
    mock_parser.parse_proposal = Mock(return_value=sample_parsed_proposal)
    mock_openspec_repo.create = AsyncMock(return_value=sample_proposal)

    # Execute
    result = await openspec_service.create_from_filesystem(
        project_id=project_id,
        proposal_name="test-proposal",
        user_id=user_id,
    )

    # Verify
    assert result.name == "test-proposal"
    assert result.status == "pending"
    mock_project_service.check_permission.assert_called_once()
    mock_openspec_repo.get_by_name.assert_called_once()
    mock_parser.parse_proposal.assert_called_once()
    mock_openspec_repo.create.assert_called_once()


@pytest.mark.asyncio
async def test_create_from_filesystem_duplicate_name(
    openspec_service,
    mock_openspec_repo,
    mock_project_service,
    sample_proposal,
):
    """Test creation fails when proposal name already exists."""
    # Setup
    project_id = uuid4()
    user_id = uuid4()

    mock_project_service.check_permission = AsyncMock(return_value=True)
    mock_openspec_repo.get_by_name = AsyncMock(return_value=sample_proposal)

    # Execute & Verify
    with pytest.raises(OpenSpecProposalExistsError):
        await openspec_service.create_from_filesystem(
            project_id=project_id,
            proposal_name="test-proposal",
            user_id=user_id,
        )


@pytest.mark.asyncio
async def test_create_from_filesystem_parse_error(
    openspec_service,
    mock_openspec_repo,
    mock_parser,
    mock_project_service,
):
    """Test creation fails when parsing fails."""
    # Setup
    from ardha.core.exceptions import OpenSpecParseError

    project_id = uuid4()
    user_id = uuid4()

    mock_project_service.check_permission = AsyncMock(return_value=True)
    mock_openspec_repo.get_by_name = AsyncMock(return_value=None)
    mock_parser.parse_proposal = Mock(side_effect=OpenSpecParseError("Parse error"))

    # Execute & Verify
    with pytest.raises(OpenSpecParseError):
        await openspec_service.create_from_filesystem(
            project_id=project_id,
            proposal_name="test-proposal",
            user_id=user_id,
        )


@pytest.mark.asyncio
async def test_get_proposal_with_access(
    openspec_service,
    mock_openspec_repo,
    mock_project_service,
    sample_proposal,
):
    """Test getting proposal with proper access."""
    # Setup
    mock_openspec_repo.get_by_id = AsyncMock(return_value=sample_proposal)
    mock_project_service.check_permission = AsyncMock(return_value=True)

    # Execute
    result = await openspec_service.get_proposal(
        proposal_id=sample_proposal.id,
        user_id=uuid4(),
    )

    # Verify
    assert result == sample_proposal
    mock_project_service.check_permission.assert_called_once()


@pytest.mark.asyncio
async def test_get_proposal_without_access(
    openspec_service,
    mock_openspec_repo,
    mock_project_service,
    sample_proposal,
):
    """Test getting proposal without access raises error."""
    # Setup
    mock_openspec_repo.get_by_id = AsyncMock(return_value=sample_proposal)
    mock_project_service.check_permission = AsyncMock(return_value=False)

    # Execute & Verify
    with pytest.raises(InsufficientOpenSpecPermissionsError):
        await openspec_service.get_proposal(
            proposal_id=sample_proposal.id,
            user_id=uuid4(),
        )


@pytest.mark.asyncio
async def test_approve_proposal_success(
    openspec_service,
    mock_openspec_repo,
    mock_project_service,
    sample_proposal,
):
    """Test successful proposal approval."""
    # Setup
    user_id = uuid4()
    sample_proposal.status = "pending"  # Can approve
    approved_proposal = Mock(**sample_proposal.__dict__)
    approved_proposal.status = "approved"

    mock_openspec_repo.get_by_id = AsyncMock(return_value=sample_proposal)
    mock_project_service.check_permission = AsyncMock(return_value=True)
    mock_openspec_repo.update_status = AsyncMock(return_value=approved_proposal)

    # Execute
    result = await openspec_service.approve_proposal(
        proposal_id=sample_proposal.id,
        user_id=user_id,
    )

    # Verify
    assert result.status == "approved"
    mock_project_service.check_permission.assert_called_once_with(
        project_id=sample_proposal.project_id,
        user_id=user_id,
        required_role="admin",
    )


@pytest.mark.asyncio
async def test_approve_proposal_requires_admin(
    openspec_service,
    mock_openspec_repo,
    mock_project_service,
    sample_proposal,
):
    """Test approval requires admin role."""
    # Setup
    mock_openspec_repo.get_by_id = AsyncMock(return_value=sample_proposal)
    mock_project_service.check_permission = AsyncMock(return_value=False)

    # Execute & Verify
    with pytest.raises(InsufficientOpenSpecPermissionsError):
        await openspec_service.approve_proposal(
            proposal_id=sample_proposal.id,
            user_id=uuid4(),
        )


@pytest.mark.asyncio
async def test_approve_proposal_not_pending(
    openspec_service,
    mock_openspec_repo,
    mock_project_service,
    sample_proposal,
):
    """Test approval fails if proposal is not pending."""
    # Setup
    sample_proposal.status = "approved"  # Already approved
    sample_proposal.can_approve = False  # Not approvable
    mock_openspec_repo.get_by_id = AsyncMock(return_value=sample_proposal)
    mock_project_service.check_permission = AsyncMock(return_value=True)

    # Execute & Verify
    with pytest.raises(ProposalNotApprovableError):
        await openspec_service.approve_proposal(
            proposal_id=sample_proposal.id,
            user_id=uuid4(),
        )


@pytest.mark.asyncio
async def test_reject_proposal_success(
    openspec_service,
    mock_openspec_repo,
    mock_project_service,
    sample_proposal,
):
    """Test successful proposal rejection."""
    # Setup
    user_id = uuid4()
    rejected_proposal = Mock(**sample_proposal.__dict__)
    rejected_proposal.status = "rejected"

    mock_openspec_repo.get_by_id = AsyncMock(return_value=sample_proposal)
    mock_project_service.check_permission = AsyncMock(return_value=True)
    mock_openspec_repo.update_status = AsyncMock(return_value=rejected_proposal)
    mock_openspec_repo.update = AsyncMock(return_value=rejected_proposal)

    # Execute
    result = await openspec_service.reject_proposal(
        proposal_id=sample_proposal.id,
        user_id=user_id,
        reason="Not feasible at this time",
    )

    # Verify
    assert result.status == "rejected"
    mock_openspec_repo.update.assert_called_once()


@pytest.mark.asyncio
async def test_sync_tasks_success(
    openspec_service,
    mock_openspec_repo,
    mock_parser,
    mock_task_service,
    mock_project_service,
    sample_proposal,
):
    """Test successful task synchronization."""
    # Setup
    user_id = uuid4()
    sample_proposal.status = "approved"

    # Mock parsed tasks
    parsed_task = ParsedTask(
        identifier="TAS-001",
        title="Test Task",
        description="Test description",
        phase=None,
        estimated_hours=None,
        dependencies=[],
        acceptance_criteria=[],
        markdown_section="## TAS-001: Test Task",
    )

    # Mock created task
    created_task = Mock()
    created_task.id = uuid4()
    created_task.identifier = "ARD-001"

    mock_openspec_repo.get_by_id = AsyncMock(return_value=sample_proposal)
    mock_project_service.check_permission = AsyncMock(return_value=True)
    mock_openspec_repo.update_sync_status = AsyncMock()
    mock_parser.extract_tasks_from_markdown = Mock(return_value=[parsed_task])
    mock_task_service.create_task = AsyncMock(return_value=created_task)
    mock_task_service.link_openspec_proposal = AsyncMock()

    # Execute
    result = await openspec_service.sync_tasks_to_database(
        proposal_id=sample_proposal.id,
        user_id=user_id,
    )

    # Verify
    assert len(result) == 1
    assert result[0].identifier == "ARD-001"
    mock_task_service.create_task.assert_called_once()
    mock_task_service.link_openspec_proposal.assert_called_once()


@pytest.mark.asyncio
async def test_sync_tasks_not_approved(
    openspec_service,
    mock_openspec_repo,
    mock_project_service,
    sample_proposal,
):
    """Test task sync fails if proposal not approved."""
    # Setup
    sample_proposal.status = "pending"
    mock_openspec_repo.get_by_id = AsyncMock(return_value=sample_proposal)
    mock_project_service.check_permission = AsyncMock(return_value=True)

    # Execute & Verify
    with pytest.raises(TaskSyncError, match="Only approved proposals"):
        await openspec_service.sync_tasks_to_database(
            proposal_id=sample_proposal.id,
            user_id=uuid4(),
        )


@pytest.mark.asyncio
async def test_refresh_from_filesystem(
    openspec_service,
    mock_openspec_repo,
    mock_parser,
    mock_project_service,
    sample_proposal,
    sample_parsed_proposal,
):
    """Test refreshing proposal from filesystem."""
    # Setup
    refreshed_proposal = Mock(**sample_proposal.__dict__)
    refreshed_proposal.proposal_content = "# Updated Proposal"

    mock_openspec_repo.get_by_id = AsyncMock(return_value=sample_proposal)
    mock_project_service.check_permission = AsyncMock(return_value=True)
    mock_parser.parse_proposal = Mock(return_value=sample_parsed_proposal)
    mock_openspec_repo.update_content = AsyncMock(return_value=refreshed_proposal)

    # Execute
    result = await openspec_service.refresh_from_filesystem(
        proposal_id=sample_proposal.id,
        user_id=uuid4(),
    )

    # Verify
    mock_parser.parse_proposal.assert_called_once_with("test-proposal")
    mock_openspec_repo.update_content.assert_called_once()


@pytest.mark.asyncio
async def test_archive_proposal(
    openspec_service,
    mock_openspec_repo,
    mock_project_service,
    sample_proposal,
):
    """Test proposal archival."""
    # Setup
    archived_proposal = Mock(**sample_proposal.__dict__)
    archived_proposal.status = "archived"
    archived_proposal.archived_at = datetime.now(UTC)

    mock_openspec_repo.get_by_id = AsyncMock(return_value=sample_proposal)
    mock_project_service.check_permission = AsyncMock(return_value=True)
    mock_openspec_repo.update_status = AsyncMock(return_value=archived_proposal)
    mock_openspec_repo.update = AsyncMock(return_value=archived_proposal)

    # Mock filesystem operations
    with patch("pathlib.Path.exists", return_value=False):
        # Execute
        result = await openspec_service.archive_proposal(
            proposal_id=sample_proposal.id,
            user_id=uuid4(),
        )

    # Verify
    assert result.status == "archived"
    mock_openspec_repo.update_status.assert_called_once()


@pytest.mark.asyncio
async def test_calculate_completion(
    openspec_service,
    mock_openspec_repo,
):
    """Test completion percentage calculation."""
    # Setup
    proposal_id = uuid4()
    mock_openspec_repo.calculate_completion = AsyncMock(return_value=66)

    # Execute
    result = await openspec_service.calculate_and_update_completion(proposal_id)

    # Verify
    assert result == 66
    mock_openspec_repo.calculate_completion.assert_called_once_with(proposal_id)


@pytest.mark.asyncio
async def test_verify_project_access_success(
    openspec_service,
    mock_project_service,
):
    """Test project access verification succeeds."""
    # Setup
    project_id = uuid4()
    user_id = uuid4()
    mock_project_service.check_permission = AsyncMock(return_value=True)

    # Execute
    result = await openspec_service._verify_project_access(
        project_id=project_id,
        user_id=user_id,
        required_role="member",
    )

    # Verify
    assert result is True


@pytest.mark.asyncio
async def test_verify_project_access_denied(
    openspec_service,
    mock_project_service,
):
    """Test project access verification fails."""
    # Setup
    project_id = uuid4()
    user_id = uuid4()
    mock_project_service.check_permission = AsyncMock(return_value=False)

    # Execute & Verify
    with pytest.raises(InsufficientOpenSpecPermissionsError):
        await openspec_service._verify_project_access(
            project_id=project_id,
            user_id=user_id,
            required_role="admin",
        )


@pytest.mark.asyncio
async def test_update_proposal_not_editable(
    openspec_service,
    mock_openspec_repo,
    mock_project_service,
    sample_proposal,
):
    """Test update fails if proposal is not editable."""
    # Setup
    sample_proposal.status = "approved"  # Not editable
    sample_proposal.is_editable = False  # Property set to False
    mock_openspec_repo.get_by_id = AsyncMock(return_value=sample_proposal)
    mock_project_service.check_permission = AsyncMock(return_value=True)

    # Execute & Verify
    with pytest.raises(ProposalNotEditableError):
        await openspec_service.update_proposal(
            proposal_id=sample_proposal.id,
            update_data={"proposal_content": "New content"},
            user_id=uuid4(),
        )


@pytest.mark.asyncio
async def test_delete_proposal_with_synced_tasks(
    openspec_service,
    mock_openspec_repo,
    mock_project_service,
    sample_proposal,
):
    """Test delete fails if proposal has synced tasks."""
    # Setup
    sample_proposal.task_sync_status = "synced"
    sample_proposal.tasks = [Mock()]  # Has tasks

    mock_openspec_repo.get_by_id = AsyncMock(return_value=sample_proposal)
    mock_project_service.check_permission = AsyncMock(return_value=True)

    # Execute & Verify
    with pytest.raises(TaskSyncError, match="Cannot delete proposal with synced tasks"):
        await openspec_service.delete_proposal(
            proposal_id=sample_proposal.id,
            user_id=uuid4(),
        )


@pytest.mark.asyncio
async def test_list_proposals(
    openspec_service,
    mock_openspec_repo,
    mock_project_service,
    sample_proposal,
):
    """Test listing proposals for a project."""
    # Setup
    project_id = uuid4()
    user_id = uuid4()

    mock_project_service.check_permission = AsyncMock(return_value=True)
    mock_openspec_repo.list_by_project = AsyncMock(return_value=[sample_proposal])
    mock_openspec_repo.count_by_project = AsyncMock(return_value=1)

    # Execute
    proposals, total = await openspec_service.list_proposals(
        project_id=project_id,
        user_id=user_id,
        status="pending",
        skip=0,
        limit=100,
    )

    # Verify
    assert len(proposals) == 1
    assert total == 1
    assert proposals[0].name == "test-proposal"
