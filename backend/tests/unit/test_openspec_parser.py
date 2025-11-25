"""
Unit tests for OpenSpec file parser service.

Tests cover:
- Proposal parsing from file system
- Task extraction from markdown
- Metadata JSON parsing
- Validation logic
- Edge cases and error handling
"""

import json
from datetime import datetime
from pathlib import Path

import pytest

from ardha.core.exceptions import (
    OpenSpecFileNotFoundError,
    OpenSpecParseError,
    OpenSpecValidationError,
)
from ardha.schemas.openspec.parsed import ParsedMetadata, ParsedProposal, ParsedTask
from ardha.services.openspec_parser import OpenSpecParserService

# ============= Test Fixtures =============


@pytest.fixture
def temp_openspec_dir(tmp_path):
    """Create temporary OpenSpec directory structure."""
    openspec_dir = tmp_path / "openspec"
    changes_dir = openspec_dir / "changes"
    archive_dir = openspec_dir / "archive"

    changes_dir.mkdir(parents=True)
    archive_dir.mkdir(parents=True)

    return tmp_path


@pytest.fixture
def sample_metadata():
    """Sample metadata.json content."""
    return {
        "proposal_id": "test-proposal-001",
        "title": "Test Proposal",
        "author": "Test Author",
        "created_at": "2025-11-15T10:00:00Z",
        "priority": "high",
        "estimated_effort": "2-3 weeks",
        "tags": ["test", "sample"],
    }


@pytest.fixture
def sample_proposal_md():
    """Sample proposal.md content."""
    return """# Test Proposal

## Summary
This is a test proposal for validating the parser.

## Motivation
We need to test the OpenSpec parser to ensure it works correctly.

## Implementation Plan
1. Create test fixtures
2. Write comprehensive tests
3. Validate all functionality

## Estimated Effort
2-3 weeks of development time.
"""


@pytest.fixture
def sample_tasks_md():
    """Sample tasks.md with multiple tasks."""
    return """# Tasks

## TAS-001: Implement base functionality
Phase 1 - Estimated: 4 hours
Depends on: None

Create the core parser service with file reading capabilities.

### Acceptance Criteria
- Parser can read markdown files
- Parser handles missing files gracefully
- Parser validates file structure

## TAS-002: Add task extraction
Phase 1 - Estimated: 6 hours
Depends on: TAS-001

Extract tasks from tasks.md markdown content.

### Acceptance Criteria
- Extracts task identifiers
- Parses dependencies correctly
- Handles multiple task formats

## TAS-003: Comprehensive validation
Phase 2 - 8 hours
Depends on: TAS-001, TAS-002

Validate proposal structure and content.
"""


@pytest.fixture
def sample_spec_delta_md():
    """Sample spec-delta.md content."""
    return """## API Changes

### New Endpoints
- POST /api/v1/openspec/proposals
- GET /api/v1/openspec/proposals/{id}

### Database Changes
- Add openspec_proposals table
"""


@pytest.fixture
def parser_service(temp_openspec_dir):
    """Create parser service with temporary directory."""
    return OpenSpecParserService(temp_openspec_dir)


def create_valid_proposal(
    changes_dir: Path,
    proposal_name: str,
    metadata: dict,
    proposal_md: str,
    tasks_md: str,
    spec_delta_md: str,
):
    """Helper to create a complete valid proposal directory."""
    proposal_dir = changes_dir / proposal_name
    proposal_dir.mkdir()

    # Write all required files
    (proposal_dir / "proposal.md").write_text(proposal_md, encoding="utf-8")
    (proposal_dir / "tasks.md").write_text(tasks_md, encoding="utf-8")
    (proposal_dir / "spec-delta.md").write_text(spec_delta_md, encoding="utf-8")
    (proposal_dir / "metadata.json").write_text(json.dumps(metadata, indent=2), encoding="utf-8")

    return proposal_dir


# ============= Test Cases =============


def test_parse_valid_proposal_success(
    parser_service,
    temp_openspec_dir,
    sample_metadata,
    sample_proposal_md,
    sample_tasks_md,
    sample_spec_delta_md,
):
    """Test parsing a complete valid proposal."""
    # Create valid proposal
    changes_dir = temp_openspec_dir / "openspec" / "changes"
    create_valid_proposal(
        changes_dir,
        "test-proposal",
        sample_metadata,
        sample_proposal_md,
        sample_tasks_md,
        sample_spec_delta_md,
    )

    # Parse proposal
    result = parser_service.parse_proposal("test-proposal")

    # Assertions
    assert result.name == "test-proposal"
    assert result.is_valid is True
    assert len(result.validation_errors) == 0
    assert result.proposal_content == sample_proposal_md
    assert result.tasks_content == sample_tasks_md
    assert result.spec_delta_content == sample_spec_delta_md
    assert result.metadata is not None
    assert result.metadata.proposal_id == "test-proposal-001"
    assert len(result.parsed_tasks) == 3  # TAS-001, TAS-002, TAS-003
    assert "proposal.md" in result.files_found
    assert "tasks.md" in result.files_found
    assert "spec-delta.md" in result.files_found
    assert "metadata.json" in result.files_found


