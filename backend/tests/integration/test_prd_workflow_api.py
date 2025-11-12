"""
Integration tests for PRD workflow API endpoints.

This module tests the PRD workflow API endpoints to ensure
they work correctly with real database and service interactions.
"""

import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4
from fastapi.testclient import TestClient

from ardha.main import app
from ardha.workflows.prd_workflow import PRDWorkflow, get_prd_workflow
from ardha.schemas.workflows.prd import PRDWorkflowConfig, PRDState
from ardha.workflows.state import WorkflowStatus, WorkflowType


@pytest.fixture
def client():
    """Create test client."""
    return TestClient(app)


@pytest.fixture
def mock_user_session():
    """Create mock authenticated user session."""
    return {
        "user_id": uuid4(),
        "email": "test@example.com",
        "is_active": True
    }


@pytest.fixture
def sample_research_summary():
    """Sample research summary for testing."""
    return {
        "idea": "A collaborative markdown editor with real-time collaboration",
        "idea_analysis": {
            "core_concept": "Real-time collaborative markdown editing",
            "value_proposition": "Seamless collaboration for technical content",
            "target_users": ["Developers", "Technical writers", "Content creators"]
        },
        "market_research": {
            "market_size": "$2.5B market for collaborative tools",
            "growth_rate": "15% annually",
            "target_audience": "Developers, writers, content creators",
            "competitors": ["Notion", "Google Docs", "HackMD"],
            "market_opportunity": "Developer-focused collaborative tools"
        },
        "competitive_analysis": {
            "direct_competitors": ["Notion", "Google Docs"],
            "indirect_competitors": ["HackMD", "Typora"],
            "competitive_advantages": ["Better performance", "Developer-focused features"],
            "market_positioning": "Premium collaborative tool for technical teams"
        },
        "technical_feasibility": {
            "complexity": "Medium",
            "technologies": ["WebSocket", "CRDT", "React", "Node.js"],
            "challenges": ["Real-time synchronization", "Conflict resolution"],
            "feasibility_score": 0.8,
            "technical_risks": ["Scalability", "Data consistency"]
        },
        "research_summary": {
            "overall_confidence": 0.85,
            "sources_found": 25,
            "key_insights": [
                "Strong market demand for developer-focused tools",
                "Real-time collaboration is a key differentiator",
                "Performance and reliability are critical success factors"
            ]
        }
    }


@pytest.fixture
def mock_prd_workflow():
    """Create mock PRD workflow."""
    workflow = MagicMock(spec=PRDWorkflow)
    workflow.execute = AsyncMock()
    workflow.get_execution_status = AsyncMock()
    workflow.cancel_execution = AsyncMock()
    return workflow


