"""
Workflow test fixtures for unit and integration tests.

This module provides comprehensive fixtures for testing LangGraph
workflows including mocked AI responses, sample inputs, and test data.
"""

from datetime import datetime, timezone
from typing import Optional
from unittest.mock import AsyncMock, MagicMock
from uuid import UUID, uuid4

import pytest

from ardha.models.workflow_execution import WorkflowExecution
from ardha.schemas.workflows.research import ResearchState
from ardha.workflows.state import WorkflowContext, WorkflowStatus, WorkflowType

# =============================================================================
# Mock OpenRouter Responses
# =============================================================================


@pytest.fixture
def mock_openrouter_idea_analysis():
    """Mock OpenRouter response for idea analysis."""
    return {
        "content": """# Idea Analysis

**Core Concept**: Real-time collaborative markdown editor
**Value Proposition**: Enable teams to write documentation together seamlessly
**Target Market**: Development teams, technical writers, remote teams

**Key Requirements**:
- Real-time synchronization
- Markdown rendering
- Conflict resolution
- Version history
- User presence indicators

**Preliminary Feasibility**: High - established technology stack available
**Confidence Score**: 0.85
""",
        "confidence_score": 0.85,
        "model_used": "anthropic/claude-sonnet-4.5",
        "tokens_input": 150,
        "tokens_output": 200,
        "cost": 0.015,
    }


@pytest.fixture
def mock_openrouter_market_research():
    """Mock OpenRouter response for market research."""
    return {
        "content": """# Market Research

**Market Size**: $2.5B collaborative tools market (growing 15% YoY)
**Target Segments**:
- Software development teams (40%)
- Technical documentation teams (30%)
- Academic institutions (20%)
- Enterprise knowledge bases (10%)

**Key Trends**:
- Remote work acceleration
- API-first platforms
- Real-time collaboration demand
- Markdown adoption in technical teams

**Market Opportunity**: High demand, moderate competition
**Confidence Score**: 0.78
""",
        "confidence_score": 0.78,
        "model_used": "anthropic/claude-sonnet-4.5",
        "tokens_input": 200,
        "tokens_output": 300,
        "cost": 0.025,
    }


@pytest.fixture
def mock_openrouter_competitive_analysis():
    """Mock OpenRouter response for competitive analysis."""
    return {
        "content": """# Competitive Analysis

**Direct Competitors**:
1. **Notion** - Block-based, limited markdown, strong brand ($10B valuation)
2. **HackMD** - Open source, real-time, limited features
3. **Google Docs** - Market leader, weak markdown support
4. **Obsidian** - Local-first, limited collaboration

**Competitive Advantages**:
- Native markdown (vs Notion's blocks)
- Real-time sync (vs Obsidian's local-first)
- Developer-focused (vs Google Docs' general audience)
- API-first architecture

**Market Gaps**:
- Developer-native collaborative markdown
- Strong version control integration
- Programmable via API

**Confidence Score**: 0.82
""",
        "confidence_score": 0.82,
        "model_used": "anthropic/claude-sonnet-4.5",
        "tokens_input": 250,
        "tokens_output": 350,
        "cost": 0.030,
    }


@pytest.fixture
def mock_openrouter_technical_feasibility():
    """Mock OpenRouter response for technical feasibility."""
    return {
        "content": """# Technical Feasibility

**Tech Stack Recommendation**:
- **Frontend**: React + CodeMirror 6 (markdown editing)
- **Backend**: Node.js + WebSocket (real-time sync)
- **Sync Engine**: CRDT (Yjs or Automerge)
- **Database**: PostgreSQL + Redis
- **Storage**: S3-compatible object storage

**Implementation Complexity**: Medium-High
**Estimated Timeline**: 4-6 months for MVP
**Team Requirements**: 2-3 full-stack developers

**Technical Risks**:
- CRDT conflict resolution complexity
- WebSocket scaling challenges
- Real-time performance optimization

**Mitigation Strategies**:
- Use proven CRDT libraries (Yjs)
- Implement WebSocket clustering early
- Performance testing from MVP stage

**Confidence Score**: 0.88
""",
        "confidence_score": 0.88,
        "model_used": "anthropic/claude-sonnet-4.5",
        "tokens_input": 300,
        "tokens_output": 400,
        "cost": 0.035,
    }


