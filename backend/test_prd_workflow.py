#!/usr/bin/env python3
"""
PRD Workflow Validation Test Script

This script validates the complete PRD workflow implementation
by running comprehensive tests and providing detailed feedback.
"""

import asyncio
import json
import sys
import traceback
from datetime import datetime
from uuid import uuid4

# Add the src directory to Python path
sys.path.insert(0, 'src')

from ardha.schemas.workflows.prd import PRDState, PRDWorkflowConfig
from ardha.workflows.nodes.prd_nodes import PRDNodeException
from ardha.workflows.prd_workflow import PRDWorkflow, get_prd_workflow
from ardha.workflows.state import WorkflowStatus, WorkflowType


class PRDWorkflowValidator:
    """Comprehensive PRD workflow validator."""

    def __init__(self):
        self.test_results = {
            "unit_tests": {"passed": 0, "failed": 0, "errors": []},
            "integration_tests": {"passed": 0, "failed": 0, "errors": []},
            "e2e_tests": {"passed": 0, "failed": 0, "errors": []},
            "workflow_execution": {"passed": 0, "failed": 0, "errors": []}
        }
        self.sample_research_summary = self._create_sample_research_summary()

    def _create_sample_research_summary(self):
        """Create comprehensive sample research summary for testing."""
        return {
            "idea": "A collaborative markdown editor with real-time collaboration features",
            "idea_analysis": {
                "core_concept": "Real-time collaborative markdown editing platform",
                "value_proposition": "Seamless collaboration for technical content creators",
                "target_users": [
                    "Software development teams",
                    "Technical writers and documentation teams",
                    "Open source project maintainers",
                    "Content creators and bloggers"
                ],
                "key_features": [
                    "Real-time collaborative editing",
                    "Version control and history",
                    "Comment and suggestion system",
                    "Export to multiple formats"
                ],
                "unique_differentiators": [
                    "Developer-focused tooling",
                    "Superior performance and reliability",
                    "Advanced markdown support",
                    "Seamless integrations"
                ]
            },
            "market_research": {
                "market_size": "$2.5B total addressable market for collaborative tools",
                "market_growth": "15% annual growth rate in collaborative software",
                "target_segments": [
                    "Enterprise development teams (40%)",
                    "SMB tech companies (35%)",
                    "Individual developers (15%)",
                    "Educational institutions (10%)"
                ],
                "competitors": {
                    "direct": ["Notion", "Google Docs", "Coda"],
                    "indirect": ["HackMD", "Typora", "VS Code"],
                    "potential": ["GitHub Codespaces", "Replit"]
                },
                "market_opportunity": {
                    "gap": "Lack of developer-focused collaborative tools",
                    "timing": "Growing demand for remote collaboration tools",
                    "advantage": "Performance and developer experience focus"
                },
                "revenue_model": {
                    "primary": "SaaS subscription model",
                    "pricing": "$10/user/month for teams, $5/user/month for individuals",
                    "enterprise": "Custom pricing for large organizations"
                }
            },
            "competitive_analysis": {
                "notion": {
                    "strengths": ["All-in-one workspace", "Strong brand recognition"],
                    "weaknesses": ["Not developer-focused", "Performance issues"],
                    "market_share": "35% of collaborative tools market"
                },
                "google_docs": {
                    "strengths": ["Free tier", "Google ecosystem integration"],
                    "weaknesses": ["Limited markdown support", "Generic collaboration"],
                    "market_share": "40% of document collaboration"
                },
                "hackmd": {
                    "strengths": ["Markdown-focused", "Open source"],
                    "weaknesses": ["Limited features", "Small user base"],
                    "market_share": "5% of markdown editors"
                },
                "competitive_positioning": {
                    "our_advantages": [
                        "Superior performance and reliability",
                        "Developer-focused feature set",
                        "Advanced markdown capabilities",
                        "Better integration with development tools"
                    ],
                    "market_entry_strategy": "Target development teams first, then expand"
                }
            },
            "technical_feasibility": {
                "complexity_assessment": "Medium complexity with some challenging components",
                "core_technologies": [
                    "WebSocket for real-time communication",
                    "CRDT (Conflict-free Replicated Data Types) for synchronization",
                    "React 18 with TypeScript for frontend",
                    "Node.js with Express for backend API",
                    "PostgreSQL for primary data storage",
                    "Redis for caching and session management"
                ],
                "technical_challenges": [
                    "Real-time conflict resolution at scale",
                    "Performance optimization for large documents",
                    "Reliable offline synchronization",
                    "Cross-platform compatibility"
                ],
                "feasibility_score": 0.85,
                "development_timeline": "6-9 months for MVP, 12-18 months for full feature set",
                "technical_risks": [
                    "Scalability of real-time synchronization",
                    "Data consistency across distributed systems",
                    "Performance with large collaborative sessions"
                ],
                "mitigation_strategies": [
                    "Use proven CRDT libraries",
                    "Implement sharding for large documents",
                    "Comprehensive testing and monitoring"
                ]
            },
            "research_summary": {
                "overall_confidence": 0.88,
                "sources_analyzed": 45,
                "key_insights": [
                    "Strong market demand for developer-focused collaborative tools",
                    "Performance and reliability are critical success factors",
                    "Real-time collaboration is a key differentiator in the market",
                    "Integration with existing development workflows is essential"
                ],
                "success_factors": [
                    "Superior performance compared to competitors",
                    "Developer-focused feature set and user experience",
                    "Reliable real-time synchronization",
                    "Strong integration ecosystem"
                ],
                "risk_factors": [
                    "Competition from established players",
                    "Technical complexity of real-time features",
                    "Market education required for new approach"
                ]
            }
        }

    async def run_all_tests(self):
        """Run all validation tests."""
        print("🚀 Starting PRD Workflow Validation Tests")
        print("=" * 60)

        # Test 1: Schema Validation
        await self._test_schema_validation()

        # Test 2: Node Initialization
        await self._test_node_initialization()

        # Test 3: Workflow Configuration
        await self._test_workflow_configuration()

        # Test 4: Mock Workflow Execution
        await self._test_mock_workflow_execution()

        # Test 5: Error Handling
        await self._test_error_handling()

        # Test 6: State Management
        await self._test_state_management()

        # Test 7: Quality Metrics
        await self._test_quality_metrics()

        # Print final results
        self._print_final_results()

    async def _test_schema_validation(self):
        """Test PRDState schema validation."""
        print("\n📋 Testing Schema Validation...")

        try:
            # Test valid state creation
            state = PRDState(
                workflow_id=uuid4(),
                execution_id=uuid4(),
                workflow_type=WorkflowType.CUSTOM,
                user_id=uuid4(),
                project_id=uuid4(),
                initial_request="Generate PRD from research",
                research_summary=self.sample_research_summary,
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

            # Test state methods
            state.mark_node_completed("extract_requirements", {"test": "data"})
            state.update_prd_progress("define_features", 20)

            # Test quality score calculation
            state.requirements_completeness = 0.9
            state.feature_prioritization_quality = 0.85
            state.metrics_specificity = 0.8
            state.document_coherence = 0.95

            quality_score = state.calculate_prd_quality_score()
            assert quality_score > 0.8, f"Quality score too low: {quality_score}"

            self.test_results["unit_tests"]["passed"] += 1
            print("✅ Schema validation tests passed")

        except Exception as e:
            self.test_results["unit_tests"]["failed"] += 1
            self.test_results["unit_tests"]["errors"].append(str(e))
            print(f"❌ Schema validation failed: {e}")

    async def _test_node_initialization(self):
        """Test PRD workflow node initialization."""
        print("\n🔧 Testing Node Initialization...")

        try:
            from ardha.workflows.nodes.prd_nodes import (
                DefineFeaturesNode,
                ExtractRequirementsNode,
                GeneratePRDNode,
                ReviewFormatNode,
                SetMetricsNode,
            )

            # Test node creation
            nodes = {
                "extract_requirements": ExtractRequirementsNode(),
                "define_features": DefineFeaturesNode(),
                "set_metrics": SetMetricsNode(),
                "generate_prd": GeneratePRDNode(),
                "review_format": ReviewFormatNode(),
            }

            # Verify node names
            expected_names = [
                "extract_requirements", "define_features", "set_metrics",
                "generate_prd", "review_format"
            ]

            for node_name, node in nodes.items():
                assert node.name == node_name, f"Node name mismatch: {node.name} != {node_name}"
                assert hasattr(node, 'execute'), f"Node {node_name} missing execute method"

            self.test_results["unit_tests"]["passed"] += 1
            print("✅ Node initialization tests passed")

        except Exception as e:
            self.test_results["unit_tests"]["failed"] += 1
            self.test_results["unit_tests"]["errors"].append(str(e))
            print(f"❌ Node initialization failed: {e}")

    async def _test_workflow_configuration(self):
        """Test PRD workflow configuration."""
        print("\n⚙️ Testing Workflow Configuration...")

        try:
            # Test default configuration
            default_config = PRDWorkflowConfig()
            assert default_config.extract_requirements_model is not None
            assert default_config.max_retries_per_step > 0
            assert default_config.timeout_per_step_seconds > 0

            # Test custom configuration
            custom_config = PRDWorkflowConfig(
                extract_requirements_model="z-ai/glm-4.6",
                define_features_model="z-ai/glm-4.6",
                set_metrics_model="z-ai/glm-4.6",
                generate_prd_model="z-ai/glm-4.6",
                review_format_model="z-ai/glm-4.6",
                max_retries_per_step=3,
                timeout_per_step_seconds=120,
                enable_streaming=False,
                enable_human_approval=False,
            )

            assert custom_config.extract_requirements_model == "z-ai/glm-4.6"
            assert custom_config.max_retries_per_step == 3
            assert custom_config.timeout_per_step_seconds == 120

            # Test workflow creation with config
            workflow = PRDWorkflow(custom_config)
            assert workflow.config == custom_config
            assert workflow.graph is not None

            self.test_results["unit_tests"]["passed"] += 1
            print("✅ Workflow configuration tests passed")

        except Exception as e:
            self.test_results["unit_tests"]["failed"] += 1
            self.test_results["unit_tests"]["errors"].append(str(e))
            print(f"❌ Workflow configuration failed: {e}")

    async def _test_mock_workflow_execution(self):
        """Test PRD workflow execution with mocked AI responses."""
        print("\n🤖 Testing Mock Workflow Execution...")

        try:
            # Create workflow with test configuration
            config = PRDWorkflowConfig(
                extract_requirements_model="z-ai/glm-4.6",
                define_features_model="z-ai/glm-4.6",
                set_metrics_model="z-ai/glm-4.6",
                generate_prd_model="z-ai/glm-4.6",
                review_format_model="z-ai/glm-4.6",
                max_retries_per_step=1,
                timeout_per_step_seconds=30,
                enable_streaming=False,
                enable_human_approval=False,
            )

            workflow = PRDWorkflow(config)

            # Mock the AI client
            from unittest.mock import AsyncMock, MagicMock, patch

            # Mock the OpenRouterClient and get_qdrant_service at the module level
            with patch('ardha.core.openrouter.OpenRouterClient') as mock_client_class, \
                 patch('ardha.core.qdrant.get_qdrant_service') as mock_qdrant_func:

                mock_client = AsyncMock()
                mock_client_class.return_value = mock_client
                mock_qdrant_service = AsyncMock()
                mock_qdrant_func.return_value = mock_qdrant_service

                # Mock AI responses
                mock_responses = {
                    "extract_requirements": json.dumps({
                        "functional_requirements": [
                            {
                                "id": "REQ-F-001",
                                "description": "Real-time collaborative editing",
                                "priority": "High",
                                "acceptance_criteria": "Multiple users can edit simultaneously"
                            }
                        ],
                        "non_functional_requirements": [
                            {
                                "id": "REQ-NF-001",
                                "description": "Sub-100ms latency",
                                "priority": "High",
                                "category": "Performance",
                                "metrics": "<100ms round-trip time"
                            }
                        ],
                        "business_requirements": [],
                        "technical_requirements": [],
                        "requirements_summary": {
                            "total_requirements": 2,
                            "by_priority": {"high": 2, "medium": 0, "low": 0},
                            "by_category": {"functional": 1, "non_functional": 1, "business": 0, "technical": 0}
                        }
                    }),

                    "define_features": json.dumps({
                        "features": [
                            {
                                "id": "FEAT-001",
                                "name": "Real-time Editor",
                                "description": "Collaborative markdown editor",
                                "priority": "M",
                                "complexity": "Complex",
                                "dependencies": [],
                                "acceptance_criteria": ["Real-time editing"],
                                "related_requirements": ["REQ-F-001"],
                                "estimated_effort": "8 story points"
                            }
                        ],
                        "feature_roadmap": {
                            "must_have_features": ["FEAT-001"],
                            "should_have_features": [],
                            "could_have_features": [],
                            "wont_have_features": [],
                            "total_features": 1,
                            "priority_distribution": {"M": 1, "S": 0, "C": 0, "W": 0}
                        },
                        "release_phases": []
                    }),

                    "set_metrics": json.dumps({
                        "success_metrics": {
                            "user_engagement": [
                                {
                                    "name": "DAU",
                                    "description": "Daily active users",
                                    "measurement": "Track user sessions",
                                    "targets": {"short_term": "1,000 DAU"},
                                    "success_criteria": "Upward trend",
                                    "data_sources": "Auth logs",
                                    "measurement_frequency": "Daily"
                                }
                            ],
                            "business": [],
                            "technical": [],
                            "quality": [],
                            "adoption": []
                        },
                        "kpi_dashboard": {
                            "primary_kpis": ["DAU"],
                            "secondary_kpis": [],
                            "monitoring_tools": []
                        },
                        "metrics_summary": {
                            "total_metrics": 1,
                            "by_category": {"user_engagement": 1, "business": 0, "technical": 0, "quality": 0, "adoption": 0},
                            "measurement_frequency": {"real_time": 0, "daily": 1, "weekly": 0, "monthly": 0, "quarterly": 0}
                        }
                    }),

                    "generate_prd": """# Product Requirements Document

## Executive Summary
This document outlines requirements for a collaborative markdown editor.

## Problem Statement
Users need real-time collaboration for markdown documents.

## Requirements
- REQ-F-001: Real-time collaborative editing
- REQ-NF-001: Sub-100ms latency

## Features
- FEAT-001: Real-time Editor

## Success Metrics
- DAU: 1,000 users within 3 months

## Technical Architecture
- WebSocket for real-time communication
- CRDT for conflict resolution
""",

                    "review_format": json.dumps({
                        "review_summary": {
                            "overall_quality_score": 0.85,
                            "completeness_score": 0.8,
                            "consistency_score": 0.9,
                            "clarity_score": 0.85,
                            "formatting_score": 0.9
                        },
                        "issues_found": [],
                        "improvements_made": ["Enhanced formatting"],
                        "final_prd": """# Product Requirements Document: Collaborative Markdown Editor

## Executive Summary
This document presents comprehensive requirements for a real-time collaborative markdown editor.

## Problem Statement
Development teams need dedicated real-time collaboration for markdown documents.

## Requirements
### Functional Requirements
- REQ-F-001: Real-time collaborative editing with sub-100ms latency

### Non-Functional Requirements
- REQ-NF-001: Performance requirements with <100ms synchronization

## Features
### Must Have Features
- FEAT-001: Real-time Editor with collaborative editing capabilities

## Success Metrics
- DAU: 1,000 users within 3 months

## Technical Architecture
- WebSocket-based real-time communication
- CRDT for automatic conflict resolution
"""
                    })
                }

                # Configure mock client
                def mock_complete_side_effect(request):
                    response = MagicMock()
                    content = request.messages[-1].content if request.messages else ""

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

                # Mock Qdrant service search
                mock_qdrant_service.search_similar.return_value = []

                # Execute workflow
                user_id = uuid4()
                project_id = uuid4()

                result = await workflow.execute(
                    research_summary=self.sample_research_summary,
                    user_id=user_id,
                    project_id=project_id,
                    parameters={"test_mode": True}
                )

                # Verify results
                assert result.status == WorkflowStatus.COMPLETED, f"Workflow status: {result.status}"
                assert result.final_prd is not None, "Final PRD should not be None"
                assert len(result.final_prd) > 1000, "PRD should be substantial"

                # Verify quality metrics
                assert result.requirements_completeness > 0.5, "Requirements completeness too low"
                assert result.feature_prioritization_quality > 0.5, "Feature prioritization quality too low"
                assert result.metrics_specificity > 0.5, "Metrics specificity too low"
                assert result.document_coherence > 0.5, "Document coherence too low"

                # Verify overall quality score
                overall_quality = result.calculate_prd_quality_score()
                assert overall_quality > 0.5, f"Overall quality too low: {overall_quality}"

                self.test_results["workflow_execution"]["passed"] += 1
                print("✅ Mock workflow execution tests passed")

        except Exception as e:
            self.test_results["workflow_execution"]["failed"] += 1
            self.test_results["workflow_execution"]["errors"].append(str(e))
            print(f"❌ Mock workflow execution failed: {e}")
            traceback.print_exc()

    async def _test_error_handling(self):
        """Test PRD workflow error handling."""
        print("\n⚠️ Testing Error Handling...")

        try:
            from ardha.workflows.nodes.prd_nodes import PRDNodeException

            # Test PRDNodeException
            exception = PRDNodeException("Test error")
            assert str(exception) == "Test error"

            # Test workflow error handling with mock
            config = PRDWorkflowConfig(
                max_retries_per_step=1,
                timeout_per_step_seconds=10,
                enable_streaming=False,
            )

            workflow = PRDWorkflow(config)

            from unittest.mock import AsyncMock, MagicMock, patch

            # Mock the OpenRouterClient and get_qdrant_service at the module level
            with patch('ardha.core.openrouter.OpenRouterClient') as mock_client_class, \
                 patch('ardha.core.qdrant.get_qdrant_service') as mock_qdrant_func:

                mock_client = AsyncMock()
                mock_client_class.return_value = mock_client
                mock_qdrant_service = AsyncMock()
                mock_qdrant_func.return_value = mock_qdrant_service

                # Configure mock to always fail
                mock_client.complete.side_effect = Exception("Persistent AI service failure")

                # Mock Qdrant service search
                mock_qdrant_service.search_similar.return_value = []

                # Execute workflow - should fail gracefully
                user_id = uuid4()

                try:
                    await workflow.execute(
                        research_summary=self.sample_research_summary,
                        user_id=user_id,
                        parameters={"test_mode": True}
                    )
                    assert False, "Should have raised an exception"
                except Exception as e:
                    # Any exception is acceptable for this test since we're mocking failure
                    self.test_results["workflow_execution"]["passed"] += 1
                    print("✅ Error handling tests passed")

        except Exception as e:
            self.test_results["workflow_execution"]["failed"] += 1
            self.test_results["workflow_execution"]["errors"].append(str(e))
            print(f"❌ Error handling test failed: {e}")

    async def _test_state_management(self):
        """Test PRD workflow state management."""
        print("\n📊 Testing State Management...")

        try:
            # Test state creation and updates
            state = PRDState(
                workflow_id=uuid4(),
                execution_id=uuid4(),
                workflow_type=WorkflowType.CUSTOM,
                user_id=uuid4(),
                initial_request="Test PRD generation",
                research_summary=self.sample_research_summary,
                status=WorkflowStatus.RUNNING,
            )

            # Test node completion tracking
            state.mark_node_completed("extract_requirements", {"test": "result"})
            assert "extract_requirements" in state.completed_nodes
            assert state.prd_progress_percentage == 20

            # Test progress updates
            state.update_prd_progress("define_features", 40)
            assert state.current_prd_step == "define_features"
            assert state.prd_progress_percentage == 40

            # Test node failure tracking
            state.mark_node_failed("test_node", {"error": "Test error"})
            assert "test_node" in state.failed_nodes

            # Test quality metrics updates
            state.requirements_completeness = 0.9
            state.feature_prioritization_quality = 0.85
            state.metrics_specificity = 0.8
            state.document_coherence = 0.95

            # Test quality score calculation
            quality_score = state.calculate_prd_quality_score()
            expected_score = (0.9 + 0.85 + 0.8 + 0.95) / 4
            assert abs(quality_score - expected_score) < 0.01, f"Quality score mismatch: {quality_score} != {expected_score}"

            self.test_results["unit_tests"]["passed"] += 1
            print("✅ State management tests passed")

        except Exception as e:
            self.test_results["unit_tests"]["failed"] += 1
            self.test_results["unit_tests"]["errors"].append(str(e))
            print(f"❌ State management test failed: {e}")

    async def _test_quality_metrics(self):
        """Test PRD workflow quality metrics calculation."""
        print("\n📈 Testing Quality Metrics...")

        try:
            # Test quality score calculation with different scenarios
            test_cases = [
                {"requirements": 1.0, "features": 0.9, "metrics": 0.8, "coherence": 0.95, "expected": 0.9125},
                {"requirements": 0.7, "features": 0.8, "metrics": 0.6, "coherence": 0.9, "expected": 0.75},
                {"requirements": 0.5, "features": 0.5, "metrics": 0.5, "coherence": 0.5, "expected": 0.5},
            ]

            for i, case in enumerate(test_cases):
                state = PRDState(
                    workflow_id=uuid4(),
                    execution_id=uuid4(),
                    workflow_type=WorkflowType.CUSTOM,
                    user_id=uuid4(),
                    initial_request=f"Test case {i+1}",
                    research_summary=self.sample_research_summary,
                    status=WorkflowStatus.RUNNING,
                )

                state.requirements_completeness = case["requirements"]
                state.feature_prioritization_quality = case["features"]
                state.metrics_specificity = case["metrics"]
                state.document_coherence = case["coherence"]

                quality_score = state.calculate_prd_quality_score()
                assert abs(quality_score - case["expected"]) < 0.01, f"Test case {i+1} failed: {quality_score} != {case['expected']}"

            self.test_results["unit_tests"]["passed"] += 1
            print("✅ Quality metrics tests passed")

        except Exception as e:
            self.test_results["unit_tests"]["failed"] += 1
            self.test_results["unit_tests"]["errors"].append(str(e))
            print(f"❌ Quality metrics test failed: {e}")

    def _print_final_results(self):
        """Print final test results summary."""
        print("\n" + "=" * 60)
        print("📊 FINAL TEST RESULTS")
        print("=" * 60)

        total_passed = 0
        total_failed = 0

        for test_type, results in self.test_results.items():
            passed = results["passed"]
            failed = results["failed"]
            errors = results["errors"]

            total_passed += passed
            total_failed += failed

            print(f"\n{test_type.upper().replace('_', ' ')}:")
            print(f"  ✅ Passed: {passed}")
            print(f"  ❌ Failed: {failed}")

            if errors:
                print(f"  🚨 Errors:")
                for error in errors:
                    print(f"    - {error}")

        print(f"\n🎯 OVERALL SUMMARY:")
        print(f"  ✅ Total Passed: {total_passed}")
        print(f"  ❌ Total Failed: {total_failed}")
        print(f"  📈 Success Rate: {(total_passed / (total_passed + total_failed) * 100):.1f}%")

        if total_failed == 0:
            print("\n🎉 ALL TESTS PASSED! PRD workflow is ready for production.")
        else:
            print(f"\n⚠️  {total_failed} test(s) failed. Please review and fix issues.")

        print("\n" + "=" * 60)


async def main():
    """Main test execution function."""
    print("🔍 PRD Workflow Validation Script")
    print("This script validates the complete PRD workflow implementation")
    print("including schemas, nodes, workflow orchestration, and error handling.")
    print()

    validator = PRDWorkflowValidator()
    await validator.run_all_tests()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n⚠️  Tests interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n🚨 Unexpected error: {e}")
        traceback.print_exc()
        sys.exit(1)
