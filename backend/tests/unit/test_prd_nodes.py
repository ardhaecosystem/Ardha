"""
Unit tests for PRD workflow nodes.

This module tests individual PRD workflow nodes to ensure
they function correctly with mocked dependencies.
"""

import json
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from ardha.schemas.workflows.prd import PRDState
from ardha.workflows.nodes.prd_nodes import (
    DefineFeaturesNode,
    ExtractRequirementsNode,
    GeneratePRDNode,
    PRDNodeException,
    ReviewFormatNode,
    SetMetricsNode,
)
from ardha.workflows.state import WorkflowContext, WorkflowStatus


@pytest.fixture
def mock_context():
    """Create mock workflow context."""
    context = MagicMock(spec=WorkflowContext)
    context.openrouter_client = AsyncMock()
    context.qdrant_service = AsyncMock()
    context.settings = {
        "extract_requirements_model": "anthropic/claude-sonnet-4.5",
        "define_features_model": "z-ai/glm-4.6",
        "set_metrics_model": "z-ai/glm-4.6",
        "generate_prd_model": "anthropic/claude-sonnet-4.5",
        "review_format_model": "z-ai/glm-4.6",
    }
    context.get_model = MagicMock()
    return context


@pytest.fixture
def sample_research_summary():
    """Sample research summary for testing."""
    return {
        "idea": "A collaborative markdown editor with real-time collaboration",
        "market_research": {
            "market_size": "$2.5B market for collaborative tools",
            "target_audience": "Developers, writers, content creators",
            "competitors": ["Notion", "Google Docs", "HackMD"],
        },
        "technical_feasibility": {
            "complexity": "Medium",
            "technologies": ["WebSocket", "CRDT", "React", "Node.js"],
            "challenges": ["Real-time synchronization", "Conflict resolution"],
        },
        "competitive_analysis": {
            "strengths": ["Better performance", "Developer-focused"],
            "weaknesses": ["New entrant", "Limited features initially"],
        },
    }


@pytest.fixture
def sample_prd_state(sample_research_summary):
    """Create sample PRD state for testing."""
    from ardha.workflows.state import WorkflowType

    return PRDState(
        workflow_id=uuid4(),
        execution_id=uuid4(),
        workflow_type=WorkflowType.CUSTOM,
        user_id=uuid4(),
        project_id=uuid4(),
        initial_request="Generate PRD from research",
        research_summary=sample_research_summary,
        status=WorkflowStatus.RUNNING,
        current_prd_step="extract_requirements",
        prd_progress_percentage=0,
        completed_nodes=[],
        failed_nodes=[],
        retry_count=0,
        errors=[],
        metadata={},
        requirements=None,
        features=None,
        success_metrics=None,
        prd_content=None,
        final_prd=None,
        version="1.0.0",
        last_updated=None,
        requirements_completeness=0.0,
        feature_prioritization_quality=0.0,
        metrics_specificity=0.0,
        document_coherence=0.0,
        human_approval_points=[],
        human_edits_made=[],
    )


