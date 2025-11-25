"""
OpenSpec Proposal response schemas for API responses.

This module defines Pydantic models for formatting OpenSpec proposal-related responses.
"""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class OpenSpecProposalResponse(BaseModel):
    """
    Response schema for OpenSpec proposal with complete details.

    Attributes:
        id: Proposal UUID
        project_id: Parent project UUID
        name: Proposal name
        directory_path: Full path to proposal directory
        status: Current status (pending, approved, rejected, etc.)
        created_by_user_id: Creator UUID
        created_by_username: Creator username (if available)
        created_by_full_name: Creator full name (if available)
        proposal_content: Content of proposal.md
        tasks_content: Content of tasks.md
        spec_delta_content: Content of spec-delta.md
        metadata_json: Parsed metadata
        approved_by_user_id: Approver UUID (nullable)
        approved_by_username: Approver username (if available)
        approved_by_full_name: Approver full name (if available)
        approved_at: Approval timestamp
        archived_at: Archival timestamp
        completion_percentage: Progress percentage (0-100)
        task_sync_status: Task synchronization status
        last_sync_at: Last sync timestamp
        sync_error_message: Sync error message (if any)
        created_at: Creation timestamp
        updated_at: Last update timestamp
        is_editable: Computed: Can proposal be edited?
        can_approve: Computed: Can proposal be approved?
    """

    # Identity
    id: UUID
    project_id: UUID
    name: str
    directory_path: str

    # Status and workflow
    status: str
    created_by_user_id: UUID
    created_by_username: str | None = None
    created_by_full_name: str | None = None

    # Content fields
    proposal_content: str | None
    tasks_content: str | None
    spec_delta_content: str | None
    metadata_json: dict | None

    # Approval workflow
    approved_by_user_id: UUID | None
    approved_by_username: str | None = None
    approved_by_full_name: str | None = None
    approved_at: datetime | None
    archived_at: datetime | None

    # Progress tracking
    completion_percentage: int
    task_sync_status: str
    last_sync_at: datetime | None
    sync_error_message: str | None

    # Timestamps
    created_at: datetime
    updated_at: datetime

    # Computed fields (from model properties)
    is_editable: bool = False
    can_approve: bool = False

    model_config = ConfigDict(from_attributes=True)


class OpenSpecProposalListResponse(BaseModel):
    """
    Response schema for OpenSpec proposal in list view (summary).

    Lighter version for list endpoints, excluding large content fields.

    Attributes:
        id: Proposal UUID
        project_id: Parent project UUID
        name: Proposal name
        status: Current status
        created_by_user_id: Creator UUID
        created_by_username: Creator username
        approved_by_user_id: Approver UUID (nullable)
        approved_by_username: Approver username (nullable)
        completion_percentage: Progress percentage
        task_sync_status: Task sync status
        created_at: Creation timestamp
        updated_at: Last update timestamp
    """

    id: UUID
    project_id: UUID
    name: str
    status: str

    # Creator info
    created_by_user_id: UUID
    created_by_username: str | None = None

    # Approval info
    approved_by_user_id: UUID | None
    approved_by_username: str | None = None

    # Progress
    completion_percentage: int
    task_sync_status: str

    # Timestamps
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class OpenSpecProposalSyncResponse(BaseModel):
    """
    Response schema for task synchronization operation.

    Attributes:
        proposal_id: Proposal UUID
        tasks_created: Number of tasks created
        tasks_updated: Number of tasks updated
        sync_status: Result status (synced/sync_failed)
        error_message: Error message if sync failed
        synced_at: Timestamp of sync completion
    """

    proposal_id: UUID
    tasks_created: int
    tasks_updated: int = 0
    sync_status: str
    error_message: str | None = None
    synced_at: datetime


class OpenSpecProposalPaginatedResponse(BaseModel):
    """
    Response schema for paginated proposal lists.

    Attributes:
        proposals: List of proposals
        total: Total count (before pagination)
        skip: Pagination offset
        limit: Page size
    """

    proposals: list[OpenSpecProposalListResponse]
    total: int
    skip: int = 0
    limit: int = 100