@pytest.fixture
def mock_openrouter_research_synthesis():
    """Mock OpenRouter response for research synthesis."""
    return {
        "content": """# Research Summary: Real-time Collaborative Markdown Editor

## Executive Summary
Strong market opportunity for developer-focused collaborative markdown editor with real-time sync capabilities. Target $2.5B market with 15% YoY growth.

## Key Findings
1. **Market Validation**: High demand from dev teams, technical writers
2. **Competitive Landscape**: Room for differentiation via markdown-native approach
3. **Technical Feasibility**: Proven tech stack available, medium complexity
4. **Go-to-Market**: API-first, developer community focus

## Recommendations
- **Build MVP**: 4-6 month timeline with 2-3 developers
- **Differentiation**: Focus on developer experience and API
- **Monetization**: Freemium model with team/enterprise tiers
- **Initial Target**: Developer teams at tech companies (40% of market)

## Risk Assessment
- Medium technical risk (CRDT complexity)
- Low market risk (validated demand)
- Medium competitive risk (established players exist)

## Next Steps
1. Create detailed PRD
2. Prototype CRDT sync engine
3. Design API specification
4. Plan MVP feature set

**Overall Confidence**: 0.83
""",
        "confidence_score": 0.83,
        "model_used": "anthropic/claude-sonnet-4.5",
        "tokens_input": 400,
        "tokens_output": 500,
        "cost": 0.040,
    }


@pytest.fixture
def mock_openrouter_streaming_chunks():
    """Mock streaming chunks for SSE testing."""
    return [
        {"type": "chunk", "content": "# Idea", "delta": "# Idea"},
        {"type": "chunk", "content": " Analysis\n", "delta": " Analysis\n"},
        {"type": "chunk", "content": "\n**Core", "delta": "\n**Core"},
        {"type": "chunk", "content": " Concept**:", "delta": " Concept**:"},
        {
            "type": "done",
            "content": "# Idea Analysis\n\n**Core Concept**: ...",
            "total_tokens": 150,
        },
    ]


@pytest.fixture
def mock_openrouter_error_response():
    """Mock OpenRouter error for error handling tests."""
    from ardha.core.openrouter import OpenRouterError

    return OpenRouterError(
        message="API rate limit exceeded", error_type="rate_limit_error", code="429"
    )


# =============================================================================
# Sample Workflow Inputs
# =============================================================================


@pytest.fixture
def sample_research_input():
    """Sample input for research workflow."""
    return {
        "idea": "A real-time collaborative markdown editor for development teams",
        "context": {
            "target_audience": "Software developers and technical writers",
            "problem": "Existing tools are too complex or lack markdown support",
            "goals": [
                "Real-time collaboration",
                "Native markdown support",
                "Developer-friendly features",
            ],
        },
        "parameters": {
            "depth": "comprehensive",
            "focus_areas": ["market", "technical", "competitive"],
        },
    }


@pytest.fixture
def sample_prd_input():
    """Sample input for PRD workflow."""
    return {
        "research_summary": """Market validated idea with strong technical feasibility.
Target: development teams and technical writers.
Tech stack: React + Node.js + CRDT sync engine.
MVP timeline: 4-6 months.""",
        "context": {
            "project_goals": ["Real-time collaboration", "Markdown native", "API-first"],
            "target_users": ["Developers", "Technical writers"],
            "constraints": ["Must be self-hostable", "Open source core"],
        },
    }


@pytest.fixture
def sample_task_input():
    """Sample input for task generation workflow."""
    return {
        "prd_content": """# Product Requirements Document

## Overview
Build a real-time collaborative markdown editor.

## Features
1. Real-time sync using CRDT
2. Markdown rendering with CodeMirror 6
3. User presence and cursors
4. Version history
5. API for programmatic access

## Technical Requirements
- React frontend
- Node.js backend
- PostgreSQL database
- Redis for real-time
- WebSocket connections
""",
        "context": {"project_id": str(uuid4()), "team_size": 3, "timeline": "6 months"},
    }


# =============================================================================
# Sample Workflow States
# =============================================================================


@pytest.fixture
def sample_research_state(sample_research_input):
    """Sample ResearchState for testing."""
    workflow_id = uuid4()
    execution_id = uuid4()
    user_id = uuid4()

    return ResearchState(
        workflow_id=workflow_id,
        execution_id=execution_id,
        workflow_type=WorkflowType.RESEARCH,
        user_id=user_id,
        project_id=None,
        initial_request=sample_research_input["idea"],
        idea=sample_research_input["idea"],
        context=sample_research_input["context"],
        parameters=sample_research_input["parameters"],
        status=WorkflowStatus.PENDING,
        created_at=datetime.now(timezone.utc).isoformat(),
        current_step="analyze_idea",
        progress_percentage=0,
        completed_nodes=[],
        failed_nodes=[],
        retry_count=0,
        errors=[],
        metadata={},
        # Research-specific fields
        idea_analysis=None,
        market_research=None,
        competitive_analysis=None,
        technical_feasibility=None,
        research_summary=None,
        research_confidence=0.0,
        sources_found=0,
        hypotheses_generated=0,
        analysis_depth_score=0.0,
        market_data_quality=0.0,
        competitor_coverage=0.0,
        technical_detail_level=0.0,
    )


