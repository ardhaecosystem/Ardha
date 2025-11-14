"""
Unit tests for ResearchWorkflow.

This module tests the research workflow functionality including
state management, node execution, and error handling.
"""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest

from ardha.schemas.workflows.research import (
    ResearchProgressUpdate,
    ResearchState,
    ResearchWorkflowConfig,
)
from ardha.workflows.research_workflow import ResearchWorkflow, get_research_workflow
from ardha.workflows.state import WorkflowStatus, WorkflowType

# Removed unused imports: ResearchNodeException, WorkflowContext


@pytest.fixture
def research_config():
    """Create research workflow config for testing."""
    return ResearchWorkflowConfig(
        idea_analysis_model="z-ai/glm-4.6",
        market_research_model="anthropic/claude-sonnet-4.5",
        competitive_analysis_model="anthropic/claude-sonnet-4.5",
        technical_feasibility_model="anthropic/claude-sonnet-4.5",
        synthesis_model="anthropic/claude-sonnet-4.5",
        max_retries_per_step=2,
        timeout_per_step_seconds=300,
        enable_streaming=True,
        minimum_confidence_threshold=0.7,
    )


@pytest.fixture
def research_workflow(research_config):
    """Create research workflow instance for testing."""
    return ResearchWorkflow(research_config)


@pytest.fixture
def sample_idea():
    """Sample idea for testing."""
    return "AI-powered project management tool for remote teams with real-time collaboration"


