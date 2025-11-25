"""
Test fixtures for OpenSpec proposal testing.

This module provides reusable test fixtures for OpenSpec proposal testing,
including sample data, factories, and helper functions.
"""

from datetime import UTC, datetime
from uuid import UUID, uuid4

import pytest

from ardha.models.openspec import OpenSpecProposal
from ardha.models.project import Project
from ardha.models.user import User


@pytest.fixture
def sample_proposal_data():
    """
    Sample data for creating OpenSpec proposals.

    Returns:
        Dictionary with all required proposal fields
    """
    return {
        "project_id": uuid4(),
        "name": "user-auth-system",
        "directory_path": "openspec/changes/user-auth-system",
        "status": "pending",
        "created_by_user_id": uuid4(),
        "proposal_content": """# User Authentication System

## Summary
Implement JWT-based authentication with OAuth support.

## Motivation
Users need secure authentication to access the platform.

## Implementation Plan
1. Create User model
2. Implement JWT token generation
3. Add OAuth providers (GitHub, Google)
""",
        "tasks_content": """# Tasks

## TAS-001: Create User Model
- Create SQLAlchemy User model
- Add email, password_hash fields
- Create migration

## TAS-002: Implement JWT Service
- Token generation
- Token validation
- Refresh token logic

## TAS-003: OAuth Integration
- GitHub OAuth flow
- Google OAuth flow
""",
        "spec_delta_content": """# Specification Changes

## Database Schema
- Add `users` table
- Add `oauth_accounts` table

## API Endpoints
- POST /api/v1/auth/register
- POST /api/v1/auth/login
- POST /api/v1/auth/refresh
""",
        "metadata_json": {
            "proposal_id": "user-auth-system",
            "title": "User Authentication System",
            "author": "AI Assistant",
            "created_at": datetime.now(UTC).isoformat(),
            "priority": "high",
            "estimated_effort": "3 days",
            "tags": ["backend", "security", "authentication"],
        },
        "task_sync_status": "not_synced",
        "completion_percentage": 0,
    }


@pytest.fixture
def sample_approved_proposal_data():
    """
    Sample data for an approved proposal.

    Returns:
        Dictionary with approved proposal fields
    """
    approver_id = uuid4()
    return {
        "project_id": uuid4(),
        "name": "task-management",
        "directory_path": "openspec/changes/task-management",
        "status": "approved",
        "created_by_user_id": uuid4(),
        "approved_by_user_id": approver_id,
        "approved_at": datetime.now(UTC),
        "proposal_content": "# Task Management System\n...",
        "tasks_content": "# Tasks\n## TAS-001: Create Task Model\n...",
        "spec_delta_content": "# Changes\n- Add tasks table\n...",
        "metadata_json": {
            "proposal_id": "task-management",
            "title": "Task Management System",
            "priority": "critical",
        },
        "task_sync_status": "synced",
        "completion_percentage": 0,
    }


@pytest.fixture
def sample_archived_proposal_data():
    """
    Sample data for an archived proposal.

    Returns:
        Dictionary with archived proposal fields
    """
    return {
        "project_id": uuid4(),
        "name": "deprecated-feature",
        "directory_path": "openspec/archive/deprecated-feature",
        "status": "archived",
        "created_by_user_id": uuid4(),
        "archived_at": datetime.now(UTC),
        "proposal_content": "# Deprecated Feature\n...",
        "tasks_content": "# Tasks\n## TAS-001: Remove Feature\n...",
        "spec_delta_content": "# Changes\n- Remove deprecated code\n...",
        "metadata_json": {"proposal_id": "deprecated-feature", "title": "Deprecated"},
        "task_sync_status": "not_synced",
        "completion_percentage": 100,
    }


@pytest.fixture
def sample_proposals_batch():
    """
    Batch of sample proposals for pagination and filtering tests.

    Returns:
        List of 5 proposal data dictionaries with different statuses
    """
    project_id = uuid4()
    user_id = uuid4()

    return [
        {
            "project_id": project_id,
            "name": "proposal-pending-1",
            "directory_path": "openspec/changes/proposal-pending-1",
            "status": "pending",
            "created_by_user_id": user_id,
            "proposal_content": "# Pending Proposal 1\n...",
            "tasks_content": "# Tasks\n## TAS-001: Task 1\n...",
            "spec_delta_content": "# Changes\n...",
            "metadata_json": {"proposal_id": "proposal-pending-1", "priority": "low"},
        },
        {
            "project_id": project_id,
            "name": "proposal-approved-1",
            "directory_path": "openspec/changes/proposal-approved-1",
            "status": "approved",
            "created_by_user_id": user_id,
            "approved_by_user_id": uuid4(),
            "approved_at": datetime.now(UTC),
            "proposal_content": "# Approved Proposal 1\n...",
            "tasks_content": "# Tasks\n## TAS-001: Task 1\n...",
            "spec_delta_content": "# Changes\n...",
            "metadata_json": {"proposal_id": "proposal-approved-1", "priority": "high"},
        },
        {
            "project_id": project_id,
            "name": "proposal-in-progress",
            "directory_path": "openspec/changes/proposal-in-progress",
            "status": "in_progress",
            "created_by_user_id": user_id,
            "proposal_content": "# In Progress Proposal\n...",
            "tasks_content": "# Tasks\n## TAS-001: Task 1\n...",
            "spec_delta_content": "# Changes\n...",
            "metadata_json": {"proposal_id": "proposal-in-progress", "priority": "medium"},
            "task_sync_status": "synced",
            "completion_percentage": 50,
        },
        {
            "project_id": project_id,
            "name": "proposal-archived-1",
            "directory_path": "openspec/archive/proposal-archived-1",
            "status": "archived",
            "created_by_user_id": user_id,
            "archived_at": datetime.now(UTC),
            "proposal_content": "# Archived Proposal 1\n...",
            "tasks_content": "# Tasks\n## TAS-001: Task 1\n...",
            "spec_delta_content": "# Changes\n...",
            "metadata_json": {"proposal_id": "proposal-archived-1", "priority": "low"},
            "completion_percentage": 100,
        },
        {
            "project_id": project_id,
            "name": "proposal-rejected",
            "directory_path": "openspec/changes/proposal-rejected",
            "status": "rejected",
            "created_by_user_id": user_id,
            "proposal_content": "# Rejected Proposal\n...",
            "tasks_content": "# Tasks\n## TAS-001: Task 1\n...",
            "spec_delta_content": "# Changes\n...",
            "metadata_json": {"proposal_id": "proposal-rejected", "priority": "low"},
        },
    ]


