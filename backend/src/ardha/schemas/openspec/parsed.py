"""
Pydantic schemas for parsed OpenSpec content.

This module defines schemas for OpenSpec files parsed from the file system,
including proposals, tasks, and metadata.
"""

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator


class ParsedMetadata(BaseModel):
    """Schema for parsed metadata.json content."""

    proposal_id: str = Field(..., description="Unique proposal identifier")
    title: str = Field(..., description="Proposal title")
    author: str = Field(..., description="Proposal author")
    created_at: datetime = Field(..., description="Creation timestamp")
    priority: str = Field(
        default="medium",
        description="Priority level (low/medium/high/critical)",
    )
    estimated_effort: str = Field(
        default="unknown",
        description="Estimated effort (e.g., '2-4 weeks', '1 sprint')",
    )
    tags: List[str] = Field(default_factory=list, description="Proposal tags")
    raw_json: dict = Field(..., description="Complete raw JSON for extensions")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "proposal_id": "user-auth-001",
                "title": "User Authentication System",
                "author": "John Doe",
                "created_at": "2025-11-15T10:00:00Z",
                "priority": "high",
                "estimated_effort": "2-3 weeks",
                "tags": ["authentication", "security", "backend"],
                "raw_json": {},
            }
        }
    )

    @field_validator("priority")
    @classmethod
    def validate_priority(cls, v: str) -> str:
        """Validate priority is one of allowed values."""
        allowed = ["low", "medium", "high", "critical"]
        if v.lower() not in allowed:
            raise ValueError(f"Priority must be one of: {', '.join(allowed)}")
        return v.lower()


class ParsedTask(BaseModel):
    """Schema for parsed task from tasks.md."""

    identifier: str = Field(..., description="Task identifier (e.g., 'TAS-001')")
    title: str = Field(..., description="Task title")
    description: str = Field(default="", description="Task description")
    phase: Optional[str] = Field(None, description="Development phase (e.g., 'Phase 1')")
    estimated_hours: Optional[int] = Field(
        None,
        ge=0,
        description="Estimated hours to complete",
    )
    dependencies: List[str] = Field(
        default_factory=list,
        description="List of task identifiers this task depends on",
    )
    acceptance_criteria: List[str] = Field(
        default_factory=list,
        description="List of acceptance criteria",
    )
    markdown_section: str = Field(
        ...,
        description="Original markdown text for this task",
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "identifier": "TAS-001",
                "title": "Implement user login endpoint",
                "description": "Create POST /api/v1/auth/login endpoint with JWT tokens",
                "phase": "Phase 1",
                "estimated_hours": 4,
                "dependencies": [],
                "acceptance_criteria": [
                    "Returns valid JWT tokens",
                    "Validates credentials",
                    "Handles errors gracefully",
                ],
                "markdown_section": "## TAS-001: Implement user login endpoint...",
            }
        }
    )

    @field_validator("identifier")
    @classmethod
    def validate_identifier(cls, v: str) -> str:
        """Validate task identifier format."""
        if not v or len(v) < 3:
            raise ValueError("Task identifier must be at least 3 characters")
        # Allow various formats: TAS-001, TASK-001, T001, etc.
        if not (v[0].isalpha() or v.startswith("TAS-")):
            raise ValueError("Task identifier must start with a letter or TAS-")
        return v.strip().upper()


class ParsedProposal(BaseModel):
    """Schema for complete parsed OpenSpec proposal."""

    name: str = Field(..., description="Proposal name (directory name)")
    directory_path: str = Field(..., description="Full path to proposal directory")
    proposal_content: str = Field(default="", description="Content of proposal.md")
    tasks_content: str = Field(default="", description="Content of tasks.md")
    spec_delta_content: str = Field(default="", description="Content of spec-delta.md")
    metadata: Optional[ParsedMetadata] = Field(
        default=None,
        description="Parsed metadata from metadata.json",
    )
    readme_content: Optional[str] = Field(default=None, description="Content of README.md")
    risk_assessment_content: Optional[str] = Field(
        default=None,
        description="Content of risk-assessment.md",
    )
    files_found: List[str] = Field(
        default_factory=list,
        description="List of all files found in proposal directory",
    )
    validation_errors: List[str] = Field(
        default_factory=list,
        description="List of validation errors (empty if valid)",
    )
    is_valid: bool = Field(
        default=True,
        description="True if proposal passed all validation checks",
    )

    # Parsed tasks extracted from tasks_content
    parsed_tasks: List[ParsedTask] = Field(
        default_factory=list,
        description="List of tasks parsed from tasks.md",
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "name": "user-auth-system",
                "directory_path": "/path/to/openspec/changes/user-auth-system",
                "proposal_content": "# User Authentication System\n\n...",
                "tasks_content": "## Tasks\n\n### TAS-001: Login endpoint...",
                "spec_delta_content": "## API Changes\n\n...",
                "metadata": {
                    "proposal_id": "user-auth-001",
                    "title": "User Authentication System",
                    "author": "John Doe",
                    "created_at": "2025-11-15T10:00:00Z",
                },
                "files_found": [
                    "proposal.md",
                    "tasks.md",
                    "spec-delta.md",
                    "metadata.json",
                ],
                "validation_errors": [],
                "is_valid": True,
                "parsed_tasks": [],
            }
        }
    )

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        """Validate proposal name."""
        if not v or not v.strip():
            raise ValueError("Proposal name cannot be empty")
        return v.strip()

    def add_validation_error(self, error: str) -> None:
        """
        Add a validation error to the proposal.

        Args:
            error: Error message to add
        """
        self.validation_errors.append(error)
        self.is_valid = False

    def has_required_files(self) -> bool:
        """
        Check if all required files are present.

        Returns:
            True if proposal.md, tasks.md, spec-delta.md, and metadata.json exist
        """
        required = ["proposal.md", "tasks.md", "spec-delta.md", "metadata.json"]
        return all(any(f.endswith(req) for f in self.files_found) for req in required)
