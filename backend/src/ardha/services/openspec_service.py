"""
OpenSpec service for business logic.

This module orchestrates OpenSpec file parsing and database operations,
providing business logic for proposal lifecycle management.
"""

import json
import logging
import shutil
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import UUID

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from ardha.core.exceptions import (
    OpenSpecFileNotFoundError,
    OpenSpecParseError,
    OpenSpecValidationError,
)
from ardha.models.openspec import OpenSpecProposal
from ardha.models.task import Task
from ardha.repositories.openspec import OpenSpecRepository
from ardha.services.openspec_parser import OpenSpecParserService
from ardha.services.project_service import ProjectService
from ardha.services.task_service import TaskService

logger = logging.getLogger(__name__)


# ============= Custom Exceptions =============


class OpenSpecProposalNotFoundError(Exception):
    """Raised when an OpenSpec proposal is not found."""

    pass


class OpenSpecProposalExistsError(Exception):
    """Raised when a proposal with the same name already exists."""

    pass


class InsufficientOpenSpecPermissionsError(Exception):
    """Raised when user lacks permissions for OpenSpec operation."""

    pass


class ProposalNotEditableError(Exception):
    """Raised when attempting to edit a non-editable proposal."""

    pass


class ProposalNotApprovableError(Exception):
    """Raised when attempting to approve a proposal that can't be approved."""

    pass


class TaskSyncError(Exception):
    """Raised when task synchronization fails."""

    pass


