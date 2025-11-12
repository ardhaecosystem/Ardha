"""
PRD (Product Requirements Document) workflow schemas and state management.

This module defines the state structures and schemas specific
to the PRD generation workflow that converts research into structured requirements.
"""

from typing import Any, Dict, List, Optional
from uuid import UUID
from datetime import datetime

from pydantic import BaseModel, Field

from ...workflows.state import WorkflowState, WorkflowType


class PRDState(WorkflowState):
    """
    Extended workflow state for PRD generation workflow.
    
    Contains PRD-specific fields for tracking the conversion
    of research into structured requirements and documentation.
    """
    
    # PRD-specific input
    research_summary: Dict[str, Any] = Field(
        description="Research summary from the research workflow"
    )
    
    # PRD generation step results
    requirements: Optional[Dict[str, Any]] = Field(
        default=None, description="Extracted functional and non-functional requirements"
    )
    features: Optional[Dict[str, Any]] = Field(
        default=None, description="Prioritized feature list with MoSCoW classification"
    )
    success_metrics: Optional[Dict[str, Any]] = Field(
        default=None, description="Defined success metrics and KPIs"
    )
    prd_content: Optional[str] = Field(
        default=None, description="Generated PRD document content"
    )
    final_prd: Optional[str] = Field(
        default=None, description="Final polished PRD document"
    )
    
    # Document metadata
    version: str = Field(default="1.0.0", description="PRD document version")
    last_updated: Optional[str] = Field(
        default=None, description="Last update timestamp"
    )
    
    # PRD quality metrics
    requirements_completeness: float = Field(default=0.0, description="Completeness of requirements extraction (0-1)")
    feature_prioritization_quality: float = Field(default=0.0, description="Quality of feature prioritization (0-1)")
    metrics_specificity: float = Field(default=0.0, description="Specificity of success metrics (0-1)")
    document_coherence: float = Field(default=0.0, description="Overall document coherence (0-1)")
    
    # Human-in-the-loop tracking
    human_approval_points: List[str] = Field(
        default_factory=list, description="Points where human approval was requested"
    )
    human_edits_made: List[Dict[str, Any]] = Field(
        default_factory=list, description="Track human edits made during workflow"
    )
    
    # Progress tracking
    current_prd_step: str = Field(default="extract_requirements", description="Currently executing PRD step")
    prd_progress_percentage: int = Field(default=0, description="PRD workflow progress percentage (0-100)")
    
    model_config = {
        "use_enum_values": True,
        "arbitrary_types_allowed": True,
    }
    
    def update_prd_progress(self, step: str, percentage: int) -> None:
        """Update PRD workflow progress tracking."""
        self.current_prd_step = step
        self.prd_progress_percentage = max(0, min(100, percentage))
        self._update_timestamp()
    
    def add_human_approval(self, approval_point: str, approved: bool, feedback: Optional[str] = None) -> None:
        """Record human approval decision."""
        approval_record = {
            "approval_point": approval_point,
            "approved": approved,
            "feedback": feedback,
            "timestamp": self._get_timestamp(),
        }
        self.human_approval_points.append(approval_point)
        self.metadata[f"human_approval_{approval_point}"] = approval_record
        self._update_timestamp()
    
    def add_human_edit(self, step: str, edit_type: str, original: str, modified: str) -> None:
        """Record human edit made during workflow."""
        edit_record = {
            "step": step,
            "edit_type": edit_type,
            "original": original,
            "modified": modified,
            "timestamp": self._get_timestamp(),
        }
        self.human_edits_made.append(edit_record)
        self._update_timestamp()
    
    def calculate_prd_quality_score(self) -> float:
        """Calculate overall PRD quality score based on component metrics."""
        quality_components = [
            self.requirements_completeness,
            self.feature_prioritization_quality,
            self.metrics_specificity,
            self.document_coherence,
        ]
        
        # Filter out zero values (not yet completed)
        valid_components = [score for score in quality_components if score > 0]
        
        if not valid_components:
            return 0.0
        
        return sum(valid_components) / len(valid_components)
    
    def get_prd_summary(self) -> Dict[str, Any]:
        """Get comprehensive PRD generation summary."""
        return {
            "research_summary": self.research_summary,
            "current_step": self.current_prd_step,
            "progress_percentage": self.prd_progress_percentage,
            "version": self.version,
            "last_updated": self.last_updated,
            "quality_metrics": {
                "requirements_completeness": self.requirements_completeness,
                "feature_prioritization_quality": self.feature_prioritization_quality,
                "metrics_specificity": self.metrics_specificity,
                "document_coherence": self.document_coherence,
                "overall_quality": self.calculate_prd_quality_score(),
            },
            "human_in_the_loop": {
                "approval_points": self.human_approval_points,
                "edits_made": len(self.human_edits_made),
            },
            "step_results": {
                "requirements": self.requirements,
                "features": self.features,
                "success_metrics": self.success_metrics,
                "prd_content": self.prd_content,
                "final_prd": self.final_prd,
            }
        }


class PRDStepResult(BaseModel):
    """Result schema for individual PRD generation steps."""
    
    step_name: str = Field(description="Name of the PRD generation step")
    model_used: str = Field(description="AI model used for this step")
    execution_time_ms: int = Field(description="Execution time in milliseconds")
    tokens_used: int = Field(description="Total tokens used")
    cost_incurred: float = Field(description="Cost incurred for this step")
    
    # Step-specific data
    key_outputs: List[str] = Field(default_factory=list, description="Key outputs from this step")
    data_structures: Dict[str, Any] = Field(default_factory=dict, description="Structured data generated")
    
    # Quality indicators
    completeness_score: float = Field(description="How complete the step output is (0-1)")
    accuracy_score: float = Field(description="Estimated accuracy of results (0-1)")
    
    # Human interaction
    human_approval_required: bool = Field(default=False, description="Whether human approval was required")
    human_approval_granted: Optional[bool] = Field(default=None, description="Whether human approval was granted")
    human_feedback: Optional[str] = Field(default=None, description="Human feedback provided")
    
    # Raw results
    raw_content: str = Field(description="Raw AI-generated content")
    
    model_config = {
        "use_enum_values": True,
        "protected_namespaces": (),
    }


