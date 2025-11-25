"""
Milestone service for business logic.

This module provides business logic for milestone management, including CRUD operations,
status transitions, permission checks, and progress tracking.
"""

import logging
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from ardha.models.milestone import Milestone
from ardha.repositories.milestone_repository import MilestoneRepository
from ardha.schemas.requests.milestone import MilestoneCreateRequest, MilestoneUpdateRequest
from ardha.services.project_service import ProjectService

logger = logging.getLogger(__name__)

# Valid status transitions
VALID_TRANSITIONS = {
    "not_started": ["in_progress", "cancelled"],
    "in_progress": ["completed", "not_started", "cancelled"],
    "completed": ["in_progress"],  # Can reopen
    "cancelled": ["not_started"],  # Can uncancel
}


class MilestoneNotFoundError(Exception):
    """Raised when milestone is not found."""

    pass


class MilestoneHasTasksError(Exception):
    """Raised when trying to delete milestone with tasks."""

    pass


class InvalidMilestoneStatusError(Exception):
    """Raised when invalid status transition."""

    pass


class InsufficientMilestonePermissionsError(Exception):
    """Raised when user lacks permissions."""

    pass


class MilestoneService:
    """
    Service for milestone management business logic.

    Handles milestone CRUD operations, status transitions, permission checks,
    and progress tracking. Enforces business rules including status transition
    validation and delete protection.

    Attributes:
        db: SQLAlchemy async session
        repository: MilestoneRepository for data access
        project_service: ProjectService for permission checks
    """

    def __init__(self, db: AsyncSession) -> None:
        """
        Initialize MilestoneService.

        Args:
            db: SQLAlchemy async session for database operations
        """
        self.db = db
        self.repository = MilestoneRepository(db)
        self.project_service = ProjectService(db)

    # ============= Core CRUD Operations =============

    async def create_milestone(
        self,
        milestone_data: MilestoneCreateRequest,
        project_id: UUID,
        user_id: UUID,
    ) -> Milestone:
        """
        Create a new milestone.

        Requires project member access (member role or higher).

        Args:
            milestone_data: Milestone creation request data
            project_id: UUID of the project
            user_id: UUID of user creating the milestone

        Returns:
            Created Milestone object

        Raises:
            InsufficientMilestonePermissionsError: If user lacks permissions
            SQLAlchemyError: If database operation fails
        """
        # Check permissions (must be project member)
        if not await self.project_service.check_permission(project_id, user_id, "member"):
            logger.warning(
                f"User {user_id} lacks permission to create milestone in project {project_id}"
            )
            raise InsufficientMilestonePermissionsError(
                "Only project members can create milestones"
            )

        logger.info(f"Creating milestone '{milestone_data.name}' for project {project_id}")

        # Convert Pydantic model to dict, exclude order (let repository auto-assign)
        milestone_dict = milestone_data.model_dump(exclude_none=True, exclude={"order"})
        milestone_dict["project_id"] = project_id

        # Create milestone (repository handles order generation)
        milestone = await self.repository.create(milestone_dict)
        await self.db.flush()
        await self.db.refresh(milestone)

        logger.info(f"Created milestone {milestone.id}")
        return milestone

    async def get_milestone(self, milestone_id: UUID, user_id: UUID) -> Milestone:
        """
        Get milestone by ID.

        Requires project member access.

        Args:
            milestone_id: UUID of the milestone
            user_id: UUID of user making the request

        Returns:
            Milestone object

        Raises:
            MilestoneNotFoundError: If milestone not found
            InsufficientMilestonePermissionsError: If user lacks permissions
        """
        milestone = await self.repository.get_by_id(milestone_id)
        if not milestone:
            logger.warning(f"Milestone {milestone_id} not found")
            raise MilestoneNotFoundError(f"Milestone {milestone_id} not found")

        # Check permissions
        if not await self.project_service.check_permission(milestone.project_id, user_id, "member"):
            logger.warning(f"User {user_id} lacks permission to view milestone {milestone_id}")
            raise InsufficientMilestonePermissionsError("Only project members can view milestones")

        return milestone

    async def get_project_milestones(
        self,
        project_id: UUID,
        user_id: UUID,
        skip: int = 0,
        limit: int = 100,
    ) -> list[Milestone]:
        """
        Get all milestones for a project.

        Requires project member access.

        Args:
            project_id: UUID of the project
            user_id: UUID of user making the request
            skip: Number of records to skip (pagination)
            limit: Maximum number of records to return

        Returns:
            List of Milestone objects ordered by order

        Raises:
            InsufficientMilestonePermissionsError: If user lacks permissions
        """
        # Check permissions
        if not await self.project_service.check_permission(project_id, user_id, "member"):
            logger.warning(
                f"User {user_id} lacks permission to view milestones for project {project_id}"
            )
            raise InsufficientMilestonePermissionsError("Only project members can view milestones")

        return await self.repository.get_project_milestones(
            project_id,
            skip=skip,
            limit=limit,
        )

    async def update_milestone(
        self,
        milestone_id: UUID,
        user_id: UUID,
        update_data: MilestoneUpdateRequest,
    ) -> Milestone:
        """
        Update milestone.

        Requires project member access (member role or higher).

        Args:
            milestone_id: UUID of milestone to update
            user_id: UUID of user making the request
            update_data: Fields to update

        Returns:
            Updated Milestone object

        Raises:
            MilestoneNotFoundError: If milestone not found
            InsufficientMilestonePermissionsError: If user lacks permissions
        """
        # Get milestone and check it exists
        milestone = await self.repository.get_by_id(milestone_id)
        if not milestone:
            raise MilestoneNotFoundError(f"Milestone {milestone_id} not found")

        # Check permissions
        if not await self.project_service.check_permission(milestone.project_id, user_id, "member"):
            logger.warning(f"User {user_id} lacks permission to update milestone {milestone_id}")
            raise InsufficientMilestonePermissionsError(
                "Only project members can update milestones"
            )

        # Convert Pydantic model to dict, excluding None values
        update_dict = update_data.model_dump(exclude_none=True)

        if not update_dict:
            # No fields to update
            return milestone

        logger.info(f"Updating milestone {milestone_id} with fields: {list(update_dict.keys())}")

        updated_milestone = await self.repository.update(milestone_id, **update_dict)
        if not updated_milestone:
            raise MilestoneNotFoundError(f"Milestone {milestone_id} not found")

        await self.db.flush()
        await self.db.refresh(updated_milestone)

        logger.info(f"Updated milestone {milestone_id}")
        return updated_milestone

    async def delete_milestone(self, milestone_id: UUID, user_id: UUID) -> bool:
        """
        Delete a milestone.

        Requires admin or owner role. Prevents deletion if milestone has linked tasks.

        Args:
            milestone_id: UUID of milestone to delete
            user_id: UUID of user making the request

        Returns:
            True if deleted successfully

        Raises:
            MilestoneNotFoundError: If milestone not found
            InsufficientMilestonePermissionsError: If user lacks permissions
            MilestoneHasTasksError: If milestone has linked tasks
        """
        # Get milestone and check it exists
        milestone = await self.repository.get_by_id(milestone_id)
        if not milestone:
            raise MilestoneNotFoundError(f"Milestone {milestone_id} not found")

        # Check permissions (admin or owner only)
        if not await self.project_service.check_permission(milestone.project_id, user_id, "admin"):
            logger.warning(f"User {user_id} lacks permission to delete milestone {milestone_id}")
            raise InsufficientMilestonePermissionsError(
                "Only project owner or admin can delete milestones"
            )

        # Check for linked tasks
        task_counts = await self.repository.count_milestone_tasks(milestone_id)
        total_tasks = sum(task_counts.values())

        if total_tasks > 0:
            logger.warning(
                f"Cannot delete milestone {milestone_id}: has {total_tasks} linked tasks"
            )
            raise MilestoneHasTasksError(
                f"Cannot delete milestone with {total_tasks} linked tasks. "
                "Unlink tasks first or delete them."
            )

        logger.info(f"Deleting milestone {milestone_id}")

        success = await self.repository.delete(milestone_id)
        if not success:
            raise MilestoneNotFoundError(f"Milestone {milestone_id} not found")

        await self.db.flush()
        logger.info(f"Deleted milestone {milestone_id}")
        return True

    # ============= Status Management =============

    async def update_status(
        self,
        milestone_id: UUID,
        user_id: UUID,
        status: str,
    ) -> Milestone:
        """
        Update milestone status with validation.

        Validates status transitions and automatically sets completed_at timestamp.

        Args:
            milestone_id: UUID of the milestone
            user_id: UUID of user making the request
            status: New status value

        Returns:
            Updated Milestone object

        Raises:
            MilestoneNotFoundError: If milestone not found
            InsufficientMilestonePermissionsError: If user lacks permissions
            InvalidMilestoneStatusError: If invalid status transition
        """
        # Get milestone and check it exists
        milestone = await self.repository.get_by_id(milestone_id)
        if not milestone:
            raise MilestoneNotFoundError(f"Milestone {milestone_id} not found")

        # Check permissions
        if not await self.project_service.check_permission(milestone.project_id, user_id, "member"):
            logger.warning(
                f"User {user_id} lacks permission to update milestone {milestone_id} status"
            )
            raise InsufficientMilestonePermissionsError(
                "Only project members can update milestone status"
            )

        # Validate status transition
        current_status = milestone.status
        valid_next_statuses = VALID_TRANSITIONS.get(current_status, [])

        if status not in valid_next_statuses:
            logger.warning(
                f"Invalid status transition for milestone {milestone_id}: "
                f"{current_status} -> {status}"
            )
            raise InvalidMilestoneStatusError(
                f"Cannot transition from {current_status} to {status}. "
                f"Valid transitions: {', '.join(valid_next_statuses)}"
            )

        logger.info(f"Updating milestone {milestone_id} status to {status}")

        # Repository handles completed_at timestamp
        updated_milestone = await self.repository.update_status(milestone_id, status)
        if not updated_milestone:
            raise MilestoneNotFoundError(f"Milestone {milestone_id} not found")

        await self.db.flush()
        await self.db.refresh(updated_milestone)

        logger.info(f"Updated milestone {milestone_id} status to {status}")
        return updated_milestone

    # ============= Progress Management =============

    async def update_progress(
        self,
        milestone_id: UUID,
        user_id: UUID,
        progress: int,
    ) -> Milestone:
        """
        Manually update milestone progress percentage.

        Args:
            milestone_id: UUID of the milestone
            user_id: UUID of user making the request
            progress: Progress percentage (0-100)

        Returns:
            Updated Milestone object

        Raises:
            MilestoneNotFoundError: If milestone not found
            InsufficientMilestonePermissionsError: If user lacks permissions
            ValueError: If progress not in range 0-100
        """
        # Get milestone and check it exists
        milestone = await self.repository.get_by_id(milestone_id)
        if not milestone:
            raise MilestoneNotFoundError(f"Milestone {milestone_id} not found")

        # Check permissions
        if not await self.project_service.check_permission(milestone.project_id, user_id, "member"):
            logger.warning(
                f"User {user_id} lacks permission to update milestone {milestone_id} progress"
            )
            raise InsufficientMilestonePermissionsError(
                "Only project members can update milestone progress"
            )

        logger.info(f"Manually updating milestone {milestone_id} progress to {progress}%")

        updated_milestone = await self.repository.update_progress(milestone_id, progress)
        if not updated_milestone:
            raise MilestoneNotFoundError(f"Milestone {milestone_id} not found")

        await self.db.flush()
        await self.db.refresh(updated_milestone)

        logger.info(f"Updated milestone {milestone_id} progress to {progress}%")
        return updated_milestone

    async def recalculate_progress(self, milestone_id: UUID) -> Milestone:
        """
        Auto-calculate progress from task completion.

        Calculates progress as (completed_tasks / total_tasks) * 100
        and updates the milestone.

        Args:
            milestone_id: UUID of the milestone

        Returns:
            Updated Milestone object with recalculated progress

        Raises:
            MilestoneNotFoundError: If milestone not found
        """
        milestone = await self.repository.get_by_id(milestone_id)
        if not milestone:
            raise MilestoneNotFoundError(f"Milestone {milestone_id} not found")

        logger.info(f"Recalculating progress for milestone {milestone_id}")

        # Calculate progress from tasks
        progress = await self.repository.calculate_progress(milestone_id)

        # Update milestone with calculated progress
        updated_milestone = await self.repository.update_progress(milestone_id, progress)
        if not updated_milestone:
            raise MilestoneNotFoundError(f"Milestone {milestone_id} not found")

        await self.db.flush()
        await self.db.refresh(updated_milestone)

        logger.info(f"Recalculated milestone {milestone_id} progress to {progress}%")
        return updated_milestone

    # ============= Ordering =============

    async def reorder_milestone(
        self,
        milestone_id: UUID,
        user_id: UUID,
        new_order: int,
    ) -> Milestone:
        """
        Change milestone order (for drag-drop UI).

        Args:
            milestone_id: UUID of the milestone
            user_id: UUID of user making the request
            new_order: New order value

        Returns:
            Updated Milestone object

        Raises:
            MilestoneNotFoundError: If milestone not found
            InsufficientMilestonePermissionsError: If user lacks permissions
            ValueError: If new_order is negative
        """
        # Get milestone and check it exists
        milestone = await self.repository.get_by_id(milestone_id)
        if not milestone:
            raise MilestoneNotFoundError(f"Milestone {milestone_id} not found")

        # Check permissions
        if not await self.project_service.check_permission(milestone.project_id, user_id, "member"):
            logger.warning(f"User {user_id} lacks permission to reorder milestone {milestone_id}")
            raise InsufficientMilestonePermissionsError(
                "Only project members can reorder milestones"
            )

        logger.info(f"Reordering milestone {milestone_id} to order {new_order}")

        updated_milestone = await self.repository.reorder(
            milestone.project_id,
            milestone_id,
            new_order,
        )
        if not updated_milestone:
            raise MilestoneNotFoundError(f"Milestone {milestone_id} not found")

        await self.db.flush()
        await self.db.refresh(updated_milestone)

        logger.info(f"Reordered milestone {milestone_id} to order {new_order}")
        return updated_milestone

    # ============= Analytics & Views =============

    async def get_milestone_summary(
        self,
        milestone_id: UUID,
        user_id: UUID,
    ) -> dict:
        """
        Get milestone summary with statistics.

        Includes task counts by status, total/completed tasks, and auto-calculated progress.

        Args:
            milestone_id: UUID of the milestone
            user_id: UUID of user making the request

        Returns:
            Dictionary with milestone data and statistics

        Raises:
            MilestoneNotFoundError: If milestone not found
            InsufficientMilestonePermissionsError: If user lacks permissions
        """
        # Get milestone with permission check
        milestone = await self.get_milestone(milestone_id, user_id)

        # Get task statistics
        task_stats = await self.repository.count_milestone_tasks(milestone_id)
        total_tasks = sum(task_stats.values())
        completed_tasks = task_stats.get("done", 0)

        # Calculate auto progress
        auto_progress = await self.repository.calculate_progress(milestone_id)

        return {
            "milestone": milestone,
            "task_stats": task_stats,
            "total_tasks": total_tasks,
            "completed_tasks": completed_tasks,
            "auto_progress": auto_progress,
        }

    async def get_project_roadmap(
        self,
        project_id: UUID,
        user_id: UUID,
    ) -> list[Milestone]:
        """
        Get project roadmap (all milestones ordered).

        Perfect for roadmap/timeline visualization.

        Args:
            project_id: UUID of the project
            user_id: UUID of user making the request

        Returns:
            List of Milestone objects ordered by order/dates

        Raises:
            InsufficientMilestonePermissionsError: If user lacks permissions
        """
        return await self.get_project_milestones(
            project_id,
            user_id,
            skip=0,
            limit=1000,  # Get all for roadmap view
        )

    async def get_upcoming_milestones(
        self,
        project_id: UUID,
        user_id: UUID,
        days: int = 30,
    ) -> list[Milestone]:
        """
        Get milestones due within N days.

        Args:
            project_id: UUID of the project
            user_id: UUID of user making the request
            days: Number of days to look ahead (default: 30)

        Returns:
            List of upcoming Milestone objects

        Raises:
            InsufficientMilestonePermissionsError: If user lacks permissions
        """
        # Check permissions
        if not await self.project_service.check_permission(project_id, user_id, "member"):
            logger.warning(
                f"User {user_id} lacks permission to view milestones for project {project_id}"
            )
            raise InsufficientMilestonePermissionsError("Only project members can view milestones")

        return await self.repository.get_upcoming_milestones(project_id, days)
