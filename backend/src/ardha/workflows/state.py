"""
Workflow state management for LangGraph integration.

This module defines the state structures and enums used throughout
the AI workflow system for tracking execution status and data flow.
"""

from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Union
from uuid import UUID

from pydantic import BaseModel, Field


class WorkflowStatus(str, Enum):
    """Status of workflow execution."""
    
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    PAUSED = "paused"


class NodeStatus(str, Enum):
    """Status of individual workflow node execution."""
    
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


class WorkflowType(str, Enum):
    """Types of available workflows."""
    
    RESEARCH = "research"
    ARCHITECT = "architect"
    IMPLEMENT = "implement"
    DEBUG = "debug"
    FULL_DEVELOPMENT = "full_development"
    CUSTOM = "custom"


class WorkflowState(BaseModel):
    """
    Central state object for workflow execution.
    
    This state flows through all nodes in the workflow and contains
    all context, results, and metadata needed for execution.
    """
    
    # Core identification
    workflow_id: UUID = Field(description="Unique workflow identifier")
    execution_id: UUID = Field(description="Unique execution identifier")
    workflow_type: WorkflowType = Field(description="Type of workflow")
    user_id: UUID = Field(description="User who initiated the workflow")
    project_id: Optional[UUID] = Field(default=None, description="Associated project")
    
    # Status tracking
    status: WorkflowStatus = Field(default=WorkflowStatus.PENDING, description="Current workflow status")
    current_node: Optional[str] = Field(default=None, description="Currently executing node")
    completed_nodes: List[str] = Field(default_factory=list, description="Completed node names")
    failed_nodes: List[str] = Field(default_factory=list, description="Failed node names")
    
    # Input data
    initial_request: str = Field(description="Original user request")
    context: Dict[str, Any] = Field(default_factory=dict, description="Additional context data")
    parameters: Dict[str, Any] = Field(default_factory=dict, description="Workflow parameters")
    
    # Execution results
    results: Dict[str, Any] = Field(default_factory=dict, description="Accumulated results from nodes")
    artifacts: Dict[str, Any] = Field(default_factory=dict, description="Generated artifacts (code, docs, etc.)")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Execution metadata")
    
    # AI interaction data
    ai_calls: List[Dict[str, Any]] = Field(default_factory=list, description="AI API calls made")
    token_usage: Dict[str, Dict[str, int]] = Field(default_factory=dict, description="Token usage by model")
    total_cost: float = Field(default=0.0, description="Total cost of AI calls")
    
    # Error handling
    errors: List[Dict[str, Any]] = Field(default_factory=list, description="Errors encountered during execution")
    retry_count: int = Field(default=0, description="Number of retries attempted")
    max_retries: int = Field(default=3, description="Maximum allowed retries")
    
    # Timing
    created_at: Optional[str] = Field(default=None, description="Creation timestamp")
    started_at: Optional[str] = Field(default=None, description="Execution start timestamp")
    completed_at: Optional[str] = Field(default=None, description="Completion timestamp")
    last_activity: Optional[str] = Field(default=None, description="Last activity timestamp")
    
    class Config:
        """Pydantic configuration."""
        use_enum_values = True
    
    def mark_node_started(self, node_name: str) -> None:
        """Mark a node as started."""
        self.current_node = node_name
        self.status = WorkflowStatus.RUNNING
        self._update_timestamp()
    
    def mark_node_completed(self, node_name: str, result: Dict[str, Any]) -> None:
        """Mark a node as completed with results."""
        if node_name not in self.completed_nodes:
            self.completed_nodes.append(node_name)
        
        # Remove from failed nodes if it was previously failed
        if node_name in self.failed_nodes:
            self.failed_nodes.remove(node_name)
        
        # Store node results
        self.results[node_name] = result
        self._update_timestamp()
    
    def mark_node_failed(self, node_name: str, error: Dict[str, Any]) -> None:
        """Mark a node as failed with error details."""
        if node_name not in self.failed_nodes:
            self.failed_nodes.append(node_name)
        
        # Remove from completed nodes if it was previously completed
        if node_name in self.completed_nodes:
            self.completed_nodes.remove(node_name)
        
        # Store error
        self.errors.append({
            "node": node_name,
            "error": error,
            "timestamp": self._get_timestamp(),
        })
        self._update_timestamp()
    
    def add_artifact(self, artifact_type: str, content: Any, metadata: Optional[Dict[str, Any]] = None) -> None:
        """Add an artifact to the workflow results."""
        self.artifacts[artifact_type] = {
            "content": content,
            "metadata": metadata or {},
            "created_at": self._get_timestamp(),
        }
        self._update_timestamp()
    
    def add_ai_call(self, model: str, operation: str, tokens_input: int, tokens_output: int, cost: float) -> None:
        """Record an AI API call."""
        call_record = {
            "model": model,
            "operation": operation,
            "tokens_input": tokens_input,
            "tokens_output": tokens_output,
            "cost": cost,
            "timestamp": self._get_timestamp(),
        }
        self.ai_calls.append(call_record)
        
        # Update token usage
        if model not in self.token_usage:
            self.token_usage[model] = {"input": 0, "output": 0}
        self.token_usage[model]["input"] += tokens_input
        self.token_usage[model]["output"] += tokens_output
        
        # Update total cost
        self.total_cost += cost
        self._update_timestamp()
    
    def get_result(self, node_name: str, default: Any = None) -> Any:
        """Get result from a specific node."""
        return self.results.get(node_name, default)
    
    def get_artifact(self, artifact_type: str, default: Any = None) -> Any:
        """Get artifact of a specific type."""
        return self.artifacts.get(artifact_type, default)
    
    def is_completed(self) -> bool:
        """Check if workflow is completed."""
        return self.status == WorkflowStatus.COMPLETED
    
    def is_failed(self) -> bool:
        """Check if workflow is failed."""
        return self.status == WorkflowStatus.FAILED
    
    def is_running(self) -> bool:
        """Check if workflow is currently running."""
        return self.status == WorkflowStatus.RUNNING
    
    def can_retry(self) -> bool:
        """Check if workflow can be retried."""
        return self.retry_count < self.max_retries and self.is_failed()
    
    def get_progress(self) -> float:
        """Calculate workflow progress as percentage."""
        if not self.completed_nodes and not self.failed_nodes:
            return 0.0
        
        # This would need to be customized based on workflow definition
        # For now, simple calculation based on completed vs failed
        total_processed = len(self.completed_nodes) + len(self.failed_nodes)
        if total_processed == 0:
            return 0.0
        
        return (len(self.completed_nodes) / total_processed) * 100.0
    
    def _update_timestamp(self) -> None:
        """Update the last activity timestamp."""
        self.last_activity = self._get_timestamp()
    
    def _get_timestamp(self) -> str:
        """Get current timestamp in ISO format."""
        from datetime import datetime, timezone
        return datetime.now(timezone.utc).isoformat() + "Z"


