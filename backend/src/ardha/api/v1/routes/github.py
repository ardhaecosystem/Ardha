"""
GitHub Integration REST API routes.

Provides endpoints for GitHub integration management, pull request operations,
webhook setup, and GitHub statistics.
"""

import logging
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from ardha.core.database import get_db
from ardha.core.security import get_current_active_user
from ardha.models.user import User
from ardha.repositories.github_integration import GitHubIntegrationRepository
from ardha.repositories.pull_request import PullRequestRepository
from ardha.schemas.requests.github import (
    CreateGitHubIntegrationRequest,
    CreatePullRequestRequest,
    MergePRRequest,
    SetupWebhookRequest,
    SyncPullRequestsRequest,
    UpdateGitHubIntegrationRequest,
)
from ardha.schemas.responses.github import (
    GitHubConnectionStatusResponse,
    GitHubIntegrationResponse,
    GitHubStatsResponse,
    PaginatedPRResponse,
    PullRequestResponse,
    PullRequestWithDetailsResponse,
    WebhookResponse,
)
from ardha.services.git_commit_service import GitCommitService
from ardha.services.github_integration_service import (
    GitHubIntegrationExistsError,
    GitHubIntegrationNotFoundError,
    GitHubIntegrationService,
    GitHubPRNotFoundError,
    InsufficientGitHubPermissionsError,
)
from ardha.services.project_service import ProjectService
from ardha.services.task_service import TaskService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/github", tags=["github"])


# ============= Dependency Injection =============


def get_github_service(
    db: AsyncSession = Depends(get_db),
) -> GitHubIntegrationService:
    """Get GitHubIntegrationService with dependencies."""
    integration_repo = GitHubIntegrationRepository(db)
    pr_repo = PullRequestRepository(db)
    project_service = ProjectService(db)
    task_service = TaskService(db)

    return GitHubIntegrationService(
        integration_repo=integration_repo,
        pr_repo=pr_repo,
        project_service=project_service,
        task_service=task_service,
        db=db,
    )


# ============= Integration Management Endpoints =============


@router.post(
    "/projects/{project_id}/github/integration",
    response_model=GitHubIntegrationResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create GitHub integration",
    description="Create GitHub integration for a project with OAuth token",
)
async def create_github_integration(
    project_id: UUID,
    request: CreateGitHubIntegrationRequest,
    current_user: User = Depends(get_current_active_user),
    service: GitHubIntegrationService = Depends(get_github_service),
) -> GitHubIntegrationResponse:
    """
    Create GitHub integration.

    Requires admin+ role on project.
    """
    try:
        integration = await service.create_integration(
            project_id=project_id,
            repository_owner=request.repository_owner,
            repository_name=request.repository_name,
            access_token=request.access_token,
            user_id=current_user.id,
            configuration={
                "auto_create_pr": request.auto_create_pr,
                "auto_link_tasks": request.auto_link_tasks,
                "require_review": request.require_review,
                **(request.configuration or {}),
            },
        )

        return GitHubIntegrationResponse.model_validate(integration)

    except InsufficientGitHubPermissionsError as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e),
        )
    except GitHubIntegrationExistsError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(e),
        )
    except Exception as e:
        logger.error(f"Failed to create GitHub integration: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create GitHub integration",
        )


@router.get(
    "/projects/{project_id}/github/integration",
    response_model=GitHubIntegrationResponse,
    summary="Get GitHub integration",
    description="Get GitHub integration details for a project",
)
async def get_github_integration(
    project_id: UUID,
    current_user: User = Depends(get_current_active_user),
    service: GitHubIntegrationService = Depends(get_github_service),
) -> GitHubIntegrationResponse:
    """
    Get GitHub integration.

    Requires viewer+ role on project.
    """
    try:
        integration = await service.get_integration(
            project_id=project_id,
            user_id=current_user.id,
        )

        return GitHubIntegrationResponse.model_validate(integration)

    except GitHubIntegrationNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except InsufficientGitHubPermissionsError as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e),
        )


@router.patch(
    "/projects/{project_id}/github/integration",
    response_model=GitHubIntegrationResponse,
    summary="Update GitHub integration",
    description="Update GitHub integration configuration",
)
async def update_github_integration(
    project_id: UUID,
    request: UpdateGitHubIntegrationRequest,
    current_user: User = Depends(get_current_active_user),
    service: GitHubIntegrationService = Depends(get_github_service),
) -> GitHubIntegrationResponse:
    """
    Update GitHub integration.

    Requires admin+ role on project.
    """
    try:
        # Convert request to dict, excluding unset fields
        update_data = request.model_dump(exclude_unset=True)

        integration = await service.update_integration(
            project_id=project_id,
            update_data=update_data,
            user_id=current_user.id,
        )

        return GitHubIntegrationResponse.model_validate(integration)

    except GitHubIntegrationNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except InsufficientGitHubPermissionsError as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e),
        )
    except Exception as e:
        logger.error(f"Failed to update GitHub integration: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update GitHub integration",
        )


