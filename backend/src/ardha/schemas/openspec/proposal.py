"""
Pydantic schemas for OpenSpec Proposal operations.

This module defines request and response schemas for OpenSpec proposal
CRUD operations with comprehensive validation.
"""

from datetime import datetime
from enum import Enum
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator


class ProposalStatus(str, Enum):
    """Enumeration of proposal statuses."""

    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    ARCHIVED = "archived"


class TaskSyncStatus(str, Enum):
    """Enumeration of task synchronization statuses."""

    NOT_SYNCED = "not_synced"
    SYNCING = "syncing"
    SYNCED = "synced"
    SYNC_FAILED = "sync_failed"


# ============= Base Schemas =============


class OpenSpecProposalBase(BaseModel):
    """Base schema with common proposal fields."""

    name: str = Field(
        ...,
        min_length=1,
        max_length=255,
        description="Unique proposal name within project (alphanumeric + hyphens)",
    )
    directory_path: str = Field(
        ...,
        min_length=1,
        max_length=512,
        description="Full path to proposal directory",
    )
    project_id: UUID = Field(..., description="UUID of parent project")

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        """
        Validate proposal name format.

        Args:
            v: Name to validate

        Returns:
            Validated name

        Raises:
            ValueError: If name contains invalid characters
        """
        # Allow alphanumeric, hyphens, and underscores only
        if not v.replace("-", "").replace("_", "").replace(" ", "").isalnum():
            raise ValueError(
                "Name must contain only alphanumeric characters, hyphens, "
                "underscores, and spaces"
            )
        return v.strip()


# ============= Request Schemas =============


class OpenSpecProposalCreate(OpenSpecProposalBase):
    """Schema for creating a new OpenSpec proposal."""

    proposal_content: Optional[str] = Field(None, description="Content of proposal.md file")
    tasks_content: Optional[str] = Field(None, description="Content of tasks.md file")
    spec_delta_content: Optional[str] = Field(None, description="Content of spec-delta.md file")
    metadata_json: Optional[dict] = Field(None, description="Parsed metadata.json content")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "name": "user-authentication-system",
                "directory_path": "openspec/changes/user-authentication-system",
                "project_id": "123e4567-e89b-12d3-a456-426614174000",
                "proposal_content": "# User Authentication System...",
                "tasks_content": "## Tasks\n- [ ] Implement login...",
            }
        }
    )


class OpenSpecProposalUpdate(BaseModel):
    """Schema for updating an existing OpenSpec proposal."""

    name: Optional[str] = Field(
        None,
        min_length=1,
        max_length=255,
        description="Updated proposal name",
    )
    directory_path: Optional[str] = Field(
        None,
        min_length=1,
        max_length=512,
        description="Updated directory path",
    )
    proposal_content: Optional[str] = Field(None, description="Updated proposal.md content")
    tasks_content: Optional[str] = Field(None, description="Updated tasks.md content")
    spec_delta_content: Optional[str] = Field(None, description="Updated spec-delta.md content")
    metadata_json: Optional[dict] = Field(None, description="Updated metadata.json content")
    status: Optional[ProposalStatus] = Field(None, description="Updated status")

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: Optional[str]) -> Optional[str]:
        """Validate proposal name format if provided."""
        if v is not None:
            if not v.replace("-", "").replace("_", "").replace(" ", "").isalnum():
                raise ValueError(
                    "Name must contain only alphanumeric characters, hyphens, "
                    "underscores, and spaces"
                )
            return v.strip()
        return v


class ApprovalRequest(BaseModel):
    """Schema for approving or rejecting a proposal."""

    approved: bool = Field(..., description="True to approve, False to reject")
    rejection_reason: Optional[str] = Field(
        None,
        min_length=1,
        max_length=1000,
        description="Reason for rejection (required if approved=False)",
    )

    @field_validator("rejection_reason")
    @classmethod
    def validate_rejection_reason(cls, v: Optional[str], info) -> Optional[str]:
        """Ensure rejection reason is provided when rejecting."""
        approved = info.data.get("approved")
        if approved is False and not v:
            raise ValueError("Rejection reason is required when rejecting a proposal")
        return v


# ============= Response Schemas =============


class OpenSpecProposalResponse(BaseModel):
    """Full response schema for OpenSpec proposal."""

    id: UUID
    project_id: UUID
    name: str
    directory_path: str
    status: ProposalStatus
    created_by_user_id: UUID
    proposal_content: Optional[str]
    tasks_content: Optional[str]
    spec_delta_content: Optional[str]
    metadata_json: Optional[dict]
    approved_by_user_id: Optional[UUID]
    approved_at: Optional[datetime]
    archived_at: Optional[datetime]
    completion_percentage: int
    task_sync_status: TaskSyncStatus
    last_sync_at: Optional[datetime]
    sync_error_message: Optional[str]
    created_at: datetime
    updated_at: datetime

    # Computed fields
    is_editable: bool = Field(
        ..., description="Whether proposal can be edited (pending or rejected)"
    )
    can_approve: bool = Field(..., description="Whether proposal can be approved (pending only)")

    # User names from relationships
    created_by_name: Optional[str] = Field(
        None, description="Full name of creator from User relationship"
    )
    approved_by_name: Optional[str] = Field(
        None, description="Full name of approver from User relationship"
    )

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "id": "123e4567-e89b-12d3-a456-426614174000",
                "project_id": "223e4567-e89b-12d3-a456-426614174001",
                "name": "user-authentication-system",
                "directory_path": "openspec/changes/user-authentication-system",
                "status": "approved",
                "created_by_user_id": "323e4567-e89b-12d3-a456-426614174002",
                "completion_percentage": 75,
                "task_sync_status": "synced",
                "is_editable": False,
                "can_approve": False,
                "created_by_name": "John Doe",
                "approved_by_name": "Jane Smith",
            }
        },
    )


class OpenSpecProposalListResponse(BaseModel):
    """Simplified response schema for list views (excludes large content fields)."""

    id: UUID
    project_id: UUID
    name: str
    directory_path: str
    status: ProposalStatus
    created_by_user_id: UUID
    approved_by_user_id: Optional[UUID]
    approved_at: Optional[datetime]
    archived_at: Optional[datetime]
    completion_percentage: int
    task_sync_status: TaskSyncStatus
    last_sync_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime

    # Computed fields
    is_editable: bool
    can_approve: bool

    # User names
    created_by_name: Optional[str] = None
    approved_by_name: Optional[str] = None

    # Summary stats
    total_tasks: int = Field(0, description="Total number of synced tasks")
    completed_tasks: int = Field(0, description="Number of completed tasks")

    model_config = ConfigDict(from_attributes=True)


class OpenSpecProposalSummary(BaseModel):
    """Minimal summary for dropdown selections and references."""

    id: UUID
    name: str
    status: ProposalStatus
    completion_percentage: int

    model_config = ConfigDict(from_attributes=True)