class TestExtractRequirementsNode:
    """Test ExtractRequirementsNode functionality."""

    @pytest.fixture
    def node(self):
        return ExtractRequirementsNode()

    @pytest.mark.asyncio
    async def test_successful_requirements_extraction(self, node, sample_prd_state, mock_context):
        """Test successful requirements extraction."""
        # Mock AI response
        mock_response = json.dumps(
            {
                "functional_requirements": [
                    {
                        "id": "REQ-F-001",
                        "description": "Real-time collaborative editing",
                        "priority": "High",
                        "acceptance_criteria": "Multiple users can edit simultaneously",
                    }
                ],
                "non_functional_requirements": [
                    {
                        "id": "REQ-NF-001",
                        "description": "Sub-100ms latency for edits",
                        "priority": "High",
                        "category": "Performance",
                        "metrics": "<100ms round-trip time",
                    }
                ],
                "business_requirements": [
                    {
                        "id": "REQ-B-001",
                        "description": "Support 1000 concurrent users",
                        "priority": "Medium",
                        "success_criteria": "System handles 1000 users without degradation",
                    }
                ],
                "technical_requirements": [
                    {
                        "id": "REQ-T-001",
                        "description": "WebSocket-based communication",
                        "priority": "High",
                        "constraints": "Must support bidirectional communication",
                    }
                ],
                "requirements_summary": {
                    "total_requirements": 4,
                    "by_priority": {"high": 3, "medium": 1, "low": 0},
                    "by_category": {
                        "functional": 1,
                        "non_functional": 1,
                        "business": 1,
                        "technical": 1,
                    },
                },
            }
        )

        mock_context.openrouter_client.complete.return_value = MagicMock(
            content=mock_response, usage=MagicMock(prompt_tokens=1000, completion_tokens=500)
        )

        mock_context.get_model.return_value = MagicMock(
            calculate_cost=MagicMock(return_value=0.015)
        )

        # Execute node
        result = await node.execute(sample_prd_state, mock_context)

        # Verify result
        assert "requirements" in result
        assert result["total_requirements"] == 4
        assert result["completeness_score"] > 0
        assert result["extraction_confidence"] > 0

        # Verify state was updated
        assert sample_prd_state.requirements_completeness > 0

    @pytest.mark.asyncio
    async def test_invalid_json_response(self, node, sample_prd_state, mock_context):
        """Test handling of invalid JSON response."""
        # Mock invalid JSON response
        mock_context.openrouter_client.complete.return_value = MagicMock(
            content="Invalid JSON response",
            usage=MagicMock(prompt_tokens=1000, completion_tokens=500),
        )

        mock_context.get_model.return_value = MagicMock(
            calculate_cost=MagicMock(return_value=0.015)
        )

        # Should raise PRDNodeException
        with pytest.raises(PRDNodeException, match="Invalid JSON response"):
            await node.execute(sample_prd_state, mock_context)

    @pytest.mark.asyncio
    async def test_missing_required_sections(self, node, sample_prd_state, mock_context):
        """Test handling of missing required sections."""
        # Mock response with missing sections
        mock_response = json.dumps(
            {
                "functional_requirements": [],
                # Missing other required sections
            }
        )

        mock_context.openrouter_client.complete.return_value = MagicMock(
            content=mock_response, usage=MagicMock(prompt_tokens=1000, completion_tokens=500)
        )

        mock_context.get_model.return_value = MagicMock(
            calculate_cost=MagicMock(return_value=0.015)
        )

        # Should raise PRDNodeException
        with pytest.raises(PRDNodeException, match="Missing required section"):
            await node.execute(sample_prd_state, mock_context)


class TestDefineFeaturesNode:
    """Test DefineFeaturesNode functionality."""

    @pytest.fixture
    def node(self):
        return DefineFeaturesNode()

    @pytest.fixture
    def state_with_requirements(self, sample_prd_state):
        """Create state with requirements already extracted."""
        sample_prd_state.requirements = {
            "functional_requirements": [
                {
                    "id": "REQ-F-001",
                    "description": "Real-time collaborative editing",
                    "priority": "High",
                    "acceptance_criteria": "Multiple users can edit simultaneously",
                }
            ],
            "requirements_summary": {
                "total_requirements": 4,
                "by_priority": {"high": 3, "medium": 1, "low": 0},
                "by_category": {
                    "functional": 1,
                    "non_functional": 1,
                    "business": 1,
                    "technical": 1,
                },
            },
        }
        return sample_prd_state

    @pytest.mark.asyncio
    async def test_successful_feature_definition(self, node, state_with_requirements, mock_context):
        """Test successful feature definition."""
        # Mock AI response
        mock_response = json.dumps(
            {
                "features": [
                    {
                        "id": "FEAT-001",
                        "name": "Real-time Editor",
                        "description": "Collaborative markdown editor with real-time sync",
                        "priority": "M",
                        "user_stories": [
                            "As a user, I want to edit documents in real-time with others"
                        ],
                        "complexity": "Complex",
                        "dependencies": [],
                        "acceptance_criteria": ["Multiple users can edit simultaneously"],
                        "related_requirements": ["REQ-F-001"],
                        "estimated_effort": "8 story points",
                    }
                ],
                "feature_roadmap": {
                    "must_have_features": ["FEAT-001"],
                    "should_have_features": [],
                    "could_have_features": [],
                    "wont_have_features": [],
                    "total_features": 1,
                    "priority_distribution": {"M": 1, "S": 0, "C": 0, "W": 0},
                },
                "release_phases": [
                    {
                        "phase": "Phase 1 - MVP",
                        "features": ["FEAT-001"],
                        "description": "Core collaborative editing features",
                    }
                ],
            }
        )

        mock_context.openrouter_client.complete.return_value = MagicMock(
            content=mock_response, usage=MagicMock(prompt_tokens=1000, completion_tokens=500)
        )

        mock_context.get_model.return_value = MagicMock(
            calculate_cost=MagicMock(return_value=0.015)
        )

        # Execute node
        result = await node.execute(state_with_requirements, mock_context)

        # Verify result
        assert "features" in result
        assert result["total_features"] == 1
        assert result["must_have_count"] == 1
        assert result["prioritization_quality"] > 0

        # Verify state was updated
        assert state_with_requirements.feature_prioritization_quality > 0

    @pytest.mark.asyncio
    async def test_balanced_prioritization(self, node, state_with_requirements, mock_context):
        """Test balanced prioritization scoring."""
        # Mock response with balanced priorities
        mock_response = json.dumps(
            {
                "features": [],
                "feature_roadmap": {
                    "must_have_features": [],
                    "should_have_features": [],
                    "could_have_features": [],
                    "wont_have_features": [],
                    "total_features": 10,
                    "priority_distribution": {
                        "M": 3,
                        "S": 4,
                        "C": 2,
                        "W": 1,
                    },  # Balanced distribution
                },
                "release_phases": [],
            }
        )

        mock_context.openrouter_client.complete.return_value = MagicMock(
            content=mock_response, usage=MagicMock(prompt_tokens=1000, completion_tokens=500)
        )

        mock_context.get_model.return_value = MagicMock(
            calculate_cost=MagicMock(return_value=0.015)
        )

        # Execute node
        result = await node.execute(state_with_requirements, mock_context)

        # Should have good prioritization quality due to balanced distribution
        assert result["prioritization_quality"] > 0.5


