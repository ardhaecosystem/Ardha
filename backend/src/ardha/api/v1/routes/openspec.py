"""
OpenSpec Proposal API routes.

This module provides REST API endpoints for OpenSpec proposal management including:
- Proposal creation from filesystem
- Proposal lifecycle (approve, reject, archive)
- Task synchronization
- Content refresh
- List and filter operations
"""

import logging
from datetime import datetime
from pathlib import Path
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from ardha.core.database import get_db
from ardha.core.exceptions import (
    OpenSpecFileNotFoundError,
    OpenSpecParseError,
    OpenSpecValidationError,
)
from ardha.core.security import get_current_user
from ardha.models.user import User
from ardha.repositories.openspec import OpenSpecRepository
from ardha.schemas.requests.openspec_proposal import (
    OpenSpecProposalCreateRequest,
    OpenSpecProposalFilterRequest,
    OpenSpecProposalRejectRequest,
    OpenSpecProposalUpdateRequest,
)
from ardha.schemas.responses.openspec_proposal import (
    OpenSpecProposalListResponse,
    OpenSpecProposalPaginatedResponse,
    OpenSpecProposalResponse,
    OpenSpecProposalSyncResponse,
)
from ardha.schemas.responses.task import TaskResponse
from ardha.services.openspec_parser import OpenSpecParserService
from ardha.services.openspec_service import (
    InsufficientOpenSpecPermissionsError,
    OpenSpecProposalExistsError,
    OpenSpecProposalNotFoundError,
    OpenSpecService,
    ProposalNotApprovableError,
    ProposalNotEditableError,
    TaskSyncError,
)
from ardha.services.project_service import ProjectService
from ardha.services.task_service import TaskService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/openspec", tags=["openspec"])


# ============= Helper Functions =============


def _get_openspec_service(db: AsyncSession) -> OpenSpecService:
    """
    Create OpenSpec service with all dependencies.

    Args:
        db: Database session

    Returns:
        Configured OpenSpecService instance
    """
    # Initialize dependencies
    openspec_repo = OpenSpecRepository(db)
    project_root = Path("/home/veda/ardha-projects/Ardha")
    parser = OpenSpecParserService(project_root)
    task_service = TaskService(db)
    project_service = ProjectService(db)

    return OpenSpecService(
        openspec_repo=openspec_repo,
        parser=parser,
        task_service=task_service,
        project_service=project_service,
        db=db,
    )


def _build_proposal_response(proposal: Any) -> OpenSpecProposalResponse:
    """
    Build OpenSpecProposalResponse from model.

    Args:
        proposal: OpenSpecProposal model instance

    Returns:
        OpenSpecProposalResponse with populated fields
    """
    response_data = {
        "id": proposal.id,
        "project_id": proposal.project_id,
        "name": proposal.name,
        "directory_path": proposal.directory_path,
        "status": proposal.status,
        "created_by_user_id": proposal.created_by_user_id,
        "proposal_content": proposal.proposal_content,
        "tasks_content": proposal.tasks_content,
        "spec_delta_content": proposal.spec_delta_content,
        "metadata_json": proposal.metadata_json,
        "approved_by_user_id": proposal.approved_by_user_id,
        "approved_at": proposal.approved_at,
        "archived_at": proposal.archived_at,
        "completion_percentage": proposal.completion_percentage,
        "task_sync_status": proposal.task_sync_status,
        "last_sync_at": proposal.last_sync_at,
        "sync_error_message": proposal.sync_error_message,
        "created_at": proposal.created_at,
        "updated_at": proposal.updated_at,
        "is_editable": proposal.is_editable,
        "can_approve": proposal.can_approve,
    }

    # Add creator info if available
    if proposal.created_by:
        response_data["created_by_username"] = proposal.created_by.username
        response_data["created_by_full_name"] = proposal.created_by.full_name

    # Add approver info if available
    if proposal.approved_by:
        response_data["approved_by_username"] = proposal.approved_by.username
        response_data["approved_by_full_name"] = proposal.approved_by.full_name

    return OpenSpecProposalResponse(**response_data)