class NodeState(BaseModel):
    """
    State for individual workflow node execution.
    
    Each node maintains its own state for tracking execution
    progress and intermediate results.
    """
    
    node_name: str = Field(description="Name of the node")
    node_type: str = Field(description="Type of the node")
    status: NodeStatus = Field(default=NodeStatus.PENDING, description="Node execution status")
    
    # Input/Output data
    input_data: Dict[str, Any] = Field(default_factory=dict, description="Input data for the node")
    output_data: Dict[str, Any] = Field(default_factory=dict, description="Output data from the node")
    
    # Execution details
    started_at: Optional[str] = Field(default=None, description="Node start timestamp")
    completed_at: Optional[str] = Field(default=None, description="Node completion timestamp")
    duration_ms: Optional[int] = Field(default=None, description="Execution duration in milliseconds")
    
    # Error handling
    error_message: Optional[str] = Field(default=None, description="Error message if failed")
    retry_count: int = Field(default=0, description="Number of retries for this node")
    
    # Resource usage
    ai_calls_made: int = Field(default=0, description="Number of AI calls made")
    tokens_used: int = Field(default=0, description="Total tokens used")
    cost_incurred: float = Field(default=0.0, description="Cost incurred by this node")
    
    def mark_started(self) -> None:
        """Mark node as started."""
        self.status = NodeStatus.RUNNING
        from datetime import datetime
        self.started_at = datetime.utcnow().isoformat() + "Z"
    
    def mark_completed(self, output_data: Dict[str, Any]) -> None:
        """Mark node as completed with output data."""
        self.status = NodeStatus.COMPLETED
        self.output_data = output_data
        
        from datetime import datetime
        self.completed_at = datetime.utcnow().isoformat() + "Z"
        
        # Calculate duration
        if self.started_at:
            start_dt = datetime.fromisoformat(self.started_at.replace("Z", "+00:00"))
            end_dt = datetime.fromisoformat(self.completed_at.replace("Z", "+00:00"))
            self.duration_ms = int((end_dt - start_dt).total_seconds() * 1000)
    
    def mark_failed(self, error_message: str) -> None:
        """Mark node as failed with error message."""
        self.status = NodeStatus.FAILED
        self.error_message = error_message
        
        from datetime import datetime
        self.completed_at = datetime.utcnow().isoformat() + "Z"
        
        # Calculate duration
        if self.started_at:
            start_dt = datetime.fromisoformat(self.started_at.replace("Z", "+00:00"))
            end_dt = datetime.fromisoformat(self.completed_at.replace("Z", "+00:00"))
            self.duration_ms = int((end_dt - start_dt).total_seconds() * 1000)
    
    def add_ai_usage(self, tokens: int, cost: float) -> None:
        """Add AI usage statistics."""
        self.ai_calls_made += 1
        self.tokens_used += tokens
        self.cost_incurred += cost


class WorkflowContext(BaseModel):
    """
    Context object for workflow execution.
    
    Provides access to external services and configuration
    throughout the workflow execution.
    """
    
    # Database session
    db_session: Any = Field(description="Database session for persistence")
    
    # Service instances
    openrouter_client: Any = Field(description="OpenRouter AI client")
    qdrant_service: Any = Field(description="Qdrant vector database service")
    
    # Configuration
    settings: Dict[str, Any] = Field(default_factory=dict, description="Workflow configuration")
    
    # Callbacks and hooks
    progress_callback: Optional[Callable] = Field(default=None, description="Progress update callback")
    error_callback: Optional[Callable] = Field(default=None, description="Error handling callback")
    
    # Execution context
    logger: Any = Field(description="Logger instance")
    
    def get_model(self, model_name: str) -> Optional[Any]:
        """Get AI model configuration."""
        from ..schemas.ai.models import get_model
        return get_model(model_name)
    
    def log(self, level: str, message: str, **kwargs) -> None:
        """Log a message with context."""
        if self.logger:
            getattr(self.logger, level)(message, **kwargs)