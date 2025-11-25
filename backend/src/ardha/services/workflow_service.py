"""
Workflow service for workflow execution management.

This module provides high-level workflow execution services with
comprehensive error handling, resource tracking, and state management.
"""

import logging
from typing import Any, Dict, List, Optional
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from ..core.exceptions import NotFoundError, ServiceError, ValidationError
from ..models.workflow_execution import WorkflowExecution
from ..repositories.workflow_repository import WorkflowRepository
from ..workflows.orchestrator import get_workflow_orchestrator
from ..workflows.state import WorkflowStatus, WorkflowType

logger = logging.getLogger(__name__)


class WorkflowService:
    """
    Service for managing workflow execution operations.

    Provides high-level workflow execution services with comprehensive
    error handling, resource tracking, and state management.
    """

    def __init__(self, db_session: AsyncSession):
        """
        Initialize workflow service.

        Args:
            db_session: Async database session
        """
        self.db = db_session
        self.repository = WorkflowRepository(db_session)
        self.orchestrator = get_workflow_orchestrator()

    async def execute_workflow(
        self,
        user_id: UUID,
        workflow_type: str,
        initial_request: str,
        project_id: Optional[UUID] = None,
        parameters: Optional[Dict[str, Any]] = None,
        context: Optional[Dict[str, Any]] = None,
    ) -> WorkflowExecution:
        """
        Execute a workflow with the given parameters.

        Args:
            user_id: User ID who initiated the workflow
            workflow_type: Type of workflow to execute
            initial_request: Initial request/prompt for the workflow
            project_id: Optional project ID
            parameters: Optional workflow parameters
            context: Optional additional context

        Returns:
            Created and started workflow execution

        Raises:
            ValidationError: If input validation fails
            ServiceError: If execution fails
        """
        try:
            # Validate workflow type
            try:
                workflow_enum = WorkflowType(workflow_type)
            except ValueError:
                raise ValidationError(f"Invalid workflow type: {workflow_type}")

            # Validate input
            if not initial_request or not initial_request.strip():
                raise ValidationError("Initial request cannot be empty")

            # Prepare input data
            input_data = {
                "initial_request": initial_request,
                "parameters": parameters or {},
                "context": context or {},
            }

            # Create workflow execution record
            execution = await self.repository.create(
                user_id=user_id,
                workflow_type=workflow_type,
                input_data=input_data,
                project_id=project_id,
                status=WorkflowStatus.PENDING,
            )

            # Start workflow execution asynchronously
            try:
                await self._start_workflow_execution(
                    execution.id, workflow_enum, initial_request, parameters, context
                )
            except Exception as e:
                # Update execution status to failed if start fails
                await self.repository.update_status(
                    execution.id,
                    WorkflowStatus.FAILED,
                    error_message=f"Failed to start workflow: {str(e)}",
                )
                raise ServiceError(f"Failed to start workflow execution: {e}")

            logger.info(f"Started workflow execution {execution.id} for user {user_id}")
            return execution

        except (ValidationError, ServiceError):
            raise
        except Exception as e:
            logger.error(f"Failed to execute workflow: {e}")
            raise ServiceError(f"Failed to execute workflow: {e}")

    async def get_execution(self, execution_id: UUID, user_id: UUID) -> Optional[WorkflowExecution]:
        """
        Get workflow execution by ID for a specific user.

        Args:
            execution_id: Execution ID
            user_id: User ID requesting the execution

        Returns:
            Workflow execution or None if not found

        Raises:
            ServiceError: If retrieval fails
        """
        try:
            execution = await self.repository.get_by_id(execution_id)

            if not execution:
                return None

            # Check if user owns this execution
            if execution.user_id != user_id:
                raise NotFoundError(
                    "Execution not found",
                    resource_type="WorkflowExecution",
                    resource_id=str(execution_id),
                )

            return execution

        except (NotFoundError, ServiceError):
            raise
        except Exception as e:
            logger.error(f"Failed to get execution {execution_id}: {e}")
            raise ServiceError(f"Failed to get execution: {e}")

    async def list_user_executions(
        self,
        user_id: UUID,
        status: Optional[WorkflowStatus] = None,
        workflow_type: Optional[str] = None,
        project_id: Optional[UUID] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> List[WorkflowExecution]:
        """
        List workflow executions for a user with filtering.

        Args:
            user_id: User ID
            status: Optional status filter
            workflow_type: Optional workflow type filter
            project_id: Optional project ID filter
            limit: Maximum number of results
            offset: Number of results to skip

        Returns:
            List of workflow executions

        Raises:
            ServiceError: If listing fails
        """
        try:
            return await self.repository.get_user_executions(
                user_id=user_id,
                status=status,
                workflow_type=workflow_type,
                project_id=project_id,
                limit=limit,
                offset=offset,
            )

        except Exception as e:
            logger.error(f"Failed to list user executions: {e}")
            raise ServiceError(f"Failed to list user executions: {e}")

    async def cancel_execution(
        self, execution_id: UUID, user_id: UUID, reason: Optional[str] = None
    ) -> bool:
        """
        Cancel a running workflow execution.

        Args:
            execution_id: Execution ID
            user_id: User ID requesting cancellation
            reason: Optional cancellation reason

        Returns:
            True if cancelled successfully

        Raises:
            NotFoundError: If execution not found
            ValidationError: If execution cannot be cancelled
            ServiceError: If cancellation fails
        """
        try:
            # Get execution and verify ownership
            execution = await self.get_execution(execution_id, user_id)
            if not execution:
                raise NotFoundError(
                    "Execution not found",
                    resource_type="WorkflowExecution",
                    resource_id=str(execution_id),
                )

            # Check if execution can be cancelled
            if execution.status not in [WorkflowStatus.PENDING, WorkflowStatus.RUNNING]:
                raise ValidationError(f"Cannot cancel execution in status: {execution.status}")

            # Cancel in orchestrator
            success = await self.orchestrator.cancel_execution(execution_id, reason)
            if not success:
                raise ValidationError("Failed to cancel execution in orchestrator")

            # Update status in database
            await self.repository.update_status(
                execution_id, WorkflowStatus.CANCELLED, error_message=reason
            )

            logger.info(f"Cancelled workflow execution {execution_id} for user {user_id}")
            return True

        except (NotFoundError, ValidationError, ServiceError):
            raise
        except Exception as e:
            logger.error(f"Failed to cancel execution {execution_id}: {e}")
            raise ServiceError(f"Failed to cancel execution: {e}")

    async def resume_execution(self, execution_id: UUID, user_id: UUID) -> bool:
        """
        Resume a failed workflow execution from checkpoint.

        Args:
            execution_id: Execution ID
            user_id: User ID requesting resumption

        Returns:
            True if resumed successfully

        Raises:
            NotFoundError: If execution not found
            ValidationError: If execution cannot be resumed
            ServiceError: If resumption fails
        """
        try:
            # Get execution and verify ownership
            execution = await self.get_execution(execution_id, user_id)
            if not execution:
                raise NotFoundError(
                    "Execution not found",
                    resource_type="WorkflowExecution",
                    resource_id=str(execution_id),
                )

            # Check if execution can be resumed
            if not execution.can_resume:
                raise ValidationError("Execution cannot be resumed")

            # Update status to running
            await self.repository.update_status(execution_id, WorkflowStatus.RUNNING)

            # Resume execution in orchestrator
            try:
                # Note: orchestrator doesn't have resume_execution method yet
                # This would need to be implemented in the orchestrator
                await self.orchestrator.execute_workflow(
                    workflow_type=WorkflowType(execution.workflow_type),
                    initial_request=execution.input_data.get("initial_request", ""),
                    user_id=user_id,
                    project_id=execution.project_id,
                    parameters=execution.input_data.get("parameters", {}),
                    context=execution.input_data.get("context", {}),
                )
            except Exception as e:
                # Revert status if resumption fails
                await self.repository.update_status(
                    execution_id, WorkflowStatus.FAILED, error_message=f"Failed to resume: {str(e)}"
                )
                raise ServiceError(f"Failed to resume execution in orchestrator: {e}")

            logger.info(f"Resumed workflow execution {execution_id} for user {user_id}")
            return True

        except (NotFoundError, ValidationError, ServiceError):
            raise
        except Exception as e:
            logger.error(f"Failed to resume execution {execution_id}: {e}")
            raise ServiceError(f"Failed to resume execution: {e}")

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

        Raises:
            ServiceError: If stats retrieval fails
        """
        try:
            return await self.repository.get_execution_stats(
                user_id=user_id, project_id=project_id, workflow_type=workflow_type
            )

        except Exception as e:
            logger.error(f"Failed to get execution stats: {e}")
            raise ServiceError(f"Failed to get execution stats: {e}")

    async def delete_execution(self, execution_id: UUID, user_id: UUID) -> bool:
        """
        Soft delete a workflow execution.

        Args:
            execution_id: Execution ID
            user_id: User ID requesting deletion

        Returns:
            True if deleted successfully

        Raises:
            NotFoundError: If execution not found
            ValidationError: If execution cannot be deleted
            ServiceError: If deletion fails
        """
        try:
            # Get execution and verify ownership
            execution = await self.get_execution(execution_id, user_id)
            if not execution:
                raise NotFoundError(
                    "Execution not found",
                    resource_type="WorkflowExecution",
                    resource_id=str(execution_id),
                )

            # Check if execution can be deleted
            if execution.status == WorkflowStatus.RUNNING:
                raise ValidationError("Cannot delete running execution")

            # Soft delete
            success = await self.repository.delete(execution_id)
            if not success:
                raise ServiceError("Failed to delete execution")

            logger.info(f"Deleted workflow execution {execution_id} for user {user_id}")
            return True

        except (NotFoundError, ValidationError, ServiceError):
            raise
        except Exception as e:
            logger.error(f"Failed to delete execution {execution_id}: {e}")
            raise ServiceError(f"Failed to delete execution: {e}")

    async def _start_workflow_execution(
        self,
        execution_id: UUID,
        workflow_type: WorkflowType,
        initial_request: str,
        parameters: Optional[Dict[str, Any]],
        context: Optional[Dict[str, Any]],
    ) -> None:
        """
        Start workflow execution in the orchestrator.

        Args:
            execution_id: Execution ID
            workflow_type: Type of workflow
            initial_request: Initial request
            parameters: Optional parameters
            context: Optional context
        """
        try:
            # Update status to running
            await self.repository.update_status(execution_id, WorkflowStatus.RUNNING)

            # Get execution to get user_id and project_id
            execution = await self.repository.get_by_id(execution_id)
            if not execution:
                raise ServiceError("Execution not found for update")

            # Execute in orchestrator
            state = await self.orchestrator.execute_workflow(
                workflow_type=workflow_type,
                initial_request=initial_request,
                user_id=execution.user_id,
                project_id=execution.project_id,
                parameters=parameters or {},
                context=context or {},
            )

            # Update execution with results
            await self._update_execution_from_state(execution_id, state)

        except Exception as e:
            # Update status to failed
            await self.repository.update_status(
                execution_id, WorkflowStatus.FAILED, error_message=str(e)
            )
            raise

    async def _update_execution_from_state(self, execution_id: UUID, state) -> None:
        """
        Update execution record from orchestrator state.

        Args:
            execution_id: Execution ID
            state: Workflow state from orchestrator
        """
        try:
            # Calculate total tokens
            total_tokens = 0
            if state.token_usage:
                for model_usage in state.token_usage.values():
                    if isinstance(model_usage, dict):
                        total_tokens += model_usage.get("input", 0) + model_usage.get("output", 0)

            # Update resource usage
            await self.repository.update_resource_usage(
                execution_id, total_tokens, state.total_cost
            )

            # Update status and output data
            await self.repository.update_status(
                execution_id,
                state.status,
                output_data={
                    "results": state.results,
                    "artifacts": state.artifacts,
                    "metadata": state.metadata,
                },
                checkpoint_data={
                    "completed_nodes": state.completed_nodes,
                    "failed_nodes": state.failed_nodes,
                    "current_node": state.current_node,
                },
            )

            # Trigger memory ingestion for completed workflows
            if state.status == WorkflowStatus.COMPLETED:
                try:
                    # Get execution to get user_id
                    execution = await self.repository.get_by_id(execution_id)
                    if execution:
                        # Import here to avoid circular imports
                        from ardha.core.celery_app import celery_app

                        # Trigger background job
                        celery_app.send_task(
                            "ardha.jobs.memory_jobs.ingest_workflow_memory",
                            args=[str(execution_id), str(execution.user_id)],
                        )
                        logger.info(f"Triggered memory ingestion for workflow {execution_id}")
                except Exception as e:
                    logger.warning(f"Failed to trigger workflow memory ingestion: {e}")

        except Exception as e:
            logger.error(f"Failed to update execution from state: {e}")
            # Don't raise here to avoid masking the original execution error
