"""
Task Generation workflow API endpoints.

This module provides REST API endpoints for the Task Generation workflow
that creates OpenSpec proposals and task breakdowns from PRD documents.
"""

import asyncio
import json
import logging
from typing import Any, Dict, List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from ardha.core.database import get_db
from ardha.core.security import get_current_active_user
from ardha.models.user import User
from ardha.schemas.workflows.task_generation import (
    TaskGenerationWorkflowConfig, TaskGenerationProgressUpdate, TaskGenerationState
)
from ardha.workflows.task_generation_workflow import (
    get_task_generation_workflow, TaskGenerationWorkflow
)
from ardha.workflows.nodes.task_generation_nodes import TaskGenerationNodeException

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/task-generation", tags=["task-generation"])


# Request/Response schemas
class TaskGenerationRequest(BaseModel):
    """Request schema for task generation workflow."""
    
    prd_content: str = Field(..., description="PRD document content")
    project_id: Optional[UUID] = Field(None, description="Associated project ID")
    project_context: Optional[Dict[str, Any]] = Field(None, description="Project context and constraints")
    existing_tasks: Optional[List[Dict[str, Any]]] = Field(None, description="Existing tasks in project")
    parameters: Optional[Dict[str, Any]] = Field(None, description="Workflow parameters")
    config: Optional[TaskGenerationWorkflowConfig] = Field(None, description="Workflow configuration")
    
    class Config:
        """Pydantic configuration."""
        populate_by_name = True


class TaskGenerationResponse(BaseModel):
    """Response schema for task generation workflow."""
    
    workflow_id: UUID = Field(..., description="Workflow execution ID")
    execution_id: UUID = Field(..., description="Execution ID")
    status: str = Field(..., description="Workflow status")
    message: str = Field(..., description="Status message")
    progress_url: str = Field(..., description="URL for progress tracking")
    
    class Config:
        """Pydantic configuration."""
        populate_by_name = True


class TaskGenerationStatusResponse(BaseModel):
    """Response schema for task generation status."""
    
    execution_id: UUID = Field(..., description="Execution ID")
    workflow_id: UUID = Field(..., description="Workflow ID")
    status: str = Field(..., description="Current status")
    current_step: str = Field(..., description="Current step")
    progress_percentage: float = Field(..., description="Progress percentage")
    completed_steps: List[str] = Field(..., description="Completed steps")
    failed_steps: List[str] = Field(..., description="Failed steps")
    quality_score: float = Field(..., description="Overall quality score")
    task_summary: Dict[str, Any] = Field(..., description="Task generation summary")
    errors: List[Dict[str, Any]] = Field(..., description="Errors encountered")
    created_at: str = Field(..., description="Creation timestamp")
    started_at: Optional[str] = Field(None, description="Start timestamp")
    completed_at: Optional[str] = Field(None, description="Completion timestamp")
    
    class Config:
        """Pydantic configuration."""
        populate_by_name = True


class TaskGenerationResultResponse(BaseModel):
    """Response schema for task generation results."""
    
    execution_id: UUID = Field(..., description="Execution ID")
    workflow_id: UUID = Field(..., description="Workflow ID")
    status: str = Field(..., description="Final status")
    prd_analysis: Dict[str, Any] = Field(..., description="PRD analysis results")
    task_breakdown: List[Dict[str, Any]] = Field(..., description="Complete task breakdown")
    dependencies: List[Dict[str, Any]] = Field(..., description="Task dependencies")
    effort_estimates: Dict[str, Any] = Field(..., description="Effort estimates")
    openspec_proposal: Dict[str, Any] = Field(..., description="OpenSpec proposal")
    change_directory_path: str = Field(..., description="OpenSpec change directory path")
    quality_metrics: Dict[str, float] = Field(..., description="Quality metrics")
    step_results: List[Dict[str, Any]] = Field(..., description="Step results")
    total_cost: float = Field(..., description="Total AI cost")
    created_at: str = Field(..., description="Creation timestamp")
    completed_at: Optional[str] = Field(None, description="Completion timestamp")
    
    class Config:
        """Pydantic configuration."""
        populate_by_name = True


