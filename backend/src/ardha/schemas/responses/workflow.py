"""
Workflow response schemas for API output.

This module contains Pydantic models for formatting
workflow-related API responses.
"""

from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class WorkflowResponse(BaseModel):
    """Response schema for workflow details."""
    
    id: UUID = Field(..., description="Workflow ID")
    name: str = Field(..., description="Workflow name")
    description: Optional[str] = Field(None, description="Workflow description")
    workflow_type: str = Field(..., description="Workflow type")
    node_sequence: Dict[str, List[str]] = Field(..., description="Node execution sequence")
    default_parameters: Dict[str, Any] = Field(..., description="Default parameters")
    user_id: UUID = Field(..., description="Owner user ID")
    project_id: Optional[UUID] = Field(None, description="Associated project ID")
    created_at: str = Field(..., description="Creation timestamp")
    updated_at: str = Field(..., description="Last update timestamp")
    
    model_config = ConfigDict(from_attributes=True)


class WorkflowExecutionResponse(BaseModel):
    """Response schema for workflow execution details."""
    
    id: UUID = Field(..., description="Execution ID")
    workflow_id: UUID = Field(..., description="Workflow ID")
    user_id: UUID = Field(..., description="User ID who executed")
    project_id: Optional[UUID] = Field(None, description="Associated project ID")
    initial_request: str = Field(..., description="Initial request/prompt")
    context: Dict[str, Any] = Field(..., description="Execution context")
    parameters: Dict[str, Any] = Field(..., description="Execution parameters")
    status: str = Field(..., description="Execution status")
    current_node: Optional[str] = Field(None, description="Currently executing node")
    completed_nodes: List[str] = Field(..., description="Completed nodes")
    failed_nodes: List[str] = Field(..., description="Failed nodes")
    results: Dict[str, Any] = Field(..., description="Execution results")
    artifacts: Dict[str, Any] = Field(..., description="Generated artifacts")
    metadata: Dict[str, Any] = Field(..., description="Execution metadata")
    ai_calls: List[Dict[str, Any]] = Field(..., description="AI calls made")
    token_usage: Dict[str, int] = Field(..., description="Token usage statistics")
    total_cost: float = Field(..., description="Total cost incurred")
    errors: List[Dict[str, Any]] = Field(..., description="Execution errors")
    retry_count: int = Field(..., description="Number of retries")
    created_at: str = Field(..., description="Creation timestamp")
    started_at: Optional[str] = Field(None, description="Start timestamp")
    completed_at: Optional[str] = Field(None, description="Completion timestamp")
    last_activity: Optional[str] = Field(None, description="Last activity timestamp")
    
    model_config = ConfigDict(from_attributes=True)


class WorkflowStatusResponse(BaseModel):
    """Response schema for workflow execution status."""
    
    execution_id: UUID = Field(..., description="Execution ID")
    workflow_id: UUID = Field(..., description="Workflow ID")
    status: str = Field(..., description="Current status")
    current_node: Optional[str] = Field(None, description="Currently executing node")
    completed_nodes: List[str] = Field(..., description="Completed nodes")
    failed_nodes: List[str] = Field(..., description="Failed nodes")
    progress: float = Field(..., description="Progress percentage (0-100)")
    results: Dict[str, Any] = Field(..., description="Execution results")
    artifacts: Dict[str, Any] = Field(..., description="Generated artifacts")
    errors: List[Dict[str, Any]] = Field(..., description="Execution errors")
    total_cost: float = Field(..., description="Total cost incurred")
    token_usage: Dict[str, int] = Field(..., description="Token usage statistics")
    last_activity: Optional[str] = Field(None, description="Last activity timestamp")
    
    model_config = ConfigDict(from_attributes=True)


class WorkflowListResponse(BaseModel):
    """Response schema for paginated workflow execution list."""
    
    executions: List[WorkflowExecutionResponse] = Field(..., description="List of executions")
    total: int = Field(..., description="Total number of executions")
    limit: int = Field(..., description="Page limit")
    offset: int = Field(..., description="Page offset")
    
    model_config = ConfigDict(from_attributes=True)


class WorkflowNodeResponse(BaseModel):
    """Response schema for workflow node information."""
    
    name: str = Field(..., description="Node name")
    type: str = Field(..., description="Node type")
    description: str = Field(..., description="Node description")
    status: str = Field(..., description="Node status")
    started_at: Optional[str] = Field(None, description="Start timestamp")
    completed_at: Optional[str] = Field(None, description="Completion timestamp")
    duration_ms: Optional[int] = Field(None, description="Duration in milliseconds")
    input_data: Optional[Dict[str, Any]] = Field(None, description="Node input data")
    output_data: Optional[Dict[str, Any]] = Field(None, description="Node output data")
    error_message: Optional[str] = Field(None, description="Error message if failed")
    retry_count: int = Field(0, description="Number of retries")
    ai_calls_made: int = Field(0, description="Number of AI calls made")
    tokens_used: int = Field(0, description="Tokens used by this node")
    cost_incurred: float = Field(0.0, description="Cost incurred by this node")
    
    model_config = ConfigDict(from_attributes=True)


class WorkflowStatsResponse(BaseModel):
    """Response schema for workflow statistics."""
    
    total_executions: int = Field(..., description="Total executions")
    successful_executions: int = Field(..., description="Successful executions")
    failed_executions: int = Field(..., description="Failed executions")
    average_duration: Optional[float] = Field(None, description="Average execution duration (seconds)")
    total_cost: float = Field(..., description="Total cost incurred")
    total_tokens: int = Field(..., description="Total tokens used")
    most_used_workflow_type: str = Field(..., description="Most used workflow type")
    
    model_config = ConfigDict(from_attributes=True)


class WorkflowCancelResponse(BaseModel):
    """Response schema for workflow cancellation."""
    
    message: str = Field(..., description="Cancellation message")
    execution_id: UUID = Field(..., description="Cancelled execution ID")
    reason: Optional[str] = Field(None, description="Cancellation reason")
    cancelled_at: str = Field(..., description="Cancellation timestamp")
    
    model_config = ConfigDict(from_attributes=True)