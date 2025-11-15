"""
Task Generation workflow nodes.

This module implements the specialized nodes for the Task Generation workflow
that creates OpenSpec proposals and task breakdowns from PRD documents.
"""

import json
import logging
from datetime import datetime
from typing import TYPE_CHECKING, Any, Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel

from .base import BaseNode

if TYPE_CHECKING:
    from ...schemas.workflows.task_generation import TaskGenerationState
    from ...workflows.state import WorkflowState


class TaskGenerationStepResult(BaseModel):
    """Result of a task generation workflow step."""

    step_name: str
    success: bool
    result_data: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None
    confidence_score: Optional[float] = None
    tokens_used: Optional[int] = None
    cost_incurred: Optional[float] = None
    timestamp: str

    class Config:
        populate_by_name = True


logger = logging.getLogger(__name__)


class TaskGenerationNodeException(Exception):
    """Exception raised by task generation nodes."""

    pass


class AnalyzePRDNode(BaseNode):
    """
    Node for analyzing PRD content and extracting key information.

    This node processes the PRD document to identify features, requirements,
    technical constraints, and project scope for task generation.
    """

    def __init__(self):
        super().__init__("analyze_prd")

    async def execute(
        self,
        state: "WorkflowState",
        context,
    ) -> Dict[str, Any]:
        """
        Analyze PRD content and extract key information.

        Args:
            state: TaskGenerationState
            context: WorkflowContext

        Returns:
            Analysis results with features, requirements, and constraints
        """
        try:
            self.logger.info("Starting PRD analysis")

            # Get relevant context from memory
            relevant_context = await self._get_relevant_context(
                f"PRD analysis for {state.project_id}" if state.project_id else "PRD analysis",
                context,
                state,
                limit=5,
            )

            # Prepare AI prompt
            system_prompt = """You are an expert project analyst and technical architect.
            Analyze the provided PRD document and extract structured information for task generation.

            Your analysis should include:
            1. Core features and functionality
            2. Technical requirements and constraints
            3. User stories and acceptance criteria
            4. Project scope and boundaries
            5. Risk factors and considerations
            6. Dependencies and integrations

            Format your response as JSON with the following structure:
            {
                "core_features": [{"name": "...", "description": "...", "priority": "..."}],
                "technical_requirements": [{"type": "...", "description": "...", "complexity": "..."}],
                "user_stories": [{"as_a": "...", "i_want": "...", "so_that": "...", "acceptance_criteria": [...]}],
                "project_scope": {"in_scope": [...], "out_of_scope": [...]},
                "risk_factors": [{"risk": "...", "impact": "...", "mitigation": "..."}],
                "dependencies": [{"type": "...", "description": "...", "critical": "..."}],
                "complexity_assessment": {"overall": "...", "technical": "...", "business": "..."},
                "estimated_phases": [{"phase": "...", "description": "...", "key_deliverables": [...]}]
            }"""

            user_prompt = f"""Analyze this PRD document for task generation:

            PRD Content:
            {getattr(state, 'prd_content', '')}

            Project Context:
            {json.dumps(getattr(state, 'project_context', {}), indent=2)}

            Existing Tasks:
            {json.dumps(getattr(state, 'existing_tasks', []), indent=2)}

            Provide comprehensive analysis in JSON format."""

            # Call AI
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ]

            model = context.settings.get("analyze_prd_model", "anthropic/claude-sonnet-4.5")
            response = await self._call_ai(messages, model, context, state, temperature=0.3)

            # Parse JSON response
            try:
                analysis_data = json.loads(response)
            except json.JSONDecodeError:
                # Fallback: extract JSON from response
                import re

                json_match = re.search(r"\{.*\}", response, re.DOTALL)
                if json_match:
                    analysis_data = json.loads(json_match.group())
                else:
                    raise TaskGenerationNodeException("Failed to parse AI response as JSON")

            # Store analysis in state
            setattr(state, "prd_analysis", analysis_data)
            setattr(state, "prd_analysis_quality", self._calculate_analysis_quality(analysis_data))

            # Store in memory
            await self._store_memory(
                f"PRD Analysis: {len(analysis_data.get('core_features', []))} features identified",
                {
                    "node": self.node_name,
                    "workflow_id": str(state.workflow_id),
                    "analysis_summary": {
                        "features_count": len(analysis_data.get("core_features", [])),
                        "requirements_count": len(analysis_data.get("technical_requirements", [])),
                        "user_stories_count": len(analysis_data.get("user_stories", [])),
                        "complexity": analysis_data.get("complexity_assessment", {}).get(
                            "overall", "unknown"
                        ),
                    },
                },
                context,
                state,
                "chats",
            )

            # Create step result
            step_result = TaskGenerationStepResult(
                step_name=self.node_name,
                success=True,
                result_data=analysis_data,
                error_message=None,
                confidence_score=getattr(state, "prd_analysis_quality", 0.0),
                tokens_used=None,
                cost_incurred=None,
                timestamp=self._get_timestamp(),
            )

            if hasattr(state, "mark_task_step_completed"):
                getattr(state, "mark_task_step_completed")(self.node_name, step_result)
            if hasattr(state, "update_task_progress"):
                getattr(state, "update_task_progress")("breakdown_tasks", 20)

            self.logger.info(
                f"PRD analysis completed: {len(analysis_data.get('core_features', []))} features identified"
            )

            return {
                "analysis": analysis_data,
                "quality_score": getattr(state, "prd_analysis_quality", 0.0),
                "next_step": "breakdown_tasks",
            }

        except Exception as e:
            self.logger.error(f"PRD analysis failed: {e}")
            if hasattr(state, "mark_task_step_failed"):
                getattr(state, "mark_task_step_failed")(self.node_name, str(e))
            raise TaskGenerationNodeException(f"PRD analysis failed: {str(e)}") from e

    def _calculate_analysis_quality(self, analysis_data: Dict[str, Any]) -> float:
        """Calculate quality score for PRD analysis."""
        score = 0.0
        max_score = 7.0

        # Check for required sections
        if analysis_data.get("core_features"):
            score += 1.0
        if analysis_data.get("technical_requirements"):
            score += 1.0
        if analysis_data.get("user_stories"):
            score += 1.0
        if analysis_data.get("project_scope"):
            score += 1.0
        if analysis_data.get("risk_factors"):
            score += 1.0
        if analysis_data.get("dependencies"):
            score += 1.0
        if analysis_data.get("complexity_assessment"):
            score += 1.0

        return min(score / max_score, 1.0)