class TestSetMetricsNode:
    """Test SetMetricsNode functionality."""

    @pytest.fixture
    def node(self):
        return SetMetricsNode()

    @pytest.fixture
    def state_with_features(self, sample_prd_state):
        """Create state with features already defined."""
        sample_prd_state.requirements = {
            "functional_requirements": [
                {"id": "REQ-F-001", "description": "Real-time editing", "priority": "High"}
            ]
        }
        sample_prd_state.features = {
            "features": [
                {
                    "id": "FEAT-001",
                    "name": "Real-time Editor",
                    "priority": "M",
                    "complexity": "Complex",
                }
            ],
            "feature_roadmap": {
                "total_features": 1,
                "priority_distribution": {"M": 1, "S": 0, "C": 0, "W": 0},
            },
        }
        return sample_prd_state

    @pytest.mark.asyncio
    async def test_successful_metrics_definition(self, node, state_with_features, mock_context):
        """Test successful metrics definition."""
        # Mock AI response
        mock_response = json.dumps(
            {
                "success_metrics": {
                    "user_engagement": [
                        {
                            "name": "Daily Active Users (DAU)",
                            "description": "Number of unique users per day",
                            "measurement": "Track user logins",
                            "targets": {
                                "short_term": "1,000 DAU within 3 months",
                                "long_term": "10,000 DAU within 12 months",
                            },
                            "success_criteria": "Consistent upward trend",
                            "data_sources": "User authentication logs",
                            "measurement_frequency": "Daily",
                        }
                    ],
                    "business": [
                        {
                            "name": "Revenue Growth",
                            "description": "Monthly recurring revenue growth",
                            "measurement": "Track subscription revenue",
                            "targets": {
                                "short_term": "$10K MRR within 6 months",
                                "long_term": "$100K MRR within 18 months",
                            },
                            "success_criteria": ">15% month-over-month growth",
                            "data_sources": "Payment processor",
                            "measurement_frequency": "Monthly",
                        }
                    ],
                    "technical": [],
                    "quality": [],
                    "adoption": [],
                },
                "kpi_dashboard": {
                    "primary_kpis": ["DAU", "Revenue"],
                    "secondary_kpis": ["Uptime", "Retention"],
                    "monitoring_tools": ["Analytics platform"],
                },
                "metrics_summary": {
                    "total_metrics": 2,
                    "by_category": {
                        "user_engagement": 1,
                        "business": 1,
                        "technical": 0,
                        "quality": 0,
                        "adoption": 0,
                    },
                    "measurement_frequency": {
                        "real_time": 0,
                        "daily": 1,
                        "weekly": 0,
                        "monthly": 1,
                        "quarterly": 0,
                    },
                },
            }
        )

        mock_context.openrouter_client.complete.return_value = MagicMock(
            content=mock_response, usage=MagicMock(prompt_tokens=1000, completion_tokens=500)
        )

        mock_context.get_model.return_value = MagicMock(
            calculate_cost=MagicMock(return_value=0.015)
        )

        # Execute node
        result = await node.execute(state_with_features, mock_context)

        # Verify result
        assert "success_metrics" in result
        assert result["total_metrics"] == 2
        assert result["category_coverage"] == 2  # user_engagement + business
        assert result["specificity_score"] > 0

        # Verify state was updated
        assert state_with_features.metrics_specificity > 0


