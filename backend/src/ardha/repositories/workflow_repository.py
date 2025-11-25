"""
Workflow repository for data access operations.

This module provides repository methods for workflow execution
management with comprehensive CRUD operations and analytics.
"""

import logging
from typing import Any, Dict, List, Optional, Tuple
from uuid import UUID

from sqlalchemy import and_, desc, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ..core.exceptions import RepositoryError
from ..models.project import Project
from ..models.user import User
from ..models.workflow_execution import WorkflowExecution
from ..workflows.state import WorkflowStatus, WorkflowType

logger = logging.getLogger(__name__)


class WorkflowRepository:
    """
    Repository for workflow execution data access operations.

    Provides comprehensive CRUD operations and analytics for
    workflow execution management with proper error handling.
    """

    def __init__(self, db_session: AsyncSession):
        """
        Initialize repository with database session.

        Args:
            db_session: Async database session
        """
        self.db = db_session

    async def create(
        self,
        user_id: UUID,
        workflow_type: str,
        input_data: Dict[str, Any],
        project_id: Optional[UUID] = None,
        **kwargs,
    ) -> WorkflowExecution:
        """
        Create a new workflow execution.

        Args:
            user_id: User ID who initiated the workflow
            workflow_type: Type of workflow (research, prd, task_generation)
            input_data: Input data for the workflow
            project_id: Optional project ID
            **kwargs: Additional fields

        Returns:
            Created workflow execution

        Raises:
            RepositoryError: If creation fails
        """
        try:
            execution = WorkflowExecution()
            execution.user_id = user_id
            execution.workflow_type = workflow_type
            execution.input_data = input_data
            execution.project_id = project_id

            # Set any additional kwargs
            for key, value in kwargs.items():
                if hasattr(execution, key):
                    setattr(execution, key, value)

            self.db.add(execution)
            await self.db.flush()

            logger.info(f"Created workflow execution: {execution.id}")
            return execution

        except Exception as e:
            logger.error(f"Failed to create workflow execution: {e}")
            raise RepositoryError(f"Failed to create workflow execution: {e}")

    async def get_by_id(self, execution_id: UUID) -> Optional[WorkflowExecution]:
        """
        Get workflow execution by ID.

        Args:
            execution_id: Execution ID

        Returns:
            Workflow execution or None if not found
        """
        try:
            stmt = (
                select(WorkflowExecution)
                .where(
                    and_(
                        WorkflowExecution.id == execution_id, WorkflowExecution.deleted_at.is_(None)
                    )
                )
                .options(
                    selectinload(WorkflowExecution.user), selectinload(WorkflowExecution.project)
                )
            )

            result = await self.db.execute(stmt)
            return result.scalar_one_or_none()

        except Exception as e:
            logger.error(f"Failed to get workflow execution {execution_id}: {e}")
            raise RepositoryError(f"Failed to get workflow execution: {e}")

    async def get_user_executions(
        self,
        user_id: UUID,
        status: Optional[WorkflowStatus] = None,
        workflow_type: Optional[str] = None,
        project_id: Optional[UUID] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> List[WorkflowExecution]:
        """
        Get workflow executions for a user with filtering.

        Args:
            user_id: User ID
            status: Optional status filter
            workflow_type: Optional workflow type filter
            project_id: Optional project ID filter
            limit: Maximum number of results
            offset: Number of results to skip

        Returns:
            List of workflow executions
        """
        try:
            conditions = [
                WorkflowExecution.user_id == user_id,
                WorkflowExecution.deleted_at.is_(None),
            ]

            if status:
                conditions.append(WorkflowExecution.status == status)
            if workflow_type:
                conditions.append(WorkflowExecution.workflow_type == workflow_type)
            if project_id:
                conditions.append(WorkflowExecution.project_id == project_id)

            stmt = (
                select(WorkflowExecution)
                .where(and_(*conditions))
                .order_by(desc(WorkflowExecution.created_at))
                .limit(limit)
                .offset(offset)
                .options(
                    selectinload(WorkflowExecution.user), selectinload(WorkflowExecution.project)
                )
            )

            result = await self.db.execute(stmt)
            return list(result.scalars().all())

        except Exception as e:
            logger.error(f"Failed to get user executions: {e}")
            raise RepositoryError(f"Failed to get user executions: {e}")

    async def get_project_executions(
        self,
        project_id: UUID,
        status: Optional[WorkflowStatus] = None,
        workflow_type: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> List[WorkflowExecution]:
        """
        Get workflow executions for a project.

        Args:
            project_id: Project ID
            status: Optional status filter
            workflow_type: Optional workflow type filter
            limit: Maximum number of results
            offset: Number of results to skip

        Returns:
            List of workflow executions
        """
        try:
            conditions = [
                WorkflowExecution.project_id == project_id,
                WorkflowExecution.deleted_at.is_(None),
            ]

            if status:
                conditions.append(WorkflowExecution.status == status)
            if workflow_type:
                conditions.append(WorkflowExecution.workflow_type == workflow_type)

            stmt = (
                select(WorkflowExecution)
                .where(and_(*conditions))
                .order_by(desc(WorkflowExecution.created_at))
                .limit(limit)
                .offset(offset)
                .options(
                    selectinload(WorkflowExecution.user), selectinload(WorkflowExecution.project)
                )
            )

            result = await self.db.execute(stmt)
            return list(result.scalars().all())

        except Exception as e:
            logger.error(f"Failed to get project executions: {e}")
            raise RepositoryError(f"Failed to get project executions: {e}")

    async def update_status(
        self,
        execution_id: UUID,
        status: WorkflowStatus,
        error_message: Optional[str] = None,
        output_data: Optional[Dict[str, Any]] = None,
        checkpoint_data: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """
        Update workflow execution status.

        Args:
            execution_id: Execution ID
            status: New status
            error_message: Optional error message
            output_data: Optional output data
            checkpoint_data: Optional checkpoint data

        Returns:
            True if updated successfully
        """
        try:
            stmt = select(WorkflowExecution).where(
                and_(WorkflowExecution.id == execution_id, WorkflowExecution.deleted_at.is_(None))
            )

            result = await self.db.execute(stmt)
            execution = result.scalar_one_or_none()

            if not execution:
                return False

            execution.status = status

            if error_message:
                execution.error_message = error_message

            if output_data:
                execution.output_data = output_data

            if checkpoint_data:
                execution.checkpoint_data = checkpoint_data

            # Update timestamps
            if status == WorkflowStatus.RUNNING and not execution.started_at:
                execution.started_at = func.now()
            elif status in [
                WorkflowStatus.COMPLETED,
                WorkflowStatus.FAILED,
                WorkflowStatus.CANCELLED,
            ]:
                execution.completed_at = func.now()

            await self.db.flush()

            logger.info(f"Updated workflow execution {execution_id} status to {status}")
            return True

        except Exception as e:
            logger.error(f"Failed to update workflow execution status: {e}")
            raise RepositoryError(f"Failed to update workflow execution status: {e}")

    async def update_resource_usage(
        self, execution_id: UUID, tokens_used: int, cost_incurred: float
    ) -> bool:
        """
        Update resource usage for workflow execution.

        Args:
            execution_id: Execution ID
            tokens_used: Number of tokens used
            cost_incurred: Cost incurred

        Returns:
            True if updated successfully
        """
        try:
            stmt = select(WorkflowExecution).where(
                and_(WorkflowExecution.id == execution_id, WorkflowExecution.deleted_at.is_(None))
            )

            result = await self.db.execute(stmt)
            execution = result.scalar_one_or_none()

            if not execution:
                return False

            execution.total_tokens += tokens_used
            execution.total_cost += float(cost_incurred)

            await self.db.flush()

            logger.info(f"Updated resource usage for execution {execution_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to update resource usage: {e}")
            raise RepositoryError(f"Failed to update resource usage: {e}")

    async def delete(self, execution_id: UUID) -> bool:
        """
        Soft delete workflow execution.

        Args:
            execution_id: Execution ID

        Returns:
            True if deleted successfully
        """
        try:
            stmt = select(WorkflowExecution).where(
                and_(WorkflowExecution.id == execution_id, WorkflowExecution.deleted_at.is_(None))
            )

            result = await self.db.execute(stmt)
            execution = result.scalar_one_or_none()

            if not execution:
                return False

            execution.is_deleted = True
            execution.deleted_at = func.now()
            await self.db.flush()

            logger.info(f"Soft deleted workflow execution {execution_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to delete workflow execution: {e}")
            raise RepositoryError(f"Failed to delete workflow execution: {e}")

    async def get_execution_stats(
        self,
        user_id: Optional[UUID] = None,
        project_id: Optional[UUID] = None,
        workflow_type: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Get execution statistics.

        Args:
            user_id: Optional user ID filter
            project_id: Optional project ID filter
            workflow_type: Optional workflow type filter

        Returns:
            Dictionary with execution statistics
        """
        try:
            conditions = [WorkflowExecution.deleted_at.is_(None)]

            if user_id:
                conditions.append(WorkflowExecution.user_id == user_id)
            if project_id:
                conditions.append(WorkflowExecution.project_id == project_id)
            if workflow_type:
                conditions.append(WorkflowExecution.workflow_type == workflow_type)

            # Total executions
            total_stmt = select(func.count(WorkflowExecution.id)).where(and_(*conditions))
            total_result = await self.db.execute(total_stmt)
            total_executions = total_result.scalar()

            # Status breakdown
            status_stmt = (
                select(WorkflowExecution.status, func.count(WorkflowExecution.id))
                .where(and_(*conditions))
                .group_by(WorkflowExecution.status)
            )
            status_result = await self.db.execute(status_stmt)
            status_rows = status_result.all()
            status_breakdown = {status: count for status, count in status_rows}

            # Resource totals
            resource_stmt = select(
                func.sum(WorkflowExecution.total_tokens).label("total_tokens"),
                func.sum(WorkflowExecution.total_cost).label("total_cost"),
                func.avg(WorkflowExecution.total_cost).label("avg_cost"),
            ).where(and_(*conditions))

            resource_result = await self.db.execute(resource_stmt)
            resource_row = resource_result.first()

            return {
                "total_executions": total_executions or 0,
                "status_breakdown": {
                    status.value if hasattr(status, "value") else str(status): count
                    for status, count in status_breakdown.items()
                },
                "total_tokens": int(resource_row.total_tokens or 0) if resource_row else 0,
                "total_cost": float(resource_row.total_cost or 0.0) if resource_row else 0.0,
                "average_cost": float(resource_row.avg_cost or 0.0) if resource_row else 0.0,
            }

        except Exception as e:
            logger.error(f"Failed to get execution stats: {e}")
            raise RepositoryError(f"Failed to get execution stats: {e}")

    async def get_running_executions(self) -> List[WorkflowExecution]:
        """
        Get all currently running executions.

        Returns:
            List of running workflow executions
        """
        try:
            stmt = (
                select(WorkflowExecution)
                .where(
                    and_(
                        WorkflowExecution.status == WorkflowStatus.RUNNING,
                        WorkflowExecution.deleted_at.is_(None),
                    )
                )
                .options(
                    selectinload(WorkflowExecution.user), selectinload(WorkflowExecution.project)
                )
            )

            result = await self.db.execute(stmt)
            return list(result.scalars().all())

        except Exception as e:
            logger.error(f"Failed to get running executions: {e}")
            raise RepositoryError(f"Failed to get running executions: {e}")

    async def count_user_executions(
        self, user_id: UUID, status: Optional[WorkflowStatus] = None
    ) -> int:
        """
        Count executions for a user.

        Args:
            user_id: User ID
            status: Optional status filter

        Returns:
            Number of executions
        """
        try:
            conditions = [
                WorkflowExecution.user_id == user_id,
                WorkflowExecution.deleted_at.is_(None),
            ]

            if status:
                conditions.append(WorkflowExecution.status == status)

            stmt = select(func.count(WorkflowExecution.id)).where(and_(*conditions))
            result = await self.db.execute(stmt)
            return result.scalar() or 0

        except Exception as e:
            logger.error(f"Failed to count user executions: {e}")
            raise RepositoryError(f"Failed to count user executions: {e}")