class TestPRDWorkflowAPI:
    """Test PRD workflow API endpoints."""
    
    @pytest.mark.asyncio
    async def test_start_prd_workflow_success(self, client, mock_user_session, sample_research_summary, mock_prd_workflow):
        """Test successful PRD workflow start."""
        # Mock workflow execution
        expected_state = PRDState(
            workflow_id=uuid4(),
            execution_id=uuid4(),
            workflow_type=WorkflowType.CUSTOM,
            user_id=mock_user_session["user_id"],
            project_id=uuid4(),
            initial_request="Generate PRD from research",
            research_summary=sample_research_summary,
            status=WorkflowStatus.RUNNING,
            final_prd="# Product Requirements Document\n\nGenerated PRD content...",
            requirements_completeness=0.9,
            feature_prioritization_quality=0.85,
            metrics_specificity=0.8,
            document_coherence=0.95,
        )
        
        mock_prd_workflow.execute.return_value = expected_state
        
        # Mock the workflow factory
        with patch('ardha.workflows.prd_workflow.get_prd_workflow', return_value=mock_prd_workflow):
            # Make request
            response = client.post(
                "/api/v1/workflows/prd/start",
                json={
                    "research_summary": sample_research_summary,
                    "project_id": str(uuid4()),
                    "parameters": {
                        "enable_human_approval": False,
                        "include_technical_architecture": True
                    }
                },
                headers={"Authorization": f"Bearer {mock_user_session['user_id']}"}
            )
        
        # Verify response
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert "workflow_id" in data
        assert "execution_id" in data
        assert data["workflow_type"] == "prd"
        
        # Verify workflow was called correctly
        mock_prd_workflow.execute.assert_called_once()
        call_args = mock_prd_workflow.execute.call_args
        assert call_args[1]["research_summary"] == sample_research_summary
        assert call_args[1]["user_id"] == mock_user_session["user_id"]
    
    @pytest.mark.asyncio
    async def test_start_prd_workflow_invalid_input(self, client, mock_user_session):
        """Test PRD workflow start with invalid input."""
        # Make request with missing research_summary
        response = client.post(
            "/api/v1/workflows/prd/start",
            json={
                "project_id": str(uuid4())
            },
            headers={"Authorization": f"Bearer {mock_user_session['user_id']}"}
        )
        
        # Verify error response
        assert response.status_code == 422
        data = response.json()
        assert "detail" in data
    
    @pytest.mark.asyncio
    async def test_get_prd_workflow_status(self, client, mock_user_session, mock_prd_workflow):
        """Test getting PRD workflow status."""
        execution_id = uuid4()
        
        # Mock workflow state
        mock_state = PRDState(
            workflow_id=uuid4(),
            execution_id=execution_id,
            workflow_type=WorkflowType.CUSTOM,
            user_id=mock_user_session["user_id"],
            initial_request="Generate PRD from research",
            research_summary={},
            status=WorkflowStatus.RUNNING,
            current_prd_step="generate_prd",
            prd_progress_percentage=60,
            requirements_completeness=0.9,
            feature_prioritization_quality=0.85,
            metrics_specificity=0.8,
            document_coherence=0.0,
        )
        
        mock_prd_workflow.get_execution_status.return_value = mock_state
        
        with patch('ardha.workflows.prd_workflow.get_prd_workflow', return_value=mock_prd_workflow):
            # Make request
            response = client.get(
                f"/api/v1/workflows/prd/{execution_id}/status",
                headers={"Authorization": f"Bearer {mock_user_session['user_id']}"}
            )
        
        # Verify response
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert data["workflow_status"] == "running"
        assert data["current_step"] == "generate_prd"
        assert data["progress_percentage"] == 60
        assert data["quality_metrics"]["requirements_completeness"] == 0.9
        assert data["quality_metrics"]["feature_prioritization_quality"] == 0.85
        assert data["quality_metrics"]["metrics_specificity"] == 0.8
    
    @pytest.mark.asyncio
    async def test_get_prd_workflow_not_found(self, client, mock_user_session, mock_prd_workflow):
        """Test getting status for non-existent workflow."""
        execution_id = uuid4()
        
        mock_prd_workflow.get_execution_status.return_value = None
        
        with patch('ardha.workflows.prd_workflow.get_prd_workflow', return_value=mock_prd_workflow):
            # Make request
            response = client.get(
                f"/api/v1/workflows/prd/{execution_id}/status",
                headers={"Authorization": f"Bearer {mock_user_session['user_id']}"}
            )
        
        # Verify error response
        assert response.status_code == 404
        data = response.json()
        assert data["status"] == "error"
        assert "not found" in data["message"].lower()
    
    @pytest.mark.asyncio
    async def test_cancel_prd_workflow(self, client, mock_user_session, mock_prd_workflow):
        """Test cancelling PRD workflow."""
        execution_id = uuid4()
        
        mock_prd_workflow.cancel_execution.return_value = True
        
        with patch('ardha.workflows.prd_workflow.get_prd_workflow', return_value=mock_prd_workflow):
            # Make request
            response = client.post(
                f"/api/v1/workflows/prd/{execution_id}/cancel",
                json={"reason": "User requested cancellation"},
                headers={"Authorization": f"Bearer {mock_user_session['user_id']}"}
            )
        
        # Verify response
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert data["message"] == "PRD workflow cancelled successfully"
        
        # Verify workflow was called correctly
        mock_prd_workflow.cancel_execution.assert_called_once_with(
            execution_id, 
            reason="User requested cancellation"
        )
    
    @pytest.mark.asyncio
    async def test_get_prd_workflow_result(self, client, mock_user_session, mock_prd_workflow):
        """Test getting completed PRD workflow result."""
        execution_id = uuid4()
        
        # Mock completed workflow state
        mock_state = PRDState(
            workflow_id=uuid4(),
            execution_id=execution_id,
            workflow_type=WorkflowType.CUSTOM,
            user_id=mock_user_session["user_id"],
            initial_request="Generate PRD from research",
            research_summary={},
            status=WorkflowStatus.COMPLETED,
            final_prd="# Product Requirements Document: Collaborative Markdown Editor\n\n## Executive Summary\n\nThis document outlines...",
            requirements={
                "functional_requirements": [
                    {"id": "REQ-F-001", "description": "Real-time collaborative editing"}
                ]
            },
            features={
                "features": [
                    {"id": "FEAT-001", "name": "Real-time Editor", "priority": "M"}
                ]
            },
            success_metrics={
                "success_metrics": {
                    "user_engagement": [
                        {"name": "DAU", "description": "Daily active users"}
                    ]
                }
            },
            requirements_completeness=0.9,
            feature_prioritization_quality=0.85,
            metrics_specificity=0.8,
            document_coherence=0.95,
            version="1.0.0",
            completed_at="2025-01-15T10:30:00Z",
        )
        
        mock_prd_workflow.get_execution_status.return_value = mock_state
        
        with patch('ardha.workflows.prd_workflow.get_prd_workflow', return_value=mock_prd_workflow):
            # Make request
            response = client.get(
                f"/api/v1/workflows/prd/{execution_id}/result",
                headers={"Authorization": f"Bearer {mock_user_session['user_id']}"}
            )
        
        # Verify response
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert data["workflow_status"] == "completed"
        assert "final_prd" in data
        assert len(data["final_prd"]) > 1000  # Substantial document
        assert "requirements" in data
        assert "features" in data
        assert "success_metrics" in data
        assert data["version"] == "1.0.0"
        assert data["quality_metrics"]["overall_quality"] > 0.8
    
    @pytest.mark.asyncio
    async def test_get_prd_workflow_result_not_completed(self, client, mock_user_session, mock_prd_workflow):
        """Test getting result for workflow that hasn't completed."""
        execution_id = uuid4()
        
        # Mock running workflow state
        mock_state = PRDState(
            workflow_id=uuid4(),
            execution_id=execution_id,
            workflow_type=WorkflowType.CUSTOM,
            user_id=mock_user_session["user_id"],
            initial_request="Generate PRD from research",
            research_summary={},
            status=WorkflowStatus.RUNNING,
            final_prd=None,
        )
        
        mock_prd_workflow.get_execution_status.return_value = mock_state
        
        with patch('ardha.workflows.prd_workflow.get_prd_workflow', return_value=mock_prd_workflow):
            # Make request
            response = client.get(
                f"/api/v1/workflows/prd/{execution_id}/result",
                headers={"Authorization": f"Bearer {mock_user_session['user_id']}"}
            )
        
        # Verify error response
        assert response.status_code == 400
        data = response.json()
        assert data["status"] == "error"
        assert "not completed" in data["message"].lower()
    
    @pytest.mark.asyncio
    async def test_list_prd_workflows(self, client, mock_user_session, mock_prd_workflow):
        """Test listing user's PRD workflows."""
        # Mock active executions
        execution_id1 = uuid4()
        execution_id2 = uuid4()
        
        mock_prd_workflow.active_executions = {
            execution_id1: PRDState(
                workflow_id=uuid4(),
                execution_id=execution_id1,
                workflow_type=WorkflowType.CUSTOM,
                user_id=mock_user_session["user_id"],
                initial_request="Generate PRD from research",
                research_summary={},
                status=WorkflowStatus.COMPLETED,
                created_at="2025-01-15T09:00:00Z",
                completed_at="2025-01-15T10:30:00Z",
            ),
            execution_id2: PRDState(
                workflow_id=uuid4(),
                execution_id=execution_id2,
                workflow_type=WorkflowType.CUSTOM,
                user_id=mock_user_session["user_id"],
                initial_request="Generate another PRD",
                research_summary={},
                status=WorkflowStatus.RUNNING,
                created_at="2025-01-15T11:00:00Z",
            ),
        }
        
        with patch('ardha.workflows.prd_workflow.get_prd_workflow', return_value=mock_prd_workflow):
            # Make request
            response = client.get(
                "/api/v1/workflows/prd/list",
                headers={"Authorization": f"Bearer {mock_user_session['user_id']}"}
            )
        
        # Verify response
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert "workflows" in data
        assert len(data["workflows"]) == 2
        
        # Verify workflow data
        workflows = data["workflows"]
        completed_workflow = next(w for w in workflows if w["execution_id"] == str(execution_id1))
        running_workflow = next(w for w in workflows if w["execution_id"] == str(execution_id2))
        
        assert completed_workflow["status"] == "completed"
        assert running_workflow["status"] == "running"
        assert "created_at" in completed_workflow
        assert "created_at" in running_workflow
    
    @pytest.mark.asyncio
    async def test_prd_workflow_error_handling(self, client, mock_user_session, mock_prd_workflow):
        """Test PRD workflow error handling."""
        from ardha.workflows.nodes.prd_nodes import PRDNodeException
        
        # Mock workflow execution failure
        mock_prd_workflow.execute.side_effect = PRDNodeException("AI service unavailable")
        
        with patch('ardha.workflows.prd_workflow.get_prd_workflow', return_value=mock_prd_workflow):
            # Make request
            response = client.post(
                "/api/v1/workflows/prd/start",
                json={
                    "research_summary": {"idea": "Test idea"},
                    "project_id": str(uuid4())
                },
                headers={"Authorization": f"Bearer {mock_user_session['user_id']}"}
            )
        
        # Verify error response
        assert response.status_code == 500
        data = response.json()
        assert data["status"] == "error"
        assert "AI service unavailable" in data["message"]
    
    @pytest.mark.asyncio
    async def test_prd_workflow_with_custom_config(self, client, mock_user_session, sample_research_summary, mock_prd_workflow):
        """Test PRD workflow with custom configuration."""
        expected_state = PRDState(
            workflow_id=uuid4(),
            execution_id=uuid4(),
            workflow_type=WorkflowType.CUSTOM,
            user_id=mock_user_session["user_id"],
            project_id=uuid4(),
            initial_request="Generate PRD from research",
            research_summary=sample_research_summary,
            status=WorkflowStatus.RUNNING,
        )
        
        mock_prd_workflow.execute.return_value = expected_state
        
        # Custom configuration
        custom_config = {
            "extract_requirements_model": "anthropic/claude-opus-4.1",
            "generate_prd_model": "anthropic/claude-sonnet-4.5",
            "enable_human_approval": True,
            "auto_approve_confidence_threshold": 0.95,
            "include_technical_architecture": True,
            "include_timeline_milestones": True,
            "max_retries_per_step": 5,
        }
        
        with patch('ardha.workflows.prd_workflow.get_prd_workflow', return_value=mock_prd_workflow):
            # Make request with custom config
            response = client.post(
                "/api/v1/workflows/prd/start",
                json={
                    "research_summary": sample_research_summary,
                    "project_id": str(uuid4()),
                    "config": custom_config
                },
                headers={"Authorization": f"Bearer {mock_user_session['user_id']}"}
            )
        
        # Verify response
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        
        # Verify workflow was called with custom config
        mock_prd_workflow.execute.assert_called_once()
        call_args = mock_prd_workflow.execute.call_args
        assert "parameters" in call_args[1]
        assert call_args[1]["parameters"]["config"] == custom_config