class BreakdownTasksNode(BaseNode):
    """
    Node for breaking down features into actionable tasks.

    This node takes the analyzed PRD and creates a comprehensive task breakdown
    with epics, main tasks, and subtasks.
    """

    def __init__(self):
        super().__init__("breakdown_tasks")

    async def execute(
        self,
        state: "WorkflowState",
        context,
    ) -> Dict[str, Any]:
        """
        Break down features into actionable tasks.

        Args:
            state: TaskGenerationState
            context: WorkflowContext

        Returns:
            Task breakdown with epics, tasks, and subtasks
        """
        try:
            self.logger.info("Starting task breakdown")

            # Get relevant context
            relevant_context = await self._get_relevant_context(
                f"Task breakdown for {state.project_id}" if state.project_id else "Task breakdown",
                context,
                state,
                limit=5,
            )

            # Prepare AI prompt
            system_prompt = """You are an expert project manager and technical lead.
            Break down the analyzed PRD features into actionable tasks with proper hierarchy.

            Create a task breakdown following this structure:
            1. Epics - Large feature areas
            2. Main Tasks - Specific deliverables within epics
            3. Subtasks - Detailed work items for main tasks

            For each task, include:
            - Clear, actionable title
            - Detailed description
            - Acceptance criteria
            - Estimated complexity (trivial, simple, medium, complex, very_complex)
            - Priority (urgent, high, medium, low)
            - Dependencies on other tasks
            - Required skills/roles

            Format your response as JSON:
            {
                "epics": [
                    {
                        "id": "epic_001",
                        "title": "...",
                        "description": "...",
                        "priority": "...",
                        "main_tasks": [
                            {
                                "id": "task_001",
                                "title": "...",
                                "description": "...",
                                "acceptance_criteria": [...],
                                "complexity": "...",
                                "priority": "...",
                                "estimated_hours": "...",
                                "dependencies": [...],
                                "required_skills": [...],
                                "subtasks": [
                                    {
                                        "id": "subtask_001",
                                        "title": "...",
                                        "description": "...",
                                        "complexity": "...",
                                        "estimated_hours": "...",
                                        "dependencies": [...]
                                    }
                                ]
                            }
                        ]
                    }
                ],
                "task_statistics": {
                    "total_tasks": "...",
                    "total_epics": "...",
                    "total_subtasks": "...",
                    "complexity_distribution": {...}
                }
            }"""

            user_prompt = f"""Break down these analyzed features into actionable tasks:

            PRD Analysis:
            {json.dumps(getattr(state, 'prd_analysis', {}), indent=2)}

            Project Context:
            {json.dumps(getattr(state, 'project_context', {}), indent=2)}

            Existing Tasks:
            {json.dumps(getattr(state, 'existing_tasks', []), indent=2)}

            Configuration:
            - Max tasks per epic: {context.settings.get('max_tasks_per_epic', 20)}
            - Include subtasks: {context.settings.get('include_subtasks', True)}
            - Detail level: {context.settings.get('min_task_detail_level', 'medium')}

            Create comprehensive task breakdown in JSON format."""

            # Call AI
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ]

            model = context.settings.get("breakdown_tasks_model", "anthropic/claude-sonnet-4.5")
            response = await self._call_ai(messages, model, context, state, temperature=0.4)

            # Parse JSON response
            try:
                breakdown_data = json.loads(response)
            except json.JSONDecodeError:
                import re

                json_match = re.search(r"\{.*\}", response, re.DOTALL)
                if json_match:
                    breakdown_data = json.loads(json_match.group())
                else:
                    raise TaskGenerationNodeException("Failed to parse AI response as JSON")

            # Flatten task structure for easier processing
            all_tasks = []
            epics = breakdown_data.get("epics", [])

            for epic in epics:
                epic["is_epic"] = True
                epic["epic_id"] = epic.get("id")
                all_tasks.append(epic)

                for main_task in epic.get("main_tasks", []):
                    main_task["is_main_task"] = True
                    main_task["epic_id"] = epic.get("id")
                    main_task["parent_epic"] = epic.get("title")
                    all_tasks.append(main_task)

                    for subtask in main_task.get("subtasks", []):
                        subtask["is_subtask"] = True
                        subtask["parent_task_id"] = main_task.get("id")
                        subtask["parent_task"] = main_task.get("title")
                        subtask["epic_id"] = epic.get("id")
                        all_tasks.append(subtask)

            # Store breakdown in state
            setattr(state, "task_breakdown", all_tasks)
            setattr(state, "epics_defined", epics)
            setattr(
                state,
                "task_breakdown_completeness",
                self._calculate_breakdown_quality(breakdown_data),
            )

            # Store in memory
            await self._store_memory(
                f"Task Breakdown: {len(all_tasks)} tasks created across {len(epics)} epics",
                {
                    "node": self.node_name,
                    "workflow_id": str(state.workflow_id),
                    "breakdown_summary": breakdown_data.get("task_statistics", {}),
                },
                context,
                state,
                "chats",
            )

            # Create step result
            step_result = TaskGenerationStepResult(
                step_name=self.node_name,
                success=True,
                result_data=breakdown_data,
                error_message=None,
                confidence_score=getattr(state, "task_breakdown_completeness", 0.0),
                tokens_used=None,
                cost_incurred=None,
                timestamp=self._get_timestamp(),
            )

            if hasattr(state, "mark_task_step_completed"):
                getattr(state, "mark_task_step_completed")(self.node_name, step_result)
            if hasattr(state, "update_task_progress"):
                getattr(state, "update_task_progress")("define_dependencies", 40)

            self.logger.info(
                f"Task breakdown completed: {len(all_tasks)} tasks across {len(epics)} epics"
            )

            return {
                "breakdown": breakdown_data,
                "all_tasks": all_tasks,
                "quality_score": getattr(state, "task_breakdown_completeness", 0.0),
                "next_step": "define_dependencies",
            }

        except Exception as e:
            self.logger.error(f"Task breakdown failed: {e}")
            if hasattr(state, "mark_task_step_failed"):
                getattr(state, "mark_task_step_failed")(self.node_name, str(e))
            raise TaskGenerationNodeException(f"Task breakdown failed: {str(e)}") from e

    def _calculate_breakdown_quality(self, breakdown_data: Dict[str, Any]) -> float:
        """Calculate quality score for task breakdown."""
        score = 0.0
        max_score = 6.0

        epics = breakdown_data.get("epics", [])

        # Check for proper structure
        if epics:
            score += 1.0

        # Check for main tasks
        has_main_tasks = any(epic.get("main_tasks") for epic in epics)
        if has_main_tasks:
            score += 1.0

        # Check for subtasks
        has_subtasks = any(
            task.get("subtasks") for epic in epics for task in epic.get("main_tasks", [])
        )
        if has_subtasks:
            score += 1.0

        # Check for task details
        has_details = all(
            task.get("title") and task.get("description") and task.get("acceptance_criteria")
            for epic in epics
            for task in epic.get("main_tasks", [])
        )
        if has_details:
            score += 1.0

        # Check for estimates
        has_estimates = any(
            task.get("estimated_hours") for epic in epics for task in epic.get("main_tasks", [])
        )
        if has_estimates:
            score += 1.0

        # Check for dependencies
        has_dependencies = any(
            task.get("dependencies") for epic in epics for task in epic.get("main_tasks", [])
        )
        if has_dependencies:
            score += 1.0

        return min(score / max_score, 1.0)


