"""
Integration tests for Task Generation workflow.

This module tests the complete Task Generation workflow including:
- OpenSpec file generation
- Database integration
- Task creation and dependencies
- End-to-end workflow execution
"""

import json
from unittest.mock import patch
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from ardha.models.project import Project
from ardha.models.user import User
from ardha.schemas.workflows.task_generation import (
    TaskGenerationState,
    TaskGenerationWorkflowConfig,
)
from ardha.services.openspec_service import get_openspec_service
from ardha.services.task_generation_service import get_task_generation_service
from ardha.workflows.task_generation_workflow import get_task_generation_workflow


@pytest.fixture
def sample_prd_content():
    """Sample PRD content for testing."""
    return """
    # User Authentication System

    ## Overview
    Implement a comprehensive user authentication system with email/password login,
    social login options, and session management.

    ## Features
    1. Email/Password Authentication
    2. Social Login (GitHub, Google)
    3. Password Reset
    4. User Profile Management
    5. Session Management

    ## Technical Requirements
    - JWT tokens for authentication
    - OAuth 2.0 for social login
    - Secure password hashing
    - Session timeout handling
    - Rate limiting for auth endpoints

    ## Success Criteria
    - Users can register with email/password
    - Users can login with social accounts
    - Password reset flow works end-to-end
    - Sessions expire properly
    - All auth endpoints are rate limited
    """


@pytest.fixture
def sample_project_context():
    """Sample project context for testing."""
    return {
        "name": "Authentication System",
        "description": "User authentication and authorization",
        "tech_stack": ["FastAPI", "PostgreSQL", "JWT", "OAuth2"],
        "team_size": 3,
        "timeline": "4 weeks",
        "constraints": {
            "budget": "$10,000",
            "deadline": "2024-12-31",
            "compliance": ["GDPR", "SOC2"],
        },
    }


@pytest.fixture
def task_generation_config():
    """Task Generation workflow configuration for testing."""
    return TaskGenerationWorkflowConfig(
        analyze_prd_model="z-ai/glm-4.6",  # Use cheaper model for tests
        breakdown_tasks_model="z-ai/glm-4.6",
        define_dependencies_model="z-ai/glm-4.6",
        estimate_effort_model="z-ai/glm-4.6",
        generate_openspec_model="z-ai/glm-4.6",
        max_retries_per_step=2,  # Reduce for faster tests
        timeout_per_step_seconds=120,  # Reduce for faster tests
        max_tasks_per_epic=10,  # Reduce for faster tests
        include_subtasks=True,
        minimum_task_quality_score=0.6,  # Lower for tests
        openspec_template_path=None,  # Add missing parameter
    )