@router.post("/execute", response_model=TaskGenerationResponse)
async def execute_task_generation(
    request: TaskGenerationRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Execute the Task Generation workflow.
    
    This endpoint starts the task generation workflow that analyzes PRD content,
    creates task breakdowns, defines dependencies, estimates effort, and generates
    an OpenSpec proposal.
    
    Args:
        request: Task generation request
        background_tasks: FastAPI background tasks
        current_user: Authenticated user
        db: Database session
        
    Returns:
        Task generation execution response with progress tracking URL
    """
    try:
        logger.info(f"User {current_user.id} starting task generation workflow")
        
        # Get workflow instance
        workflow = get_task_generation_workflow(request.config)
        
        # Execute workflow asynchronously
        async def execute_workflow():
            try:
                await workflow.execute(
                    prd_content=request.prd_content,
                    user_id=current_user.id,
                    project_id=request.project_id,
                    project_context=request.project_context,
                    existing_tasks=request.existing_tasks,
                    parameters=request.parameters,
                    progress_callback=None,  # Progress handled via separate endpoint
                )
            except TaskGenerationNodeException as e:
                logger.error(f"Task generation workflow failed: {e}")
                # Error is stored in workflow state, no need to raise
            except Exception as e:
                logger.error(f"Unexpected error in task generation workflow: {e}")
                # Error is stored in workflow state, no need to raise
        
        # Start workflow in background
        background_tasks.add_task(execute_workflow)
        
        # For now, return a mock response since we can't get the execution ID
        # without actually executing the workflow
        from uuid import uuid4
        execution_id = uuid4()
        workflow_id = uuid4()
        
        return TaskGenerationResponse(
            workflow_id=workflow_id,
            execution_id=execution_id,
            status="pending",
            message="Task generation workflow started",
            progress_url=f"/api/v1/task-generation/{execution_id}/progress"
        )
        
    except Exception as e:
        logger.error(f"Failed to start task generation workflow: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to start task generation workflow: {str(e)}"
        )


@router.get("/{execution_id}/status", response_model=TaskGenerationStatusResponse)
async def get_task_generation_status(
    execution_id: UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Get the status of a task generation workflow execution.
    
    Args:
        execution_id: Workflow execution ID
        current_user: Authenticated user
        db: Database session
        
    Returns:
        Current workflow status and progress information
    """
    try:
        logger.info(f"User {current_user.id} requesting status for execution {execution_id}")
        
        # Get workflow instance
        workflow = get_task_generation_workflow()
        
        # Get execution status
        state = await workflow.get_execution_status(execution_id)
        if not state:
            raise HTTPException(
                status_code=404,
                detail=f"Task generation execution {execution_id} not found"
            )
        
        # Check permissions (user can only see their own executions)
        if state.user_id != current_user.id:
            raise HTTPException(
                status_code=403,
                detail="Access denied to this workflow execution"
            )
        
        # Build response
        return TaskGenerationStatusResponse(
            execution_id=state.execution_id,
            workflow_id=state.workflow_id,
            status=state.status.value if hasattr(state.status, 'value') else str(state.status),
            current_step=state.current_task_step,
            progress_percentage=state.task_progress_percentage,
            completed_steps=state.completed_task_steps,
            failed_steps=state.failed_task_steps,
            quality_score=state.calculate_task_quality_score(),
            task_summary=state.get_task_summary(),
            errors=state.errors,
            created_at=state.created_at or "",
            started_at=state.started_at,
            completed_at=state.completed_at,
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get task generation status: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get task generation status: {str(e)}"
        )


@router.get("/{execution_id}/progress")
async def get_task_generation_progress(
    execution_id: UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Get real-time progress updates for a task generation workflow execution.
    
    This endpoint provides Server-Sent Events (SSE) for real-time progress
    tracking during workflow execution.
    
    Args:
        execution_id: Workflow execution ID
        current_user: Authenticated user
        db: Database session
        
    Returns:
        Streaming response with progress updates
    """
    try:
        logger.info(f"User {current_user.id} requesting progress stream for execution {execution_id}")
        
        # Get workflow instance
        workflow = get_task_generation_workflow()
        
        # Check if execution exists and user has permission
        state = await workflow.get_execution_status(execution_id)
        if not state:
            raise HTTPException(
                status_code=404,
                detail=f"Task generation execution {execution_id} not found"
            )
        
        if state.user_id != current_user.id:
            raise HTTPException(
                status_code=403,
                detail="Access denied to this workflow execution"
            )
        
        async def progress_stream():
            """Generate SSE progress updates."""
            try:
                # Get initial state
                current_state = await workflow.get_execution_status(execution_id)
                if not current_state:
                    return
                
                # Send initial status
                progress_data = {
                    "type": "status",
                    "execution_id": str(execution_id),
                    "status": current_state.status.value if hasattr(current_state.status, 'value') else str(current_state.status),
                    "current_step": current_state.current_task_step,
                    "progress_percentage": current_state.task_progress_percentage,
                    "completed_steps": current_state.completed_task_steps,
                    "failed_steps": current_state.failed_task_steps,
                    "quality_score": current_state.calculate_task_quality_score(),
                    "task_summary": current_state.get_task_summary(),
                    "timestamp": current_state._get_timestamp(),
                }
                
                yield f"data: {json.dumps(progress_data)}\n\n"
                
                # Continue polling for updates
                last_update = current_state.last_activity
                max_iterations = 300  # 5 minutes max
                iteration = 0
                
                while current_state.status in ["pending", "running"] and iteration < max_iterations:
                    await asyncio.sleep(1)  # Poll every second
                    
                    # Get updated state
                    updated_state = await workflow.get_execution_status(execution_id)
                    if not updated_state:
                        break
                    
                    # Check if there's an update
                    if (updated_state.last_activity != last_update or
                        updated_state.status != current_state.status):
                        
                        last_update = updated_state.last_activity
                        current_state = updated_state
                        
                        progress_data = {
                            "type": "progress",
                            "execution_id": str(execution_id),
                            "status": current_state.status.value if hasattr(current_state.status, 'value') else str(current_state.status),
                            "current_step": current_state.current_task_step,
                            "progress_percentage": current_state.task_progress_percentage,
                            "completed_steps": current_state.completed_task_steps,
                            "failed_steps": current_state.failed_task_steps,
                            "quality_score": current_state.calculate_task_quality_score(),
                            "task_summary": current_state.get_task_summary(),
                            "timestamp": current_state._get_timestamp(),
                        }
                        
                        yield f"data: {json.dumps(progress_data)}\n\n"
                    
                    iteration += 1
                
                # Send final status
                final_state = await workflow.get_execution_status(execution_id)
                if final_state:
                    progress_data = {
                        "type": "completed",
                        "execution_id": str(execution_id),
                        "status": final_state.status.value if hasattr(final_state.status, 'value') else str(final_state.status),
                        "current_step": final_state.current_task_step,
                        "progress_percentage": final_state.task_progress_percentage,
                        "completed_steps": final_state.completed_task_steps,
                        "failed_steps": final_state.failed_task_steps,
                        "quality_score": final_state.calculate_task_quality_score(),
                        "task_summary": final_state.get_task_summary(),
                        "timestamp": final_state._get_timestamp(),
                    }
                    
                    yield f"data: {json.dumps(progress_data)}\n\n"
                
            except Exception as e:
                logger.error(f"Error in progress stream: {e}")
                from datetime import datetime
                error_data = {
                    "type": "error",
                    "execution_id": str(execution_id),
                    "error": str(e),
                    "timestamp": datetime.utcnow().isoformat(),
                }
                yield f"data: {json.dumps(error_data)}\n\n"
        
        return StreamingResponse(
            progress_stream(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "Access-Control-Allow-Origin": "*",
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to create progress stream: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to create progress stream: {str(e)}"
        )


@router.get("/{execution_id}/results", response_model=TaskGenerationResultResponse)
async def get_task_generation_results(
    execution_id: UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Get the complete results of a task generation workflow execution.
    
    Args:
        execution_id: Workflow execution ID
        current_user: Authenticated user
        db: Database session
        
    Returns:
        Complete workflow results including task breakdown and OpenSpec proposal
    """
    try:
        logger.info(f"User {current_user.id} requesting results for execution {execution_id}")
        
        # Get workflow instance
        workflow = get_task_generation_workflow()
        
        # Get execution state
        state = await workflow.get_execution_status(execution_id)
        if not state:
            raise HTTPException(
                status_code=404,
                detail=f"Task generation execution {execution_id} not found"
            )
        
        # Check permissions
        if state.user_id != current_user.id:
            raise HTTPException(
                status_code=403,
                detail="Access denied to this workflow execution"
            )
        
        # Check if workflow is completed
        if state.status not in ["completed", "failed"]:
            raise HTTPException(
                status_code=400,
                detail=f"Task generation execution {execution_id} is not yet completed"
            )
        
        # Build response
        return TaskGenerationResultResponse(
            execution_id=state.execution_id,
            workflow_id=state.workflow_id,
            status=state.status.value if hasattr(state.status, 'value') else str(state.status),
            prd_analysis=state.prd_analysis or {},
            task_breakdown=state.task_breakdown or [],
            dependencies=state.task_dependencies or [],
            effort_estimates=state.effort_estimates or {},
            openspec_proposal=state.openspec_proposal or {},
            change_directory_path=state.change_directory_path or "",
            quality_metrics={
                "prd_analysis_quality": state.prd_analysis_quality,
                "task_breakdown_completeness": state.task_breakdown_completeness,
                "dependency_accuracy": state.dependency_accuracy,
                "effort_estimation_quality": state.effort_estimation_quality,
                "openspec_quality_score": state.openspec_quality_score,
                "overall_quality_score": state.calculate_task_quality_score(),
            },
            step_results=[
                result if isinstance(result, dict)
                else result.model_dump() if hasattr(result, 'model_dump') and callable(getattr(result, 'model_dump'))
                else result.dict() if hasattr(result, 'dict') and callable(getattr(result, 'dict'))
                else {}
                for result in state.step_results
            ],
            total_cost=state.total_cost,
            created_at=state.created_at or "",
            completed_at=state.completed_at,
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get task generation results: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get task generation results: {str(e)}"
        )


@router.delete("/{execution_id}")
async def cancel_task_generation(
    execution_id: UUID,
    reason: Optional[str] = Query(None, description="Cancellation reason"),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Cancel a running task generation workflow execution.
    
    Args:
        execution_id: Workflow execution ID
        reason: Optional cancellation reason
        current_user: Authenticated user
        db: Database session
        
    Returns:
        Cancellation confirmation
    """
    try:
        logger.info(f"User {current_user.id} cancelling execution {execution_id}")
        
        # Get workflow instance
        workflow = get_task_generation_workflow()
        
        # Check if execution exists and user has permission
        state = await workflow.get_execution_status(execution_id)
        if not state:
            raise HTTPException(
                status_code=404,
                detail=f"Task generation execution {execution_id} not found"
            )
        
        if state.user_id != current_user.id:
            raise HTTPException(
                status_code=403,
                detail="Access denied to this workflow execution"
            )
        
        # Cancel execution
        success = await workflow.cancel_execution(execution_id, reason)
        if not success:
            raise HTTPException(
                status_code=400,
                detail=f"Cannot cancel execution {execution_id}. It may already be completed."
            )
        
        return {
            "message": f"Task generation execution {execution_id} cancelled successfully",
            "execution_id": str(execution_id),
            "reason": reason,
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to cancel task generation execution: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to cancel task generation execution: {str(e)}"
        )


@router.get("/config")
async def get_task_generation_config(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Get the default task generation workflow configuration.
    
    Args:
        current_user: Authenticated user
        db: Database session
        
    Returns:
        Default workflow configuration
    """
    try:
        config = TaskGenerationWorkflowConfig(openspec_template_path=None)
        return config.model_dump()
        
    except Exception as e:
        logger.error(f"Failed to get task generation config: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get task generation config: {str(e)}"
        )


@router.get("/executions")
async def list_task_generation_executions(
    limit: int = Query(20, ge=1, le=100, description="Maximum number of executions to return"),
    offset: int = Query(0, ge=0, description="Number of executions to skip"),
    status: Optional[str] = Query(None, description="Filter by status"),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """
    List task generation workflow executions for the current user.
    
    Args:
        limit: Maximum number of executions to return
        offset: Number of executions to skip
        status: Optional status filter
        current_user: Authenticated user
        db: Database session
        
    Returns:
        List of workflow executions
    """
    try:
        logger.info(f"User {current_user.id} listing task generation executions")
        
        # For now, return empty list since we don't have persistence
        # In a real implementation, this would query the database
        return {
            "executions": [],
            "total": 0,
            "limit": limit,
            "offset": offset,
            "status_filter": status,
        }
        
    except Exception as e:
        logger.error(f"Failed to list task generation executions: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to list task generation executions: {str(e)}"
        )