"""
Milestone repository for data access abstraction.

This module provides the repository pattern implementation for the Milestone model,
handling all database operations related to milestones including CRUD operations,
task-related queries, and analytics.
"""

import logging
from datetime import datetime, timedelta, timezone
from uuid import UUID

from sqlalchemy import and_, case, func, select, update
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ardha.models.milestone import Milestone
from ardha.models.task import Task

logger = logging.getLogger(__name__)


class MilestoneRepository:
    """
    Repository for Milestone model database operations.

    Provides data access methods for milestone-related operations including
    CRUD operations, task queries, progress calculation, and analytics.
    Follows the repository pattern to abstract database implementation from
    business logic.

    Attributes:
        db: SQLAlchemy async session for database operations
    """

    def __init__(self, db: AsyncSession) -> None:
        """
        Initialize the MilestoneRepository with a database session.

        Args:
            db: SQLAlchemy async session for database operations
        """
        self.db = db

    # ============= Core CRUD Operations =============

    async def get_by_id(self, milestone_id: UUID) -> Milestone | None:
        """
        Fetch a milestone by its UUID.

        Args:
            milestone_id: UUID of the milestone to fetch

        Returns:
            Milestone object if found, None otherwise

        Raises:
            SQLAlchemyError: If database query fails
        """
        try:
            stmt = select(Milestone).where(Milestone.id == milestone_id)
            result = await self.db.execute(stmt)
            return result.scalar_one_or_none()
        except SQLAlchemyError as e:
            logger.error(f"Error fetching milestone by id {milestone_id}: {e}", exc_info=True)
            raise

    async def get_project_milestones(
        self,
        project_id: UUID,
        skip: int = 0,
        limit: int = 100,
    ) -> list[Milestone]:
        """
        Fetch all milestones for a project, ordered by order field.

        Args:
            project_id: UUID of the project
            skip: Number of records to skip (for pagination)
            limit: Maximum number of records to return (capped at 100)

        Returns:
            List of Milestone objects ordered by order

        Raises:
            SQLAlchemyError: If database query fails
        """
        try:
            stmt = (
                select(Milestone)
                .where(Milestone.project_id == project_id)
                .order_by(Milestone.order)
                .offset(skip)
                .limit(min(limit, 100))
            )
            result = await self.db.execute(stmt)
            return list(result.scalars().all())
        except SQLAlchemyError as e:
            logger.error(f"Error fetching milestones for project {project_id}: {e}", exc_info=True)
            raise

    async def get_by_status(self, project_id: UUID, status: str) -> list[Milestone]:
        """
        Fetch milestones filtered by status.

        Args:
            project_id: UUID of the project
            status: Status to filter by (not_started, in_progress, completed, cancelled)

        Returns:
            List of Milestone objects matching the status

        Raises:
            SQLAlchemyError: If database query fails
        """
        try:
            stmt = (
                select(Milestone)
                .where(and_(Milestone.project_id == project_id, Milestone.status == status))
                .order_by(Milestone.order)
            )
            result = await self.db.execute(stmt)
            return list(result.scalars().all())
        except SQLAlchemyError as e:
            logger.error(
                f"Error fetching milestones by status for project {project_id}: {e}", exc_info=True
            )
            raise

    async def create(self, milestone_data: dict) -> Milestone:
        """
        Create a new milestone.

        If no order is specified, appends to end (max order + 1).

        Args:
            milestone_data: Dictionary containing milestone fields

        Returns:
            Created Milestone object with generated ID and timestamps

        Raises:
            IntegrityError: If unique constraint violated
            SQLAlchemyError: If database operation fails
        """
        try:
            # Always auto-assign order to prevent conflicts
            # Important: Flush any pending changes first to get accurate max order
            await self.db.flush()

            # Get the next available order for this project
            project_id = milestone_data.get("project_id")
            max_order_stmt = select(func.coalesce(func.max(Milestone.order), -1)).where(
                Milestone.project_id == project_id
            )
            result = await self.db.execute(max_order_stmt)
            max_order = result.scalar()
            # Always assign next order, ignoring any provided value
            next_order = (max_order or -1) + 1
            milestone_data["order"] = next_order

            logger.info(
                f"Auto-assigning order {next_order} for project {project_id} (max_order was {max_order})"
            )

            milestone = Milestone(**milestone_data)
            self.db.add(milestone)
            await self.db.flush()
            await self.db.refresh(milestone)

            logger.info(f"Created milestone {milestone.id} for project {milestone.project_id}")
            return milestone
        except IntegrityError as e:
            logger.warning(f"Integrity error creating milestone: {e}")
            raise
        except SQLAlchemyError as e:
            logger.error(f"Error creating milestone: {e}", exc_info=True)
            raise

    async def update(self, milestone_id: UUID, **kwargs) -> Milestone | None:
        """
        Update milestone fields.

        Updates specified fields for a milestone identified by UUID.
        Only updates fields provided in kwargs.

        Args:
            milestone_id: UUID of milestone to update
            **kwargs: Fields to update (e.g., name="New Name", description="...")

        Returns:
            Updated Milestone object if found, None if milestone doesn't exist

        Raises:
            IntegrityError: If update violates unique constraints
            SQLAlchemyError: If database operation fails
        """
        try:
            milestone = await self.get_by_id(milestone_id)
            if not milestone:
                logger.warning(f"Cannot update: milestone {milestone_id} not found")
                return None

            # Update only provided fields
            for key, value in kwargs.items():
                if hasattr(milestone, key):
                    setattr(milestone, key, value)
                else:
                    logger.warning(f"Skipping unknown field: {key}")

            await self.db.flush()
            await self.db.refresh(milestone)
            logger.info(f"Updated milestone {milestone_id}")
            return milestone
        except IntegrityError as e:
            logger.warning(f"Integrity error updating milestone {milestone_id}: {e}")
            raise
        except SQLAlchemyError as e:
            logger.error(f"Error updating milestone {milestone_id}: {e}", exc_info=True)
            raise

    async def delete(self, milestone_id: UUID) -> bool:
        """
        Delete a milestone.

        Args:
            milestone_id: UUID of milestone to delete

        Returns:
            True if milestone was deleted, False if milestone not found

        Raises:
            SQLAlchemyError: If database operation fails
        """
        try:
            milestone = await self.get_by_id(milestone_id)
            if not milestone:
                logger.warning(f"Cannot delete: milestone {milestone_id} not found")
                return False

            await self.db.delete(milestone)
            await self.db.flush()
            logger.info(f"Deleted milestone {milestone_id}")
            return True
        except SQLAlchemyError as e:
            logger.error(f"Error deleting milestone {milestone_id}: {e}", exc_info=True)
            raise

    async def update_status(
        self,
        milestone_id: UUID,
        status: str,
    ) -> Milestone | None:
        """
        Update milestone status and set completed_at timestamp if applicable.

        When status → completed: Sets completed_at to current timestamp
        When status changes from completed: Clears completed_at

        Args:
            milestone_id: UUID of milestone to update
            status: New status value

        Returns:
            Updated Milestone object if found, None otherwise

        Raises:
            SQLAlchemyError: If database operation fails
        """
        try:
            milestone = await self.get_by_id(milestone_id)
            if not milestone:
                logger.warning(f"Cannot update status: milestone {milestone_id} not found")
                return None

            old_status = milestone.status
            milestone.status = status

            # Update completed_at based on status transition
            if status == "completed" and old_status != "completed":
                milestone.completed_at = datetime.now(timezone.utc)
            elif status != "completed" and milestone.completed_at:
                milestone.completed_at = None

            await self.db.flush()
            await self.db.refresh(milestone)
            logger.info(f"Updated milestone {milestone_id} status to {status}")
            return milestone
        except SQLAlchemyError as e:
            logger.error(f"Error updating milestone status {milestone_id}: {e}", exc_info=True)
            raise

    async def update_progress(
        self,
        milestone_id: UUID,
        progress: int,
    ) -> Milestone | None:
        """
        Manually update milestone progress percentage.

        Args:
            milestone_id: UUID of milestone to update
            progress: Progress percentage (0-100)

        Returns:
            Updated Milestone object if found, None otherwise

        Raises:
            ValueError: If progress not in range 0-100
            SQLAlchemyError: If database operation fails
        """
        try:
            if not 0 <= progress <= 100:
                raise ValueError(f"Progress must be 0-100, got {progress}")

            milestone = await self.get_by_id(milestone_id)
            if not milestone:
                logger.warning(f"Cannot update progress: milestone {milestone_id} not found")
                return None

            milestone.progress_percentage = progress
            await self.db.flush()
            await self.db.refresh(milestone)
            logger.info(f"Updated milestone {milestone_id} progress to {progress}%")
            return milestone
        except SQLAlchemyError as e:
            logger.error(f"Error updating milestone progress {milestone_id}: {e}", exc_info=True)
            raise

    async def reorder(
        self,
        project_id: UUID,
        milestone_id: UUID,
        new_order: int,
    ) -> Milestone | None:
        """
        Change milestone order (for drag-drop in UI).

        Handles order collision by shifting other milestones:
        1. Get current milestone and validate
        2. Update all milestones >= new_order (shift up by 1)
        3. Set milestone to new_order

        Args:
            project_id: UUID of the project
            milestone_id: UUID of milestone to reorder
            new_order: New order value

        Returns:
            Updated Milestone object if found, None otherwise

        Raises:
            ValueError: If new_order is negative
            SQLAlchemyError: If database operation fails
        """
        try:
            if new_order < 0:
                raise ValueError(f"Order must be >= 0, got {new_order}")

            milestone = await self.get_by_id(milestone_id)
            if not milestone:
                logger.warning(f"Cannot reorder: milestone {milestone_id} not found")
                return None

            if milestone.project_id != project_id:
                raise ValueError(
                    f"Milestone {milestone_id} does not belong to project {project_id}"
                )

            old_order = milestone.order

            if old_order == new_order:
                # No change needed
                return milestone

            # Shift other milestones to make room
            if new_order < old_order:
                # Moving up: shift down milestones in range [new_order, old_order)
                stmt = (
                    update(Milestone)
                    .where(
                        and_(
                            Milestone.project_id == project_id,
                            Milestone.order >= new_order,
                            Milestone.order < old_order,
                        )
                    )
                    .values(order=Milestone.order + 1)
                )
            else:
                # Moving down: shift up milestones in range (old_order, new_order]
                stmt = (
                    update(Milestone)
                    .where(
                        and_(
                            Milestone.project_id == project_id,
                            Milestone.order > old_order,
                            Milestone.order <= new_order,
                        )
                    )
                    .values(order=Milestone.order - 1)
                )

            await self.db.execute(stmt)

            # Update the milestone's order
            milestone.order = new_order
            await self.db.flush()
            await self.db.refresh(milestone)

            logger.info(f"Reordered milestone {milestone_id} from {old_order} to {new_order}")
            return milestone
        except SQLAlchemyError as e:
            logger.error(f"Error reordering milestone {milestone_id}: {e}", exc_info=True)
            raise

    # ============= Task-Related Queries =============

    async def get_milestone_tasks(
        self,
        milestone_id: UUID,
        skip: int = 0,
        limit: int = 100,
    ) -> list[Task]:
        """
        Fetch all tasks belonging to a milestone.

        Args:
            milestone_id: UUID of the milestone
            skip: Number of records to skip (for pagination)
            limit: Maximum number of records to return (capped at 100)

        Returns:
            List of Task objects

        Raises:
            SQLAlchemyError: If database query fails
        """
        try:
            stmt = (
                select(Task)
                .where(Task.milestone_id == milestone_id)
                .order_by(Task.created_at.desc())
                .offset(skip)
                .limit(min(limit, 100))
            )
            result = await self.db.execute(stmt)
            return list(result.scalars().all())
        except SQLAlchemyError as e:
            logger.error(f"Error fetching tasks for milestone {milestone_id}: {e}", exc_info=True)
            raise

    async def count_milestone_tasks(self, milestone_id: UUID) -> dict[str, int]:
        """
        Count tasks by status for a milestone.

        Returns counts for each status: todo, in_progress, in_review, done, cancelled

        Args:
            milestone_id: UUID of the milestone

        Returns:
            Dictionary mapping status to count

        Raises:
            SQLAlchemyError: If database query fails
        """
        try:
            stmt = (
                select(Task.status, func.count(Task.id).label("count"))
                .where(Task.milestone_id == milestone_id)
                .group_by(Task.status)
            )
            result = await self.db.execute(stmt)
            rows = result.all()

            # Build dictionary with all statuses (default 0)
            status_counts = {
                "todo": 0,
                "in_progress": 0,
                "in_review": 0,
                "done": 0,
                "cancelled": 0,
            }

            for row in rows:
                # Access row attributes properly (row is a Row object)
                status = row[0]  # Task.status
                count = row[1]  # count
                status_counts[status] = count

            return status_counts
        except SQLAlchemyError as e:
            logger.error(f"Error counting tasks for milestone {milestone_id}: {e}", exc_info=True)
            raise

    async def calculate_progress(self, milestone_id: UUID) -> int:
        """
        Calculate progress from task completion.

        Formula: progress = (completed_tasks / total_tasks) * 100
        Returns 0 if no tasks exist.

        Args:
            milestone_id: UUID of the milestone

        Returns:
            Progress percentage (0-100)

        Raises:
            SQLAlchemyError: If database query fails
        """
        try:
            stmt = select(
                func.count(Task.id).label("total"),
                func.count(case((Task.status == "done", 1))).label("completed"),
            ).where(Task.milestone_id == milestone_id)

            result = await self.db.execute(stmt)
            row = result.first()

            if not row or row.total == 0:
                return 0

            progress = int((row.completed / row.total) * 100)
            return progress
        except SQLAlchemyError as e:
            logger.error(
                f"Error calculating progress for milestone {milestone_id}: {e}", exc_info=True
            )
            raise

    async def get_milestones_with_task_counts(
        self,
        project_id: UUID,
    ) -> list[tuple[Milestone, int]]:
        """
        Fetch milestones with their task counts.

        Args:
            project_id: UUID of the project

        Returns:
            List of tuples (Milestone, task_count)

        Raises:
            SQLAlchemyError: If database query fails
        """
        try:
            # Get all milestones for project
            milestones = await self.get_project_milestones(project_id, skip=0, limit=1000)

            # Get task counts for each milestone
            result = []
            for milestone in milestones:
                task_count_stmt = select(func.count(Task.id)).where(
                    Task.milestone_id == milestone.id
                )
                count_result = await self.db.execute(task_count_stmt)
                task_count = count_result.scalar() or 0
                result.append((milestone, task_count))

            return result
        except SQLAlchemyError as e:
            logger.error(
                f"Error fetching milestones with task counts for project {project_id}: {e}",
                exc_info=True,
            )
            raise

    # ============= Analytics Queries =============

    async def get_upcoming_milestones(
        self,
        project_id: UUID,
        days: int = 30,
    ) -> list[Milestone]:
        """
        Fetch milestones due within the next N days.

        Excludes completed and cancelled milestones.

        Args:
            project_id: UUID of the project
            days: Number of days to look ahead (default: 30)

        Returns:
            List of Milestone objects ordered by due_date

        Raises:
            SQLAlchemyError: If database query fails
        """
        try:
            cutoff_date = datetime.now(timezone.utc) + timedelta(days=days)

            stmt = (
                select(Milestone)
                .where(
                    and_(
                        Milestone.project_id == project_id,
                        Milestone.due_date.isnot(None),
                        Milestone.due_date <= cutoff_date,
                        Milestone.status.notin_(["completed", "cancelled"]),
                    )
                )
                .order_by(Milestone.due_date)
            )
            result = await self.db.execute(stmt)
            return list(result.scalars().all())
        except SQLAlchemyError as e:
            logger.error(
                f"Error fetching upcoming milestones for project {project_id}: {e}", exc_info=True
            )
            raise

    async def get_overdue_milestones(self, project_id: UUID) -> list[Milestone]:
        """
        Fetch milestones past their due date.

        Excludes completed and cancelled milestones.

        Args:
            project_id: UUID of the project

        Returns:
            List of overdue Milestone objects ordered by due_date

        Raises:
            SQLAlchemyError: If database query fails
        """
        try:
            now = datetime.now(timezone.utc)

            stmt = (
                select(Milestone)
                .where(
                    and_(
                        Milestone.project_id == project_id,
                        Milestone.due_date.isnot(None),
                        Milestone.due_date < now,
                        Milestone.status.notin_(["completed", "cancelled"]),
                    )
                )
                .order_by(Milestone.due_date)
            )
            result = await self.db.execute(stmt)
            return list(result.scalars().all())
        except SQLAlchemyError as e:
            logger.error(
                f"Error fetching overdue milestones for project {project_id}: {e}", exc_info=True
            )
            raise