def _build_proposal_list_response(proposal: Any) -> OpenSpecProposalListResponse:
    """
    Build OpenSpecProposalListResponse from model (lighter version).

    Args:
        proposal: OpenSpecProposal model instance

    Returns:
        OpenSpecProposalListResponse with summary fields
    """
    response_data = {
        "id": proposal.id,
        "project_id": proposal.project_id,
        "name": proposal.name,
        "status": proposal.status,
        "created_by_user_id": proposal.created_by_user_id,
        "approved_by_user_id": proposal.approved_by_user_id,
        "completion_percentage": proposal.completion_percentage,
        "task_sync_status": proposal.task_sync_status,
        "created_at": proposal.created_at,
        "updated_at": proposal.updated_at,
    }

    # Add creator username if available
    if proposal.created_by:
        response_data["created_by_username"] = proposal.created_by.username

    # Add approver username if available
    if proposal.approved_by:
        response_data["approved_by_username"] = proposal.approved_by.username

    return OpenSpecProposalListResponse(**response_data)


# ============= Proposal CRUD Endpoints =============


@router.post(
    "/projects/{project_id}/proposals",
    response_model=OpenSpecProposalResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create proposal from filesystem",
    description="Create an OpenSpec proposal by reading from the filesystem.",
)
async def create_proposal(
    project_id: UUID,
    proposal_data: OpenSpecProposalCreateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> OpenSpecProposalResponse:
    """
    Create new OpenSpec proposal from filesystem.

    Reads proposal directory from openspec/changes/ and creates database record.
    Requires project member permissions.

    Args:
        project_id: Project UUID
        proposal_data: Proposal creation request
        current_user: Authenticated user
        db: Database session

    Returns:
        Created proposal with full details

    Raises:
        400: Validation error (invalid proposal structure)
        403: Forbidden (insufficient permissions)
        404: Not found (proposal directory not found on filesystem)
        409: Conflict (proposal name already exists in database)
    """
    service = _get_openspec_service(db)

    try:
        proposal = await service.create_from_filesystem(
            project_id=project_id,
            proposal_name=proposal_data.proposal_name,
            user_id=current_user.id,
        )

        await db.commit()
        await db.refresh(proposal)

        return _build_proposal_response(proposal)

    except InsufficientOpenSpecPermissionsError as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e),
        )
    except OpenSpecProposalExistsError as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(e),
        )
    except OpenSpecFileNotFoundError as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except (OpenSpecParseError, OpenSpecValidationError) as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except Exception as e:
        await db.rollback()
        logger.error(f"Error creating proposal: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create proposal",
        )


@router.get(
    "/projects/{project_id}/proposals",
    response_model=OpenSpecProposalPaginatedResponse,
    summary="List project proposals",
    description="Get paginated list of proposals for a project with optional filtering.",
)
async def list_project_proposals(
    project_id: UUID,
    status_filter: str | None = None,
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> OpenSpecProposalPaginatedResponse:
    """
    List proposals for a project.

    Supports filtering by status and pagination.
    Requires project viewer permissions.

    Args:
        project_id: Project UUID
        status_filter: Optional status filter
        skip: Pagination offset
        limit: Page size (max 100)
        current_user: Authenticated user
        db: Database session

    Returns:
        Paginated list of proposals

    Raises:
        403: Forbidden (insufficient permissions)
    """
    service = _get_openspec_service(db)

    try:
        proposals, total = await service.list_proposals(
            project_id=project_id,
            user_id=current_user.id,
            status=status_filter,
            skip=skip,
            limit=limit,
        )

        proposal_responses = [_build_proposal_list_response(p) for p in proposals]

        return OpenSpecProposalPaginatedResponse(
            proposals=proposal_responses,
            total=total,
            skip=skip,
            limit=limit,
        )

    except InsufficientOpenSpecPermissionsError as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e),
        )


@router.get(
    "/proposals/{proposal_id}",
    response_model=OpenSpecProposalResponse,
    summary="Get proposal details",
    description="Get complete OpenSpec proposal with all content.",
)
async def get_proposal(
    proposal_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> OpenSpecProposalResponse:
    """
    Get proposal by ID with full details.

    Includes all content fields (proposal.md, tasks.md, spec-delta.md).
    Requires project viewer permissions.

    Args:
        proposal_id: Proposal UUID
        current_user: Authenticated user
        db: Database session

    Returns:
        Complete proposal details

    Raises:
        403: Forbidden (insufficient permissions)
        404: Not found (proposal doesn't exist)
    """
    service = _get_openspec_service(db)

    try:
        proposal = await service.get_proposal(
            proposal_id=proposal_id,
            user_id=current_user.id,
        )

        return _build_proposal_response(proposal)

    except OpenSpecProposalNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Proposal {proposal_id} not found",
        )
    except InsufficientOpenSpecPermissionsError as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e),
        )


