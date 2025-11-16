"""
Unit tests for GitCommitRepository.

This module tests all GitCommitRepository methods to ensure proper
database operations, error handling, and relationship management.
"""

from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from ardha.models.file import File
from ardha.models.git_commit import GitCommit
from ardha.models.project import Project
from ardha.models.task import Task
from ardha.models.user import User
from ardha.repositories.git_commit import GitCommitRepository
from ardha.schemas.file import ChangeType


@pytest.fixture
async def commit_repo(test_db: AsyncSession) -> GitCommitRepository:
    """Create GitCommitRepository instance for testing."""
    return GitCommitRepository(test_db)


@pytest.fixture
async def test_user(test_db: AsyncSession) -> User:
    """Create test user for commit operations."""
    user = User(
        id=uuid4(),
        email="commit@example.com",
        username="commituser",
        full_name="Commit Test User",
        password_hash="hashed_password",
    )
    test_db.add(user)
    await test_db.flush()
    return user


@pytest.fixture
async def test_project(test_db: AsyncSession, test_user: User) -> Project:
    """Create test project for commit operations."""
    project = Project(
        id=uuid4(),
        name="Commit Test Project",
        slug="commit-test-project",
        owner_id=test_user.id,
        visibility="private",
    )
    test_db.add(project)
    await test_db.flush()
    return project


