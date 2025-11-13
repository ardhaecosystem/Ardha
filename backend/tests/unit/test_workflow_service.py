"""
Unit tests for WorkflowService.

This module tests the workflow service functionality
including execution management and state tracking.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

from ardha.services.workflow_service import WorkflowService
from ardha.repositories.workflow_repository import WorkflowRepository
from ardha.workflows.orchestrator import WorkflowOrchestrator
from ardha.workflows.state import WorkflowStatus, WorkflowType
from ardha.core.exceptions import ValidationError, NotFoundError


@pytest.fixture
def mock_db_session():
    """Create a mock database session."""
    return AsyncMock()


@pytest.fixture
def mock_repository():
    """Create a mock workflow repository."""
    return AsyncMock(spec=WorkflowRepository)


@pytest.fixture
def mock_orchestrator():
    """Create a mock workflow orchestrator."""
    return AsyncMock(spec=WorkflowOrchestrator)


@pytest.fixture
def workflow_service(mock_db_session, mock_repository, mock_orchestrator):
    """Create a workflow service with mocked dependencies."""
    service = WorkflowService(mock_db_session)
    service.repository = mock_repository
    service.orchestrator = mock_orchestrator
    return service


class TestWorkflowService:
    """Test cases for WorkflowService."""
    
    @pytest.mark.asyncio
    async def test_execute_workflow_success(self, workflow_service, mock_repository, mock_orchestrator):
        """Test successful workflow execution."""
        # Arrange
        user_id = uuid4()
        workflow_type = "research"
        initial_request = "Test request"
        project_id = uuid4()
        parameters = {"test": "param"}
        context = {"test": "context"}
        
        # Mock execution creation
        mock_execution = MagicMock()
        mock_execution.id = uuid4()
        mock_execution.user_id = user_id
        mock_execution.workflow_type = workflow_type
        mock_execution.project_id = project_id
        mock_execution.input_data = {
            "initial_request": initial_request,
            "parameters": parameters,
            "context": context
        }
        mock_execution.status = WorkflowStatus.PENDING
        mock_execution.output_data = {"results": {}}
        mock_execution.total_tokens = 100
        mock_execution.total_cost = 0.5
        mock_execution.created_at = MagicMock()
        mock_execution.started_at = None
        mock_execution.completed_at = None
        mock_execution.updated_at = MagicMock()
        
        mock_repository.create.return_value = mock_execution
        mock_repository.get_by_id.return_value = mock_execution
        
        # Mock orchestrator execution
        mock_state = MagicMock()
        mock_state.status = WorkflowStatus.COMPLETED
        mock_state.results = {"test": "result"}
        mock_state.artifacts = {}
        mock_state.metadata = {}
        mock_state.total_cost = 0.5
        mock_state.token_usage = {"total": 100}
        mock_orchestrator.execute_workflow.return_value = mock_state
        
        # Act
        result = await workflow_service.execute_workflow(
            user_id=user_id,
            workflow_type=workflow_type,
            initial_request=initial_request,
            project_id=project_id,
            parameters=parameters,
            context=context
        )
        
        # Assert
        assert result.id == mock_execution.id
        assert result.user_id == user_id
        assert result.workflow_type == workflow_type
        mock_repository.create.assert_called_once()
        mock_orchestrator.execute_workflow.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_execute_workflow_invalid_type(self, workflow_service):
        """Test workflow execution with invalid type."""
        # Arrange
        user_id = uuid4()
        workflow_type = "invalid_type"
        initial_request = "Test request"
        
        # Act & Assert
        with pytest.raises(ValidationError, match="Invalid workflow type"):
            await workflow_service.execute_workflow(
                user_id=user_id,
                workflow_type=workflow_type,
                initial_request=initial_request
            )
    
    @pytest.mark.asyncio
    async def test_execute_workflow_empty_request(self, workflow_service):
        """Test workflow execution with empty request."""
        # Arrange
        user_id = uuid4()
        workflow_type = "research"
        initial_request = ""
        
        # Act & Assert
        with pytest.raises(ValidationError, match="Initial request cannot be empty"):
            await workflow_service.execute_workflow(
                user_id=user_id,
                workflow_type=workflow_type,
                initial_request=initial_request
            )
    
    @pytest.mark.asyncio
    async def test_get_execution_success(self, workflow_service, mock_repository):
        """Test successful execution retrieval."""
        # Arrange
        user_id = uuid4()
        execution_id = uuid4()
        
        mock_execution = MagicMock()
        mock_execution.user_id = user_id
        mock_repository.get_by_id.return_value = mock_execution
        
        # Act
        result = await workflow_service.get_execution(execution_id, user_id)
        
        # Assert
        assert result == mock_execution
        mock_repository.get_by_id.assert_called_once_with(execution_id)
    
    @pytest.mark.asyncio
    async def test_get_execution_not_found(self, workflow_service, mock_repository):
        """Test execution retrieval when not found."""
        # Arrange
        user_id = uuid4()
        execution_id = uuid4()
        
        mock_repository.get_by_id.return_value = None
        
        # Act
        result = await workflow_service.get_execution(execution_id, user_id)
        
        # Assert
        assert result is None
        mock_repository.get_by_id.assert_called_once_with(execution_id)
    
    @pytest.mark.asyncio
    async def test_get_execution_access_denied(self, workflow_service, mock_repository):
        """Test execution retrieval with access denied."""
        # Arrange
        user_id = uuid4()
        other_user_id = uuid4()
        execution_id = uuid4()
        
        mock_execution = MagicMock()
        mock_execution.user_id = other_user_id  # Different user
        mock_repository.get_by_id.return_value = mock_execution
        
        # Act & Assert
        with pytest.raises(NotFoundError, match="Execution not found"):
            await workflow_service.get_execution(execution_id, user_id)
    
    @pytest.mark.asyncio
    async def test_cancel_execution_success(self, workflow_service, mock_repository, mock_orchestrator):
        """Test successful execution cancellation."""
        # Arrange
        user_id = uuid4()
        execution_id = uuid4()
        reason = "Test cancellation"
        
        mock_execution = MagicMock()
        mock_execution.user_id = user_id
        mock_execution.status = WorkflowStatus.RUNNING
        mock_execution.can_resume = False
        mock_repository.get_by_id.return_value = mock_execution
        
        mock_orchestrator.cancel_execution.return_value = True
        
        # Act
        result = await workflow_service.cancel_execution(execution_id, user_id, reason)
        
        # Assert
        assert result is True
        mock_repository.get_by_id.assert_called_once_with(execution_id)
        mock_orchestrator.cancel_execution.assert_called_once_with(execution_id, reason)
        mock_repository.update_status.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_cancel_execution_not_found(self, workflow_service, mock_repository):
        """Test execution cancellation when not found."""
        # Arrange
        user_id = uuid4()
        execution_id = uuid4()
        
        mock_repository.get_by_id.return_value = None
        
        # Act & Assert
        with pytest.raises(NotFoundError, match="Execution not found"):
            await workflow_service.cancel_execution(execution_id, user_id)
    
    @pytest.mark.asyncio
    async def test_list_user_executions(self, workflow_service, mock_repository):
        """Test listing user executions."""
        # Arrange
        user_id = uuid4()
        status = WorkflowStatus.COMPLETED
        workflow_type = "research"
        project_id = uuid4()
        limit = 10
        offset = 0
        
        mock_executions = [MagicMock(), MagicMock()]
        mock_repository.get_user_executions.return_value = mock_executions
        
        # Act
        result = await workflow_service.list_user_executions(
            user_id=user_id,
            status=status,
            workflow_type=workflow_type,
            project_id=project_id,
            limit=limit,
            offset=offset
        )
        
        # Assert
        assert result == mock_executions
        mock_repository.get_user_executions.assert_called_once_with(
            user_id=user_id,
            status=status,
            workflow_type=workflow_type,
            project_id=project_id,
            limit=limit,
            offset=offset
        )
    
    @pytest.mark.asyncio
    async def test_get_execution_stats(self, workflow_service, mock_repository):
        """Test getting execution statistics."""
        # Arrange
        user_id = uuid4()
        workflow_type = "research"
        project_id = uuid4()
        
        mock_stats = {
            "total_executions": 10,
            "status_breakdown": {"completed": 8, "failed": 2},
            "total_tokens": 1000,
            "total_cost": 5.0,
            "average_cost": 0.5
        }
        mock_repository.get_execution_stats.return_value = mock_stats
        
        # Act
        result = await workflow_service.get_execution_stats(
            user_id=user_id,
            workflow_type=workflow_type,
            project_id=project_id
        )
        
        # Assert
        assert result == mock_stats
        mock_repository.get_execution_stats.assert_called_once_with(
            user_id=user_id,
            workflow_type=workflow_type,
            project_id=project_id
        )
    
    @pytest.mark.asyncio
    async def test_delete_execution_success(self, workflow_service, mock_repository):
        """Test successful execution deletion."""
        # Arrange
        user_id = uuid4()
        execution_id = uuid4()
        
        mock_execution = MagicMock()
        mock_execution.user_id = user_id
        mock_execution.status = WorkflowStatus.COMPLETED
        mock_repository.get_by_id.return_value = mock_execution
        mock_repository.delete.return_value = True
        
        # Act
        result = await workflow_service.delete_execution(execution_id, user_id)
        
        # Assert
        assert result is True
        mock_repository.get_by_id.assert_called_once_with(execution_id)
        mock_repository.delete.assert_called_once_with(execution_id)
    
    @pytest.mark.asyncio
    async def test_delete_execution_not_found(self, workflow_service, mock_repository):
        """Test execution deletion when not found."""
        # Arrange
        user_id = uuid4()
        execution_id = uuid4()
        
        mock_repository.get_by_id.return_value = None
        
        # Act & Assert
        with pytest.raises(NotFoundError, match="Execution not found"):
            await workflow_service.delete_execution(execution_id, user_id)
    
    @pytest.mark.asyncio
    async def test_delete_running_execution(self, workflow_service, mock_repository):
        """Test deletion of running execution should fail."""
        # Arrange
        user_id = uuid4()
        execution_id = uuid4()
        
        mock_execution = MagicMock()
        mock_execution.user_id = user_id
        mock_execution.status = WorkflowStatus.RUNNING
        mock_repository.get_by_id.return_value = mock_execution
        
        # Act & Assert
        with pytest.raises(ValidationError, match="Cannot delete running execution"):
            await workflow_service.delete_execution(execution_id, user_id)