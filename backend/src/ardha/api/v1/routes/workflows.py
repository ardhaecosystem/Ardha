"""
Workflow API endpoints.

This module provides REST API endpoints for managing
and executing AI workflows using workflow service layer.
"""

import asyncio
import logging
from typing import Any, Dict, List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from ....core.database import get_db
from ....core.security import get_current_user
from ....models.user import User
from ....schemas.requests.workflow import WorkflowCreateRequest, WorkflowExecuteRequest
from ....schemas.responses.workflow import (
    WorkflowExecutionResponse,
    WorkflowListResponse,
    WorkflowResponse,
    WorkflowStatusResponse,
)
from ....services.workflow_service import WorkflowService
from ....workflows.state import WorkflowStatus, WorkflowType

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/workflows", tags=["workflows"])


@router.post("/execute", response_model=WorkflowExecutionResponse)
async def execute_workflow(
    request: WorkflowExecuteRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> WorkflowExecutionResponse:
    """
    Execute a workflow.

    Args:
        request: Workflow execution request
        current_user: Authenticated user

    Returns:
        Workflow execution details

    Raises:
        HTTPException: If execution fails
    """
    try:
        service = WorkflowService(db)

        # Execute workflow
        execution = await service.execute_workflow(
            user_id=current_user.id,
            workflow_type=request.workflow_type,
            initial_request=request.initial_request,
            project_id=request.project_id,
            parameters=request.parameters,
            context=request.context,
        )

        return WorkflowExecutionResponse(
            id=execution.id,
            workflow_id=execution.id,  # Same for now
            user_id=execution.user_id,
            project_id=execution.project_id,
            initial_request=execution.input_data.get("initial_request", ""),
            context=execution.input_data.get("context", {}),
            parameters=execution.input_data.get("parameters", {}),
            status=execution.status,
            current_node=None,
            completed_nodes=[],
            failed_nodes=[],
            results=execution.output_data.get("results", {}),
            artifacts=execution.output_data.get("artifacts", {}),
            metadata=execution.output_data.get("metadata", {}),
            ai_calls=[],
            token_usage={"total": execution.total_tokens},
            total_cost=float(execution.total_cost),
            errors=[],
            retry_count=0,
            created_at=execution.created_at.isoformat() if execution.created_at else "",
            started_at=execution.started_at.isoformat() if execution.started_at else None,
            completed_at=execution.completed_at.isoformat() if execution.completed_at else None,
            last_activity=execution.updated_at.isoformat() if execution.updated_at else None,
        )

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to execute workflow: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/executions/{execution_id}", response_model=WorkflowStatusResponse)
async def get_execution_status(
    execution_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> WorkflowStatusResponse:
    """
    Get workflow execution status.

    Args:
        execution_id: Execution identifier
        current_user: Authenticated user

    Returns:
        Current execution status

    Raises:
        HTTPException: If execution not found
    """
    try:
        service = WorkflowService(db)

        execution = await service.get_execution(execution_id, current_user.id)
        if not execution:
            raise HTTPException(status_code=404, detail="Execution not found")

        return WorkflowStatusResponse(
            execution_id=execution.id,
            workflow_id=execution.id,
            status=execution.status,
            current_node=None,
            completed_nodes=[],
            failed_nodes=[],
            progress=100.0 if execution.is_completed else 0.0,
            results=execution.output_data.get("results", {}),
            artifacts=execution.output_data.get("artifacts", {}),
            errors=[],
            total_cost=float(execution.total_cost),
            token_usage={"total": execution.total_tokens},
            last_activity=execution.updated_at.isoformat() if execution.updated_at else None,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get execution status: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/executions/{execution_id}/cancel")
async def cancel_workflow_execution(
    execution_id: UUID,
    reason: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """
    Cancel a running workflow execution.

    Args:
        execution_id: Execution identifier
        reason: Optional cancellation reason
        current_user: Authenticated user

    Returns:
        Cancellation confirmation

    Raises:
        HTTPException: If cancellation fails
    """
    try:
        service = WorkflowService(db)

        success = await service.cancel_execution(execution_id, current_user.id, reason)
        if not success:
            raise HTTPException(status_code=400, detail="Cannot cancel execution")

        return {
            "message": "Execution cancelled successfully",
            "execution_id": str(execution_id),
            "reason": reason,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to cancel execution: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/executions", response_model=WorkflowListResponse)
async def list_user_executions(
    status: Optional[WorkflowStatus] = Query(None, description="Filter by status"),
    workflow_type: Optional[str] = Query(None, description="Filter by workflow type"),
    project_id: Optional[UUID] = Query(None, description="Filter by project ID"),
    limit: int = Query(50, ge=1, le=100, description="Maximum number of results"),
    offset: int = Query(0, ge=0, description="Number of results to skip"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> WorkflowListResponse:
    """
    List workflow executions for the current user.

    Args:
        status: Optional status filter
        workflow_type: Optional workflow type filter
        project_id: Optional project ID filter
        limit: Maximum number of results
        offset: Number of results to skip
        current_user: Authenticated user

    Returns:
        List of workflow executions

    Raises:
        HTTPException: If listing fails
    """
    try:
        service = WorkflowService(db)

        executions = await service.list_user_executions(
            user_id=current_user.id,
            status=status,
            workflow_type=workflow_type,
            project_id=project_id,
            limit=limit,
            offset=offset,
        )

        # Convert to response format
        execution_responses = []
        for execution in executions:
            execution_responses.append(
                WorkflowExecutionResponse(
                    id=execution.id,
                    workflow_id=execution.id,
                    user_id=execution.user_id,
                    project_id=execution.project_id,
                    initial_request=execution.input_data.get("initial_request", ""),
                    context=execution.input_data.get("context", {}),
                    parameters=execution.input_data.get("parameters", {}),
                    status=execution.status,
                    current_node=None,
                    completed_nodes=[],
                    failed_nodes=[],
                    results=execution.output_data.get("results", {}),
                    artifacts=execution.output_data.get("artifacts", {}),
                    metadata=execution.output_data.get("metadata", {}),
                    ai_calls=[],
                    token_usage={"total": execution.total_tokens},
                    total_cost=float(execution.total_cost),
                    errors=[],
                    retry_count=0,
                    created_at=execution.created_at.isoformat() if execution.created_at else "",
                    started_at=execution.started_at.isoformat() if execution.started_at else None,
                    completed_at=(
                        execution.completed_at.isoformat() if execution.completed_at else None
                    ),
                    last_activity=(
                        execution.updated_at.isoformat() if execution.updated_at else None
                    ),
                )
            )

        return WorkflowListResponse(
            executions=execution_responses,
            total=len(execution_responses),
            limit=limit,
            offset=offset,
        )

    except Exception as e:
        logger.error(f"Failed to list executions: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.delete("/executions/{execution_id}")
async def delete_workflow_execution(
    execution_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Dict[str, str]:
    """
    Delete a workflow execution.

    Args:
        execution_id: Execution identifier
        current_user: Authenticated user

    Returns:
        Deletion confirmation

    Raises:
        HTTPException: If deletion fails
    """
    try:
        service = WorkflowService(db)

        success = await service.delete_execution(execution_id, current_user.id)
        if not success:
            raise HTTPException(status_code=404, detail="Execution not found")

        return {"message": "Execution deleted successfully"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete execution: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/types", response_model=List[str])
async def get_workflow_types() -> List[str]:
    """
    Get available workflow types.

    Returns:
        List of available workflow types
    """
    return [wt.value for wt in WorkflowType]


@router.get("/stats")
async def get_workflow_stats(
    workflow_type: Optional[str] = Query(None, description="Filter by workflow type"),
    project_id: Optional[UUID] = Query(None, description="Filter by project ID"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """
    Get workflow execution statistics.

    Args:
        workflow_type: Optional workflow type filter
        project_id: Optional project ID filter
        current_user: Authenticated user

    Returns:
        Workflow execution statistics

    Raises:
        HTTPException: If stats retrieval fails
    """
    try:
        service = WorkflowService(db)

        stats = await service.get_execution_stats(
            user_id=current_user.id, workflow_type=workflow_type, project_id=project_id
        )

        return stats

    except Exception as e:
        logger.error(f"Failed to get workflow stats: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")
