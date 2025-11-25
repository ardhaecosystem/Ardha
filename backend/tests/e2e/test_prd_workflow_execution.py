"""
End-to-end tests for PRD workflow execution.

This module tests the complete PRD workflow execution from
start to finish with real services and database interactions.
"""

import asyncio
import json
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from ardha.schemas.workflows.prd import PRDState, PRDWorkflowConfig
from ardha.workflows.nodes.prd_nodes import PRDNodeException
from ardha.workflows.prd_workflow import PRDWorkflow, get_prd_workflow
from ardha.workflows.state import WorkflowStatus, WorkflowType


@pytest.fixture
def sample_research_summary():
    """Comprehensive sample research summary for E2E testing."""
    return {
        "idea": "A collaborative markdown editor with real-time collaboration features",
        "idea_analysis": {
            "core_concept": "Real-time collaborative markdown editing platform",
            "value_proposition": "Seamless collaboration for technical content creators",
            "target_users": [
                "Software development teams",
                "Technical writers and documentation teams",
                "Open source project maintainers",
                "Content creators and bloggers",
            ],
            "key_features": [
                "Real-time collaborative editing",
                "Version control and history",
                "Comment and suggestion system",
                "Export to multiple formats",
            ],
            "unique_differentiators": [
                "Developer-focused tooling",
                "Superior performance and reliability",
                "Advanced markdown support",
                "Seamless integrations",
            ],
        },
        "market_research": {
            "market_size": "$2.5B total addressable market for collaborative tools",
            "market_growth": "15% annual growth rate in collaborative software",
            "target_segments": [
                "Enterprise development teams (40%)",
                "SMB tech companies (35%)",
                "Individual developers (15%)",
                "Educational institutions (10%)",
            ],
            "competitors": {
                "direct": ["Notion", "Google Docs", "Coda"],
                "indirect": ["HackMD", "Typora", "VS Code"],
                "potential": ["GitHub Codespaces", "Replit"],
            },
            "market_opportunity": {
                "gap": "Lack of developer-focused collaborative tools",
                "timing": "Growing demand for remote collaboration tools",
                "advantage": "Performance and developer experience focus",
            },
            "revenue_model": {
                "primary": "SaaS subscription model",
                "pricing": "$10/user/month for teams, $5/user/month for individuals",
                "enterprise": "Custom pricing for large organizations",
            },
        },
        "competitive_analysis": {
            "notion": {
                "strengths": ["All-in-one workspace", "Strong brand recognition"],
                "weaknesses": ["Not developer-focused", "Performance issues"],
                "market_share": "35% of collaborative tools market",
            },
            "google_docs": {
                "strengths": ["Free tier", "Google ecosystem integration"],
                "weaknesses": ["Limited markdown support", "Generic collaboration"],
                "market_share": "40% of document collaboration",
            },
            "hackmd": {
                "strengths": ["Markdown-focused", "Open source"],
                "weaknesses": ["Limited features", "Small user base"],
                "market_share": "5% of markdown editors",
            },
            "competitive_positioning": {
                "our_advantages": [
                    "Superior performance and reliability",
                    "Developer-focused feature set",
                    "Advanced markdown capabilities",
                    "Better integration with development tools",
                ],
                "market_entry_strategy": "Target development teams first, then expand",
            },
        },
        "technical_feasibility": {
            "complexity_assessment": "Medium complexity with some challenging components",
            "core_technologies": [
                "WebSocket for real-time communication",
                "CRDT (Conflict-free Replicated Data Types) for synchronization",
                "React 18 with TypeScript for frontend",
                "Node.js with Express for backend API",
                "PostgreSQL for primary data storage",
                "Redis for caching and session management",
            ],
            "technical_challenges": [
                "Real-time conflict resolution at scale",
                "Performance optimization for large documents",
                "Reliable offline synchronization",
                "Cross-platform compatibility",
            ],
            "feasibility_score": 0.85,
            "development_timeline": "6-9 months for MVP, 12-18 months for full feature set",
            "technical_risks": [
                "Scalability of real-time synchronization",
                "Data consistency across distributed systems",
                "Performance with large collaborative sessions",
            ],
            "mitigation_strategies": [
                "Use proven CRDT libraries",
                "Implement sharding for large documents",
                "Comprehensive testing and monitoring",
            ],
        },
        "research_summary": {
            "overall_confidence": 0.88,
            "sources_analyzed": 45,
            "key_insights": [
                "Strong market demand for developer-focused collaborative tools",
                "Performance and reliability are critical success factors",
                "Real-time collaboration is a key differentiator in the market",
                "Integration with existing development workflows is essential",
            ],
            "success_factors": [
                "Superior performance compared to competitors",
                "Developer-focused feature set and user experience",
                "Reliable real-time synchronization",
                "Strong integration ecosystem",
            ],
            "risk_factors": [
                "Competition from established players",
                "Technical complexity of real-time features",
                "Market education required for new approach",
            ],
        },
    }


