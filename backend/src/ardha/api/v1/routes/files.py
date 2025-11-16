"""
File API routes.

This module defines REST API endpoints for file management, including
CRUD operations, content management, and file history.
"""

import logging
from datetime import datetime
from pathlib import Path
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from ardha.core.database import get_db
from ardha.core.security import get_current_active_user
from ardha.models.user import User
from ardha.schemas.requests.file import (
    CreateFileRequest,
    UpdateFileContentRequest,
    RenameFileRequest,
)
from ardha.schemas.responses.file import (
    FileResponse,
    FileWithContentResponse,
    FileListResponse,
    FileHistoryResponse,
    FileOperationResponse,
)
from ardha.services.file_service import (
    FileNotFoundError,
    FilePermissionError,
    FileValidationError,
    FileOperationError,
    FileService,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/files", tags=["Files"])


@router.post(
    "/",
    response_model=FileResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new file",
    description="Create a new file in a project with optional git commit.",
)
async def create_file(
    file_data: CreateFileRequest,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> FileResponse:
    """
    Create a new file.
    
    - **project_id**: Project UUID (required)
    - **path**: Relative file path (required)
    - **content**: File content (required)
    - **commit**: Whether to create git commit (default: false)
    - **commit_message**: Custom commit message
    
    Returns the created file with metadata.
    User must be at least a project member.
    """
    try:
        from ardha.core.config import get_settings
        settings = get_settings()
        
        service = FileService(db, Path("/tmp/ardha"))
        file = await service.create_file(
            project_id=file_data.project_id,
            file_path=file_data.path,
            content=file_data.content,
            user_id=current_user.id,
            commit=file_data.commit,
            commit_message=file_data.commit_message,
        )
        
        return FileResponse.model_validate(file)
        
    except FilePermissionError as e:
        logger.warning(f"Permission denied creating file: {e}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e),
        )
    except FileValidationError as e:
        logger.warning(f"Validation error creating file: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except Exception as e:
        logger.error(f"Error creating file: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create file",
        )


@router.get(
    "/{file_id}",
    response_model=FileResponse,
    summary="Get file details",
    description="Get file metadata by ID. User must be a project member.",
)
async def get_file(
    file_id: UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> FileResponse:
    """
    Get file by ID.
    
    User must be a project member to view files.
    
    Returns file metadata without content.
    """
    try:
        from ardha.core.config import get_settings
        settings = get_settings()
        
        service = FileService(db, Path("/tmp/ardha"))
        file = await service.get_file(file_id, current_user.id)
        
        return FileResponse.model_validate(file)
        
    except FileNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except FilePermissionError as e:
        logger.warning(f"Permission denied accessing file: {e}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e),
        )
    except Exception as e:
        logger.error(f"Error getting file {file_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get file",
        )


@router.get(
    "/{file_id}/content",
    response_model=FileWithContentResponse,
    summary="Get file content",
    description="Get file with content by ID. User must be a project member.",
)
async def get_file_content(
    file_id: UUID,
    ref: str = Query("HEAD", description="Git reference (default: HEAD)"),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> FileWithContentResponse:
    """
    Get file with content.
    
    Query parameters:
    - **ref**: Git reference (commit SHA, branch, tag, default: HEAD)
    
    User must be a project member to view file content.
    
    Returns file with full content.
    """
    try:
        from ardha.core.config import get_settings
        settings = get_settings()
        
        service = FileService(db, Path("/tmp/ardha"))
        file = await service.get_file(file_id, current_user.id)
        content = await service.get_file_content(file_id, current_user.id, ref)
        
        # Create response with content
        response = FileWithContentResponse.model_validate(file)
        response.content = content
        
        return response
        
    except FileNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except FilePermissionError as e:
        logger.warning(f"Permission denied accessing file content: {e}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e),
        )
    except Exception as e:
        logger.error(f"Error getting file content {file_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get file content",
        )


@router.patch(
    "/{file_id}",
    response_model=FileResponse,
    summary="Update file content",
    description="Update file content with optional git commit. Requires member role.",
)
async def update_file_content(
    file_id: UUID,
    update_data: UpdateFileContentRequest,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> FileResponse:
    """
    Update file content.
    
    - **content**: New file content (required)
    - **commit**: Whether to create git commit (default: false)
    - **commit_message**: Custom commit message
    
    Requires at least project member role.
    
    Returns updated file metadata.
    """
    try:
        from ardha.core.config import get_settings
        settings = get_settings()
        
        service = FileService(db, Path("/tmp/ardha"))
        file = await service.update_file_content(
            file_id=file_id,
            content=update_data.content,
            user_id=current_user.id,
            commit=update_data.commit,
            commit_message=update_data.commit_message,
        )
        
        return FileResponse.model_validate(file)
        
    except FileNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except FilePermissionError as e:
        logger.warning(f"Permission denied updating file: {e}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e),
        )
    except FileValidationError as e:
        logger.warning(f"Validation error updating file: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except Exception as e:
        logger.error(f"Error updating file {file_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update file",
        )


@router.patch(
    "/{file_id}/rename",
    response_model=FileResponse,
    summary="Rename file",
    description="Rename/move file with optional git commit. Requires member role.",
)
async def rename_file(
    file_id: UUID,
    rename_data: RenameFileRequest,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> FileResponse:
    """
    Rename/move file.
    
    - **new_path**: New file path (required)
    - **commit**: Whether to create git commit (default: false)
    - **commit_message**: Custom commit message
    
    Requires at least project member role.
    
    Returns updated file metadata.
    """
    try:
        from ardha.core.config import get_settings
        settings = get_settings()
        
        service = FileService(db, Path("/tmp/ardha"))
        file = await service.rename_file(
            file_id=file_id,
            new_path=rename_data.new_path,
            user_id=current_user.id,
            commit=rename_data.commit,
            commit_message=rename_data.commit_message,
        )
        
        return FileResponse.model_validate(file)
        
    except FileNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except FilePermissionError as e:
        logger.warning(f"Permission denied renaming file: {e}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e),
        )
    except FileValidationError as e:
        logger.warning(f"Validation error renaming file: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except Exception as e:
        logger.error(f"Error renaming file {file_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to rename file",
        )


@router.delete(
    "/{file_id}",
    response_model=FileOperationResponse,
    summary="Delete file",
    description="Delete file with optional git commit. Requires admin role.",
)
async def delete_file(
    file_id: UUID,
    commit: bool = Query(False, description="Whether to create git commit"),
    commit_message: str = Query(None, description="Custom commit message"),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> FileOperationResponse:
    """
    Delete file.
    
    Query parameters:
    - **commit**: Whether to create git commit (default: false)
    - **commit_message**: Custom commit message
    
    Requires project admin or owner role.
    This is a soft delete - file can be restored.
    
    Returns operation result.
    """
    try:
        from ardha.core.config import get_settings
        settings = get_settings()
        
        service = FileService(db, Path("/tmp/ardha"))
        success = await service.delete_file(
            file_id=file_id,
            user_id=current_user.id,
            commit=commit,
            commit_message=commit_message,
        )
        
        return FileOperationResponse(
            success=success,
            message="File deleted successfully" if success else "Failed to delete file",
        )
        
    except FileNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except FilePermissionError as e:
        logger.warning(f"Permission denied deleting file: {e}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e),
        )
    except Exception as e:
        logger.error(f"Error deleting file {file_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete file",
        )


@router.get(
    "/projects/{project_id}/files",
    response_model=FileListResponse,
    summary="List project files",
    description="List files in a project with filtering. User must be a project member.",
)
async def list_project_files(
    project_id: UUID,
    directory: str = Query(None, description="Filter by directory"),
    file_type: str = Query(None, description="Filter by file type"),
    search: str = Query(None, description="Search in file names and content"),
    include_deleted: bool = Query(False, description="Include soft-deleted files"),
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(50, ge=1, le=100, description="Maximum records to return"),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> FileListResponse:
    """
    List files in a project.
    
    Query parameters:
    - **directory**: Filter by directory path
    - **file_type**: Filter by file type (code, doc, config, test, asset, other)
    - **search**: Search in file names and content
    - **include_deleted**: Include soft-deleted files (default: false)
    - **skip**: Number of records to skip (pagination, default: 0)
    - **limit**: Maximum records to return (1-100, default: 50)
    
    User must be a project member to view files.
    
    Returns paginated list of files.
    """
    try:
        from ardha.core.config import get_settings
        from ardha.schemas.file import FileType
        
        settings = get_settings()
        
        service = FileService(db, Path("/tmp/ardha"))
        
        # Convert file_type string to enum if provided
        file_type_enum = None
        if file_type:
            try:
                file_type_enum = FileType(file_type)
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid file type: {file_type}",
                )
        
        files, total = await service.list_project_files(
            project_id=project_id,
            user_id=current_user.id,
            directory=directory,
            file_type=file_type_enum,
            search=search,
            include_deleted=include_deleted,
            skip=skip,
            limit=limit,
        )
        
        return FileListResponse(
            files=[FileResponse.model_validate(f) for f in files],
            total=total,
            page=skip // limit + 1,
            page_size=limit,
            has_next=skip + limit < total,
        )
        
    except FilePermissionError as e:
        logger.warning(f"Permission denied listing files: {e}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e),
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error listing files for project {project_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to list files",
        )


@router.get(
    "/{file_id}/history",
    response_model=FileHistoryResponse,
    summary="Get file history",
    description="Get file with commit history. User must be a project member.",
)
async def get_file_history(
    file_id: UUID,
    max_commits: int = Query(50, ge=1, le=100, description="Maximum commits to return"),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> FileHistoryResponse:
    """
    Get file with commit history.
    
    Query parameters:
    - **max_commits**: Maximum number of commits to return (1-100, default: 50)
    
    User must be a project member to view file history.
    
    Returns file with commit history.
    """
    try:
        from ardha.core.config import get_settings
        
        settings = get_settings()
        
        service = FileService(db, Path("/tmp/ardha"))
        file, commits = await service.get_file_history(
            file_id=file_id,
            user_id=current_user.id,
            max_commits=max_commits,
        )
        
        # Convert commits to response format
        commit_responses = []
        for commit in commits:
            commit_responses.append(FileHistoryResponse(
                id=file_id,  # Using file_id as placeholder
                sha=commit["sha"],
                short_sha=commit["short_sha"],
                message=commit["message"],
                author_name=commit["author_name"],
                author_email=commit["author_email"],
                committed_at=commit["date"],
                change_type="modified",  # Default for history
                insertions=commit.get("changes", {}).get("insertions", 0),
                deletions=commit.get("changes", {}).get("deletions", 0),
                time_ago=None,  # Could calculate this
            ))
        
        return FileHistoryResponse(
            id=file_id,
            sha=commit_responses[0].sha if commit_responses else "",
            short_sha=commit_responses[0].short_sha if commit_responses else "",
            message=commit_responses[0].message if commit_responses else "",
            author_name=commit_responses[0].author_name if commit_responses else "",
            author_email=commit_responses[0].author_email if commit_responses else "",
            committed_at=commit_responses[0].committed_at if commit_responses else datetime.now(),
            change_type="modified",
            time_ago=None,
        )
        
    except FileNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except FilePermissionError as e:
        logger.warning(f"Permission denied accessing file history: {e}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e),
        )
    except Exception as e:
        logger.error(f"Error getting file history {file_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get file history",
        )