@router.patch(
    "/proposals/{proposal_id}",
    response_model=OpenSpecProposalResponse,
    summary="Update proposal content",
    description="Update proposal content fields (only for pending/rejected proposals).",
)
async def update_proposal(
    proposal_id: UUID,
    update_data: OpenSpecProposalUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> OpenSpecProposalResponse:
    """
    Update proposal content.

    Only proposals with status 'pending' or 'rejected' can be updated.
    Requires project member permissions.

    Args:
        proposal_id: Proposal UUID
        update_data: Fields to update
        current_user: Authenticated user
        db: Database session

    Returns:
        Updated proposal

    Raises:
        400: Bad request (proposal not editable)
        403: Forbidden (insufficient permissions)
        404: Not found (proposal doesn't exist)
    """
    service = _get_openspec_service(db)

    try:
        update_dict = update_data.model_dump(exclude_none=True)

        if not update_dict:
            # No changes, just return current proposal
            proposal = await service.get_proposal(proposal_id, current_user.id)
            return _build_proposal_response(proposal)

        proposal = await service.update_proposal(
            proposal_id=proposal_id,
            update_data=update_dict,
            user_id=current_user.id,
        )

        await db.commit()
        await db.refresh(proposal)

        return _build_proposal_response(proposal)

    except OpenSpecProposalNotFoundError:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Proposal {proposal_id} not found",
        )
    except ProposalNotEditableError as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except InsufficientOpenSpecPermissionsError as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e),
        )


# ============= Approval Workflow Endpoints =============


@router.post(
    "/proposals/{proposal_id}/approve",
    response_model=OpenSpecProposalResponse,
    summary="Approve proposal",
    description="Approve a pending proposal (requires admin permissions).",
)
async def approve_proposal(
    proposal_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> OpenSpecProposalResponse:
    """
    Approve a proposal.

    Sets status to 'approved' and records approver and timestamp.
    Requires project admin permissions.

    Args:
        proposal_id: Proposal UUID
        current_user: Authenticated user
        db: Database session

    Returns:
        Approved proposal

    Raises:
        400: Bad request (proposal not approvable)
        403: Forbidden (insufficient permissions)
        404: Not found (proposal doesn't exist)
    """
    service = _get_openspec_service(db)

    try:
        proposal = await service.approve_proposal(
            proposal_id=proposal_id,
            user_id=current_user.id,
        )

        await db.commit()
        await db.refresh(proposal)

        return _build_proposal_response(proposal)

    except OpenSpecProposalNotFoundError:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Proposal {proposal_id} not found",
        )
    except ProposalNotApprovableError as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except InsufficientOpenSpecPermissionsError as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e),
        )


@router.post(
    "/proposals/{proposal_id}/reject",
    response_model=OpenSpecProposalResponse,
    summary="Reject proposal",
    description="Reject a proposal with reason (requires admin permissions).",
)
async def reject_proposal(
    proposal_id: UUID,
    reject_data: OpenSpecProposalRejectRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> OpenSpecProposalResponse:
    """
    Reject a proposal.

    Sets status to 'rejected' and stores rejection reason in metadata.
    Requires project admin permissions.

    Args:
        proposal_id: Proposal UUID
        reject_data: Rejection details
        current_user: Authenticated user
        db: Database session

    Returns:
        Rejected proposal

    Raises:
        403: Forbidden (insufficient permissions)
        404: Not found (proposal doesn't exist)
    """
    service = _get_openspec_service(db)

    try:
        proposal = await service.reject_proposal(
            proposal_id=proposal_id,
            user_id=current_user.id,
            reason=reject_data.reason,
        )

        await db.commit()
        await db.refresh(proposal)

        return _build_proposal_response(proposal)

    except OpenSpecProposalNotFoundError:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Proposal {proposal_id} not found",
        )
    except InsufficientOpenSpecPermissionsError as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e),
        )


# ============= Task Synchronization Endpoints =============