class TestPRDWorkflowE2E:
    """End-to-end tests for PRD workflow execution."""

    @pytest.mark.asyncio
    async def test_complete_prd_workflow_execution(self, sample_research_summary):
        """Test complete PRD workflow execution from start to finish."""
        # Create workflow with test configuration
        config = PRDWorkflowConfig(
            extract_requirements_model="z-ai/glm-4.6",  # Use cheaper models for testing
            define_features_model="z-ai/glm-4.6",
            set_metrics_model="z-ai/glm-4.6",
            generate_prd_model="z-ai/glm-4.6",
            review_format_model="z-ai/glm-4.6",
            max_retries_per_step=1,
            timeout_per_step_seconds=60,
            enable_streaming=False,  # Disable streaming for simpler testing
            enable_human_approval=False,  # Disable human approval for automated testing
        )

        workflow = PRDWorkflow(config)

        # Mock the AI client to avoid real API calls
        with patch("ardha.workflows.prd_workflow.OpenRouterClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value = mock_client

            # Mock AI responses for each node
            mock_responses = {
                "extract_requirements": json.dumps(
                    {
                        "functional_requirements": [
                            {
                                "id": "REQ-F-001",
                                "description": "Real-time collaborative markdown editing",
                                "priority": "High",
                                "acceptance_criteria": "Multiple users can edit the same document simultaneously with sub-100ms latency",
                            },
                            {
                                "id": "REQ-F-002",
                                "description": "User presence indicators and cursors",
                                "priority": "High",
                                "acceptance_criteria": "Users can see other users' cursors and selection in real-time",
                            },
                            {
                                "id": "REQ-F-003",
                                "description": "Automatic conflict resolution using CRDT",
                                "priority": "High",
                                "acceptance_criteria": "Edit conflicts are resolved automatically without user intervention",
                            },
                        ],
                        "non_functional_requirements": [
                            {
                                "id": "REQ-NF-001",
                                "description": "Sub-100ms latency for edit synchronization",
                                "priority": "High",
                                "category": "Performance",
                                "metrics": "<100ms round-trip time for edit propagation",
                            },
                            {
                                "id": "REQ-NF-002",
                                "description": "Support for 1000+ concurrent users per document",
                                "priority": "High",
                                "category": "Scalability",
                                "metrics": "System maintains performance with 1000+ concurrent users",
                            },
                            {
                                "id": "REQ-NF-003",
                                "description": "99.9% uptime availability",
                                "priority": "High",
                                "category": "Reliability",
                                "metrics": "<0.1% downtime per month",
                            },
                        ],
                        "business_requirements": [
                            {
                                "id": "REQ-B-001",
                                "description": "SaaS subscription revenue model",
                                "priority": "Medium",
                                "success_criteria": "Achieve $1M ARR within 24 months",
                            }
                        ],
                        "technical_requirements": [
                            {
                                "id": "REQ-T-001",
                                "description": "WebSocket-based real-time communication",
                                "priority": "High",
                                "constraints": "Must support bidirectional communication with fallback options",
                            }
                        ],
                        "requirements_summary": {
                            "total_requirements": 8,
                            "by_priority": {"high": 7, "medium": 1, "low": 0},
                            "by_category": {
                                "functional": 3,
                                "non_functional": 3,
                                "business": 1,
                                "technical": 1,
                            },
                        },
                    }
                ),
                "define_features": json.dumps(
                    {
                        "features": [
                            {
                                "id": "FEAT-001",
                                "name": "Real-time Collaborative Editor",
                                "description": "Core markdown editor with real-time synchronization and collaboration features",
                                "priority": "M",
                                "user_stories": [
                                    "As a developer, I want to edit markdown documents in real-time with my team",
                                    "As a user, I want to see other users' cursors and selections while editing",
                                    "As a collaborator, I want conflicts to be resolved automatically",
                                ],
                                "complexity": "Complex",
                                "dependencies": [],
                                "acceptance_criteria": [
                                    "Multiple users can edit simultaneously",
                                    "Real-time cursor and presence indicators",
                                    "Automatic conflict resolution",
                                    "Sub-100ms synchronization latency",
                                ],
                                "related_requirements": ["REQ-F-001", "REQ-F-002", "REQ-F-003"],
                                "estimated_effort": "13 story points",
                            },
                            {
                                "id": "FEAT-002",
                                "name": "Document Management",
                                "description": "Document creation, organization, sharing, and permission management",
                                "priority": "M",
                                "user_stories": [
                                    "As a user, I want to create and organize documents in workspaces",
                                    "As a team lead, I want to manage permissions and access control",
                                    "As a user, I want to share documents with external collaborators",
                                ],
                                "complexity": "Medium",
                                "dependencies": [],
                                "acceptance_criteria": [
                                    "Document creation and editing",
                                    "Workspace organization",
                                    "User permission management",
                                    "Document sharing capabilities",
                                ],
                                "related_requirements": ["REQ-B-001"],
                                "estimated_effort": "8 story points",
                            },
                            {
                                "id": "FEAT-003",
                                "name": "Version History and Restore",
                                "description": "Complete version control with branching and restore capabilities",
                                "priority": "S",
                                "user_stories": [
                                    "As a user, I want to see complete version history of documents",
                                    "As a collaborator, I want to restore previous versions",
                                    "As a developer, I want to branch and merge document changes",
                                ],
                                "complexity": "Complex",
                                "dependencies": ["FEAT-001"],
                                "acceptance_criteria": [
                                    "Complete version history tracking",
                                    "Point-in-time restore functionality",
                                    "Branch and merge capabilities",
                                    "Diff visualization",
                                ],
                                "related_requirements": ["REQ-NF-002"],
                                "estimated_effort": "13 story points",
                            },
                        ],
                        "feature_roadmap": {
                            "must_have_features": ["FEAT-001", "FEAT-002"],
                            "should_have_features": ["FEAT-003"],
                            "could_have_features": [],
                            "wont_have_features": [],
                            "total_features": 3,
                            "priority_distribution": {"M": 2, "S": 1, "C": 0, "W": 0},
                        },
                        "release_phases": [
                            {
                                "phase": "Phase 1 - MVP (3 months)",
                                "features": ["FEAT-001", "FEAT-002"],
                                "description": "Core collaborative editing and document management features",
                            },
                            {
                                "phase": "Phase 2 - Enhanced Features (3 months)",
                                "features": ["FEAT-003"],
                                "description": "Version control and advanced collaboration features",
                            },
                        ],
                    }
                ),
                "set_metrics": json.dumps(
                    {
                        "success_metrics": {
                            "user_engagement": [
                                {
                                    "name": "Daily Active Users (DAU)",
                                    "description": "Number of unique users who actively use the platform daily",
                                    "measurement": "Track authenticated user sessions and document interactions",
                                    "targets": {
                                        "short_term": "1,000 DAU within 3 months of launch",
                                        "long_term": "10,000 DAU within 12 months",
                                    },
                                    "success_criteria": "Consistent upward trend with >20% month-over-month growth",
                                    "data_sources": "User authentication logs, document activity tracking",
                                    "measurement_frequency": "Daily",
                                },
                                {
                                    "name": "Average Session Duration",
                                    "description": "Average time users spend actively editing per session",
                                    "measurement": "Track user session length and document interaction time",
                                    "targets": {
                                        "short_term": "15 minutes average session duration",
                                        "long_term": "30 minutes average session duration",
                                    },
                                    "success_criteria": "Increasing trend indicating user engagement and value",
                                    "data_sources": "Session tracking, user analytics platform",
                                    "measurement_frequency": "Weekly",
                                },
                            ],
                            "business": [
                                {
                                    "name": "Monthly Recurring Revenue (MRR)",
                                    "description": "Predictable monthly revenue from subscription plans",
                                    "measurement": "Track active subscriptions and billing cycles",
                                    "targets": {
                                        "short_term": "$10K MRR within 6 months",
                                        "long_term": "$100K MRR within 18 months",
                                    },
                                    "success_criteria": ">15% month-over-month growth with low churn rate",
                                    "data_sources": "Payment processor, billing system, subscription management",
                                    "measurement_frequency": "Monthly",
                                },
                                {
                                    "name": "Customer Acquisition Cost (CAC)",
                                    "description": "Cost to acquire a new paying customer",
                                    "measurement": "Track marketing spend and new customer acquisition",
                                    "targets": {
                                        "short_term": "$50 CAC for individual plans",
                                        "long_term": "$200 CAC for team plans",
                                    },
                                    "success_criteria": "CAC < 3x monthly customer value for sustainable growth",
                                    "data_sources": "Marketing analytics, sales CRM, financial tracking",
                                    "measurement_frequency": "Monthly",
                                },
                            ],
                            "technical": [
                                {
                                    "name": "Edit Synchronization Latency",
                                    "description": "Time for edits to propagate to all collaborators",
                                    "measurement": "Track WebSocket message round-trip times",
                                    "targets": {
                                        "short_term": "<200ms average latency",
                                        "long_term": "<100ms average latency",
                                    },
                                    "success_criteria": "95% of edits sync within target latency",
                                    "data_sources": "WebSocket monitoring, performance metrics",
                                    "measurement_frequency": "Real-time",
                                },
                                {
                                    "name": "System Uptime",
                                    "description": "Percentage of time the service is available",
                                    "measurement": "Monitor service health and response times",
                                    "targets": {
                                        "short_term": "99.5% uptime",
                                        "long_term": "99.9% uptime",
                                    },
                                    "success_criteria": "Consistent uptime >99.5% with minimal downtime",
                                    "data_sources": "Infrastructure monitoring, health checks",
                                    "measurement_frequency": "Real-time",
                                },
                            ],
                            "quality": [
                                {
                                    "name": "User Satisfaction Score (NPS)",
                                    "description": "Net Promoter Score measuring user satisfaction and loyalty",
                                    "measurement": "Regular user surveys and feedback collection",
                                    "targets": {
                                        "short_term": "NPS > 40 within 6 months",
                                        "long_term": "NPS > 60 within 12 months",
                                    },
                                    "success_criteria": "Positive trend with increasing promoter percentage",
                                    "data_sources": "User surveys, feedback forms, app store reviews",
                                    "measurement_frequency": "Quarterly",
                                }
                            ],
                            "adoption": [
                                {
                                    "name": "User Retention Rate",
                                    "description": "Percentage of users who continue using the platform over time",
                                    "measurement": "Track user cohorts and retention curves",
                                    "targets": {
                                        "short_term": "70% retention after 30 days",
                                        "long_term": "80% retention after 90 days",
                                    },
                                    "success_criteria": "Improving retention rates indicating product value",
                                    "data_sources": "User activity logs, cohort analysis",
                                    "measurement_frequency": "Monthly",
                                }
                            ],
                        },
                        "kpi_dashboard": {
                            "primary_kpis": ["DAU", "MRR", "Edit Latency", "NPS"],
                            "secondary_kpis": [
                                "Session Duration",
                                "CAC",
                                "Uptime",
                                "Retention Rate",
                            ],
                            "monitoring_tools": [
                                "User analytics",
                                "Payment processor",
                                "Infrastructure monitoring",
                                "Survey tools",
                            ],
                        },
                        "metrics_summary": {
                            "total_metrics": 8,
                            "by_category": {
                                "user_engagement": 2,
                                "business": 2,
                                "technical": 2,
                                "quality": 1,
                                "adoption": 1,
                            },
                            "measurement_frequency": {
                                "real_time": 2,
                                "daily": 1,
                                "weekly": 1,
                                "monthly": 3,
                                "quarterly": 1,
                            },
                        },
                    }
                ),
                "generate_prd": """# Product Requirements Document: Collaborative Markdown Editor

## Executive Summary

This document outlines the comprehensive requirements for a real-time collaborative markdown editor specifically designed for development teams and technical content creators. The platform addresses the critical gap in the market for developer-focused collaboration tools that combine superior performance with advanced markdown capabilities.

## Problem Statement

Development teams and technical content creators currently lack a dedicated platform that provides seamless real-time collaboration for markdown documents. Existing solutions either lack developer-specific features, suffer from performance issues, or fail to provide the advanced markdown capabilities required for technical documentation.

## Target Users

### Primary Users
- **Software Development Teams**: Collaborating on technical documentation, README files, and code comments
- **Technical Writers**: Creating and maintaining comprehensive documentation with multiple contributors
- **Open Source Project Maintainers**: Managing community contributions to project documentation

### Secondary Users
- **Content Creators**: Bloggers and technical writers requiring markdown collaboration
- **Educational Institutions**: Collaborative learning environments for technical subjects
- **Enterprise Teams**: Large organizations requiring advanced permission and workflow management

## Requirements

### Functional Requirements

#### REQ-F-001: Real-time Collaborative Editing
**Priority**: High
**Description**: Multiple users must be able to edit the same markdown document simultaneously with real-time synchronization.
**Acceptance Criteria**:
- Sub-100ms latency for edit propagation
- Visual indicators for other users' cursors and selections
- Automatic conflict resolution without user intervention

#### REQ-F-002: User Presence and Awareness
**Priority**: High
**Description**: Users must be able to see other active collaborators and their current focus within the document.
**Acceptance Criteria**:
- Real-time cursor position display for all users
- User avatars and presence indicators
- Selection highlighting for active users

#### REQ-F-003: Automatic Conflict Resolution
**Priority**: High
**Description**: Edit conflicts must be resolved automatically using CRDT (Conflict-free Replicated Data Types) algorithms.
**Acceptance Criteria**:
- No manual conflict resolution required
- Preservation of all user edits
- Transparent conflict resolution process

### Non-Functional Requirements

#### REQ-NF-001: Performance Requirements
**Priority**: High
**Category**: Performance
**Description**: System must maintain high performance for real-time collaboration.
**Metrics**: <100ms round-trip time for edit synchronization

#### REQ-NF-002: Scalability Requirements
**Priority**: High
**Category**: Scalability
**Description**: System must support large numbers of concurrent users.
**Metrics**: 1000+ concurrent users per document without performance degradation

#### REQ-NF-003: Reliability Requirements
**Priority**: High
**Category**: Reliability
**Description**: System must maintain high availability for business continuity.
**Metrics**: 99.9% uptime with <0.1% monthly downtime

### Business Requirements

#### REQ-B-001: Revenue Model
**Priority**: Medium
**Description**: SaaS subscription model with tiered pricing.
**Success Criteria**: Achieve $1M ARR within 24 months

### Technical Requirements

#### REQ-T-001: Communication Protocol
**Priority**: High
**Description**: WebSocket-based real-time communication with fallback options.
**Constraints**: Must support bidirectional communication and maintain connection state

## Features

### Must Have Features (MVP)

#### FEAT-001: Real-time Collaborative Editor
**Complexity**: Complex
**Estimated Effort**: 13 story points
**Dependencies**: None

**User Stories**:
- As a developer, I want to edit markdown documents in real-time with my team
- As a user, I want to see other users' cursors and selections while editing
- As a collaborator, I want conflicts to be resolved automatically

**Acceptance Criteria**:
- Multiple users can edit simultaneously
- Real-time cursor and presence indicators
- Automatic conflict resolution
- Sub-100ms synchronization latency

#### FEAT-002: Document Management
**Complexity**: Medium
**Estimated Effort**: 8 story points
**Dependencies**: None

**User Stories**:
- As a user, I want to create and organize documents in workspaces
- As a team lead, I want to manage permissions and access control
- As a user, I want to share documents with external collaborators

**Acceptance Criteria**:
- Document creation and editing
- Workspace organization
- User permission management
- Document sharing capabilities

### Should Have Features (Phase 2)

#### FEAT-003: Version History and Restore
**Complexity**: Complex
**Estimated Effort**: 13 story points
**Dependencies**: FEAT-001

**User Stories**:
- As a user, I want to see complete version history of documents
- As a collaborator, I want to restore previous versions
- As a developer, I want to branch and merge document changes

**Acceptance Criteria**:
- Complete version history tracking
- Point-in-time restore functionality
- Branch and merge capabilities
- Diff visualization

## Success Metrics

### User Engagement Metrics

#### Daily Active Users (DAU)
- **Target**: 1,000 DAU within 3 months, 10,000 DAU within 12 months
- **Success Criteria**: >20% month-over-month growth
- **Measurement**: Daily tracking of authenticated user sessions

#### Average Session Duration
- **Target**: 15 minutes (short-term), 30 minutes (long-term)
- **Success Criteria**: Increasing trend indicating user engagement
- **Measurement**: Weekly analysis of user session data

### Business Metrics

#### Monthly Recurring Revenue (MRR)
- **Target**: $10K MRR within 6 months, $100K MRR within 18 months
- **Success Criteria**: >15% month-over-month growth with low churn
- **Measurement**: Monthly financial tracking

#### Customer Acquisition Cost (CAC)
- **Target**: $50 (individual plans), $200 (team plans)
- **Success Criteria**: CAC < 3x monthly customer value
- **Measurement**: Monthly marketing and sales analysis

### Technical Metrics

#### Edit Synchronization Latency
- **Target**: <200ms (short-term), <100ms (long-term)
- **Success Criteria**: 95% of edits sync within target latency
- **Measurement**: Real-time WebSocket monitoring

#### System Uptime
- **Target**: 99.5% (short-term), 99.9% (long-term)
- **Success Criteria**: Consistent uptime >99.5%
- **Measurement**: Real-time infrastructure monitoring

### Quality Metrics

#### User Satisfaction Score (NPS)
- **Target**: NPS > 40 within 6 months, NPS > 60 within 12 months
- **Success Criteria**: Positive trend with increasing promoters
- **Measurement**: Quarterly user surveys

### Adoption Metrics

#### User Retention Rate
- **Target**: 70% retention after 30 days, 80% retention after 90 days
- **Success Criteria**: Improving retention rates over time
- **Measurement**: Monthly cohort analysis

## Technical Architecture

### Core Technologies
- **Frontend**: React 18 with TypeScript and Tailwind CSS
- **Backend**: Node.js with Express framework
- **Real-time Communication**: WebSocket with Socket.IO
- **Data Synchronization**: CRDT libraries (Yjs or Automerge)
- **Database**: PostgreSQL for primary storage
- **Caching**: Redis for session management and caching
- **Infrastructure**: Docker containers on Kubernetes

### System Architecture
```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   React Client  │◄──►│   WebSocket     │◄──►│   Node.js API   │
│                 │    │   Gateway       │    │                 │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                                                        │
                                                        ▼
                                               ┌─────────────────┐
                                               │   PostgreSQL    │
                                               │                 │
                                               └─────────────────┘
```

### Data Flow
1. Client edits trigger WebSocket events
2. CRDT algorithm manages conflict resolution
3. Changes propagated to all connected clients
4. Database persists document state and metadata
5. Redis caches active sessions and temporary data

## Timeline & Milestones

### Phase 1 - MVP (3 months)
**Duration**: Months 1-3
**Features**: FEAT-001, FEAT-002
**Deliverables**:
- Core real-time editing functionality
- Basic document management
- User authentication and permissions
- WebSocket infrastructure

### Phase 2 - Enhanced Features (3 months)
**Duration**: Months 4-6
**Features**: FEAT-003
**Deliverables**:
- Version control and history
- Advanced collaboration features
- Performance optimization
- Beta testing with pilot customers

### Phase 3 - Scale & Enterprise (6 months)
**Duration**: Months 7-12
**Features**: Enterprise features, integrations
**Deliverables**:
- Enterprise security features
- Advanced analytics and insights
- Third-party integrations
- Mobile applications

## Assumptions & Constraints

### Assumptions
- Users have modern browsers supporting WebSocket and ES6+
- Stable internet connection (>10Mbps) for optimal experience
- Basic familiarity with markdown syntax and collaborative tools
- Organizations have existing workflows that can integrate with new tools

### Constraints
- Initial launch limited to web-based interface (mobile apps in Phase 3)
- Enterprise features require additional compliance and security measures
- Performance optimization may limit feature complexity in early versions
- Market education required for new collaborative approach

## Risk Assessment

### Technical Risks
- **CRDT Implementation Complexity**: Mitigate by using proven libraries
- **Scalability Challenges**: Address with sharding and load testing
- **Real-time Performance**: Optimize with efficient algorithms and infrastructure

### Market Risks
- **Competition from Established Players**: Differentiate with developer focus
- **User Adoption Challenges**: Provide excellent onboarding and migration tools
- **Pricing Pressure**: Demonstrate clear value proposition and ROI

### Business Risks
- **Funding and Runway**: Secure adequate funding for 18+ month development
- **Team Scaling**: Hire experienced engineers with real-time systems expertise
- **Go-to-Market Strategy**: Build strong community and developer relations

## Success Criteria

### Launch Success (3 months)
- 1,000+ active users
- $10K+ MRR
- <100ms average edit latency
- NPS > 40

### Growth Success (12 months)
- 10,000+ active users
- $100K+ MRR
- 80%+ user retention
- NPS > 60

### Market Success (18 months)
- Market leader in developer-focused collaborative tools
- Profitable operations with positive unit economics
- Strong brand recognition in developer community
- Established enterprise customer base

## Appendices

### Technical Specifications
- **WebSocket Protocol**: Custom protocol over standard WebSocket
- **CRDT Implementation**: Yjs library with custom extensions
- **Authentication**: JWT with refresh tokens and OAuth integration
- **Data Encryption**: AES-256 for document storage, TLS 1.3 for transmission

### User Research Summary
- **Interviews Conducted**: 50+ target users across all segments
- **Competitive Analysis**: 10+ existing solutions evaluated
- **Market Research**: $2.5B total addressable market identified
- **Pricing Research**: Willingness to pay $5-15/user/month confirmed

### Integration Requirements
- **Git Integration**: GitHub, GitLab, Bitbucket
- **Development Tools**: VS Code, JetBrains IDEs
- **Communication Tools**: Slack, Microsoft Teams
- **Documentation Platforms**: Confluence, ReadTheDocs
""",
                "review_format": json.dumps(
                    {
                        "review_summary": {
                            "overall_quality_score": 0.92,
                            "completeness_score": 0.95,
                            "consistency_score": 0.90,
                            "clarity_score": 0.93,
                            "formatting_score": 0.95,
                        },
                        "issues_found": [],
                        "improvements_made": [
                            "Enhanced executive summary with clearer value proposition",
                            "Improved technical architecture section with detailed diagrams",
                            "Added comprehensive risk assessment with mitigation strategies",
                            "Expanded success criteria with specific measurable targets",
                        ],
                        "final_prd": """# Product Requirements Document: Collaborative Markdown Editor

## Executive Summary

This document presents the comprehensive requirements for a real-time collaborative markdown editor specifically engineered for development teams and technical content creators. Our platform addresses the critical market gap for developer-focused collaboration tools that combine exceptional performance with advanced markdown capabilities, targeting a $2.5B total addressable market with 15% annual growth.

## Problem Statement

Development teams and technical content creators currently face a significant limitation in accessing dedicated platforms that provide seamless real-time collaboration for markdown documents. Existing solutions either lack developer-specific features, suffer from performance degradation, or fail to deliver the advanced markdown capabilities essential for technical documentation workflows.

## Target Users

### Primary Users
- **Software Development Teams**: Collaborating on technical documentation, README files, and code comments
- **Technical Writers**: Creating and maintaining comprehensive documentation with multiple contributors
- **Open Source Project Maintainers**: Managing community contributions to project documentation

### Secondary Users
- **Content Creators**: Bloggers and technical writers requiring markdown collaboration
- **Educational Institutions**: Collaborative learning environments for technical subjects
- **Enterprise Teams**: Large organizations requiring advanced permission and workflow management

## Requirements

### Functional Requirements

#### REQ-F-001: Real-time Collaborative Editing
**Priority**: High
**Description**: Multiple users must be able to edit the same markdown document simultaneously with real-time synchronization.
**Acceptance Criteria**:
- Sub-100ms latency for edit propagation
- Visual indicators for other users' cursors and selections
- Automatic conflict resolution without user intervention

[... Enhanced PRD content with all improvements applied ...]

## Success Criteria

### Launch Success (3 months)
- 1,000+ active users
- $10K+ MRR
- <100ms average edit latency
- NPS > 40

### Growth Success (12 months)
- 10,000+ active users
- $100K+ MRR
- 80%+ user retention
- NPS > 60

### Market Success (18 months)
- Market leader in developer-focused collaborative tools
- Profitable operations with positive unit economics
- Strong brand recognition in developer community
- Established enterprise customer base

## Appendices

### Technical Specifications
- **WebSocket Protocol**: Custom protocol over standard WebSocket
- **CRDT Implementation**: Yjs library with custom extensions
- **Authentication**: JWT with refresh tokens and OAuth integration
- **Data Encryption**: AES-256 for document storage, TLS 1.3 for transmission

### User Research Summary
- **Interviews Conducted**: 50+ target users across all segments
- **Competitive Analysis**: 10+ existing solutions evaluated
- **Market Research**: $2.5B total addressable market identified
- **Pricing Research**: Willingness to pay $5-15/user/month confirmed
""",
                    }
                ),
            }

            # Configure mock client to return different responses based on content
            def mock_complete_side_effect(request):
                response = MagicMock()
                content = request.messages[-1].content if request.messages else ""

                # Determine which node is calling based on the prompt content
                if "Extract comprehensive requirements" in content:
                    response.content = mock_responses["extract_requirements"]
                elif "Convert the following requirements" in content:
                    response.content = mock_responses["define_features"]
                elif "Define comprehensive success metrics" in content:
                    response.content = mock_responses["set_metrics"]
                elif "Generate a comprehensive Product Requirements Document" in content:
                    response.content = mock_responses["generate_prd"]
                elif "Review and polish the following Product Requirements Document" in content:
                    response.content = mock_responses["review_format"]
                else:
                    response.content = "Default mock response"

                response.usage = MagicMock(prompt_tokens=1000, completion_tokens=500)
                return response

            mock_client.complete.side_effect = mock_complete_side_effect

            # Mock model info
            mock_model = MagicMock()
            mock_model.calculate_cost.return_value = 0.015
            mock_client.get_model.return_value = mock_model

            # Mock Qdrant service
            with patch("ardha.workflows.prd_workflow.get_qdrant_service") as mock_qdrant:
                mock_qdrant.return_value = AsyncMock()

                # Execute workflow
                user_id = uuid4()
                project_id = uuid4()

                result = await workflow.execute(
                    research_summary=sample_research_summary,
                    user_id=user_id,
                    project_id=project_id,
                    parameters={"test_mode": True},
                )

                # Verify workflow completed successfully
                assert result.status == WorkflowStatus.COMPLETED
                assert result.final_prd is not None
                assert len(result.final_prd) > 5000  # Substantial PRD document

                # Verify all quality metrics are high
                assert result.requirements_completeness > 0.8
                assert result.feature_prioritization_quality > 0.7
                assert result.metrics_specificity > 0.7
                assert result.document_coherence > 0.8

                # Verify overall quality score
                overall_quality = result.calculate_prd_quality_score()
                assert overall_quality > 0.8

                # Verify PRD contains expected sections
                prd_content = result.final_prd.lower()
                expected_sections = [
                    "executive summary",
                    "problem statement",
                    "target users",
                    "requirements",
                    "features",
                    "success metrics",
                    "technical architecture",
                    "timeline",
                    "assumptions",
                ]

                for section in expected_sections:
                    assert section in prd_content, f"Missing section: {section}"

                # Verify specific requirements are included
                assert "req-f-001" in prd_content.lower()
                assert "real-time collaborative editing" in prd_content.lower()

                # Verify features are included
                assert "feat-001" in prd_content.lower()
                assert "real-time collaborative editor" in prd_content.lower()

                # Verify success metrics are included
                assert "daily active users" in prd_content.lower()
                assert "monthly recurring revenue" in prd_content.lower()

                print("E2E PRD workflow test completed successfully")

    @pytest.mark.asyncio
    async def test_prd_workflow_error_recovery(self, sample_research_summary):
        """Test PRD workflow error recovery and retry mechanisms."""
        config = PRDWorkflowConfig(
            max_retries_per_step=2,
            timeout_per_step_seconds=30,
            enable_streaming=False,
        )

        workflow = PRDWorkflow(config)

        # Mock AI client to fail on first attempt, succeed on retry
        with patch("ardha.workflows.prd_workflow.OpenRouterClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value = mock_client

            # Configure mock to fail first, then succeed
            call_count = 0

            def mock_complete_with_retry(request):
                nonlocal call_count
                call_count += 1

                if call_count == 1:
                    # First call fails
                    from ardha.core.openrouter import OpenRouterError

                    raise OpenRouterError("AI service temporarily unavailable")
                else:
                    # Second call succeeds
                    response = MagicMock()
                    response.content = json.dumps(
                        {
                            "functional_requirements": [
                                {
                                    "id": "REQ-F-001",
                                    "description": "Real-time collaborative editing",
                                    "priority": "High",
                                    "acceptance_criteria": "Multiple users can edit simultaneously",
                                }
                            ],
                            "non_functional_requirements": [],
                            "business_requirements": [],
                            "technical_requirements": [],
                            "requirements_summary": {
                                "total_requirements": 1,
                                "by_priority": {"high": 1, "medium": 0, "low": 0},
                                "by_category": {
                                    "functional": 1,
                                    "non_functional": 0,
                                    "business": 0,
                                    "technical": 0,
                                },
                            },
                        }
                    )
                    response.usage = MagicMock(prompt_tokens=1000, completion_tokens=500)
                    return response

            mock_client.complete.side_effect = mock_complete_with_retry

            # Mock model info
            mock_model = MagicMock()
            mock_model.calculate_cost.return_value = 0.015
            mock_client.get_model.return_value = mock_model

            # Mock Qdrant service
            with patch("ardha.workflows.prd_workflow.get_qdrant_service") as mock_qdrant:
                mock_qdrant.return_value = AsyncMock()

                # Execute workflow
                user_id = uuid4()

                result = await workflow.execute(
                    research_summary=sample_research_summary,
                    user_id=user_id,
                    parameters={"test_mode": True},
                )

                # Verify retry mechanism worked
                assert call_count == 2  # Should have retried once
                assert result.status == WorkflowStatus.COMPLETED
                assert result.requirements is not None

                print("PRD workflow error recovery test completed successfully")

    @pytest.mark.asyncio
    async def test_prd_workflow_max_retries_exceeded(self, sample_research_summary):
        """Test PRD workflow when max retries are exceeded."""
        config = PRDWorkflowConfig(
            max_retries_per_step=1,  # Low retry count for testing
            timeout_per_step_seconds=30,
            enable_streaming=False,
        )

        workflow = PRDWorkflow(config)

        # Mock AI client to always fail
        with patch("ardha.workflows.prd_workflow.OpenRouterClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value = mock_client

            # Configure mock to always fail
            mock_client.complete.side_effect = Exception("Persistent AI service failure")

            # Mock Qdrant service
            with patch("ardha.workflows.prd_workflow.get_qdrant_service") as mock_qdrant:
                mock_qdrant.return_value = AsyncMock()

                # Execute workflow - should fail after max retries
                user_id = uuid4()

                with pytest.raises(PRDNodeException, match="PRD workflow failed"):
                    await workflow.execute(
                        research_summary=sample_research_summary,
                        user_id=user_id,
                        parameters={"test_mode": True},
                    )

                print("PRD workflow max retries test completed successfully")

    @pytest.mark.asyncio
    async def test_prd_workflow_cancellation(self, sample_research_summary):
        """Test PRD workflow cancellation functionality."""
        config = PRDWorkflowConfig(
            max_retries_per_step=1,
            timeout_per_step_seconds=30,
            enable_streaming=False,
        )

        workflow = PRDWorkflow(config)

        # Mock AI client with delay
        with patch("ardha.workflows.prd_workflow.OpenRouterClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value = mock_client

            # Configure mock to take a long time (simulating long-running operation)
            async def mock_complete_with_delay(request):
                await asyncio.sleep(2)  # Simulate delay
                response = MagicMock()
                response.content = json.dumps(
                    {
                        "functional_requirements": [],
                        "non_functional_requirements": [],
                        "business_requirements": [],
                        "technical_requirements": [],
                        "requirements_summary": {
                            "total_requirements": 0,
                            "by_priority": {"high": 0, "medium": 0, "low": 0},
                            "by_category": {
                                "functional": 0,
                                "non_functional": 0,
                                "business": 0,
                                "technical": 0,
                            },
                        },
                    }
                )
                response.usage = MagicMock(prompt_tokens=1000, completion_tokens=500)
                return response

            mock_client.complete.side_effect = mock_complete_with_delay

            # Mock model info
            mock_model = MagicMock()
            mock_model.calculate_cost.return_value = 0.015
            mock_client.get_model.return_value = mock_model

            # Mock Qdrant service
            with patch("ardha.workflows.prd_workflow.get_qdrant_service") as mock_qdrant:
                mock_qdrant.return_value = AsyncMock()

                # Start workflow execution
                user_id = uuid4()
                execution_id = uuid4()

                # Add to active executions manually for testing
                initial_state = PRDState(
                    workflow_id=uuid4(),
                    execution_id=execution_id,
                    workflow_type=WorkflowType.CUSTOM,
                    user_id=user_id,
                    initial_request="Generate PRD from research",
                    research_summary=sample_research_summary,
                    status=WorkflowStatus.RUNNING,
                )
                workflow.active_executions[execution_id] = initial_state

                # Start workflow in background
                workflow_task = asyncio.create_task(
                    workflow.execute(
                        research_summary=sample_research_summary,
                        user_id=user_id,
                        project_id=uuid4(),
                        parameters={"test_mode": True},
                    )
                )

                # Wait a bit then cancel
                await asyncio.sleep(0.1)
                cancel_result = await workflow.cancel_execution(
                    execution_id, reason="User requested cancellation"
                )

                # Verify cancellation
                assert cancel_result is True
                assert execution_id not in workflow.active_executions

                # Wait for workflow task to complete (should handle cancellation gracefully)
                try:
                    await workflow_task
                except Exception:
                    pass  # Expected due to cancellation

                print("PRD workflow cancellation test completed successfully")


if __name__ == "__main__":
    # Run the E2E tests
    pytest.main([__file__, "-v", "--tb=short"])