@pytest.fixture
def completed_research_state(
    sample_research_state,
    mock_openrouter_idea_analysis,
    mock_openrouter_market_research,
    mock_openrouter_competitive_analysis,
    mock_openrouter_technical_feasibility,
    mock_openrouter_research_synthesis,
):
    """Sample completed ResearchState for testing."""
    state = sample_research_state

    # Mark as completed with all results
    state.status = WorkflowStatus.COMPLETED
    state.current_step = "completed"
    state.progress_percentage = 100
    state.completed_nodes = [
        "analyze_idea",
        "market_research",
        "competitive_analysis",
        "technical_feasibility",
        "synthesize",
    ]

    # Add research results
    state.idea_analysis = mock_openrouter_idea_analysis
    state.market_research = mock_openrouter_market_research
    state.competitive_analysis = mock_openrouter_competitive_analysis
    state.technical_feasibility = mock_openrouter_technical_feasibility
    state.research_summary = mock_openrouter_research_synthesis

    # Set quality metrics
    state.analysis_depth_score = 0.85
    state.market_data_quality = 0.78
    state.competitor_coverage = 0.82
    state.technical_detail_level = 0.88
    state.research_confidence = 0.83
    state.sources_found = 15
    state.hypotheses_generated = 8

    # Set timestamps
    state.started_at = datetime.now(timezone.utc).isoformat()
    state.completed_at = datetime.now(timezone.utc).isoformat()

    return state