class TestGeneratePRDNode:
    """Test GeneratePRDNode functionality."""

    @pytest.fixture
    def node(self):
        return GeneratePRDNode()

    @pytest.fixture
    def complete_prd_state(self, sample_prd_state):
        """Create state with all previous steps completed."""
        sample_prd_state.requirements = {
            "functional_requirements": [{"id": "REQ-F-001", "description": "Real-time editing"}]
        }
        sample_prd_state.features = {
            "features": [{"id": "FEAT-001", "name": "Real-time Editor", "priority": "M"}]
        }
        sample_prd_state.success_metrics = {
            "success_metrics": {
                "user_engagement": [{"name": "DAU", "description": "Daily active users"}]
            }
        }
        return sample_prd_state

    @pytest.mark.asyncio
    async def test_successful_prd_generation(self, node, complete_prd_state, mock_context):
        """Test successful PRD document generation."""
        # Mock AI response
        mock_response = """# Product Requirements Document: Collaborative Markdown Editor

## Executive Summary
This document outlines the requirements for a real-time collaborative markdown editor.

## Problem Statement
Users need to collaborate on markdown documents in real-time with seamless synchronization.

## Target Users
- Developers
- Content creators
- Technical writers

## Requirements
### Functional Requirements
- REQ-F-001: Real-time collaborative editing

## Features
### Must Have Features
- FEAT-001: Real-time Editor - Collaborative markdown editor with real-time sync

## Success Metrics
- Daily Active Users (DAU): 1,000 within 3 months
- Revenue Growth: $10K MRR within 6 months

## Technical Architecture
- WebSocket-based real-time communication
- CRDT for conflict resolution
- React frontend with Node.js backend

## Timeline & Milestones
- Phase 1 (MVP): Core editing features
- Phase 2: Advanced collaboration features
- Phase 3: Enterprise features

## Assumptions & Constraints
- Users have modern browsers
- Stable internet connection required
"""

        mock_context.openrouter_client.complete.return_value = MagicMock(
            content=mock_response, usage=MagicMock(prompt_tokens=1000, completion_tokens=800)
        )

        mock_context.get_model.return_value = MagicMock(
            calculate_cost=MagicMock(return_value=0.024)
        )

        # Execute node
        result = await node.execute(complete_prd_state, mock_context)

        # Verify result
        assert "prd_content" in result
        assert len(result["prd_content"]) > 1000  # Substantial document
        assert result["section_count"] >= 5  # Multiple sections
        assert result["model_used"] == "anthropic/claude-sonnet-4.5"

        # Verify state was updated
        assert complete_prd_state.document_coherence > 0
        assert complete_prd_state.prd_content == mock_response