@pytest.fixture
async def create_test_proposal(test_db):
    """
    Factory fixture to create test proposals in database.

    Args:
        test_db: Async database session fixture

    Returns:
        Async function to create proposals with optional overrides
    """

    async def _create(**overrides):
        """
        Create a test proposal with optional field overrides.

        Args:
            **overrides: Fields to override in default data

        Returns:
            Created OpenSpecProposal instance
        """
        # Default proposal data
        default_data = {
            "project_id": uuid4(),
            "name": f"test-proposal-{uuid4().hex[:8]}",
            "directory_path": f"openspec/changes/test-{uuid4().hex[:8]}",
            "status": "pending",
            "created_by_user_id": uuid4(),
            "proposal_content": "# Test Proposal\n## Summary\nTest content",
            "tasks_content": "# Tasks\n## TAS-001: Test Task\nTest task",
            "spec_delta_content": "# Changes\n- Test change",
            "metadata_json": {"proposal_id": "test", "title": "Test"},
        }

        # Merge with overrides
        data = {**default_data, **overrides}

        # Create proposal
        proposal = OpenSpecProposal(**data)
        test_db.add(proposal)
        await test_db.flush()
        await test_db.refresh(proposal)

        return proposal

    return _create


@pytest.fixture
async def sample_proposal(test_db, sample_proposal_data):
    """
    Create a single test proposal in the database.

    Args:
        test_db: Async database session
        sample_proposal_data: Sample proposal data

    Returns:
        Created OpenSpecProposal instance
    """
    proposal = OpenSpecProposal(**sample_proposal_data)
    test_db.add(proposal)
    await test_db.flush()
    await test_db.refresh(proposal)
    return proposal


@pytest.fixture
async def sample_proposals(test_db, sample_proposals_batch):
    """
    Create multiple test proposals in the database.

    Args:
        test_db: Async database session
        sample_proposals_batch: Batch of proposal data

    Returns:
        List of created OpenSpecProposal instances
    """
    proposals = []
    for data in sample_proposals_batch:
        proposal = OpenSpecProposal(**data)
        test_db.add(proposal)
        proposals.append(proposal)

    await test_db.flush()
    for proposal in proposals:
        await test_db.refresh(proposal)

    return proposals


@pytest.fixture
def sample_proposal_with_project(sample_proposal_data):
    """
    Sample proposal data with associated project and user.

    Returns:
        Tuple of (project, user, proposal_data)
    """
    project = Project(
        id=sample_proposal_data["project_id"],
        name="Test Project",
        slug="test-project",
        owner_id=sample_proposal_data["created_by_user_id"],
        visibility="private",
    )

    user = User(
        id=sample_proposal_data["created_by_user_id"],
        email="test@example.com",
        username="testuser",
        full_name="Test User",
        hashed_password="hashed",
    )

    return project, user, sample_proposal_data


@pytest.fixture
def sample_sync_status_data():
    """
    Sample data for testing sync status updates.

    Returns:
        Dictionary with sync status test data
    """
    return {
        "not_synced": {
            "sync_status": "not_synced",
            "error_message": None,
        },
        "syncing": {
            "sync_status": "syncing",
            "error_message": None,
        },
        "synced": {
            "sync_status": "synced",
            "error_message": None,
        },
        "sync_failed": {
            "sync_status": "sync_failed",
            "error_message": "Failed to parse tasks.md: Invalid task format at line 42",
        },
    }


@pytest.fixture
def sample_content_updates():
    """
    Sample data for testing content updates.

    Returns:
        Dictionary with different content update scenarios
    """
    return {
        "proposal_only": {
            "proposal_content": "# Updated Proposal\n## New Summary\nUpdated content",
        },
        "tasks_only": {
            "tasks_content": "# Updated Tasks\n## TAS-001: Updated Task\nNew task",
        },
        "all_content": {
            "proposal_content": "# Updated Proposal\n...",
            "tasks_content": "# Updated Tasks\n...",
            "spec_delta_content": "# Updated Spec\n...",
            "metadata_json": {"proposal_id": "updated", "title": "Updated"},
        },
    }
