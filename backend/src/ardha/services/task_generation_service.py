"""
Task Generation service for database integration.

This service handles saving generated tasks, dependencies, and
OpenSpec proposals to the database.
"""

import logging
from typing import Any, Dict, List, Optional, Tuple
from uuid import UUID

from ..core.config import settings
from ..core.database import async_session_factory, get_db
from ..models.project import Project
from ..models.task import Task
from ..models.task_activity import TaskActivity
from ..models.task_dependency import TaskDependency
from ..models.user import User
from .openspec_service import get_openspec_service

logger = logging.getLogger(__name__)


class TaskGenerationService:
    """
    Service for integrating Task Generation workflow with database.

    Handles saving generated tasks, dependencies, and linking
    to projects and users.
    """

    def __init__(self):
        """Initialize Task Generation service."""
        self.logger = logger.getChild("TaskGenerationService")
        self.openspec_service = get_openspec_service()

    async def save_generated_tasks(
        self,
        task_breakdown: List[Dict[str, Any]],
        project_id: UUID,
        user_id: UUID,
        workflow_id: UUID,
    ) -> Tuple[List[UUID], List[UUID]]:
        """
        Save generated tasks to database.

        Args:
            task_breakdown: List of generated tasks
            project_id: Project to link tasks to
            user_id: User who generated the tasks
            workflow_id: Workflow execution ID

        Returns:
            Tuple of (task_ids, epic_ids)

        Raises:
            Exception: If database operation fails
        """
        task_ids = []
        epic_ids = []

        try:
            async with async_session_factory() as session:
                # Process tasks in order to maintain dependencies
                for task_data in task_breakdown:
                    # Skip epics for now (they're just containers)
                    if task_data.get("is_epic", False):
                        continue

                    # Generate task identifier
                    task_identifier = await self._generate_task_identifier(task_data, session)

                    # Determine task type
                    task_type = self._determine_task_type(task_data)

                    # Create task
                    task = Task(
                        identifier=task_identifier,
                        title=task_data.get("title", "Untitled Task"),
                        description=task_data.get("description", ""),
                        priority=task_data.get("priority", "medium"),
                        status="pending_approval",  # Generated tasks need approval
                        project_id=project_id,
                        created_by=user_id,
                        estimate_hours=task_data.get("estimated_hours"),
                        actual_hours=None,
                        completion_percentage=0.0,
                        metadata={
                            "generated_by_workflow": True,
                            "workflow_id": str(workflow_id),
                            "is_subtask": task_data.get("is_subtask", False),
                            "is_main_task": task_data.get("is_main_task", False),
                            "epic_id": task_data.get("epic_id"),
                            "parent_task_id": task_data.get("parent_task_id"),
                            "acceptance_criteria": task_data.get("acceptance_criteria", []),
                            "required_skills": task_data.get("required_skills", []),
                            "complexity": task_data.get("complexity", "medium"),
                            "task_type": task_type,  # Store task type in metadata
                        },
                    )

                    session.add(task)
                    await session.flush()  # Get the task ID
                    task_ids.append(task.id)

                    # Track epic IDs separately
                    if task_data.get("is_epic", False):
                        epic_ids.append(task.id)

                    self.logger.info(
                        f"Saved task: {task_identifier} - {task_data.get('title', 'Untitled')}"
                    )

                await session.commit()

            self.logger.info(f"Saved {len(task_ids)} tasks to database for project {project_id}")
            return task_ids, epic_ids

        except Exception as e:
            self.logger.error(f"Failed to save generated tasks: {e}")
            raise

    async def save_task_dependencies(
        self,
        task_dependencies: List[Dict[str, Any]],
        task_breakdown: List[Dict[str, Any]],
        task_ids: List[UUID],
    ) -> List[UUID]:
        """
        Save task dependencies to database.

        Args:
            task_dependencies: List of dependency definitions
            task_breakdown: Original task breakdown for mapping
            task_ids: List of created task IDs

        Returns:
            List of dependency IDs created

        Raises:
            Exception: If database operation fails
        """
        dependency_ids = []

        try:
            # Create mapping from task identifiers to IDs
            task_id_map = self._create_task_id_mapping(task_breakdown, task_ids)

            async with async_session_factory() as session:
                for dep_data in task_dependencies:
                    task_id_key = dep_data.get("task_id")
                    depends_on_key = dep_data.get("depends_on")
                    task_id = task_id_map.get(task_id_key) if task_id_key else None
                    depends_on_task_id = task_id_map.get(depends_on_key) if depends_on_key else None

                    if not task_id or not depends_on_task_id:
                        self.logger.warning(f"Skipping dependency - missing task IDs: {dep_data}")
                        continue

                    # Create dependency
                    dependency = TaskDependency(
                        task_id=task_id,
                        depends_on_task_id=depends_on_task_id,
                        dependency_type=dep_data.get("dependency_type", "finish_to_start"),
                        created_by=task_ids[0] if task_ids else None,  # First task as creator
                    )

                    session.add(dependency)
                    await session.flush()
                    dependency_ids.append(dependency.id)

                    self.logger.info(f"Saved dependency: {task_id} -> {depends_on_task_id}")

                await session.commit()

            self.logger.info(f"Saved {len(dependency_ids)} task dependencies")
            return dependency_ids

        except Exception as e:
            self.logger.error(f"Failed to save task dependencies: {e}")
            raise

    async def link_openspec_to_project(
        self,
        proposal_id: str,
        project_id: UUID,
        user_id: UUID,
        workflow_id: UUID,
        openspec_data: Dict[str, Any],
    ) -> bool:
        """
        Link OpenSpec proposal to project.

        Args:
            proposal_id: Unique proposal identifier
            project_id: Project to link to
            user_id: User who created the proposal
            workflow_id: Workflow execution ID
            openspec_data: Complete OpenSpec proposal data

        Returns:
            True if linked successfully
        """
        try:
            # Create activity record for OpenSpec generation
            activity = TaskActivity(
                project_id=project_id,
                user_id=user_id,
                activity_type="openspec_generated",
                description=f"Generated OpenSpec proposal: {proposal_id}",
                metadata={
                    "proposal_id": proposal_id,
                    "workflow_id": str(workflow_id),
                    "files_generated": list(openspec_data.get("files", {}).keys()),
                    "change_directory": openspec_data.get("metadata", {}).get(
                        "change_directory_path"
                    ),
                    "quality_score": openspec_data.get("metadata", {}).get("quality_score"),
                },
            )

            async with async_session_factory() as session:
                session.add(activity)
                await session.commit()

            self.logger.info(f"Linked OpenSpec proposal {proposal_id} to project {project_id}")
            return True

        except Exception as e:
            self.logger.error(f"Failed to link OpenSpec to project: {e}")
            return False

    async def _generate_task_identifier(self, task_data: Dict[str, Any], session) -> str:
        """
        Generate unique task identifier.

        Args:
            task_data: Task data
            session: Database session for querying existing tasks

        Returns:
            Unique task identifier
        """
        # Get project ID from the first task (they all belong to same project)
        project_id = task_data.get("project_id")

        # Query existing task identifiers for this project
        from sqlalchemy import func, select

        result = await session.execute(
            select(func.count(Task.id)).where(Task.project_id == project_id)
        )
        task_count = result.scalar() or 0

        # Generate identifier like TAS-001, TAS-002, etc.
        return f"TAS-{task_count + 1:03d}"

    def _determine_task_type(self, task_data: Dict[str, Any]) -> str:
        """
        Determine task type from task data.

        Args:
            task_data: Task data

        Returns:
            Task type string
        """
        # Use priority and complexity to determine type
        priority = task_data.get("priority", "medium").lower()
        complexity = task_data.get("complexity", "medium").lower()

        if priority in ["urgent", "high"] or complexity in ["complex", "very_complex"]:
            return "feature"
        elif "bug" in task_data.get("title", "").lower():
            return "bug"
        elif "refactor" in task_data.get("description", "").lower():
            return "tech_debt"
        else:
            return "feature"

    def _create_task_id_mapping(
        self, task_breakdown: List[Dict[str, Any]], task_ids: List[UUID]
    ) -> Dict[str, UUID]:
        """
        Create mapping from task identifiers to database IDs.

        Args:
            task_breakdown: Original task breakdown
            task_ids: Generated task IDs

        Returns:
            Mapping from task identifiers to IDs
        """
        mapping = {}

        # Filter out epics and create mapping
        non_epic_tasks = [task for task in task_breakdown if not task.get("is_epic", False)]

        for i, task_data in enumerate(non_epic_tasks):
            if i < len(task_ids):
                task_id = task_data.get("id", f"task_{i}")
                mapping[task_id] = task_ids[i]

        return mapping

    async def get_project_tasks_for_generation(self, project_id: UUID) -> List[Dict[str, Any]]:
        """
        Get existing tasks for a project to inform generation.

        Args:
            project_id: Project ID

        Returns:
            List of existing task data
        """
        try:
            async with async_session_factory() as session:
                from sqlalchemy import select

                result = await session.execute(
                    select(Task)
                    .where(Task.project_id == project_id)
                    .order_by(Task.created_at.desc())
                )
                tasks = result.scalars().all()

                # Convert to dict format for workflow
                existing_tasks = []
                for task in tasks:
                    existing_tasks.append(
                        {
                            "id": task.identifier,
                            "title": task.title,
                            "description": task.description,
                            "type": task.status,  # Using status as type for now
                            "priority": task.priority,
                            "status": task.status,
                            "estimated_hours": task.estimate_hours,
                            "created_at": task.created_at.isoformat() if task.created_at else None,
                        }
                    )

                self.logger.info(
                    f"Retrieved {len(existing_tasks)} existing tasks for project {project_id}"
                )
                return existing_tasks

        except Exception as e:
            self.logger.error(f"Failed to get existing tasks: {e}")
            return []


# Global service instance
_task_generation_service: Optional[TaskGenerationService] = None


def get_task_generation_service() -> TaskGenerationService:
    """
    Get cached Task Generation service instance.

    Returns:
        TaskGenerationService instance
    """
    global _task_generation_service
    if _task_generation_service is None:
        _task_generation_service = TaskGenerationService()
    return _task_generation_service
