"""
Simplified unit tests for workflow orchestrator.

Tests WorkflowOrchestrator class with its actual implementation
to ensure proper workflow execution and management.
"""

from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest

from ardha.workflows.orchestrator import WorkflowOrchestrator, get_workflow_orchestrator
from ardha.workflows.state import WorkflowState, WorkflowStatus, WorkflowType


class TestWorkflowOrchestratorSimple:
    """Test cases for WorkflowOrchestrator class (simplified)."""

    @pytest.fixture
    def orchestrator(self):
        """Create workflow orchestrator for testing."""
        return WorkflowOrchestrator()

    @pytest.fixture
    def sample_state(self):
        """Create sample workflow state for testing."""
        return WorkflowState(
            workflow_id=uuid4(),
            execution_id=uuid4(),
            workflow_type=WorkflowType.RESEARCH,
            user_id=uuid4(),
            initial_request="Test request",
        )

    def test_orchestrator_initialization(self, orchestrator):
        """Test orchestrator initialization."""
        assert orchestrator.active_executions == {}
        assert orchestrator.logger is not None
        assert orchestrator.nodes is not None
        assert "research" in orchestrator.nodes
        assert "architect" in orchestrator.nodes
        assert "implement" in orchestrator.nodes
        assert "debug" in orchestrator.nodes
        assert "memory_ingestion" in orchestrator.nodes

    def test_get_workflow_orchestrator_singleton(self):
        """Test that get_workflow_orchestrator returns singleton."""
        orchestrator1 = get_workflow_orchestrator()
        orchestrator2 = get_workflow_orchestrator()

        assert orchestrator1 is orchestrator2

    @pytest.mark.asyncio
    async def test_execute_workflow_research(self, orchestrator):
        """Test executing a research workflow."""
        workflow_type = WorkflowType.RESEARCH
        initial_request = "Research AI workflow systems"
        user_id = uuid4()
        project_id = uuid4()
        parameters = {"max_results": 5}
        context = {"domain": "software_engineering"}

        with patch("ardha.workflows.nodes.BaseNode.execute") as mock_execute:
            mock_execute.return_value = {"research_results": "mock_data"}

            state = await orchestrator.execute_workflow(
                workflow_type=workflow_type,
                initial_request=initial_request,
                user_id=user_id,
                project_id=project_id,
                parameters=parameters,
                context=context,
            )

            assert isinstance(state, WorkflowState)
            assert state.workflow_type == workflow_type
            assert state.user_id == user_id
            assert state.project_id == project_id
            assert state.initial_request == initial_request
            assert state.context == context
            assert state.parameters == parameters
            assert state.status in [WorkflowStatus.COMPLETED, WorkflowStatus.FAILED]

    @pytest.mark.asyncio
    async def test_execute_workflow_architect(self, orchestrator):
        """Test executing an architect workflow."""
        workflow_type = WorkflowType.ARCHITECT
        initial_request = "Design system architecture"
        user_id = uuid4()

        with patch("ardha.workflows.nodes.BaseNode.execute") as mock_execute:
            mock_execute.return_value = {"architecture": "mock_design"}

            state = await orchestrator.execute_workflow(
                workflow_type=workflow_type,
                initial_request=initial_request,
                user_id=user_id,
            )

            assert state.workflow_type == workflow_type
            assert state.initial_request == initial_request

    @pytest.mark.asyncio
    async def test_execute_workflow_implement(self, orchestrator):
        """Test executing an implement workflow."""
        workflow_type = WorkflowType.IMPLEMENT
        initial_request = "Implement feature X"
        user_id = uuid4()

        with patch("ardha.workflows.nodes.BaseNode.execute") as mock_execute:
            mock_execute.return_value = {"code": "mock_implementation"}

            state = await orchestrator.execute_workflow(
                workflow_type=workflow_type,
                initial_request=initial_request,
                user_id=user_id,
            )

            assert state.workflow_type == workflow_type
            assert state.initial_request == initial_request

    @pytest.mark.asyncio
    async def test_execute_workflow_debug(self, orchestrator):
        """Test executing a debug workflow."""
        workflow_type = WorkflowType.DEBUG
        initial_request = "Debug issue X"
        user_id = uuid4()

        with patch("ardha.workflows.nodes.BaseNode.execute") as mock_execute:
            mock_execute.return_value = {"solution": "mock_fix"}

            state = await orchestrator.execute_workflow(
                workflow_type=workflow_type,
                initial_request=initial_request,
                user_id=user_id,
            )

            assert state.workflow_type == workflow_type
            assert state.initial_request == initial_request

    @pytest.mark.asyncio
    async def test_get_execution_status(self, orchestrator, sample_state):
        """Test getting execution status."""
        execution_id = sample_state.execution_id

        # Add to active executions
        orchestrator.active_executions[execution_id] = sample_state

        # Get status
        status = await orchestrator.get_execution_status(execution_id)

        assert status is sample_state
        assert status.execution_id == execution_id

    @pytest.mark.asyncio
    async def test_get_execution_status_not_found(self, orchestrator):
        """Test getting status for non-existent execution."""
        execution_id = uuid4()

        status = await orchestrator.get_execution_status(execution_id)

        assert status is None

    @pytest.mark.asyncio
    async def test_cancel_execution(self, orchestrator, sample_state):
        """Test canceling an execution."""
        execution_id = sample_state.execution_id

        # Add to active executions
        orchestrator.active_executions[execution_id] = sample_state

        # Cancel execution
        success = await orchestrator.cancel_execution(execution_id, "User requested cancellation")

        assert success is True
        assert sample_state.status == WorkflowStatus.CANCELLED
        assert execution_id not in orchestrator.active_executions
        assert sample_state.metadata["cancellation_reason"] == "User requested cancellation"

    @pytest.mark.asyncio
    async def test_cancel_execution_not_found(self, orchestrator):
        """Test canceling non-existent execution."""
        execution_id = uuid4()

        success = await orchestrator.cancel_execution(execution_id, "Test cancellation")

        assert success is False

    @pytest.mark.asyncio
    async def test_cancel_execution_already_completed(self, orchestrator, sample_state):
        """Test canceling already completed execution."""
        execution_id = sample_state.execution_id
        sample_state.status = WorkflowStatus.COMPLETED

        # Add to active executions
        orchestrator.active_executions[execution_id] = sample_state

        # Try to cancel
        success = await orchestrator.cancel_execution(execution_id, "Test cancellation")

        assert success is True  # Still cancels but status was already COMPLETED
        assert sample_state.status == WorkflowStatus.CANCELLED

    def test_get_default_node_sequence(self, orchestrator):
        """Test getting default node sequences."""
        # Test research workflow
        sequence = orchestrator._get_default_node_sequence(WorkflowType.RESEARCH)
        assert "research" in sequence
        assert "memory_ingestion" in sequence

        # Test architect workflow
        sequence = orchestrator._get_default_node_sequence(WorkflowType.ARCHITECT)
        assert "research" in sequence
        assert "architect" in sequence
        assert "memory_ingestion" in sequence

        # Test implement workflow
        sequence = orchestrator._get_default_node_sequence(WorkflowType.IMPLEMENT)
        assert "research" in sequence
        assert "architect" in sequence
        assert "implement" in sequence
        assert "memory_ingestion" in sequence

        # Test debug workflow
        sequence = orchestrator._get_default_node_sequence(WorkflowType.DEBUG)
        assert "debug" in sequence
        assert "memory_ingestion" in sequence

        # Test full development workflow
        sequence = orchestrator._get_default_node_sequence(WorkflowType.FULL_DEVELOPMENT)
        assert "research" in sequence
        assert "architect" in sequence
        assert "implement" in sequence
        assert "debug" in sequence
        assert "memory_ingestion" in sequence

        # Test custom workflow
        sequence = orchestrator._get_default_node_sequence(WorkflowType.CUSTOM)
        assert sequence == []

    @pytest.mark.asyncio
    async def test_execute_workflow_with_error(self, orchestrator):
        """Test workflow execution with node error - should handle gracefully."""
        workflow_type = WorkflowType.RESEARCH
        initial_request = "Test with error"
        user_id = uuid4()

        # Mock BaseNode.execute to raise an exception
        with patch("ardha.workflows.nodes.ResearchNode.execute") as mock_execute:
            mock_execute.side_effect = Exception("Node execution failed")

            # Should NOT raise exception - should handle gracefully
            state = await orchestrator.execute_workflow(
                workflow_type=workflow_type,
                initial_request=initial_request,
                user_id=user_id,
            )

            # Verify graceful error handling
            assert state is not None
            assert state.status == WorkflowStatus.FAILED
            assert len(state.errors) > 0
            assert len(state.failed_nodes) > 0
            assert "research" in state.failed_nodes

    def test_on_progress_update(self, orchestrator):
        """Test progress update callback."""
        execution_id = uuid4()
        node_name = "test_node"
        progress = 75.0

        # Should not raise any exceptions
        orchestrator._on_progress_update(execution_id, node_name, progress)

    def test_on_error(self, orchestrator):
        """Test error callback."""
        execution_id = uuid4()
        node_name = "test_node"
        error = {"error": "Test error", "details": "Something went wrong"}

        # Should not raise any exceptions
        orchestrator._on_error(execution_id, node_name, error)

    @pytest.mark.asyncio
    async def test_workflow_execution_with_context(self, orchestrator):
        """Test workflow execution creates proper context."""
        workflow_type = WorkflowType.RESEARCH
        initial_request = "Test context"
        user_id = uuid4()

        with patch("ardha.workflows.nodes.BaseNode.execute") as mock_execute:
            mock_execute.return_value = {"results": "success"}

            with (
                patch("ardha.workflows.orchestrator.OpenRouterClient") as mock_client,
                patch("ardha.workflows.orchestrator.get_qdrant_service") as mock_qdrant,
            ):

                await orchestrator.execute_workflow(
                    workflow_type=workflow_type,
                    initial_request=initial_request,
                    user_id=user_id,
                )

                # Verify context was created with proper components
                mock_client.assert_called_once()
                mock_qdrant.assert_called_once()

    @pytest.mark.asyncio
    async def test_workflow_execution_state_transitions(self, orchestrator):
        """Test workflow execution state transitions."""
        workflow_type = WorkflowType.RESEARCH
        initial_request = "Test state transitions"
        user_id = uuid4()

        with patch("ardha.workflows.nodes.BaseNode.execute") as mock_execute:
            mock_execute.return_value = {"results": "success"}

            state = await orchestrator.execute_workflow(
                workflow_type=workflow_type,
                initial_request=initial_request,
                user_id=user_id,
            )

            # Verify state transitions
            assert state.status in [WorkflowStatus.COMPLETED, WorkflowStatus.FAILED]
            assert state.started_at is not None
            assert state.completed_at is not None
            assert state.last_activity is not None
            assert len(state.completed_nodes) > 0

    @pytest.mark.asyncio
    async def test_workflow_execution_with_unknown_node(self, orchestrator):
        """Test workflow execution with unknown node in sequence."""
        workflow_type = WorkflowType.CUSTOM  # Empty sequence by default
        initial_request = "Test unknown node"
        user_id = uuid4()

        # Manually add a node that doesn't exist
        with patch.object(orchestrator, "_get_default_node_sequence") as mock_sequence:
            mock_sequence.return_value = ["unknown_node"]

            with patch("ardha.workflows.nodes.BaseNode.execute") as mock_execute:
                mock_execute.return_value = {"results": "success"}

                state = await orchestrator.execute_workflow(
                    workflow_type=workflow_type,
                    initial_request=initial_request,
                    user_id=user_id,
                )

                # Should handle unknown node gracefully
                assert state is not None