class TestReviewFormatNode:
    """Test ReviewFormatNode functionality."""

    @pytest.fixture
    def node(self):
        return ReviewFormatNode()

    @pytest.fixture
    def state_with_prd(self, sample_prd_state):
        """Create state with generated PRD content."""
        sample_prd_state.prd_content = """# Product Requirements Document

## Executive Summary
Basic summary...

## Requirements
Some requirements...

## Features
Some features...
"""
        sample_prd_state.requirements = {"functional_requirements": []}
        sample_prd_state.features = {"features": []}
        sample_prd_state.success_metrics = {"success_metrics": {}}
        return sample_prd_state

    @pytest.mark.asyncio
    async def test_successful_prd_review(self, node, state_with_prd, mock_context):
        """Test successful PRD review and formatting."""
        # Mock AI response
        mock_response = json.dumps(
            {
                "review_summary": {
                    "overall_quality_score": 0.85,
                    "completeness_score": 0.9,
                    "consistency_score": 0.8,
                    "clarity_score": 0.85,
                    "formatting_score": 0.9,
                },
                "issues_found": [
                    {
                        "section": "Requirements",
                        "issue": "Missing acceptance criteria",
                        "severity": "Minor",
                        "suggestion": "Add specific acceptance criteria for each requirement",
                    }
                ],
                "improvements_made": [
                    "Added proper Markdown formatting",
                    "Improved section organization",
                    "Enhanced clarity of requirements",
                ],
                "final_prd": """# Product Requirements Document: Collaborative Markdown Editor

## Executive Summary
This document outlines the comprehensive requirements for a real-time collaborative markdown editor designed for modern development teams.

## Problem Statement
Development teams and content creators need a seamless way to collaborate on markdown documents in real-time, with instant synchronization and conflict resolution.

## Target Users
- Software developers and development teams
- Technical writers and documentation teams
- Content creators and bloggers
- Open source project maintainers

## Requirements
### Functional Requirements
- Real-time collaborative editing with sub-100ms latency
- Automatic conflict resolution using CRDT algorithms
- Version history and document restore functionality
- User authentication and permission management

### Non-Functional Requirements
- Performance: Support 1000+ concurrent users
- Security: End-to-end encryption for sensitive documents
- Reliability: 99.9% uptime with automatic failover
- Scalability: Horizontal scaling capability

## Features
### Must Have Features (MVP)
- Real-time collaborative editing interface
- User presence indicators and cursors
- Basic document sharing and permissions
- Export to multiple formats (PDF, HTML, DOCX)

### Should Have Features
- Advanced formatting tools and themes
- Comment and suggestion system
- Document templates and snippets
- Integration with popular development tools

### Could Have Features
- AI-powered writing assistance
- Advanced analytics and insights
- Custom branding and white-labeling
- Plugin ecosystem and extensions

## Success Metrics
- User Engagement: 1,000 DAU within 3 months, 10,000 DAU within 12 months
- Business Metrics: $10K MRR within 6 months, $100K MRR within 18 months
- Technical Performance: <100ms edit latency, 99.9% uptime
- Quality Metrics: NPS > 60, user retention > 80% after 90 days
- Adoption Metrics: 70% retention after 30 days, 15% MoM growth

## Technical Architecture
- Frontend: React 18 with TypeScript and Tailwind CSS
- Backend: Node.js with Express and Socket.IO
- Database: PostgreSQL for metadata, Redis for caching
- Real-time: WebSocket with CRDT for conflict resolution
- Infrastructure: Docker containers on Kubernetes cluster

## Timeline & Milestones
### Phase 1 - MVP (3 months)
- Core collaborative editing functionality
- Basic user authentication and permissions
- Document sharing and export features

### Phase 2 - Enhanced Features (3 months)
- Advanced formatting and themes
- Comment and suggestion system
- Integration with development tools

### Phase 3 - Scale & Enterprise (6 months)
- Advanced analytics and insights
- Enterprise security features
- Plugin ecosystem and API

## Assumptions & Constraints
### Assumptions
- Users have modern browsers supporting WebSocket
- Stable internet connection (>10Mbps) for optimal experience
- Basic familiarity with markdown syntax

### Constraints
- Initial launch limited to web-based interface
- Mobile apps planned for Phase 3
- Enterprise features require additional compliance

## Appendices
### Technical Specifications
- WebSocket protocol for real-time communication
- CRDT data structure for conflict-free replication
- JWT-based authentication with refresh tokens
- AES-256 encryption for document storage

### User Research Summary
- Interviews with 50+ target users conducted
- Competitive analysis of 10+ existing solutions
- Market research indicating $2.5B total addressable market
""",
            }
        )

        mock_context.openrouter_client.complete.return_value = MagicMock(
            content=mock_response, usage=MagicMock(prompt_tokens=1500, completion_tokens=1200)
        )

        mock_context.get_model.return_value = MagicMock(
            calculate_cost=MagicMock(return_value=0.036)
        )

        # Execute node
        result = await node.execute(state_with_prd, mock_context)

        # Verify result
        assert "final_prd" in result
        assert len(result["final_prd"]) > len(state_with_prd.prd_content)  # Should be enhanced
        assert result["issues_found"] == 1
        assert result["improvements_made"] == 3
        assert result["final_document_length"] > 2000  # Substantial document

        # Verify state was updated
        assert state_with_prd.final_prd == result["final_prd"]
        assert state_with_prd.last_updated is not None

    @pytest.mark.asyncio
    async def test_fallback_on_json_error(self, node, state_with_prd, mock_context):
        """Test fallback behavior when JSON parsing fails."""
        # Mock non-JSON response
        mock_response = """# Enhanced Product Requirements Document

This is an enhanced version of the PRD with better formatting and structure.

## Improved Sections
- Better organization
- Enhanced clarity
- Professional formatting
"""

        mock_context.openrouter_client.complete.return_value = MagicMock(
            content=mock_response, usage=MagicMock(prompt_tokens=1000, completion_tokens=500)
        )

        mock_context.get_model.return_value = MagicMock(
            calculate_cost=MagicMock(return_value=0.015)
        )

        # Execute node - should not raise exception
        result = await node.execute(state_with_prd, mock_context)

        # Verify fallback behavior
        assert "final_prd" in result
        assert result["final_prd"] == mock_response
        assert result["issues_found"] == 0  # No issues found in fallback mode

        # Verify state was updated
        assert state_with_prd.final_prd == mock_response