class DefineDependenciesNode(BaseNode):
    """
    Node for defining and analyzing task dependencies.

    This node creates a comprehensive dependency graph and identifies
    critical paths and potential bottlenecks.
    """

    def __init__(self):
        super().__init__("define_dependencies")

    async def execute(
        self,
        state: "WorkflowState",
        context,
    ) -> Dict[str, Any]:
        """
        Define and analyze task dependencies.

        Args:
            state: TaskGenerationState
            context: WorkflowContext

        Returns:
            Dependency graph and analysis
        """
        try:
            self.logger.info("Starting dependency definition")

            # Get relevant context
            relevant_context = await self._get_relevant_context(
                (
                    f"Dependency analysis for {state.project_id}"
                    if state.project_id
                    else "Dependency analysis"
                ),
                context,
                state,
                limit=3,
            )

            # Prepare AI prompt
            system_prompt = """You are an expert technical architect and project planner.
            Analyze the task breakdown and define comprehensive dependencies.

            Create dependency analysis including:
            1. Task dependency relationships
            2. Critical path identification
            3. Parallel execution opportunities
            4. Risk assessment for dependencies
            5. Resource allocation recommendations

            Format your response as JSON:
            {
                "dependencies": [
                    {
                        "task_id": "...",
                        "depends_on": [...],
                        "dependency_type": "...",
                        "criticality": "...",
                        "risk_level": "..."
                    }
                ],
                "dependency_graph": {
                    "nodes": [...],
                    "edges": [...],
                    "critical_path": [...]
                },
                "execution_phases": [
                    {
                        "phase": "...",
                        "tasks": [...],
                        "can_start_in_parallel": [...],
                        "blocking_tasks": [...]
                    }
                ],
                "risk_assessment": {
                    "high_risk_dependencies": [...],
                    "potential_bottlenecks": [...],
                    "mitigation_strategies": [...]
                },
                "resource_recommendations": {
                    "required_skills": [...],
                    "team_composition": [...],
                    "timeline_optimizations": [...]
                }
            }"""

            user_prompt = f"""Analyze dependencies for this task breakdown:

            Task Breakdown:
            {json.dumps(getattr(state, 'task_breakdown', []), indent=2)}

            PRD Analysis:
            {json.dumps(getattr(state, 'prd_analysis', {}), indent=2)}

            Project Context:
            {json.dumps(getattr(state, 'project_context', {}), indent=2)}

            Create comprehensive dependency analysis in JSON format."""

            # Call AI
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ]

            model = context.settings.get("define_dependencies_model", "anthropic/claude-sonnet-4.5")
            response = await self._call_ai(messages, model, context, state, temperature=0.3)

            # Parse JSON response
            try:
                dependency_data = json.loads(response)
            except json.JSONDecodeError:
                import re

                json_match = re.search(r"\{.*\}", response, re.DOTALL)
                if json_match:
                    dependency_data = json.loads(json_match.group())
                else:
                    raise TaskGenerationNodeException("Failed to parse AI response as JSON")

            # Store dependency data in state
            setattr(state, "task_dependencies", dependency_data.get("dependencies", []))
            setattr(state, "dependency_graph", dependency_data.get("dependency_graph", {}))
            setattr(
                state, "dependency_accuracy", self._calculate_dependency_quality(dependency_data)
            )

            # Store in memory
            await self._store_memory(
                f"Dependencies Defined: {len(getattr(state, 'task_dependencies', []))} task dependencies identified",
                {
                    "node": self.node_name,
                    "workflow_id": str(state.workflow_id),
                    "dependency_summary": {
                        "total_dependencies": len(getattr(state, "task_dependencies", [])),
                        "critical_path_length": len(
                            dependency_data.get("dependency_graph", {}).get("critical_path", [])
                        ),
                        "execution_phases": len(dependency_data.get("execution_phases", [])),
                    },
                },
                context,
                state,
                "chats",
            )

            # Create step result
            step_result = TaskGenerationStepResult(
                step_name=self.node_name,
                success=True,
                result_data=dependency_data,
                error_message=None,
                confidence_score=getattr(state, "dependency_accuracy", 0.0),
                tokens_used=None,
                cost_incurred=None,
                timestamp=self._get_timestamp(),
            )

            if hasattr(state, "mark_task_step_completed"):
                getattr(state, "mark_task_step_completed")(self.node_name, step_result)
            if hasattr(state, "update_task_progress"):
                getattr(state, "update_task_progress")("estimate_effort", 60)

            self.logger.info(
                f"Dependency definition completed: {len(getattr(state, 'task_dependencies', []))} dependencies identified"
            )

            return {
                "dependencies": dependency_data,
                "quality_score": getattr(state, "dependency_accuracy", 0.0),
                "next_step": "estimate_effort",
            }

        except Exception as e:
            self.logger.error(f"Dependency definition failed: {e}")
            if hasattr(state, "mark_task_step_failed"):
                getattr(state, "mark_task_step_failed")(self.node_name, str(e))
            raise TaskGenerationNodeException(f"Dependency definition failed: {str(e)}") from e

    def _calculate_dependency_quality(self, dependency_data: Dict[str, Any]) -> float:
        """Calculate quality score for dependency analysis."""
        score = 0.0
        max_score = 5.0

        # Check for dependencies
        if dependency_data.get("dependencies"):
            score += 1.0

        # Check for dependency graph
        if dependency_data.get("dependency_graph"):
            score += 1.0

        # Check for critical path
        if dependency_data.get("dependency_graph", {}).get("critical_path"):
            score += 1.0

        # Check for execution phases
        if dependency_data.get("execution_phases"):
            score += 1.0

        # Check for risk assessment
        if dependency_data.get("risk_assessment"):
            score += 1.0

        return min(score / max_score, 1.0)