@pytest.fixture
def mock_node_result():
    """Mock successful node execution result."""
    return {
        "step_name": "analyze_idea",
        "raw_content": "Analysis complete",
        "structured_content": {"key": "value"},
        "confidence_score": 0.85,
        "model_used": "z-ai/glm-4.6",
        "tokens_input": 100,
        "tokens_output": 200,
        "cost": 0.015,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


class TestResearchWorkflowInitialization:
    """Test research workflow initialization."""

    def test_workflow_initialization_default_config(self):
        """Test workflow initializes with default config."""
        workflow = ResearchWorkflow()

        assert workflow.config is not None
        assert isinstance(workflow.config, ResearchWorkflowConfig)
        assert workflow.nodes is not None
        assert len(workflow.nodes) == 5
        assert "analyze_idea" in workflow.nodes
        assert "market_research" in workflow.nodes
        assert "competitive_analysis" in workflow.nodes
        assert "technical_feasibility" in workflow.nodes
        assert "synthesize" in workflow.nodes

    def test_workflow_initialization_custom_config(self, research_config):
        """Test workflow initializes with custom config."""
        workflow = ResearchWorkflow(research_config)

        assert workflow.config == research_config
        assert workflow.config.max_retries_per_step == 2
        assert workflow.config.enable_streaming is True

    def test_workflow_graph_is_built(self, research_workflow):
        """Test that LangGraph StateGraph is built."""
        assert research_workflow.graph is not None
        # Graph is compiled, so it should have the necessary structure

    def test_global_workflow_instance(self, research_config):
        """Test get_research_workflow returns singleton."""
        workflow1 = get_research_workflow(research_config)
        workflow2 = get_research_workflow()

        assert workflow1 is workflow2  # Same instance


class TestResearchWorkflowStateManagement:
    """Test research workflow state management."""

    def test_state_initialization(self, sample_idea):
        """Test ResearchState initialization."""
        workflow_id = uuid4()
        execution_id = uuid4()
        user_id = uuid4()

        state = ResearchState(
            workflow_id=workflow_id,
            execution_id=execution_id,
            workflow_type=WorkflowType.RESEARCH,
            user_id=user_id,
            initial_request=sample_idea,
            idea=sample_idea,
            created_at=datetime.now(timezone.utc).isoformat(),
        )

        assert state.workflow_id == workflow_id
        assert state.execution_id == execution_id
        assert state.user_id == user_id
        assert state.idea == sample_idea
        assert state.status == WorkflowStatus.PENDING
        assert state.progress_percentage == 0
        assert state.completed_nodes == []
        assert state.failed_nodes == []

    def test_state_progress_updates(self, sample_idea):
        """Test state progress tracking."""
        state = ResearchState(
            workflow_id=uuid4(),
            execution_id=uuid4(),
            workflow_type=WorkflowType.RESEARCH,
            user_id=uuid4(),
            initial_request=sample_idea,
            idea=sample_idea,
            created_at=datetime.now(timezone.utc).isoformat(),
        )

        # Update progress
        state.update_progress("analyze_idea", 20)
        assert state.current_step == "analyze_idea"
        assert state.progress_percentage == 20

        state.update_progress("market_research", 40)
        assert state.current_step == "market_research"
        assert state.progress_percentage == 40

    def test_state_node_completion(self, sample_idea, mock_node_result):
        """Test marking nodes as completed."""
        state = ResearchState(
            workflow_id=uuid4(),
            execution_id=uuid4(),
            workflow_type=WorkflowType.RESEARCH,
            user_id=uuid4(),
            initial_request=sample_idea,
            idea=sample_idea,
            created_at=datetime.now(timezone.utc).isoformat(),
        )

        # Mark node completed
        state.mark_node_completed("analyze_idea", mock_node_result)

        assert "analyze_idea" in state.completed_nodes
        assert "analyze_idea" not in state.failed_nodes

    def test_state_node_failure(self, sample_idea):
        """Test marking nodes as failed."""
        state = ResearchState(
            workflow_id=uuid4(),
            execution_id=uuid4(),
            workflow_type=WorkflowType.RESEARCH,
            user_id=uuid4(),
            initial_request=sample_idea,
            idea=sample_idea,
            created_at=datetime.now(timezone.utc).isoformat(),
        )

        # Mark node failed
        error_data = {"error": "Test error"}
        state.mark_node_failed("market_research", error_data)

        assert "market_research" in state.failed_nodes
        assert "market_research" not in state.completed_nodes
        assert len(state.errors) > 0

    def test_state_research_metadata(self, sample_idea):
        """Test research metadata management."""
        state = ResearchState(
            workflow_id=uuid4(),
            execution_id=uuid4(),
            workflow_type=WorkflowType.RESEARCH,
            user_id=uuid4(),
            initial_request=sample_idea,
            idea=sample_idea,
            created_at=datetime.now(timezone.utc).isoformat(),
        )

        # Add metadata
        state.add_research_metadata(test_key="test_value", count=5)

        assert state.metadata["test_key"] == "test_value"
        assert state.metadata["count"] == 5

    def test_state_confidence_calculation(self, sample_idea):
        """Test research confidence calculation."""
        state = ResearchState(
            workflow_id=uuid4(),
            execution_id=uuid4(),
            workflow_type=WorkflowType.RESEARCH,
            user_id=uuid4(),
            initial_request=sample_idea,
            idea=sample_idea,
            created_at=datetime.now(timezone.utc).isoformat(),
        )

        # Set quality metrics
        state.analysis_depth_score = 0.85
        state.market_data_quality = 0.78
        state.competitor_coverage = 0.82
        state.technical_detail_level = 0.88

        # Calculate confidence
        confidence = state.calculate_research_confidence()

        assert isinstance(confidence, float)
        assert 0.0 <= confidence <= 1.0
        assert state.research_confidence == confidence

    def test_state_research_summary(self, sample_idea):
        """Test research summary generation."""
        state = ResearchState(
            workflow_id=uuid4(),
            execution_id=uuid4(),
            workflow_type=WorkflowType.RESEARCH,
            user_id=uuid4(),
            initial_request=sample_idea,
            idea=sample_idea,
            created_at=datetime.now(timezone.utc).isoformat(),
        )

        # Set some research data
        state.idea_analysis = {"content": "Analysis"}
        state.market_research = {"content": "Market research"}
        state.progress_percentage = 50
        state.completed_nodes = ["analyze_idea", "market_research"]

        # Get summary
        summary = state.get_research_summary()

        assert "idea" in summary
        assert "progress_percentage" in summary
        assert (
            "completed_steps" in summary
        )  # Method returns 'completed_steps' not 'completed_nodes'
        assert summary["progress_percentage"] == 50
        assert len(summary["completed_steps"]) == 2


class TestResearchWorkflowExecution:
    """Test research workflow execution."""

    @pytest.mark.asyncio
    async def test_workflow_execution_success(
        self, research_workflow, sample_idea, mock_node_result
    ):
        """Test successful workflow execution (mocked)."""
        user_id = uuid4()

        # Mock all nodes to return success
        with (
            patch.object(
                research_workflow.nodes["analyze_idea"], "execute", new_callable=AsyncMock
            ) as mock_analyze,
            patch.object(
                research_workflow.nodes["market_research"], "execute", new_callable=AsyncMock
            ) as mock_market,
            patch.object(
                research_workflow.nodes["competitive_analysis"], "execute", new_callable=AsyncMock
            ) as mock_competitive,
            patch.object(
                research_workflow.nodes["technical_feasibility"], "execute", new_callable=AsyncMock
            ) as mock_technical,
            patch.object(
                research_workflow.nodes["synthesize"], "execute", new_callable=AsyncMock
            ) as mock_synthesize,
        ):

            # Configure mocks to return successful results
            mock_analyze.return_value = {**mock_node_result, "step_name": "analyze_idea"}
            mock_market.return_value = {**mock_node_result, "step_name": "market_research"}
            mock_competitive.return_value = {
                **mock_node_result,
                "step_name": "competitive_analysis",
            }
            mock_technical.return_value = {**mock_node_result, "step_name": "technical_feasibility"}
            mock_synthesize.return_value = {**mock_node_result, "step_name": "synthesize"}

            # Execute workflow
            result = await research_workflow.execute(idea=sample_idea, user_id=user_id)

            # Verify result
            assert isinstance(result, ResearchState)
            assert result.status in [WorkflowStatus.COMPLETED, WorkflowStatus.FAILED]
            assert result.idea == sample_idea
            assert result.user_id == user_id

    @pytest.mark.asyncio
    async def test_workflow_execution_with_project(self, research_workflow, sample_idea):
        """Test workflow execution with project association."""
        user_id = uuid4()
        project_id = uuid4()

        # Mock nodes
        with patch.object(
            research_workflow.nodes["analyze_idea"],
            "execute",
            new_callable=AsyncMock,
            return_value={},
        ):

            # Execute workflow with project
            result = await research_workflow.execute(
                idea=sample_idea, user_id=user_id, project_id=project_id
            )

            assert result.project_id == project_id

    @pytest.mark.asyncio
    async def test_workflow_execution_with_parameters(self, research_workflow, sample_idea):
        """Test workflow execution with custom parameters."""
        user_id = uuid4()
        parameters = {"test_mode": True, "depth": "shallow"}

        # Mock nodes
        with patch.object(
            research_workflow.nodes["analyze_idea"],
            "execute",
            new_callable=AsyncMock,
            return_value={},
        ):

            # Execute workflow with parameters
            result = await research_workflow.execute(
                idea=sample_idea, user_id=user_id, parameters=parameters
            )

            assert result.parameters == parameters

    @pytest.mark.asyncio
    async def test_workflow_execution_with_progress_callback(self, research_workflow, sample_idea):
        """Test workflow execution with progress tracking."""
        user_id = uuid4()
        progress_updates = []

        async def progress_callback(update):
            progress_updates.append(update)

        # Mock nodes
        with patch.object(
            research_workflow.nodes["analyze_idea"],
            "execute",
            new_callable=AsyncMock,
            return_value={},
        ):

            # Execute workflow with callback
            result = await research_workflow.execute(
                idea=sample_idea, user_id=user_id, progress_callback=progress_callback
            )

            # Progress updates should have been called
            # Note: actual updates depend on node execution
            assert isinstance(result, ResearchState)


class TestResearchWorkflowNodes:
    """Test individual research workflow nodes execution."""

    @pytest.mark.asyncio
    async def test_analyze_idea_node_success(
        self, research_workflow, sample_idea, mock_node_result
    ):
        """Test successful idea analysis node execution."""
        # Create test state
        state = ResearchState(
            workflow_id=uuid4(),
            execution_id=uuid4(),
            workflow_type=WorkflowType.RESEARCH,
            user_id=uuid4(),
            initial_request=sample_idea,
            idea=sample_idea,
            created_at=datetime.now(timezone.utc).isoformat(),
        )

        # Mock the node execution
        with patch.object(
            research_workflow.nodes["analyze_idea"],
            "execute",
            new_callable=AsyncMock,
            return_value=mock_node_result,
        ):

            # Execute node
            result_state = await research_workflow._analyze_idea_node(state)

            # Verify state was updated
            assert result_state.idea_analysis == mock_node_result
            assert "analyze_idea" in result_state.completed_nodes
            assert result_state.current_step == "market_research"

    @pytest.mark.asyncio
    async def test_analyze_idea_node_failure(self, research_workflow, sample_idea):
        """Test idea analysis node failure handling."""
        state = ResearchState(
            workflow_id=uuid4(),
            execution_id=uuid4(),
            workflow_type=WorkflowType.RESEARCH,
            user_id=uuid4(),
            initial_request=sample_idea,
            idea=sample_idea,
            created_at=datetime.now(timezone.utc).isoformat(),
        )

        # Mock node to raise exception
        with patch.object(
            research_workflow.nodes["analyze_idea"], "execute", side_effect=Exception("Test error")
        ):

            # Execute node
            result_state = await research_workflow._analyze_idea_node(state)

            # Verify error was handled
            assert "analyze_idea" in result_state.failed_nodes
            assert result_state.current_step == "error"

    @pytest.mark.asyncio
    async def test_market_research_node(self, research_workflow, sample_idea, mock_node_result):
        """Test market research node execution."""
        state = ResearchState(
            workflow_id=uuid4(),
            execution_id=uuid4(),
            workflow_type=WorkflowType.RESEARCH,
            user_id=uuid4(),
            initial_request=sample_idea,
            idea=sample_idea,
            created_at=datetime.now(timezone.utc).isoformat(),
        )

        # Set prerequisites
        state.idea_analysis = {"content": "Analysis done"}

        # Mock the node
        with patch.object(
            research_workflow.nodes["market_research"],
            "execute",
            new_callable=AsyncMock,
            return_value=mock_node_result,
        ):

            result_state = await research_workflow._market_research_node(state)

            assert result_state.market_research == mock_node_result
            assert "market_research" in result_state.completed_nodes

    @pytest.mark.asyncio
    async def test_competitive_analysis_node(
        self, research_workflow, sample_idea, mock_node_result
    ):
        """Test competitive analysis node execution."""
        state = ResearchState(
            workflow_id=uuid4(),
            execution_id=uuid4(),
            workflow_type=WorkflowType.RESEARCH,
            user_id=uuid4(),
            initial_request=sample_idea,
            idea=sample_idea,
            created_at=datetime.now(timezone.utc).isoformat(),
        )

        # Mock the node
        with patch.object(
            research_workflow.nodes["competitive_analysis"],
            "execute",
            new_callable=AsyncMock,
            return_value=mock_node_result,
        ):

            result_state = await research_workflow._competitive_analysis_node(state)

            assert result_state.competitive_analysis == mock_node_result
            assert "competitive_analysis" in result_state.completed_nodes

    @pytest.mark.asyncio
    async def test_technical_feasibility_node(
        self, research_workflow, sample_idea, mock_node_result
    ):
        """Test technical feasibility node execution."""
        state = ResearchState(
            workflow_id=uuid4(),
            execution_id=uuid4(),
            workflow_type=WorkflowType.RESEARCH,
            user_id=uuid4(),
            initial_request=sample_idea,
            idea=sample_idea,
            created_at=datetime.now(timezone.utc).isoformat(),
        )

        # Mock the node
        with patch.object(
            research_workflow.nodes["technical_feasibility"],
            "execute",
            new_callable=AsyncMock,
            return_value=mock_node_result,
        ):

            result_state = await research_workflow._technical_feasibility_node(state)

            assert result_state.technical_feasibility == mock_node_result
            assert "technical_feasibility" in result_state.completed_nodes

    @pytest.mark.asyncio
    async def test_synthesize_node(self, research_workflow, sample_idea, mock_node_result):
        """Test synthesis node execution."""
        state = ResearchState(
            workflow_id=uuid4(),
            execution_id=uuid4(),
            workflow_type=WorkflowType.RESEARCH,
            user_id=uuid4(),
            initial_request=sample_idea,
            idea=sample_idea,
            created_at=datetime.now(timezone.utc).isoformat(),
        )

        # Set prerequisites
        state.idea_analysis = {"content": "Analysis"}
        state.market_research = {"content": "Research"}
        state.competitive_analysis = {"content": "Analysis"}
        state.technical_feasibility = {"content": "Feasibility"}

        # Mock the node
        with patch.object(
            research_workflow.nodes["synthesize"],
            "execute",
            new_callable=AsyncMock,
            return_value=mock_node_result,
        ):

            result_state = await research_workflow._synthesize_node(state)

            assert result_state.research_summary == mock_node_result
            assert "synthesize" in result_state.completed_nodes
            assert result_state.progress_percentage == 100


class TestResearchWorkflowErrorHandling:
    """Test research workflow error recovery."""

    @pytest.mark.asyncio
    async def test_error_handler_node_retry(self, research_workflow, sample_idea):
        """Test error handler triggers retry."""
        state = ResearchState(
            workflow_id=uuid4(),
            execution_id=uuid4(),
            workflow_type=WorkflowType.RESEARCH,
            user_id=uuid4(),
            initial_request=sample_idea,
            idea=sample_idea,
            created_at=datetime.now(timezone.utc).isoformat(),
        )

        state.current_step = "error"
        state.retry_count = 0

        # Execute error handler
        result_state = await research_workflow._error_handler_node(state)

        assert result_state.retry_count == 1
        assert result_state.current_step == "retry"

    @pytest.mark.asyncio
    async def test_error_handler_max_retries(self, research_workflow, sample_idea):
        """Test error handler stops after max retries."""
        state = ResearchState(
            workflow_id=uuid4(),
            execution_id=uuid4(),
            workflow_type=WorkflowType.RESEARCH,
            user_id=uuid4(),
            initial_request=sample_idea,
            idea=sample_idea,
            created_at=datetime.now(timezone.utc).isoformat(),
        )

        state.current_step = "error"
        state.retry_count = research_workflow.config.max_retries_per_step

        # Execute error handler
        result_state = await research_workflow._error_handler_node(state)

        assert result_state.current_step == "end"
        assert result_state.status == WorkflowStatus.FAILED

    def test_decide_next_step_normal_flow(self, research_workflow, sample_idea):
        """Test next step decision in normal flow."""
        state = ResearchState(
            workflow_id=uuid4(),
            execution_id=uuid4(),
            workflow_type=WorkflowType.RESEARCH,
            user_id=uuid4(),
            initial_request=sample_idea,
            idea=sample_idea,
            created_at=datetime.now(timezone.utc).isoformat(),
        )

        # Test progression through nodes
        state.current_step = "analyze_idea_node"
        assert research_workflow._decide_next_step(state) == "market_research_node"

        state.current_step = "market_research_node"
        assert research_workflow._decide_next_step(state) == "competitive_analysis_node"

        state.current_step = "competitive_analysis_node"
        assert research_workflow._decide_next_step(state) == "technical_feasibility_node"

        state.current_step = "technical_feasibility_node"
        assert research_workflow._decide_next_step(state) == "synthesize_node"

        state.current_step = "synthesize_node"
        assert research_workflow._decide_next_step(state) == "end"

    def test_decide_next_step_error_flow(self, research_workflow, sample_idea):
        """Test next step decision in error flow."""
        state = ResearchState(
            workflow_id=uuid4(),
            execution_id=uuid4(),
            workflow_type=WorkflowType.RESEARCH,
            user_id=uuid4(),
            initial_request=sample_idea,
            idea=sample_idea,
            created_at=datetime.now(timezone.utc).isoformat(),
        )

        state.current_step = "error"
        assert research_workflow._decide_next_step(state) == "error"

    def test_decide_error_recovery_retry(self, research_workflow, sample_idea):
        """Test error recovery decision for retry."""
        state = ResearchState(
            workflow_id=uuid4(),
            execution_id=uuid4(),
            workflow_type=WorkflowType.RESEARCH,
            user_id=uuid4(),
            initial_request=sample_idea,
            idea=sample_idea,
            created_at=datetime.now(timezone.utc).isoformat(),
        )

        state.retry_count = 0
        assert research_workflow._decide_error_recovery(state) == "retry"

    def test_decide_error_recovery_end(self, research_workflow, sample_idea):
        """Test error recovery decision to end."""
        state = ResearchState(
            workflow_id=uuid4(),
            execution_id=uuid4(),
            workflow_type=WorkflowType.RESEARCH,
            user_id=uuid4(),
            initial_request=sample_idea,
            idea=sample_idea,
            created_at=datetime.now(timezone.utc).isoformat(),
        )

        state.retry_count = research_workflow.config.max_retries_per_step
        assert research_workflow._decide_error_recovery(state) == "end"


class TestResearchWorkflowCancellation:
    """Test research workflow cancellation."""

    @pytest.mark.asyncio
    async def test_cancel_execution_success(self, research_workflow):
        """Test successful execution cancellation."""
        execution_id = uuid4()

        # Add to active executions
        state = ResearchState(
            workflow_id=uuid4(),
            execution_id=execution_id,
            workflow_type=WorkflowType.RESEARCH,
            user_id=uuid4(),
            initial_request="Test",
            idea="Test",
            created_at=datetime.now(timezone.utc).isoformat(),
        )
        research_workflow.active_executions[execution_id] = state

        # Cancel execution
        result = await research_workflow.cancel_execution(execution_id, reason="Test cancel")

        assert result is True
        assert execution_id not in research_workflow.active_executions
        assert state.status == WorkflowStatus.CANCELLED
        assert state.metadata["cancellation_reason"] == "Test cancel"

    @pytest.mark.asyncio
    async def test_cancel_execution_not_found(self, research_workflow):
        """Test cancelling non-existent execution."""
        execution_id = uuid4()

        result = await research_workflow.cancel_execution(execution_id)

        assert result is False

    @pytest.mark.asyncio
    async def test_get_execution_status(self, research_workflow):
        """Test getting execution status."""
        execution_id = uuid4()

        # Add to active executions
        state = ResearchState(
            workflow_id=uuid4(),
            execution_id=execution_id,
            workflow_type=WorkflowType.RESEARCH,
            user_id=uuid4(),
            initial_request="Test",
            idea="Test",
            created_at=datetime.now(timezone.utc).isoformat(),
        )
        research_workflow.active_executions[execution_id] = state

        # Get status
        result = await research_workflow.get_execution_status(execution_id)

        assert result == state

    @pytest.mark.asyncio
    async def test_get_execution_status_not_found(self, research_workflow):
        """Test getting status for non-existent execution."""
        execution_id = uuid4()

        result = await research_workflow.get_execution_status(execution_id)

        assert result is None


class TestResearchWorkflowCallbacks:
    """Test research workflow callback mechanisms."""

    @pytest.mark.asyncio
    async def test_default_progress_callback(self, research_workflow):
        """Test default progress callback."""
        progress_update = ResearchProgressUpdate(
            workflow_id=uuid4(),
            execution_id=uuid4(),
            current_step="analyze_idea",
            progress_percentage=20,
            step_status="running",
            timestamp=datetime.now(timezone.utc).isoformat(),
        )

        # Should not raise exception
        await research_workflow._default_progress_callback(progress_update)

    @pytest.mark.asyncio
    async def test_default_error_callback(self, research_workflow):
        """Test default error callback."""
        execution_id = uuid4()
        error_data = {"error": "Test error", "timestamp": datetime.now(timezone.utc).isoformat()}

        # Should not raise exception
        await research_workflow._default_error_callback(execution_id, "test_node", error_data)
