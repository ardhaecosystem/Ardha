"""
OpenSpec Proposal repository for data access operations.

This module provides the data access layer for OpenSpec proposals, handling all
database queries and CRUD operations with proper async patterns.
"""

import logging
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from sqlalchemy import and_, func, select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ardha.models.openspec import OpenSpecProposal

logger = logging.getLogger(__name__)


class OpenSpecRepository:
    """
    Repository for OpenSpec proposal database operations.

    Handles:
    - CRUD operations for proposals
    - Status workflow management
    - Content updates and versioning
    - Task synchronization tracking
    - Completion percentage calculation
    """

    def __init__(self, session: AsyncSession):
        """
        Initialize OpenSpec repository.

        Args:
            session: Async SQLAlchemy database session
        """
        self.session = session

    # ============= Core CRUD Operations =============

    async def create(self, proposal: OpenSpecProposal) -> OpenSpecProposal:
        """
        Create a new OpenSpec proposal.

        Args:
            proposal: OpenSpecProposal instance to create

        Returns:
            Created proposal with populated ID

        Raises:
            IntegrityError: If unique constraint violated (duplicate name)
        """
        try:
            self.session.add(proposal)
            await self.session.flush()
            await self.session.refresh(proposal)

            logger.info(
                f"Created OpenSpec proposal '{proposal.name}' "
                f"(id={proposal.id}, project={proposal.project_id})"
            )
            return proposal

        except IntegrityError:
            logger.error(
                f"Failed to create proposal '{proposal.name}': "
                f"Duplicate name in project {proposal.project_id}"
            )
            raise

        except SQLAlchemyError as e:
            logger.error(f"Database error creating proposal: {e}", exc_info=True)
            raise

    async def get_by_id(self, proposal_id: UUID) -> OpenSpecProposal | None:
        """
        Get proposal by ID with eager loaded relationships.

        Args:
            proposal_id: Proposal UUID

        Returns:
            Proposal if found, None otherwise
        """
        try:
            stmt = (
                select(OpenSpecProposal)
                .where(OpenSpecProposal.id == proposal_id)
                .options(
                    selectinload(OpenSpecProposal.project),
                    selectinload(OpenSpecProposal.created_by),
                    selectinload(OpenSpecProposal.approved_by),
                    selectinload(OpenSpecProposal.tasks),
                )
            )
            result = await self.session.execute(stmt)
            proposal = result.scalar_one_or_none()

            if proposal:
                logger.debug(f"Retrieved proposal {proposal_id}")
            else:
                logger.debug(f"Proposal {proposal_id} not found")

            return proposal

        except SQLAlchemyError as e:
            logger.error(f"Error fetching proposal {proposal_id}: {e}", exc_info=True)
            return None

    async def get_by_name(self, project_id: UUID, name: str) -> OpenSpecProposal | None:
        """
        Get proposal by project ID and name (case-insensitive).

        Args:
            project_id: Project UUID
            name: Proposal name

        Returns:
            Proposal if found, None otherwise
        """
        try:
            stmt = (
                select(OpenSpecProposal)
                .where(
                    and_(
                        OpenSpecProposal.project_id == project_id,
                        func.lower(OpenSpecProposal.name) == name.lower(),
                    )
                )
                .options(
                    selectinload(OpenSpecProposal.project),
                    selectinload(OpenSpecProposal.created_by),
                    selectinload(OpenSpecProposal.approved_by),
                )
            )
            result = await self.session.execute(stmt)
            return result.scalar_one_or_none()

        except SQLAlchemyError as e:
            logger.error(
                f"Error fetching proposal by name '{name}' " f"in project {project_id}: {e}",
                exc_info=True,
            )
            return None

    async def list_by_project(
        self,
        project_id: UUID,
        status: str | None = None,
        skip: int = 0,
        limit: int = 100,
    ) -> list[OpenSpecProposal]:
        """
        List proposals for a project with optional status filter.

        Args:
            project_id: Project UUID
            status: Optional status filter
            skip: Number of records to skip (pagination)
            limit: Maximum number of records to return (max 100)

        Returns:
            List of proposals matching criteria
        """
        try:
            # Validate pagination
            if skip < 0:
                raise ValueError("skip must be >= 0")
            if limit < 1 or limit > 100:
                raise ValueError("limit must be between 1 and 100")

            stmt = select(OpenSpecProposal).where(OpenSpecProposal.project_id == project_id)

            # Apply status filter
            if status:
                stmt = stmt.where(OpenSpecProposal.status == status)

            # Order by created_at DESC (newest first)
            stmt = stmt.order_by(OpenSpecProposal.created_at.desc())

            # Pagination
            stmt = stmt.offset(skip).limit(limit)

            # Eager load relationships
            stmt = stmt.options(
                selectinload(OpenSpecProposal.created_by),
                selectinload(OpenSpecProposal.approved_by),
            )

            result = await self.session.execute(stmt)
            proposals = list(result.scalars().all())

            logger.debug(f"Retrieved {len(proposals)} proposals for project {project_id}")
            return proposals

        except SQLAlchemyError as e:
            logger.error(
                f"Error listing proposals for project {project_id}: {e}",
                exc_info=True,
            )
            return []

    async def list_by_user(
        self,
        user_id: UUID,
        status: str | None = None,
        skip: int = 0,
        limit: int = 100,
    ) -> list[OpenSpecProposal]:
        """
        List proposals created by a user with optional status filter.

        Args:
            user_id: User UUID
            status: Optional status filter
            skip: Number of records to skip (pagination)
            limit: Maximum number of records to return (max 100)

        Returns:
            List of proposals created by user
        """
        try:
            # Validate pagination
            if skip < 0:
                raise ValueError("skip must be >= 0")
            if limit < 1 or limit > 100:
                raise ValueError("limit must be between 1 and 100")

            stmt = select(OpenSpecProposal).where(OpenSpecProposal.created_by_user_id == user_id)

            # Apply status filter
            if status:
                stmt = stmt.where(OpenSpecProposal.status == status)

            # Order by created_at DESC (newest first)
            stmt = stmt.order_by(OpenSpecProposal.created_at.desc())

            # Pagination
            stmt = stmt.offset(skip).limit(limit)

            # Eager load relationships
            stmt = stmt.options(
                selectinload(OpenSpecProposal.project),
                selectinload(OpenSpecProposal.approved_by),
            )

            result = await self.session.execute(stmt)
            proposals = list(result.scalars().all())

            logger.debug(f"Retrieved {len(proposals)} proposals for user {user_id}")
            return proposals

        except SQLAlchemyError as e:
            logger.error(f"Error listing proposals for user {user_id}: {e}", exc_info=True)
            return []

    async def update(
        self, proposal_id: UUID, update_data: dict[str, Any]
    ) -> OpenSpecProposal | None:
        """
        Update proposal fields.

        Args:
            proposal_id: Proposal UUID
            update_data: Dictionary of fields to update

        Returns:
            Updated proposal if found, None otherwise
        """
        try:
            proposal = await self.session.get(OpenSpecProposal, proposal_id)
            if not proposal:
                logger.warning(f"Proposal {proposal_id} not found for update")
                return None

            # Update fields
            for key, value in update_data.items():
                if hasattr(proposal, key):
                    setattr(proposal, key, value)

            # Always update updated_at timestamp
            proposal.updated_at = datetime.now(UTC)

            await self.session.flush()
            await self.session.refresh(proposal)

            logger.info(
                f"Updated proposal {proposal.name} (id={proposal_id}): "
                f"{list(update_data.keys())}"
            )
            return proposal

        except SQLAlchemyError as e:
            logger.error(f"Error updating proposal {proposal_id}: {e}", exc_info=True)
            return None

    async def delete(self, proposal_id: UUID) -> bool:
        """
        Delete a proposal (hard delete).

        Args:
            proposal_id: Proposal UUID

        Returns:
            True if deleted, False if not found
        """
        try:
            proposal = await self.session.get(OpenSpecProposal, proposal_id)
            if not proposal:
                logger.warning(f"Proposal {proposal_id} not found for deletion")
                return False

            name = proposal.name
            await self.session.delete(proposal)
            await self.session.flush()

            logger.info(f"Deleted proposal '{name}' (id={proposal_id})")
            return True

        except SQLAlchemyError as e:
            logger.error(f"Error deleting proposal {proposal_id}: {e}", exc_info=True)
            return False

    # ============= Status Management =============

    async def update_status(
        self,
        proposal_id: UUID,
        new_status: str,
        user_id: UUID | None = None,
    ) -> OpenSpecProposal | None:
        """
        Update proposal status with workflow-specific timestamps.

        Args:
            proposal_id: Proposal UUID
            new_status: New status value
            user_id: User ID for approval (if status is approved)

        Returns:
            Updated proposal if found, None otherwise
        """
        try:
            proposal = await self.session.get(OpenSpecProposal, proposal_id)
            if not proposal:
                logger.warning(f"Proposal {proposal_id} not found for status update")
                return None

            old_status = proposal.status
            proposal.status = new_status

            # Set workflow-specific timestamps and fields
            if new_status == "approved":
                proposal.approved_by_user_id = user_id
                proposal.approved_at = datetime.now(UTC)
            elif new_status == "archived":
                proposal.archived_at = datetime.now(UTC)

            proposal.updated_at = datetime.now(UTC)

            await self.session.flush()
            await self.session.refresh(proposal)

            logger.info(f"Proposal {proposal.name} status: {old_status} → {new_status}")
            return proposal

        except SQLAlchemyError as e:
            logger.error(
                f"Error updating status for proposal {proposal_id}: {e}",
                exc_info=True,
            )
            return None

    # ============= Content Management =============

    async def update_content(
        self,
        proposal_id: UUID,
        proposal_content: str | None = None,
        tasks_content: str | None = None,
        spec_delta_content: str | None = None,
        metadata_json: dict | None = None,
    ) -> OpenSpecProposal | None:
        """
        Update proposal content fields.

        Args:
            proposal_id: Proposal UUID
            proposal_content: Optional new proposal.md content
            tasks_content: Optional new tasks.md content
            spec_delta_content: Optional new spec-delta.md content
            metadata_json: Optional new metadata

        Returns:
            Updated proposal if found, None otherwise
        """
        try:
            proposal = await self.session.get(OpenSpecProposal, proposal_id)
            if not proposal:
                logger.warning(f"Proposal {proposal_id} not found for content update")
                return None

            # Track if tasks content changed
            tasks_changed = False

            # Update only provided content fields
            if proposal_content is not None:
                proposal.proposal_content = proposal_content

            if tasks_content is not None:
                if proposal.tasks_content != tasks_content:
                    tasks_changed = True
                proposal.tasks_content = tasks_content

            if spec_delta_content is not None:
                proposal.spec_delta_content = spec_delta_content

            if metadata_json is not None:
                proposal.metadata_json = metadata_json

            # If tasks changed, reset sync status
            if tasks_changed:
                proposal.task_sync_status = "not_synced"
                logger.info(
                    f"Tasks content changed for proposal {proposal.name}, "
                    f"reset sync status to not_synced"
                )

            proposal.updated_at = datetime.now(UTC)

            await self.session.flush()
            await self.session.refresh(proposal)

            logger.info(f"Updated content for proposal {proposal.name}")
            return proposal

        except SQLAlchemyError as e:
            logger.error(
                f"Error updating content for proposal {proposal_id}: {e}",
                exc_info=True,
            )
            return None

    # ============= Task Synchronization =============

    async def update_sync_status(
        self,
        proposal_id: UUID,
        sync_status: str,
        error_message: str | None = None,
    ) -> OpenSpecProposal | None:
        """
        Update task synchronization status.

        Args:
            proposal_id: Proposal UUID
            sync_status: New sync status (not_synced, syncing, synced, sync_failed)
            error_message: Optional error message if sync failed

        Returns:
            Updated proposal if found, None otherwise
        """
        try:
            proposal = await self.session.get(OpenSpecProposal, proposal_id)
            if not proposal:
                logger.warning(f"Proposal {proposal_id} not found for sync update")
                return None

            proposal.task_sync_status = sync_status
            proposal.last_sync_at = datetime.now(UTC)

            if error_message:
                proposal.sync_error_message = error_message
            elif sync_status == "synced":
                # Clear error message on successful sync
                proposal.sync_error_message = None

            proposal.updated_at = datetime.now(UTC)

            await self.session.flush()
            await self.session.refresh(proposal)

            logger.info(f"Updated sync status for proposal {proposal.name}: {sync_status}")
            return proposal

        except SQLAlchemyError as e:
            logger.error(
                f"Error updating sync status for proposal {proposal_id}: {e}",
                exc_info=True,
            )
            return None

    async def calculate_completion(self, proposal_id: UUID) -> int:
        """
        Calculate and update completion percentage from linked tasks.

        Args:
            proposal_id: Proposal UUID

        Returns:
            Completion percentage (0-100), or 0 if no tasks
        """
        try:
            # Fetch proposal with tasks relationship
            stmt = (
                select(OpenSpecProposal)
                .where(OpenSpecProposal.id == proposal_id)
                .options(selectinload(OpenSpecProposal.tasks))
            )
            result = await self.session.execute(stmt)
            proposal = result.scalar_one_or_none()

            if not proposal:
                logger.warning(f"Proposal {proposal_id} not found for completion calculation")
                return 0

            # Calculate completion
            total_tasks = len(proposal.tasks) if proposal.tasks else 0
            completed_tasks = (
                sum(1 for task in proposal.tasks if task.status == "done") if proposal.tasks else 0
            )

            if total_tasks == 0:
                completion = 0
            else:
                completion = int((completed_tasks / total_tasks) * 100)

            # Update proposal
            proposal.completion_percentage = completion
            proposal.updated_at = datetime.now(UTC)

            await self.session.flush()

            logger.info(
                f"Calculated completion for proposal {proposal.name}: "
                f"{completion}% ({completed_tasks}/{total_tasks} tasks)"
            )
            return completion

        except SQLAlchemyError as e:
            logger.error(
                f"Error calculating completion for proposal {proposal_id}: {e}",
                exc_info=True,
            )
            return 0

    # ============= Querying & Counting =============

    async def count_by_project(self, project_id: UUID, status: str | None = None) -> int:
        """
        Count proposals for a project with optional status filter.

        Args:
            project_id: Project UUID
            status: Optional status filter

        Returns:
            Total count of proposals
        """
        try:
            stmt = select(func.count(OpenSpecProposal.id)).where(
                OpenSpecProposal.project_id == project_id
            )

            if status:
                stmt = stmt.where(OpenSpecProposal.status == status)

            result = await self.session.execute(stmt)
            count = result.scalar() or 0

            logger.debug(
                f"Counted {count} proposals for project {project_id}"
                + (f" with status {status}" if status else "")
            )
            return count

        except SQLAlchemyError as e:
            logger.error(
                f"Error counting proposals for project {project_id}: {e}",
                exc_info=True,
            )
            return 0

    async def get_active_proposals(self, project_id: UUID) -> list[OpenSpecProposal]:
        """
        Get all active proposals (not archived or completed).

        Args:
            project_id: Project UUID

        Returns:
            List of active proposals
        """
        try:
            stmt = (
                select(OpenSpecProposal)
                .where(
                    and_(
                        OpenSpecProposal.project_id == project_id,
                        OpenSpecProposal.status.notin_(["archived", "completed"]),
                    )
                )
                .order_by(OpenSpecProposal.created_at.desc())
                .options(
                    selectinload(OpenSpecProposal.created_by),
                    selectinload(OpenSpecProposal.approved_by),
                )
            )
            result = await self.session.execute(stmt)
            proposals = list(result.scalars().all())

            logger.debug(f"Retrieved {len(proposals)} active proposals for project {project_id}")
            return proposals

        except SQLAlchemyError as e:
            logger.error(
                f"Error fetching active proposals for project {project_id}: {e}",
                exc_info=True,
            )
            return []