class OpenSpecService:
    """
    Service layer for OpenSpec business logic.

    Orchestrates:
    - File system parsing via OpenSpecParserService
    - Database operations via OpenSpecRepository
    - Task synchronization via TaskService
    - Permission checks via ProjectService
    - Proposal lifecycle management
    """

    def __init__(
        self,
        openspec_repo: OpenSpecRepository,
        parser: OpenSpecParserService,
        task_service: TaskService,
        project_service: ProjectService,
        db: AsyncSession,
    ):
        """
        Initialize OpenSpec service.

        Args:
            openspec_repo: Repository for database operations
            parser: Parser for file system operations
            task_service: Service for task operations
            project_service: Service for project operations
            db: Async database session
        """
        self.repo = openspec_repo
        self.parser = parser
        self.task_service = task_service
        self.project_service = project_service
        self.db = db

    # ============= Core Methods =============

    async def create_from_filesystem(
        self,
        project_id: UUID,
        proposal_name: str,
        user_id: UUID,
    ) -> OpenSpecProposal:
        """
        Create proposal from filesystem OpenSpec directory.

        Args:
            project_id: Project UUID
            proposal_name: Name of proposal (directory name)
            user_id: User creating the proposal

        Returns:
            Created OpenSpecProposal

        Raises:
            InsufficientOpenSpecPermissionsError: If user lacks permissions
            OpenSpecProposalExistsError: If proposal name already exists
            OpenSpecFileNotFoundError: If proposal directory not found
            OpenSpecParseError: If parsing fails
            OpenSpecValidationError: If validation fails
        """
        # Verify user has project member access
        await self._verify_project_access(project_id, user_id, required_role="member")

        logger.info(f"Creating proposal '{proposal_name}' for project {project_id}")

        # Check if proposal already exists
        existing = await self.repo.get_by_name(project_id, proposal_name)
        if existing:
            raise OpenSpecProposalExistsError(
                f"Proposal '{proposal_name}' already exists in this project"
            )

        # Parse proposal from filesystem
        try:
            parsed = self.parser.parse_proposal(proposal_name)
        except OpenSpecFileNotFoundError as e:
            logger.error(f"Proposal '{proposal_name}' not found: {e}")
            raise
        except OpenSpecParseError as e:
            logger.error(f"Failed to parse proposal '{proposal_name}': {e}")
            raise

        # Validate parsed proposal
        if not parsed.is_valid:
            raise OpenSpecValidationError(
                f"Proposal validation failed: {', '.join(parsed.validation_errors)}",
                validation_errors=parsed.validation_errors,
            )

        # Create database record
        proposal = OpenSpecProposal(
            project_id=project_id,
            name=parsed.name,
            directory_path=parsed.directory_path,
            status="pending",
            created_by_user_id=user_id,
            proposal_content=parsed.proposal_content,
            tasks_content=parsed.tasks_content,
            spec_delta_content=parsed.spec_delta_content,
            metadata_json=parsed.metadata.model_dump() if parsed.metadata else None,
            task_sync_status="not_synced",
            completion_percentage=0,
        )

        try:
            proposal = await self.repo.create(proposal)
            await self.db.flush()
            await self.db.refresh(proposal)

            logger.info(f"Created proposal '{proposal.name}' (id={proposal.id}) from filesystem")
            return proposal

        except IntegrityError as e:
            logger.error(f"Integrity error creating proposal: {e}")
            raise OpenSpecProposalExistsError(
                f"Proposal '{proposal_name}' already exists in this project"
            )

    async def get_proposal(
        self,
        proposal_id: UUID,
        user_id: UUID,
    ) -> OpenSpecProposal:
        """
        Get proposal by ID with permission check.

        Args:
            proposal_id: Proposal UUID
            user_id: User requesting proposal

        Returns:
            OpenSpecProposal

        Raises:
            OpenSpecProposalNotFoundError: If proposal not found
            InsufficientOpenSpecPermissionsError: If user lacks permissions
        """
        proposal = await self.repo.get_by_id(proposal_id)
        if not proposal:
            raise OpenSpecProposalNotFoundError(f"Proposal {proposal_id} not found")

        # Verify user has project viewer access
        await self._verify_project_access(proposal.project_id, user_id, required_role="viewer")

        return proposal

    async def list_proposals(
        self,
        project_id: UUID,
        user_id: UUID,
        status: str | None = None,
        skip: int = 0,
        limit: int = 100,
    ) -> tuple[list[OpenSpecProposal], int]:
        """
        List proposals for a project with permission check.

        Args:
            project_id: Project UUID
            user_id: User requesting proposals
            status: Optional status filter
            skip: Pagination offset
            limit: Page size

        Returns:
            Tuple of (proposals list, total count)

        Raises:
            InsufficientOpenSpecPermissionsError: If user lacks permissions
        """
        # Verify user has project viewer access
        await self._verify_project_access(project_id, user_id, required_role="viewer")

        # Get proposals
        proposals = await self.repo.list_by_project(
            project_id=project_id,
            status=status,
            skip=skip,
            limit=limit,
        )

        # Get total count
        total = await self.repo.count_by_project(project_id, status=status)

        logger.debug(f"Listed {len(proposals)} proposals for project {project_id}")
        return proposals, total

    async def update_proposal(
        self,
        proposal_id: UUID,
        update_data: dict[str, Any],
        user_id: UUID,
    ) -> OpenSpecProposal:
        """
        Update proposal content.

        Args:
            proposal_id: Proposal UUID
            update_data: Fields to update
            user_id: User updating proposal

        Returns:
            Updated OpenSpecProposal

        Raises:
            OpenSpecProposalNotFoundError: If proposal not found
            ProposalNotEditableError: If proposal status is not pending/rejected
            InsufficientOpenSpecPermissionsError: If user lacks permissions
        """
        proposal = await self.repo.get_by_id(proposal_id)
        if not proposal:
            raise OpenSpecProposalNotFoundError(f"Proposal {proposal_id} not found")

        # Verify user has project member access
        await self._verify_project_access(proposal.project_id, user_id, required_role="member")

        # Verify proposal is editable
        if not proposal.is_editable:
            raise ProposalNotEditableError(
                f"Proposal with status '{proposal.status}' cannot be edited. "
                f"Only pending or rejected proposals can be updated."
            )

        # Update proposal content
        proposal = await self.repo.update_content(
            proposal_id=proposal_id,
            proposal_content=update_data.get("proposal_content"),
            tasks_content=update_data.get("tasks_content"),
            spec_delta_content=update_data.get("spec_delta_content"),
            metadata_json=update_data.get("metadata_json"),
        )

        if not proposal:
            raise OpenSpecProposalNotFoundError(f"Proposal {proposal_id} not found after update")

        await self.db.flush()
        await self.db.refresh(proposal)

        logger.info(f"Updated proposal '{proposal.name}' (id={proposal_id})")
        return proposal

    async def approve_proposal(
        self,
        proposal_id: UUID,
        user_id: UUID,
    ) -> OpenSpecProposal:
        """
        Approve a proposal.

        Args:
            proposal_id: Proposal UUID
            user_id: User approving proposal

        Returns:
            Approved OpenSpecProposal

        Raises:
            OpenSpecProposalNotFoundError: If proposal not found
            ProposalNotApprovableError: If proposal status is not pending
            InsufficientOpenSpecPermissionsError: If user lacks admin permissions
        """
        proposal = await self.repo.get_by_id(proposal_id)
        if not proposal:
            raise OpenSpecProposalNotFoundError(f"Proposal {proposal_id} not found")

        # Verify user has project admin access
        await self._verify_project_access(proposal.project_id, user_id, required_role="admin")

        # Verify proposal can be approved
        if not proposal.can_approve:
            raise ProposalNotApprovableError(
                f"Proposal with status '{proposal.status}' cannot be approved. "
                f"Only pending proposals can be approved."
            )

        # Update status to approved
        proposal = await self.repo.update_status(
            proposal_id=proposal_id,
            new_status="approved",
            user_id=user_id,
        )

        if not proposal:
            raise OpenSpecProposalNotFoundError(f"Proposal {proposal_id} not found after approval")

        await self.db.flush()
        await self.db.refresh(proposal)

        logger.info(f"Approved proposal '{proposal.name}' (id={proposal_id}) by user {user_id}")
        return proposal

    async def reject_proposal(
        self,
        proposal_id: UUID,
        user_id: UUID,
        reason: str,
    ) -> OpenSpecProposal:
        """
        Reject a proposal.

        Args:
            proposal_id: Proposal UUID
            user_id: User rejecting proposal
            reason: Rejection reason

        Returns:
            Rejected OpenSpecProposal

        Raises:
            OpenSpecProposalNotFoundError: If proposal not found
            InsufficientOpenSpecPermissionsError: If user lacks admin permissions
        """
        proposal = await self.repo.get_by_id(proposal_id)
        if not proposal:
            raise OpenSpecProposalNotFoundError(f"Proposal {proposal_id} not found")

        # Verify user has project admin access
        await self._verify_project_access(proposal.project_id, user_id, required_role="admin")

        # Update status to rejected
        proposal = await self.repo.update_status(
            proposal_id=proposal_id,
            new_status="rejected",
        )

        if not proposal:
            raise OpenSpecProposalNotFoundError(f"Proposal {proposal_id} not found after rejection")

        # Store rejection reason in metadata
        metadata = proposal.metadata_json or {}
        metadata["rejection_reason"] = reason
        metadata["rejected_by_user_id"] = str(user_id)
        metadata["rejected_at"] = datetime.now(UTC).isoformat()

        updated_proposal = await self.repo.update(proposal_id, {"metadata_json": metadata})

        if not updated_proposal:
            raise OpenSpecProposalNotFoundError(
                f"Proposal {proposal_id} not found after updating metadata"
            )

        await self.db.flush()
        await self.db.refresh(updated_proposal)

        logger.info(
            f"Rejected proposal '{updated_proposal.name}' (id={proposal_id}) by user {user_id}: {reason}"
        )
        return updated_proposal

    async def sync_tasks_to_database(
        self,
        proposal_id: UUID,
        user_id: UUID,
    ) -> list[Task]:
        """
        Sync tasks from proposal to database.

        Args:
            proposal_id: Proposal UUID
            user_id: User initiating sync

        Returns:
            List of created Task objects

        Raises:
            OpenSpecProposalNotFoundError: If proposal not found
            TaskSyncError: If proposal not approved or sync fails
            InsufficientOpenSpecPermissionsError: If user lacks permissions
        """
        proposal = await self.repo.get_by_id(proposal_id)
        if not proposal:
            raise OpenSpecProposalNotFoundError(f"Proposal {proposal_id} not found")

        # Verify user has project member access
        await self._verify_project_access(proposal.project_id, user_id, required_role="member")

        # Verify proposal is approved
        if proposal.status != "approved":
            raise TaskSyncError(
                f"Cannot sync tasks for proposal with status '{proposal.status}'. "
                f"Only approved proposals can be synced."
            )

        # Update sync status to syncing
        await self.repo.update_sync_status(proposal_id, "syncing")
        await self.db.flush()

        created_tasks = []

        try:
            # Parse tasks from tasks_content
            if not proposal.tasks_content:
                raise TaskSyncError("Proposal has no tasks content to sync")

            parsed_tasks = self.parser.extract_tasks_from_markdown(proposal.tasks_content)

            if not parsed_tasks:
                raise TaskSyncError("No parseable tasks found in tasks.md")

            logger.info(f"Parsed {len(parsed_tasks)} tasks from proposal '{proposal.name}'")

            # Create tasks in database
            for parsed_task in parsed_tasks:
                # Prepare task data
                task_data = {
                    "title": parsed_task.title,
                    "description": parsed_task.description,
                    "status": "todo",
                    "phase": parsed_task.phase,
                    "estimate_hours": parsed_task.estimated_hours,
                    "openspec_change_path": proposal.directory_path,
                    "ai_generated": True,
                    "ai_confidence": 0.85,  # Default confidence for OpenSpec tasks
                    "ai_reasoning": f"Generated from OpenSpec proposal: {proposal.name}",
                }

                # Create task via task service
                task = await self.task_service.create_task(
                    project_id=proposal.project_id,
                    task_data=task_data,
                    created_by_id=user_id,
                )

                # Link task to proposal
                await self.task_service.link_openspec_proposal(
                    task_id=task.id,
                    proposal_id=proposal_id,
                )

                created_tasks.append(task)

                logger.info(
                    f"Created task {task.identifier} from parsed task {parsed_task.identifier}"
                )

            # Handle task dependencies (second pass after all tasks created)
            # Map parsed identifiers to created task UUIDs
            identifier_to_task = {task.identifier: task for task in created_tasks}

            for i, parsed_task in enumerate(parsed_tasks):
                if parsed_task.dependencies:
                    task = created_tasks[i]

                    for dep_identifier in parsed_task.dependencies:
                        # Find matching task by identifier pattern
                        # Note: OpenSpec identifiers may not match generated identifiers
                        # For MVP, we'll skip dependencies that can't be resolved
                        logger.warning(
                            f"Task dependency resolution not fully implemented: "
                            f"{task.identifier} depends on {dep_identifier}"
                        )

            # Update sync status to synced
            await self.repo.update_sync_status(
                proposal_id=proposal_id,
                sync_status="synced",
            )

            await self.db.flush()

            logger.info(
                f"Successfully synced {len(created_tasks)} tasks for proposal '{proposal.name}'"
            )
            return created_tasks

        except Exception as e:
            # Update sync status to failed
            await self.repo.update_sync_status(
                proposal_id=proposal_id,
                sync_status="sync_failed",
                error_message=str(e),
            )
            await self.db.flush()

            logger.error(f"Failed to sync tasks for proposal {proposal_id}: {e}", exc_info=True)
            raise TaskSyncError(f"Task synchronization failed: {str(e)}")

    async def refresh_from_filesystem(
        self,
        proposal_id: UUID,
        user_id: UUID,
    ) -> OpenSpecProposal:
        """
        Refresh proposal content from filesystem.

        Args:
            proposal_id: Proposal UUID
            user_id: User initiating refresh

        Returns:
            Updated OpenSpecProposal

        Raises:
            OpenSpecProposalNotFoundError: If proposal not found
            OpenSpecParseError: If parsing fails
            InsufficientOpenSpecPermissionsError: If user lacks permissions
        """
        proposal = await self.repo.get_by_id(proposal_id)
        if not proposal:
            raise OpenSpecProposalNotFoundError(f"Proposal {proposal_id} not found")

        # Verify user has project member access
        await self._verify_project_access(proposal.project_id, user_id, required_role="member")

        logger.info(f"Refreshing proposal '{proposal.name}' from filesystem")

        # Re-parse from filesystem
        try:
            parsed = self.parser.parse_proposal(proposal.name)
        except OpenSpecFileNotFoundError as e:
            logger.error(f"Proposal '{proposal.name}' not found on filesystem: {e}")
            raise OpenSpecParseError(f"Proposal directory not found during refresh: {e}")

        # Validate parsed proposal
        if not parsed.is_valid:
            logger.warning(
                f"Refreshed proposal '{proposal.name}' has validation errors: "
                f"{parsed.validation_errors}"
            )

        # Update content in database
        proposal = await self.repo.update_content(
            proposal_id=proposal_id,
            proposal_content=parsed.proposal_content,
            tasks_content=parsed.tasks_content,
            spec_delta_content=parsed.spec_delta_content,
            metadata_json=parsed.metadata.model_dump() if parsed.metadata else None,
        )

        if not proposal:
            raise OpenSpecProposalNotFoundError(f"Proposal {proposal_id} not found after refresh")

        await self.db.flush()
        await self.db.refresh(proposal)

        logger.info(f"Refreshed proposal '{proposal.name}' from filesystem")
        return proposal

    async def archive_proposal(
        self,
        proposal_id: UUID,
        user_id: UUID,
    ) -> OpenSpecProposal:
        """
        Archive a completed proposal.

        Moves filesystem directory to archive/ and updates database status.

        Args:
            proposal_id: Proposal UUID
            user_id: User archiving proposal

        Returns:
            Archived OpenSpecProposal

        Raises:
            OpenSpecProposalNotFoundError: If proposal not found
            InsufficientOpenSpecPermissionsError: If user lacks admin permissions
        """
        proposal = await self.repo.get_by_id(proposal_id)
        if not proposal:
            raise OpenSpecProposalNotFoundError(f"Proposal {proposal_id} not found")

        # Verify user has project admin access
        await self._verify_project_access(proposal.project_id, user_id, required_role="admin")

        logger.info(f"Archiving proposal '{proposal.name}'")

        # Update database status
        proposal = await self.repo.update_status(
            proposal_id=proposal_id,
            new_status="archived",
        )

        if not proposal:
            raise OpenSpecProposalNotFoundError(f"Proposal {proposal_id} not found after archive")

        # Move filesystem directory to archive
        try:
            source_path = Path(proposal.directory_path)
            archive_dir = self.parser.archive_dir

            # Ensure archive directory exists
            archive_dir.mkdir(parents=True, exist_ok=True)

            # Generate unique archive path (add timestamp if name collision)
            archive_path = archive_dir / proposal.name

            if archive_path.exists():
                timestamp = int(datetime.now(UTC).timestamp())
                archive_path = archive_dir / f"{proposal.name}-{timestamp}"

            # Move directory
            if source_path.exists():
                shutil.move(str(source_path), str(archive_path))

                # Update directory path in database
                await self.repo.update(
                    proposal_id=proposal_id,
                    update_data={"directory_path": str(archive_path)},
                )

                # Create archive metadata
                archive_metadata = {
                    "original_path": str(source_path),
                    "archived_at": datetime.now(UTC).isoformat(),
                    "archived_by_user_id": str(user_id),
                }

                metadata_file = archive_path / "archive_metadata.json"
                metadata_file.write_text(
                    json.dumps(archive_metadata, indent=2),
                    encoding="utf-8",
                )

                logger.info(f"Moved proposal directory to archive: {archive_path}")
            else:
                logger.warning(f"Proposal directory not found for archival: {source_path}")

        except Exception as e:
            logger.error(f"Failed to move proposal directory to archive: {e}", exc_info=True)
            # Continue - database status is updated even if file move fails

        await self.db.flush()
        await self.db.refresh(proposal)

        logger.info(f"Archived proposal '{proposal.name}' (id={proposal_id})")
        return proposal

    async def delete_proposal(
        self,
        proposal_id: UUID,
        user_id: UUID,
    ) -> bool:
        """
        Delete a proposal.

        Args:
            proposal_id: Proposal UUID
            user_id: User deleting proposal

        Returns:
            True if deleted

        Raises:
            OpenSpecProposalNotFoundError: If proposal not found
            TaskSyncError: If proposal has synced tasks
            InsufficientOpenSpecPermissionsError: If user lacks admin permissions
        """
        proposal = await self.repo.get_by_id(proposal_id)
        if not proposal:
            raise OpenSpecProposalNotFoundError(f"Proposal {proposal_id} not found")

        # Verify user has project admin access
        await self._verify_project_access(proposal.project_id, user_id, required_role="admin")

        # Check if proposal has synced tasks
        if proposal.task_sync_status == "synced" and proposal.tasks:
            raise TaskSyncError(
                f"Cannot delete proposal with synced tasks. "
                f"Archive the proposal instead, or delete linked tasks first."
            )

        # Delete from database
        success = await self.repo.delete(proposal_id)

        if success:
            await self.db.flush()
            logger.info(f"Deleted proposal '{proposal.name}' (id={proposal_id})")
        else:
            logger.warning(f"Failed to delete proposal {proposal_id}")

        return success

    async def calculate_and_update_completion(
        self,
        proposal_id: UUID,
    ) -> int:
        """
        Calculate and update completion percentage from linked tasks.

        Args:
            proposal_id: Proposal UUID

        Returns:
            Completion percentage (0-100)
        """
        completion = await self.repo.calculate_completion(proposal_id)
        await self.db.flush()

        logger.debug(f"Calculated completion for proposal {proposal_id}: {completion}%")
        return completion

    async def apply_spec_delta(
        self,
        proposal_id: UUID,
        user_id: UUID,
    ) -> bool:
        """
        Apply spec-delta to main specifications.

        For MVP: Just marks as applied in metadata.
        Full implementation (applying changes to openspec/project.md) deferred to Phase 6.

        Args:
            proposal_id: Proposal UUID
            user_id: User applying spec delta

        Returns:
            True if marked as applied

        Raises:
            OpenSpecProposalNotFoundError: If proposal not found
            InsufficientOpenSpecPermissionsError: If user lacks admin permissions
        """
        proposal = await self.repo.get_by_id(proposal_id)
        if not proposal:
            raise OpenSpecProposalNotFoundError(f"Proposal {proposal_id} not found")

        # Verify user has project admin access
        await self._verify_project_access(proposal.project_id, user_id, required_role="admin")

        # For MVP: just mark as applied in metadata
        metadata = proposal.metadata_json or {}
        metadata["spec_delta_applied"] = True
        metadata["spec_delta_applied_by"] = str(user_id)
        metadata["spec_delta_applied_at"] = datetime.now(UTC).isoformat()

        updated_proposal = await self.repo.update(proposal_id, {"metadata_json": metadata})

        if not updated_proposal:
            raise OpenSpecProposalNotFoundError(
                f"Proposal {proposal_id} not found after updating metadata"
            )

        # Update status to completed if not already
        if updated_proposal.status != "completed":
            final_proposal = await self.repo.update_status(proposal_id, "completed")
            if final_proposal:
                updated_proposal = final_proposal

        await self.db.flush()

        logger.info(
            f"Marked spec-delta as applied for proposal '{updated_proposal.name}' (MVP implementation)"
        )
        return True

    # ============= Access Control Helper =============

    async def _verify_project_access(
        self,
        project_id: UUID,
        user_id: UUID,
        required_role: str | None = None,
    ) -> bool:
        """
        Verify user has project access with optional role requirement.

        Args:
            project_id: Project UUID
            user_id: User UUID
            required_role: Minimum required role (viewer/member/admin/owner)

        Returns:
            True if access granted

        Raises:
            InsufficientOpenSpecPermissionsError: If user lacks permissions
        """
        # Default to viewer if no role specified
        role = required_role or "viewer"

        has_permission = await self.project_service.check_permission(
            project_id=project_id,
            user_id=user_id,
            required_role=role,
        )

        if not has_permission:
            logger.warning(f"User {user_id} lacks '{role}' permission for project {project_id}")
            raise InsufficientOpenSpecPermissionsError(
                f"User must have at least '{role}' role in project to perform this operation"
            )

        return True
