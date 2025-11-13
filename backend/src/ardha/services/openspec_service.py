"""
OpenSpec service for managing proposal generation and file operations.

This service handles the creation, validation, and management of OpenSpec
proposals and their associated files.
"""

import json
import logging
import os
import shutil
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from uuid import UUID, uuid4

from ..core.config import get_settings

logger = logging.getLogger(__name__)


class OpenSpecService:
    """
    Service for managing OpenSpec proposals and file operations.
    
    Handles creation of proposal directories, file generation, validation,
    and archival of OpenSpec proposals.
    """
    
    def __init__(self, base_path: Optional[str] = None):
        """
        Initialize OpenSpec service.
        
        Args:
            base_path: Base path for OpenSpec directory (optional)
        """
        self.settings = get_settings()
        # Use current working directory as base if not provided
        project_root = Path.cwd().parent if base_path is None else Path(base_path)
        self.base_path = project_root / "openspec"
        self.changes_path = self.base_path / "changes"
        self.templates_path = self.base_path / "templates"
        self.logger = logger.getChild("OpenSpecService")
        
        # Ensure directories exist
        self._ensure_directories()
    
    def _ensure_directories(self) -> None:
        """Ensure OpenSpec directories exist."""
        try:
            self.base_path.mkdir(parents=True, exist_ok=True)
            self.changes_path.mkdir(parents=True, exist_ok=True)
            self.templates_path.mkdir(parents=True, exist_ok=True)
            self.logger.info("OpenSpec directories ensured")
        except Exception as e:
            self.logger.error(f"Failed to create OpenSpec directories: {e}")
            raise
    
    def create_proposal_directory(self, proposal_id: str) -> Path:
        """
        Create a new proposal directory.
        
        Args:
            proposal_id: Unique proposal identifier
            
        Returns:
            Path to created proposal directory
            
        Raises:
            OSError: If directory creation fails
        """
        try:
            proposal_path = self.changes_path / proposal_id
            proposal_path.mkdir(parents=True, exist_ok=True)
            self.logger.info(f"Created proposal directory: {proposal_path}")
            return proposal_path
        except Exception as e:
            self.logger.error(f"Failed to create proposal directory {proposal_id}: {e}")
            raise
    
    def generate_openspec_files(
        self,
        proposal_data: Dict[str, Any],
        proposal_id: str,
        change_directory_path: str
    ) -> Dict[str, str]:
        """
        Generate all OpenSpec files for a proposal.
        
        Args:
            proposal_data: Complete proposal data from workflow
            proposal_id: Unique proposal identifier
            change_directory_path: Path for change directory
            
        Returns:
            Dictionary mapping filenames to their file paths
            
        Raises:
            ValueError: If proposal data is invalid
            OSError: If file creation fails
        """
        try:
            # Create proposal directory
            proposal_path = self.create_proposal_directory(proposal_id)
            
            # Extract files from proposal data
            files = proposal_data.get("files", {})
            if not files:
                raise ValueError("No files found in proposal data")
            
            generated_files = {}
            
            # Generate each file
            for filename, content in files.items():
                file_path = proposal_path / filename
                
                # Validate file content
                self._validate_file_content(filename, content, proposal_data)
                
                # Write file
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(content)
                
                generated_files[filename] = str(file_path)
                self.logger.info(f"Generated OpenSpec file: {filename}")
            
            # Generate metadata file
            metadata_path = self._generate_metadata_file(
                proposal_data, proposal_id, proposal_path
            )
            generated_files["metadata.json"] = str(metadata_path)
            
            # Generate summary file
            summary_path = self._generate_summary_file(
                proposal_data, proposal_id, proposal_path
            )
            generated_files["summary.md"] = str(summary_path)
            
            self.logger.info(f"Generated {len(generated_files)} OpenSpec files for proposal {proposal_id}")
            return generated_files
            
        except Exception as e:
            self.logger.error(f"Failed to generate OpenSpec files for proposal {proposal_id}: {e}")
            raise
    
    def _validate_file_content(self, filename: str, content: str, proposal_data: Dict[str, Any]) -> None:
        """
        Validate OpenSpec file content against requirements.
        
        Args:
            filename: Name of the file
            content: File content to validate
            proposal_data: Complete proposal data for context
            
        Raises:
            ValueError: If content doesn't meet requirements
        """
        if not content or not content.strip():
            raise ValueError(f"File {filename} has empty content")
        
        # File-specific validations
        if filename == "proposal.md":
            self._validate_proposal_file(content, proposal_data)
        elif filename == "tasks.md":
            self._validate_tasks_file(content, proposal_data)
        elif filename == "spec-delta.md":
            self._validate_spec_delta_file(content, proposal_data)
        elif filename == "README.md":
            self._validate_readme_file(content, proposal_data)
        elif filename == "risk-assessment.md":
            self._validate_risk_assessment_file(content, proposal_data)
    
    def _validate_proposal_file(self, content: str, proposal_data: Dict[str, Any]) -> None:
        """Validate proposal.md file content."""
        required_sections = ["# ", "## Summary", "## Motivation", "## Implementation Plan", "## Estimated Effort"]
        
        for section in required_sections:
            if section not in content:
                raise ValueError(f"proposal.md missing required section: {section}")
        
        # Check if proposal data matches content
        proposal = proposal_data.get("proposal", {})
        if proposal.get("title") and proposal["title"] not in content:
            raise ValueError("proposal.md title doesn't match proposal data")
    
    def _validate_tasks_file(self, content: str, proposal_data: Dict[str, Any]) -> None:
        """Validate tasks.md file content."""
        required_sections = ["# Task Breakdown", "## Phase"]
        
        for section in required_sections:
            if section not in content:
                raise ValueError(f"tasks.md missing required section: {section}")
        
        # Check for task list items
        if "- [ ]" not in content:
            raise ValueError("tasks.md missing task list items")
    
    def _validate_spec_delta_file(self, content: str, proposal_data: Dict[str, Any]) -> None:
        """Validate spec-delta.md file content."""
        required_sections = ["# Specification Updates", "## New Components", "## Modified Components"]
        
        for section in required_sections:
            if section not in content:
                raise ValueError(f"spec-delta.md missing required section: {section}")
    
    def _validate_readme_file(self, content: str, proposal_data: Dict[str, Any]) -> None:
        """Validate README.md file content."""
        required_sections = ["# ", "## Setup", "## Implementation"]
        
        for section in required_sections:
            if section not in content:
                raise ValueError(f"README.md missing required section: {section}")
    
    def _validate_risk_assessment_file(self, content: str, proposal_data: Dict[str, Any]) -> None:
        """Validate risk-assessment.md file content."""
        required_sections = ["# Risk Assessment", "## Security Risks", "## Mitigation Strategies"]
        
        for section in required_sections:
            if section not in content:
                raise ValueError(f"risk-assessment.md missing required section: {section}")
    
    def _generate_metadata_file(self, proposal_data: Dict[str, Any], proposal_id: str, proposal_path: Path) -> Path:
        """
        Generate metadata.json file for the proposal.
        
        Args:
            proposal_data: Complete proposal data
            proposal_id: Proposal identifier
            proposal_path: Path to proposal directory
            
        Returns:
            Path to generated metadata file
        """
        metadata = {
            "proposal_id": proposal_id,
            "generated_at": proposal_data.get("metadata", {}).get("generated_at"),
            "workflow_id": proposal_data.get("metadata", {}).get("workflow_id"),
            "title": proposal_data.get("proposal", {}).get("title"),
            "description": proposal_data.get("proposal", {}).get("description"),
            "objectives": proposal_data.get("proposal", {}).get("objectives", []),
            "scope": proposal_data.get("proposal", {}).get("scope", {}),
            "success_criteria": proposal_data.get("proposal", {}).get("success_criteria", []),
            "total_tasks": proposal_data.get("metadata", {}).get("total_tasks"),
            "estimated_effort": proposal_data.get("metadata", {}).get("estimated_effort"),
            "quality_score": proposal_data.get("metadata", {}).get("quality_score"),
            "files_generated": list(proposal_data.get("files", {}).keys()),
            "change_directory_path": str(proposal_path),
        }
        
        metadata_path = proposal_path / "metadata.json"
        with open(metadata_path, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, indent=2, ensure_ascii=False)
        
        return metadata_path
    
    def _generate_summary_file(self, proposal_data: Dict[str, Any], proposal_id: str, proposal_path: Path) -> Path:
        """
        Generate summary.md file for the proposal.
        
        Args:
            proposal_data: Complete proposal data
            proposal_id: Proposal identifier
            proposal_path: Path to proposal directory
            
        Returns:
            Path to generated summary file
        """
        proposal = proposal_data.get("proposal", {})
        metadata = proposal_data.get("metadata", {})
        
        summary_content = f"""# {proposal.get('title', 'Untitled Proposal')}

## Summary

{proposal.get('description', 'No description available')}

## Quick Facts

- **Proposal ID**: {proposal_id}
- **Generated**: {metadata.get('generated_at', 'Unknown')}
- **Total Tasks**: {metadata.get('total_tasks', 'Unknown')}
- **Estimated Effort**: {metadata.get('estimated_effort', 'Unknown')}
- **Quality Score**: {metadata.get('quality_score', 'Unknown')}

## Objectives

"""
        
        for i, objective in enumerate(proposal.get("objectives", []), 1):
            summary_content += f"{i}. {objective}\n"
        
        summary_content += f"""
## Success Criteria

"""
        
        for i, criterion in enumerate(proposal.get("success_criteria", []), 1):
            summary_content += f"{i}. {criterion}\n"
        
        summary_content += f"""
## Files Generated

"""
        
        for filename in proposal_data.get("files", {}):
            summary_content += f"- [{filename}]({filename})\n"
        
        summary_content += f"""
## Next Steps

1. Review all generated files
2. Validate task breakdown and dependencies
3. Approve or modify the proposal
4. Begin implementation

---

*Generated by Ardha Task Generation Workflow*
"""
        
        summary_path = proposal_path / "summary.md"
        with open(summary_path, 'w', encoding='utf-8') as f:
            f.write(summary_content)
        
        return summary_path
    
    def get_proposal_files(self, proposal_id: str) -> Dict[str, str]:
        """
        Get all files for a proposal.
        
        Args:
            proposal_id: Proposal identifier
            
        Returns:
            Dictionary mapping filenames to their content
            
        Raises:
            FileNotFoundError: If proposal directory doesn't exist
        """
        proposal_path = self.changes_path / proposal_id
        
        if not proposal_path.exists():
            raise FileNotFoundError(f"Proposal directory not found: {proposal_id}")
        
        files = {}
        
        for file_path in proposal_path.rglob("*"):
            if file_path.is_file():
                relative_path = file_path.relative_to(proposal_path)
                with open(file_path, 'r', encoding='utf-8') as f:
                    files[str(relative_path)] = f.read()
        
        return files
    
    def archive_proposal(self, proposal_id: str, reason: str = "completed") -> bool:
        """
        Archive a completed proposal.
        
        Args:
            proposal_id: Proposal identifier
            reason: Reason for archiving
            
        Returns:
            True if archived successfully
        """
        try:
            proposal_path = self.changes_path / proposal_id
            archive_path = self.base_path / "archive" / proposal_id
            
            if not proposal_path.exists():
                self.logger.warning(f"Proposal directory not found for archiving: {proposal_id}")
                return False
            
            # Create archive directory
            archive_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Move proposal to archive
            shutil.move(str(proposal_path), str(archive_path))
            
            # Create archive metadata
            archive_metadata = {
                "proposal_id": proposal_id,
                "archived_at": json.dumps({"timestamp": "now"}),  # Would use real timestamp
                "reason": reason,
                "original_path": str(proposal_path),
            }
            
            with open(archive_path / "archive_metadata.json", 'w') as f:
                json.dump(archive_metadata, f, indent=2)
            
            self.logger.info(f"Archived proposal: {proposal_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to archive proposal {proposal_id}: {e}")
            return False
    
    def list_proposals(self, include_archived: bool = False) -> List[Dict[str, Any]]:
        """
        List all proposals.
        
        Args:
            include_archived: Whether to include archived proposals
            
        Returns:
            List of proposal information
        """
        proposals = []
        
        # List active proposals
        if self.changes_path.exists():
            for proposal_dir in self.changes_path.iterdir():
                if proposal_dir.is_dir():
                    proposals.append(self._get_proposal_info(proposal_dir.name, proposal_dir, "active"))
        
        # List archived proposals
        if include_archived:
            archive_path = self.base_path / "archive"
            if archive_path.exists():
                for proposal_dir in archive_path.iterdir():
                    if proposal_dir.is_dir():
                        proposals.append(self._get_proposal_info(proposal_dir.name, proposal_dir, "archived"))
        
        return proposals
    
    def _get_proposal_info(self, proposal_id: str, proposal_path: Path, status: str) -> Dict[str, Any]:
        """Get proposal information from directory."""
        info = {
            "proposal_id": proposal_id,
            "status": status,
            "path": str(proposal_path),
        }
        
        # Check if this is an archived proposal by looking for archive metadata
        archive_metadata_path = proposal_path / "archive_metadata.json"
        if archive_metadata_path.exists():
            info["status"] = "archived"
            try:
                with open(archive_metadata_path, 'r') as f:
                    archive_metadata = json.load(f)
                    info["archived_at"] = archive_metadata.get("archived_at")
                    info["archive_reason"] = archive_metadata.get("reason")
            except Exception as e:
                self.logger.warning(f"Failed to read archive metadata for {proposal_id}: {e}")
        else:
            # Try to read regular metadata
            metadata_path = proposal_path / "metadata.json"
            if metadata_path.exists():
                try:
                    with open(metadata_path, 'r') as f:
                        metadata = json.load(f)
                    info.update(metadata)
                except Exception as e:
                    self.logger.warning(f"Failed to read metadata for {proposal_id}: {e}")
        
        return info


# Global service instance
_openspec_service: Optional[OpenSpecService] = None


def get_openspec_service() -> OpenSpecService:
    """
    Get cached OpenSpec service instance.
    
    Returns:
        OpenSpecService instance
    """
    global _openspec_service
    if _openspec_service is None:
        _openspec_service = OpenSpecService()
    return _openspec_service