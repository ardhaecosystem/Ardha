"""
Workflow request schemas for API validation.

This module contains Pydantic models for validating
workflow-related API requests.
"""

from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, Field


class WorkflowCreateRequest(BaseModel):
    """Request schema for creating a new workflow."""
    
    name: str = Field(..., min_length=1, max_length=255, description="Workflow name")
    description: Optional[str] = Field(None, max_length=1000, description="Workflow description")
    workflow_type: str = Field(..., description="Type of workflow")
    node_sequence: Optional[List[str]] = Field(None, description="Sequence of nodes to execute")
    default_parameters: Optional[Dict[str, Any]] = Field(None, description="Default parameters")
    project_id: Optional[UUID] = Field(None, description="Associated project ID")
    
    class Config:
        json_schema_extra = {
            "example": {
                "name": "Research and Implementation",
                "description": "Research topic and implement solution",
                "workflow_type": "implement",
                "node_sequence": ["research", "architect", "implement"],
                "default_parameters": {
                    "max_retries": 3,
                    "timeout": 300
                },
                "project_id": "123e4567-e89b-12d3-a456-426614174000"
            }
        }


class WorkflowExecuteRequest(BaseModel):
    """Request schema for executing a workflow."""
    
    workflow_type: str = Field(..., description="Type of workflow to execute")
    initial_request: str = Field(..., min_length=1, max_length=10000, description="Initial request or prompt")
    project_id: Optional[UUID] = Field(None, description="Associated project ID")
    parameters: Optional[Dict[str, Any]] = Field(None, description="Workflow parameters")
    context: Optional[Dict[str, Any]] = Field(None, description="Additional context data")
    
    class Config:
        json_schema_extra = {
            "example": {
                "workflow_type": "implement",
                "initial_request": "Create a REST API for user management with CRUD operations",
                "project_id": "123e4567-e89b-12d3-a456-426614174000",
                "parameters": {
                    "max_retries": 3,
                    "timeout": 300
                },
                "context": {
                    "tech_stack": ["FastAPI", "PostgreSQL"],
                    "requirements": ["authentication", "validation"]
                }
            }
        }


class WorkflowUpdateRequest(BaseModel):
    """Request schema for updating a workflow."""
    
    name: Optional[str] = Field(None, min_length=1, max_length=255, description="Workflow name")
    description: Optional[str] = Field(None, max_length=1000, description="Workflow description")
    node_sequence: Optional[List[str]] = Field(None, description="Sequence of nodes to execute")
    default_parameters: Optional[Dict[str, Any]] = Field(None, description="Default parameters")
    
    class Config:
        json_schema_extra = {
            "example": {
                "name": "Updated Workflow Name",
                "description": "Updated description",
                "node_sequence": ["research", "implement"],
                "default_parameters": {
                    "max_retries": 5
                }
            }
        }