def test_parse_proposal_with_optional_files(
    parser_service,
    temp_openspec_dir,
    sample_metadata,
    sample_proposal_md,
    sample_tasks_md,
    sample_spec_delta_md,
):
    """Test parsing proposal with optional README and risk assessment."""
    changes_dir = temp_openspec_dir / "openspec" / "changes"
    proposal_dir = create_valid_proposal(
        changes_dir,
        "test-proposal",
        sample_metadata,
        sample_proposal_md,
        sample_tasks_md,
        sample_spec_delta_md,
    )

    # Add optional files
    readme_content = "# Test Proposal\n\nThis is a test README."
    risk_content = "## Risks\n\n- Low risk of failure"

    (proposal_dir / "README.md").write_text(readme_content, encoding="utf-8")
    (proposal_dir / "risk-assessment.md").write_text(risk_content, encoding="utf-8")

    # Parse proposal
    result = parser_service.parse_proposal("test-proposal")

    # Assertions
    assert result.is_valid is True
    assert result.readme_content == readme_content
    assert result.risk_assessment_content == risk_content
    assert "README.md" in result.files_found
    assert "risk-assessment.md" in result.files_found


def test_parse_proposal_missing_required_files(parser_service, temp_openspec_dir, sample_metadata):
    """Test parsing fails gracefully when required files are missing."""
    changes_dir = temp_openspec_dir / "openspec" / "changes"
    proposal_dir = changes_dir / "incomplete-proposal"
    proposal_dir.mkdir()

    # Only create metadata.json (missing proposal.md, tasks.md, spec-delta.md)
    (proposal_dir / "metadata.json").write_text(
        json.dumps(sample_metadata, indent=2), encoding="utf-8"
    )

    # Parse proposal
    result = parser_service.parse_proposal("incomplete-proposal")

    # Assertions
    assert result.is_valid is False
    assert len(result.validation_errors) > 0
    assert any("Missing required file" in error for error in result.validation_errors)
    assert result.proposal_content == ""
    assert result.tasks_content == ""


def test_parse_proposal_directory_not_found(parser_service):
    """Test error when proposal directory doesn't exist."""
    with pytest.raises(OpenSpecFileNotFoundError) as exc_info:
        parser_service.parse_proposal("nonexistent-proposal")

    assert "not found" in str(exc_info.value).lower()
    assert exc_info.value.file_path == "nonexistent-proposal"


def test_extract_tasks_from_markdown_success(parser_service, sample_tasks_md):
    """Test task extraction from valid tasks.md content."""
    tasks = parser_service.extract_tasks_from_markdown(sample_tasks_md)

    # Should extract 3 tasks
    assert len(tasks) == 3

    # Check first task
    task1 = tasks[0]
    assert task1.identifier == "TAS-001"
    assert "base functionality" in task1.title
    assert task1.phase == "Phase 1"
    assert task1.estimated_hours == 4
    assert len(task1.dependencies) == 0
    assert len(task1.acceptance_criteria) == 3

    # Check second task
    task2 = tasks[1]
    assert task2.identifier == "TAS-002"
    assert "task extraction" in task2.title
    assert task2.estimated_hours == 6
    assert "TAS-001" in task2.dependencies

    # Check third task
    task3 = tasks[2]
    assert task3.identifier == "TAS-003"
    assert task3.estimated_hours == 8
    assert len(task3.dependencies) == 2
    assert "TAS-001" in task3.dependencies
    assert "TAS-002" in task3.dependencies


def test_extract_tasks_handles_various_formats(parser_service):
    """Test task extraction handles different task ID formats."""
    markdown = """
### TASK-001: First format
Description here

## TAS-002: Second format
Another description

### T003: Third format
Yet another description
"""

    tasks = parser_service.extract_tasks_from_markdown(markdown)

    assert len(tasks) == 3
    assert tasks[0].identifier == "TASK-001"
    assert tasks[1].identifier == "TAS-002"
    assert tasks[2].identifier == "T003"


