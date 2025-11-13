"""
Task Generation workflow state and configuration schemas.

This module defines the state management and configuration for the
Task Generation workflow that creates OpenSpec proposals and task breakdowns.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional, Union
from uuid import UUID

from pydantic import BaseModel, Field, field_validator

from ...workflows.state import WorkflowState, WorkflowStatus, WorkflowType


class TaskGenerationStepResult(BaseModel):
    """Result of a single task generation step."""
    
    step_name: str = Field(..., description="Name of the step")
    success: bool = Field(..., description="Whether the step succeeded")
    result_data: Dict[str, Any] = Field(default_factory=dict, description="Step result data")
    error_message: Optional[str] = Field(None, description="Error message if failed")
    confidence_score: float = Field(default=0.0, ge=0.0, le=1.0, description="Confidence in result")
    tokens_used: Optional[int] = Field(None, ge=0, description="Tokens used in this step")
    cost_incurred: Optional[float] = Field(None, ge=0.0, description="Cost incurred in this step")
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat(), description="Step completion timestamp")
    
    model_config = {"populate_by_name": True}


class TaskGenerationProgressUpdate(BaseModel):
    """Progress update for task generation workflow."""
    
    workflow_id: UUID = Field(..., description="Workflow identifier")
    execution_id: UUID = Field(..., description="Execution identifier")
    current_step: str = Field(..., description="Current step name")
    progress_percentage: float = Field(..., ge=0.0, le=100.0, description="Overall progress percentage")
    step_status: str = Field(..., description="Status of current step")
    message: Optional[str] = Field(None, description="Progress message")
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat(), description="Update timestamp")


class TaskGenerationWorkflowConfig(BaseModel):
    """Configuration for Task Generation workflow."""
    
    # Model selection per step
    analyze_prd_model: str = Field(default="anthropic/claude-sonnet-4.5", description="Model for PRD analysis")
    breakdown_tasks_model: str = Field(default="anthropic/claude-sonnet-4.5", description="Model for task breakdown")
    define_dependencies_model: str = Field(default="anthropic/claude-sonnet-4.5", description="Model for dependency definition")
    estimate_effort_model: str = Field(default="z-ai/glm-4.6", description="Model for effort estimation")
    generate_openspec_model: str = Field(default="anthropic/claude-sonnet-4.5", description="Model for OpenSpec generation")
    
    # Workflow parameters
    max_retries_per_step: int = Field(default=3, ge=1, le=10, description="Max retries per step")
    timeout_per_step_seconds: int = Field(default=300, ge=60, le=1800, description="Timeout per step in seconds")
    enable_streaming: bool = Field(default=True, description="Enable progress streaming")
    
    # Task generation parameters
    max_tasks_per_epic: int = Field(default=20, ge=5, le=100, description="Maximum tasks per epic")
    min_task_detail_level: str = Field(default="medium", description="Minimum task detail level")
    include_subtasks: bool = Field(default=True, description="Include subtasks in breakdown")
    include_acceptance_criteria: bool = Field(default=True, description="Include acceptance criteria")
    
    # Quality thresholds
    minimum_task_quality_score: float = Field(default=0.7, ge=0.0, le=1.0, description="Minimum task quality score")
    minimum_dependency_clarity: float = Field(default=0.8, ge=0.0, le=1.0, description="Minimum dependency clarity score")
    minimum_effort_accuracy: float = Field(default=0.6, ge=0.0, le=1.0, description="Minimum effort estimation accuracy")
    
    # OpenSpec parameters
    openspec_template_path: Optional[str] = Field(None, description="Custom OpenSpec template path")
    include_proposal_summary: bool = Field(default=True, description="Include proposal summary in OpenSpec")
    include_risk_assessment: bool = Field(default=True, description="Include risk assessment in OpenSpec")
    
    @field_validator('min_task_detail_level')
    @classmethod
    def validate_detail_level(cls, v):
        """Validate task detail level."""
        valid_levels = ['minimal', 'basic', 'medium', 'detailed', 'comprehensive']
        if v not in valid_levels:
            raise ValueError(f'Detail level must be one of: {valid_levels}')
        return v


class TaskGenerationState(WorkflowState):
    """Extended workflow state for Task Generation workflow."""
    
    # ============= Task Generation Specific State =============
    
    # Input data
    prd_content: Optional[str] = Field(None, description="PRD document content")
    project_context: Optional[Dict[str, Any]] = Field(None, description="Project context and constraints")
    existing_tasks: Optional[List[Dict[str, Any]]] = Field(None, description="Existing tasks in project")
    
    # Analysis results
    prd_analysis: Optional[Dict[str, Any]] = Field(None, description="Analysis of PRD content")
    feature_breakdown: Optional[List[Dict[str, Any]]] = Field(None, description="Feature breakdown from PRD")
    technical_requirements: Optional[List[Dict[str, Any]]] = Field(None, description="Technical requirements extracted")
    
    # Task breakdown results
    task_breakdown: Optional[List[Dict[str, Any]]] = Field(None, description="Complete task breakdown")
    epics_defined: Optional[List[Dict[str, Any]]] = Field(None, description="Epics identified and defined")
    subtasks_created: Optional[List[Dict[str, Any]]] = Field(None, description="Subtasks created for main tasks")
    
    # Dependency and effort results
    task_dependencies: Optional[List[Dict[str, Any]]] = Field(None, description="Task dependencies defined")
    dependency_graph: Optional[Dict[str, Any]] = Field(None, description="Complete dependency graph")
    effort_estimates: Optional[Dict[str, Any]] = Field(None, description="Effort estimates for all tasks")
    resource_allocation: Optional[Dict[str, Any]] = Field(None, description="Resource allocation recommendations")
    
    # OpenSpec generation results
    openspec_proposal: Optional[Dict[str, Any]] = Field(None, description="Generated OpenSpec proposal")
    proposal_metadata: Optional[Dict[str, Any]] = Field(None, description="OpenSpec proposal metadata")
    change_directory_path: Optional[str] = Field(None, description="Path for openspec/changes/ directory")
    generated_files: Optional[Dict[str, str]] = Field(None, description="Generated OpenSpec files mapping")
    
    # ============= Progress Tracking =============
    
    current_task_step: str = Field(default="analyze_prd", description="Current task generation step")
    task_progress_percentage: float = Field(default=0.0, ge=0.0, le=100.0, description="Task generation progress percentage")
    completed_task_steps: List[str] = Field(default_factory=list, description="Completed task generation steps")
    failed_task_steps: List[str] = Field(default_factory=list, description="Failed task generation steps")
    
    # ============= Quality Metrics =============
    
    prd_analysis_quality: float = Field(default=0.0, ge=0.0, le=1.0, description="Quality of PRD analysis")
    task_breakdown_completeness: float = Field(default=0.0, ge=0.0, le=1.0, description="Completeness of task breakdown")
    dependency_accuracy: float = Field(default=0.0, ge=0.0, le=1.0, description="Accuracy of dependency definitions")
    effort_estimation_quality: float = Field(default=0.0, ge=0.0, le=1.0, description="Quality of effort estimates")
    openspec_quality_score: float = Field(default=0.0, ge=0.0, le=1.0, description="Overall OpenSpec quality score")
    
    # ============= Step Results =============
    
    step_results: List[Dict[str, Any]] = Field(default_factory=list, description="Results of each step")
    
    # ============= Human Interaction Points =============
    
    human_approval_points: List[str] = Field(default_factory=list, description="Points requiring human approval")
    human_edits_made: List[Dict[str, Any]] = Field(default_factory=list, description="Human edits recorded")
    
    # ============= Timestamp Fields =============
    
    updated_at: Optional[str] = Field(None, description="Last update timestamp")
    
    def __init__(self, **data):
        """Initialize TaskGenerationState."""
        super().__init__(**data)
        # Ensure workflow_type is set correctly
        if self.workflow_type is None:
            self.workflow_type = WorkflowType.CUSTOM  # Using CUSTOM for task generation workflow
    
    def update_task_progress(self, step: str, percentage: float) -> None:
        """
        Update task generation progress.
        
        Args:
            step: Current step name
            percentage: Progress percentage (0-100)
        """
        self.current_task_step = step
        self.task_progress_percentage = max(0.0, min(100.0, percentage))
        self.updated_at = datetime.utcnow().isoformat()
    
    def mark_task_step_completed(self, step: str, result: TaskGenerationStepResult) -> None:
        """
        Mark a task generation step as completed.
        
        Args:
            step: Step name
            result: Step result
        """
        if step not in self.completed_task_steps:
            self.completed_task_steps.append(step)
        # Convert TaskGenerationStepResult to dictionary before storing
        if hasattr(result, 'model_dump'):
            self.step_results.append(result.model_dump())
        elif hasattr(result, 'dict'):
            self.step_results.append(result.dict())
        else:
            # Handle case where result is already a TaskGenerationStepResult
            if isinstance(result, TaskGenerationStepResult):
                self.step_results.append(result.model_dump())
            else:
                self.step_results.append(result)
        self.updated_at = datetime.utcnow().isoformat()
    
    def mark_task_step_failed(self, step: str, error: str) -> None:
        """
        Mark a task generation step as failed.
        
        Args:
            step: Step name
            error: Error message
        """
        if step not in self.failed_task_steps:
            self.failed_task_steps.append(step)
        self.errors.append({
            "step": step,
            "error": error,
            "timestamp": datetime.utcnow().isoformat(),
        })
        self.updated_at = datetime.utcnow().isoformat()
    
    def calculate_task_quality_score(self) -> float:
        """
        Calculate overall task generation quality score.
        
        Returns:
            Overall quality score (0.0-1.0)
        """
        weights = {
            "prd_analysis_quality": 0.2,
            "task_breakdown_completeness": 0.25,
            "dependency_accuracy": 0.2,
            "effort_estimation_quality": 0.2,
            "openspec_quality_score": 0.15,
        }
        
        weighted_score = 0.0
        
        for metric, weight in weights.items():
            value = getattr(self, metric, 0.0)
            weighted_score += value * weight
        
        return weighted_score
    
    def get_progress_summary(self) -> Dict[str, Any]:
        """
        Get summary of task generation progress.
        
        Returns:
            Progress summary dictionary
        """
        return {
            "current_step": self.current_task_step,
            "progress_percentage": self.task_progress_percentage,
            "completed_steps": self.completed_task_steps,
            "failed_steps": self.failed_task_steps,
            "total_steps": 5,  # analyze_prd, breakdown_tasks, define_dependencies, estimate_effort, generate_openspec
            "quality_score": self.calculate_task_quality_score(),
            "tasks_generated": len(self.task_breakdown) if self.task_breakdown else 0,
            "dependencies_defined": len(self.task_dependencies) if self.task_dependencies else 0,
            "openspec_generated": self.openspec_proposal is not None,
        }
    
    def get_task_summary(self) -> Dict[str, Any]:
        """
        Get summary of generated tasks.
        
        Returns:
            Task summary dictionary
        """
        if not self.task_breakdown:
            return {"total_tasks": 0, "epics": 0, "subtasks": 0}
        
        total_tasks = len(self.task_breakdown)
        epics = len([t for t in self.task_breakdown if t.get("is_epic", False)])
        subtasks = len([t for t in self.task_breakdown if t.get("is_subtask", False)])
        
        # Get estimated hours and cost from effort estimates
        estimated_hours = 0
        estimated_cost = 0
        if self.effort_estimates and "project_summary" in self.effort_estimates:
            estimated_hours = self.effort_estimates["project_summary"].get("total_hours", 0)
            estimated_cost = self.effort_estimates["project_summary"].get("total_cost", 0)
        
        return {
            "total_tasks": total_tasks,
            "epics": epics,
            "subtasks": subtasks,
            "main_tasks": total_tasks - epics - subtasks,
            "tasks_with_estimates": len([t for t in self.task_breakdown if t.get("estimate_hours")]),
            "tasks_with_dependencies": len([t for t in self.task_breakdown if t.get("dependencies")]),
            "total_dependencies": len(self.task_dependencies) if self.task_dependencies else 0,
            "estimated_hours": estimated_hours,
            "estimated_cost": estimated_cost,
        }