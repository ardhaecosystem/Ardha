"""
Integration tests for workflow API endpoints.

Tests workflow API endpoints with real FastAPI app
to ensure proper integration and functionality.
"""

from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest
from httpx import AsyncClient

from ardha.main import create_app
from ardha.workflows.state import WorkflowStatus, WorkflowType


class TestWorkflowAPI:
    """Integration tests for workflow API endpoints."""

    @pytest.fixture
    async def client(self):
        """Create test client."""
        app = create_app()
        async with AsyncClient(app=app, base_url="http://test") as client:
            yield client

    @pytest.fixture
    def auth_headers(self):
        """Create authentication headers."""
        # Mock authentication - in real tests, this would be JWT tokens
        return {"Authorization": "Bearer mock_token"}

    @pytest.mark.asyncio
    async def test_create_workflow_success(self, client, auth_headers):
        """Test successful workflow creation."""
        workflow_data = {
            "name": "Test Research Workflow",
            "description": "A test research workflow",
            "workflow_type": "research",
            "node_sequence": ["research_node", "analysis_node"],
            "default_parameters": {"max_results": 10},
            "project_id": str(uuid4()),
        }

        with patch("ardha.api.v1.routes.workflows.get_current_user") as mock_user:
            mock_user.return_value = {"id": uuid4(), "email": "test@example.com"}

            response = await client.post(
                "/api/v1/workflows/",
                json=workflow_data,
                headers=auth_headers,
            )

            assert response.status_code == 200
            data = response.json()
            assert data["name"] == workflow_data["name"]
            assert data["description"] == workflow_data["description"]
            assert data["workflow_type"] == workflow_data["workflow_type"]
            assert "id" in data
            assert "created_at" in data

    @pytest.mark.asyncio
    async def test_create_workflow_invalid_type(self, client, auth_headers):
        """Test workflow creation with invalid type."""
        workflow_data = {
            "name": "Invalid Workflow",
            "description": "A test with invalid type",
            "workflow_type": "invalid_type",
            "node_sequence": [],
        }

        with patch("ardha.api.v1.routes.workflows.get_current_user") as mock_user:
            mock_user.return_value = {"id": uuid4(), "email": "test@example.com"}

            response = await client.post(
                "/api/v1/workflows/",
                json=workflow_data,
                headers=auth_headers,
            )

            assert response.status_code == 400
            data = response.json()
            assert "detail" in data

    @pytest.mark.asyncio
    async def test_create_workflow_unauthorized(self, client):
        """Test workflow creation without authentication."""
        workflow_data = {
            "name": "Test Workflow",
            "workflow_type": "research",
            "node_sequence": [],
        }

        response = await client.post(
            "/api/v1/workflows/",
            json=workflow_data,
        )

        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_execute_workflow_success(self, client, auth_headers):
        """Test successful workflow execution."""
        execution_data = {
            "workflow_id": str(uuid4()),
            "workflow_type": "research",
            "initial_request": "Research AI workflow systems",
            "parameters": {"max_results": 5},
            "context": {"domain": "software_engineering"},
            "project_id": str(uuid4()),
        }

        with (
            patch("ardha.api.v1.routes.workflows.get_current_user") as mock_user,
            patch("ardha.api.v1.routes.workflows.get_workflow_orchestrator") as mock_orchestrator,
        ):

            mock_user.return_value = {"id": uuid4(), "email": "test@example.com"}

            # Mock successful execution
            mock_state = AsyncMock()
            mock_state.execution_id = uuid4()
            mock_state.status = WorkflowStatus.COMPLETED
            mock_state.results = {"research": "mock_results"}
            mock_state.artifacts = {"report": "mock_report"}
            mock_state.total_cost = 0.05
            mock_state.token_usage = {"gpt-4": {"input": 100, "output": 200}}

            mock_orchestrator.return_value.execute_workflow.return_value = mock_state

            response = await client.post(
                "/api/v1/workflows/execute",
                json=execution_data,
                headers=auth_headers,
            )

            assert response.status_code == 200
            data = response.json()
            assert data["execution_id"] == str(mock_state.execution_id)
            assert data["status"] == WorkflowStatus.COMPLETED.value
            assert data["results"] == {"research": "mock_results"}
            assert data["artifacts"] == {"report": "mock_report"}
            assert data["total_cost"] == 0.05
            assert data["token_usage"] == {"gpt-4": {"input": 100, "output": 200}}

    @pytest.mark.asyncio
    async def test_execute_workflow_invalid_type(self, client, auth_headers):
        """Test workflow execution with invalid type."""
        execution_data = {
            "workflow_id": str(uuid4()),
            "workflow_type": "invalid_type",
            "initial_request": "Test request",
        }

        with patch("ardha.api.v1.routes.workflows.get_current_user") as mock_user:
            mock_user.return_value = {"id": uuid4(), "email": "test@example.com"}

            response = await client.post(
                "/api/v1/workflows/execute",
                json=execution_data,
                headers=auth_headers,
            )

            assert response.status_code == 400
            data = response.json()
            assert "detail" in data

    @pytest.mark.asyncio
    async def test_execute_workflow_unauthorized(self, client):
        """Test workflow execution without authentication."""
        execution_data = {
            "workflow_id": str(uuid4()),
            "workflow_type": "research",
            "initial_request": "Test request",
        }

        response = await client.post(
            "/api/v1/workflows/execute",
            json=execution_data,
        )

        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_get_execution_status_success(self, client, auth_headers):
        """Test getting execution status successfully."""
        execution_id = uuid4()

        with (
            patch("ardha.api.v1.routes.workflows.get_current_user") as mock_user,
            patch("ardha.api.v1.routes.workflows.get_workflow_orchestrator") as mock_orchestrator,
        ):

            mock_user.return_value = {"id": uuid4(), "email": "test@example.com"}

            # Mock execution state
            mock_state = AsyncMock()
            mock_state.execution_id = execution_id
            mock_state.status = WorkflowStatus.RUNNING
            mock_state.current_node = "research_node"
            mock_state.completed_nodes = []
            mock_state.failed_nodes = []
            mock_state.results = {}
            mock_state.artifacts = {}
            mock_state.total_cost = 0.02
            mock_state.token_usage = {"gpt-4": {"input": 50, "output": 100}}
            mock_state.created_at = "2024-01-01T00:00:00Z"
            mock_state.started_at = "2024-01-01T00:01:00Z"
            mock_state.last_activity = "2024-01-01T00:02:00Z"

            mock_orchestrator.return_value.get_execution_status.return_value = mock_state

            response = await client.get(
                f"/api/v1/workflows/executions/{execution_id}",
                headers=auth_headers,
            )

            assert response.status_code == 200
            data = response.json()
            assert data["execution_id"] == str(execution_id)
            assert data["status"] == WorkflowStatus.RUNNING.value
            assert data["current_node"] == "research_node"
            assert data["completed_nodes"] == []
            assert data["failed_nodes"] == []
            assert data["results"] == {}
            assert data["artifacts"] == {}
            assert data["total_cost"] == 0.02
            assert data["token_usage"] == {"gpt-4": {"input": 50, "output": 100}}
            assert data["created_at"] == "2024-01-01T00:00:00Z"
            assert data["started_at"] == "2024-01-01T00:01:00Z"
            assert data["last_activity"] == "2024-01-01T00:02:00Z"

    @pytest.mark.asyncio
    async def test_get_execution_status_not_found(self, client, auth_headers):
        """Test getting status for non-existent execution."""
        execution_id = uuid4()

        with (
            patch("ardha.api.v1.routes.workflows.get_current_user") as mock_user,
            patch("ardha.api.v1.routes.workflows.get_workflow_orchestrator") as mock_orchestrator,
        ):

            mock_user.return_value = {"id": uuid4(), "email": "test@example.com"}
            mock_orchestrator.return_value.get_execution_status.return_value = None

            response = await client.get(
                f"/api/v1/workflows/executions/{execution_id}",
                headers=auth_headers,
            )

            assert response.status_code == 404
            data = response.json()
            assert "detail" in data

    @pytest.mark.asyncio
    async def test_get_execution_status_unauthorized(self, client):
        """Test getting execution status without authentication."""
        execution_id = uuid4()

        response = await client.get(
            f"/api/v1/workflows/executions/{execution_id}",
        )

        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_list_executions_success(self, client, auth_headers):
        """Test listing user executions successfully."""
        with (
            patch("ardha.api.v1.routes.workflows.get_current_user") as mock_user,
            patch("ardha.api.v1.routes.workflows.get_workflow_orchestrator") as mock_orchestrator,
        ):

            user_id = uuid4()
            mock_user.return_value = {"id": user_id, "email": "test@example.com"}

            # Mock execution list
            mock_executions = [
                {
                    "execution_id": uuid4(),
                    "workflow_type": "research",
                    "status": "completed",
                    "created_at": "2024-01-01T00:00:00Z",
                },
                {
                    "execution_id": uuid4(),
                    "workflow_type": "implement",
                    "status": "running",
                    "created_at": "2024-01-01T01:00:00Z",
                },
            ]

            mock_orchestrator.return_value.list_active_executions.return_value = mock_executions

            response = await client.get(
                "/api/v1/workflows/executions",
                headers=auth_headers,
            )

            assert response.status_code == 200
            data = response.json()
            assert "executions" in data
            assert len(data["executions"]) == 2
            assert data["total"] == 2

            # Verify execution data
            for i, execution in enumerate(mock_executions):
                assert data["executions"][i]["execution_id"] == str(execution["execution_id"])
                assert data["executions"][i]["workflow_type"] == execution["workflow_type"]
                assert data["executions"][i]["status"] == execution["status"]
                assert data["executions"][i]["created_at"] == execution["created_at"]

    @pytest.mark.asyncio
    async def test_list_executions_with_filters(self, client, auth_headers):
        """Test listing executions with filters."""
        with (
            patch("ardha.api.v1.routes.workflows.get_current_user") as mock_user,
            patch("ardha.api.v1.routes.workflows.get_workflow_orchestrator") as mock_orchestrator,
        ):

            mock_user.return_value = {"id": uuid4(), "email": "test@example.com"}

            # Mock filtered executions
            mock_executions = [
                {
                    "execution_id": uuid4(),
                    "workflow_type": "research",
                    "status": "completed",
                },
            ]

            mock_orchestrator.return_value.list_active_executions.return_value = mock_executions

            response = await client.get(
                "/api/v1/workflows/executions?workflow_type=research&status=completed&limit=10",
                headers=auth_headers,
            )

            assert response.status_code == 200
            data = response.json()
            assert len(data["executions"]) == 1
            assert data["executions"][0]["workflow_type"] == "research"
            assert data["executions"][0]["status"] == "completed"

    @pytest.mark.asyncio
    async def test_list_executions_unauthorized(self, client):
        """Test listing executions without authentication."""
        response = await client.get("/api/v1/workflows/executions")

        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_cancel_execution_success(self, client, auth_headers):
        """Test successful execution cancellation."""
        execution_id = uuid4()

        with (
            patch("ardha.api.v1.routes.workflows.get_current_user") as mock_user,
            patch("ardha.api.v1.routes.workflows.get_workflow_orchestrator") as mock_orchestrator,
        ):

            mock_user.return_value = {"id": uuid4(), "email": "test@example.com"}
            mock_orchestrator.return_value.cancel_execution.return_value = True

            response = await client.delete(
                f"/api/v1/workflows/executions/{execution_id}",
                headers=auth_headers,
            )

            assert response.status_code == 200
            data = response.json()
            assert data["message"] == "Execution cancelled successfully"

    @pytest.mark.asyncio
    async def test_cancel_execution_not_found(self, client, auth_headers):
        """Test cancelling non-existent execution."""
        execution_id = uuid4()

        with (
            patch("ardha.api.v1.routes.workflows.get_current_user") as mock_user,
            patch("ardha.api.v1.routes.workflows.get_workflow_orchestrator") as mock_orchestrator,
        ):

            mock_user.return_value = {"id": uuid4(), "email": "test@example.com"}
            mock_orchestrator.return_value.cancel_execution.return_value = False

            response = await client.delete(
                f"/api/v1/workflows/executions/{execution_id}",
                headers=auth_headers,
            )

            assert response.status_code == 404
            data = response.json()
            assert "detail" in data

    @pytest.mark.asyncio
    async def test_cancel_execution_unauthorized(self, client):
        """Test cancelling execution without authentication."""
        execution_id = uuid4()

        response = await client.delete(
            f"/api/v1/workflows/executions/{execution_id}",
        )

        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_stream_execution_success(self, client, auth_headers):
        """Test successful execution streaming."""
        execution_id = uuid4()

        with (
            patch("ardha.api.v1.routes.workflows.get_current_user") as mock_user,
            patch("ardha.api.v1.routes.workflows.get_workflow_orchestrator") as mock_orchestrator,
        ):

            mock_user.return_value = {"id": uuid4(), "email": "test@example.com"}

            # Mock execution state
            mock_state = AsyncMock()
            mock_state.execution_id = execution_id
            mock_state.user_id = mock_user.return_value["id"]
            mock_state.status = WorkflowStatus.RUNNING
            mock_state.last_activity = "2024-01-01T00:00:00Z"

            mock_orchestrator.return_value.get_execution_status.return_value = mock_state

            response = await client.get(
                f"/api/v1/workflows/executions/{execution_id}/stream",
                headers=auth_headers,
            )

            assert response.status_code == 200
            assert response.headers["content-type"] == "text/event-stream"
            assert response.headers["cache-control"] == "no-cache"
            assert response.headers["connection"] == "keep-alive"

            # Check streaming content
            content = response.text
            assert "data: running" in content
            assert "event: complete" in content

    @pytest.mark.asyncio
    async def test_stream_execution_not_found(self, client, auth_headers):
        """Test streaming non-existent execution."""
        execution_id = uuid4()

        with (
            patch("ardha.api.v1.routes.workflows.get_current_user") as mock_user,
            patch("ardha.api.v1.routes.workflows.get_workflow_orchestrator") as mock_orchestrator,
        ):

            mock_user.return_value = {"id": uuid4(), "email": "test@example.com"}
            mock_orchestrator.return_value.get_execution_status.return_value = None

            response = await client.get(
                f"/api/v1/workflows/executions/{execution_id}/stream",
                headers=auth_headers,
            )

            assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_stream_execution_unauthorized(self, client):
        """Test streaming execution without authentication."""
        execution_id = uuid4()

        response = await client.get(
            f"/api/v1/workflows/executions/{execution_id}/stream",
        )

        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_stream_execution_access_denied(self, client, auth_headers):
        """Test streaming execution owned by different user."""
        execution_id = uuid4()

        with (
            patch("ardha.api.v1.routes.workflows.get_current_user") as mock_user,
            patch("ardha.api.v1.routes.workflows.get_workflow_orchestrator") as mock_orchestrator,
        ):

            user_id = uuid4()
            different_user_id = uuid4()
            mock_user.return_value = {"id": user_id, "email": "test@example.com"}

            # Mock execution owned by different user
            mock_state = AsyncMock()
            mock_state.execution_id = execution_id
            mock_state.user_id = different_user_id  # Different user
            mock_state.status = WorkflowStatus.RUNNING

            mock_orchestrator.return_value.get_execution_status.return_value = mock_state

            response = await client.get(
                f"/api/v1/workflows/executions/{execution_id}/stream",
                headers=auth_headers,
            )

            assert response.status_code == 403
            data = response.json()
            assert "detail" in data