def test_parse_metadata_success(parser_service, temp_openspec_dir, sample_metadata):
    """Test metadata.json parsing with all fields."""
    # Create metadata file
    metadata_path = temp_openspec_dir / "metadata.json"
    metadata_path.write_text(json.dumps(sample_metadata, indent=2), encoding="utf-8")

    # Parse metadata
    result = parser_service.parse_metadata(metadata_path)

    # Assertions
    assert result.proposal_id == "test-proposal-001"
    assert result.title == "Test Proposal"
    assert result.author == "Test Author"
    assert isinstance(result.created_at, datetime)
    assert result.priority == "high"
    assert result.estimated_effort == "2-3 weeks"
    assert len(result.tags) == 2
    assert "test" in result.tags


def test_parse_metadata_invalid_json(parser_service, temp_openspec_dir):
    """Test metadata parsing fails on invalid JSON."""
    metadata_path = temp_openspec_dir / "metadata.json"
    metadata_path.write_text("{ invalid json }", encoding="utf-8")

    with pytest.raises(OpenSpecParseError) as exc_info:
        parser_service.parse_metadata(metadata_path)

    assert "Invalid JSON" in str(exc_info.value)
    assert exc_info.value.file_path == str(metadata_path)


def test_parse_metadata_missing_required_fields(parser_service, temp_openspec_dir):
    """Test metadata validation fails when required fields missing."""
    metadata_path = temp_openspec_dir / "metadata.json"
    incomplete_metadata = {"title": "Test"}  # Missing proposal_id, author, created_at

    metadata_path.write_text(json.dumps(incomplete_metadata), encoding="utf-8")

    with pytest.raises(OpenSpecValidationError) as exc_info:
        parser_service.parse_metadata(metadata_path)

    assert "Missing required fields" in str(exc_info.value)
    assert len(exc_info.value.validation_errors) > 0


def test_validate_proposal_structure_complete(
    parser_service, sample_proposal_md, sample_tasks_md, sample_spec_delta_md
):
    """Test validation passes for complete proposal."""
    # Extract tasks first
    tasks = parser_service.extract_tasks_from_markdown(sample_tasks_md)

    parsed = ParsedProposal(
        name="test",
        directory_path="/test",
        proposal_content=sample_proposal_md,
        tasks_content=sample_tasks_md,
        spec_delta_content=sample_spec_delta_md,
        metadata=ParsedMetadata(
            proposal_id="test-001",
            title="Test",
            author="Author",
            created_at=datetime.now(),
            raw_json={},
        ),
        files_found=["proposal.md", "tasks.md", "spec-delta.md", "metadata.json"],
        parsed_tasks=tasks,
    )

    errors = parser_service.validate_proposal_structure(parsed)

    # Should have no errors
    assert len(errors) == 0


def test_validate_proposal_structure_missing_sections(parser_service):
    """Test validation detects missing required sections."""
    # Proposal without required sections
    incomplete_proposal_md = "# Test\n\nJust some text without proper sections."

    parsed = ParsedProposal(
        name="test",
        directory_path="/test",
        proposal_content=incomplete_proposal_md,
        tasks_content="# Tasks\n\n## TAS-001: Test task\nDescription",
        spec_delta_content="## Changes\n\nSome changes",
        files_found=["proposal.md", "tasks.md", "spec-delta.md", "metadata.json"],
    )

    errors = parser_service.validate_proposal_structure(parsed)

    # Should detect missing sections
    assert len(errors) > 0
    assert any("Missing required section" in error for error in errors)


def test_validate_proposal_structure_empty_content(parser_service):
    """Test validation detects empty or too-short content."""
    parsed = ParsedProposal(
        name="test",
        directory_path="/test",
        proposal_content="# Short",  # Too short
        tasks_content="",  # Empty
        spec_delta_content="",  # Empty
        files_found=["proposal.md", "tasks.md", "spec-delta.md", "metadata.json"],
    )

    errors = parser_service.validate_proposal_structure(parsed)

    # Should detect multiple issues
    assert len(errors) >= 3
    assert any("too short" in error for error in errors)
    assert any("empty" in error.lower() for error in errors)


def test_list_proposals_active(parser_service, temp_openspec_dir):
    """Test listing active proposals from changes/."""
    changes_dir = temp_openspec_dir / "openspec" / "changes"

    # Create multiple proposal directories
    (changes_dir / "proposal-1").mkdir()
    (changes_dir / "proposal-2").mkdir()
    (changes_dir / "proposal-3").mkdir()
    (changes_dir / ".hidden").mkdir()  # Should be ignored

    proposals = parser_service.list_proposals(status="active")

    assert len(proposals) == 3
    assert "proposal-1" in proposals
    assert "proposal-2" in proposals
    assert "proposal-3" in proposals
    assert ".hidden" not in proposals
    # Should be sorted
    assert proposals == sorted(proposals)


