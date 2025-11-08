"""
Task service for business logic.

This module provides the business logic layer for tasks, handling:
- Permission checks
- Status transition validation
- Circular dependency detection
- Activity logging
- OpenSpec integration
- Git commit linking
"""

import json
import logging
from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from ardha.repositories.task_repository import TaskRepository
from ardha.services.project_service import ProjectService

logger = logging.getLogger(__name__)


# ============= Custom Exceptions =============


class TaskNotFoundError(Exception):
    """Raised when a task is not found."""
    pass


class CircularDependencyError(Exception):
    """Raised when a circular dependency is detected."""
    pass


class InvalidStatusTransitionError(Exception):
    """Raised when an invalid status transition is attempted."""
    pass


class InsufficientTaskPermissionsError(Exception):
    """Raised when user lacks permissions for task operation."""
    pass


# ============= Status Transition Rules =============

VALID_TRANSITIONS = {
    "todo": ["in_progress", "cancelled"],
    "in_progress": ["in_review", "todo", "cancelled"],
    "in_review": ["done", "in_progress", "cancelled"],
    "done": ["in_review"],  # Can reopen
    "cancelled": ["todo"],  # Can uncancel
}


class TaskService:
    """
    Service layer for task business logic.
    
    Handles:
    - Permission-based access control
    - Status transition validation
    - Circular dependency detection
    - Activity logging for all mutations
    - OpenSpec integration
    - Git commit linking
    """
    
    def __init__(self, db: AsyncSession):
        """
        Initialize task service.
        
        Args:
            db: Async SQLAlchemy database session
        """
        self.db = db
        self.repository = TaskRepository(db)
        self.project_service = ProjectService(db)
    
    # ============= Core Task Operations =============
    
    async def create_task(
        self,
        project_id: UUID,
        task_data: dict[str, Any],
        created_by_id: UUID,
    ) -> Any:  # Returns Task
        """
        Create a new task with activity logging.
        
        Args:
            project_id: Project UUID
            task_data: Task creation data
            created_by_id: User creating the task
            
        Returns:
            Created task
            
        Raises:
            InsufficientTaskPermissionsError: If user lacks permissions
        """
        # Check project permissions (must be at least member)
        if not await self.project_service.check_permission(
            project_id=project_id,
            user_id=created_by_id,
            required_role="member",
        ):
            raise InsufficientTaskPermissionsError(
                "Must be at least a project member to create tasks"
            )
        
        # Prepare task data
        task_create_data = {
            "project_id": project_id,
            "created_by_id": created_by_id,
            **task_data,
        }
        
        # Create task
        task = await self.repository.create(task_create_data)
        
        # Log creation activity
        await self.repository.log_activity(
            task_id=task.id,
            user_id=created_by_id,
            action="created",
            new_value=json.dumps({
                "title": task.title,
                "status": task.status,
                "priority": task.priority,
            }),
        )
        
        logger.info(f"Created task {task.identifier} by user {created_by_id}")
        return task
    
    async def get_task(self, task_id: UUID, user_id: UUID) -> Any:  # Returns Task
        """
        Get task by ID with permission check.
        
        Args:
            task_id: Task UUID
            user_id: User requesting task
            
        Returns:
            Task if found and user has permission
            
        Raises:
            TaskNotFoundError: If task not found
            InsufficientTaskPermissionsError: If user lacks permissions
        """
        task = await self.repository.get_by_id(task_id)
        if not task:
            raise TaskNotFoundError(f"Task {task_id} not found")
        
        # Check project access
        if not await self.project_service.check_permission(
            project_id=task.project_id,
            user_id=user_id,
            required_role="viewer",
        ):
            raise InsufficientTaskPermissionsError(
                "Must be a project member to view tasks"
            )
        
        return task
    
    async def get_project_tasks(
        self,
        project_id: UUID,
        user_id: UUID,
        filters: dict[str, Any],
        skip: int = 0,
        limit: int = 100,
    ) -> tuple[list, int]:
        """
        Get filtered project tasks with permission check.
        
        Args:
            project_id: Project UUID
            user_id: User requesting tasks
            filters: Filter criteria
            skip: Pagination offset
            limit: Page size
            
        Returns:
            Tuple of (tasks list, total count)
            
        Raises:
            InsufficientTaskPermissionsError: If user lacks permissions
        """
        # Check project access
        if not await self.project_service.check_permission(
            project_id=project_id,
            user_id=user_id,
            required_role="viewer",
        ):
            raise InsufficientTaskPermissionsError(
                "Must be a project member to view tasks"
            )
        
        # Get tasks
        tasks = await self.repository.get_project_tasks(
            project_id=project_id,
            filters=filters,
            skip=skip,
            limit=limit,
        )
        
        # Get total count
        total = await self.repository.count_tasks(project_id, filters)
        
        return tasks, total
    
    async def update_task(
        self,
        task_id: UUID,
        user_id: UUID,
        update_data: dict[str, Any],
    ) -> Any:  # Returns Task
        """
        Update task with permission check and activity logging.
        
        Args:
            task_id: Task UUID
            user_id: User updating task
            update_data: Fields to update
            
        Returns:
            Updated task
            
        Raises:
            TaskNotFoundError: If task not found
            InsufficientTaskPermissionsError: If user lacks permissions
        """
        task = await self.repository.get_by_id(task_id)
        if not task:
            raise TaskNotFoundError(f"Task {task_id} not found")
        
        # Check project permissions (must be at least member)
        if not await self.project_service.check_permission(
            project_id=task.project_id,
            user_id=user_id,
            required_role="member",
        ):
            raise InsufficientTaskPermissionsError(
                "Must be at least a project member to update tasks"
            )
        
        # Track changes for activity log
        changes = {}
        for key, new_value in update_data.items():
            if hasattr(task, key):
                old_value = getattr(task, key)
                if old_value != new_value:
                    changes[key] = {"old": old_value, "new": new_value}
        
        # Update task
        task = await self.repository.update(task_id, **update_data)
        
        # Log activities for each change
        for field, values in changes.items():
            await self.repository.log_activity(
                task_id=task_id,
                user_id=user_id,
                action=f"{field}_changed",
                old_value=str(values["old"]),
                new_value=str(values["new"]),
            )
        
        logger.info(f"Updated task {task.identifier}: {list(changes.keys())}")
        return task
    
    async def delete_task(self, task_id: UUID, user_id: UUID) -> bool:
        """
        Delete task with permission check.
        
        Args:
            task_id: Task UUID
            user_id: User deleting task
            
        Returns:
            True if deleted
            
        Raises:
            TaskNotFoundError: If task not found
            InsufficientTaskPermissionsError: If user lacks permissions
        """
        task = await self.repository.get_by_id(task_id)
        if not task:
            raise TaskNotFoundError(f"Task {task_id} not found")
        
        # Check project permissions (must be at least admin)
        if not await self.project_service.check_permission(
            project_id=task.project_id,
            user_id=user_id,
            required_role="admin",
        ):
            raise InsufficientTaskPermissionsError(
                "Must be project admin or owner to delete tasks"
            )
        
        # Delete task
        success = await self.repository.delete(task_id)
        
        if success:
            logger.info(f"Deleted task {task.identifier} by user {user_id}")
        
        return success
    
    async def update_status(
        self,
        task_id: UUID,
        user_id: UUID,
        new_status: str,
    ) -> Any:  # Returns Task
        """
        Update task status with transition validation and logging.
        
        Args:
            task_id: Task UUID
            user_id: User updating status
            new_status: New status value
            
        Returns:
            Updated task
            
        Raises:
            TaskNotFoundError: If task not found
            InvalidStatusTransitionError: If transition is invalid
            InsufficientTaskPermissionsError: If user lacks permissions
        """
        task = await self.repository.get_by_id(task_id)
        if not task:
            raise TaskNotFoundError(f"Task {task_id} not found")
        
        # Check project permissions
        if not await self.project_service.check_permission(
            project_id=task.project_id,
            user_id=user_id,
            required_role="member",
        ):
            raise InsufficientTaskPermissionsError(
                "Must be at least a project member to update status"
            )
        
        # Validate status transition
        old_status = task.status
        valid_next_statuses = VALID_TRANSITIONS.get(old_status, [])
        
        if new_status not in valid_next_statuses:
            raise InvalidStatusTransitionError(
                f"Invalid transition: {old_status} → {new_status}. "
                f"Valid transitions: {', '.join(valid_next_statuses)}"
            )
        
        # Update status (repository handles timestamps)
        task = await self.repository.update_status(task_id, new_status)
        
        # Log activity
        await self.repository.log_activity(
            task_id=task_id,
            user_id=user_id,
            action="status_changed",
            old_value=old_status,
            new_value=new_status,
        )
        
        logger.info(f"Task {task.identifier} status: {old_status} → {new_status}")
        return task
    
    async def assign_task(
        self,
        task_id: UUID,
        user_id: UUID,
        assignee_id: UUID,
    ) -> Any:  # Returns Task
        """
        Assign task to a user.
        
        Args:
            task_id: Task UUID
            user_id: User performing assignment
            assignee_id: User to assign task to
            
        Returns:
            Updated task
            
        Raises:
            TaskNotFoundError: If task not found
            InsufficientTaskPermissionsError: If user lacks permissions
        """
        task = await self.repository.get_by_id(task_id)
        if not task:
            raise TaskNotFoundError(f"Task {task_id} not found")
        
        # Check project permissions
        if not await self.project_service.check_permission(
            project_id=task.project_id,
            user_id=user_id,
            required_role="member",
        ):
            raise InsufficientTaskPermissionsError(
                "Must be at least a project member to assign tasks"
            )
        
        # Verify assignee is project member
        if not await self.project_service.check_permission(
            project_id=task.project_id,
            user_id=assignee_id,
            required_role="viewer",
        ):
            raise InsufficientTaskPermissionsError(
                "Assignee must be a project member"
            )
        
        # Assign task
        task = await self.repository.assign_user(task_id, assignee_id)
        
        # Log activity
        await self.repository.log_activity(
            task_id=task_id,
            user_id=user_id,
            action="assigned",
            new_value=str(assignee_id),
        )
        
        logger.info(f"Assigned task {task.identifier} to user {assignee_id}")
        return task
    
    async def unassign_task(self, task_id: UUID, user_id: UUID) -> Any:  # Returns Task
        """
        Remove assignee from task.
        
        Args:
            task_id: Task UUID
            user_id: User performing unassignment
            
        Returns:
            Updated task
            
        Raises:
            TaskNotFoundError: If task not found
            InsufficientTaskPermissionsError: If user lacks permissions
        """
        task = await self.repository.get_by_id(task_id)
        if not task:
            raise TaskNotFoundError(f"Task {task_id} not found")
        
        # Check project permissions
        if not await self.project_service.check_permission(
            project_id=task.project_id,
            user_id=user_id,
            required_role="member",
        ):
            raise InsufficientTaskPermissionsError(
                "Must be at least a project member to unassign tasks"
            )
        
        old_assignee = task.assignee_id
        task = await self.repository.unassign_user(task_id)
        
        # Log activity
        await self.repository.log_activity(
            task_id=task_id,
            user_id=user_id,
            action="unassigned",
            old_value=str(old_assignee) if old_assignee else None,
        )
        
        logger.info(f"Unassigned task {task.identifier}")
        return task
    
    # ============= Dependency Management =============
    
    async def add_dependency(
        self,
        task_id: UUID,
        user_id: UUID,
        depends_on_task_id: UUID,
    ) -> Any:  # Returns TaskDependency
        """
        Add task dependency with circular detection.
        
        Args:
            task_id: Task that will depend on another
            user_id: User adding dependency
            depends_on_task_id: Task to depend on
            
        Returns:
            Created dependency
            
        Raises:
            TaskNotFoundError: If either task not found
            CircularDependencyError: If would create circular dependency
            InsufficientTaskPermissionsError: If user lacks permissions
        """
        task = await self.repository.get_by_id(task_id)
        depends_on_task = await self.repository.get_by_id(depends_on_task_id)
        
        if not task or not depends_on_task:
            raise TaskNotFoundError("One or both tasks not found")
        
        # Must be same project
        if task.project_id != depends_on_task.project_id:
            raise ValueError("Tasks must be in the same project")
        
        # Check permissions
        if not await self.project_service.check_permission(
            project_id=task.project_id,
            user_id=user_id,
            required_role="member",
        ):
            raise InsufficientTaskPermissionsError(
                "Must be at least a project member to add dependencies"
            )
        
        # Check for circular dependency
        if await self.check_circular_dependency(task_id, depends_on_task_id):
            raise CircularDependencyError(
                f"Adding dependency would create circular dependency"
            )
        
        # Add dependency
        dependency = await self.repository.add_dependency(task_id, depends_on_task_id)
        
        # Log activity
        await self.repository.log_activity(
            task_id=task_id,
            user_id=user_id,
            action="dependency_added",
            new_value=depends_on_task.identifier,
        )
        
        logger.info(f"Added dependency: {task.identifier} depends on {depends_on_task.identifier}")
        return dependency
    
    async def remove_dependency(
        self,
        task_id: UUID,
        user_id: UUID,
        depends_on_task_id: UUID,
    ) -> bool:
        """
        Remove task dependency.
        
        Args:
            task_id: Task with dependency
            user_id: User removing dependency
            depends_on_task_id: Dependency to remove
            
        Returns:
            True if removed
            
        Raises:
            TaskNotFoundError: If task not found
            InsufficientTaskPermissionsError: If user lacks permissions
        """
        task = await self.repository.get_by_id(task_id)
        if not task:
            raise TaskNotFoundError(f"Task {task_id} not found")
        
        # Check permissions
        if not await self.project_service.check_permission(
            project_id=task.project_id,
            user_id=user_id,
            required_role="member",
        ):
            raise InsufficientTaskPermissionsError(
                "Must be at least a project member to remove dependencies"
            )
        
        # Remove dependency
        success = await self.repository.remove_dependency(task_id, depends_on_task_id)
        
        if success:
            # Log activity
            depends_on_task = await self.repository.get_by_id(depends_on_task_id)
            await self.repository.log_activity(
                task_id=task_id,
                user_id=user_id,
                action="dependency_removed",
                old_value=depends_on_task.identifier if depends_on_task else str(depends_on_task_id),
            )
            
            logger.info(f"Removed dependency from task {task.identifier}")
        
        return success
    
    async def check_circular_dependency(
        self,
        task_id: UUID,
        depends_on_task_id: UUID,
    ) -> bool:
        """
        Check if adding dependency would create circular dependency.
        
        Uses graph traversal to detect cycles.
        
        Args:
            task_id: Task that would depend on another
            depends_on_task_id: Task to depend on
            
        Returns:
            True if circular dependency would occur
        """
        # Self-dependency check
        if task_id == depends_on_task_id:
            return True
        
        # BFS to check if depends_on_task already depends on task (directly or indirectly)
        visited = set()
        queue = [depends_on_task_id]
        
        while queue:
            current_task_id = queue.pop(0)
            
            if current_task_id == task_id:
                # Found cycle: depends_on_task → ... → task
                return True
            
            if current_task_id in visited:
                continue
            
            visited.add(current_task_id)
            
            # Get dependencies of current task
            dependencies = await self.repository.get_dependencies(current_task_id)
            for dep in dependencies:
                if dep.id not in visited:
                    queue.append(dep.id)
        
        return False
    
    # ============= Tag Management =============
    
    async def add_tag_to_task(
        self,
        task_id: UUID,
        user_id: UUID,
        tag_name: str,
        color: str = "#6366f1",
    ) -> Any:  # Returns Task
        """
        Add tag to task (creates tag if doesn't exist).
        
        Args:
            task_id: Task UUID
            user_id: User adding tag
            tag_name: Tag name
            color: Tag color (default: purple)
            
        Returns:
            Updated task
            
        Raises:
            TaskNotFoundError: If task not found
            InsufficientTaskPermissionsError: If user lacks permissions
        """
        task = await self.repository.get_by_id(task_id)
        if not task:
            raise TaskNotFoundError(f"Task {task_id} not found")
        
        # Check permissions
        if not await self.project_service.check_permission(
            project_id=task.project_id,
            user_id=user_id,
            required_role="member",
        ):
            raise InsufficientTaskPermissionsError(
                "Must be at least a project member to add tags"
            )
        
        # Get or create tag
        tag = await self.repository.get_or_create_tag(
            project_id=task.project_id,
            name=tag_name,
            color=color,
        )
        
        # Add tag to task
        await self.repository.add_tag(task_id, tag.id)
        
        # Log activity
        await self.repository.log_activity(
            task_id=task_id,
            user_id=user_id,
            action="tag_added",
            new_value=tag_name,
        )
        
        # Refresh task
        task = await self.repository.get_by_id(task_id)
        if not task:
            raise TaskNotFoundError(f"Task {task_id} not found after refresh")
        
        logger.info(f"Added tag '{tag_name}' to task {task.identifier}")
        return task
    
    async def remove_tag_from_task(
        self,
        task_id: UUID,
        user_id: UUID,
        tag_id: UUID,
    ) -> Any:  # Returns Task
        """
        Remove tag from task.
        
        Args:
            task_id: Task UUID
            user_id: User removing tag
            tag_id: Tag UUID
            
        Returns:
            Updated task
            
        Raises:
            TaskNotFoundError: If task not found
            InsufficientTaskPermissionsError: If user lacks permissions
        """
        task = await self.repository.get_by_id(task_id)
        if not task:
            raise TaskNotFoundError(f"Task {task_id} not found")
        
        # Check permissions
        if not await self.project_service.check_permission(
            project_id=task.project_id,
            user_id=user_id,
            required_role="member",
        ):
            raise InsufficientTaskPermissionsError(
                "Must be at least a project member to remove tags"
            )
        
        # Get tag for logging
        tags = await self.repository.get_task_tags(task_id)
        tag_name = next((t.name for t in tags if t.id == tag_id), None)
        
        # Remove tag
        success = await self.repository.remove_tag(task_id, tag_id)
        
        if success and tag_name:
            # Log activity
            await self.repository.log_activity(
                task_id=task_id,
                user_id=user_id,
                action="tag_removed",
                old_value=tag_name,
            )
            
            logger.info(f"Removed tag '{tag_name}' from task {task.identifier}")
        
        # Refresh task
        task = await self.repository.get_by_id(task_id)
        return task
    
    # ============= OpenSpec Integration =============
    
    async def link_openspec_proposal(
        self,
        task_id: UUID,
        proposal_id: UUID,
    ) -> Any:  # Returns Task
        """
        Link task to OpenSpec proposal.
        
        Args:
            task_id: Task UUID
            proposal_id: OpenSpec proposal UUID
            
        Returns:
            Updated task
        """
        task = await self.repository.update(
            task_id=task_id,
            openspec_proposal_id=proposal_id,
        )
        
        # Log activity
        await self.repository.log_activity(
            task_id=task_id,
            user_id=None,  # System action
            action="openspec_linked",
            new_value=str(proposal_id),
        )
        
        logger.info(f"Linked task {task.identifier} to OpenSpec proposal {proposal_id}")
        return task
    
    async def sync_task_from_openspec(
        self,
        openspec_change_path: str,
        project_id: UUID,
    ) -> Any:  # Returns Task
        """
        Create or update task from OpenSpec change proposal.
        
        This would parse openspec/changes/xxx/tasks.md and create/update tasks.
        
        Args:
            openspec_change_path: Path to OpenSpec change directory
            project_id: Project UUID
            
        Returns:
            Updated or created task
            
        Note:
            This is a placeholder for future OpenSpec integration.
            Would need to parse markdown files and extract task information.
        """
        # TODO: Implement OpenSpec parsing
        # - Read tasks.md from openspec_change_path
        # - Parse task definitions
        # - Create or update tasks
        # - Link to proposal
        
        logger.warning("OpenSpec sync not yet implemented")
        raise NotImplementedError("OpenSpec sync will be implemented in Phase 3")
    
    # ============= Git Integration =============
    
    async def link_git_commit(
        self,
        task_id: UUID,
        commit_sha: str,
        auto_status: bool = True,
    ) -> Any:  # Returns Task
        """
        Link git commit to task and optionally update status.
        
        Args:
            task_id: Task UUID
            commit_sha: Git commit SHA
            auto_status: Whether to auto-update status to in_progress
            
        Returns:
            Updated task
        """
        task = await self.repository.get_by_id(task_id)
        if not task:
            raise TaskNotFoundError(f"Task {task_id} not found")
        
        # Add commit to related_commits array
        related_commits = task.related_commits or []
        if commit_sha not in related_commits:
            related_commits.append(commit_sha)
            
            task = await self.repository.update(
                task_id=task_id,
                related_commits=related_commits,
            )
            
            # Optionally update status
            if auto_status and task.status == "todo":
                task = await self.repository.update_status(task_id, "in_progress")
            
            # Log activity
            await self.repository.log_activity(
                task_id=task_id,
                user_id=None,  # System/Git action
                action="git_commit_linked",
                new_value=commit_sha[:8],  # Short SHA
            )
            
            logger.info(f"Linked commit {commit_sha[:8]} to task {task.identifier}")
        
        return task
    
    async def get_member_count(self, task_id: UUID) -> int:
        """
        Get count of users involved with task (creator + assignee).
        
        Args:
            task_id: Task UUID
            
        Returns:
            Count of unique users
        """
        task = await self.repository.get_by_id(task_id)
        if not task:
            return 0
        
        unique_users = {task.created_by_id}
        if task.assignee_id:
            unique_users.add(task.assignee_id)
        
        return len(unique_users)