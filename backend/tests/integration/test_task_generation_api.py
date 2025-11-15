"""
Integration tests for Task Generation workflow API endpoints.

This module tests the complete Task Generation workflow API including
execution, status tracking, progress streaming, and results retrieval.
"""

import asyncio
import json
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from httpx import AsyncClient

from ardha.api.v1.routes.task_generation import router
from ardha.schemas.workflows.task_generation import (
    TaskGenerationState,
    TaskGenerationWorkflowConfig,
)
from ardha.workflows.state import WorkflowStatus, WorkflowType
from ardha.workflows.task_generation_workflow import TaskGenerationWorkflow


class TestTaskGenerationAPI:
    """Integration tests for Task Generation API endpoints."""

    @pytest.fixture
    def app(self):
        """Create FastAPI app with task generation router."""
        from ardha.main import app

        return app

    @pytest.fixture
    def client(self, app):
        """Create test client."""
        from ardha.core.security import get_current_active_user

        # Create mock user for dependency override
        mock_user = MagicMock()
        mock_user.id = uuid4()

        # Override authentication dependency
        app.dependency_overrides[get_current_active_user] = lambda: mock_user

        try:
            yield TestClient(app)
        finally:
            # Clear override
            app.dependency_overrides.clear()

    @pytest.fixture
    def async_client(self, app):
        """Create async test client."""
        from ardha.main import app

        return AsyncClient(app=app, base_url="http://test")

    @pytest.fixture
    def mock_user(self):
        """Create mock authenticated user."""
        user = MagicMock()
        user.id = uuid4()
        return user

    @pytest.fixture
    def mock_workflow(self):
        """Create mock TaskGenerationWorkflow."""
        workflow = MagicMock()
        workflow.execute = AsyncMock()
        workflow.get_execution_status = AsyncMock()
        workflow.cancel_execution = AsyncMock()
        return workflow

    def test_execute_task_generation_success(self, client, mock_user, mock_workflow):
        """Test successful task generation execution."""
        # Mock workflow execution
        execution_id = uuid4()
        workflow_id = uuid4()

        mock_workflow.execute.return_value = TaskGenerationState(
            workflow_id=workflow_id,
            execution_id=execution_id,
            workflow_type=WorkflowType.CUSTOM,
            user_id=mock_user.id,
            initial_request="Generate tasks and OpenSpec from PRD",
            prd_content="Test PRD content",
            status="completed",
        )

        # Mock dependencies
        with patch(
            "ardha.api.v1.routes.task_generation.get_current_active_user", return_value=mock_user
        ):
            with patch(
                "ardha.api.v1.routes.task_generation.get_task_generation_workflow",
                return_value=mock_workflow,
            ):
                with patch("ardha.api.v1.routes.task_generation.BackgroundTasks"):
                    # Make request
                    response = client.post(
                        "/api/v1/task-generation/execute",
                        json={
                            "prd_content": "Test PRD for user authentication system",
                            "project_id": str(uuid4()),
                            "project_context": {"tech_stack": "Python"},
                            "existing_tasks": [],
                            "parameters": {},
                        },
                    )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "pending"
        assert "workflow_id" in data
        assert "execution_id" in data
        assert "progress_url" in data

    def test_execute_task_generation_invalid_request(self, client, mock_user):
        """Test task generation execution with invalid request."""
        with patch(
            "ardha.api.v1.routes.task_generation.get_current_active_user", return_value=mock_user
        ):
            # Make request with missing required field
            response = client.post(
                "/api/v1/task-generation/execute",
                json={
                    "project_context": {"tech_stack": "Python"},
                    # Missing prd_content
                },
            )

        assert response.status_code == 422  # Validation error

    def test_get_task_generation_status_success(self, client, mock_user, mock_workflow):
        """Test successful task generation status retrieval."""
        execution_id = uuid4()
        workflow_id = uuid4()

        # Mock workflow state
        mock_state = TaskGenerationState(
            workflow_id=workflow_id,
            execution_id=execution_id,
            workflow_type=WorkflowType.CUSTOM,
            user_id=mock_user.id,
            initial_request="Generate tasks and OpenSpec from PRD",
            prd_content="Test PRD",
            status=WorkflowStatus.RUNNING,
            current_task_step="breakdown_tasks",
            task_progress_percentage=40.0,
            completed_task_steps=["analyze_prd"],
            failed_task_steps=[],
            prd_analysis_quality=0.8,
            task_breakdown_completeness=0.0,
            dependency_accuracy=0.0,
            effort_estimation_quality=0.0,
            openspec_quality_score=0.0,
            created_at="2025-01-01T00:00:00Z",
            started_at="2025-01-01T00:01:00Z",
        )

        mock_workflow.get_execution_status.return_value = mock_state

        # Override authentication dependency
        from ardha.core.security import get_current_active_user
        from ardha.main import app

        app.dependency_overrides[get_current_active_user] = lambda: mock_user

        try:
            with patch(
                "ardha.api.v1.routes.task_generation.get_task_generation_workflow",
                return_value=mock_workflow,
            ):
                response = client.get(f"/api/v1/task-generation/{execution_id}/status")
        finally:
            # Clear override
            app.dependency_overrides.clear()

        assert response.status_code == 200
        data = response.json()
        assert data["execution_id"] == str(execution_id)
        assert data["workflow_id"] == str(workflow_id)
        assert data["status"] == "running"
        assert data["current_step"] == "breakdown_tasks"
        assert data["progress_percentage"] == 40.0
        assert data["completed_steps"] == ["analyze_prd"]
        assert (
            abs(data["quality_score"] - 0.16) < 1e-10
        )  # Weighted average with only prd_analysis_quality

    def test_get_task_generation_status_not_found(self, client, mock_user, mock_workflow):
        """Test status retrieval for non-existent execution."""
        execution_id = uuid4()
        mock_workflow.get_execution_status.return_value = None

        with patch(
            "ardha.api.v1.routes.task_generation.get_task_generation_workflow",
            return_value=mock_workflow,
        ):
            response = client.get(f"/api/v1/task-generation/{execution_id}/status")

        assert response.status_code == 404
        data = response.json()
        assert "not found" in data["detail"].lower()

    def test_get_task_generation_status_access_denied(self, client, mock_workflow):
        """Test status retrieval with access denied."""
        execution_id = uuid4()
        other_user_id = uuid4()

        # Mock state belonging to different user
        mock_state = TaskGenerationState(
            workflow_id=uuid4(),
            execution_id=execution_id,
            workflow_type=WorkflowType.CUSTOM,
            user_id=other_user_id,  # Different user
            initial_request="Generate tasks and OpenSpec from PRD",
            prd_content="Test PRD",
            status="completed",
        )

        mock_workflow.get_execution_status.return_value = mock_state

        # Mock current user
        current_user = MagicMock()
        current_user.id = uuid4()

        with patch(
            "ardha.api.v1.routes.task_generation.get_current_active_user", return_value=current_user
        ):
            with patch(
                "ardha.api.v1.routes.task_generation.get_task_generation_workflow",
                return_value=mock_workflow,
            ):
                response = client.get(f"/api/v1/task-generation/{execution_id}/status")

        assert response.status_code == 403
        data = response.json()
        assert "access denied" in data["detail"].lower()

    def test_get_task_generation_results_success(self, client, mock_user, mock_workflow):
        """Test successful task generation results retrieval."""
        execution_id = uuid4()
        workflow_id = uuid4()

        # Mock completed workflow state
        mock_state = TaskGenerationState(
            workflow_id=workflow_id,
            execution_id=execution_id,
            workflow_type=WorkflowType.CUSTOM,
            user_id=mock_user.id,
            initial_request="Generate tasks and OpenSpec from PRD",
            prd_content="Test PRD",
            status="completed",
            prd_analysis={"core_features": [{"name": "Auth"}]},
            task_breakdown=[{"id": "task1", "title": "Login API"}],
            task_dependencies=[{"task": "task1", "depends_on": ["task2"]}],
            effort_estimates={"project_summary": {"total_hours": 40}},
            openspec_proposal={"proposal": {"id": "proposal-001"}, "files": {}},
            change_directory_path="openspec/changes/task-gen-123",
            prd_analysis_quality=0.8,
            task_breakdown_completeness=0.9,
            dependency_accuracy=0.7,
            effort_estimation_quality=0.8,
            openspec_quality_score=0.9,
            created_at="2025-01-01T00:00:00Z",
            completed_at="2025-01-01T00:30:00Z",
        )

        mock_workflow.get_execution_status.return_value = mock_state

        # Override authentication dependency
        from ardha.core.security import get_current_active_user
        from ardha.main import app

        app.dependency_overrides[get_current_active_user] = lambda: mock_user

        try:
            with patch(
                "ardha.api.v1.routes.task_generation.get_task_generation_workflow",
                return_value=mock_workflow,
            ):
                response = client.get(f"/api/v1/task-generation/{execution_id}/results")
        finally:
            # Clear override
            app.dependency_overrides.clear()

        assert response.status_code == 200
        data = response.json()
        assert data["execution_id"] == str(execution_id)
        assert data["workflow_id"] == str(workflow_id)
        assert data["status"] == "completed"
        assert data["prd_analysis"]["core_features"][0]["name"] == "Auth"
        assert len(data["task_breakdown"]) == 1
        assert data["task_breakdown"][0]["title"] == "Login API"
        assert data["effort_estimates"]["project_summary"]["total_hours"] == 40
        assert data["openspec_proposal"]["proposal"]["id"] == "proposal-001"
        assert data["change_directory_path"] == "openspec/changes/task-gen-123"
        assert data["quality_metrics"]["prd_analysis_quality"] == 0.8
        assert data["quality_metrics"]["overall_quality_score"] > 0.5

    def test_get_task_generation_results_not_completed(self, client, mock_user, mock_workflow):
        """Test results retrieval for non-completed execution."""
        execution_id = uuid4()

        # Mock running workflow state
        mock_state = TaskGenerationState(
            workflow_id=uuid4(),
            execution_id=execution_id,
            workflow_type=WorkflowType.CUSTOM,
            user_id=mock_user.id,
            initial_request="Generate tasks and OpenSpec from PRD",
            prd_content="Test PRD",
            status="running",  # Not completed
        )

        mock_workflow.get_execution_status.return_value = mock_state

        # Override authentication dependency
        from ardha.core.security import get_current_active_user
        from ardha.main import app

        app.dependency_overrides[get_current_active_user] = lambda: mock_user

        try:
            with patch(
                "ardha.api.v1.routes.task_generation.get_task_generation_workflow",
                return_value=mock_workflow,
            ):
                response = client.get(f"/api/v1/task-generation/{execution_id}/results")
        finally:
            # Clear override
            app.dependency_overrides.clear()

        assert response.status_code == 400
        data = response.json()
        assert "not yet completed" in data["detail"].lower()

    def test_cancel_task_generation_success(self, client, mock_user, mock_workflow):
        """Test successful task generation cancellation."""
        execution_id = uuid4()

        # Mock running workflow state
        mock_state = TaskGenerationState(
            workflow_id=uuid4(),
            execution_id=execution_id,
            workflow_type=WorkflowType.CUSTOM,
            user_id=mock_user.id,
            initial_request="Generate tasks and OpenSpec from PRD",
            prd_content="Test PRD",
            status=WorkflowStatus.RUNNING,
        )

        mock_workflow.get_execution_status.return_value = mock_state
        mock_workflow.cancel_execution.return_value = True

        # Override authentication dependency
        from ardha.core.security import get_current_active_user
        from ardha.main import app

        app.dependency_overrides[get_current_active_user] = lambda: mock_user

        try:
            with patch(
                "ardha.api.v1.routes.task_generation.get_task_generation_workflow",
                return_value=mock_workflow,
            ):
                response = client.delete(
                    f"/api/v1/task-generation/{execution_id}?reason=Test cancellation"
                )
        finally:
            # Clear override
            app.dependency_overrides.clear()

        assert response.status_code == 200
        data = response.json()
        assert "cancelled successfully" in data["message"].lower()
        assert data["execution_id"] == str(execution_id)
        assert data["reason"] == "Test cancellation"

        # Verify cancel was called
        mock_workflow.cancel_execution.assert_called_once_with(execution_id, "Test cancellation")

    def test_cancel_task_generation_not_found(self, client, mock_user, mock_workflow):
        """Test cancellation for non-existent execution."""
        execution_id = uuid4()
        mock_workflow.get_execution_status.return_value = None

        # Override authentication dependency
        from ardha.core.security import get_current_active_user
        from ardha.main import app

        app.dependency_overrides[get_current_active_user] = lambda: mock_user

        try:
            with patch(
                "ardha.api.v1.routes.task_generation.get_task_generation_workflow",
                return_value=mock_workflow,
            ):
                response = client.delete(f"/api/v1/task-generation/{execution_id}")
        finally:
            # Clear override
            app.dependency_overrides.clear()

        assert response.status_code == 404
        data = response.json()
        assert "not found" in data["detail"].lower()

    def test_cancel_task_generation_already_completed(self, client, mock_user, mock_workflow):
        """Test cancellation for already completed execution."""
        execution_id = uuid4()

        # Mock completed workflow state
        mock_state = TaskGenerationState(
            workflow_id=uuid4(),
            execution_id=execution_id,
            workflow_type=WorkflowType.CUSTOM,
            user_id=mock_user.id,
            initial_request="Generate tasks and OpenSpec from PRD",
            prd_content="Test PRD",
            status="completed",
        )

        mock_workflow.get_execution_status.return_value = mock_state
        mock_workflow.cancel_execution.return_value = False  # Cannot cancel completed

        # Override authentication dependency
        from ardha.core.security import get_current_active_user
        from ardha.main import app

        app.dependency_overrides[get_current_active_user] = lambda: mock_user

        try:
            with patch(
                "ardha.api.v1.routes.task_generation.get_task_generation_workflow",
                return_value=mock_workflow,
            ):
                response = client.delete(f"/api/v1/task-generation/{execution_id}")
        finally:
            # Clear override
            app.dependency_overrides.clear()

        assert response.status_code == 400
        data = response.json()
        assert "cannot cancel" in data["detail"].lower()

    def test_get_task_generation_config(self, client, mock_user):
        """Test getting task generation configuration."""
        # Override authentication dependency
        from ardha.core.security import get_current_active_user
        from ardha.main import app

        app.dependency_overrides[get_current_active_user] = lambda: mock_user

        try:
            response = client.get("/api/v1/task-generation/config")
        finally:
            # Clear override
            app.dependency_overrides.clear()

        assert response.status_code == 200
        data = response.json()
        assert "analyze_prd_model" in data
        assert "breakdown_tasks_model" in data
        assert "define_dependencies_model" in data
        assert "estimate_effort_model" in data
        assert "generate_openspec_model" in data
        assert "max_retries_per_step" in data
        assert "enable_streaming" in data

    def test_list_task_generation_executions(self, client, mock_user):
        """Test listing task generation executions."""
        # Override authentication dependency
        from ardha.core.security import get_current_active_user
        from ardha.main import app

        app.dependency_overrides[get_current_active_user] = lambda: mock_user

        try:
            response = client.get("/api/v1/task-generation/executions")
        finally:
            # Clear override
            app.dependency_overrides.clear()

        assert response.status_code == 200
        data = response.json()
        assert "executions" in data
        assert "total" in data
        assert "limit" in data
        assert "offset" in data
        assert data["executions"] == []  # Empty for now (no persistence)
        assert data["total"] == 0

    def test_list_task_generation_executions_with_filters(self, client, mock_user):
        """Test listing task generation executions with filters."""
        # Override authentication dependency
        from ardha.core.security import get_current_active_user
        from ardha.main import app

        app.dependency_overrides[get_current_active_user] = lambda: mock_user

        try:
            response = client.get(
                "/api/v1/task-generation/executions?limit=10&offset=5&status=completed"
            )
        finally:
            # Clear override
            app.dependency_overrides.clear()

        assert response.status_code == 200
        data = response.json()
        assert data["limit"] == 10
        assert data["offset"] == 5
        assert data["status_filter"] == "completed"