@router.delete(
    "/projects/{project_id}/github/integration",
    summary="Delete GitHub integration",
    description="Delete GitHub integration and remove webhooks",
)
async def delete_github_integration(
    project_id: UUID,
    current_user: User = Depends(get_current_active_user),
    service: GitHubIntegrationService = Depends(get_github_service),
) -> dict:
    """
    Delete GitHub integration.

    Requires admin+ role on project.
    """
    try:
        success = await service.delete_integration(
            project_id=project_id,
            user_id=current_user.id,
        )

        return {"success": success}

    except GitHubIntegrationNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except InsufficientGitHubPermissionsError as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e),
        )


# ============= Pull Request Sync & Creation =============


@router.post(
    "/projects/{project_id}/github/sync",
    summary="Sync pull requests",
    description="Sync pull requests from GitHub to database",
)
async def sync_pull_requests(
    project_id: UUID,
    request: SyncPullRequestsRequest,
    current_user: User = Depends(get_current_active_user),
    service: GitHubIntegrationService = Depends(get_github_service),
) -> dict:
    """
    Sync pull requests from GitHub.

    Requires member+ role on project.
    """
    try:
        synced_count = await service.sync_pull_requests(
            project_id=project_id,
            user_id=current_user.id,
            full_sync=request.full_sync,
        )

        return {"synced_count": synced_count}

    except GitHubIntegrationNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except InsufficientGitHubPermissionsError as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e),
        )
    except Exception as e:
        logger.error(f"Failed to sync pull requests: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to sync pull requests",
        )


@router.post(
    "/projects/{project_id}/github/webhook",
    response_model=WebhookResponse,
    summary="Setup webhook",
    description="Setup GitHub webhook for repository",
)
async def setup_webhook(
    project_id: UUID,
    request: SetupWebhookRequest,
    current_user: User = Depends(get_current_active_user),
    service: GitHubIntegrationService = Depends(get_github_service),
) -> WebhookResponse:
    """
    Setup GitHub webhook.

    Requires admin+ role on project.
    """
    try:
        webhook_data = await service.setup_webhook(
            project_id=project_id,
            webhook_url=request.webhook_url,
            events=request.events,
            user_id=current_user.id,
        )

        return WebhookResponse(
            webhook_id=webhook_data["id"],
            webhook_url=webhook_data["url"],
            events=webhook_data["events"],
            active=webhook_data["active"],
            created_at=webhook_data.get("created_at"),
            secret_configured=True,
        )

    except GitHubIntegrationNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except InsufficientGitHubPermissionsError as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e),
        )
    except Exception as e:
        logger.error(f"Failed to setup webhook: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to setup webhook",
        )


@router.post(
    "/projects/{project_id}/github/pr",
    response_model=PullRequestResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create pull request",
    description="Create pull request on GitHub",
)
async def create_pull_request(
    project_id: UUID,
    request: CreatePullRequestRequest,
    current_user: User = Depends(get_current_active_user),
    service: GitHubIntegrationService = Depends(get_github_service),
) -> PullRequestResponse:
    """
    Create pull request.

    Requires member+ role on project.
    """
    try:
        # Parse linked_task_ids if provided
        linked_task_uuids = None
        if request.linked_task_ids:
            linked_task_uuids = [UUID(tid) for tid in request.linked_task_ids]

        pr = await service.create_pull_request(
            project_id=project_id,
            title=request.title,
            body=request.body,
            head_branch=request.head_branch,
            base_branch=request.base_branch,
            draft=request.draft,
            user_id=current_user.id,
            linked_task_ids=linked_task_uuids,
        )

        return PullRequestResponse.model_validate(pr)

    except GitHubIntegrationNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except InsufficientGitHubPermissionsError as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e),
        )
    except Exception as e:
        logger.error(f"Failed to create pull request: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create pull request",
        )


# ============= Pull Request Operations =============


@router.get(
    "/projects/{project_id}/github/prs",
    response_model=PaginatedPRResponse,
    summary="List pull requests",
    description="List pull requests for a project with optional filters",
)
async def list_pull_requests(
    project_id: UUID,
    state: Optional[str] = Query(None, description="Filter by state (open, closed, merged, draft)"),
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(50, ge=1, le=100, description="Maximum records to return"),
    current_user: User = Depends(get_current_active_user),
    service: GitHubIntegrationService = Depends(get_github_service),
    db: AsyncSession = Depends(get_db),
) -> PaginatedPRResponse:
    """
    List pull requests.

    Requires viewer+ role on project.
    """
    try:
        prs = await service.list_pull_requests(
            project_id=project_id,
            user_id=current_user.id,
            state=state,
            skip=skip,
            limit=limit,
        )

        # Get total count
        pr_repo = PullRequestRepository(db)
        total = await pr_repo.count_by_project(project_id, state=state)

        return PaginatedPRResponse(
            prs=[PullRequestResponse.model_validate(pr) for pr in prs],
            total=total,
            skip=skip,
            limit=limit,
        )

    except InsufficientGitHubPermissionsError as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e),
        )


