"""
OpenSpec Proposal request schemas for API validation.

This module defines Pydantic models for OpenSpec proposal-related requests.
"""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field, field_validator


class OpenSpecProposalCreateRequest(BaseModel):
    """
    Request schema for creating an OpenSpec proposal from filesystem.

    Attributes:
        proposal_name: Name of the proposal (directory name in openspec/changes/)
    """

    proposal_name: str = Field(
        ...,
        min_length=1,
        max_length=255,
        description="Proposal name (directory name)",
    )

    @field_validator("proposal_name")
    @classmethod
    def validate_proposal_name(cls, v: str) -> str:
        """
        Validate proposal name.

        Args:
            v: Proposal name to validate

        Returns:
            Stripped proposal name

        Raises:
            ValueError: If name is empty or contains invalid characters
        """
        stripped = v.strip()
        if not stripped:
            raise ValueError("Proposal name cannot be empty or whitespace")

        # Check for invalid characters in directory names
        invalid_chars = ["/", "\\", ":", "*", "?", '"', "<", ">", "|"]
        if any(char in stripped for char in invalid_chars):
            raise ValueError(f"Proposal name cannot contain: {', '.join(invalid_chars)}")

        return stripped


class OpenSpecProposalUpdateRequest(BaseModel):
    """
    Request schema for updating an OpenSpec proposal.

    All fields are optional for partial updates.
    Only proposals with status 'pending' or 'rejected' can be updated.

    Attributes:
        proposal_content: Updated proposal.md content
        tasks_content: Updated tasks.md content
        spec_delta_content: Updated spec-delta.md content
        metadata_json: Updated metadata
    """

    proposal_content: str | None = Field(
        None,
        description="Content of proposal.md file",
    )

    tasks_content: str | None = Field(
        None,
        description="Content of tasks.md file",
    )

    spec_delta_content: str | None = Field(
        None,
        description="Content of spec-delta.md file",
    )

    metadata_json: dict | None = Field(
        None,
        description="Metadata JSON object",
    )


class OpenSpecProposalRejectRequest(BaseModel):
    """
    Request schema for rejecting a proposal.

    Attributes:
        reason: Reason for rejection (required)
    """

    reason: str = Field(
        ...,
        min_length=10,
        max_length=1000,
        description="Reason for rejection",
    )

    @field_validator("reason")
    @classmethod
    def validate_reason(cls, v: str) -> str:
        """Ensure reason is not just whitespace."""
        if not v or not v.strip():
            raise ValueError("Rejection reason cannot be empty")
        return v.strip()


class OpenSpecProposalFilterRequest(BaseModel):
    """
    Query parameters for filtering OpenSpec proposals.

    Attributes:
        status: Filter by status
        skip: Pagination offset
        limit: Page size (max 100)
    """

    status: str | None = Field(
        None,
        pattern="^(pending|approved|rejected|in_progress|completed|archived)$",
        description="Filter by proposal status",
    )

    skip: int = Field(
        default=0,
        ge=0,
        description="Number of records to skip",
    )

    limit: int = Field(
        default=100,
        ge=1,
        le=100,
        description="Maximum records to return",
    )