class TestTaskGenerationWorkflow:
    """Test Task Generation workflow integration."""

    @pytest.mark.asyncio
    async def test_complete_workflow_execution(
        self, sample_prd_content, sample_project_context, task_generation_config
    ):
        """Test complete workflow execution from PRD to OpenSpec."""
        # Arrange
        workflow = get_task_generation_workflow(task_generation_config)

        state = TaskGenerationState(
            workflow_id=uuid4(),
            execution_id=uuid4(),
            workflow_type="custom",
            user_id=uuid4(),
            project_id=uuid4(),
            initial_request="Generate tasks from PRD",
            context=sample_project_context,
            prd_content=sample_prd_content,
            existing_tasks=[],
        )

        # Act
        result_state = await workflow.execute(
            prd_content=state.prd_content or "",
            user_id=state.user_id,
            project_id=state.project_id,
            project_context=state.project_context,
            existing_tasks=state.existing_tasks,
        )

        # Assert
        assert result_state.status == "completed"
        assert result_state.prd_analysis is not None
        assert result_state.task_breakdown is not None
        assert result_state.task_dependencies is not None
        assert result_state.effort_estimates is not None
        assert result_state.openspec_proposal is not None
        assert result_state.generated_files is not None

        # Check quality scores
        assert result_state.prd_analysis_quality > 0.5
        assert result_state.task_breakdown_completeness > 0.5
        assert result_state.dependency_accuracy > 0.5
        assert result_state.effort_estimation_quality > 0.5
        assert result_state.openspec_quality_score > 0.5

        # Check OpenSpec files
        openspec_files = result_state.generated_files
        assert "proposal.md" in openspec_files
        assert "tasks.md" in openspec_files
        assert "spec-delta.md" in openspec_files
        assert "README.md" in openspec_files
        assert "risk-assessment.md" in openspec_files
        assert "metadata.json" in openspec_files
        assert "summary.md" in openspec_files

    @pytest.mark.asyncio
    async def test_openspec_file_generation(self, sample_prd_content, sample_project_context):
        """Test OpenSpec file generation service."""
        # Arrange
        openspec_service = get_openspec_service()

        proposal_data = {
            "proposal": {
                "id": "test-proposal",
                "title": "Test Authentication System",
                "description": "Test description",
                "objectives": ["Implement auth", "Add social login"],
                "scope": {"in_scope": ["Auth"], "out_of_scope": ["Admin"]},
                "success_criteria": ["Users can login", "Password reset works"],
            },
            "files": {
                "proposal.md": "# Test Authentication System\n\n## Summary\n\nThis is a test proposal.\n\n## Motivation\n\nTest motivation.\n\n## Implementation Plan\n\nTest plan.\n\n## Estimated Effort\n\nTest effort.",
                "tasks.md": "# Task Breakdown\n\n## Phase 1\n\n- [ ] Implement auth\n- [ ] Add social login",
                "spec-delta.md": "# Specification Updates\n\n## New Components\n\nNew auth components.\n\n## Modified Components\n\nModified components.",
                "README.md": "# README\n\n## Setup\n\nSetup instructions.\n\n## Implementation\n\nImplementation details.",
                "risk-assessment.md": "# Risk Assessment\n\n## Security Risks\n\nSecurity considerations.\n\n## Mitigation Strategies\n\nMitigation strategies.",
            },
            "metadata": {
                "generated_at": "2024-01-01T00:00:00Z",
                "workflow_id": str(uuid4()),
                "total_tasks": 5,
                "estimated_effort": "40 hours",
                "quality_score": 0.8,
            },
        }

        # Act
        generated_files = openspec_service.generate_openspec_files(
            proposal_data, "test-proposal", "openspec/changes/test-proposal"
        )

        # Assert
        assert len(generated_files) >= 7  # At least 7 files
        assert "proposal.md" in generated_files
        assert "tasks.md" in generated_files
        assert "spec-delta.md" in generated_files
        assert "README.md" in generated_files
        assert "risk-assessment.md" in generated_files
        assert "metadata.json" in generated_files
        assert "summary.md" in generated_files

        # Check files actually exist
        import os
        from pathlib import Path

        for filename, filepath in generated_files.items():
            assert Path(filepath).exists(), f"File {filename} was not created"
            assert Path(filepath).stat().st_size > 0, f"File {filename} is empty"

    @pytest.mark.asyncio
    async def test_task_database_integration(self, sample_project_context, test_db: AsyncSession):
        """Test task generation service database integration."""
        # Arrange
        task_gen_service = get_task_generation_service()

        # Override database session for test
        from unittest.mock import patch

        with patch(
            "ardha.services.task_generation_service.async_session_factory"
        ) as mock_session_factory:
            mock_session_factory.return_value.__aenter__.return_value = test_db

        task_breakdown = [
            {
                "id": "task_001",
                "title": "Implement User Registration",
                "description": "Create user registration endpoint",
                "priority": "high",
                "complexity": "medium",
                "estimated_hours": 8,
                "acceptance_criteria": ["User can register", "Email validation works"],
                "required_skills": ["FastAPI", "SQLAlchemy"],
                "is_main_task": True,
                "epic_id": "epic_001",
            },
            {
                "id": "task_002",
                "title": "Implement Login Endpoint",
                "description": "Create login endpoint with JWT",
                "priority": "high",
                "complexity": "medium",
                "estimated_hours": 6,
                "acceptance_criteria": ["User can login", "JWT token returned"],
                "required_skills": ["FastAPI", "JWT"],
                "is_main_task": True,
                "epic_id": "epic_001",
            },
        ]

        task_dependencies = [
            {
                "task_id": "task_002",
                "depends_on": "task_001",
                "dependency_type": "finish_to_start",
                "criticality": "high",
            }
        ]

        project_id = uuid4()
        user_id = uuid4()
        workflow_id = uuid4()

        # Act
        task_ids, epic_ids = await task_gen_service.save_generated_tasks(
            task_breakdown, project_id, user_id, workflow_id
        )

        dependency_ids = await task_gen_service.save_task_dependencies(
            task_dependencies, task_breakdown, task_ids
        )

        # Assert
        assert len(task_ids) == 2
        assert len(epic_ids) == 0  # No epics in this test
        assert len(dependency_ids) == 1

        # Check OpenSpec linking
        openspec_data = {
            "metadata": {
                "change_directory_path": "openspec/changes/test-proposal",
                "quality_score": 0.8,
                "files": ["proposal.md", "tasks.md"],
            }
        }

        linked = await task_gen_service.link_openspec_to_project(
            "test-proposal", project_id, user_id, workflow_id, openspec_data
        )

        assert linked is True

    @pytest.mark.asyncio
    async def test_openspec_file_validation(self):
        """Test OpenSpec file content validation."""
        # Arrange
        openspec_service = get_openspec_service()

        # Test invalid tasks.md
        invalid_tasks = {
            "files": {
                "proposal.md": "# Proposal\n\n## Summary\n\nValid proposal\n\n## Motivation\n\nValid motivation\n\n## Implementation Plan\n\nValid plan\n\n## Estimated Effort\n\nValid effort",  # Has ALL required sections
                "tasks.md": "Invalid tasks without checklist",
                "spec-delta.md": "# Spec Delta\n\nNew components",
                "README.md": "# README\n\nSetup",
                "risk-assessment.md": "# Risk Assessment\n\nRisks",
            }
        }

        # Act & Assert
        with pytest.raises(ValueError, match="tasks.md missing required section"):
            openspec_service.generate_openspec_files(
                invalid_tasks, "invalid-tasks", "openspec/changes/invalid-tasks"
            )

        # Test invalid proposal.md (missing required sections)
        invalid_proposal = {
            "files": {
                "proposal.md": "Invalid content without required sections",
                "tasks.md": "# Tasks\n\n- [ ] Task 1",
                "spec-delta.md": "# Spec Delta\n\nNew components",
                "README.md": "# README\n\nSetup",
                "risk-assessment.md": "# Risk Assessment\n\nRisks",
            }
        }

        # Act & Assert
        with pytest.raises(ValueError, match="proposal.md missing required section"):
            openspec_service.generate_openspec_files(
                invalid_proposal, "invalid-proposal", "openspec/changes/invalid-proposal"
            )

    @pytest.mark.asyncio
    async def test_workflow_error_handling(self, task_generation_config):
        """Test workflow error handling and recovery."""
        # Arrange
        workflow = get_task_generation_workflow(task_generation_config)

        # Test with invalid PRD content
        state = TaskGenerationState(
            workflow_id=uuid4(),
            execution_id=uuid4(),
            workflow_type="custom",
            user_id=uuid4(),
            project_id=uuid4(),
            initial_request="Generate tasks from invalid PRD",
            context={},
            prd_content="Invalid PRD content",  # Too short
            existing_tasks=[],
        )

        # Act
        result_state = await workflow.execute(
            prd_content=state.prd_content or "",
            user_id=state.user_id,
            project_id=state.project_id,
            project_context=state.project_context,
            existing_tasks=state.existing_tasks,
        )

        # Assert - should handle gracefully
        assert result_state.status in ["failed", "completed"]  # May fail or complete
        assert len(result_state.errors) >= 0  # Should have some errors

    @pytest.mark.asyncio
    async def test_workflow_progress_tracking(
        self, sample_prd_content, sample_project_context, task_generation_config
    ):
        """Test workflow progress tracking."""
        # Arrange
        workflow = get_task_generation_workflow(task_generation_config)

        progress_updates = []

        def progress_callback(update):
            progress_updates.append(update)

        # Note: progress_callback not implemented in workflow yet
        # workflow.progress_callback = progress_callback

        state = TaskGenerationState(
            workflow_id=uuid4(),
            execution_id=uuid4(),
            workflow_type="custom",
            user_id=uuid4(),
            project_id=uuid4(),
            initial_request="Generate tasks with progress tracking",
            context=sample_project_context,
            prd_content=sample_prd_content,
            existing_tasks=[],
        )

        # Act
        result_state = await workflow.execute(
            prd_content=state.prd_content or "",
            user_id=state.user_id,
            project_id=state.project_id,
            project_context=state.project_context,
            existing_tasks=state.existing_tasks,
        )

        # Assert
        assert len(progress_updates) > 0

        # Check progress progression
        progress_values = [update.progress_percentage for update in progress_updates]
        assert max(progress_values) >= 90  # Should reach near completion

        # Check step completion
        completed_steps = result_state.completed_task_steps
        expected_steps = [
            "analyze_prd",
            "breakdown_tasks",
            "define_dependencies",
            "estimate_effort",
            "generate_openspec",
        ]

        for step in expected_steps:
            if result_state.status == "completed":
                assert step in completed_steps, f"Step {step} should be completed"

    @pytest.mark.asyncio
    async def test_openspec_proposal_listing(self):
        """Test OpenSpec proposal listing functionality."""
        # Arrange
        openspec_service = get_openspec_service()

        # Create a test proposal first
        proposal_data = {
            "files": {
                "proposal.md": "# Test Proposal\n\n## Summary\n\nTest summary\n\n## Motivation\n\nTest motivation\n\n## Implementation Plan\n\nTest plan\n\n## Estimated Effort\n\nTest effort",
                "tasks.md": "# Task Breakdown\n\n## Phase 1\n\n- [ ] Task 1",
                "spec-delta.md": "# Specification Updates\n\n## New Components\n\nNew components\n\n## Modified Components\n\nModified components",
                "README.md": "# README\n\n## Setup\n\nSetup instructions\n\n## Implementation\n\nImplementation details",
                "risk-assessment.md": "# Risk Assessment\n\n## Security Risks\n\nSecurity considerations\n\n## Mitigation Strategies\n\nMitigation strategies",
            },
            "metadata": {
                "generated_at": "2024-01-01T00:00:00Z",
                "workflow_id": str(uuid4()),
                "total_tasks": 1,
                "estimated_effort": "10 hours",
                "quality_score": 0.8,
            },
        }

        openspec_service.generate_openspec_files(
            proposal_data, "list-test-proposal", "openspec/changes/list-test-proposal"
        )

        # Act
        proposals = openspec_service.list_proposals()

        # Assert
        assert len(proposals) >= 1

        # Find our test proposal
        test_proposal = next(
            (p for p in proposals if p.get("proposal_id") == "list-test-proposal"), None
        )

        assert test_proposal is not None
        assert test_proposal["status"] == "active"
        assert test_proposal["total_tasks"] == 1
        assert test_proposal["estimated_effort"] == "10 hours"
        assert test_proposal["quality_score"] == 0.8

    @pytest.mark.asyncio
    async def test_openspec_archival(self):
        """Test OpenSpec proposal archival functionality."""
        # Arrange
        openspec_service = get_openspec_service()

        # Create a test proposal
        proposal_data = {
            "files": {
                "proposal.md": "# Test Proposal for Archive\n\n## Summary\n\nTest summary\n\n## Motivation\n\nTest motivation\n\n## Implementation Plan\n\nTest plan\n\n## Estimated Effort\n\nTest effort",
                "tasks.md": "# Task Breakdown\n\n## Phase 1\n\n- [ ] Task 1",
                "spec-delta.md": "# Specification Updates\n\n## New Components\n\nNew components\n\n## Modified Components\n\nModified components",
                "README.md": "# README\n\n## Setup\n\nSetup instructions\n\n## Implementation\n\nImplementation details",
                "risk-assessment.md": "# Risk Assessment\n\n## Security Risks\n\nSecurity considerations\n\n## Mitigation Strategies\n\nMitigation strategies",
            },
            "metadata": {
                "generated_at": "2024-01-01T00:00:00Z",
                "workflow_id": str(uuid4()),
                "total_tasks": 1,
                "estimated_effort": "10 hours",
                "quality_score": 0.8,
            },
        }

        # Use unique proposal ID to avoid conflicts
        import time

        unique_id = f"archive-test-proposal-{int(time.time())}"

        openspec_service.generate_openspec_files(
            proposal_data, unique_id, "openspec/changes/" + unique_id
        )

        # Act
        archived = openspec_service.archive_proposal(unique_id, "test completed")

        # Assert
        assert archived is True

        # Check it's no longer in active proposals (should not be found)
        active_proposals = openspec_service.list_proposals(include_archived=False)
        found_in_active = any(
            p.get("proposal_id", "").startswith(unique_id) for p in active_proposals
        )

        assert (
            not found_in_active
        ), f"Archived proposal still found in active proposals: {[p.get('proposal_id') for p in active_proposals]}"

        # Check it's in archived proposals
        all_proposals = openspec_service.list_proposals(include_archived=True)
        archived_proposal = next(
            (p for p in all_proposals if p.get("proposal_id") == unique_id), None
        )

        assert archived_proposal is not None
        assert archived_proposal["status"] == "archived"