@router.get(
    "/github/prs/{pr_id}",
    response_model=PullRequestWithDetailsResponse,
    summary="Get pull request details",
    description="Get detailed pull request information with tasks and commits",
)
async def get_pull_request(
    pr_id: UUID,
    sync_from_github: bool = Query(False, description="Fetch latest from GitHub"),
    current_user: User = Depends(get_current_active_user),
    service: GitHubIntegrationService = Depends(get_github_service),
    db: AsyncSession = Depends(get_db),
) -> PullRequestWithDetailsResponse:
    """
    Get pull request details.

    Requires viewer+ role on project.
    """
    try:
        pr = await service.get_pull_request(
            pr_id=pr_id,
            user_id=current_user.id,
            sync_from_github=sync_from_github,
        )

        # Get linked tasks
        pr_repo = PullRequestRepository(db)
        tasks = await pr_repo.get_linked_tasks(pr_id)

        # Get linked commits
        commits = await pr_repo.get_linked_commits(pr_id)

        pr_response = PullRequestWithDetailsResponse.model_validate(pr)
        pr_response.linked_tasks = [
            {
                "id": str(t.id),
                "identifier": t.identifier,
                "title": t.title,
                "status": t.status,
            }
            for t in tasks
        ]
        pr_response.commits = [
            {
                "sha": c.sha,
                "short_sha": c.short_sha,
                "message": c.message,
                "author_name": c.author_name,
            }
            for c in commits
        ]

        return pr_response

    except GitHubPRNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except InsufficientGitHubPermissionsError as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e),
        )


@router.post(
    "/github/prs/{pr_id}/merge",
    response_model=PullRequestResponse,
    summary="Merge pull request",
    description="Merge pull request on GitHub and auto-close linked tasks",
)
async def merge_pull_request(
    pr_id: UUID,
    request: MergePRRequest,
    current_user: User = Depends(get_current_active_user),
    service: GitHubIntegrationService = Depends(get_github_service),
) -> PullRequestResponse:
    """
    Merge pull request.

    Requires admin+ role on project.
    Automatically closes linked tasks with "closes" link type.
    """
    try:
        pr = await service.merge_pull_request(
            pr_id=pr_id,
            user_id=current_user.id,
            merge_method=request.merge_method,
            commit_message=request.commit_message,
        )

        return PullRequestResponse.model_validate(pr)

    except GitHubPRNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except InsufficientGitHubPermissionsError as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e),
        )
    except Exception as e:
        logger.error(f"Failed to merge pull request: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


@router.post(
    "/github/prs/{pr_id}/close",
    response_model=PullRequestResponse,
    summary="Close pull request",
    description="Close pull request without merging",
)
async def close_pull_request(
    pr_id: UUID,
    current_user: User = Depends(get_current_active_user),
    service: GitHubIntegrationService = Depends(get_github_service),
) -> PullRequestResponse:
    """
    Close pull request.

    Requires member+ role on project.
    """
    try:
        pr = await service.close_pull_request(
            pr_id=pr_id,
            user_id=current_user.id,
        )

        return PullRequestResponse.model_validate(pr)

    except GitHubPRNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except InsufficientGitHubPermissionsError as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e),
        )


# ============= Status & Statistics =============


@router.get(
    "/projects/{project_id}/github/connection",
    response_model=GitHubConnectionStatusResponse,
    summary="Verify GitHub connection",
    description="Verify GitHub connection status and repository access",
)
async def verify_github_connection(
    project_id: UUID,
    current_user: User = Depends(get_current_active_user),
    service: GitHubIntegrationService = Depends(get_github_service),
) -> GitHubConnectionStatusResponse:
    """
    Verify GitHub connection.

    Tests token validity and repository access.
    Requires viewer+ role on project.
    """
    try:
        connection_info = await service.verify_connection(
            project_id=project_id,
            user_id=current_user.id,
        )

        return GitHubConnectionStatusResponse(**connection_info)

    except GitHubIntegrationNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except InsufficientGitHubPermissionsError as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e),
        )


@router.get(
    "/projects/{project_id}/github/stats",
    response_model=GitHubStatsResponse,
    summary="Get GitHub statistics",
    description="Get comprehensive GitHub statistics for a project",
)
async def get_github_statistics(
    project_id: UUID,
    current_user: User = Depends(get_current_active_user),
    service: GitHubIntegrationService = Depends(get_github_service),
) -> GitHubStatsResponse:
    """
    Get GitHub statistics.

    Includes PR metrics, contributor stats, and activity metrics.
    Requires viewer+ role on project.
    """
    try:
        stats = await service.get_project_statistics(
            project_id=project_id,
            user_id=current_user.id,
        )

        return GitHubStatsResponse(**stats)

    except GitHubIntegrationNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except InsufficientGitHubPermissionsError as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e),
        )