@router.post(
    "/proposals/{proposal_id}/sync-tasks",
    response_model=OpenSpecProposalSyncResponse,
    summary="Sync tasks to database",
    description="Create tasks from proposal tasks.md content (requires approval first).",
)
async def sync_tasks(
    proposal_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> OpenSpecProposalSyncResponse:
    """
    Sync tasks from proposal to database.

    Parses tasks.md and creates Task records linked to this proposal.
    Only works for approved proposals.
    Requires project member permissions.

    Args:
        proposal_id: Proposal UUID
        current_user: Authenticated user
        db: Database session

    Returns:
        Sync result with task count

    Raises:
        400: Bad request (proposal not approved or sync error)
        403: Forbidden (insufficient permissions)
        404: Not found (proposal doesn't exist)
    """
    service = _get_openspec_service(db)

    try:
        tasks = await service.sync_tasks_to_database(
            proposal_id=proposal_id,
            user_id=current_user.id,
        )

        await db.commit()

        return OpenSpecProposalSyncResponse(
            proposal_id=proposal_id,
            tasks_created=len(tasks),
            tasks_updated=0,
            sync_status="synced",
            synced_at=datetime.now(),
        )

    except OpenSpecProposalNotFoundError:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Proposal {proposal_id} not found",
        )
    except TaskSyncError as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except InsufficientOpenSpecPermissionsError as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e),
        )
    except Exception as e:
        await db.rollback()
        logger.error(f"Error syncing tasks: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to sync tasks",
        )


@router.post(
    "/proposals/{proposal_id}/refresh",
    response_model=OpenSpecProposalResponse,
    summary="Refresh from filesystem",
    description="Re-read proposal content from filesystem and update database.",
)
async def refresh_proposal(
    proposal_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> OpenSpecProposalResponse:
    """
    Refresh proposal content from filesystem.

    Re-parses all markdown files and updates database content.
    Sets task_sync_status to 'not_synced' if tasks.md changes.
    Requires project member permissions.

    Args:
        proposal_id: Proposal UUID
        current_user: Authenticated user
        db: Database session

    Returns:
        Updated proposal

    Raises:
        400: Bad request (parse error)
        403: Forbidden (insufficient permissions)
        404: Not found (proposal or filesystem directory not found)
    """
    service = _get_openspec_service(db)

    try:
        proposal = await service.refresh_from_filesystem(
            proposal_id=proposal_id,
            user_id=current_user.id,
        )

        await db.commit()
        await db.refresh(proposal)

        return _build_proposal_response(proposal)

    except OpenSpecProposalNotFoundError:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Proposal {proposal_id} not found",
        )
    except OpenSpecParseError as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except InsufficientOpenSpecPermissionsError as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e),
        )


@router.post(
    "/proposals/{proposal_id}/archive",
    response_model=OpenSpecProposalResponse,
    summary="Archive proposal",
    description="Archive completed proposal and move filesystem directory.",
)
async def archive_proposal(
    proposal_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> OpenSpecProposalResponse:
    """
    Archive a completed proposal.

    Sets status to 'archived' and moves filesystem directory to archive/.
    Requires project admin permissions.

    Args:
        proposal_id: Proposal UUID
        current_user: Authenticated user
        db: Database session

    Returns:
        Archived proposal

    Raises:
        403: Forbidden (insufficient permissions)
        404: Not found (proposal doesn't exist)
    """
    service = _get_openspec_service(db)

    try:
        proposal = await service.archive_proposal(
            proposal_id=proposal_id,
            user_id=current_user.id,
        )

        await db.commit()
        await db.refresh(proposal)

        return _build_proposal_response(proposal)

    except OpenSpecProposalNotFoundError:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Proposal {proposal_id} not found",
        )
    except InsufficientOpenSpecPermissionsError as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e),
        )


@router.delete(
    "/proposals/{proposal_id}",
    status_code=status.HTTP_200_OK,
    summary="Delete proposal",
    description="Delete proposal (only if no synced tasks exist).",
)
async def delete_proposal(
    proposal_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, str]:
    """
    Delete a proposal permanently.

    Cannot delete proposals with synced tasks - archive them instead.
    Requires project admin permissions.

    Args:
        proposal_id: Proposal UUID
        current_user: Authenticated user
        db: Database session

    Returns:
        Success message

    Raises:
        400: Bad request (proposal has synced tasks)
        403: Forbidden (insufficient permissions)
        404: Not found (proposal doesn't exist)
    """
    service = _get_openspec_service(db)

    try:
        success = await service.delete_proposal(
            proposal_id=proposal_id,
            user_id=current_user.id,
        )

        await db.commit()

        if success:
            return {"message": "Proposal deleted successfully"}
        else:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Proposal not found",
            )

    except OpenSpecProposalNotFoundError:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Proposal {proposal_id} not found",
        )
    except TaskSyncError as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except InsufficientOpenSpecPermissionsError as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e),
        )
