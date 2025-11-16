"""
Unit tests for FileRepository.

This module tests all FileRepository methods to ensure proper
database operations, error handling, and data integrity.
"""

import pytest
from datetime import datetime, timedelta, timezone
from uuid import uuid4

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from ardha.models.file import File
from ardha.models.project import Project
from ardha.models.user import User
from ardha.repositories.file import FileRepository
from ardha.schemas.file import FileType


@pytest.fixture
async def file_repo(test_db: AsyncSession) -> FileRepository:
    """Create FileRepository instance for testing."""
    return FileRepository(test_db)


@pytest.fixture
async def test_user(test_db: AsyncSession) -> User:
    """Create test user for file operations."""
    user = User(
        id=uuid4(),
        email="filetest@example.com",
        username="filetestuser",
        full_name="File Test User",
        password_hash="hashed_password",
    )
    test_db.add(user)
    await test_db.commit()
    await test_db.refresh(user)
    return user


@pytest.fixture
async def test_project(test_db: AsyncSession, test_user: User) -> Project:
    """Create test project for file operations."""
    project = Project(
        id=uuid4(),
        name="File Test Project",
        slug="file-test-project",
        owner_id=test_user.id,
        visibility="private",
    )
    test_db.add(project)
    await test_db.commit()
    await test_db.refresh(project)
    return project


@pytest.fixture
async def sample_file(test_project: Project) -> File:
    """Create sample file for testing."""
    return File(
        id=uuid4(),
        project_id=test_project.id,
        path="src/main.py",
        name="main.py",
        extension=".py",
        file_type="code",
        content="print('Hello, World!')",
        content_hash=File.calculate_content_hash("print('Hello, World!')"),
        size_bytes=22,
        encoding="utf-8",
        language="python",
        is_binary=False,
    )


@pytest.fixture
async def sample_files_batch(test_project: Project) -> list[File]:
    """Create batch of sample files for testing."""
    files = []
    file_data = [
        ("src/utils.py", "code", "python", "# Utility functions\nThis file contains utility functions."),
        ("README.md", "doc", "markdown", "# Project README\nThis is the project README."),
        ("config.json", "config", "json", '{"debug": true}'),
        ("test_main.py", "test", "python", "# Test file\nThis is a test file."),
        ("assets/logo.png", "asset", None, None),  # Binary file
    ]
    
    for path, file_type, language, content in file_data:
        file_obj = File(
            id=uuid4(),
            project_id=test_project.id,
            path=path,
            name=path.split("/")[-1],
            extension="." + path.split(".")[-1] if "." in path else None,
            file_type=file_type,
            content=content,
            content_hash=File.calculate_content_hash(content) if content else None,
            size_bytes=len(content.encode()) if content else 1024,
            encoding="utf-8",
            language=language,
            is_binary=content is None,
        )
        files.append(file_obj)
    
    return files


