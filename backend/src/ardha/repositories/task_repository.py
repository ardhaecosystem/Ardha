"""
Task repository for data access operations.

This module provides the data access layer for tasks, handling all
database queries and CRUD operations for tasks, dependencies, tags, and activities.
"""

import logging
from datetime import datetime, timedelta
from typing import Any
from uuid import UUID

from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ardha.models.project import Project
from ardha.models.task import Task
from ardha.models.task_activity import TaskActivity
from ardha.models.task_dependency import TaskDependency
from ardha.models.task_tag import TaskTag

logger = logging.getLogger(__name__)


class TaskRepository:
    """
    Repository for task-related database operations.
    
    Handles:
    - CRUD operations for tasks
    - Dependency management
    - Tag management
    - Activity logging
    - Complex querying and filtering
    """
    
    def __init__(self, db: AsyncSession):
        """
        Initialize task repository.
        
        Args:
            db: Async SQLAlchemy database session
        """
        self.db = db
    
    # ============= Core CRUD Operations =============
    
    async def get_by_id(self, task_id: UUID) -> Task | None:
        """
        Get task by ID with eager loaded relationships.
        
        Args:
            task_id: Task UUID
            
        Returns:
            Task if found, None otherwise
        """
        stmt = (
            select(Task)
            .where(Task.id == task_id)
            .options(
                selectinload(Task.assignee),
                selectinload(Task.created_by),
                selectinload(Task.tags),
                selectinload(Task.dependencies),
                selectinload(Task.blocking),
            )
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()
    
    async def get_by_identifier(self, project_id: UUID, identifier: str) -> Task | None:
        """
        Get task by project-specific identifier (e.g., "ARD-001").
        
        Args:
            project_id: Project UUID
            identifier: Task identifier string
            
        Returns:
            Task if found, None otherwise
        """
        stmt = (
            select(Task)
            .where(and_(Task.project_id == project_id, Task.identifier == identifier))
            .options(
                selectinload(Task.assignee),
                selectinload(Task.created_by),
                selectinload(Task.tags),
                selectinload(Task.dependencies),
                selectinload(Task.blocking),
            )
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()
    
    async def get_project_tasks(
        self,
        project_id: UUID,
        filters: dict[str, Any],
        skip: int = 0,
        limit: int = 100,
    ) -> list[Task]:
        """
        Get filtered and paginated tasks for a project.
        
        Args:
            project_id: Project UUID
            filters: Dictionary of filter criteria (status, assignee_id, priority, etc.)
            skip: Number of records to skip (pagination)
            limit: Maximum number of records to return
            
        Returns:
            List of tasks matching criteria
        """
        stmt = select(Task).where(Task.project_id == project_id)
        
        # Apply filters
        if filters.get("status"):
            if isinstance(filters["status"], list):
                stmt = stmt.where(Task.status.in_(filters["status"]))
            else:
                stmt = stmt.where(Task.status == filters["status"])
        
        if filters.get("assignee_id"):
            stmt = stmt.where(Task.assignee_id == filters["assignee_id"])
        
        if filters.get("priority"):
            if isinstance(filters["priority"], list):
                stmt = stmt.where(Task.priority.in_(filters["priority"]))
            else:
                stmt = stmt.where(Task.priority == filters["priority"])
        
        if filters.get("milestone_id"):
            stmt = stmt.where(Task.milestone_id == filters["milestone_id"])
        
        if filters.get("has_due_date") is not None:
            if filters["has_due_date"]:
                stmt = stmt.where(Task.due_date.isnot(None))
            else:
                stmt = stmt.where(Task.due_date.is_(None))
        
        if filters.get("overdue_only"):
            stmt = stmt.where(
                and_(
                    Task.due_date.isnot(None),
                    Task.due_date < datetime.utcnow(),
                    Task.status.notin_(["done", "cancelled"]),
                )
            )
        
        if filters.get("search"):
            search_term = f"%{filters['search']}%"
            stmt = stmt.where(
                or_(
                    Task.title.ilike(search_term),
                    Task.description.ilike(search_term),
                    Task.identifier.ilike(search_term),
                )
            )
        
        # Sorting
        sort_by = filters.get("sort_by", "created_at")
        sort_order = filters.get("sort_order", "desc")
        
        if sort_by == "created_at":
            stmt = stmt.order_by(Task.created_at.desc() if sort_order == "desc" else Task.created_at.asc())
        elif sort_by == "due_date":
            stmt = stmt.order_by(Task.due_date.desc() if sort_order == "desc" else Task.due_date.asc())
        elif sort_by == "priority":
            stmt = stmt.order_by(Task.priority.asc() if sort_order == "asc" else Task.priority.desc())
        elif sort_by == "status":
            stmt = stmt.order_by(Task.status.asc() if sort_order == "asc" else Task.status.desc())
        
        # Pagination
        stmt = stmt.offset(skip).limit(limit)
        
        # Eager load relationships
        stmt = stmt.options(
            selectinload(Task.assignee),
            selectinload(Task.created_by),
            selectinload(Task.tags),
        )
        
        result = await self.db.execute(stmt)
        return list(result.scalars().all())
    
    async def create(self, task_data: dict[str, Any]) -> Task:
        """
        Create a new task with auto-generated identifier.
        
        Args:
            task_data: Dictionary of task attributes
            
        Returns:
            Created task instance
        """
        # Generate unique identifier
        identifier = await self._generate_identifier(task_data["project_id"])
        
        # Create task
        task = Task(
            identifier=identifier,
            **task_data
        )
        
        self.db.add(task)
        await self.db.flush()
        await self.db.refresh(task)
        
        logger.info(f"Created task {task.identifier} in project {task.project_id}")
        return task
    
    async def update(self, task_id: UUID, **kwargs) -> Task:
        """
        Update task fields.
        
        Args:
            task_id: Task UUID
            **kwargs: Fields to update
            
        Returns:
            Updated task instance
        """
        task = await self.db.get(Task, task_id)
        if not task:
            raise ValueError(f"Task {task_id} not found")
        
        for key, value in kwargs.items():
            if hasattr(task, key):
                setattr(task, key, value)
        
        await self.db.flush()
        await self.db.refresh(task)
        
        logger.info(f"Updated task {task.identifier}: {list(kwargs.keys())}")
        return task
    
    async def delete(self, task_id: UUID) -> bool:
        """
        Delete a task (hard delete).
        
        Args:
            task_id: Task UUID
            
        Returns:
            True if deleted, False if not found
        """
        task = await self.db.get(Task, task_id)
        if not task:
            return False
        
        identifier = task.identifier
        await self.db.delete(task)
        await self.db.flush()
        
        logger.info(f"Deleted task {identifier}")
        return True
    
    async def update_status(self, task_id: UUID, status: str) -> Task:
        """
        Update task status and related timestamps.
        
        Args:
            task_id: Task UUID
            status: New status value
            
        Returns:
            Updated task instance
        """
        task = await self.db.get(Task, task_id)
        if not task:
            raise ValueError(f"Task {task_id} not found")
        
        old_status = task.status
        task.status = status
        
        # Update timestamps based on status
        if status == "in_progress" and old_status == "todo":
            task.started_at = datetime.utcnow()
        elif status == "done" and old_status != "done":
            task.completed_at = datetime.utcnow()
        elif status == "todo" and old_status == "done":
            # Reopening task
            task.completed_at = None
            task.started_at = None
        
        await self.db.flush()
        await self.db.refresh(task)
        
        logger.info(f"Task {task.identifier} status: {old_status} → {status}")
        return task
    
    async def assign_user(self, task_id: UUID, user_id: UUID) -> Task:
        """
        Assign task to a user.
        
        Args:
            task_id: Task UUID
            user_id: User UUID
            
        Returns:
            Updated task instance
        """
        task = await self.db.get(Task, task_id)
        if not task:
            raise ValueError(f"Task {task_id} not found")
        
        task.assignee_id = user_id
        await self.db.flush()
        await self.db.refresh(task)
        
        logger.info(f"Assigned task {task.identifier} to user {user_id}")
        return task
    
    async def unassign_user(self, task_id: UUID) -> Task:
        """
        Remove assignee from task.
        
        Args:
            task_id: Task UUID
            
        Returns:
            Updated task instance
        """
        task = await self.db.get(Task, task_id)
        if not task:
            raise ValueError(f"Task {task_id} not found")
        
        task.assignee_id = None
        await self.db.flush()
        await self.db.refresh(task)
        
        logger.info(f"Unassigned task {task.identifier}")
        return task
    
    # ============= Dependency Management =============
    
    async def add_dependency(
        self,
        task_id: UUID,
        depends_on_task_id: UUID,
    ) -> TaskDependency:
        """
        Add a dependency between tasks.
        
        Args:
            task_id: Task that depends on another
            depends_on_task_id: Task that must be completed first
            
        Returns:
            Created dependency instance
        """
        dependency = TaskDependency(
            task_id=task_id,
            depends_on_task_id=depends_on_task_id,
            dependency_type="depends_on",
        )
        
        self.db.add(dependency)
        await self.db.flush()
        await self.db.refresh(dependency)
        
        logger.info(f"Added dependency: {task_id} depends on {depends_on_task_id}")
        return dependency
    
    async def remove_dependency(
        self,
        task_id: UUID,
        depends_on_task_id: UUID,
    ) -> bool:
        """
        Remove a dependency between tasks.
        
        Args:
            task_id: Task with dependency
            depends_on_task_id: Task dependency to remove
            
        Returns:
            True if removed, False if not found
        """
        stmt = select(TaskDependency).where(
            and_(
                TaskDependency.task_id == task_id,
                TaskDependency.depends_on_task_id == depends_on_task_id,
            )
        )
        result = await self.db.execute(stmt)
        dependency = result.scalar_one_or_none()
        
        if not dependency:
            return False
        
        await self.db.delete(dependency)
        await self.db.flush()
        
        logger.info(f"Removed dependency: {task_id} depends on {depends_on_task_id}")
        return True
    
    async def get_dependencies(self, task_id: UUID) -> list[Task]:
        """
        Get all tasks that this task depends on.
        
        Args:
            task_id: Task UUID
            
        Returns:
            List of tasks this task depends on
        """
        stmt = (
            select(Task)
            .join(TaskDependency, TaskDependency.depends_on_task_id == Task.id)
            .where(TaskDependency.task_id == task_id)
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())
    
    async def get_blocking_tasks(self, task_id: UUID) -> list[Task]:
        """
        Get all tasks that are blocked by this task.
        
        Args:
            task_id: Task UUID
            
        Returns:
            List of tasks blocked by this task
        """
        stmt = (
            select(Task)
            .join(TaskDependency, TaskDependency.task_id == Task.id)
            .where(TaskDependency.depends_on_task_id == task_id)
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())
    
    # ============= Tag Management =============
    
    async def add_tag(self, task_id: UUID, tag_id: UUID) -> None:
        """
        Add a tag to a task.
        
        Args:
            task_id: Task UUID
            tag_id: Tag UUID
        """
        task = await self.db.get(Task, task_id)
        tag = await self.db.get(TaskTag, tag_id)
        
        if not task or not tag:
            raise ValueError("Task or tag not found")
        
        if tag not in task.tags:
            task.tags.append(tag)
            await self.db.flush()
            logger.info(f"Added tag {tag.name} to task {task.identifier}")
    
    async def remove_tag(self, task_id: UUID, tag_id: UUID) -> bool:
        """
        Remove a tag from a task.
        
        Args:
            task_id: Task UUID
            tag_id: Tag UUID
            
        Returns:
            True if removed, False if not found
        """
        task = await self.db.get(Task, task_id)
        tag = await self.db.get(TaskTag, tag_id)
        
        if not task or not tag:
            return False
        
        if tag in task.tags:
            task.tags.remove(tag)
            await self.db.flush()
            logger.info(f"Removed tag {tag.name} from task {task.identifier}")
            return True
        
        return False
    
    async def get_task_tags(self, task_id: UUID) -> list[TaskTag]:
        """
        Get all tags for a task.
        
        Args:
            task_id: Task UUID
            
        Returns:
            List of tags
        """
        stmt = select(Task).where(Task.id == task_id).options(selectinload(Task.tags))
        result = await self.db.execute(stmt)
        task = result.scalar_one_or_none()
        
        return task.tags if task else []
    
    async def get_or_create_tag(
        self,
        project_id: UUID,
        name: str,
        color: str = "#6366f1",
    ) -> TaskTag:
        """
        Get existing tag or create a new one.
        
        Args:
            project_id: Project UUID
            name: Tag name
            color: Hex color code (default: purple)
            
        Returns:
            Tag instance (existing or new)
        """
        # Try to find existing tag
        stmt = select(TaskTag).where(
            and_(TaskTag.project_id == project_id, TaskTag.name == name)
        )
        result = await self.db.execute(stmt)
        tag = result.scalar_one_or_none()
        
        if tag:
            return tag
        
        # Create new tag
        tag = TaskTag(
            project_id=project_id,
            name=name,
            color=color,
        )
        self.db.add(tag)
        await self.db.flush()
        await self.db.refresh(tag)
        
        logger.info(f"Created tag {name} for project {project_id}")
        return tag
    
    # ============= Activity Logging =============
    
    async def log_activity(
        self,
        task_id: UUID,
        user_id: UUID | None,
        action: str,
        old_value: str | None = None,
        new_value: str | None = None,
        comment: str | None = None,
    ) -> TaskActivity:
        """
        Log an activity/change to a task.
        
        Args:
            task_id: Task UUID
            user_id: User who performed action (None if AI)
            action: Action type (e.g., 'status_changed', 'assigned')
            old_value: Previous value (JSON string)
            new_value: New value (JSON string)
            comment: Optional user comment
            
        Returns:
            Created activity instance
        """
        activity = TaskActivity(
            task_id=task_id,
            user_id=user_id,
            action=action,
            old_value=old_value,
            new_value=new_value,
            comment=comment,
        )
        
        self.db.add(activity)
        await self.db.flush()
        await self.db.refresh(activity)
        
        logger.debug(f"Logged activity for task {task_id}: {action}")
        return activity
    
    async def get_task_activities(
        self,
        task_id: UUID,
        limit: int = 50,
    ) -> list[TaskActivity]:
        """
        Get activity log for a task.
        
        Args:
            task_id: Task UUID
            limit: Maximum number of activities to return
            
        Returns:
            List of activities (newest first)
        """
        stmt = (
            select(TaskActivity)
            .where(TaskActivity.task_id == task_id)
            .order_by(TaskActivity.created_at.desc())
            .limit(limit)
            .options(selectinload(TaskActivity.user))
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())
    
    # ============= Querying & Filtering =============
    
    async def count_by_status(self, project_id: UUID) -> dict[str, int]:
        """
        Count tasks by status for a project.
        
        Args:
            project_id: Project UUID
            
        Returns:
            Dictionary mapping status to count
        """
        stmt = (
            select(Task.status, func.count(Task.id))
            .where(Task.project_id == project_id)
            .group_by(Task.status)
        )
        result = await self.db.execute(stmt)
        
        counts = {status: count for status, count in result.all()}
        
        # Ensure all statuses are present
        for status in ["todo", "in_progress", "in_review", "done", "cancelled"]:
            counts.setdefault(status, 0)
        
        return counts
    
    async def get_upcoming_tasks(
        self,
        project_id: UUID,
        days: int = 7,
    ) -> list[Task]:
        """
        Get tasks due within the next N days.
        
        Args:
            project_id: Project UUID
            days: Number of days to look ahead
            
        Returns:
            List of tasks due soon
        """
        cutoff_date = datetime.utcnow() + timedelta(days=days)
        
        stmt = (
            select(Task)
            .where(
                and_(
                    Task.project_id == project_id,
                    Task.due_date.isnot(None),
                    Task.due_date <= cutoff_date,
                    Task.status.notin_(["done", "cancelled"]),
                )
            )
            .order_by(Task.due_date.asc())
            .options(selectinload(Task.assignee))
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())
    
    async def get_blocked_tasks(self, project_id: UUID) -> list[Task]:
        """
        Get tasks that are blocked by incomplete dependencies.
        
        Args:
            project_id: Project UUID
            
        Returns:
            List of blocked tasks
        """
        # Subquery: task IDs with incomplete dependencies
        incomplete_deps_subq = (
            select(TaskDependency.task_id)
            .join(Task, TaskDependency.depends_on_task_id == Task.id)
            .where(Task.status != "done")
        ).scalar_subquery()
        
        stmt = (
            select(Task)
            .where(
                and_(
                    Task.project_id == project_id,
                    Task.id.in_(incomplete_deps_subq),
                    Task.status.notin_(["done", "cancelled"]),
                )
            )
            .options(selectinload(Task.dependencies))
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())
    
    async def count_tasks(self, project_id: UUID, filters: dict[str, Any] | None = None) -> int:
        """
        Count total tasks matching filters.
        
        Args:
            project_id: Project UUID
            filters: Optional filter criteria
            
        Returns:
            Total count
        """
        stmt = select(func.count(Task.id)).where(Task.project_id == project_id)
        
        if filters:
            if filters.get("status"):
                if isinstance(filters["status"], list):
                    stmt = stmt.where(Task.status.in_(filters["status"]))
                else:
                    stmt = stmt.where(Task.status == filters["status"])
            
            if filters.get("assignee_id"):
                stmt = stmt.where(Task.assignee_id == filters["assignee_id"])
        
        result = await self.db.execute(stmt)
        return result.scalar() or 0
    
    # ============= Helper Methods =============
    
    async def _generate_identifier(self, project_id: UUID) -> str:
        """
        Generate next unique identifier for task (e.g., ARD-001, ARD-002).
        
        Args:
            project_id: Project UUID
            
        Returns:
            Generated identifier string
        """
        # Count existing tasks in project
        result = await self.db.execute(
            select(func.count(Task.id)).where(Task.project_id == project_id)
        )
        count = result.scalar() or 0
        
        # Get project to extract prefix from slug
        project = await self.db.get(Project, project_id)
        if project and project.slug:
            # Use first 3 letters of slug as prefix
            prefix = project.slug[:3].upper()
        else:
            # Fallback to generic prefix
            prefix = "TSK"
        
        # Generate identifier: PREFIX-NNN (e.g., ARD-001)
        return f"{prefix}-{count + 1:03d}"