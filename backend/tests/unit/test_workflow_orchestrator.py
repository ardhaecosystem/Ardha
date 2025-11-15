"""
Unit tests for workflow orchestrator.

Tests WorkflowOrchestrator class and its methods
to ensure proper workflow execution and management.
"""

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from ardha.workflows.orchestrator import WorkflowOrchestrator, get_workflow_orchestrator
from ardha.workflows.state import WorkflowState, WorkflowStatus, WorkflowType


class TestWorkflowOrchestrator:
    """Test cases for WorkflowOrchestrator class."""

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
            initial_request="Test research request",
        )

    def test_orchestrator_initialization(self, orchestrator):
        """Test orchestrator initialization."""
        assert orchestrator.active_executions == {}
        assert orchestrator.logger is not None
        assert orchestrator.openrouter_client is not None
        assert orchestrator.qdrant_service is not None

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

        with patch.object(orchestrator, "_execute_research_workflow") as mock_research:
            mock_research.return_value = {"research_results": "mock_data"}

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

            mock_research.assert_called_once_with(
                initial_request=initial_request,
                parameters=parameters,
                context=context,
                state=state,
            )

    @pytest.mark.asyncio
    async def test_execute_workflow_architect(self, orchestrator):
        """Test executing an architect workflow."""
        workflow_type = WorkflowType.ARCHITECT
        initial_request = "Design system architecture"
        user_id = uuid4()

        with patch.object(orchestrator, "_execute_architect_workflow") as mock_architect:
            mock_architect.return_value = {"architecture": "mock_design"}

            state = await orchestrator.execute_workflow(
                workflow_type=workflow_type,
                initial_request=initial_request,
                user_id=user_id,
            )

            assert state.workflow_type == workflow_type
            assert state.initial_request == initial_request

            mock_architect.assert_called_once()

    @pytest.mark.asyncio
    async def test_execute_workflow_implement(self, orchestrator):
        """Test executing an implement workflow."""
        workflow_type = WorkflowType.IMPLEMENT
        initial_request = "Implement feature X"
        user_id = uuid4()

        with patch.object(orchestrator, "_execute_implement_workflow") as mock_implement:
            mock_implement.return_value = {"code": "mock_implementation"}

            state = await orchestrator.execute_workflow(
                workflow_type=workflow_type,
                initial_request=initial_request,
                user_id=user_id,
            )

            assert state.workflow_type == workflow_type
            mock_implement.assert_called_once()

    @pytest.mark.asyncio
    async def test_execute_workflow_debug(self, orchestrator):
        """Test executing a debug workflow."""
        workflow_type = WorkflowType.DEBUG
        initial_request = "Debug issue X"
        user_id = uuid4()

        with patch.object(orchestrator, "_execute_debug_workflow") as mock_debug:
            mock_debug.return_value = {"solution": "mock_fix"}

            state = await orchestrator.execute_workflow(
                workflow_type=workflow_type,
                initial_request=initial_request,
                user_id=user_id,
            )

            assert state.workflow_type == workflow_type
            mock_debug.assert_called_once()

    @pytest.mark.asyncio
    async def test_execute_workflow_invalid_type(self, orchestrator):
        """Test executing workflow with invalid type."""
        with patch.object(orchestrator, "_execute_research_workflow") as mock_research:
            mock_research.return_value = {"results": "data"}

            state = await orchestrator.execute_workflow(
                workflow_type="invalid_type",
                initial_request="Test request",
                user_id=uuid4(),
            )

            # Should still work but use research as fallback
            assert state is not None
            mock_research.assert_called_once()

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

        assert success is False
        assert sample_state.status == WorkflowStatus.COMPLETED

    @pytest.mark.asyncio
    async def test_list_active_executions(self, orchestrator):
        """Test listing active executions."""
        user_id = uuid4()

        # Create sample executions
        state1 = WorkflowState(
            workflow_id=uuid4(),
            execution_id=uuid4(),
            workflow_type=WorkflowType.RESEARCH,
            user_id=user_id,
            initial_request="Request 1",
        )

        state2 = WorkflowState(
            workflow_id=uuid4(),
            execution_id=uuid4(),
            workflow_type=WorkflowType.IMPLEMENT,
            user_id=uuid4(),  # Different user
            initial_request="Request 2",
        )

        state3 = WorkflowState(
            workflow_id=uuid4(),
            execution_id=uuid4(),
            workflow_type=WorkflowType.DEBUG,
            user_id=user_id,
            initial_request="Request 3",
        )

        # Add to active executions
        orchestrator.active_executions[state1.execution_id] = state1
        orchestrator.active_executions[state2.execution_id] = state2
        orchestrator.active_executions[state3.execution_id] = state3

        # List executions for user_id
        executions = await orchestrator.list_active_executions(user_id)

        assert len(executions) == 2
        assert state1 in executions
        assert state3 in executions
        assert state2 not in executions  # Different user

    @pytest.mark.asyncio
    async def test_execute_research_workflow(self, orchestrator, sample_state):
        """Test research workflow execution logic."""
        initial_request = "Research AI workflow systems"
        parameters = {"max_results": 5}
        context = {"domain": "software_engineering"}

        with patch.object(orchestrator.openrouter_client, "chat_completion") as mock_ai:
            mock_ai.return_value = {
                "choices": [{"message": {"content": "Research results on AI workflow systems..."}}]
            }

            result = await orchestrator._execute_research_workflow(
                initial_request=initial_request,
                parameters=parameters,
                context=context,
                state=sample_state,
            )

            assert isinstance(result, dict)
            assert "research_results" in result

            # Verify AI was called
            mock_ai.assert_called_once()

            # Verify state was updated
            assert sample_state.status == WorkflowStatus.COMPLETED
            assert "research_node" in sample_state.completed_nodes

    @pytest.mark.asyncio
    async def test_execute_research_workflow_with_error(self, orchestrator, sample_state):
        """Test research workflow execution with error."""
        initial_request = "Research AI workflow systems"

        with patch.object(orchestrator.openrouter_client, "chat_completion") as mock_ai:
            mock_ai.side_effect = Exception("AI service error")

            result = await orchestrator._execute_research_workflow(
                initial_request=initial_request,
                parameters={},
                context={},
                state=sample_state,
            )

            assert result is None

            # Verify error was recorded
            assert sample_state.status == WorkflowStatus.FAILED
            assert len(sample_state.errors) > 0
            assert "research_node" in sample_state.failed_nodes

    @pytest.mark.asyncio
    async def test_execute_architect_workflow(self, orchestrator, sample_state):
        """Test architect workflow execution logic."""
        initial_request = "Design system architecture"
        context = {"requirements": ["scalability", "security"]}

        with patch.object(orchestrator.openrouter_client, "chat_completion") as mock_ai:
            mock_ai.return_value = {
                "choices": [
                    {"message": {"content": "Architecture design with scalability and security..."}}
                ]
            }

            result = await orchestrator._execute_architect_workflow(
                initial_request=initial_request,
                parameters={},
                context=context,
                state=sample_state,
            )

            assert isinstance(result, dict)
            assert "architecture" in result

            # Verify state was updated
            assert sample_state.status == WorkflowStatus.COMPLETED
            assert "architect_node" in sample_state.completed_nodes

    @pytest.mark.asyncio
    async def test_execute_implement_workflow(self, orchestrator, sample_state):
        """Test implement workflow execution logic."""
        initial_request = "Implement user authentication"
        context = {"tech_stack": "python_fastapi"}

        with patch.object(orchestrator.openrouter_client, "chat_completion") as mock_ai:
            mock_ai.return_value = {
                "choices": [
                    {"message": {"content": "Python FastAPI authentication implementation..."}}
                ]
            }

            result = await orchestrator._execute_implement_workflow(
                initial_request=initial_request,
                parameters={},
                context=context,
                state=sample_state,
            )

            assert isinstance(result, dict)
            assert "implementation" in result

            # Verify state was updated
            assert sample_state.status == WorkflowStatus.COMPLETED
            assert "implement_node" in sample_state.completed_nodes

    @pytest.mark.asyncio
    async def test_execute_debug_workflow(self, orchestrator, sample_state):
        """Test debug workflow execution logic."""
        initial_request = "Debug authentication issue"
        context = {"error_logs": ["401 unauthorized", "token validation failed"]}

        with patch.object(orchestrator.openrouter_client, "chat_completion") as mock_ai:
            mock_ai.return_value = {
                "choices": [
                    {"message": {"content": "Debug analysis reveals token validation issue..."}}
                ]
            }

            result = await orchestrator._execute_debug_workflow(
                initial_request=initial_request,
                parameters={},
                context=context,
                state=sample_state,
            )

            assert isinstance(result, dict)
            assert "debug_analysis" in result
            assert "solution" in result

            # Verify state was updated
            assert sample_state.status == WorkflowStatus.COMPLETED
            assert "debug_node" in sample_state.completed_nodes

    def test_build_workflow_prompt(self, orchestrator):
        """Test building workflow prompts."""
        # Test research prompt
        prompt = orchestrator._build_workflow_prompt(
            "research",
            "Analyze AI workflow systems",
            {"domain": "software_engineering"},
            {"max_results": 5},
        )

        assert "research" in prompt.lower()
        assert "analyze ai workflow systems" in prompt.lower()
        assert "software engineering" in prompt.lower()
        assert "max_results: 5" in prompt

        # Test architect prompt
        prompt = orchestrator._build_workflow_prompt(
            "architect", "Design system architecture", {"requirements": ["scalability"]}, {}
        )

        assert "architect" in prompt.lower()
        assert "design system architecture" in prompt.lower()
        assert "scalability" in prompt.lower()

    def test_parse_ai_response(self, orchestrator):
        """Test parsing AI responses."""
        # Test successful response
        ai_response = {"choices": [{"message": {"content": '{"results": ["data1", "data2"]}'}}]}

        parsed = orchestrator._parse_ai_response(ai_response, "research")

        assert parsed is not None
        assert "results" in parsed
        assert parsed["results"] == ["data1", "data2"]

        # Test malformed response
        ai_response = {"invalid": "structure"}

        parsed = orchestrator._parse_ai_response(ai_response, "research")

        assert parsed is None

        # Test empty response
        parsed = orchestrator._parse_ai_response(None, "research")

        assert parsed is None

    def test_handle_workflow_error(self, orchestrator, sample_state):
        """Test error handling in workflows."""
        error = Exception("Test error")
        node_name = "test_node"

        orchestrator._handle_workflow_error(sample_state, node_name, error)

        assert sample_state.status == WorkflowStatus.FAILED
        assert node_name in sample_state.failed_nodes
        assert len(sample_state.errors) > 0
        assert sample_state.errors[-1]["node"] == node_name
        assert "Test error" in str(sample_state.errors[-1]["error"])

    def test_handle_workflow_success(self, orchestrator, sample_state):
        """Test success handling in workflows."""
        node_name = "test_node"
        result = {"output": "success_data"}

        orchestrator._handle_workflow_success(sample_state, node_name, result)

        assert sample_state.status == WorkflowStatus.COMPLETED
        assert node_name in sample_state.completed_nodes
        assert sample_state.results[node_name] == result

    @pytest.mark.asyncio
    async def test_workflow_with_retry(self, orchestrator, sample_state):
        """Test workflow execution with retry logic."""
        initial_request = "Test with retry"

        with patch.object(orchestrator, "_execute_research_workflow") as mock_research:
            # Fail first time, succeed second time
            mock_research.side_effect = [None, {"results": "success"}]

            # Set up state for retry
            sample_state.retry_count = 0
            sample_state.max_retries = 2

            # Execute workflow (this would be called by execute_workflow)
            result = await orchestrator._execute_research_workflow(
                initial_request=initial_request,
                parameters={},
                context={},
                state=sample_state,
            )

            # First call should fail
            assert result is None
            assert sample_state.retry_count == 1
            assert sample_state.status == WorkflowStatus.FAILED

            # Second call should succeed
            result = await orchestrator._execute_research_workflow(
                initial_request=initial_request,
                parameters={},
                context={},
                state=sample_state,
            )

            assert result == {"results": "success"}
            assert sample_state.status == WorkflowStatus.COMPLETED