class TestFileRepository:
    """Test suite for FileRepository methods."""

    @pytest.mark.asyncio
    async def test_create_file(self, file_repo: FileRepository, sample_file: File):
        """Test creating a new file."""
        created_file = await file_repo.create(sample_file)
        
        assert created_file.id == sample_file.id
        assert created_file.path == sample_file.path
        assert created_file.project_id == sample_file.project_id
        assert created_file.created_at is not None
        assert created_file.updated_at is not None

    @pytest.mark.asyncio
    async def test_create_file_duplicate_path(
        self, file_repo: FileRepository, sample_file: File, test_db: AsyncSession
    ):
        """Test creating file with duplicate path raises IntegrityError."""
        # Create first file
        await file_repo.create(sample_file)
        
        # Try to create duplicate
        duplicate_file = File(
            id=uuid4(),
            project_id=sample_file.project_id,
            path=sample_file.path,  # Same path
            name="duplicate.py",
            file_type="code",
        )
        
        with pytest.raises(IntegrityError):
            await file_repo.create(duplicate_file)

    @pytest.mark.asyncio
    async def test_get_by_id(self, file_repo: FileRepository, sample_file: File):
        """Test fetching file by ID."""
        # Create file first
        created_file = await file_repo.create(sample_file)
        
        # Fetch by ID
        fetched_file = await file_repo.get_by_id(created_file.id)
        
        assert fetched_file is not None
        assert fetched_file.id == created_file.id
        assert fetched_file.path == created_file.path

    @pytest.mark.asyncio
    async def test_get_by_id_not_found(self, file_repo: FileRepository):
        """Test fetching non-existent file by ID."""
        non_existent_id = uuid4()
        fetched_file = await file_repo.get_by_id(non_existent_id)
        
        assert fetched_file is None

    @pytest.mark.asyncio
    async def test_get_by_path(self, file_repo: FileRepository, sample_file: File):
        """Test fetching file by project_id and path."""
        # Create file first
        created_file = await file_repo.create(sample_file)
        
        # Fetch by path
        fetched_file = await file_repo.get_by_path(
            created_file.project_id, created_file.path
        )
        
        assert fetched_file is not None
        assert fetched_file.id == created_file.id
        assert fetched_file.path == created_file.path

    @pytest.mark.asyncio
    async def test_get_by_path_not_found(self, file_repo: FileRepository, test_project: Project):
        """Test fetching non-existent file by path."""
        fetched_file = await file_repo.get_by_path(test_project.id, "nonexistent.py")
        
        assert fetched_file is None

    @pytest.mark.asyncio
    async def test_list_by_project(
        self, file_repo: FileRepository, sample_files_batch: list[File]
    ):
        """Test listing files by project."""
        # Create files
        for file_obj in sample_files_batch:
            await file_repo.create(file_obj)
        
        # List all files
        files = await file_repo.list_by_project(sample_files_batch[0].project_id)
        
        assert len(files) == len(sample_files_batch)
        assert all(f.project_id == sample_files_batch[0].project_id for f in files)

    @pytest.mark.asyncio
    async def test_list_by_project_with_filters(
        self, file_repo: FileRepository, sample_files_batch: list[File]
    ):
        """Test listing files by project with filters."""
        # Create files
        for file_obj in sample_files_batch:
            await file_repo.create(file_obj)
        
        project_id = sample_files_batch[0].project_id
        
        # Filter by file type
        code_files = await file_repo.list_by_project(
            project_id, file_type=FileType.CODE
        )
        assert len(code_files) == 1  # src/utils.py (only one with file_type="code")
        
        # Filter by language
        python_files = await file_repo.list_by_project(
            project_id, language="python"
        )
        assert len(python_files) == 2  # src/utils.py, test_main.py

    @pytest.mark.asyncio
    async def test_list_by_directory(
        self, file_repo: FileRepository, sample_files_batch: list[File]
    ):
        """Test listing files by directory."""
        # Create files
        for file_obj in sample_files_batch:
            await file_repo.create(file_obj)
        
        project_id = sample_files_batch[0].project_id
        
        # List files in src directory
        src_files = await file_repo.list_by_directory(project_id, "src")
        assert len(src_files) == 1  # src/utils.py (only one in test data)
        
        # List files recursively
        all_files = await file_repo.list_by_directory(project_id, "src", recursive=True)
        assert len(all_files) == 1  # Same files, no subdirectories in test data

    @pytest.mark.asyncio
    async def test_search_files(
        self, file_repo: FileRepository, sample_files_batch: list[File]
    ):
        """Test searching files by name."""
        # Create files
        for file_obj in sample_files_batch:
            await file_repo.create(file_obj)
        
        project_id = sample_files_batch[0].project_id
        
        # Search by name
        results = await file_repo.search_files(project_id, "main")
        assert len(results) == 1
        assert "main" in results[0].name
        
        # Search by path
        results = await file_repo.search_files(project_id, "src")
        assert len(results) == 1  # src/utils.py (only one in test data)

    @pytest.mark.asyncio
    async def test_search_files_with_content(
        self, file_repo: FileRepository, sample_files_batch: list[File]
    ):
        """Test searching files including content."""
        # Create files
        for file_obj in sample_files_batch:
            await file_repo.create(file_obj)
        
        project_id = sample_files_batch[0].project_id
        
        # Search including content
        results = await file_repo.search_files(project_id, "Utility", search_content=True)
        assert len(results) == 1  # src/utils.py contains "Utility"

    @pytest.mark.asyncio
    async def test_update_file(self, file_repo: FileRepository, sample_file: File):
        """Test updating file fields."""
        # Create file first
        created_file = await file_repo.create(sample_file)
        
        # Update file
        update_data = {
            "name": "updated_main.py",
            "file_type": "test",
            "language": "python",
        }
        updated_file = await file_repo.update(created_file.id, update_data)
        
        assert updated_file is not None
        assert updated_file.name == "updated_main.py"
        assert updated_file.file_type == "test"
        assert updated_file.language == "python"

    @pytest.mark.asyncio
    async def test_update_file_not_found(self, file_repo: FileRepository):
        """Test updating non-existent file."""
        non_existent_id = uuid4()
        update_data = {"name": "updated.py"}
        
        updated_file = await file_repo.update(non_existent_id, update_data)
        assert updated_file is None

    @pytest.mark.asyncio
    async def test_update_content(self, file_repo: FileRepository, sample_file: File):
        """Test updating file content."""
        # Create file first
        created_file = await file_repo.create(sample_file)
        
        # Update content
        new_content = "print('Updated content!')"
        updated_file = await file_repo.update_content(created_file.id, new_content)
        
        assert updated_file is not None
        assert updated_file.content == new_content
        assert updated_file.content_hash == File.calculate_content_hash(new_content)
        assert updated_file.size_bytes == len(new_content.encode())

    @pytest.mark.asyncio
    async def test_update_from_git(
        self, file_repo: FileRepository, sample_file: File, test_user: User
    ):
        """Test updating file git metadata."""
        # Create file first
        created_file = await file_repo.create(sample_file)
        
        # Update git metadata
        commit_sha = "abc123def456789012345678901234567890abcd"
        commit_message = "Update main.py"
        modified_at = datetime.now(timezone.utc)
        
        updated_file = await file_repo.update_from_git(
            created_file.id, commit_sha, commit_message, test_user.id, modified_at
        )
        
        assert updated_file is not None
        assert updated_file.last_commit_sha == commit_sha
        assert updated_file.last_commit_message == commit_message
        assert updated_file.last_modified_by_user_id == test_user.id
        assert updated_file.last_modified_at == modified_at

    @pytest.mark.asyncio
    async def test_delete_file_soft(self, file_repo: FileRepository, sample_file: File):
        """Test soft deleting a file."""
        # Create file first
        created_file = await file_repo.create(sample_file)
        
        # Soft delete
        deleted = await file_repo.delete(created_file.id, soft=True)
        assert deleted is True
        
        # Verify file is soft deleted
        deleted_file = await file_repo.get_by_id(created_file.id)
        assert deleted_file is not None
        assert deleted_file.is_deleted is True
        assert deleted_file.deleted_at is not None

    @pytest.mark.asyncio
    async def test_delete_file_hard(self, file_repo: FileRepository, sample_file: File):
        """Test hard deleting a file."""
        # Create file first
        created_file = await file_repo.create(sample_file)
        
        # Hard delete
        deleted = await file_repo.delete(created_file.id, soft=False)
        assert deleted is True
        
        # Verify file is completely deleted
        deleted_file = await file_repo.get_by_id(created_file.id)
        assert deleted_file is None

    @pytest.mark.asyncio
    async def test_restore_file(self, file_repo: FileRepository, sample_file: File):
        """Test restoring a soft-deleted file."""
        # Create and soft delete file
        created_file = await file_repo.create(sample_file)
        await file_repo.delete(created_file.id, soft=True)
        
        # Restore file
        restored_file = await file_repo.restore(created_file.id)
        
        assert restored_file is not None
        assert restored_file.is_deleted is False
        assert restored_file.deleted_at is None

    @pytest.mark.asyncio
    async def test_count_by_project(
        self, file_repo: FileRepository, sample_files_batch: list[File]
    ):
        """Test counting files by project."""
        project_id = sample_files_batch[0].project_id
        
        # Count before creating
        count_before = await file_repo.count_by_project(project_id)
        assert count_before == 0
        
        # Create files
        for file_obj in sample_files_batch:
            await file_repo.create(file_obj)
        
        # Count after creating
        count_after = await file_repo.count_by_project(project_id)
        assert count_after == len(sample_files_batch)

    @pytest.mark.asyncio
    async def test_get_file_with_commits(self, file_repo: FileRepository, sample_file: File):
        """Test getting file with commit history."""
        # Create file first
        created_file = await file_repo.create(sample_file)
        
        # Get file with commits (should be empty for now)
        result = await file_repo.get_file_with_commits(created_file.id)
        
        assert result is not None
        file, commits = result
        assert file.id == created_file.id
        assert len(commits) == 0  # No commits linked yet

    @pytest.mark.asyncio
    async def test_bulk_create(
        self, file_repo: FileRepository, sample_files_batch: list[File]
    ):
        """Test bulk creating files."""
        # Bulk create files
        created_files = await file_repo.bulk_create(sample_files_batch)
        
        assert len(created_files) == len(sample_files_batch)
        assert all(f.id is not None for f in created_files)
        
        # Verify all files were created
        project_id = sample_files_batch[0].project_id
        count = await file_repo.count_by_project(project_id)
        assert count == len(sample_files_batch)

    @pytest.mark.asyncio
    async def test_get_files_modified_since(
        self, file_repo: FileRepository, sample_file: File, test_user: User
    ):
        """Test getting files modified since a specific date."""
        # Create file first
        created_file = await file_repo.create(sample_file)
        
        # Update with git metadata to set last_modified_at
        commit_time = datetime.now(timezone.utc)
        await file_repo.update_from_git(
            created_file.id, "abc123", "Test commit", test_user.id, commit_time
        )
        
        # Get files modified since earlier time
        earlier_time = commit_time.replace(second=0, microsecond=0) - timedelta(minutes=1)
        modified_files = await file_repo.get_files_modified_since(
            created_file.project_id, earlier_time
        )
        
        assert len(modified_files) == 1
        assert modified_files[0].id == created_file.id

    @pytest.mark.asyncio
    async def test_list_by_project_pagination(
        self, file_repo: FileRepository, sample_files_batch: list[File]
    ):
        """Test pagination in list_by_project."""
        # Create files
        for file_obj in sample_files_batch:
            await file_repo.create(file_obj)
        
        project_id = sample_files_batch[0].project_id
        
        # Test pagination
        first_page = await file_repo.list_by_project(project_id, skip=0, limit=2)
        second_page = await file_repo.list_by_project(project_id, skip=2, limit=2)
        
        assert len(first_page) == 2
        assert len(second_page) == 2
        
        # Ensure no overlap
        first_page_ids = {f.id for f in first_page}
        second_page_ids = {f.id for f in second_page}
        assert len(first_page_ids.intersection(second_page_ids)) == 0

    @pytest.mark.asyncio
    async def test_update_content_recalculates_hash(
        self, file_repo: FileRepository, sample_file: File
    ):
        """Test that updating content recalculates hash correctly."""
        # Create file first
        created_file = await file_repo.create(sample_file)
        original_hash = created_file.content_hash
        
        # Update content
        new_content = "print('Completely different content!')"
        updated_file = await file_repo.update_content(created_file.id, new_content)
        
        assert updated_file is not None
        assert updated_file.content_hash != original_hash
        assert updated_file.content_hash == File.calculate_content_hash(new_content)

    @pytest.mark.asyncio
    async def test_search_files_case_insensitive(
        self, file_repo: FileRepository, sample_files_batch: list[File]
    ):
        """Test that file search is case insensitive."""
        # Create files
        for file_obj in sample_files_batch:
            await file_repo.create(file_obj)
        
        project_id = sample_files_batch[0].project_id
        
        # Search with different case
        results_lower = await file_repo.search_files(project_id, "main")
        results_upper = await file_repo.search_files(project_id, "MAIN")
        
        assert len(results_lower) == len(results_upper) == 1
        assert results_lower[0].id == results_upper[0].id