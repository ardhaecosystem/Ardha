"""
PRD (Product Requirements Document) workflow implementation with LangGraph StateGraph.

This module implements the PRD generation workflow using LangGraph for
orchestration, with proper state management, error recovery, and streaming.
"""

import asyncio
import logging
from typing import Any, Dict, List, Optional, Union
from uuid import UUID, uuid4

from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver

import json
from typing import Callable

from ..core.openrouter import OpenRouterClient
from ..core.qdrant import get_qdrant_service
from .state import WorkflowStatus, WorkflowContext, WorkflowType
from .nodes.prd_nodes import (
    ExtractRequirementsNode, DefineFeaturesNode, SetMetricsNode,
    GeneratePRDNode, ReviewFormatNode, PRDNodeException
)
from ..schemas.workflows.prd import PRDState, PRDWorkflowConfig, PRDProgressUpdate

logger = logging.getLogger(__name__)


class PRDWorkflow:
    """
    PRD generation workflow using LangGraph StateGraph.
    
    Orchestrates the conversion of research into structured requirements
    and generates comprehensive PRD documents with state persistence.
    """
    
    def __init__(self, config: Optional[PRDWorkflowConfig] = None):
        """
        Initialize PRD workflow.
        
        Args:
            config: Workflow configuration (optional)
        """
        self.config = config or PRDWorkflowConfig()
        self.logger = logger.getChild("PRDWorkflow")
        
        # Initialize nodes
        self.nodes = {
            "extract_requirements": ExtractRequirementsNode(),
            "define_features": DefineFeaturesNode(),
            "set_metrics": SetMetricsNode(),
            "generate_prd": GeneratePRDNode(),
            "review_format": ReviewFormatNode(),
        }
        
        # Initialize checkpoint saver for state persistence
        self.checkpointer = MemorySaver()
        
        # Initialize LangGraph StateGraph
        self.graph = self._build_graph()
        
        # Active executions tracking
        self.active_executions: Dict[UUID, PRDState] = {}
        
        self.logger.info("PRD workflow initialized")
    
    def _build_graph(self):
        """
        Build the LangGraph StateGraph for PRD workflow.
        
        Returns:
            Configured StateGraph instance
        """
        # Create StateGraph with PRDState
        workflow = StateGraph(PRDState)
        
        # Add nodes to graph
        workflow.add_node("extract_requirements_node", self._extract_requirements_node)
        workflow.add_node("define_features_node", self._define_features_node)
        workflow.add_node("set_metrics_node", self._set_metrics_node)
        workflow.add_node("generate_prd_node", self._generate_prd_node)
        workflow.add_node("review_format_node", self._review_format_node)
        workflow.add_node("error_handler", self._error_handler_node)
        
        # Add conditional edges for workflow flow
        workflow.add_conditional_edges(
            "extract_requirements_node",
            self._decide_next_step,
            {
                "define_features_node": "define_features_node",
                "error": "error_handler",
                "end": END
            }
        )
        
        workflow.add_conditional_edges(
            "define_features_node",
            self._decide_next_step,
            {
                "set_metrics_node": "set_metrics_node",
                "error": "error_handler",
                "end": END
            }
        )
        
        workflow.add_conditional_edges(
            "set_metrics_node",
            self._decide_next_step,
            {
                "generate_prd_node": "generate_prd_node",
                "error": "error_handler",
                "end": END
            }
        )
        
        workflow.add_conditional_edges(
            "generate_prd_node",
            self._decide_next_step,
            {
                "review_format_node": "review_format_node",
                "error": "error_handler",
                "end": END
            }
        )
        
        workflow.add_conditional_edges(
            "review_format_node",
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
                "retry": "extract_requirements_node",  # Retry from start
                "end": END
            }
        )
        
        # Set entry point
        workflow.set_entry_point("extract_requirements_node")
        
        # Compile graph
        compiled_workflow = workflow.compile(checkpointer=self.checkpointer)
        
        self.logger.info("LangGraph StateGraph built successfully for PRD workflow")
        return compiled_workflow
    
    async def execute(
        self,
        research_summary: Dict[str, Any],
        user_id: UUID,
        project_id: Optional[UUID] = None,
        parameters: Optional[Dict[str, Any]] = None,
        context: Optional[Dict[str, Any]] = None,
        progress_callback: Optional[Callable] = None,
    ) -> PRDState:
        """
        Execute the PRD generation workflow.
        
        Args:
            research_summary: Research summary from research workflow
            user_id: User executing the workflow
            project_id: Associated project (optional)
            parameters: Workflow parameters (optional)
            context: Additional context (optional)
            progress_callback: Callback for progress updates (optional)
            
        Returns:
            PRDState with complete PRD document
            
        Raises:
            PRDNodeException: If workflow fails critically
        """
        # Create workflow state
        workflow_id = uuid4()
        execution_id = uuid4()
        
        from datetime import datetime
        state = PRDState(
            workflow_id=workflow_id,
            execution_id=execution_id,
            workflow_type=WorkflowType.CUSTOM,  # Using CUSTOM for PRD workflow
            user_id=user_id,
            project_id=project_id,
            initial_request="Generate PRD from research summary",
            research_summary=research_summary,
            context=context or {},
            parameters=parameters or {},
            created_at=datetime.utcnow().isoformat(),
        )
        
        # Add to active executions
        self.active_executions[execution_id] = state
        
        try:
            self.logger.info(f"Starting PRD workflow for research summary")
            
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
            state.update_prd_progress("extract_requirements", 0)
            
            # Execute the graph
            config = {"configurable": {"thread_id": str(execution_id)}}
            
            result = await self.graph.ainvoke(
                {
                    "workflow_id": workflow_id,
                    "execution_id": execution_id,
                    "workflow_type": WorkflowType.CUSTOM,
                    "user_id": user_id,
                    "project_id": project_id,
                    "initial_request": "Generate PRD from research summary",
                    "research_summary": research_summary,
                    "context": context or {},
                    "parameters": parameters or {},
                    # Don't pass workflow_context in state (not serializable)
                    "status": WorkflowStatus.RUNNING,
                    "created_at": state.created_at,
                    "started_at": state.started_at,
                    "current_prd_step": "extract_requirements",
                    "prd_progress_percentage": 0,
                    "completed_nodes": [],
                    "failed_nodes": [],
                    "retry_count": 0,
                    "errors": [],
                    "metadata": {},
                    "requirements": None,
                    "features": None,
                    "success_metrics": None,
                    "prd_content": None,
                    "final_prd": None,
                    "version": "1.0.0",
                    "last_updated": None,
                    "requirements_completeness": 0.0,
                    "feature_prioritization_quality": 0.0,
                    "metrics_specificity": 0.0,
                    "document_coherence": 0.0,
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
            final_quality_score = state.calculate_prd_quality_score()
            state.metadata["final_quality_score"] = final_quality_score
            state.update_prd_progress("completed", 100)
            
            # Mark as completed
            state.status = WorkflowStatus.COMPLETED
            state.completed_at = state._get_timestamp()
            
            self.logger.info(f"PRD workflow completed successfully for {execution_id}")
            return state
            
        except Exception as e:
            self.logger.error(f"PRD workflow failed: {e}")
            state.status = WorkflowStatus.FAILED
            state.completed_at = state._get_timestamp()
            state.errors.append({
                "error": str(e),
                "timestamp": state._get_timestamp(),
            })
            raise PRDNodeException(f"PRD workflow failed: {str(e)}") from e
        
        finally:
            # Remove from active executions
            if execution_id in self.active_executions:
                del self.active_executions[execution_id]
    
    async def _extract_requirements_node(self, state: PRDState) -> PRDState:
        """Execute requirements extraction node."""
        try:
            self.logger.info("Executing extract_requirements node")
            
            # Workflow context is not stored in state, get from instance
            workflow_context = self._get_workflow_context()
            if not workflow_context:
                raise PRDNodeException("Workflow context not available")
            
            # Execute node
            result = await self.nodes["extract_requirements"].execute(state, workflow_context)
            
            # Update state
            state.requirements = result["requirements"]
            state.mark_node_completed("extract_requirements", result)
            state.update_prd_progress("define_features", 20)
            
            # Update quality metrics
            state.requirements_completeness = result["completeness_score"]
            
            self.logger.info("extract_requirements node completed successfully")
            return state
            
        except Exception as e:
            self.logger.error(f"extract_requirements node failed: {e}")
            state.mark_node_failed("extract_requirements", {"error": str(e)})
            state.current_prd_step = "error"
            return state
    
    async def _define_features_node(self, state: PRDState) -> PRDState:
        """Execute feature definition node."""
        try:
            self.logger.info("Executing define_features node")
            
            workflow_context = self._get_workflow_context()
            if not workflow_context:
                raise PRDNodeException("Workflow context not available")
            
            result = await self.nodes["define_features"].execute(state, workflow_context)
            
            state.features = result["features"]
            state.mark_node_completed("define_features", result)
            state.update_prd_progress("set_metrics", 40)
            
            # Update quality metrics
            state.feature_prioritization_quality = result["prioritization_quality"]
            
            self.logger.info("define_features node completed successfully")
            return state
            
        except Exception as e:
            self.logger.error(f"define_features node failed: {e}")
            state.mark_node_failed("define_features", {"error": str(e)})
            state.current_prd_step = "error"
            return state
    
    async def _set_metrics_node(self, state: PRDState) -> PRDState:
        """Execute metrics definition node."""
        try:
            self.logger.info("Executing set_metrics node")
            
            workflow_context = self._get_workflow_context()
            if not workflow_context:
                raise PRDNodeException("Workflow context not available")
            
            result = await self.nodes["set_metrics"].execute(state, workflow_context)
            
            state.success_metrics = result["success_metrics"]
            state.mark_node_completed("set_metrics", result)
            state.update_prd_progress("generate_prd", 60)
            
            # Update quality metrics
            state.metrics_specificity = result["specificity_score"]
            
            self.logger.info("set_metrics node completed successfully")
            return state
            
        except Exception as e:
            self.logger.error(f"set_metrics node failed: {e}")
            state.mark_node_failed("set_metrics", {"error": str(e)})
            state.current_prd_step = "error"
            return state
    
    async def _generate_prd_node(self, state: PRDState) -> PRDState:
        """Execute PRD generation node."""
        try:
            self.logger.info("Executing generate_prd node")
            
            workflow_context = self._get_workflow_context()
            if not workflow_context:
                raise PRDNodeException("Workflow context not available")
            
            result = await self.nodes["generate_prd"].execute(state, workflow_context)
            
            state.prd_content = result["prd_content"]
            state.mark_node_completed("generate_prd", result)
            state.update_prd_progress("review_format", 80)
            
            # Update quality metrics
            state.document_coherence = result.get("coherence_score", 0.8)
            
            self.logger.info("generate_prd node completed successfully")
            return state
            
        except Exception as e:
            self.logger.error(f"generate_prd node failed: {e}")
            state.mark_node_failed("generate_prd", {"error": str(e)})
            state.current_prd_step = "error"
            return state
    
    async def _review_format_node(self, state: PRDState) -> PRDState:
        """Execute review and format node."""
        try:
            self.logger.info("Executing review_format node")
            
            workflow_context = self._get_workflow_context()
            if not workflow_context:
                raise PRDNodeException("Workflow context not available")
            
            result = await self.nodes["review_format"].execute(state, workflow_context)
            
            state.final_prd = result["final_prd"]
            state.mark_node_completed("review_format", result)
            state.update_prd_progress("completed", 100)
            
            self.logger.info("review_format node completed successfully")
            return state
            
        except Exception as e:
            self.logger.error(f"review_format node failed: {e}")
            state.mark_node_failed("review_format", {"error": str(e)})
            state.current_prd_step = "error"
            return state
    
    async def _error_handler_node(self, state: PRDState) -> PRDState:
        """Handle errors and decide on recovery strategy."""
        self.logger.warning("Entering error handler node")
        
        # Check retry count
        if state.retry_count < self.config.max_retries_per_step:
            state.retry_count += 1
            self.logger.info(f"Retrying PRD workflow (attempt {state.retry_count})")
            state.current_prd_step = "retry"
        else:
            self.logger.error("Max retries exceeded, ending PRD workflow")
            state.current_prd_step = "end"
            state.status = WorkflowStatus.FAILED
        
        return state
    
    def _decide_next_step(self, state: PRDState) -> str:
        """
        Decide the next step based on current state.
        
        Args:
            state: Current workflow state
            
        Returns:
            Next step name
        """
        # Check for errors
        if state.current_prd_step == "error":
            return "error"
        
        # Check if workflow should end
        if state.current_prd_step == "end":
            return "end"
        
        # Normal flow progression
        step_mapping = {
            "extract_requirements_node": "define_features_node",
            "define_features_node": "set_metrics_node",
            "set_metrics_node": "generate_prd_node",
            "generate_prd_node": "review_format_node",
            "review_format_node": "end",
        }
        
        current_step = state.current_prd_step
        if current_step in step_mapping:
            return step_mapping[current_step]
        
        # Default to next step in sequence
        return "end"
    
    def _decide_error_recovery(self, state: PRDState) -> str:
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
    
    async def _default_progress_callback(self, progress_update: PRDProgressUpdate) -> None:
        """
        Default progress callback for streaming updates.
        
        Args:
            progress_update: Progress update information
        """
        try:
            # Log progress (Redis integration removed for simplicity)
            self.logger.info(
                f"PRD Progress: {progress_update.current_step} - "
                f"{progress_update.progress_percentage}% - "
                f"{progress_update.step_status}"
            )
            
        except Exception as e:
            self.logger.warning(f"Failed to handle PRD progress update: {e}")
    
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
            self.logger.error(f"Error in PRD {node_name}: {error}")
            
        except Exception as e:
            self.logger.warning(f"Failed to handle PRD error callback: {e}")
    
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
    
    async def get_execution_status(self, execution_id: UUID) -> Optional[PRDState]:
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
        
        self.logger.info(f"Cancelled PRD workflow execution: {execution_id}")
        return True
    
    async def get_progress_from_redis(self, execution_id: UUID) -> Optional[PRDProgressUpdate]:
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
_prd_workflow: Optional[PRDWorkflow] = None


def get_prd_workflow(config: Optional[PRDWorkflowConfig] = None) -> PRDWorkflow:
    """
    Get cached PRD workflow instance.
    
    Args:
        config: Optional workflow configuration
        
    Returns:
        PRDWorkflow instance
    """
    global _prd_workflow
    if _prd_workflow is None:
        _prd_workflow = PRDWorkflow(config)
    return _prd_workflow