class EstimateEffortNode(BaseNode):
    """
    Node for estimating effort and resource requirements.

    This node provides detailed time estimates, cost projections,
    and resource allocation recommendations.
    """

    def __init__(self):
        super().__init__("estimate_effort")

    async def execute(
        self,
        state: "WorkflowState",
        context,
    ) -> Dict[str, Any]:
        """
        Estimate effort and resource requirements.

        Args:
            state: TaskGenerationState
            context: WorkflowContext

        Returns:
            Effort estimates and resource allocation
        """
        try:
            self.logger.info("Starting effort estimation")

            # Get relevant context
            relevant_context = await self._get_relevant_context(
                (
                    f"Effort estimation for {state.project_id}"
                    if state.project_id
                    else "Effort estimation"
                ),
                context,
                state,
                limit=3,
            )

            # Prepare AI prompt
            system_prompt = """You are an expert project estimator and resource planner.
            Provide detailed effort estimates for all tasks based on complexity and dependencies.

            Create comprehensive effort estimation including:
            1. Time estimates for each task
            2. Cost projections based on team rates
            3. Resource allocation recommendations
            4. Timeline optimization opportunities
            5. Risk buffers and contingency planning

            Format your response as JSON:
            {
                "task_estimates": [
                    {
                        "task_id": "...",
                        "estimated_hours": "...",
                        "confidence_level": "...",
                        "skill_requirements": [...],
                        "cost_estimate": "...",
                        "risk_buffer": "..."
                    }
                ],
                "project_summary": {
                    "total_hours": "...",
                    "total_cost": "...",
                    "timeline_weeks": "...",
                    "team_size_recommended": "...",
                    "critical_path_duration": "..."
                },
                "resource_allocation": {
                    "required_roles": [...],
                    "skill_gaps": [...],
                    "hiring_recommendations": [...],
                    "training_needs": [...]
                },
                "timeline_optimization": {
                    "parallel_opportunities": [...],
                    "fast_track_options": [...],
                    "milestone_suggestions": [...]
                },
                "cost_breakdown": {
                    "development": "...",
                    "testing": "...",
                    "deployment": "...",
                    "management": "...",
                    "contingency": "..."
                }
            }"""

            user_prompt = f"""Estimate effort for this task breakdown:

            Task Breakdown:
            {json.dumps(getattr(state, 'task_breakdown', []), indent=2)}

            Dependencies:
            {json.dumps(getattr(state, 'task_dependencies', []), indent=2)}

            Project Context:
            {json.dumps(getattr(state, 'project_context', {}), indent=2)}

            Team Configuration (if known):
            {json.dumps(getattr(state, 'project_context', {}).get('team_config', {}), indent=2)}

            Provide comprehensive effort estimation in JSON format."""

            # Call AI
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ]

            model = context.settings.get("estimate_effort_model", "z-ai/glm-4.6")
            response = await self._call_ai(messages, model, context, state, temperature=0.2)

            # Parse JSON response
            try:
                effort_data = json.loads(response)
            except json.JSONDecodeError:
                import re

                json_match = re.search(r"\{.*\}", response, re.DOTALL)
                if json_match:
                    effort_data = json.loads(json_match.group())
                else:
                    raise TaskGenerationNodeException("Failed to parse AI response as JSON")

            # Store effort data in state
            setattr(state, "effort_estimates", effort_data)
            setattr(state, "resource_allocation", effort_data.get("resource_allocation", {}))
            setattr(state, "effort_estimation_quality", self._calculate_effort_quality(effort_data))

            # Store in memory
            await self._store_memory(
                f"Effort Estimation: {effort_data.get('project_summary', {}).get('total_hours', 'unknown')} total hours estimated",
                {
                    "node": self.node_name,
                    "workflow_id": str(state.workflow_id),
                    "effort_summary": effort_data.get("project_summary", {}),
                },
                context,
                state,
                "chats",
            )

            # Create step result
            step_result = TaskGenerationStepResult(
                step_name=self.node_name,
                success=True,
                result_data=effort_data,
                error_message=None,
                confidence_score=getattr(state, "effort_estimation_quality", 0.0),
                tokens_used=None,
                cost_incurred=None,
                timestamp=self._get_timestamp(),
            )

            if hasattr(state, "mark_task_step_completed"):
                getattr(state, "mark_task_step_completed")(self.node_name, step_result)
            if hasattr(state, "update_task_progress"):
                getattr(state, "update_task_progress")("generate_openspec", 80)

            self.logger.info(
                f"Effort estimation completed: {effort_data.get('project_summary', {}).get('total_hours', 'unknown')} hours estimated"
            )

            return {
                "estimates": effort_data,
                "quality_score": getattr(state, "effort_estimation_quality", 0.0),
                "next_step": "generate_openspec",
            }

        except Exception as e:
            self.logger.error(f"Effort estimation failed: {e}")
            if hasattr(state, "mark_task_step_failed"):
                getattr(state, "mark_task_step_failed")(self.node_name, str(e))
            raise TaskGenerationNodeException(f"Effort estimation failed: {str(e)}") from e

    def _calculate_effort_quality(self, effort_data: Dict[str, Any]) -> float:
        """Calculate quality score for effort estimation."""
        score = 0.0
        max_score = 5.0

        # Check for task estimates
        if effort_data.get("task_estimates"):
            score += 1.0

        # Check for project summary
        if effort_data.get("project_summary"):
            score += 1.0

        # Check for resource allocation
        if effort_data.get("resource_allocation"):
            score += 1.0

        # Check for timeline optimization
        if effort_data.get("timeline_optimization"):
            score += 1.0

        # Check for cost breakdown
        if effort_data.get("cost_breakdown"):
            score += 1.0

        return min(score / max_score, 1.0)