class TestTaskGenerationProgressStreaming:
    """Tests for task generation progress streaming."""

    @pytest.fixture
    def app(self):
        """Create FastAPI app with task generation router."""
        from ardha.main import app

        return app

    @pytest.fixture
    def client(self, app):
        """Create test client."""
        from ardha.core.security import get_current_active_user

        # Create mock user for dependency override
        mock_user = MagicMock()
        mock_user.id = uuid4()

        # Override authentication dependency
        app.dependency_overrides[get_current_active_user] = lambda: mock_user

        try:
            yield TestClient(app)
        finally:
            # Clear override
            app.dependency_overrides.clear()

    @pytest.fixture
    def mock_user(self):
        """Create mock authenticated user."""
        user = MagicMock()
        user.id = uuid4()
        return user

    @pytest.fixture
    def mock_workflow(self):
        """Create mock TaskGenerationWorkflow."""
        workflow = MagicMock()
        workflow.get_execution_status = AsyncMock()
        return workflow

    def test_progress_stream_success(self, client, mock_user, mock_workflow):
        """Test successful progress streaming."""
        execution_id = uuid4()

        # Mock workflow state
        mock_state = TaskGenerationState(
            workflow_id=uuid4(),
            execution_id=execution_id,
            workflow_type=WorkflowType.CUSTOM,
            user_id=mock_user.id,
            initial_request="Generate tasks and OpenSpec from PRD",
            prd_content="Test PRD",
            status="running",
            current_task_step="breakdown_tasks",
            task_progress_percentage=40.0,
            completed_task_steps=["analyze_prd"],
            failed_task_steps=[],
            prd_analysis_quality=0.8,
            task_breakdown_completeness=0.0,
            dependency_accuracy=0.0,
            effort_estimation_quality=0.0,
            openspec_quality_score=0.0,
            created_at="2025-01-01T00:00:00Z",
        )

        mock_workflow.get_execution_status.return_value = mock_state

        # Override authentication dependency
        from ardha.core.security import get_current_active_user
        from ardha.main import app

        app.dependency_overrides[get_current_active_user] = lambda: mock_user

        try:
            with patch(
                "ardha.api.v1.routes.task_generation.get_task_generation_workflow",
                return_value=mock_workflow,
            ):
                # Make streaming request
                response = client.get(f"/api/v1/task-generation/{execution_id}/progress")
        finally:
            # Clear override
            app.dependency_overrides.clear()

        assert response.status_code == 200
        assert response.headers["content-type"] == "text/event-stream; charset=utf-8"
        assert "cache-control" in response.headers
        assert "connection" in response.headers

        # Check streaming content
        content = response.content.decode()
        assert "data: " in content
        assert "type" in content
        assert "execution_id" in content
        assert "status" in content

    def test_progress_stream_not_found(self, client, mock_user, mock_workflow):
        """Test progress streaming for non-existent execution."""
        execution_id = uuid4()
        mock_workflow.get_execution_status.return_value = None

        with patch(
            "ardha.api.v1.routes.task_generation.get_current_active_user", return_value=mock_user
        ):
            with patch(
                "ardha.api.v1.routes.task_generation.get_task_generation_workflow",
                return_value=mock_workflow,
            ):
                response = client.get(f"/api/v1/task-generation/{execution_id}/progress")

        assert response.status_code == 404
        data = response.json()
        assert "not found" in data["detail"].lower()

    def test_progress_stream_access_denied(self, client, mock_workflow):
        """Test progress streaming with access denied."""
        execution_id = uuid4()
        other_user_id = uuid4()

        # Mock state belonging to different user
        mock_state = TaskGenerationState(
            workflow_id=uuid4(),
            execution_id=execution_id,
            workflow_type=WorkflowType.CUSTOM,
            user_id=other_user_id,  # Different user
            initial_request="Generate tasks and OpenSpec from PRD",
            prd_content="Test PRD",
            status="running",
        )

        mock_workflow.get_execution_status.return_value = mock_state

        # Mock current user
        current_user = MagicMock()
        current_user.id = uuid4()

        with patch(
            "ardha.api.v1.routes.task_generation.get_current_active_user", return_value=current_user
        ):
            with patch(
                "ardha.api.v1.routes.task_generation.get_task_generation_workflow",
                return_value=mock_workflow,
            ):
                response = client.get(f"/api/v1/task-generation/{execution_id}/progress")

        assert response.status_code == 403
        data = response.json()
        assert "access denied" in data["detail"].lower()


