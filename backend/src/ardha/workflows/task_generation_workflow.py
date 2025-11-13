"""
Task Generation workflow implementation with LangGraph StateGraph.

This module implements the Task Generation workflow using LangGraph for
orchestration, with proper state management, error recovery, and streaming.
"""

import asyncio
import logging
from typing import Any, Dict, List, Optional, Union, TYPE_CHECKING
from uuid import UUID, uuid4

from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver

import json
from typing import Callable

from ..core.openrouter import OpenRouterClient
from ..core.qdrant import get_qdrant_service
from .state import WorkflowStatus, WorkflowContext, WorkflowType
from .nodes.task_generation_nodes import (
    AnalyzePRDNode, BreakdownTasksNode, DefineDependenciesNode,
    EstimateEffortNode, GenerateOpenSpecNode, TaskGenerationNodeException,
    TaskGenerationStepResult
)
if TYPE_CHECKING:
    from ..schemas.workflows.task_generation import (
        TaskGenerationState, TaskGenerationWorkflowConfig, TaskGenerationProgressUpdate
    )
    
# Export for imports
__all__ = ["TaskGenerationWorkflow", "TaskGenerationWorkflowConfig", "get_task_generation_workflow"]

logger = logging.getLogger(__name__)


class TaskGenerationWorkflow:
    """
    Task Generation workflow using LangGraph StateGraph.
    
    Orchestrates the conversion of PRD documents into comprehensive task breakdowns
    and OpenSpec proposals with state persistence and real-time progress tracking.
    """
    
    def __init__(self, config: Optional["TaskGenerationWorkflowConfig"] = None):
        """
        Initialize Task Generation workflow.
        
        Args:
            config: Workflow configuration (optional)
        """
        from ..schemas.workflows.task_generation import TaskGenerationWorkflowConfig
        self.config = config or TaskGenerationWorkflowConfig(openspec_template_path=None)
        self.logger = logger.getChild("TaskGenerationWorkflow")
        
        # Initialize nodes
        self.nodes = {
            "analyze_prd": AnalyzePRDNode(),
            "breakdown_tasks": BreakdownTasksNode(),
            "define_dependencies": DefineDependenciesNode(),
            "estimate_effort": EstimateEffortNode(),
            "generate_openspec": GenerateOpenSpecNode(),
        }
        
        # Initialize checkpoint saver for state persistence
        self.checkpointer = MemorySaver()
        
        # Initialize LangGraph StateGraph
        self.graph = self._build_graph()
        
        # Active executions tracking
        self.active_executions: Dict[UUID, "TaskGenerationState"] = {}
        
        self.logger.info("Task Generation workflow initialized")
    
    def _build_graph(self):
        """
        Build the LangGraph StateGraph for Task Generation workflow.
        
        Returns:
            Configured StateGraph instance
        """
        # Create StateGraph with TaskGenerationState
        from ..schemas.workflows.task_generation import TaskGenerationState
        workflow = StateGraph(TaskGenerationState)
        
        # Add nodes to graph
        workflow.add_node("analyze_prd_node", self._analyze_prd_node)
        workflow.add_node("breakdown_tasks_node", self._breakdown_tasks_node)
        workflow.add_node("define_dependencies_node", self._define_dependencies_node)
        workflow.add_node("estimate_effort_node", self._estimate_effort_node)
        workflow.add_node("generate_openspec_node", self._generate_openspec_node)
        workflow.add_node("error_handler", self._error_handler_node)
        
        # Add conditional edges for workflow flow
        workflow.add_conditional_edges(
            "analyze_prd_node",
            self._decide_next_step,
            {
                "breakdown_tasks_node": "breakdown_tasks_node",
                "error": "error_handler",
                "end": END
            }
        )
        
        workflow.add_conditional_edges(
            "breakdown_tasks_node",
            self._decide_next_step,
            {
                "define_dependencies_node": "define_dependencies_node",
                "error": "error_handler",
                "end": END
            }
        )
        
        workflow.add_conditional_edges(
            "define_dependencies_node",
            self._decide_next_step,
            {
                "estimate_effort_node": "estimate_effort_node",
                "error": "error_handler",
                "end": END
            }
        )
        
        workflow.add_conditional_edges(
            "estimate_effort_node",
            self._decide_next_step,
            {
                "generate_openspec_node": "generate_openspec_node",
                "error": "error_handler",
                "end": END
            }
        )
        
        workflow.add_conditional_edges(
            "generate_openspec_node",
            self._decide_next_step,
            {
                "end": END,
                "error": "error_handler"
            }
        )
        
        workflow.add_conditional_edges(
            "error_handler",
            self._decide_error_recovery,
            {
                "retry": "analyze_prd_node",  # Retry from start
                "end": END
            }
        )
        
        # Set entry point
        workflow.set_entry_point("analyze_prd_node")
        
        # Compile graph
        compiled_workflow = workflow.compile(checkpointer=self.checkpointer)
        
        self.logger.info("LangGraph StateGraph built successfully for Task Generation workflow")
        return compiled_workflow
    
    async def execute(
        self,
        prd_content: str,
        user_id: UUID,
        project_id: Optional[UUID] = None,
        project_context: Optional[Dict[str, Any]] = None,
        existing_tasks: Optional[List[Dict[str, Any]]] = None,
        parameters: Optional[Dict[str, Any]] = None,
        context: Optional[Dict[str, Any]] = None,
        progress_callback: Optional[Callable] = None,
    ) -> "TaskGenerationState":
        """
        Execute the Task Generation workflow.
        
        Args:
            prd_content: PRD document content
            user_id: User executing the workflow
            project_id: Associated project (optional)
            project_context: Project context and constraints (optional)
            existing_tasks: Existing tasks in project (optional)
            parameters: Workflow parameters (optional)
            context: Additional context (optional)
            progress_callback: Callback for progress updates (optional)
            
        Returns:
            TaskGenerationState with complete task breakdown and OpenSpec proposal
            
        Raises:
            TaskGenerationNodeException: If workflow fails critically
        """
        # Create workflow state
        workflow_id = uuid4()
        execution_id = uuid4()
        
        from datetime import datetime
        from ..schemas.workflows.task_generation import TaskGenerationState
        state = TaskGenerationState(
            workflow_id=workflow_id,
            execution_id=execution_id,
            workflow_type=WorkflowType.CUSTOM,  # Using CUSTOM for task generation workflow
            user_id=user_id,
            project_id=project_id,
            initial_request="Generate tasks and OpenSpec from PRD",
            prd_content=prd_content,
            project_context=project_context or {},
            existing_tasks=existing_tasks or [],
            context=context or {},
            parameters=parameters or {},
            created_at=datetime.utcnow().isoformat(),
        )
        
        # Add to active executions
        self.active_executions[execution_id] = state
        
        try:
            self.logger.info(f"Starting Task Generation workflow for PRD")
            
            # Create workflow context
            workflow_context = WorkflowContext(
                db_session=None,  # Simplified for now
                openrouter_client=OpenRouterClient(),
                qdrant_service=get_qdrant_service(),
                settings=self.config.model_dump(),
                progress_callback=progress_callback or self._default_progress_callback,
                error_callback=self._default_error_callback,
                logger=self.logger,
            )
            
            # Mark as running
            state.status = WorkflowStatus.RUNNING
            state.started_at = state._get_timestamp()
            state.update_task_progress("analyze_prd", 0)
            
            # Execute the graph
            config = {"configurable": {"thread_id": str(execution_id)}}
            
            result = await self.graph.ainvoke(
                {
                    "workflow_id": workflow_id,
                    "execution_id": execution_id,
                    "workflow_type": WorkflowType.CUSTOM,
                    "user_id": user_id,
                    "project_id": project_id,
                    "initial_request": "Generate tasks and OpenSpec from PRD",
                    "prd_content": prd_content,
                    "project_context": project_context or {},
                    "existing_tasks": existing_tasks or [],
                    "context": context or {},
                    "parameters": parameters or {},
                    # Don't pass workflow_context in state (not serializable)
                    "status": WorkflowStatus.RUNNING,
                    "created_at": state.created_at,
                    "started_at": state.started_at,
                    "current_task_step": "analyze_prd_node",
                    "task_progress_percentage": 0,
                    "completed_task_steps": [],
                    "failed_task_steps": [],
                    "retry_count": 0,
                    "errors": [],
                    "metadata": {},
                    "prd_analysis": None,
                    "feature_breakdown": None,
                    "technical_requirements": None,
                    "task_breakdown": None,
                    "epics_defined": None,
                    "subtasks_created": None,
                    "task_dependencies": None,
                    "dependency_graph": None,
                    "effort_estimates": None,
                    "resource_allocation": None,
                    "openspec_proposal": None,
                    "proposal_metadata": None,
                    "change_directory_path": None,
                    "prd_analysis_quality": 0.0,
                    "task_breakdown_completeness": 0.0,
                    "dependency_accuracy": 0.0,
                    "effort_estimation_quality": 0.0,
                    "openspec_quality_score": 0.0,
                    # step_results will be initialized by default_factory
                    "human_approval_points": [],
                    "human_edits_made": [],
                },
                config={"configurable": {"thread_id": str(execution_id)}}
            )
            
            # Update final state
            if isinstance(result, dict):
                for key, value in result.items():
                    if hasattr(state, key):
                        setattr(state, key, value)
            
            # Calculate final quality score
            final_quality_score = state.calculate_task_quality_score()
            state.metadata["final_quality_score"] = final_quality_score
            state.update_task_progress("completed", 100)
            
            # Mark as completed
            state.status = WorkflowStatus.COMPLETED
            state.completed_at = state._get_timestamp()
            
            self.logger.info(f"Task Generation workflow completed successfully for {execution_id}")
            return state
            
        except Exception as e:
            self.logger.error(f"Task Generation workflow failed: {e}")
            state.status = WorkflowStatus.FAILED
            state.completed_at = state._get_timestamp()
            state.errors.append({
                "error": str(e),
                "timestamp": state._get_timestamp(),
            })
            raise TaskGenerationNodeException(f"Task Generation workflow failed: {str(e)}") from e
        
        finally:
            # Remove from active executions
            if execution_id in self.active_executions:
                del self.active_executions[execution_id]
    
    async def _analyze_prd_node(self, state: "TaskGenerationState") -> "TaskGenerationState":
        """Execute PRD analysis node."""
        try:
            self.logger.info("Executing analyze_prd node")
            
            # Workflow context is not stored in state, get from instance
            workflow_context = self._get_workflow_context()
            if not workflow_context:
                raise TaskGenerationNodeException("Workflow context not available")
            
            # Execute node
            result = await self.nodes["analyze_prd"].execute(state, workflow_context)
            
            # Update state
            state.prd_analysis = result["analysis"]
            state.prd_analysis_quality = result["quality_score"]
            # Create step result from the analysis
            from ..schemas.workflows.task_generation import TaskGenerationStepResult
            step_result = TaskGenerationStepResult(
                step_name="analyze_prd",
                success=True,
                result_data=result["analysis"],
                error_message=None,
                confidence_score=result["quality_score"],
                tokens_used=None,
                cost_incurred=None,
                timestamp=self._get_timestamp()
            )
            state.mark_task_step_completed("analyze_prd", step_result)
            state.update_task_progress("breakdown_tasks", 20)
            state.current_task_step = "breakdown_tasks_node"  # Set next step for decision logic
            
            self.logger.info("analyze_prd node completed successfully")
            return state
            
        except Exception as e:
            self.logger.error(f"analyze_prd node failed: {e}")
            state.mark_task_step_failed("analyze_prd", str(e))
            state.current_task_step = "error"
            return state
    
    async def _breakdown_tasks_node(self, state: "TaskGenerationState") -> "TaskGenerationState":
        """Execute task breakdown node."""
        try:
            self.logger.info("Executing breakdown_tasks node")
            
            workflow_context = self._get_workflow_context()
            if not workflow_context:
                raise TaskGenerationNodeException("Workflow context not available")
            
            result = await self.nodes["breakdown_tasks"].execute(state, workflow_context)
            
            state.task_breakdown = result["all_tasks"]
            state.epics_defined = result["breakdown"]["epics"]
            state.task_breakdown_completeness = result["quality_score"]
            # Create step result from the breakdown
            from ..schemas.workflows.task_generation import TaskGenerationStepResult
            step_result = TaskGenerationStepResult(
                step_name="breakdown_tasks",
                success=True,
                result_data=result["breakdown"],
                error_message=None,
                confidence_score=result["quality_score"],
                tokens_used=None,
                cost_incurred=None,
                timestamp=self._get_timestamp()
            )
            state.mark_task_step_completed("breakdown_tasks", step_result)
            state.update_task_progress("define_dependencies", 40)
            state.current_task_step = "define_dependencies_node"  # Set next step for decision logic
            
            self.logger.info("breakdown_tasks node completed successfully")
            return state
            
        except Exception as e:
            self.logger.error(f"breakdown_tasks node failed: {e}")
            state.mark_task_step_failed("breakdown_tasks", str(e))
            state.current_task_step = "error"
            return state
    
    async def _define_dependencies_node(self, state: "TaskGenerationState") -> "TaskGenerationState":
        """Execute dependency definition node."""
        try:
            self.logger.info("Executing define_dependencies node")
            
            workflow_context = self._get_workflow_context()
            if not workflow_context:
                raise TaskGenerationNodeException("Workflow context not available")
            
            result = await self.nodes["define_dependencies"].execute(state, workflow_context)
            
            state.task_dependencies = result["dependencies"]["dependencies"]
            state.dependency_graph = result["dependencies"]["dependency_graph"]
            state.dependency_accuracy = result["quality_score"]
            # Create step result from the dependencies
            from ..schemas.workflows.task_generation import TaskGenerationStepResult
            step_result = TaskGenerationStepResult(
                step_name="define_dependencies",
                success=True,
                result_data=result["dependencies"],
                error_message=None,
                confidence_score=result["quality_score"],
                tokens_used=None,
                cost_incurred=None,
                timestamp=self._get_timestamp()
            )
            state.mark_task_step_completed("define_dependencies", step_result)
            state.update_task_progress("estimate_effort", 60)
            state.current_task_step = "estimate_effort_node"  # Set next step for decision logic
            
            self.logger.info("define_dependencies node completed successfully")
            return state
            
        except Exception as e:
            self.logger.error(f"define_dependencies node failed: {e}")
            state.mark_task_step_failed("define_dependencies", str(e))
            state.current_task_step = "error"
            return state
    
    async def _estimate_effort_node(self, state: "TaskGenerationState") -> "TaskGenerationState":
        """Execute effort estimation node."""
        try:
            self.logger.info("Executing estimate_effort node")
            
            workflow_context = self._get_workflow_context()
            if not workflow_context:
                raise TaskGenerationNodeException("Workflow context not available")
            
            result = await self.nodes["estimate_effort"].execute(state, workflow_context)
            
            state.effort_estimates = result["estimates"]
            state.resource_allocation = result["estimates"]["resource_allocation"]
            state.effort_estimation_quality = result["quality_score"]
            # Create step result from the estimates
            from ..schemas.workflows.task_generation import TaskGenerationStepResult
            step_result = TaskGenerationStepResult(
                step_name="estimate_effort",
                success=True,
                result_data=result["estimates"],
                error_message=None,
                confidence_score=result["quality_score"],
                tokens_used=None,
                cost_incurred=None,
                timestamp=self._get_timestamp()
            )
            state.mark_task_step_completed("estimate_effort", step_result)
            state.update_task_progress("generate_openspec", 80)
            state.current_task_step = "generate_openspec_node"  # Set next step for decision logic
            
            self.logger.info("estimate_effort node completed successfully")
            return state
            
        except Exception as e:
            self.logger.error(f"estimate_effort node failed: {e}")
            state.mark_task_step_failed("estimate_effort", str(e))
            state.current_task_step = "error"
            return state
    
    async def _generate_openspec_node(self, state: "TaskGenerationState") -> "TaskGenerationState":
        """Execute OpenSpec generation node."""
        try:
            self.logger.info("Executing generate_openspec node")
            
            workflow_context = self._get_workflow_context()
            if not workflow_context:
                raise TaskGenerationNodeException("Workflow context not available")
            
            result = await self.nodes["generate_openspec"].execute(state, workflow_context)
            
            state.openspec_proposal = result["openspec"]
            state.proposal_metadata = result["openspec"]["metadata"]
            state.change_directory_path = result["change_directory"]
            state.generated_files = result.get("generated_files", {})
            state.openspec_quality_score = result["quality_score"]
            # Create step result from the openspec
            from ..schemas.workflows.task_generation import TaskGenerationStepResult
            step_result = TaskGenerationStepResult(
                step_name="generate_openspec",
                success=True,
                result_data=result["openspec"],
                error_message=None,
                confidence_score=result["quality_score"],
                tokens_used=None,
                cost_incurred=None,
                timestamp=self._get_timestamp()
            )
            state.mark_task_step_completed("generate_openspec", step_result)
            state.update_task_progress("completed", 100)
            state.current_task_step = "end"  # Signal completion
            
            # Save generated tasks to database
            try:
                from ..services.task_generation_service import get_task_generation_service
                task_gen_service = get_task_generation_service()
                
                # Save tasks if we have project and user context
                if hasattr(state, 'project_id') and hasattr(state, 'user_id') and state.project_id and state.user_id:
                    task_ids, epic_ids = await task_gen_service.save_generated_tasks(
                        getattr(state, 'task_breakdown', []),
                        state.project_id,
                        state.user_id,
                        state.workflow_id
                    )
                    
                    # Save dependencies
                    if hasattr(state, 'task_dependencies'):
                        await task_gen_service.save_task_dependencies(
                            getattr(state, 'task_dependencies', []),
                            getattr(state, 'task_breakdown', []),
                            task_ids
                        )
                    
                    # Link OpenSpec to project
                    if hasattr(state, 'openspec_proposal') and state.project_id and state.user_id:
                        await task_gen_service.link_openspec_to_project(
                            getattr(state, 'change_directory_path', '').split('/')[-1],
                            state.project_id,
                            state.user_id,
                            state.workflow_id,
                            getattr(state, 'openspec_proposal', {})
                        )
                    
                    self.logger.info(f"Saved {len(task_ids)} tasks to database")
                else:
                    self.logger.warning("No project_id or user_id in state - skipping database save")
                    
            except Exception as e:
                self.logger.error(f"Failed to save tasks to database: {e}")
                # Continue without failing the workflow
            
            self.logger.info("generate_openspec node completed successfully")
            return state
            
        except Exception as e:
            self.logger.error(f"generate_openspec node failed: {e}")
            state.mark_task_step_failed("generate_openspec", str(e))
            state.current_task_step = "error"
            return state
    
    async def _error_handler_node(self, state: "TaskGenerationState") -> "TaskGenerationState":
        """Handle errors and decide on recovery strategy."""
        self.logger.warning("Entering error handler node")
        
        # Check retry count
        if state.retry_count < self.config.max_retries_per_step:
            state.retry_count += 1
            self.logger.info(f"Retrying Task Generation workflow (attempt {state.retry_count})")
            state.current_task_step = "retry"
        else:
            self.logger.error("Max retries exceeded, ending Task Generation workflow")
            state.current_task_step = "end"
            state.status = WorkflowStatus.FAILED
        
        return state
    
    def _decide_next_step(self, state: "TaskGenerationState") -> str:
        """
        Decide the next step based on current state.
        
        Args:
            state: Current workflow state
            
        Returns:
            Next step name
        """
        # Check for errors
        if state.current_task_step == "error":
            return "error"
        
        # Check if workflow should end
        if state.current_task_step == "end":
            return "end"
        
        # Get the last completed step to determine next step
        if state.completed_task_steps:
            last_completed = state.completed_task_steps[-1]
            step_mapping = {
                "analyze_prd": "breakdown_tasks_node",
                "breakdown_tasks": "define_dependencies_node",
                "define_dependencies": "estimate_effort_node",
                "estimate_effort": "generate_openspec_node",
                "generate_openspec": "end",
            }
            
            if last_completed in step_mapping:
                return step_mapping[last_completed]
        
        # Default to breakdown_tasks_node (first step after analyze_prd)
        return "breakdown_tasks_node"
    
    def _decide_error_recovery(self, state: "TaskGenerationState") -> str:
        """
        Decide error recovery strategy.
        
        Args:
            state: Current workflow state
            
        Returns:
            Recovery action
        """
        if state.retry_count < self.config.max_retries_per_step:
            return "retry"
        else:
            return "end"
    
    async def _default_progress_callback(self, progress_update: "TaskGenerationProgressUpdate") -> None:
        """
        Default progress callback for streaming updates.
        
        Args:
            progress_update: Progress update information
        """
        try:
            # Log progress (Redis integration removed for simplicity)
            self.logger.info(
                f"Task Generation Progress: {progress_update.current_step} - "
                f"{progress_update.progress_percentage}% - "
                f"{progress_update.step_status}"
            )
            
        except Exception as e:
            self.logger.warning(f"Failed to handle Task Generation progress update: {e}")
    
    async def _default_error_callback(self, execution_id: UUID, node_name: str, error: Dict[str, Any]) -> None:
        """
        Default error callback for error handling.
        
        Args:
            execution_id: Workflow execution ID
            node_name: Name of node that failed
            error: Error details
        """
        try:
            # Log error (Redis integration removed for simplicity)
            self.logger.error(f"Error in Task Generation {node_name}: {error}")
            
        except Exception as e:
            self.logger.warning(f"Failed to handle Task Generation error callback: {e}")
    
    def _get_timestamp(self) -> str:
        """Get current timestamp in ISO format."""
        from datetime import datetime, timezone
        return datetime.now(timezone.utc).isoformat() + "Z"
    
    def _get_workflow_context(self) -> WorkflowContext:
        """Get or create workflow context."""
        if not hasattr(self, '_workflow_context'):
            self._workflow_context = WorkflowContext(
                db_session=None,  # Simplified for now
                openrouter_client=OpenRouterClient(),
                qdrant_service=get_qdrant_service(),
                settings=self.config.model_dump(),
                progress_callback=self._default_progress_callback,
                error_callback=self._default_error_callback,
                logger=self.logger,
            )
        return self._workflow_context
    
    async def get_execution_status(self, execution_id: UUID) -> Optional["TaskGenerationState"]:
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
        
        self.logger.info(f"Cancelled Task Generation workflow execution: {execution_id}")
        return True
    
    async def get_progress_from_redis(self, execution_id: UUID) -> Optional["TaskGenerationProgressUpdate"]:
        """
        Get progress update from Redis.
        
        Args:
            execution_id: Execution identifier
            
        Returns:
            Progress update or None if not found
        """
        # Redis integration removed for simplicity
        return None


# Global workflow instance
_task_generation_workflow: Optional[TaskGenerationWorkflow] = None


def get_task_generation_workflow(config: Optional["TaskGenerationWorkflowConfig"] = None) -> "TaskGenerationWorkflow":
    """
    Get cached Task Generation workflow instance.
    
    Args:
        config: Optional workflow configuration
        
    Returns:
        TaskGenerationWorkflow instance
    """
    global _task_generation_workflow
    if _task_generation_workflow is None:
        _task_generation_workflow = TaskGenerationWorkflow(config)
    return _task_generation_workflow