def test_list_proposals_archived(parser_service, temp_openspec_dir):
    """Test listing archived proposals from archive/."""
    archive_dir = temp_openspec_dir / "openspec" / "archive"

    # Create archived proposal directories
    (archive_dir / "archived-1").mkdir()
    (archive_dir / "archived-2").mkdir()

    proposals = parser_service.list_proposals(status="archived")

    assert len(proposals) == 2
    assert "archived-1" in proposals
    assert "archived-2" in proposals


def test_list_proposals_empty_directory(parser_service):
    """Test listing proposals returns empty list for empty directory."""
    proposals = parser_service.list_proposals(status="active")

    assert isinstance(proposals, list)
    assert len(proposals) == 0


def test_get_proposal_path_in_changes(parser_service, temp_openspec_dir):
    """Test getting proposal path from changes/ directory."""
    changes_dir = temp_openspec_dir / "openspec" / "changes"
    proposal_dir = changes_dir / "test-proposal"
    proposal_dir.mkdir()

    path = parser_service.get_proposal_path("test-proposal")

    assert path == proposal_dir
    assert path.exists()


def test_get_proposal_path_in_archive(parser_service, temp_openspec_dir):
    """Test getting proposal path from archive/ directory."""
    archive_dir = temp_openspec_dir / "openspec" / "archive"
    proposal_dir = archive_dir / "archived-proposal"
    proposal_dir.mkdir()

    path = parser_service.get_proposal_path("archived-proposal")

    assert path == proposal_dir
    assert path.exists()


def test_get_proposal_path_not_found(parser_service):
    """Test error when proposal path not found."""
    with pytest.raises(OpenSpecFileNotFoundError) as exc_info:
        parser_service.get_proposal_path("nonexistent")

    assert "not found" in str(exc_info.value).lower()
    assert exc_info.value.file_path == "nonexistent"


def test_extract_markdown_sections(parser_service, sample_proposal_md):
    """Test markdown section extraction."""
    sections = parser_service._extract_markdown_sections(sample_proposal_md)

    assert "Summary" in sections
    assert "Motivation" in sections
    assert "Implementation Plan" in sections
    assert "Estimated Effort" in sections

    # Check content
    assert "test proposal" in sections["Summary"].lower()
    assert "test the OpenSpec parser" in sections["Motivation"]


def test_parse_task_block_complete(parser_service):
    """Test parsing a complete task block with all fields."""
    markdown_section = """### TAS-001: Implement authentication
Phase 1 - Estimated: 8 hours
Depends on: TAS-000

This task implements the authentication system with JWT tokens.

### Acceptance Criteria
- Users can log in with email/password
- JWT tokens are generated correctly
- Tokens expire after 15 minutes
"""

    task = parser_service._parse_task_block(
        identifier="TAS-001",
        title="Implement authentication",
        markdown_section=markdown_section,
    )

    assert task.identifier == "TAS-001"
    assert task.title == "Implement authentication"
    assert "authentication system" in task.description
    assert task.phase == "Phase 1"
    assert task.estimated_hours == 8
    assert "TAS-000" in task.dependencies
    assert len(task.acceptance_criteria) == 3


def test_parse_task_block_minimal(parser_service):
    """Test parsing task with minimal information."""
    markdown_section = """## TASK-999: Simple task
Just a basic description.
"""

    task = parser_service._parse_task_block(
        identifier="TASK-999",
        title="Simple task",
        markdown_section=markdown_section,
    )

    assert task.identifier == "TASK-999"
    assert task.title == "Simple task"
    assert task.phase is None
    assert task.estimated_hours is None
    assert len(task.dependencies) == 0
    assert len(task.acceptance_criteria) == 0


def test_parse_task_block_various_time_formats(parser_service):
    """Test parsing different time estimate formats."""
    test_cases = [
        ("4 hours", 4),
        ("2-6 hours", 6),  # Uses upper bound
        ("1 day", 8),  # Converts to hours
        ("2 days", 16),
        ("8h", 8),
    ]

    for time_str, expected_hours in test_cases:
        markdown = f"""### TAS-001: Test task
Estimated: {time_str}
Description here.
"""
        task = parser_service._parse_task_block(
            identifier="TAS-001",
            title="Test task",
            markdown_section=markdown,
        )

        assert task.estimated_hours == expected_hours, f"Failed for '{time_str}'"