class TestPRDWorkflowStreaming:
    """Test PRD workflow streaming endpoints."""
    
    @pytest.mark.asyncio
    async def test_prd_workflow_progress_streaming(self, client, mock_user_session, mock_prd_workflow):
        """Test PRD workflow progress streaming via Server-Sent Events."""
        execution_id = uuid4()
        
        # Mock workflow state
        mock_state = PRDState(
            workflow_id=uuid4(),
            execution_id=execution_id,
            workflow_type=WorkflowType.CUSTOM,
            user_id=mock_user_session["user_id"],
            initial_request="Generate PRD from research",
            research_summary={},
            status=WorkflowStatus.RUNNING,
            current_prd_step="generate_prd",
            prd_progress_percentage=60,
        )
        
        mock_prd_workflow.get_execution_status.return_value = mock_state
        
        with patch('ardha.workflows.prd_workflow.get_prd_workflow', return_value=mock_prd_workflow):
            # Make streaming request
            with client.stream(
                "GET", 
                f"/api/v1/workflows/prd/{execution_id}/progress",
                headers={"Authorization": f"Bearer {mock_user_session['user_id']}"}
            ) as response:
                # Verify response headers for SSE
                assert response.status_code == 200
                assert "text/event-stream" in response.headers["content-type"]
                
                # Collect events
                events = []
                for line in response.iter_lines():
                    if line.startswith(b"data: "):
                        event_data = line[6:].decode('utf-8')
                        if event_data.strip():  # Skip empty events
                            events.append(json.loads(event_data))
                
                # Verify events structure
                assert len(events) > 0
                for event in events:
                    assert "type" in event
                    assert "data" in event
                    assert "timestamp" in event
                    
                    if event["type"] == "progress":
                        assert "current_step" in event["data"]
                        assert "progress_percentage" in event["data"]
                        assert "workflow_status" in event["data"]