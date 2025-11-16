"""
File service for business logic.

This module provides the business logic layer for file management, handling:
- Permission checks
- File content validation
- Git integration
- File operations with proper error handling
"""

import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Optional
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from ardha.models.file import File
from ardha.repositories.file import FileRepository
from ardha.schemas.file import FileType
from ardha.services.project_service import ProjectService
from ardha.services.git_service import GitService

logger = logging.getLogger(__name__)


# ============= Custom Exceptions =============


class FileNotFoundError(Exception):
    """Raised when a file is not found."""
    
    pass


class FilePermissionError(Exception):
    """Raised when user lacks permissions for file operation."""
    
    pass


class FileValidationError(Exception):
    """Raised when file content validation fails."""
    
    pass


class FileOperationError(Exception):
    """Raised when file operation fails."""
    
    pass


class FileService:
    """
    Service layer for file business logic.
    
    Handles:
    - Permission-based access control
    - File content validation and processing
    - Git integration for file operations
    - File metadata management
    """
    
    def __init__(self, db: AsyncSession, project_root: Path):
        """
        Initialize file service.
        
        Args:
            db: Async SQLAlchemy database session
            project_root: Path to project root directory
        """
        self.db = db
        self.repository = FileRepository(db)
        self.project_service = ProjectService(db)
        self.git_service = GitService(project_root)
    
    # ============= Core File Operations =============
    
    async def create_file(
        self,
        project_id: UUID,
        file_path: str,
        content: str,
        user_id: UUID,
        commit: bool = False,
        commit_message: Optional[str] = None,
    ) -> File:
        """
        Create a new file with validation and optional git commit.
        
        Args:
            project_id: Project UUID
            file_path: Relative file path
            content: File content
            user_id: User creating the file
            commit: Whether to commit the file creation
            commit_message: Custom commit message
            
        Returns:
            Created File object
            
        Raises:
            FilePermissionError: If user lacks permissions
            FileValidationError: If file validation fails
            FileOperationError: If file operation fails
        """
        # Check project permissions (must be at least member)
        if not await self.project_service.check_permission(
            project_id=project_id,
            user_id=user_id,
            required_role="member",
        ):
            raise FilePermissionError("Must be at least a project member to create files")
        
        # Validate file path and content
        await self._validate_file_creation(project_id, file_path, content)
        
        try:
            # Write file to filesystem
            self.git_service.write_file(file_path, content)
            
            # Create file record
            file_data = {
                "project_id": project_id,
                "path": file_path,
                "name": Path(file_path).name,
                "extension": Path(file_path).suffix,
                "content": content if len(content.encode('utf-8')) < 1024 * 1024 else None,  # Store if <1MB
                "content_hash": File.calculate_content_hash(content),
                "size_bytes": len(content.encode('utf-8')),
                "file_type": self._detect_file_type(file_path),
                "language": self._detect_language(file_path),
                "is_binary": False,
            }
            
            file = File(**file_data)
            created_file = await self.repository.create(file)
            
            # Optional git commit
            commit_sha = None
            if commit and self.git_service.is_initialized():
                if not commit_message:
                    commit_message = f"Create file: {file_path}"
                
                commit_info = self.git_service.commit(
                    message=commit_message,
                    author_name=await self._get_user_name(user_id),
                    author_email=await self._get_user_email(user_id),
                )
                commit_sha = commit_info["sha"]
                
                # Update file with git metadata
                await self.repository.update_from_git(
                    file_id=created_file.id,
                    commit_sha=commit_sha,
                    commit_message=commit_message,
                    modified_by_user_id=user_id,
                    modified_at=datetime.now(),
                )
            
            logger.info(f"Created file {file_path} in project {project_id}")
            return created_file
            
        except Exception as e:
            logger.error(f"Failed to create file {file_path}: {e}")
            raise FileOperationError(f"Failed to create file: {e}")
    
    async def get_file(self, file_id: UUID, user_id: UUID) -> File:
        """
        Get file by ID with permission check.
        
        Args:
            file_id: File UUID
            user_id: User requesting file
            
        Returns:
            File object if found and user has permission
            
        Raises:
            FileNotFoundError: If file not found
            FilePermissionError: If user lacks permissions
        """
        file = await self.repository.get_by_id(file_id)
        if not file:
            raise FileNotFoundError(f"File {file_id} not found")
        
        # Check project access
        if not await self.project_service.check_permission(
            project_id=file.project_id,
            user_id=user_id,
            required_role="viewer",
        ):
            raise FilePermissionError("Must be a project member to view files")
        
        return file
    
    async def get_file_content(self, file_id: UUID, user_id: UUID, ref: str = "HEAD") -> str:
        """
        Get file content from git or database.
        
        Args:
            file_id: File UUID
            user_id: User requesting content
            ref: Git reference (default: HEAD)
            
        Returns:
            File content as string
            
        Raises:
            FileNotFoundError: If file not found
            FilePermissionError: If user lacks permissions
        """
        file = await self.get_file(file_id, user_id)
        
        try:
            # Try to get content from git first
            if self.git_service.is_initialized():
                return self.git_service.read_file(file.path, ref)
            
            # Fallback to database content
            if file.content:
                return file.content
            
            raise FileNotFoundError(f"File content not available for {file.path}")
            
        except Exception as e:
            logger.error(f"Failed to get file content for {file.path}: {e}")
            raise FileOperationError(f"Failed to get file content: {e}")
    
    async def update_file_content(
        self,
        file_id: UUID,
        content: str,
        user_id: UUID,
        commit: bool = False,
        commit_message: Optional[str] = None,
    ) -> File:
        """
        Update file content with validation and optional git commit.
        
        Args:
            file_id: File UUID
            content: New file content
            user_id: User updating file
            commit: Whether to commit the changes
            commit_message: Custom commit message
            
        Returns:
            Updated File object
            
        Raises:
            FileNotFoundError: If file not found
            FilePermissionError: If user lacks permissions
            FileValidationError: If content validation fails
        """
        file = await self.get_file(file_id, user_id)
        
        # Check permissions (must be at least member)
        if not await self.project_service.check_permission(
            project_id=file.project_id,
            user_id=user_id,
            required_role="member",
        ):
            raise FilePermissionError("Must be at least a project member to update files")
        
        # Validate content
        await self._validate_file_content(file.path, content)
        
        try:
            # Update file in filesystem
            self.git_service.write_file(file.path, content)
            
            # Update file record
            updated_file = await self.repository.update_content(
                file_id=file_id,
                content=content,
            )
            
            if not updated_file:
                raise FileOperationError("Failed to update file record")
            
            # Optional git commit
            commit_sha = None
            if commit and self.git_service.is_initialized():
                if not commit_message:
                    commit_message = f"Update file: {file.path}"
                
                commit_info = self.git_service.commit(
                    message=commit_message,
                    author_name=await self._get_user_name(user_id),
                    author_email=await self._get_user_email(user_id),
                )
                commit_sha = commit_info["sha"]
                
                # Update file with git metadata
                await self.repository.update_from_git(
                    file_id=file_id,
                    commit_sha=commit_sha,
                    commit_message=commit_message,
                    modified_by_user_id=user_id,
                    modified_at=datetime.now(),
                )
            
            logger.info(f"Updated file content for {file.path}")
            return updated_file
            
        except Exception as e:
            logger.error(f"Failed to update file content for {file.path}: {e}")
            raise FileOperationError(f"Failed to update file content: {e}")
    
    async def rename_file(
        self,
        file_id: UUID,
        new_path: str,
        user_id: UUID,
        commit: bool = False,
        commit_message: Optional[str] = None,
    ) -> File:
        """
        Rename/move file with validation and optional git commit.
        
        Args:
            file_id: File UUID
            new_path: New file path
            user_id: User renaming file
            commit: Whether to commit the rename
            commit_message: Custom commit message
            
        Returns:
            Updated File object
            
        Raises:
            FileNotFoundError: If file not found
            FilePermissionError: If user lacks permissions
            FileValidationError: If new path is invalid
        """
        file = await self.get_file(file_id, user_id)
        
        # Check permissions (must be at least member)
        if not await self.project_service.check_permission(
            project_id=file.project_id,
            user_id=user_id,
            required_role="member",
        ):
            raise FilePermissionError("Must be at least a project member to rename files")
        
        # Validate new path
        await self._validate_file_rename(file.project_id, file.path, new_path)
        
        try:
            # Rename file in filesystem
            self.git_service.rename_file(file.path, new_path)
            
            # Update file record
            updated_file = await self.repository.update(
                file_id=file_id,
                update_data={
                    "path": new_path,
                    "name": Path(new_path).name,
                    "extension": Path(new_path).suffix,
                    "file_type": self._detect_file_type(new_path),
                    "language": self._detect_language(new_path),
                }
            )
            
            if not updated_file:
                raise FileOperationError("Failed to update file record")
            
            # Optional git commit
            commit_sha = None
            if commit and self.git_service.is_initialized():
                if not commit_message:
                    commit_message = f"Rename file: {file.path} → {new_path}"
                
                commit_info = self.git_service.commit(
                    message=commit_message,
                    author_name=await self._get_user_name(user_id),
                    author_email=await self._get_user_email(user_id),
                )
                commit_sha = commit_info["sha"]
                
                # Update file with git metadata
                await self.repository.update_from_git(
                    file_id=file_id,
                    commit_sha=commit_sha,
                    commit_message=commit_message,
                    modified_by_user_id=user_id,
                    modified_at=datetime.now(),
                )
            
            logger.info(f"Renamed file {file.path} to {new_path}")
            return updated_file
            
        except Exception as e:
            logger.error(f"Failed to rename file {file.path}: {e}")
            raise FileOperationError(f"Failed to rename file: {e}")
    
    async def delete_file(
        self,
        file_id: UUID,
        user_id: UUID,
        commit: bool = False,
        commit_message: Optional[str] = None,
    ) -> bool:
        """
        Delete file with optional git commit.
        
        Args:
            file_id: File UUID
            user_id: User deleting file
            commit: Whether to commit the deletion
            commit_message: Custom commit message
            
        Returns:
            True if deleted successfully
            
        Raises:
            FileNotFoundError: If file not found
            FilePermissionError: If user lacks permissions
        """
        file = await self.get_file(file_id, user_id)
        
        # Check permissions (must be at least admin)
        if not await self.project_service.check_permission(
            project_id=file.project_id,
            user_id=user_id,
            required_role="admin",
        ):
            raise FilePermissionError("Must be project admin or owner to delete files")
        
        try:
            # Delete file from filesystem
            self.git_service.delete_file(file.path, stage=commit)
            
            # Soft delete file record
            success = await self.repository.delete(file_id, soft=True)
            
            # Optional git commit
            if commit and self.git_service.is_initialized():
                if not commit_message:
                    commit_message = f"Delete file: {file.path}"
                
                self.git_service.commit(
                    message=commit_message,
                    author_name=await self._get_user_name(user_id),
                    author_email=await self._get_user_email(user_id),
                )
            
            logger.info(f"Deleted file {file.path}")
            return success
            
        except Exception as e:
            logger.error(f"Failed to delete file {file.path}: {e}")
            raise FileOperationError(f"Failed to delete file: {e}")
    
    async def list_project_files(
        self,
        project_id: UUID,
        user_id: UUID,
        directory: Optional[str] = None,
        file_type: Optional[FileType] = None,
        search: Optional[str] = None,
        include_deleted: bool = False,
        skip: int = 0,
        limit: int = 50,
    ) -> tuple[list[File], int]:
        """
        List files in a project with filtering and permission check.
        
        Args:
            project_id: Project UUID
            user_id: User requesting files
            directory: Optional directory filter
            file_type: Optional file type filter
            search: Optional search query
            include_deleted: Whether to include soft-deleted files
            skip: Pagination offset
            limit: Page size
            
        Returns:
            Tuple of (files list, total count)
            
        Raises:
            FilePermissionError: If user lacks permissions
        """
        # Check project access
        if not await self.project_service.check_permission(
            project_id=project_id,
            user_id=user_id,
            required_role="viewer",
        ):
            raise FilePermissionError("Must be a project member to view files")
        
        try:
            # Get files based on filters
            if directory:
                files = await self.repository.list_by_directory(
                    project_id=project_id,
                    directory=directory,
                    recursive=True,
                )
            elif search:
                files = await self.repository.search_files(
                    project_id=project_id,
                    query=search,
                    search_content=True,
                )
            else:
                files = await self.repository.list_by_project(
                    project_id=project_id,
                    file_type=file_type,
                    include_deleted=include_deleted,
                    skip=skip,
                    limit=limit,
                )
            
            # Get total count
            total = await self.repository.count_by_project(
                project_id=project_id,
                file_type=file_type,
                include_deleted=include_deleted,
            )
            
            return files, total
            
        except Exception as e:
            logger.error(f"Failed to list files for project {project_id}: {e}")
            raise FileOperationError(f"Failed to list files: {e}")
    
    async def search_files(
        self,
        project_id: UUID,
        user_id: UUID,
        query: str,
        search_content: bool = False,
        file_types: Optional[list[FileType]] = None,
        skip: int = 0,
        limit: int = 20,
    ) -> tuple[list[File], int]:
        """
        Search files in a project with permission check.
        
        Args:
            project_id: Project UUID
            user_id: User searching files
            query: Search query
            search_content: Whether to search in file content
            file_types: Optional file type filters
            skip: Pagination offset
            limit: Page size
            
        Returns:
            Tuple of (files list, total count)
            
        Raises:
            FilePermissionError: If user lacks permissions
        """
        # Check project access
        if not await self.project_service.check_permission(
            project_id=project_id,
            user_id=user_id,
            required_role="viewer",
        ):
            raise FilePermissionError("Must be a project member to search files")
        
        try:
            # Search files
            files = await self.repository.search_files(
                project_id=project_id,
                query=query,
                search_content=search_content,
            )
            
            # Filter by file types if specified
            if file_types:
                file_type_values = [ft.value for ft in file_types]
                files = [f for f in files if f.file_type in file_type_values]
            
            # Apply pagination
            total = len(files)
            paginated_files = files[skip:skip + limit]
            
            return paginated_files, total
            
        except Exception as e:
            logger.error(f"Failed to search files in project {project_id}: {e}")
            raise FileOperationError(f"Failed to search files: {e}")
    
    async def get_file_history(
        self,
        file_id: UUID,
        user_id: UUID,
        max_commits: int = 50,
    ) -> tuple[File, list[dict]]:
        """
        Get file with commit history.
        
        Args:
            file_id: File UUID
            user_id: User requesting history
            max_commits: Maximum number of commits to return
            
        Returns:
            Tuple of (file, commit history)
            
        Raises:
            FileNotFoundError: If file not found
            FilePermissionError: If user lacks permissions
        """
        file = await self.get_file(file_id, user_id)
        
        try:
            # Get commit history from git
            commits = []
            if self.git_service.is_initialized():
                git_commits = self.git_service.get_file_history(file.path, max_commits)
                commits = git_commits
            
            return file, commits
            
        except Exception as e:
            logger.error(f"Failed to get file history for {file.path}: {e}")
            raise FileOperationError(f"Failed to get file history: {e}")
    
    # ============= Helper Methods =============
    
    async def _validate_file_creation(self, project_id: UUID, file_path: str, content: str) -> None:
        """Validate file creation parameters."""
        # Check if file already exists
        existing_file = await self.repository.get_by_path(project_id, file_path)
        if existing_file and not existing_file.is_deleted:
            raise FileValidationError(f"File already exists: {file_path}")
        
        # Validate file path
        await self._validate_file_path(file_path)
        
        # Validate content
        await self._validate_file_content(file_path, content)
    
    async def _validate_file_rename(self, project_id: UUID, old_path: str, new_path: str) -> None:
        """Validate file rename parameters."""
        # Check if new path already exists
        existing_file = await self.repository.get_by_path(project_id, new_path)
        if existing_file and not existing_file.is_deleted:
            raise FileValidationError(f"File already exists at destination: {new_path}")
        
        # Validate new path
        await self._validate_file_path(new_path)
    
    async def _validate_file_path(self, file_path: str) -> None:
        """Validate file path format and security."""
        if not file_path or file_path.startswith("/") or file_path.startswith("\\"):
            raise FileValidationError("Invalid file path format")
        
        if ".." in file_path:
            raise FileValidationError("File path cannot contain parent directory references")
        
        # Check for forbidden patterns
        forbidden_patterns = [".git/", ".gitignore", ".DS_Store", "Thumbs.db"]
        for pattern in forbidden_patterns:
            if pattern in file_path:
                raise FileValidationError(f"File path contains forbidden pattern: {pattern}")
    
    async def _validate_file_content(self, file_path: str, content: str) -> None:
        """Validate file content."""
        # Check file size (10MB limit for database storage)
        content_size = len(content.encode('utf-8'))
        if content_size > 10 * 1024 * 1024:
            raise FileValidationError("File content too large (max 10MB)")
        
        # Additional validation based on file type
        file_ext = Path(file_path).suffix.lower()
        if file_ext in ['.py', '.js', '.ts', '.jsx', '.tsx']:
            # Basic syntax validation for code files
            if not content.strip():
                raise FileValidationError("Code files cannot be empty")
    
    def _detect_file_type(self, file_path: str) -> str:
        """Detect file type from path."""
        file_ext = Path(file_path).suffix.lower()
        file_name = Path(file_path).name.lower()
        
        # Code files
        code_extensions = {'.py', '.js', '.ts', '.jsx', '.tsx', '.java', '.cpp', '.c', '.h', '.cs', '.php', '.rb', '.go', '.rs', '.swift', '.kt'}
        if file_ext in code_extensions:
            return 'code'
        
        # Documentation files
        doc_extensions = {'.md', '.txt', '.rst', '.adoc', '.doc', '.docx', '.pdf'}
        if file_ext in doc_extensions:
            return 'doc'
        
        # Configuration files
        config_extensions = {'.json', '.yaml', '.yml', '.toml', '.ini', '.cfg', '.conf', '.xml', '.env'}
        config_names = {'package.json', 'requirements.txt', 'dockerfile', 'makefile', 'cmakelists.txt'}
        if file_ext in config_extensions or file_name in config_names:
            return 'config'
        
        # Test files
        if 'test' in file_name or 'spec' in file_name:
            return 'test'
        
        # Asset files
        asset_extensions = {'.png', '.jpg', '.jpeg', '.gif', '.svg', '.ico', '.mp3', '.mp4', '.wav', '.zip', '.tar', '.gz'}
        if file_ext in asset_extensions:
            return 'asset'
        
        return 'other'
    
    def _detect_language(self, file_path: str) -> Optional[str]:
        """Detect programming language from file extension."""
        ext_to_lang = {
            '.py': 'python',
            '.js': 'javascript',
            '.ts': 'typescript',
            '.jsx': 'javascript',
            '.tsx': 'typescript',
            '.java': 'java',
            '.cpp': 'cpp',
            '.c': 'c',
            '.h': 'c',
            '.cs': 'csharp',
            '.php': 'php',
            '.rb': 'ruby',
            '.go': 'go',
            '.rs': 'rust',
            '.swift': 'swift',
            '.kt': 'kotlin',
            '.html': 'html',
            '.css': 'css',
            '.scss': 'scss',
            '.sass': 'sass',
            '.less': 'less',
            '.sql': 'sql',
            '.sh': 'bash',
            '.json': 'json',
            '.yaml': 'yaml',
            '.yml': 'yaml',
            '.xml': 'xml',
        }
        
        file_ext = Path(file_path).suffix.lower()
        return ext_to_lang.get(file_ext)
    
    async def _get_user_name(self, user_id: UUID) -> str:
        """Get user name for git operations."""
        # This would typically query the user repository
        # For now, return a placeholder
        return f"User-{user_id.hex[:8]}"
    
    async def _get_user_email(self, user_id: UUID) -> str:
        """Get user email for git operations."""
        # This would typically query the user repository
        # For now, return a placeholder
        return f"user-{user_id.hex[:8]}@ardha.local"