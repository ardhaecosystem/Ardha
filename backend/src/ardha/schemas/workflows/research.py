"""
Research workflow schemas and state management.

This module defines the state structures and schemas specific
to the research workflow with multi-agent orchestration.
"""

from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, Field

from ...workflows.state import WorkflowState


class ResearchState(WorkflowState):
    """
    Extended workflow state for research workflow.
    
    Contains research-specific fields for tracking
    the multi-step research process and results.
    """
    
    # Research input
    idea: str = Field(description="User's original idea or concept")
    
    # Research step results
    idea_analysis: Optional[Dict[str, Any]] = Field(
        default=None, description="Analysis of the core idea and concepts"
    )
    market_research: Optional[Dict[str, Any]] = Field(
        default=None, description="Market size, trends, and opportunity analysis"
    )
    competitive_analysis: Optional[Dict[str, Any]] = Field(
        default=None, description="Competitor analysis and market positioning"
    )
    technical_feasibility: Optional[Dict[str, Any]] = Field(
        default=None, description="Technical complexity and feasibility assessment"
    )
    research_summary: Optional[Dict[str, Any]] = Field(
        default=None, description="Executive summary with recommendations"
    )
    
    # Progress tracking
    current_step: str = Field(default="pending", description="Currently executing research step")
    progress_percentage: int = Field(default=0, description="Overall progress percentage (0-100)")
    
    # Research metadata
    research_confidence: float = Field(default=0.0, description="Overall confidence in research results")
    sources_found: int = Field(default=0, description="Total number of sources/references found")
    hypotheses_generated: int = Field(default=0, description="Number of research hypotheses generated")
    
    # Quality metrics
    analysis_depth_score: float = Field(default=0.0, description="Depth of analysis score (0-1)")
    market_data_quality: float = Field(default=0.0, description="Quality of market data (0-1)")
    competitor_coverage: float = Field(default=0.0, description="Coverage of competitors (0-1)")
    technical_detail_level: float = Field(default=0.0, description="Level of technical detail (0-1)")
    
    model_config = {
        "use_enum_values": True,
        "arbitrary_types_allowed": True,
    }
    
    def update_progress(self, step: str, percentage: int) -> None:
        """Update progress tracking."""
        self.current_step = step
        self.progress_percentage = max(0, min(100, percentage))
        self._update_timestamp()
    
    def add_research_metadata(self, **kwargs) -> None:
        """Add research-specific metadata."""
        for key, value in kwargs.items():
            self.metadata[key] = value
        self._update_timestamp()
    
    def calculate_research_confidence(self) -> float:
        """Calculate overall research confidence based on completed steps."""
        completed_steps = len([
            result for result in [
                self.idea_analysis, self.market_research, 
                self.competitive_analysis, self.technical_feasibility
            ]
            if result is not None
        ])
        
        total_steps = 4  # Total research steps
        base_confidence = completed_steps / total_steps
        
        # Factor in quality metrics
        quality_factor = (
            self.analysis_depth_score + 
            self.market_data_quality + 
            self.competitor_coverage + 
            self.technical_detail_level
        ) / 4
        
        # Weighted confidence calculation
        self.research_confidence = (base_confidence * 0.6) + (quality_factor * 0.4)
        return self.research_confidence
    
    def get_research_summary(self) -> Dict[str, Any]:
        """Get comprehensive research summary."""
        return {
            "idea": self.idea,
            "completed_steps": self.completed_nodes,
            "current_step": self.current_step,
            "progress_percentage": self.progress_percentage,
            "research_confidence": self.research_confidence,
            "sources_found": self.sources_found,
            "quality_metrics": {
                "analysis_depth": self.analysis_depth_score,
                "market_data_quality": self.market_data_quality,
                "competitor_coverage": self.competitor_coverage,
                "technical_detail": self.technical_detail_level,
            },
            "step_results": {
                "idea_analysis": self.idea_analysis,
                "market_research": self.market_research,
                "competitive_analysis": self.competitive_analysis,
                "technical_feasibility": self.technical_feasibility,
                "research_summary": self.research_summary,
            }
        }


