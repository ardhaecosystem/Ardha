"""
Research workflow implementation with LangGraph StateGraph.

This module implements the multi-agent research workflow using
LangGraph for orchestration, with proper state management,
error recovery, and streaming progress updates.
"""

import asyncio
import json
import logging
from typing import Any, Callable, Dict, List, Optional, Union
from uuid import UUID, uuid4

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, StateGraph

from ..core.openrouter import OpenRouterClient
from ..core.qdrant import get_qdrant_service
from ..schemas.workflows.research import (
    ResearchProgressUpdate,
    ResearchState,
    ResearchWorkflowConfig,
)
from .nodes.research_nodes import (
    AnalyzeIdeaNode,
    CompetitiveAnalysisNode,
    MarketResearchNode,
    ResearchNodeException,
    SynthesizeResearchNode,
    TechnicalFeasibilityNode,
)
from .state import WorkflowContext, WorkflowStatus, WorkflowType

logger = logging.getLogger(__name__)


class ResearchWorkflow:
    """
    Multi-agent research workflow using LangGraph StateGraph.

    Orchestrates the research process through multiple specialized
    AI agents, with state persistence, error recovery, and streaming.
    """

    def __init__(self, config: Optional[ResearchWorkflowConfig] = None):
        """
        Initialize research workflow.

        Args:
            config: Workflow configuration (optional)
        """
        self.config = config or ResearchWorkflowConfig()
        self.logger = logger.getChild("ResearchWorkflow")

        # Initialize nodes
        self.nodes = {
            "analyze_idea": AnalyzeIdeaNode(),
            "market_research": MarketResearchNode(),
            "competitive_analysis": CompetitiveAnalysisNode(),
            "technical_feasibility": TechnicalFeasibilityNode(),
            "synthesize": SynthesizeResearchNode(),
        }

        # Initialize checkpoint saver for state persistence
        self.checkpointer = MemorySaver()

        # Initialize LangGraph StateGraph
        self.graph = self._build_graph()

        # Active executions tracking
        self.active_executions: Dict[UUID, ResearchState] = {}

        self.logger.info("Research workflow initialized")

    def _build_graph(self):
        """
        Build the LangGraph StateGraph for research workflow.

        Returns:
            Configured StateGraph instance
        """
        # Create StateGraph with ResearchState
        workflow = StateGraph(ResearchState)

        # Add nodes to graph
        workflow.add_node("analyze_idea_node", self._analyze_idea_node)
        workflow.add_node("market_research_node", self._market_research_node)
        workflow.add_node("competitive_analysis_node", self._competitive_analysis_node)
        workflow.add_node("technical_feasibility_node", self._technical_feasibility_node)
        workflow.add_node("synthesize_node", self._synthesize_node)
        workflow.add_node("error_handler", self._error_handler_node)

        # Add conditional edges for workflow flow
        workflow.add_conditional_edges(
            "analyze_idea_node",
            self._decide_next_step,
            {"market_research_node": "market_research_node", "error": "error_handler", "end": END},
        )

        workflow.add_conditional_edges(
            "market_research_node",
            self._decide_next_step,
            {
                "competitive_analysis_node": "competitive_analysis_node",
                "error": "error_handler",
                "end": END,
            },
        )

        workflow.add_conditional_edges(
            "competitive_analysis_node",
            self._decide_next_step,
            {
                "technical_feasibility_node": "technical_feasibility_node",
                "error": "error_handler",
                "end": END,
            },
        )

        workflow.add_conditional_edges(
            "technical_feasibility_node",
            self._decide_next_step,
            {"synthesize_node": "synthesize_node", "error": "error_handler", "end": END},
        )

        workflow.add_conditional_edges(
            "synthesize_node", self._decide_next_step, {"end": END, "error": "error_handler"}
        )

        workflow.add_conditional_edges(
            "error_handler",
            self._decide_error_recovery,
            {"retry": "analyze_idea_node", "end": END},  # Retry from start
        )

        # Set entry point
        workflow.set_entry_point("analyze_idea_node")

        # Compile graph
        compiled_workflow = workflow.compile(checkpointer=self.checkpointer)

        self.logger.info("LangGraph StateGraph built successfully")
        return compiled_workflow

    async def execute(
        self,
        idea: str,
        user_id: UUID,
        project_id: Optional[UUID] = None,
        parameters: Optional[Dict[str, Any]] = None,
        context: Optional[Dict[str, Any]] = None,
        progress_callback: Optional[Callable] = None,
    ) -> ResearchState:
        """
        Execute the research workflow.

        Args:
            idea: The product idea to research
            user_id: User executing the workflow
            project_id: Associated project (optional)
            parameters: Workflow parameters (optional)
            context: Additional context (optional)
            progress_callback: Callback for progress updates (optional)

        Returns:
            ResearchState with complete results

        Raises:
            ResearchNodeException: If workflow fails critically
        """
        # Create workflow state
        workflow_id = uuid4()
        execution_id = uuid4()

        from datetime import datetime

        state = ResearchState(
            workflow_id=workflow_id,
            execution_id=execution_id,
            workflow_type=WorkflowType.RESEARCH,
            user_id=user_id,
            project_id=project_id,
            initial_request=idea,
            idea=idea,  # Research-specific field
            context=context or {},
            parameters=parameters or {},
            created_at=datetime.utcnow().isoformat(),
        )

        # Add to active executions
        self.active_executions[execution_id] = state

        try:
            self.logger.info(f"Starting research workflow for idea: {idea[:100]}...")

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
            state.update_progress("analyze_idea", 0)

            # Execute the graph
            config = {"configurable": {"thread_id": str(execution_id)}}

            result = await self.graph.ainvoke(
                {
                    "workflow_id": workflow_id,
                    "execution_id": execution_id,
                    "workflow_type": WorkflowType.RESEARCH,
                    "idea": idea,
                    "user_id": user_id,
                    "project_id": project_id,
                    "initial_request": idea,
                    "context": context or {},
                    "parameters": parameters or {},
                    # Don't pass workflow_context in state (not serializable)
                    "status": WorkflowStatus.RUNNING,
                    "created_at": state.created_at,
                    "started_at": state.started_at,
                    "current_step": "analyze_idea",
                    "progress_percentage": 0,
                    "completed_nodes": [],
                    "failed_nodes": [],
                    "retry_count": 0,
                    "errors": [],
                    "metadata": {},
                    "idea_analysis": None,
                    "market_research": None,
                    "competitive_analysis": None,
                    "technical_feasibility": None,
                    "research_summary": None,
                    "research_confidence": 0.0,
                    "sources_found": 0,
                    "hypotheses_generated": 0,
                    "analysis_depth_score": 0.0,
                    "market_data_quality": 0.0,
                    "competitor_coverage": 0.0,
                    "technical_detail_level": 0.0,
                },
                config={"configurable": {"thread_id": str(execution_id)}},
            )

            # Update final state
            if isinstance(result, dict):
                for key, value in result.items():
                    if hasattr(state, key):
                        setattr(state, key, value)

            # Calculate final metrics
            state.calculate_research_confidence()
            state.update_progress("completed", 100)

            # Mark as completed
            state.status = WorkflowStatus.COMPLETED
            state.completed_at = state._get_timestamp()

            self.logger.info(f"Research workflow completed successfully for {execution_id}")
            return state

        except Exception as e:
            self.logger.error(f"Research workflow failed: {e}")
            state.status = WorkflowStatus.FAILED
            state.completed_at = state._get_timestamp()
            state.errors.append(
                {
                    "error": str(e),
                    "timestamp": state._get_timestamp(),
                }
            )
            raise ResearchNodeException(f"Research workflow failed: {str(e)}") from e

        finally:
            # Remove from active executions
            if execution_id in self.active_executions:
                del self.active_executions[execution_id]

    async def _analyze_idea_node(self, state: ResearchState) -> ResearchState:
        """Execute idea analysis node."""
        try:
            self.logger.info("Executing analyze_idea node")

            # Workflow context is not stored in state, get from instance
            workflow_context = self._get_workflow_context()
            if not workflow_context:
                raise ResearchNodeException("Workflow context not available")

            # Execute node
            result = await self.nodes["analyze_idea"].execute(state, workflow_context)

            # Update state
            state.idea_analysis = result
            state.mark_node_completed("analyze_idea", result)
            state.update_progress("market_research", 20)

            # Update quality metrics
            if "confidence_score" in result:
                state.analysis_depth_score = result["confidence_score"]

            self.logger.info("analyze_idea node completed successfully")
            return state

        except Exception as e:
            self.logger.error(f"analyze_idea node failed: {e}")
            state.mark_node_failed("analyze_idea", {"error": str(e)})
            state.current_step = "error"
            return state

    async def _market_research_node(self, state: ResearchState) -> ResearchState:
        """Execute market research node."""
        try:
            self.logger.info("Executing market_research node")

            workflow_context = self._get_workflow_context()
            if not workflow_context:
                raise ResearchNodeException("Workflow context not available")

            result = await self.nodes["market_research"].execute(state, workflow_context)

            state.market_research = result
            state.mark_node_completed("market_research", result)
            state.update_progress("competitive_analysis", 40)

            # Update quality metrics
            if "confidence_score" in result:
                state.market_data_quality = result["confidence_score"]

            self.logger.info("market_research node completed successfully")
            return state

        except Exception as e:
            self.logger.error(f"market_research node failed: {e}")
            state.mark_node_failed("market_research", {"error": str(e)})
            state.current_step = "error"
            return state

    async def _competitive_analysis_node(self, state: ResearchState) -> ResearchState:
        """Execute competitive analysis node."""
        try:
            self.logger.info("Executing competitive_analysis node")

            workflow_context = self._get_workflow_context()
            if not workflow_context:
                raise ResearchNodeException("Workflow context not available")

            result = await self.nodes["competitive_analysis"].execute(state, workflow_context)

            state.competitive_analysis = result
            state.mark_node_completed("competitive_analysis", result)
            state.update_progress("technical_feasibility", 60)

            # Update quality metrics
            if "confidence_score" in result:
                state.competitor_coverage = result["confidence_score"]

            self.logger.info("competitive_analysis node completed successfully")
            return state

        except Exception as e:
            self.logger.error(f"competitive_analysis node failed: {e}")
            state.mark_node_failed("competitive_analysis", {"error": str(e)})
            state.current_step = "error"
            return state

    async def _technical_feasibility_node(self, state: ResearchState) -> ResearchState:
        """Execute technical feasibility node."""
        try:
            self.logger.info("Executing technical_feasibility node")

            workflow_context = self._get_workflow_context()
            if not workflow_context:
                raise ResearchNodeException("Workflow context not available")

            result = await self.nodes["technical_feasibility"].execute(state, workflow_context)

            state.technical_feasibility = result
            state.mark_node_completed("technical_feasibility", result)
            state.update_progress("synthesize", 80)

            # Update quality metrics
            if "confidence_score" in result:
                state.technical_detail_level = result["confidence_score"]

            self.logger.info("technical_feasibility node completed successfully")
            return state

        except Exception as e:
            self.logger.error(f"technical_feasibility node failed: {e}")
            state.mark_node_failed("technical_feasibility", {"error": str(e)})
            state.current_step = "error"
            return state

    async def _synthesize_node(self, state: ResearchState) -> ResearchState:
        """Execute synthesis node."""
        try:
            self.logger.info("Executing synthesize node")

            workflow_context = self._get_workflow_context()
            if not workflow_context:
                raise ResearchNodeException("Workflow context not available")

            result = await self.nodes["synthesize"].execute(state, workflow_context)

            state.research_summary = result
            state.mark_node_completed("synthesize", result)
            state.update_progress("completed", 100)

            self.logger.info("synthesize node completed successfully")
            return state

        except Exception as e:
            self.logger.error(f"synthesize node failed: {e}")
            state.mark_node_failed("synthesize", {"error": str(e)})
            state.current_step = "error"
            return state

    async def _error_handler_node(self, state: ResearchState) -> ResearchState:
        """Handle errors and decide on recovery strategy."""
        self.logger.warning("Entering error handler node")

        # Check retry count
        if state.retry_count < self.config.max_retries_per_step:
            state.retry_count += 1
            self.logger.info(f"Retrying workflow (attempt {state.retry_count})")
            state.current_step = "retry"
        else:
            self.logger.error("Max retries exceeded, ending workflow")
            state.current_step = "end"
            state.status = WorkflowStatus.FAILED

        return state

    def _decide_next_step(self, state: ResearchState) -> str:
        """
        Decide the next step based on current state.

        Args:
            state: Current workflow state

        Returns:
            Next step name
        """
        # Check for errors
        if state.current_step == "error":
            return "error"

        # Check if workflow should end
        if state.current_step == "end":
            return "end"

        # Normal flow progression
        step_mapping = {
            "analyze_idea_node": "market_research_node",
            "market_research_node": "competitive_analysis_node",
            "competitive_analysis_node": "technical_feasibility_node",
            "technical_feasibility_node": "synthesize_node",
            "synthesize_node": "end",
        }

        current_step = state.current_step
        if current_step in step_mapping:
            return step_mapping[current_step]

        # Default to next step in sequence
        return "end"

    def _decide_error_recovery(self, state: ResearchState) -> str:
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

    async def _default_progress_callback(self, progress_update: ResearchProgressUpdate) -> None:
        """
        Default progress callback for streaming updates.

        Args:
            progress_update: Progress update information
        """
        try:
            # Log progress (Redis integration removed for simplicity)
            self.logger.info(
                f"Progress: {progress_update.current_step} - "
                f"{progress_update.progress_percentage}% - "
                f"{progress_update.step_status}"
            )

        except Exception as e:
            self.logger.warning(f"Failed to handle progress update: {e}")

    async def _default_error_callback(
        self, execution_id: UUID, node_name: str, error: Dict[str, Any]
    ) -> None:
        """
        Default error callback for error handling.

        Args:
            execution_id: Workflow execution ID
            node_name: Name of node that failed
            error: Error details
        """
        try:
            # Log error (Redis integration removed for simplicity)
            self.logger.error(f"Error in {node_name}: {error}")

        except Exception as e:
            self.logger.warning(f"Failed to handle error callback: {e}")

    def _get_timestamp(self) -> str:
        """Get current timestamp in ISO format."""
        from datetime import datetime, timezone

        return datetime.now(timezone.utc).isoformat() + "Z"

    def _get_workflow_context(self) -> WorkflowContext:
        """Get or create workflow context."""
        if not hasattr(self, "_workflow_context"):
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

    async def get_execution_status(self, execution_id: UUID) -> Optional[ResearchState]:
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

        self.logger.info(f"Cancelled research workflow execution: {execution_id}")
        return True

    async def get_progress_from_redis(self, execution_id: UUID) -> Optional[ResearchProgressUpdate]:
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
_research_workflow: Optional[ResearchWorkflow] = None


def get_research_workflow(config: Optional[ResearchWorkflowConfig] = None) -> ResearchWorkflow:
    """
    Get cached research workflow instance.

    Args:
        config: Optional workflow configuration

    Returns:
        ResearchWorkflow instance
    """
    global _research_workflow
    if _research_workflow is None:
        _research_workflow = ResearchWorkflow(config)
    return _research_workflow