class PRDWorkflowConfig(BaseModel):
    """Configuration for PRD workflow execution."""
    
    # Model assignments
    extract_requirements_model: str = Field(default="anthropic/claude-sonnet-4.5", description="Model for requirements extraction")
    define_features_model: str = Field(default="z-ai/glm-4.6", description="Model for feature definition")
    set_metrics_model: str = Field(default="z-ai/glm-4.6", description="Model for metrics definition")
    generate_prd_model: str = Field(default="anthropic/claude-sonnet-4.5", description="Model for PRD generation")
    review_format_model: str = Field(default="z-ai/glm-4.6", description="Model for review and formatting")
    
    # Execution parameters
    max_retries_per_step: int = Field(default=3, description="Maximum retries per step")
    timeout_per_step_seconds: int = Field(default=300, description="Timeout per step in seconds")
    enable_streaming: bool = Field(default=True, description="Enable streaming progress updates")
    
    # Quality thresholds
    minimum_completeness_threshold: float = Field(default=0.8, description="Minimum completeness threshold")
    minimum_quality_threshold: float = Field(default=0.7, description="Minimum quality threshold")
    
    # Human-in-the-loop settings
    enable_human_approval: bool = Field(default=True, description="Enable human approval gates")
    auto_approve_confidence_threshold: float = Field(default=0.9, description="Auto-approve if confidence above threshold")
    
    # PRD template settings
    include_technical_architecture: bool = Field(default=True, description="Include technical architecture section")
    include_timeline_milestones: bool = Field(default=True, description="Include timeline and milestones section")
    include_success_metrics: bool = Field(default=True, description="Include success metrics section")
    
    # Version management
    auto_increment_version: bool = Field(default=True, description="Auto-increment version on changes")
    version_format: str = Field(default="semantic", description="Version format: semantic, date, custom")
    
    model_config = {
        "use_enum_values": True,
    }


class PRDProgressUpdate(BaseModel):
    """Schema for PRD workflow progress updates."""
    
    workflow_id: UUID = Field(description="Workflow identifier")
    execution_id: UUID = Field(description="Execution identifier")
    
    # Progress information
    current_step: str = Field(description="Currently executing PRD step")
    step_status: str = Field(description="Status of current step (running/completed/failed)")
    progress_percentage: int = Field(description="Overall progress percentage")
    
    # Step details
    step_start_time: Optional[str] = Field(default=None, description="Step start timestamp")
    step_completion_time: Optional[str] = Field(default=None, description="Step completion timestamp")
    step_duration_ms: Optional[int] = Field(default=None, description="Step duration in milliseconds")
    
    # Results preview
    step_result_preview: Optional[str] = Field(default=None, description="Preview of step results")
    key_outputs_preview: List[str] = Field(default_factory=list, description="Preview of key outputs")
    
    # Quality metrics
    step_quality_score: Optional[float] = Field(default=None, description="Quality score for step")
    completeness_score: Optional[float] = Field(default=None, description="Completeness score for step")
    
    # Human interaction
    human_approval_requested: bool = Field(default=False, description="Whether human approval was requested")
    human_approval_status: Optional[str] = Field(default=None, description="Status of human approval")
    human_feedback: Optional[str] = Field(default=None, description="Human feedback provided")
    
    # Error information
    error_message: Optional[str] = Field(default=None, description="Error message if step failed")
    retry_count: Optional[int] = Field(default=None, description="Current retry attempt")
    
    # Document information
    current_version: Optional[str] = Field(default=None, description="Current PRD version")
    document_length: Optional[int] = Field(default=None, description="Current document length in characters")
    
    # Overall workflow status
    total_cost_so_far: Optional[float] = Field(default=None, description="Total cost incurred so far")
    estimated_remaining_cost: Optional[float] = Field(default=None, description="Estimated remaining cost")
    
    timestamp: str = Field(description="Update timestamp")
    
    model_config = {
        "use_enum_values": True,
    }


class PRDDocumentMetadata(BaseModel):
    """Metadata for generated PRD documents."""
    
    document_id: UUID = Field(description="Unique document identifier")
    workflow_id: UUID = Field(description="Workflow that generated this document")
    version: str = Field(description="Document version")
    
    # Content statistics
    total_sections: int = Field(description="Total number of sections")
    functional_requirements_count: int = Field(default=0, description="Number of functional requirements")
    non_functional_requirements_count: int = Field(default=0, description="Number of non-functional requirements")
    features_count: int = Field(default=0, description="Total number of features")
    success_metrics_count: int = Field(default=0, description="Number of success metrics")
    
    # Quality metrics
    overall_quality_score: float = Field(description="Overall quality score (0-1)")
    completeness_score: float = Field(description="Document completeness score (0-1)")
    
    # Generation metadata
    generated_at: str = Field(description="Document generation timestamp")
    models_used: List[str] = Field(default_factory=list, description="AI models used in generation")
    total_cost: float = Field(default=0.0, description="Total cost to generate document")
    total_tokens: int = Field(default=0, description="Total tokens used in generation")
    
    # Human interaction
    human_reviewed: bool = Field(default=False, description="Whether document was human-reviewed")
    human_edits_count: int = Field(default=0, description="Number of human edits made")
    
    model_config = {
        "use_enum_values": True,
    }