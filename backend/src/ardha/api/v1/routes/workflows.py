"""
Workflow API endpoints.

This module provides REST API endpoints for managing
and executing AI workflows using workflow orchestration service.
"""

import asyncio
import logging
from typing import Any, Dict, List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse

from ....core.security import get_current_user
from ....schemas.requests.workflow import (
    WorkflowCreateRequest, WorkflowExecuteRequest
)
from ....schemas.responses.workflow import (
    WorkflowResponse, WorkflowExecutionResponse,
    WorkflowStatusResponse, WorkflowListResponse
)
from ....workflows.orchestrator import get_workflow_orchestrator
from ....workflows.state import WorkflowType
from ....models.user import User

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/workflows", tags=["workflows"])


@router.post("/", response_model=WorkflowResponse)
async def create_workflow(
    request: WorkflowCreateRequest,
    current_user: User = Depends(get_current_user),
) -> WorkflowResponse:
    """
    Create a new workflow.
    
    Args:
        request: Workflow creation request
        current_user: Authenticated user
        
    Returns:
        Created workflow details
        
    Raises:
        HTTPException: If workflow creation fails
    """
    try:
        orchestrator = get_workflow_orchestrator()
        
        # Convert workflow type string to enum
        workflow_type = WorkflowType(request.workflow_type)
        
        # For now, return a mock response since create_workflow is not implemented
        from uuid import uuid4
        workflow_id = uuid4()
        
        return WorkflowResponse(
            id=workflow_id,
            name=request.name,
            description=request.description,
            workflow_type=request.workflow_type,
            node_sequence={"nodes": request.node_sequence or []},
            default_parameters=request.default_parameters or {},
            user_id=current_user.id,
            project_id=request.project_id,
            created_at="2024-01-01T00:00:00Z",
            updated_at="2024-01-01T00:00:00Z",
        )
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to create workflow: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/execute", response_model=WorkflowExecutionResponse)
async def execute_workflow(
    request: WorkflowExecuteRequest,
    current_user: User = Depends(get_current_user),
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
        orchestrator = get_workflow_orchestrator()
        
        # Convert workflow type string to enum
        workflow_type = WorkflowType(request.workflow_type)
        
        # Execute workflow
        state = await orchestrator.execute_workflow(
            workflow_type=workflow_type,
            initial_request=request.initial_request,
            user_id=current_user.id,
            project_id=request.project_id,
            parameters=request.parameters,
            context=request.context,
        )
        
        # Calculate total tokens safely
        total_tokens = 0
        if state.token_usage:
            for v in state.token_usage.values():
                if isinstance(v, (int, float)):
                    total_tokens += v
        
        return WorkflowExecutionResponse(
            id=state.execution_id,
            workflow_id=state.workflow_id,
            user_id=state.user_id,
            project_id=state.project_id,
            initial_request=state.initial_request,
            context=state.context,
            parameters=state.parameters,
            status=state.status,
            current_node=state.current_node,
            completed_nodes=state.completed_nodes,
            failed_nodes=state.failed_nodes,
            results=state.results,
            artifacts=state.artifacts,
            metadata=state.metadata,
            ai_calls=state.ai_calls,
            token_usage={"total": int(total_tokens)},
            total_cost=state.total_cost,
            errors=state.errors,
            retry_count=state.retry_count,
            created_at=state.created_at or "",
            started_at=state.started_at,
            completed_at=state.completed_at,
            last_activity=state.last_activity,
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
        orchestrator = get_workflow_orchestrator()
        
        state = await orchestrator.get_execution_status(execution_id)
        if not state:
            raise HTTPException(status_code=404, detail="Execution not found")
        
        # Check if user owns this execution
        if state.user_id != current_user.id:
            raise HTTPException(status_code=403, detail="Access denied")
        
        # Calculate total tokens safely
        total_tokens = 0
        if state.token_usage:
            for v in state.token_usage.values():
                if isinstance(v, (int, float)):
                    total_tokens += v
        
        return WorkflowStatusResponse(
            execution_id=state.execution_id,
            workflow_id=state.workflow_id,
            status=state.status,
            current_node=state.current_node,
            completed_nodes=state.completed_nodes,
            failed_nodes=state.failed_nodes,
            progress=state.get_progress(),
            results=state.results,
            artifacts=state.artifacts,
            errors=state.errors,
            total_cost=state.total_cost,
            token_usage={"total": int(total_tokens)},
            last_activity=state.last_activity,
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get execution status: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/executions/{execution_id}/cancel")
async def cancel_execution(
    execution_id: UUID,
    reason: Optional[str] = None,
    current_user: User = Depends(get_current_user),
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
        orchestrator = get_workflow_orchestrator()
        
        # Get execution to verify ownership
        state = await orchestrator.get_execution_status(execution_id)
        if not state:
            raise HTTPException(status_code=404, detail="Execution not found")
        
        # Check if user owns this execution
        if state.user_id != current_user.id:
            raise HTTPException(status_code=403, detail="Access denied")
        
        # Cancel execution
        success = await orchestrator.cancel_execution(execution_id, reason)
        if not success:
            raise HTTPException(status_code=400, detail="Cannot cancel completed execution")
        
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


@router.get("/types", response_model=List[str])
async def get_workflow_types(
    current_user: User = Depends(get_current_user),
) -> List[str]:
    """
    Get available workflow types.
    
    Args:
        current_user: Authenticated user
        
    Returns:
        List of available workflow types
    """
    try:
        return [workflow_type.value for workflow_type in WorkflowType]
        
    except Exception as e:
        logger.error(f"Failed to get workflow types: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/executions", response_model=WorkflowListResponse)
async def list_executions(
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    status: Optional[str] = Query(None),
    current_user: User = Depends(get_current_user),
) -> WorkflowListResponse:
    """
    List workflow executions for current user.
    
    Args:
        limit: Maximum number of executions to return
        offset: Number of executions to skip
        status: Filter by execution status
        current_user: Authenticated user
        
    Returns:
        List of workflow executions
    """
    try:
        orchestrator = get_workflow_orchestrator()
        
        # Get all active executions for this user
        user_executions = []
        for execution_id, state in orchestrator.active_executions.items():
            if state.user_id == current_user.id:
                # Filter by status if provided
                if status and state.status.value != status:
                    continue
                
                # Calculate total tokens safely
                total_tokens = 0
                if state.token_usage:
                    for v in state.token_usage.values():
                        if isinstance(v, (int, float)):
                            total_tokens += v
                
                user_executions.append(WorkflowExecutionResponse(
                    id=state.execution_id,
                    workflow_id=state.workflow_id,
                    user_id=state.user_id,
                    project_id=state.project_id,
                    initial_request=state.initial_request,
                    context=state.context,
                    parameters=state.parameters,
                    status=state.status,
                    current_node=state.current_node,
                    completed_nodes=state.completed_nodes,
                    failed_nodes=state.failed_nodes,
                    results=state.results,
                    artifacts=state.artifacts,
                    metadata=state.metadata,
                    ai_calls=state.ai_calls,
                    token_usage={"total": int(total_tokens)},
                    total_cost=state.total_cost,
                    errors=state.errors,
                    retry_count=state.retry_count,
                    created_at=state.created_at or "",
                    started_at=state.started_at,
                    completed_at=state.completed_at,
                    last_activity=state.last_activity,
                ))
        
        # Apply pagination
        total = len(user_executions)
        executions = user_executions[offset:offset + limit]
        
        return WorkflowListResponse(
            executions=executions,
            total=total,
            limit=limit,
            offset=offset,
        )
        
    except Exception as e:
        logger.error(f"Failed to list executions: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/executions/{execution_id}/stream")
async def stream_execution(
    execution_id: UUID,
    current_user: User = Depends(get_current_user),
) -> StreamingResponse:
    """
    Stream workflow execution updates in real-time.
    
    Args:
        execution_id: Execution identifier
        current_user: Authenticated user
        
    Returns:
        Server-sent events stream
        
    Raises:
        HTTPException: If streaming fails
    """
    try:
        orchestrator = get_workflow_orchestrator()
        
        # Get execution to verify ownership
        state = await orchestrator.get_execution_status(execution_id)
        if not state:
            raise HTTPException(status_code=404, detail="Execution not found")
        
        # Check if user owns this execution
        if state.user_id != current_user.id:
            raise HTTPException(status_code=403, detail="Access denied")
        
        async def event_stream():
            """Generate server-sent events for execution updates."""
            try:
                # Send initial status
                yield f"data: {state.status.value}\n\n"
                
                # Poll for updates (simplified - in production use WebSocket)
                last_update = state.last_activity
                while state.status.value in ["pending", "running"]:
                    await asyncio.sleep(1)  # Poll every second
                    
                    current_state = await orchestrator.get_execution_status(execution_id)
                    if current_state and current_state.last_activity != last_update:
                        yield f"data: {current_state.status.value}\n\n"
                        last_update = current_state.last_activity
                    
                    # Exit if execution is complete
                    if current_state and current_state.status.value not in ["pending", "running"]:
                        break
                
                # Send completion event
                yield "event: complete\ndata: {}\n\n"
                
            except Exception as e:
                logger.error(f"Error in event stream: {e}")
                yield f"event: error\ndata: {{'error': '{str(e)}'}}\n\n"
        
        return StreamingResponse(
            event_stream(),
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
        logger.error(f"Failed to stream execution: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")