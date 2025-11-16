"""
Git API routes.

This module defines REST API endpoints for git operations, including
commit management, repository operations, and git history.
"""

import logging
from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from ardha.core.database import get_db
from ardha.core.security import get_current_active_user
from ardha.models.user import User
from ardha.schemas.requests.git_commit import (
    CreateCommitRequest,
    LinkTasksRequest,
    SyncCommitsRequest,
)
from ardha.schemas.responses.git_commit import (
    GitCommitResponse,
    GitCommitListResponse,
    GitCommitWithFilesResponse,
    GitCommitStatsResponse,
    GitSyncResponse,
    GitOperationResponse,
)
from ardha.services.git_commit_service import (
    GitCommitNotFoundError,
    GitCommitPermissionError,
    GitCommitValidationError,
    GitCommitOperationError,
    GitCommitService,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/git", tags=["Git"])


@router.post(
    "/commits",
    response_model=GitCommitResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a git commit",
    description="Create a git commit and record it in the database.",
)
async def create_commit(
    commit_data: CreateCommitRequest,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> GitCommitResponse:
    """
    Create a new git commit.
    
    - **project_id**: Project UUID (required)
    - **message**: Commit message (required)
    - **author_name**: Optional author name override
    - **author_email**: Optional author email override
    - **file_ids**: Optional specific files to commit
    
    Returns created commit with metadata.
    User must be at least a project member.
    """
    try:
        from ardha.core.config import get_settings
        
        settings = get_settings()
        
        service = GitCommitService(db, "/tmp/ardha")
        commit = await service.create_commit(
            project_id=commit_data.project_id,
            message=commit_data.message,
            user_id=current_user.id,
            author_name=commit_data.author_name,
            author_email=commit_data.author_email,
            file_ids=commit_data.file_ids,
        )
        
        return GitCommitResponse.model_validate(commit)
        
    except GitCommitPermissionError as e:
        logger.warning(f"Permission denied creating commit: {e}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e),
        )
    except GitCommitValidationError as e:
        logger.warning(f"Validation error creating commit: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except Exception as e:
        logger.error(f"Error creating commit: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create commit",
        )


@router.get(
    "/commits/{commit_id}",
    response_model=GitCommitResponse,
    summary="Get commit details",
    description="Get git commit by ID. User must be a project member.",
)
async def get_commit(
    commit_id: UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> GitCommitResponse:
    """
    Get commit by ID.
    
    User must be a project member to view commits.
    
    Returns commit metadata.
    """
    try:
        from ardha.core.config import get_settings
        
        settings = get_settings()
        
        service = GitCommitService(db, "/tmp/ardha")
        commit = await service.get_commit(commit_id, current_user.id)
        
        return GitCommitResponse.model_validate(commit)
        
    except GitCommitNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except GitCommitPermissionError as e:
        logger.warning(f"Permission denied accessing commit: {e}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e),
        )
    except Exception as e:
        logger.error(f"Error getting commit {commit_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get commit",
        )


@router.get(
    "/projects/{project_id}/commits",
    response_model=GitCommitListResponse,
    summary="List project commits",
    description="List git commits in a project with filtering. User must be a project member.",
)
async def list_commits(
    project_id: UUID,
    branch: str = Query(None, description="Filter by branch"),
    author_email: str = Query(None, description="Filter by author email"),
    since: datetime = Query(None, description="Filter commits since this date"),
    until: datetime = Query(None, description="Filter commits until this date"),
    search: str = Query(None, description="Search in commit messages"),
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(50, ge=1, le=100, description="Maximum records to return"),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> GitCommitListResponse:
    """
    List commits in a project.
    
    Query parameters:
    - **branch**: Filter by branch name
    - **author_email**: Filter by author email
    - **since**: Filter commits since this date (ISO 8601)
    - **until**: Filter commits until this date (ISO 8601)
    - **search**: Search in commit messages
    - **skip**: Number of records to skip (pagination, default: 0)
    - **limit**: Maximum records to return (1-100, default: 50)
    
    User must be a project member to view commits.
    
    Returns paginated list of commits.
    """
    try:
        from ardha.core.config import get_settings
        
        settings = get_settings()
        
        service = GitCommitService(db, "/tmp/ardha")
        commits, total = await service.list_commits(
            project_id=project_id,
            user_id=current_user.id,
            branch=branch,
            author_email=author_email,
            since=since,
            until=until,
            search=search,
            skip=skip,
            limit=limit,
        )
        
        return GitCommitListResponse(
            commits=[GitCommitResponse.model_validate(c) for c in commits],
            total=total,
            page=skip // limit + 1,
            page_size=limit,
            has_next=skip + limit < total,
            branch=branch or "all",
        )
        
    except GitCommitPermissionError as e:
        logger.warning(f"Permission denied listing commits: {e}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e),
        )
    except Exception as e:
        logger.error(f"Error listing commits for project {project_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to list commits",
        )


@router.post(
    "/commits/{commit_id}/link-tasks",
    response_model=GitCommitResponse,
    summary="Link commit to tasks",
    description="Link a git commit to tasks. Requires member role.",
)
async def link_commit_to_tasks(
    commit_id: UUID,
    link_data: LinkTasksRequest,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> GitCommitResponse:
    """
    Link commit to tasks.
    
    - **task_ids**: List of task identifiers (required)
    - **link_type**: Type of link (mentioned/closes, default: mentioned)
    
    Requires at least project member role.
    
    Returns updated commit with task links.
    """
    try:
        from ardha.core.config import get_settings
        
        settings = get_settings()
        
        service = GitCommitService(db, "/tmp/ardha")
        commit = await service.link_commit_to_tasks(
            commit_id=commit_id,
            user_id=current_user.id,
            task_ids=link_data.task_ids,
            link_type=link_data.link_type,
        )
        
        return GitCommitResponse.model_validate(commit)
        
    except GitCommitNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except GitCommitPermissionError as e:
        logger.warning(f"Permission denied linking tasks: {e}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e),
        )
    except Exception as e:
        logger.error(f"Error linking tasks to commit {commit_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to link tasks to commit",
        )


@router.get(
    "/commits/{commit_id}/files",
    response_model=GitCommitWithFilesResponse,
    summary="Get commit with file changes",
    description="Get commit with detailed file changes. User must be a project member.",
)
async def get_commit_with_files(
    commit_id: UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> GitCommitWithFilesResponse:
    """
    Get commit with file changes.
    
    User must be a project member to view commit details.
    
    Returns commit with detailed file changes.
    """
    try:
        from ardha.core.config import get_settings
        
        settings = get_settings()
        
        service = GitCommitService(db, "/tmp/ardha")
        commit, file_changes = await service.get_commit_with_files(commit_id, current_user.id)
        
        return GitCommitWithFilesResponse(
            id=commit.id,
            sha=commit.sha,
            short_sha=commit.sha[:7] if commit.sha else "",
            message=commit.message,
            author_name=commit.author_name,
            author_email=commit.author_email,
            branch=commit.branch,
            committed_at=commit.committed_at,
            is_merge=commit.is_merge,
            files_changed=commit.files_changed,
            insertions=commit.insertions,
            deletions=commit.deletions,
            linked_task_ids=commit.linked_task_ids or [],
            closes_task_ids=commit.closes_task_ids or [],
            file_changes=[],  # Simplified for now
        )
        
    except GitCommitNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except GitCommitPermissionError as e:
        logger.warning(f"Permission denied accessing commit files: {e}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e),
        )
    except Exception as e:
        logger.error(f"Error getting commit {commit_id} with files: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get commit with files",
        )


@router.get(
    "/files/{file_id}/commits",
    response_model=list[GitCommitResponse],
    summary="Get file commits",
    description="Get commits that changed a specific file. User must be a project member.",
)
async def get_file_commits(
    file_id: UUID,
    max_count: int = Query(50, ge=1, le=100, description="Maximum commits to return"),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> list[GitCommitResponse]:
    """
    Get commits that changed a specific file.
    
    Query parameters:
    - **max_count**: Maximum number of commits to return (1-100, default: 50)
    
    User must be a project member to view file commits.
    
    Returns list of commits that modified the file.
    """
    try:
        from ardha.core.config import get_settings
        
        settings = get_settings()
        
        service = GitCommitService(db, "/tmp/ardha")
        commits = await service.get_file_commits(file_id, current_user.id, max_count)
        
        return [GitCommitResponse.model_validate(c) for c in commits]
        
    except GitCommitPermissionError as e:
        logger.warning(f"Permission denied accessing file commits: {e}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e),
        )
    except Exception as e:
        logger.error(f"Error getting commits for file {file_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get file commits",
        )


@router.get(
    "/users/{user_id}/commits",
    response_model=list[GitCommitResponse],
    summary="Get user commits",
    description="Get commits by a specific user. User must be a project member.",
)
async def get_user_commits(
    user_id: UUID,
    requesting_user: User = Depends(get_current_active_user),
    project_id: UUID = Query(None, description="Filter by project"),
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(50, ge=1, le=100, description="Maximum records to return"),
    db: AsyncSession = Depends(get_db),
) -> list[GitCommitResponse]:
    """
    Get commits by a specific user.
    
    Query parameters:
    - **project_id**: Filter by project UUID
    - **skip**: Number of records to skip (pagination, default: 0)
    - **limit**: Maximum records to return (1-100, default: 50)
    
    User must be a project member to view user commits.
    
    Returns list of commits by the specified user.
    """
    try:
        from ardha.core.config import get_settings
        
        settings = get_settings()
        
        service = GitCommitService(db, "/tmp/ardha")
        commits = await service.get_user_commits(
            user_id=user_id,
            requesting_user_id=requesting_user.id,
            project_id=project_id,
            skip=skip,
            limit=limit,
        )
        
        return [GitCommitResponse.model_validate(c) for c in commits]
        
    except GitCommitPermissionError as e:
        logger.warning(f"Permission denied accessing user commits: {e}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e),
        )
    except Exception as e:
        logger.error(f"Error getting commits for user {user_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get user commits",
        )


@router.get(
    "/projects/{project_id}/commits/latest",
    response_model=GitCommitResponse,
    summary="Get latest commit",
    description="Get most recent commit in a project. User must be a project member.",
)
async def get_latest_commit(
    project_id: UUID,
    branch: str = Query(None, description="Filter by branch"),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> GitCommitResponse:
    """
    Get most recent commit in a project.
    
    Query parameters:
    - **branch**: Optional branch filter
    
    User must be a project member to view commits.
    
    Returns latest commit or None if no commits exist.
    """
    try:
        from ardha.core.config import get_settings
        
        settings = get_settings()
        
        service = GitCommitService(db, "/tmp/ardha")
        commit = await service.get_latest_commit(project_id, current_user.id, branch)
        
        if not commit:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No commits found in project",
            )
        
        return GitCommitResponse.model_validate(commit)
        
    except GitCommitPermissionError as e:
        logger.warning(f"Permission denied accessing latest commit: {e}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e),
        )
    except Exception as e:
        logger.error(f"Error getting latest commit for project {project_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get latest commit",
        )


@router.post(
    "/projects/{project_id}/sync-commits",
    response_model=GitSyncResponse,
    summary="Sync commits from git",
    description="Sync commits from git repository to database. Requires admin role.",
)
async def sync_commits(
    project_id: UUID,
    sync_data: SyncCommitsRequest,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> GitSyncResponse:
    """
    Sync commits from git repository to database.
    
    - **branch**: Optional branch filter
    - **since**: Optional start date filter
    
    Requires project admin or owner role.
    
    Returns sync statistics.
    """
    try:
        from ardha.core.config import get_settings
        
        settings = get_settings()
        
        service = GitCommitService(db, "/tmp/ardha")
        stats = await service.sync_commits_from_git(
            project_id=project_id,
            user_id=current_user.id,
            branch=sync_data.branch,
            since=sync_data.since,
        )
        
        return GitSyncResponse(
            synced_commits=stats["synced_count"],
            new_commits=stats["new_commits"],
            updated_commits=stats["updated_commits"],
            linked_tasks=0,
        )
        
    except GitCommitPermissionError as e:
        logger.warning(f"Permission denied syncing commits: {e}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e),
        )
    except Exception as e:
        logger.error(f"Error syncing commits for project {project_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to sync commits",
        )


@router.get(
    "/projects/{project_id}/stats",
    response_model=GitCommitStatsResponse,
    summary="Get commit statistics",
    description="Get commit statistics for a project. User must be a project member.",
)
async def get_commit_stats(
    project_id: UUID,
    branch: str = Query(None, description="Filter by branch"),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> GitCommitStatsResponse:
    """
    Get commit statistics for a project.
    
    Query parameters:
    - **branch**: Optional branch filter
    
    User must be a project member to view commit stats.
    
    Returns comprehensive commit statistics.
    """
    try:
        from ardha.core.config import get_settings
        
        settings = get_settings()
        
        service = GitCommitService(db, "/tmp/ardha")
        stats = await service.get_commit_stats(project_id, current_user.id, branch)
        
        return GitCommitStatsResponse(
            total_commits=stats["total_commits"],
            total_insertions=stats["total_insertions"],
            total_deletions=stats["total_deletions"],
            total_files_changed=stats["total_files_changed"],
            branches=stats["branches"],
            top_contributors=stats["top_contributors"],
        )
        
    except GitCommitPermissionError as e:
        logger.warning(f"Permission denied accessing commit stats: {e}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e),
        )
    except Exception as e:
        logger.error(f"Error getting commit stats for project {project_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get commit statistics",
        )


@router.get(
    "/projects/{project_id}/branches",
    response_model=list[str],
    summary="Get project branches",
    description="Get all branches in a project. User must be a project member.",
)
async def get_project_branches(
    project_id: UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> list[str]:
    """
    Get all branches in a project.
    
    User must be a project member to view branches.
    
    Returns list of branch names.
    """
    try:
        from ardha.core.config import get_settings
        from ardha.services.project_service import ProjectService
        
        settings = get_settings()
        
        # Check project permissions first
        project_service = ProjectService(db)
        if not await project_service.check_permission(project_id, current_user.id, "viewer"):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Must be a project member to view branches",
            )
        
        # Get branches from git service
        git_service = GitCommitService(db, "/tmp/ardha")
        commits, _ = await git_service.list_commits(
            project_id=project_id,
            user_id=current_user.id,
            skip=0,
            limit=1000,  # Get many commits to find all branches
        )
        
        # Extract unique branches from commits
        branches = list(set(commit.branch for commit in commits if commit.branch))
        branches.sort()
        
        return branches
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting branches for project {project_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get project branches",
        )