class GenerateOpenSpecNode(BaseNode):
    """
    Node for generating OpenSpec proposal and task files.

    This node creates the complete OpenSpec proposal with all necessary
    files and documentation for implementation.
    """

    def __init__(self):
        super().__init__("generate_openspec")

    async def execute(
        self,
        state: "WorkflowState",
        context,
    ) -> Dict[str, Any]:
        """
        Generate OpenSpec proposal and task files.

        Args:
            state: TaskGenerationState
            context: WorkflowContext

        Returns:
            OpenSpec proposal and generated files
        """
        try:
            self.logger.info("Starting OpenSpec generation")

            # Get relevant context
            relevant_context = await self._get_relevant_context(
                (
                    f"OpenSpec generation for {state.project_id}"
                    if state.project_id
                    else "OpenSpec generation"
                ),
                context,
                state,
                limit=3,
            )

            # Generate unique proposal ID
            proposal_id = f"task-gen-{state.workflow_id.hex[:8]}"
            change_directory = f"openspec/changes/{proposal_id}"

            # Prepare AI prompt
            system_prompt = """You are an expert technical writer and OpenSpec specialist.
            Generate a complete OpenSpec proposal with all necessary files.

            Create OpenSpec proposal including:
            1. proposal.md - High-level summary and objectives
            2. tasks.md - Detailed task breakdown with dependencies
            3. spec-delta.md - Specification updates and changes
            4. README.md - Implementation guide and context
            5. risk-assessment.md - Risk analysis and mitigation strategies

            Each file should be well-structured, comprehensive, and ready for
            human review and implementation.

            Format your response as JSON:
            {
                "proposal": {
                    "id": "...",
                    "title": "...",
                    "description": "...",
                    "objectives": [...],
                    "scope": {...},
                    "success_criteria": [...]
                },
                "files": {
                    "proposal.md": "...",
                    "tasks.md": "...",
                    "spec-delta.md": "...",
                    "README.md": "...",
                    "risk-assessment.md": "..."
                },
                "metadata": {
                    "generated_at": "...",
                    "workflow_id": "...",
                    "total_tasks": "...",
                    "estimated_effort": "...",
                    "quality_score": "..."
                }
            }"""

            user_prompt = f"""Generate OpenSpec proposal for this task generation:

            PRD Content:
            {getattr(state, 'prd_content', '')}

            Task Breakdown:
            {json.dumps(getattr(state, 'task_breakdown', []), indent=2)}

            Dependencies:
            {json.dumps(getattr(state, 'task_dependencies', []), indent=2)}

            Effort Estimates:
            {json.dumps(getattr(state, 'effort_estimates', {}), indent=2)}

            Project Context:
            {json.dumps(getattr(state, 'project_context', {}), indent=2)}

            Proposal ID: {proposal_id}
            Change Directory: {change_directory}

            Generate complete OpenSpec proposal in JSON format."""

            # Call AI
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ]

            model = context.settings.get("generate_openspec_model", "anthropic/claude-sonnet-4.5")
            response = await self._call_ai(messages, model, context, state, temperature=0.3)

            # Parse JSON response
            try:
                openspec_data = json.loads(response)
            except json.JSONDecodeError:
                import re

                json_match = re.search(r"\{.*\}", response, re.DOTALL)
                if json_match:
                    openspec_data = json.loads(json_match.group())
                else:
                    raise TaskGenerationNodeException("Failed to parse AI response as JSON")

            # Generate actual OpenSpec files using the service
            from ...services.openspec_service import get_openspec_service

            openspec_service = get_openspec_service()

            try:
                generated_files = openspec_service.generate_openspec_files(
                    openspec_data, proposal_id, change_directory
                )
                self.logger.info(f"Generated {len(generated_files)} OpenSpec files")
            except Exception as e:
                self.logger.warning(f"Failed to generate OpenSpec files: {e}")
                # Continue without file generation - still store the proposal data
                generated_files = {}

            # Store OpenSpec data in state
            setattr(state, "openspec_proposal", openspec_data)
            setattr(state, "proposal_metadata", openspec_data.get("metadata", {}))
            setattr(state, "change_directory_path", change_directory)
            setattr(state, "generated_files", generated_files)
            setattr(
                state, "openspec_quality_score", self._calculate_openspec_quality(openspec_data)
            )

            # Store in memory
            await self._store_memory(
                f"OpenSpec Generated: Proposal {proposal_id} with {len(openspec_data.get('files', {}))} files",
                {
                    "node": self.node_name,
                    "workflow_id": str(state.workflow_id),
                    "openspec_summary": openspec_data.get("metadata", {}),
                    "proposal_id": proposal_id,
                    "change_directory": change_directory,
                    "files_generated": list(generated_files.keys()),
                },
                context,
                state,
                "chats",
            )

            # Create step result
            step_result = TaskGenerationStepResult(
                step_name=self.node_name,
                success=True,
                result_data={
                    "openspec": openspec_data,
                    "generated_files": generated_files,
                    "proposal_id": proposal_id,
                    "change_directory": change_directory,
                },
                error_message=None,
                confidence_score=getattr(state, "openspec_quality_score", 0.0),
                tokens_used=None,
                cost_incurred=None,
                timestamp=self._get_timestamp(),
            )

            if hasattr(state, "mark_task_step_completed"):
                getattr(state, "mark_task_step_completed")(self.node_name, step_result)
            if hasattr(state, "update_task_progress"):
                getattr(state, "update_task_progress")("completed", 100)

            self.logger.info(
                f"OpenSpec generation completed: Proposal {proposal_id} with {len(openspec_data.get('files', {}))} files"
            )

            return {
                "openspec": openspec_data,
                "generated_files": generated_files,
                "proposal_id": proposal_id,
                "change_directory": change_directory,
                "quality_score": getattr(state, "openspec_quality_score", 0.0),
                "next_step": "completed",
            }

        except Exception as e:
            self.logger.error(f"OpenSpec generation failed: {e}")
            if hasattr(state, "mark_task_step_failed"):
                getattr(state, "mark_task_step_failed")(self.node_name, str(e))
            raise TaskGenerationNodeException(f"OpenSpec generation failed: {str(e)}") from e

    def _calculate_openspec_quality(self, openspec_data: Dict[str, Any]) -> float:
        """Calculate quality score for OpenSpec generation."""
        score = 0.0
        max_score = 6.0

        # Check for proposal
        if openspec_data.get("proposal"):
            score += 1.0

        # Check for required files
        required_files = ["proposal.md", "tasks.md", "spec-delta.md", "README.md"]
        files = openspec_data.get("files", {})
        has_required_files = all(file in files for file in required_files)
        if has_required_files:
            score += 1.0

        # Check for risk assessment
        if "risk-assessment.md" in files:
            score += 1.0

        # Check for metadata
        if openspec_data.get("metadata"):
            score += 1.0

        # Check file content quality
        file_contents = list(files.values())
        has_substantial_content = any(len(content) > 500 for content in file_contents)
        if has_substantial_content:
            score += 1.0

        # Check for structure
        proposal = openspec_data.get("proposal", {})
        has_structure = (
            proposal.get("objectives")
            and proposal.get("scope")
            and proposal.get("success_criteria")
        )
        if has_structure:
            score += 1.0

        return min(score / max_score, 1.0)
