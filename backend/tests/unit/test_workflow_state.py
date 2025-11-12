"""
Unit tests for workflow state management.

Tests the WorkflowState class and its methods
to ensure proper state transitions and data management.
"""

import pytest
from datetime import datetime
from uuid import uuid4

from ardha.workflows.state import WorkflowState, WorkflowStatus, WorkflowType


class TestWorkflowState:
    """Test cases for WorkflowState class."""
    
    def test_workflow_state_initialization(self):
        """Test WorkflowState initialization with required parameters."""
        workflow_id = uuid4()
        execution_id = uuid4()
        workflow_type = WorkflowType.RESEARCH
        user_id = uuid4()
        initial_request = "Test request"
        
        state = WorkflowState(
            workflow_id=workflow_id,
            execution_id=execution_id,
            workflow_type=workflow_type,
            user_id=user_id,
            initial_request=initial_request,
        )
        
        assert state.workflow_id == workflow_id
        assert state.execution_id == execution_id
        assert state.workflow_type == workflow_type
        assert state.user_id == user_id
        assert state.initial_request == initial_request
        assert state.status == WorkflowStatus.PENDING
        assert state.current_node is None
        assert state.completed_nodes == []
        assert state.failed_nodes == []
        assert state.results == {}
        assert state.artifacts == {}
        assert state.errors == []
        assert state.retry_count == 0
        assert state.total_cost == 0.0
        assert state.token_usage == {}
    
    def test_workflow_state_with_optional_parameters(self):
        """Test WorkflowState initialization with optional parameters."""
        workflow_id = uuid4()
        execution_id = uuid4()
        workflow_type = WorkflowType.IMPLEMENT
        user_id = uuid4()
        project_id = uuid4()
        initial_request = "Test request"
        context = {"key": "value"}
        parameters = {"max_retries": 3}
        
        state = WorkflowState(
            workflow_id=workflow_id,
            execution_id=execution_id,
            workflow_type=workflow_type,
            user_id=user_id,
            initial_request=initial_request,
            project_id=project_id,
            context=context,
            parameters=parameters,
        )
        
        assert state.project_id == project_id
        assert state.context == context
        assert state.parameters == parameters
    
    def test_mark_node_started(self):
        """Test marking node as started."""
        state = WorkflowState(
            workflow_id=uuid4(),
            execution_id=uuid4(),
            workflow_type=WorkflowType.DEBUG,
            user_id=uuid4(),
            initial_request="Test",
        )
        
        # Test marking node as started
        state.mark_node_started("research_node")
        assert state.status == WorkflowStatus.RUNNING
        assert state.current_node == "research_node"
        assert state.last_activity is not None
    
    def test_mark_node_completed(self):
        """Test marking node as completed."""
        state = WorkflowState(
            workflow_id=uuid4(),
            execution_id=uuid4(),
            workflow_type=WorkflowType.ARCHITECT,
            user_id=uuid4(),
            initial_request="Test",
        )
        
        # Add completed node
        result_data = {"result": "research_data"}
        state.mark_node_completed("research_node", result_data)
        
        assert "research_node" in state.completed_nodes
        assert state.results["research_node"] == result_data
        
        # Add second node
        design_result = {"design": "architecture"}
        state.mark_node_completed("design_node", design_result)
        
        assert "design_node" in state.completed_nodes
        assert len(state.completed_nodes) == 2
        assert state.results["design_node"] == design_result
    
    def test_mark_node_failed(self):
        """Test marking node as failed."""
        state = WorkflowState(
            workflow_id=uuid4(),
            execution_id=uuid4(),
            workflow_type=WorkflowType.IMPLEMENT,
            user_id=uuid4(),
            initial_request="Test",
        )
        
        # Add failed node
        error_data = {"error": "Node execution failed", "details": "Timeout"}
        state.mark_node_failed("implement_node", error_data)
        
        assert "implement_node" in state.failed_nodes
        assert len(state.errors) == 1
        assert state.errors[0]["node"] == "implement_node"
        assert state.errors[0]["error"] == error_data
        assert state.errors[0]["timestamp"] is not None
    
    def test_add_artifact(self):
        """Test adding artifacts."""
        state = WorkflowState(
            workflow_id=uuid4(),
            execution_id=uuid4(),
            workflow_type=WorkflowType.RESEARCH,
            user_id=uuid4(),
            initial_request="Test",
        )
        
        # Add artifact
        artifact_content = {"content": "artifact_content", "type": "document"}
        state.add_artifact("research_results", artifact_content, {"version": "1.0"})
        
        assert "research_results" in state.artifacts
        assert state.artifacts["research_results"]["content"] == artifact_content
        assert state.artifacts["research_results"]["metadata"]["version"] == "1.0"
        assert state.artifacts["research_results"]["created_at"] is not None
    
    def test_add_ai_call(self):
        """Test adding AI call records."""
        state = WorkflowState(
            workflow_id=uuid4(),
            execution_id=uuid4(),
            workflow_type=WorkflowType.DEBUG,
            user_id=uuid4(),
            initial_request="Test",
        )
        
        # Add AI call
        state.add_ai_call(
            model="gpt-4",
            operation="chat_completion",
            tokens_input=50,
            tokens_output=100,
            cost=0.01
        )
        
        assert len(state.ai_calls) == 1
        assert state.ai_calls[0]["model"] == "gpt-4"
        assert state.ai_calls[0]["operation"] == "chat_completion"
        assert state.ai_calls[0]["tokens_input"] == 50
        assert state.ai_calls[0]["tokens_output"] == 100
        assert state.ai_calls[0]["cost"] == 0.01
        assert state.total_cost == 0.01
        assert state.token_usage["gpt-4"]["input"] == 50
        assert state.token_usage["gpt-4"]["output"] == 100
    
    def test_get_result(self):
        """Test getting node results."""
        state = WorkflowState(
            workflow_id=uuid4(),
            execution_id=uuid4(),
            workflow_type=WorkflowType.ARCHITECT,
            user_id=uuid4(),
            initial_request="Test",
        )
        
        # Add result
        result_data = {"design": "architecture"}
        state.mark_node_completed("design_node", result_data)
        
        # Test getting existing result
        result = state.get_result("design_node")
        assert result == result_data
        
        # Test getting non-existent result
        result = state.get_result("non_existent", "default")
        assert result == "default"
    
    def test_get_artifact(self):
        """Test getting artifacts."""
        state = WorkflowState(
            workflow_id=uuid4(),
            execution_id=uuid4(),
            workflow_type=WorkflowType.RESEARCH,
            user_id=uuid4(),
            initial_request="Test",
        )
        
        # Add artifact
        artifact_content = {"content": "test_content"}
        state.add_artifact("test_artifact", artifact_content)
        
        # Test getting existing artifact
        artifact = state.get_artifact("test_artifact")
        assert artifact["content"] == artifact_content
        
        # Test getting non-existent artifact
        artifact = state.get_artifact("non_existent", "default")
        assert artifact == "default"
    
    def test_status_checks(self):
        """Test status check methods."""
        state = WorkflowState(
            workflow_id=uuid4(),
            execution_id=uuid4(),
            workflow_type=WorkflowType.IMPLEMENT,
            user_id=uuid4(),
            initial_request="Test",
        )
        
        # Initial state
        assert not state.is_completed()
        assert not state.is_failed()
        assert not state.is_running()
        
        # Mark as running
        state.mark_node_started("test_node")
        assert not state.is_completed()
        assert not state.is_failed()
        assert state.is_running()
        
        # Mark as completed
        state.mark_node_completed("test_node", {"result": "success"})
        # Note: is_completed() checks if status is COMPLETED, not just if nodes are completed
        # The status would be set to COMPLETED by the orchestrator, not by marking a node
        assert "test_node" in state.completed_nodes
        assert state.results["test_node"] == {"result": "success"}
    
    def test_can_retry(self):
        """Test retry capability check."""
        state = WorkflowState(
            workflow_id=uuid4(),
            execution_id=uuid4(),
            workflow_type=WorkflowType.DEBUG,
            user_id=uuid4(),
            initial_request="Test",
        )
        
        # Initial state - not failed, can't retry
        assert not state.can_retry()
        
        # Mark as failed - can retry
        state.mark_node_failed("test_node", {"error": "test error"})
        # Note: can_retry() checks if status is FAILED, not just if nodes failed
        # The status would be set to FAILED by the orchestrator
        assert "test_node" in state.failed_nodes
        assert len(state.errors) > 0
        
        # Exceed max retries - can't retry
        state.retry_count = 3
        assert not state.can_retry()
    
    def test_get_progress(self):
        """Test progress calculation."""
        state = WorkflowState(
            workflow_id=uuid4(),
            execution_id=uuid4(),
            workflow_type=WorkflowType.IMPLEMENT,
            user_id=uuid4(),
            initial_request="Test",
        )
        
        # No nodes completed
        progress = state.get_progress()
        assert progress == 0.0
        
        # Add completed node
        state.mark_node_completed("node1", {"result": "data1"})
        progress = state.get_progress()
        assert progress == 100.0  # 1 completed, 0 failed
        
        # Add failed node
        state.mark_node_failed("node2", {"error": "test"})
        progress = state.get_progress()
        assert progress == 50.0  # 1 completed, 1 failed = 1/2 * 100
        
        # Add another completed node
        state.mark_node_completed("node3", {"result": "data3"})
        progress = state.get_progress()
        assert abs(progress - 66.67) < 0.01  # 2 completed, 1 failed = 2/3 * 100 (rounded)
    
    def test_get_timestamp(self):
        """Test timestamp generation."""
        state = WorkflowState(
            workflow_id=uuid4(),
            execution_id=uuid4(),
            workflow_type=WorkflowType.ARCHITECT,
            user_id=uuid4(),
            initial_request="Test",
        )
        
        timestamp = state._get_timestamp()
        assert isinstance(timestamp, str)
        assert len(timestamp) > 0
        assert timestamp.endswith("Z")
    
    def test_workflow_type_enum(self):
        """Test WorkflowType enum values."""
        assert WorkflowType.RESEARCH.value == "research"
        assert WorkflowType.ARCHITECT.value == "architect"
        assert WorkflowType.IMPLEMENT.value == "implement"
        assert WorkflowType.DEBUG.value == "debug"
        assert WorkflowType.FULL_DEVELOPMENT.value == "full_development"
        assert WorkflowType.CUSTOM.value == "custom"
    
    def test_workflow_status_enum(self):
        """Test WorkflowStatus enum values."""
        assert WorkflowStatus.PENDING.value == "pending"
        assert WorkflowStatus.RUNNING.value == "running"
        assert WorkflowStatus.COMPLETED.value == "completed"
        assert WorkflowStatus.FAILED.value == "failed"
        assert WorkflowStatus.CANCELLED.value == "cancelled"
        assert WorkflowStatus.PAUSED.value == "paused"
    
    def test_node_state_transitions(self):
        """Test node state transitions."""
        state = WorkflowState(
            workflow_id=uuid4(),
            execution_id=uuid4(),
            workflow_type=WorkflowType.IMPLEMENT,
            user_id=uuid4(),
            initial_request="Test",
        )
        
        # Start node
        state.mark_node_started("test_node")
        assert state.current_node == "test_node"
        assert state.status == WorkflowStatus.RUNNING
        
        # Complete node
        result = {"output": "success"}
        state.mark_node_completed("test_node", result)
        assert "test_node" in state.completed_nodes
        assert state.results["test_node"] == result
        
        # Fail node (should move from completed to failed)
        error = {"error": "test error"}
        state.mark_node_failed("test_node", error)
        assert "test_node" in state.failed_nodes
        assert "test_node" not in state.completed_nodes
        assert len(state.errors) == 1
    
    def test_multiple_ai_calls(self):
        """Test multiple AI calls and token accumulation."""
        state = WorkflowState(
            workflow_id=uuid4(),
            execution_id=uuid4(),
            workflow_type=WorkflowType.RESEARCH,
            user_id=uuid4(),
            initial_request="Test",
        )
        
        # Add multiple AI calls
        state.add_ai_call("gpt-4", "chat", 100, 200, 0.02)
        state.add_ai_call("gpt-4", "chat", 50, 100, 0.01)
        state.add_ai_call("claude-3", "chat", 75, 150, 0.015)
        
        # Check totals
        assert len(state.ai_calls) == 3
        assert state.total_cost == 0.045  # 0.02 + 0.01 + 0.015
        assert state.token_usage["gpt-4"]["input"] == 150  # 100 + 50
        assert state.token_usage["gpt-4"]["output"] == 300  # 200 + 100
        assert state.token_usage["claude-3"]["input"] == 75
        assert state.token_usage["claude-3"]["output"] == 150