@pytest.fixture
async def test_file(test_db: AsyncSession, test_project: Project) -> File:
    """Create test file for commit operations."""
    file = File(
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
    test_db.add(file)
    await test_db.flush()
    return file


@pytest.fixture
async def test_task(test_db: AsyncSession, test_project: Project, test_user: User) -> Task:
    """Create test task for commit operations."""
    task = Task(
        id=uuid4(),
        project_id=test_project.id,
        identifier="TASK-001",  # Add required identifier field
        title="Test Task",
        description="A test task for commit testing",
        priority="medium",
        status="todo",
        created_by_id=test_user.id,  # Add required created_by_id field
    )
    test_db.add(task)
    await test_db.flush()
    return task


@pytest.fixture
async def sample_commit(test_project: Project, test_user: User) -> GitCommit:
    """Create sample git commit for testing."""
    return GitCommit(
        id=uuid4(),
        project_id=test_project.id,
        sha="abc123def456789012345678901234567890abcd",
        short_sha="abc123d",
        branch="main",
        author_name="Test Author",
        author_email="author@example.com",
        committed_at=datetime.now(timezone.utc),
        message="Initial commit",
        ardha_user_id=test_user.id,
    )


@pytest.fixture
async def sample_commits_batch(test_project: Project, test_user: User) -> list[GitCommit]:
    """Create batch of sample commits for testing."""
    commits = []
    base_time = datetime.now(timezone.utc)

    for i in range(5):
        commit = GitCommit(
            id=uuid4(),
            project_id=test_project.id,
            sha=f"abc123def456{i:03d}901234567890abcd",
            short_sha=f"abc12{i:02d}",  # Ensure exactly 7 characters
            branch="main",
            author_name="Test Author",
            author_email="author@example.com",
            committed_at=base_time - timedelta(hours=i),
            message=f"Commit {i+1}",
            ardha_user_id=test_user.id,
        )
        commits.append(commit)

    return commits


class TestGitCommitRepository:
    """Test suite for GitCommitRepository methods."""

    @pytest.mark.asyncio
    async def test_create_commit(self, commit_repo: GitCommitRepository, sample_commit: GitCommit):
        """Test creating a new git commit."""
        created_commit = await commit_repo.create(sample_commit)

        assert created_commit.id == sample_commit.id
        assert created_commit.sha == sample_commit.sha
        assert created_commit.project_id == sample_commit.project_id
        assert created_commit.created_at is not None
        assert created_commit.updated_at is not None

    @pytest.mark.asyncio
    async def test_create_commit_duplicate_sha(
        self, commit_repo: GitCommitRepository, sample_commit: GitCommit, test_db: AsyncSession
    ):
        """Test creating commit with duplicate SHA raises IntegrityError."""
        # Create first commit
        await commit_repo.create(sample_commit)

        # Try to create duplicate
        duplicate_commit = GitCommit(
            id=uuid4(),
            project_id=sample_commit.project_id,
            sha=sample_commit.sha,  # Same SHA
            short_sha="dup123",
            branch="main",
            author_name="Duplicate Author",
            author_email="dup@example.com",
            committed_at=datetime.now(timezone.utc),
            message="Duplicate commit",
        )

        with pytest.raises(IntegrityError):
            await commit_repo.create(duplicate_commit)

    @pytest.mark.asyncio
    async def test_get_by_id(self, commit_repo: GitCommitRepository, sample_commit: GitCommit):
        """Test fetching commit by ID."""
        # Create commit first
        created_commit = await commit_repo.create(sample_commit)

        # Fetch by ID
        fetched_commit = await commit_repo.get_by_id(created_commit.id)

        assert fetched_commit is not None
        assert fetched_commit.id == created_commit.id
        assert fetched_commit.sha == created_commit.sha

    @pytest.mark.asyncio
    async def test_get_by_id_not_found(self, commit_repo: GitCommitRepository):
        """Test fetching non-existent commit by ID."""
        non_existent_id = uuid4()
        fetched_commit = await commit_repo.get_by_id(non_existent_id)

        assert fetched_commit is None

    @pytest.mark.asyncio
    async def test_get_by_sha_full(
        self, commit_repo: GitCommitRepository, sample_commit: GitCommit
    ):
        """Test fetching commit by full SHA."""
        # Create commit first
        created_commit = await commit_repo.create(sample_commit)

        # Fetch by full SHA
        fetched_commit = await commit_repo.get_by_sha(created_commit.project_id, created_commit.sha)

        assert fetched_commit is not None
        assert fetched_commit.id == created_commit.id
        assert fetched_commit.sha == created_commit.sha

    @pytest.mark.asyncio
    async def test_get_by_sha_short(
        self, commit_repo: GitCommitRepository, sample_commit: GitCommit
    ):
        """Test fetching commit by short SHA."""
        # Create commit first
        created_commit = await commit_repo.create(sample_commit)

        # Fetch by short SHA
        fetched_commit = await commit_repo.get_by_sha(
            created_commit.project_id, created_commit.short_sha
        )

        assert fetched_commit is not None
        assert fetched_commit.id == created_commit.id
        assert fetched_commit.short_sha == created_commit.short_sha

    @pytest.mark.asyncio
    async def test_get_by_sha_not_found(
        self, commit_repo: GitCommitRepository, test_project: Project
    ):
        """Test fetching non-existent commit by SHA."""
        fetched_commit = await commit_repo.get_by_sha(test_project.id, "nonexistent")

        assert fetched_commit is None

    @pytest.mark.asyncio
    async def test_list_by_project(
        self, commit_repo: GitCommitRepository, sample_commits_batch: list[GitCommit]
    ):
        """Test listing commits by project."""
        # Create commits
        for commit in sample_commits_batch:
            await commit_repo.create(commit)

        project_id = sample_commits_batch[0].project_id

        # List all commits
        commits = await commit_repo.list_by_project(project_id)

        assert len(commits) == len(sample_commits_batch)
        assert all(c.project_id == project_id for c in commits)
        # Should be ordered by committed_at DESC
        for i in range(len(commits) - 1):
            assert commits[i].committed_at >= commits[i + 1].committed_at

    @pytest.mark.asyncio
    async def test_list_by_project_with_filters(
        self, commit_repo: GitCommitRepository, sample_commits_batch: list[GitCommit]
    ):
        """Test listing commits by project with filters."""
        # Create commits
        for commit in sample_commits_batch:
            await commit_repo.create(commit)

        project_id = sample_commits_batch[0].project_id

        # Filter by branch
        main_commits = await commit_repo.list_by_project(project_id, branch="main")
        assert len(main_commits) == len(sample_commits_batch)

        # Filter by author
        author_commits = await commit_repo.list_by_project(
            project_id, author_email="author@example.com"
        )
        assert len(author_commits) == len(sample_commits_batch)

    @pytest.mark.asyncio
    async def test_list_by_file(
        self,
        commit_repo: GitCommitRepository,
        sample_commit: GitCommit,
        test_file: File,
        test_db: AsyncSession,
    ):
        """Test listing commits that changed a specific file."""
        # Create commit and link to file
        await commit_repo.create(sample_commit)
        await commit_repo.link_to_files(
            sample_commit.id,
            [
                {
                    "file_id": test_file.id,
                    "change_type": ChangeType.MODIFIED,
                    "insertions": 10,
                    "deletions": 5,
                }
            ],
        )

        # List commits for file
        commits = await commit_repo.list_by_file(test_file.id)

        assert len(commits) == 1
        assert commits[0].id == sample_commit.id

    @pytest.mark.asyncio
    async def test_list_by_task(
        self,
        commit_repo: GitCommitRepository,
        sample_commit: GitCommit,
        test_task: Task,
        test_db: AsyncSession,
    ):
        """Test listing commits linked to a specific task."""
        # Create commit and link to task
        await commit_repo.create(sample_commit)
        await commit_repo.link_to_tasks(sample_commit.id, [test_task.id])

        # List commits for task
        commits = await commit_repo.list_by_task(test_task.id)

        assert len(commits) == 1
        assert commits[0].id == sample_commit.id

    @pytest.mark.asyncio
    async def test_list_by_user(
        self,
        commit_repo: GitCommitRepository,
        sample_commits_batch: list[GitCommit],
        test_user: User,
    ):
        """Test listing commits by Ardha user."""
        # Create commits
        for commit in sample_commits_batch:
            await commit_repo.create(commit)

        # List commits by user
        commits = await commit_repo.list_by_user(test_user.id)

        assert len(commits) == len(sample_commits_batch)
        assert all(c.ardha_user_id == test_user.id for c in commits)

    @pytest.mark.asyncio
    async def test_update_commit(self, commit_repo: GitCommitRepository, sample_commit: GitCommit):
        """Test updating commit fields."""
        # Create commit first
        created_commit = await commit_repo.create(sample_commit)

        # Update commit
        update_data = {
            "message": "Updated commit message",
            "pushed_at": datetime.now(timezone.utc),
        }
        updated_commit = await commit_repo.update(created_commit.id, update_data)

        assert updated_commit is not None
        assert updated_commit.message == "Updated commit message"
        assert updated_commit.pushed_at is not None

    @pytest.mark.asyncio
    async def test_update_commit_not_found(self, commit_repo: GitCommitRepository):
        """Test updating non-existent commit."""
        non_existent_id = uuid4()
        update_data = {"message": "Updated"}

        updated_commit = await commit_repo.update(non_existent_id, update_data)
        assert updated_commit is None

    @pytest.mark.asyncio
    async def test_link_to_tasks(
        self, commit_repo: GitCommitRepository, sample_commit: GitCommit, test_task: Task
    ):
        """Test linking a commit to multiple tasks."""
        # Create commit first
        created_commit = await commit_repo.create(sample_commit)

        # Link to tasks
        await commit_repo.link_to_tasks(created_commit.id, [test_task.id])

        # Verify link was created (by listing commits for task)
        commits = await commit_repo.list_by_task(test_task.id)
        assert len(commits) == 1
        assert commits[0].id == created_commit.id

    @pytest.mark.asyncio
    async def test_unlink_from_tasks(
        self, commit_repo: GitCommitRepository, sample_commit: GitCommit, test_task: Task
    ):
        """Test unlinking a commit from tasks."""
        # Create commit and link to task
        created_commit = await commit_repo.create(sample_commit)
        await commit_repo.link_to_tasks(created_commit.id, [test_task.id])

        # Verify link exists
        commits_before = await commit_repo.list_by_task(test_task.id)
        assert len(commits_before) == 1

        # Unlink from task
        await commit_repo.unlink_from_tasks(created_commit.id, [test_task.id])

        # Verify link was removed
        commits_after = await commit_repo.list_by_task(test_task.id)
        assert len(commits_after) == 0

    @pytest.mark.asyncio
    async def test_link_to_files(
        self, commit_repo: GitCommitRepository, sample_commit: GitCommit, test_file: File
    ):
        """Test linking a commit to files with change details."""
        # Create commit first
        created_commit = await commit_repo.create(sample_commit)

        # Link to files
        file_changes = [
            {
                "file_id": test_file.id,
                "change_type": ChangeType.ADDED,
                "old_path": None,
                "insertions": 22,
                "deletions": 0,
            }
        ]
        await commit_repo.link_to_files(created_commit.id, file_changes)

        # Verify link was created
        result = await commit_repo.get_commit_with_files(created_commit.id)
        assert result is not None
        commit, files = result
        assert len(files) == 1
        assert files[0][0].id == test_file.id
        assert files[0][1]["change_type"] == ChangeType.ADDED

    @pytest.mark.asyncio
    async def test_get_commit_with_files(
        self, commit_repo: GitCommitRepository, sample_commit: GitCommit, test_file: File
    ):
        """Test getting commit with file changes."""
        # Create commit and link to file
        await commit_repo.create(sample_commit)
        await commit_repo.link_to_files(
            sample_commit.id,
            [
                {
                    "file_id": test_file.id,
                    "change_type": ChangeType.MODIFIED,
                    "old_path": "src/old_main.py",
                    "insertions": 10,
                    "deletions": 5,
                }
            ],
        )

        # Get commit with files
        result = await commit_repo.get_commit_with_files(sample_commit.id)

        assert result is not None
        commit, files = result
        assert commit.id == sample_commit.id
        assert len(files) == 1
        file, change_info = files[0]
        assert file.id == test_file.id
        assert change_info["change_type"] == ChangeType.MODIFIED
        assert change_info["old_path"] == "src/old_main.py"
        assert change_info["insertions"] == 10
        assert change_info["deletions"] == 5

    @pytest.mark.asyncio
    async def test_count_by_project(
        self, commit_repo: GitCommitRepository, sample_commits_batch: list[GitCommit]
    ):
        """Test counting commits by project."""
        project_id = sample_commits_batch[0].project_id

        # Count before creating
        count_before = await commit_repo.count_by_project(project_id)
        assert count_before == 0

        # Create commits
        for commit in sample_commits_batch:
            await commit_repo.create(commit)

        # Count after creating
        count_after = await commit_repo.count_by_project(project_id)
        assert count_after == len(sample_commits_batch)

    @pytest.mark.asyncio
    async def test_get_latest_commit(
        self, commit_repo: GitCommitRepository, sample_commits_batch: list[GitCommit]
    ):
        """Test getting latest commit in a project."""
        project_id = sample_commits_batch[0].project_id

        # Create commits
        for commit in sample_commits_batch:
            await commit_repo.create(commit)

        # Get latest commit
        latest_commit = await commit_repo.get_latest_commit(project_id)

        assert latest_commit is not None
        # Should be the most recent (committed_at DESC)
        all_commits = await commit_repo.list_by_project(project_id)
        assert latest_commit.id == all_commits[0].id

    @pytest.mark.asyncio
    async def test_bulk_create(
        self, commit_repo: GitCommitRepository, sample_commits_batch: list[GitCommit]
    ):
        """Test bulk creating commits."""
        # Bulk create commits
        created_commits = await commit_repo.bulk_create(sample_commits_batch)

        assert len(created_commits) == len(sample_commits_batch)
        assert all(c.id is not None for c in created_commits)

        # Verify all commits were created
        project_id = sample_commits_batch[0].project_id
        count = await commit_repo.count_by_project(project_id)
        assert count == len(sample_commits_batch)

    @pytest.mark.asyncio
    async def test_list_by_project_pagination(
        self, commit_repo: GitCommitRepository, sample_commits_batch: list[GitCommit]
    ):
        """Test pagination in list_by_project."""
        project_id = sample_commits_batch[0].project_id

        # Create commits
        for commit in sample_commits_batch:
            await commit_repo.create(commit)

        # Test pagination
        first_page = await commit_repo.list_by_project(project_id, skip=0, limit=2)
        second_page = await commit_repo.list_by_project(project_id, skip=2, limit=2)

        assert len(first_page) == 2
        assert len(second_page) == 2

        # Ensure no overlap
        first_page_ids = {c.id for c in first_page}
        second_page_ids = {c.id for c in second_page}
        assert len(first_page_ids.intersection(second_page_ids)) == 0

    @pytest.mark.asyncio
    async def test_list_by_project_date_range(
        self, commit_repo: GitCommitRepository, sample_commits_batch: list[GitCommit]
    ):
        """Test listing commits with date range filter."""
        project_id = sample_commits_batch[0].project_id

        # Create commits
        for commit in sample_commits_batch:
            await commit_repo.create(commit)

        # Get date range (middle 3 commits)
        since = sample_commits_batch[2].committed_at
        until = sample_commits_batch[1].committed_at

        # Filter by date range
        commits = await commit_repo.list_by_project(project_id, since=since, until=until)

        assert len(commits) == 2  # Should include commits 2 and 1

    @pytest.mark.asyncio
    async def test_link_to_tasks_with_type(
        self, commit_repo: GitCommitRepository, sample_commit: GitCommit, test_task: Task
    ):
        """Test linking commit to tasks with specific link type."""
        # Create commit first
        created_commit = await commit_repo.create(sample_commit)

        # Link to tasks with custom type
        await commit_repo.link_to_tasks(created_commit.id, [test_task.id], link_type="closes")

        # Verify link was created
        commits = await commit_repo.list_by_task(test_task.id)
        assert len(commits) == 1
        assert commits[0].id == created_commit.id

    @pytest.mark.asyncio
    async def test_get_latest_commit_by_branch(
        self, commit_repo: GitCommitRepository, sample_commits_batch: list[GitCommit]
    ):
        """Test getting latest commit for specific branch."""
        project_id = sample_commits_batch[0].project_id

        # Create commits
        for commit in sample_commits_batch:
            await commit_repo.create(commit)

        # Get latest for main branch
        latest_main = await commit_repo.get_latest_commit(project_id, branch="main")
        assert latest_main is not None

        # Get latest for non-existent branch
        latest_other = await commit_repo.get_latest_commit(project_id, branch="feature")
        assert latest_other is None

    @pytest.mark.asyncio
    async def test_list_by_user_with_project_filter(
        self,
        commit_repo: GitCommitRepository,
        sample_commits_batch: list[GitCommit],
        test_user: User,
    ):
        """Test listing commits by user with project filter."""
        project_id = sample_commits_batch[0].project_id

        # Create commits
        for commit in sample_commits_batch:
            await commit_repo.create(commit)

        # List commits by user with project filter
        commits = await commit_repo.list_by_user(test_user.id, project_id=project_id)
        assert len(commits) == len(sample_commits_batch)

        # List commits by user without project filter
        all_user_commits = await commit_repo.list_by_user(test_user.id)
        assert len(all_user_commits) == len(sample_commits_batch)