@pytest.fixture
def failed_research_state(sample_research_state):
    """Sample failed ResearchState for testing."""
    state = sample_research_state

    state.status = WorkflowStatus.FAILED
    state.current_step = "error"
    state.failed_nodes = ["market_research"]
    state.errors = [
        {
            "node": "market_research",
            "error": "API rate limit exceeded",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    ]
    state.retry_count = 3

    return state


# =============================================================================
# Workflow Execution Database Models
# =============================================================================


@pytest.fixture
def sample_workflow_execution(sample_research_input):
    """Sample WorkflowExecution model for testing."""
    execution = WorkflowExecution()
    execution.id = uuid4()
    execution.user_id = uuid4()
    execution.project_id = None
    execution.workflow_type = WorkflowType.RESEARCH.value
    execution.status = WorkflowStatus.RUNNING
    execution.input_data = {
        "initial_request": sample_research_input["idea"],
        "parameters": sample_research_input["parameters"],
        "context": sample_research_input["context"],
    }
    execution.output_data = {}
    execution.total_tokens = 0
    execution.total_cost = 0.0
    execution.checkpoint_data = {}
    execution.error_message = None
    execution.is_deleted = False
    execution.deleted_at = None
    execution.created_at = datetime.now(timezone.utc)
    execution.started_at = datetime.now(timezone.utc)
    execution.completed_at = None
    execution.updated_at = datetime.now(timezone.utc)
    return execution


@pytest.fixture
def completed_workflow_execution(sample_workflow_execution):
    """Sample completed WorkflowExecution for testing."""
    execution = sample_workflow_execution

    execution.status = WorkflowStatus.COMPLETED
    execution.output_data = {
        "results": {
            "research_summary": "Comprehensive research completed",
            "confidence_score": 0.83,
        },
        "artifacts": {
            "idea_analysis": "...",
            "market_research": "...",
            "competitive_analysis": "...",
            "technical_feasibility": "...",
        },
        "metadata": {"nodes_completed": 5, "execution_time_seconds": 120.5},
    }
    execution.total_tokens = 2300
    execution.total_cost = 0.145
    execution.completed_at = datetime.now(timezone.utc)

    return execution


# =============================================================================
# Mock Workflow Components
# =============================================================================


@pytest.fixture
def mock_workflow_context():
    """Mock WorkflowContext for testing."""
    return WorkflowContext(
        db_session=None,
        openrouter_client=AsyncMock(),
        qdrant_service=AsyncMock(),
        settings={},
        progress_callback=AsyncMock(),
        error_callback=AsyncMock(),
        logger=MagicMock(),
    )


@pytest.fixture
def mock_openrouter_client(
    mock_openrouter_idea_analysis,
    mock_openrouter_market_research,
    mock_openrouter_competitive_analysis,
    mock_openrouter_technical_feasibility,
    mock_openrouter_research_synthesis,
):
    """Mock OpenRouterClient with predefined responses."""
    mock_client = AsyncMock()

    # Configure streaming responses for each node
    responses = [
        mock_openrouter_idea_analysis,
        mock_openrouter_market_research,
        mock_openrouter_competitive_analysis,
        mock_openrouter_technical_feasibility,
        mock_openrouter_research_synthesis,
    ]

    # Track call count using list (mutable)
    call_counts = [0]  # [complete_count]

    # Mock the complete method
    async def mock_complete(*args, **kwargs):
        # Return responses in order
        response_idx = call_counts[0] % len(responses)
        call_counts[0] += 1
        return responses[response_idx]

    mock_client.complete = mock_complete

    # Mock the stream method - return async generator
    async def mock_stream(*args, **kwargs):
        # Return streaming chunks fixture
        streaming_chunks = mock_openrouter_streaming_chunks()
        for chunk in streaming_chunks:
            yield chunk

    mock_client.stream = mock_stream

    return mock_client


@pytest.fixture
def mock_qdrant_service():
    """Mock Qdrant service for memory operations."""
    mock_service = AsyncMock()

    mock_service.ingest_workflow_execution = AsyncMock(return_value=True)
    mock_service.search_similar = AsyncMock(return_value=[])
    mock_service.get_collection = AsyncMock(return_value={"vectors_count": 0})

    return mock_service


@pytest.fixture
def mock_progress_callback():
    """Mock progress callback for tracking workflow progress."""
    callback = AsyncMock()

    # Track all progress updates
    callback.updates = []

    async def track_update(progress_update):
        callback.updates.append(progress_update)

    callback.side_effect = track_update

    return callback


# =============================================================================
# Checkpoint Data
# =============================================================================


@pytest.fixture
def workflow_checkpoint_data():
    """Sample checkpoint data for state persistence testing."""
    return {
        "execution_id": str(uuid4()),
        "workflow_type": "research",
        "current_step": "market_research",
        "completed_nodes": ["analyze_idea"],
        "failed_nodes": [],
        "state_snapshot": {"idea_analysis": {"content": "Idea analysis complete"}, "progress": 20},
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


# =============================================================================
# Test Utilities
# =============================================================================


@pytest.fixture
def create_mock_workflow_execution():
    """Factory fixture for creating mock workflow executions."""

    def _create(
        workflow_type: str = "research",
        status: WorkflowStatus = WorkflowStatus.RUNNING,
        user_id: Optional[UUID] = None,
        project_id: Optional[UUID] = None,
    ) -> WorkflowExecution:
        execution = WorkflowExecution()
        execution.id = uuid4()
        execution.user_id = user_id or uuid4()
        execution.project_id = project_id
        execution.workflow_type = workflow_type
        execution.status = status
        execution.input_data = {"initial_request": "Test workflow"}
        execution.output_data = {}
        execution.total_tokens = 0
        execution.total_cost = 0.0
        execution.checkpoint_data = {}
        execution.error_message = None
        execution.is_deleted = False
        execution.deleted_at = None
        execution.created_at = datetime.now(timezone.utc)
        execution.started_at = (
            datetime.now(timezone.utc) if status != WorkflowStatus.PENDING else None
        )
        execution.completed_at = (
            datetime.now(timezone.utc) if status == WorkflowStatus.COMPLETED else None
        )
        execution.updated_at = datetime.now(timezone.utc)
        return execution

    return _create


@pytest.fixture
def assert_workflow_state():
    """Utility fixture for asserting workflow state properties."""

    def _assert(state, expected_status=None, expected_nodes_completed=None, expected_errors=None):
        if expected_status:
            assert (
                state.status == expected_status
            ), f"Expected status {expected_status}, got {state.status}"

        if expected_nodes_completed is not None:
            assert (
                len(state.completed_nodes) == expected_nodes_completed
            ), f"Expected {expected_nodes_completed} completed nodes, got {len(state.completed_nodes)}"

        if expected_errors is not None:
            assert (
                len(state.errors) == expected_errors
            ), f"Expected {expected_errors} errors, got {len(state.errors)}"

    return _assert