class ResearchStepResult(BaseModel):
    """Result schema for individual research steps."""
    
    step_name: str = Field(description="Name of the research step")
    model_used: str = Field(description="AI model used for this step")
    execution_time_ms: int = Field(description="Execution time in milliseconds")
    tokens_used: int = Field(description="Total tokens used")
    cost_incurred: float = Field(description="Cost incurred for this step")
    
    # Step-specific data
    key_findings: List[str] = Field(default_factory=list, description="Key findings from this step")
    data_sources: List[str] = Field(default_factory=list, description="Data sources consulted")
    confidence_score: float = Field(description="Confidence in step results (0-1)")
    
    # Quality indicators
    completeness_score: float = Field(description="How complete the analysis is (0-1)")
    accuracy_score: float = Field(description="Estimated accuracy of results (0-1)")
    
    # Raw results
    raw_content: str = Field(description="Raw AI-generated content")
    structured_data: Dict[str, Any] = Field(default_factory=dict, description="Structured extracted data")
    
    model_config = {
        "use_enum_values": True,
        "protected_namespaces": (),
    }


class ResearchWorkflowConfig(BaseModel):
    """Configuration for research workflow execution."""
    
    # Model assignments
    idea_analysis_model: str = Field(default="z-ai/glm-4.6", description="Model for idea analysis")
    market_research_model: str = Field(default="anthropic/claude-sonnet-4.5", description="Model for market research")
    competitive_analysis_model: str = Field(default="anthropic/claude-sonnet-4.5", description="Model for competitive analysis")
    technical_feasibility_model: str = Field(default="z-ai/glm-4.6", description="Model for technical feasibility")
    synthesis_model: str = Field(default="anthropic/claude-sonnet-4.5", description="Model for research synthesis")
    
    # Execution parameters
    max_retries_per_step: int = Field(default=2, description="Maximum retries per step")
    timeout_per_step_seconds: int = Field(default=300, description="Timeout per step in seconds")
    enable_streaming: bool = Field(default=True, description="Enable streaming progress updates")
    
    # Quality thresholds
    minimum_confidence_threshold: float = Field(default=0.7, description="Minimum confidence threshold")
    minimum_completeness_threshold: float = Field(default=0.8, description="Minimum completeness threshold")
    
    # Research parameters
    max_sources_per_step: int = Field(default=10, description="Maximum sources to consider per step")
    context_items_limit: int = Field(default=5, description="Limit for context items retrieval")
    
    model_config = {
        "use_enum_values": True,
    }


class ResearchProgressUpdate(BaseModel):
    """Schema for research progress updates."""
    
    workflow_id: UUID = Field(description="Workflow identifier")
    execution_id: UUID = Field(description="Execution identifier")
    
    # Progress information
    current_step: str = Field(description="Currently executing step")
    step_status: str = Field(description="Status of current step (running/completed/failed)")
    progress_percentage: int = Field(description="Overall progress percentage")
    
    # Step details
    step_start_time: Optional[str] = Field(default=None, description="Step start timestamp")
    step_completion_time: Optional[str] = Field(default=None, description="Step completion timestamp")
    step_duration_ms: Optional[int] = Field(default=None, description="Step duration in milliseconds")
    
    # Results preview
    step_result_preview: Optional[str] = Field(default=None, description="Preview of step results")
    key_findings_preview: List[str] = Field(default_factory=list, description="Preview of key findings")
    
    # Quality metrics
    step_confidence: Optional[float] = Field(default=None, description="Confidence score for step")
    quality_score: Optional[float] = Field(default=None, description="Quality score for step")
    
    # Error information
    error_message: Optional[str] = Field(default=None, description="Error message if step failed")
    retry_count: Optional[int] = Field(default=None, description="Current retry attempt")
    
    # Overall workflow status
    total_cost_so_far: Optional[float] = Field(default=None, description="Total cost incurred so far")
    estimated_remaining_cost: Optional[float] = Field(default=None, description="Estimated remaining cost")
    
    timestamp: str = Field(description="Update timestamp")
    
    model_config = {
        "use_enum_values": True,
    }