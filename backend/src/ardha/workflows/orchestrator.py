"""
Simplified workflow orchestration service.

This module provides basic orchestration logic for
executing AI workflows with state management.
"""

import asyncio
import logging
from typing import Any, Dict, List, Optional
from uuid import UUID, uuid4

from ..core.openrouter import OpenRouterClient
from ..core.qdrant import get_qdrant_service
from .nodes import (
    ArchitectNode,
    BaseNode,
    DebugNode,
    ImplementNode,
    MemoryIngestionNode,
    ResearchNode,
)
from .state import WorkflowContext, WorkflowState, WorkflowStatus, WorkflowType

logger = logging.getLogger(__name__)


class WorkflowOrchestrator:
    """
    Simplified workflow orchestration service.

    Manages workflow execution with basic state
    management and node coordination.
    """

    def __init__(self):
        """Initialize workflow orchestrator."""
        self.logger = logger
        self.active_executions: Dict[UUID, WorkflowState] = {}

        # Initialize node instances
        self.nodes = {
            "research": ResearchNode(),
            "architect": ArchitectNode(),
            "implement": ImplementNode(),
            "debug": DebugNode(),
            "memory_ingestion": MemoryIngestionNode(),
        }

        self.logger.info("Workflow orchestrator initialized")

    async def execute_workflow(
        self,
        workflow_type: WorkflowType,
        initial_request: str,
        user_id: UUID,
        project_id: Optional[UUID] = None,
        parameters: Optional[Dict[str, Any]] = None,
        context: Optional[Dict[str, Any]] = None,
    ) -> WorkflowState:
        """
        Execute a workflow with given input.

        Args:
            workflow_type: Type of workflow to execute
            initial_request: Initial request/prompt
            user_id: User executing workflow
            project_id: Associated project
            parameters: Workflow parameters
            context: Additional context data

        Returns:
            Workflow execution state with results

        Raises:
            Exception: If execution fails
        """
        try:
            # Create workflow state
            workflow_id = uuid4()
            execution_id = uuid4()

            from datetime import datetime

            state = WorkflowState(
                workflow_id=workflow_id,
                execution_id=execution_id,
                workflow_type=workflow_type,
                user_id=user_id,
                project_id=project_id,
                initial_request=initial_request,
                context=context or {},
                parameters=parameters or {},
                created_at=datetime.utcnow().isoformat(),
            )

            # Add to active executions
            self.active_executions[execution_id] = state

            # Execute workflow nodes sequentially
            await self._execute_workflow_nodes(workflow_type, state)

            # Remove from active executions
            if execution_id in self.active_executions:
                del self.active_executions[execution_id]

            self.logger.info(f"Workflow execution completed: {execution_id}")
            return state

        except Exception as e:
            self.logger.error(f"Workflow execution failed: {e}")
            # Don't modify state here since it might not be in scope
            # The calling function should handle error state
            raise

    async def get_execution_status(self, execution_id: UUID) -> Optional[WorkflowState]:
        """
        Get current status of workflow execution.

        Args:
            execution_id: Execution identifier

        Returns:
            Current workflow state or None if not found
        """
        return self.active_executions.get(execution_id)

    async def cancel_execution(self, execution_id: UUID, reason: Optional[str] = None) -> bool:
        """
        Cancel a running workflow execution.

        Args:
            execution_id: Execution to cancel
            reason: Optional cancellation reason

        Returns:
            True if cancelled successfully
        """
        if execution_id not in self.active_executions:
            return False

        state = self.active_executions[execution_id]
        state.status = WorkflowStatus.CANCELLED
        state.metadata["cancellation_reason"] = reason

        # Remove from active executions
        del self.active_executions[execution_id]

        self.logger.info(f"Cancelled workflow execution: {execution_id}")
        return True

    def _get_default_node_sequence(self, workflow_type: WorkflowType) -> List[str]:
        """
        Get default node sequence for workflow type.

        Args:
            workflow_type: Type of workflow

        Returns:
            List of node names in execution order
        """
        sequences = {
            WorkflowType.RESEARCH: ["research", "memory_ingestion"],
            WorkflowType.ARCHITECT: ["research", "architect", "memory_ingestion"],
            WorkflowType.IMPLEMENT: ["research", "architect", "implement", "memory_ingestion"],
            WorkflowType.DEBUG: ["debug", "memory_ingestion"],
            WorkflowType.FULL_DEVELOPMENT: [
                "research",
                "architect",
                "implement",
                "debug",
                "memory_ingestion",
            ],
            WorkflowType.CUSTOM: [],  # Must be provided explicitly
        }

        return sequences.get(workflow_type, [])

    async def _execute_workflow_nodes(
        self,
        workflow_type: WorkflowType,
        state: WorkflowState,
    ) -> None:
        """
        Execute workflow nodes sequentially.

        Args:
            workflow_type: Type of workflow
            state: Current workflow state
        """
        try:
            # Get node sequence
            node_sequence = self._get_default_node_sequence(workflow_type)

            # Create workflow context
            context = WorkflowContext(
                db_session=None,  # Simplified for now
                openrouter_client=OpenRouterClient(),
                qdrant_service=get_qdrant_service(),
                settings={},
                progress_callback=self._on_progress_update,
                error_callback=self._on_error,
                logger=self.logger,
            )

            # Mark execution as started
            state.status = WorkflowStatus.RUNNING
            state.started_at = state._get_timestamp()
            state._update_timestamp()

            # Execute nodes sequentially
            for node_name in node_sequence:
                if node_name not in self.nodes:
                    self.logger.warning(f"Unknown node: {node_name}")
                    continue

                node = self.nodes[node_name]

                try:
                    # Mark node started
                    state.mark_node_started(node_name)
                    self.logger.info(f"Starting node: {node_name}")

                    # Execute node
                    result = await node.execute(state, context)

                    # Mark node completed
                    state.mark_node_completed(node_name, result)
                    self.logger.info(f"Node {node_name} completed successfully")

                except Exception as e:
                    # Mark node failed
                    error_msg = str(e)
                    state.mark_node_failed(node_name, {"error": error_msg})
                    self.logger.error(f"Node {node_name} failed: {e}")

                    # Continue with other nodes for now
                    # Could implement retry logic here

            # Mark as completed if no critical errors
            if not state.errors or all("error" not in str(error).lower() for error in state.errors):
                state.status = WorkflowStatus.COMPLETED
                state.completed_at = state._get_timestamp()
            else:
                state.status = WorkflowStatus.FAILED
                state.completed_at = state._get_timestamp()

            self.logger.info(f"Workflow execution completed with status: {state.status}")

        except Exception as e:
            self.logger.error(f"Workflow execution failed: {e}")
            state.status = WorkflowStatus.FAILED
            state.errors.append(
                {
                    "error": str(e),
                    "timestamp": state._get_timestamp(),
                }
            )
            state.completed_at = state._get_timestamp()
            raise

    def _on_progress_update(self, execution_id: UUID, node_name: str, progress: float) -> None:
        """
        Handle progress updates from nodes.

        Args:
            execution_id: Workflow execution ID
            node_name: Name of node reporting progress
            progress: Progress percentage (0-100)
        """
        self.logger.debug(f"Progress update: {execution_id} - {node_name} - {progress}%")

        # Could emit WebSocket events here for real-time updates
        # For now, just log progress

    def _on_error(self, execution_id: UUID, node_name: str, error: Dict[str, Any]) -> None:
        """
        Handle errors from nodes.

        Args:
            execution_id: Workflow execution ID
            node_name: Name of node reporting error
            error: Error details
        """
        self.logger.error(f"Error in {node_name} for {execution_id}: {error}")

        # Could emit error events here for real-time monitoring
        # For now, just log error


# Global orchestrator instance
_orchestrator: Optional[WorkflowOrchestrator] = None


def get_workflow_orchestrator() -> WorkflowOrchestrator:
    """
    Get cached workflow orchestrator instance.

    Returns:
        WorkflowOrchestrator instance
    """
    global _orchestrator
    if _orchestrator is None:
        _orchestrator = WorkflowOrchestrator()
    return _orchestrator