def test_parse_proposal_file_success(parser_service, temp_openspec_dir):
    """Test reading a markdown file."""
    file_path = temp_openspec_dir / "test.md"
    content = "# Test Content\n\nThis is a test."
    file_path.write_text(content, encoding="utf-8")

    result = parser_service.parse_proposal_file(file_path)

    assert result == content


def test_parse_proposal_file_encoding_error(parser_service, temp_openspec_dir):
    """Test handling of encoding errors."""
    file_path = temp_openspec_dir / "bad-encoding.md"
    # Write non-UTF-8 content
    file_path.write_bytes(b"\xff\xfe Invalid UTF-8")

    with pytest.raises(OpenSpecParseError) as exc_info:
        parser_service.parse_proposal_file(file_path)

    assert "Failed to decode" in str(exc_info.value)
    assert exc_info.value.file_path == str(file_path)


def test_ensure_directory_exists(parser_service, temp_openspec_dir):
    """Test directory creation helper."""
    new_dir = temp_openspec_dir / "nested" / "directory" / "path"

    parser_service._ensure_directory_exists(new_dir)

    assert new_dir.exists()
    assert new_dir.is_dir()


def test_parsed_proposal_add_validation_error():
    """Test adding validation errors to ParsedProposal."""
    parsed = ParsedProposal(name="test", directory_path="/test")

    assert parsed.is_valid is True
    assert len(parsed.validation_errors) == 0

    parsed.add_validation_error("Test error")

    assert parsed.is_valid is False
    assert len(parsed.validation_errors) == 1
    assert "Test error" in parsed.validation_errors


def test_parsed_proposal_has_required_files():
    """Test checking for required files."""
    # Complete set
    parsed = ParsedProposal(
        name="test",
        directory_path="/test",
        files_found=["proposal.md", "tasks.md", "spec-delta.md", "metadata.json"],
    )
    assert parsed.has_required_files() is True

    # Missing one file
    parsed = ParsedProposal(
        name="test",
        directory_path="/test",
        files_found=["proposal.md", "tasks.md", "metadata.json"],
    )
    assert parsed.has_required_files() is False


def test_parsed_task_identifier_validation():
    """Test task identifier validation."""
    # Valid identifiers
    valid_ids = ["TAS-001", "TASK-001", "T001", "ABC-123"]

    for task_id in valid_ids:
        task = ParsedTask(
            identifier=task_id,
            title="Test",
            description="",
            phase=None,
            estimated_hours=None,
            markdown_section="Test",
        )
        assert task.identifier == task_id.upper()

    # Invalid identifier (too short)
    with pytest.raises(ValueError):
        ParsedTask(
            identifier="AB",
            title="Test",
            description="",
            phase=None,
            estimated_hours=None,
            markdown_section="Test",
        )


def test_parsed_metadata_priority_validation():
    """Test metadata priority validation."""
    # Valid priorities
    for priority in ["low", "medium", "high", "critical"]:
        metadata = ParsedMetadata(
            proposal_id="test",
            title="Test",
            author="Author",
            created_at=datetime.now(),
            priority=priority,
            raw_json={},
        )
        assert metadata.priority == priority

    # Invalid priority
    with pytest.raises(ValueError):
        ParsedMetadata(
            proposal_id="test",
            title="Test",
            author="Author",
            created_at=datetime.now(),
            priority="invalid",
            raw_json={},
        )


def test_extract_tasks_empty_content(parser_service):
    """Test extracting tasks from empty content."""
    tasks = parser_service.extract_tasks_from_markdown("")

    assert isinstance(tasks, list)
    assert len(tasks) == 0


def test_parse_proposal_handles_unicode(
    parser_service,
    temp_openspec_dir,
    sample_metadata,
    sample_tasks_md,
    sample_spec_delta_md,
):
    """Test parsing files with unicode characters."""
    changes_dir = temp_openspec_dir / "openspec" / "changes"

    # Proposal with unicode characters
    unicode_proposal = """# Test Proposal 🚀

## Summary
This proposal has unicode: café, 日本語, émojis 🎉

## Motivation
Testing unicode support in parser.

## Implementation Plan
1. Parse unicode correctly
2. Store in database
"""

    create_valid_proposal(
        changes_dir,
        "unicode-test",
        sample_metadata,
        unicode_proposal,
        sample_tasks_md,
        sample_spec_delta_md,
    )

    # Parse proposal
    result = parser_service.parse_proposal("unicode-test")

    assert result.is_valid is True
    assert "🚀" in result.proposal_content
    assert "café" in result.proposal_content
    assert "日本語" in result.proposal_content