class TestTaskGenerationWorkflowIntegration:
    """End-to-end integration tests for Task Generation workflow."""

    @pytest.mark.asyncio
    async def test_complete_workflow_execution(self):
        """Test complete workflow execution from start to finish."""
        # Create workflow
        config = TaskGenerationWorkflowConfig(openspec_template_path=None)
        workflow = TaskGenerationWorkflow(config)

        # Mock AI responses for all nodes
        mock_ai_responses = {
            "analyze_prd": """{
                "core_features": [{"name": "User Authentication", "priority": "high"}],
                "technical_requirements": [{"type": "Security", "complexity": "medium"}],
                "user_stories": [{"as_a": "user", "i_want": "login"}],
                "project_scope": {"in_scope": ["Auth"]},
                "risk_factors": [{"risk": "Security breach", "impact": "high"}],
                "dependencies": [{"type": "External", "description": "Email service"}],
                "complexity_assessment": {"overall": "medium"}
            }""",
            "breakdown_tasks": """{
                "epics": [
                    {
                        "id": "epic_001",
                        "title": "User Authentication",
                        "main_tasks": [
                            {
                                "id": "task_001",
                                "title": "Implement Login API",
                                "acceptance_criteria": ["Valid credentials"],
                                "complexity": "medium",
                                "priority": "high",
                                "estimated_hours": 8,
                                "dependencies": [],
                                "subtasks": []
                            }
                        ]
                    }
                ],
                "task_statistics": {"total_tasks": 1, "total_epics": 1}
            }""",
            "define_dependencies": """{
                "dependencies": [
                    {"task_id": "task_001", "depends_on": [], "dependency_type": "none"}
                ],
                "dependency_graph": {"nodes": ["task_001"], "edges": []},
                "dependency_analysis": {"total_dependencies": 0, "circular_dependencies": 0}
            }""",
            "estimate_effort": """{
                "task_estimates": [{"task_id": "task_001", "base_hours": 8, "adjusted_hours": 10}],
                "project_summary": {"total_hours": 10, "total_cost": 500},
                "resource_allocation": {"required_roles": ["Backend Developer"]},
                "timeline_optimization": {"parallel_opportunities": []},
                "cost_breakdown": {"development": 400, "testing": 100}
            }""",
            "generate_openspec": """{
                "proposal": {
                    "id": "task-gen-12345678",
                    "title": "User Authentication System",
                    "objectives": ["Implement secure authentication"],
                    "scope": {"in_scope": ["Login"], "out_of_scope": ["Social login"]},
                    "success_criteria": ["Users can login securely"]
                },
                "files": {
                    "proposal.md": "# User Authentication System\\n\\n## Overview",
                    "tasks.md": "# Tasks\\n\\n## Epic 1: Authentication\\n- [ ] Login API",
                    "spec-delta.md": "# Specification Changes\\n\\n## New Endpoints",
                    "README.md": "# Authentication System\\n\\n## Setup",
                    "risk-assessment.md": "# Risk Assessment\\n\\n## Security Risks"
                },
                "metadata": {"generated_at": "2025-01-01T00:00:00Z"}
            }""",
        }

        # Mock all node calls
        with patch.object(workflow.nodes["analyze_prd"], "_call_ai") as mock_analyze:
            with patch.object(workflow.nodes["breakdown_tasks"], "_call_ai") as mock_breakdown:
                with patch.object(workflow.nodes["define_dependencies"], "_call_ai") as mock_deps:
                    with patch.object(workflow.nodes["estimate_effort"], "_call_ai") as mock_effort:
                        with patch.object(
                            workflow.nodes["generate_openspec"], "_call_ai"
                        ) as mock_openspec:

                            # Set up mock responses
                            mock_analyze.return_value = mock_ai_responses["analyze_prd"]
                            mock_breakdown.return_value = mock_ai_responses["breakdown_tasks"]
                            mock_deps.return_value = mock_ai_responses["define_dependencies"]
                            mock_effort.return_value = mock_ai_responses["estimate_effort"]
                            mock_openspec.return_value = mock_ai_responses["generate_openspec"]

                            # Mock other methods
                            with patch.object(
                                workflow.nodes["analyze_prd"],
                                "_get_relevant_context",
                                return_value=[],
                            ):
                                with patch.object(workflow.nodes["analyze_prd"], "_store_memory"):
                                    with patch.object(
                                        workflow.nodes["breakdown_tasks"],
                                        "_get_relevant_context",
                                        return_value=[],
                                    ):
                                        with patch.object(
                                            workflow.nodes["breakdown_tasks"], "_store_memory"
                                        ):
                                            with patch.object(
                                                workflow.nodes["define_dependencies"],
                                                "_get_relevant_context",
                                                return_value=[],
                                            ):
                                                with patch.object(
                                                    workflow.nodes["define_dependencies"],
                                                    "_store_memory",
                                                ):
                                                    with patch.object(
                                                        workflow.nodes["estimate_effort"],
                                                        "_get_relevant_context",
                                                        return_value=[],
                                                    ):
                                                        with patch.object(
                                                            workflow.nodes["estimate_effort"],
                                                            "_store_memory",
                                                        ):
                                                            with patch.object(
                                                                workflow.nodes["generate_openspec"],
                                                                "_get_relevant_context",
                                                                return_value=[],
                                                            ):
                                                                with patch.object(
                                                                    workflow.nodes[
                                                                        "generate_openspec"
                                                                    ],
                                                                    "_store_memory",
                                                                ):
                                                                    with patch.object(
                                                                        workflow,
                                                                        "_get_workflow_context",
                                                                    ):

                                                                        # Execute workflow
                                                                        result = await workflow.execute(
                                                                            prd_content="Test PRD for user authentication system",
                                                                            user_id=uuid4(),
                                                                            project_id=uuid4(),
                                                                            project_context={
                                                                                "tech_stack": "Python"
                                                                            },
                                                                            existing_tasks=[],
                                                                            parameters={},
                                                                        )

        # Verify results
        assert result.status.value == "completed"
        assert result.prd_analysis is not None
        assert result.task_breakdown is not None
        assert result.task_dependencies is not None
        assert result.effort_estimates is not None
        assert result.openspec_proposal is not None
        assert result.calculate_task_quality_score() > 0.5

        # Verify specific content
        assert result.prd_analysis["core_features"][0]["name"] == "User Authentication"
        assert len(result.task_breakdown) == 2  # 1 epic + 1 main task
        # Check for both epic and main task (order may vary)
        task_titles = [task["title"] for task in result.task_breakdown]
        assert "User Authentication" in task_titles  # Epic
        assert "Implement Login API" in task_titles  # Main task
        assert result.effort_estimates["project_summary"]["total_hours"] == 10
        assert result.openspec_proposal["proposal"]["title"] == "User Authentication System"
        assert len(result.openspec_proposal["files"]) == 5  # All required files


if __name__ == "__main__":
    pytest.main([__file__])
