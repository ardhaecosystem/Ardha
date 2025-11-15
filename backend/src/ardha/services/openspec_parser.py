"""
OpenSpec file parser service for reading and validating OpenSpec proposals.

This service handles parsing OpenSpec markdown files from the file system,
extracting content, validating structure, and preparing data for database storage.
"""

import json
import logging
import re
from pathlib import Path
from typing import Dict, List

from ardha.core.exceptions import (
    OpenSpecFileNotFoundError,
    OpenSpecParseError,
    OpenSpecValidationError,
)
from ardha.schemas.openspec.parsed import ParsedMetadata, ParsedProposal, ParsedTask

logger = logging.getLogger(__name__)


class OpenSpecParserService:
    """
    Service for parsing OpenSpec proposals from the file system.

    This service provides methods to:
    - Parse complete proposals from directories
    - Extract tasks from markdown
    - Validate proposal structure
    - List active and archived proposals
    """

    def __init__(self, project_root: Path):
        """
        Initialize OpenSpec parser service.

        Args:
            project_root: Path to project root directory (contains openspec/ directory)
        """
        self.project_root = Path(project_root)
        self.openspec_dir = self.project_root / "openspec"
        self.changes_dir = self.openspec_dir / "changes"
        self.archive_dir = self.openspec_dir / "archive"

        logger.info(f"Initialized OpenSpecParserService with project_root: {self.project_root}")

    def parse_proposal(self, proposal_name: str) -> ParsedProposal:
        """
        Parse a complete OpenSpec proposal from the file system.

        Args:
            proposal_name: Name of the proposal (directory name)

        Returns:
            ParsedProposal with all content and validation results

        Raises:
            OpenSpecFileNotFoundError: If proposal directory or required files missing
            OpenSpecParseError: If file reading or parsing fails
        """
        logger.info(f"Parsing proposal: {proposal_name}")

        # Get proposal directory path
        proposal_path = self.get_proposal_path(proposal_name)

        # Initialize parsed proposal
        parsed = ParsedProposal(
            name=proposal_name,
            directory_path=str(proposal_path),
        )

        # List all files in directory
        try:
            parsed.files_found = [f.name for f in proposal_path.iterdir() if f.is_file()]
            logger.debug(f"Found files: {parsed.files_found}")
        except Exception as e:
            raise OpenSpecParseError(
                f"Failed to list files in {proposal_path}: {str(e)}",
                file_path=str(proposal_path),
            )

        # Parse required files
        required_files = {
            "proposal.md": "proposal_content",
            "tasks.md": "tasks_content",
            "spec-delta.md": "spec_delta_content",
            "metadata.json": "metadata",
        }

        for filename, attr_name in required_files.items():
            file_path = proposal_path / filename
            if not file_path.exists():
                parsed.add_validation_error(f"Missing required file: {filename}")
                continue

            try:
                if filename == "metadata.json":
                    # Parse metadata JSON
                    parsed.metadata = self.parse_metadata(file_path)
                else:
                    # Read markdown content
                    content = self.parse_proposal_file(file_path)
                    setattr(parsed, attr_name, content)
            except Exception as e:
                parsed.add_validation_error(f"Failed to parse {filename}: {str(e)}")
                logger.error(f"Error parsing {filename}: {str(e)}", exc_info=True)

        # Parse optional files
        optional_files = {
            "README.md": "readme_content",
            "risk-assessment.md": "risk_assessment_content",
        }

        for filename, attr_name in optional_files.items():
            file_path = proposal_path / filename
            if file_path.exists():
                try:
                    content = self.parse_proposal_file(file_path)
                    setattr(parsed, attr_name, content)
                except Exception as e:
                    logger.warning(f"Failed to parse optional file {filename}: {str(e)}")

        # Extract tasks from tasks.md if available
        if parsed.tasks_content and parsed.is_valid:
            try:
                parsed.parsed_tasks = self.extract_tasks_from_markdown(parsed.tasks_content)
                logger.info(f"Extracted {len(parsed.parsed_tasks)} tasks")
            except Exception as e:
                parsed.add_validation_error(f"Failed to extract tasks: {str(e)}")
                logger.error(f"Error extracting tasks: {str(e)}", exc_info=True)

        # Validate proposal structure
        validation_errors = self.validate_proposal_structure(parsed)
        for error in validation_errors:
            parsed.add_validation_error(error)

        logger.info(
            f"Parsed proposal '{proposal_name}': "
            f"valid={parsed.is_valid}, errors={len(parsed.validation_errors)}"
        )

        return parsed

    def parse_proposal_file(self, file_path: Path) -> str:
        """
        Read markdown file content from the file system.

        Args:
            file_path: Path to markdown file

        Returns:
            File content as string

        Raises:
            OpenSpecParseError: If file cannot be read
        """
        try:
            content = file_path.read_text(encoding="utf-8")
            logger.debug(f"Read file {file_path}: {len(content)} characters")
            return content
        except UnicodeDecodeError as e:
            raise OpenSpecParseError(
                f"Failed to decode file {file_path} as UTF-8: {str(e)}",
                file_path=str(file_path),
            )
        except Exception as e:
            raise OpenSpecParseError(
                f"Failed to read file {file_path}: {str(e)}",
                file_path=str(file_path),
            )

    def parse_metadata(self, metadata_path: Path) -> ParsedMetadata:
        """
        Parse metadata.json file.

        Args:
            metadata_path: Path to metadata.json file

        Returns:
            ParsedMetadata schema with parsed content

        Raises:
            OpenSpecParseError: If JSON parsing fails
            OpenSpecValidationError: If required fields are missing
        """
        try:
            content = metadata_path.read_text(encoding="utf-8")
            data = json.loads(content)
        except json.JSONDecodeError as e:
            raise OpenSpecParseError(
                f"Invalid JSON in {metadata_path}: {str(e)}",
                file_path=str(metadata_path),
            )
        except Exception as e:
            raise OpenSpecParseError(
                f"Failed to read metadata file {metadata_path}: {str(e)}",
                file_path=str(metadata_path),
            )

        # Validate required fields
        required_fields = ["proposal_id", "title", "author", "created_at"]
        missing_fields = [field for field in required_fields if field not in data]

        if missing_fields:
            raise OpenSpecValidationError(
                f"Missing required fields in metadata.json: {', '.join(missing_fields)}",
                validation_errors=missing_fields,
            )

        # Parse datetime
        try:
            # Store raw JSON for extensions
            data["raw_json"] = data.copy()

            # Create ParsedMetadata (Pydantic will handle datetime parsing)
            metadata = ParsedMetadata(**data)
            logger.debug(f"Parsed metadata: {metadata.proposal_id}")
            return metadata
        except Exception as e:
            raise OpenSpecValidationError(
                f"Failed to validate metadata: {str(e)}",
                validation_errors=[str(e)],
            )

    def extract_tasks_from_markdown(self, tasks_content: str) -> List[ParsedTask]:
        """
        Extract tasks from tasks.md markdown content.

        Parses markdown to extract task blocks with:
        - Identifiers (TAS-001, TASK-001, etc.)
        - Titles and descriptions
        - Phase information
        - Estimated hours
        - Dependencies
        - Acceptance criteria

        Args:
            tasks_content: Content of tasks.md file

        Returns:
            List of ParsedTask objects

        Raises:
            OpenSpecParseError: If parsing fails
        """
        tasks = []

        try:
            # Split content into potential task blocks
            # Look for headers that might indicate tasks (### or ## with identifier)
            task_pattern = re.compile(
                r"^(#{2,3})\s+([A-Z]+-\d+|[A-Z]+\d+|TAS-\d+)[\s:]+(.+?)$",
                re.MULTILINE,
            )

            matches = list(task_pattern.finditer(tasks_content))

            for i, match in enumerate(matches):
                # Extract task identifier and title
                identifier = match.group(2).strip()
                title = match.group(3).strip()

                # Get task content (from this match to next match or end)
                end_pos = (
                    matches[i + 1].start()
                    if i + 1 < len(matches)
                    else len(tasks_content)
                )
                markdown_section = tasks_content[match.start() : end_pos].strip()

                # Parse task block
                task = self._parse_task_block(
                    identifier=identifier,
                    title=title,
                    markdown_section=markdown_section,
                )
                tasks.append(task)

            logger.info(f"Extracted {len(tasks)} tasks from markdown")
            return tasks

        except Exception as e:
            logger.error(f"Failed to extract tasks: {str(e)}", exc_info=True)
            raise OpenSpecParseError(f"Failed to extract tasks from markdown: {str(e)}")

    def validate_proposal_structure(self, parsed: ParsedProposal) -> List[str]:
        """
        Validate proposal structure and content.

        Checks:
        - All required files are present
        - proposal.md has required sections
        - tasks.md has at least one task
        - spec-delta.md is not empty
        - metadata has required fields

        Args:
            parsed: ParsedProposal to validate

        Returns:
            List of validation error messages (empty if valid)
        """
        errors = []

        # Check required files
        if not parsed.has_required_files():
            errors.append("Missing one or more required files")

        # Validate proposal.md content
        if parsed.proposal_content:
            sections = self._extract_markdown_sections(parsed.proposal_content)
            required_sections = ["Summary", "Motivation", "Implementation Plan"]

            for section in required_sections:
                # Case-insensitive check
                if not any(section.lower() in s.lower() for s in sections.keys()):
                    errors.append(f"Missing required section in proposal.md: {section}")

            # Check if proposal has substantial content (>100 chars)
            if len(parsed.proposal_content.strip()) < 100:
                errors.append("proposal.md content is too short (minimum 100 characters)")
        else:
            errors.append("proposal.md is empty")

        # Validate tasks.md content
        if parsed.tasks_content:
            if len(parsed.parsed_tasks) == 0:
                errors.append("tasks.md does not contain any parseable tasks")
            if len(parsed.tasks_content.strip()) < 50:
                errors.append("tasks.md content is too short (minimum 50 characters)")
        else:
            errors.append("tasks.md is empty")

        # Validate spec-delta.md
        if parsed.spec_delta_content:
            if len(parsed.spec_delta_content.strip()) < 20:
                errors.append("spec-delta.md content is too short (minimum 20 characters)")
        else:
            errors.append("spec-delta.md is empty")

        # Validate metadata
        if not parsed.metadata:
            errors.append("metadata.json is missing or invalid")

        logger.debug(f"Validation found {len(errors)} errors")
        return errors

    def list_proposals(self, status: str = "active") -> List[str]:
        """
        List proposal names by status.

        Args:
            status: "active" for changes/ or "archived" for archive/

        Returns:
            List of proposal names (directory names)
        """
        if status == "active":
            target_dir = self.changes_dir
        elif status == "archived":
            target_dir = self.archive_dir
        else:
            logger.warning(f"Invalid status '{status}', defaulting to 'active'")
            target_dir = self.changes_dir

        if not target_dir.exists():
            logger.warning(f"Directory does not exist: {target_dir}")
            return []

        try:
            proposals = [
                d.name for d in target_dir.iterdir() if d.is_dir() and not d.name.startswith(".")
            ]
            logger.info(f"Found {len(proposals)} {status} proposals")
            return sorted(proposals)
        except Exception as e:
            logger.error(f"Failed to list proposals in {target_dir}: {str(e)}")
            return []

    def get_proposal_path(self, proposal_name: str) -> Path:
        """
        Get full path to proposal directory.

        Searches in changes/ first, then archive/.

        Args:
            proposal_name: Name of the proposal (directory name)

        Returns:
            Path to proposal directory

        Raises:
            OpenSpecFileNotFoundError: If proposal directory not found
        """
        # Check in active changes first
        changes_path = self.changes_dir / proposal_name
        if changes_path.exists() and changes_path.is_dir():
            logger.debug(f"Found proposal in changes: {changes_path}")
            return changes_path

        # Check in archive
        archive_path = self.archive_dir / proposal_name
        if archive_path.exists() and archive_path.is_dir():
            logger.debug(f"Found proposal in archive: {archive_path}")
            return archive_path

        # Not found
        raise OpenSpecFileNotFoundError(
            f"Proposal '{proposal_name}' not found in changes/ or archive/",
            file_path=proposal_name,
        )

    # ============= Private Helper Methods =============

    def _extract_markdown_sections(self, content: str) -> Dict[str, str]:
        """
        Parse markdown content into sections based on headers.

        Extracts sections defined by ## and ### headers.

        Args:
            content: Markdown content

        Returns:
            Dictionary mapping section names to section content
        """
        sections = {}
        lines = content.split("\n")

        current_section = None
        current_content: List[str] = []

        for line in lines:
            # Check for header (## or ###)
            header_match = re.match(r"^(#{2,3})\s+(.+)$", line)

            if header_match:
                # Save previous section if any
                if current_section:
                    sections[current_section] = "\n".join(current_content).strip()

                # Start new section
                current_section = header_match.group(2).strip()
                current_content = []
            elif current_section:
                # Add line to current section
                current_content.append(line)

        # Save last section
        if current_section:
            sections[current_section] = "\n".join(current_content).strip()

        logger.debug(f"Extracted {len(sections)} sections from markdown")
        return sections

    def _parse_task_block(
        self,
        identifier: str,
        title: str,
        markdown_section: str,
    ) -> ParsedTask:
        """
        Parse a task block from markdown.

        Extracts:
        - Description (content before bullets/lists)
        - Phase (e.g., "Phase 1", "Week 2")
        - Estimated hours (patterns like "2-4 hours", "1 day")
        - Dependencies (e.g., "Depends on: TAS-001, TAS-002")
        - Acceptance criteria (bullet points)

        Args:
            identifier: Task identifier
            title: Task title
            markdown_section: Full markdown text for this task

        Returns:
            ParsedTask object
        """
        # Initialize task data
        description_lines = []
        phase = None
        estimated_hours = None
        dependencies = []
        acceptance_criteria = []

        lines = markdown_section.split("\n")
        in_acceptance_criteria = False

        for line in lines:
            line_stripped = line.strip()

            # Check for acceptance criteria section FIRST (before skipping headers)
            if re.match(r"^#{2,}\s*Acceptance\s+Criteria", line, re.IGNORECASE):
                in_acceptance_criteria = True
                continue

            # Skip other header lines (### TAS-001: ...)
            if line_stripped.startswith("#"):
                # If we were collecting criteria, new section means stop
                if in_acceptance_criteria:
                    in_acceptance_criteria = False
                continue

            # Collect acceptance criteria bullets
            if in_acceptance_criteria:
                if line_stripped.startswith("-") or line_stripped.startswith("*"):
                    criterion = re.sub(r"^[-*]\s*", "", line_stripped)
                    if criterion:
                        acceptance_criteria.append(criterion)
                continue

            # Check for phase indicators
            phase_match = re.search(
                r"\b(Phase\s+\d+|Week\s+\d+|Sprint\s+\d+)\b",
                line,
                re.IGNORECASE,
            )
            if phase_match and not phase:
                phase = phase_match.group(1)

            # Check for estimated hours
            hours_patterns = [
                r"(\d+)\s*-\s*(\d+)\s*hours?",  # "2-4 hours"
                r"(\d+)\s*hours?",  # "4 hours"
                r"(\d+)\s*days?",  # "1 day" (convert to hours)
                r"(\d+)\s*h\b",  # "4h"
            ]

            for pattern in hours_patterns:
                hours_match = re.search(pattern, line, re.IGNORECASE)
                if hours_match and estimated_hours is None:
                    if "day" in pattern:
                        # Convert days to hours (8 hours per day)
                        estimated_hours = int(hours_match.group(1)) * 8
                    elif len(hours_match.groups()) == 2:
                        # Range: use upper bound
                        estimated_hours = int(hours_match.group(2))
                    else:
                        estimated_hours = int(hours_match.group(1))
                    break

            # Check for dependencies
            dep_match = re.search(
                r"Depends?\s+on:?\s*([A-Z]+-\d+(?:\s*,\s*[A-Z]+-\d+)*)",
                line,
                re.IGNORECASE,
            )
            if dep_match:
                # Extract all task identifiers
                dep_ids = re.findall(r"[A-Z]+-\d+", dep_match.group(1))
                dependencies.extend(dep_ids)

            # Collect description (non-header, non-bullet lines)
            if (
                not in_acceptance_criteria
                and not line_stripped.startswith("#")
                and not line_stripped.startswith("-")
                and not line_stripped.startswith("*")
                and line_stripped
                and not dep_match
                and not phase_match
            ):
                description_lines.append(line_stripped)

        # Build description from collected lines
        description = " ".join(description_lines).strip()

        return ParsedTask(
            identifier=identifier,
            title=title,
            description=description,
            phase=phase,
            estimated_hours=estimated_hours,
            dependencies=dependencies,
            acceptance_criteria=acceptance_criteria,
            markdown_section=markdown_section,
        )

    def _ensure_directory_exists(self, path: Path) -> None:
        """
        Ensure directory exists, create if necessary.

        Args:
            path: Directory path to ensure exists

        Raises:
            OpenSpecParseError: If directory creation fails
        """
        try:
            path.mkdir(parents=True, exist_ok=True)
            logger.debug(f"Ensured directory exists: {path}")
        except PermissionError as e:
            raise OpenSpecParseError(
                f"Permission denied creating directory {path}: {str(e)}",
                file_path=str(path),
            )
        except Exception as e:
            raise OpenSpecParseError(
                f"Failed to create directory {path}: {str(e)}",
                file_path=str(path),
            )
