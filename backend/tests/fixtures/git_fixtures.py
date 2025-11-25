"""
Git test fixtures for testing GitService.

This module provides pytest fixtures for creating temporary git repositories
and GitService instances for comprehensive testing.
"""

import tempfile
from pathlib import Path
from typing import Generator

import pytest
from git import Repo

from ardha.services.git_service import GitService


@pytest.fixture
def temp_dir() -> Generator[Path, None, None]:
    """Create temporary directory for testing."""
    with tempfile.TemporaryDirectory() as temp_dir:
        yield Path(temp_dir)


@pytest.fixture
def temp_git_repo(temp_dir: Path) -> Generator[Path, None, None]:
    """Create temporary git repository for testing."""
    repo_path = temp_dir / "test_repo"
    repo_path.mkdir()

    # Initialize git repository
    repo = Repo.init(repo_path)

    # Configure git user using git commands
    repo.git.config("user.name", "Test User")
    repo.git.config("user.email", "test@example.com")

    # Create initial commit
    readme_file = repo_path / "README.md"
    readme_file.write_text("# Test Repository\n\nThis is a test repository.")
    repo.index.add(["README.md"])

    # Use repo.git.commit for initial commit
    repo.git.commit("-m", "Initial commit: Add README")

    yield repo_path


@pytest.fixture
def git_service(temp_git_repo: Path) -> GitService:
    """GitService instance for testing."""
    return GitService(temp_git_repo)


@pytest.fixture
def git_service_with_files(temp_git_repo: Path) -> tuple[GitService, Path]:
    """GitService instance with test files created."""
    service = GitService(temp_git_repo)

    # Create test files
    test_file1 = temp_git_repo / "test1.py"
    test_file1.write_text("print('Hello, World!')")

    test_file2 = temp_git_repo / "test2.js"
    test_file2.write_text("console.log('Hello, World!');")

    # Create subdirectory with file
    subdir = temp_git_repo / "src"
    subdir.mkdir()
    test_file3 = subdir / "main.py"
    test_file3.write_text("def main():\n    pass")

    # Stage and commit all files
    service.stage_files(["test1.py", "test2.js", "src/main.py"])
    service.commit("Add test files")

    return service, temp_git_repo


@pytest.fixture
def git_service_with_commits(temp_git_repo: Path) -> GitService:
    """GitService instance with multiple commits."""
    service = GitService(temp_git_repo)

    # First commit: Add Python file
    py_file = temp_git_repo / "app.py"
    py_file.write_text("def hello():\n    return 'Hello'")
    service.stage_files(["app.py"])
    service.commit("feat: Add Python application")

    # Second commit: Add JavaScript file
    js_file = temp_git_repo / "app.js"
    js_file.write_text("function hello() {\n    return 'Hello';\n}")
    service.stage_files(["app.js"])
    service.commit("feat: Add JavaScript application")

    # Third commit: Update Python file
    py_file.write_text("def hello():\n    return 'Hello, World!'")
    service.stage_files(["app.py"])
    service.commit("fix: Update Python greeting")

    return service


@pytest.fixture
def git_service_with_branches(temp_git_repo: Path) -> GitService:
    """GitService instance with multiple branches."""
    service = GitService(temp_git_repo)

    # Create feature branch
    service.create_branch("feature/test")

    # Switch to feature branch and add file
    service.switch_branch("feature/test")
    feature_file = temp_git_repo / "feature.txt"
    feature_file.write_text("This is a feature file.")
    service.stage_files(["feature.txt"])
    service.commit("feat: Add feature file")

    # Switch back to main
    service.switch_branch("main")

    # Create another branch
    service.create_branch("bugfix/issue-123")

    return service


@pytest.fixture
def git_service_with_remote(temp_git_repo: Path) -> GitService:
    """GitService instance with remote configured."""
    service = GitService(temp_git_repo)

    # Add a fake remote (for testing remote operations)
    service.add_remote("origin", "https://github.com/test/repo.git")

    return service


@pytest.fixture
def git_service_with_conflicts(temp_dir: Path) -> GitService:
    """GitService instance with merge conflicts setup."""
    # Create two repos to simulate conflicts
    repo1_path = temp_dir / "repo1"
    repo2_path = temp_dir / "repo2"

    # Initialize first repo
    repo1 = Repo.init(repo1_path)
    repo1.git.config("user.name", "Test User")
    repo1.git.config("user.email", "test@example.com")

    # Create initial file and commit
    shared_file = repo1_path / "shared.txt"
    shared_file.write_text("Original content")
    repo1.index.add(["shared.txt"])
    repo1.index.commit("Initial commit")

    # Clone second repo
    repo2 = Repo.clone_from(repo1_path, repo2_path)
    repo2.git.config("user.name", "Test User")
    repo2.git.config("user.email", "test@example.com")

    # Modify file in repo1
    shared_file.write_text("Repo1 modification")
    repo1.index.add(["shared.txt"])
    repo1.index.commit("Repo1 change")

    # Modify same file in repo2
    shared_file2 = repo2_path / "shared.txt"
    shared_file2.write_text("Repo2 modification")
    repo2.index.add(["shared.txt"])
    repo2.index.commit("Repo2 change")

    # Return service for repo2 (will have conflicts when pulling)
    return GitService(repo2_path)


@pytest.fixture
def empty_git_service(temp_dir: Path) -> GitService:
    """GitService instance for empty directory (no git repo)."""
    empty_path = temp_dir / "empty"
    empty_path.mkdir()
    return GitService(empty_path)


@pytest.fixture
def git_service_with_staged_changes(temp_git_repo: Path) -> GitService:
    """GitService instance with staged changes."""
    service = GitService(temp_git_repo)

    # Create and stage files without committing
    staged_file = temp_git_repo / "staged.txt"
    staged_file.write_text("This is staged content.")
    service.stage_files(["staged.txt"])

    # Create unstaged changes
    unstaged_file = temp_git_repo / "unstaged.txt"
    unstaged_file.write_text("Original content")
    service.stage_files(["unstaged.txt"])
    service.commit("Add unstaged file")

    # Modify without staging
    unstaged_file.write_text("Modified content")

    return service


@pytest.fixture
def git_service_with_deleted_files(temp_git_repo: Path) -> GitService:
    """GitService instance with deleted files."""
    service = GitService(temp_git_repo)

    # Create file and commit
    test_file = temp_git_repo / "to_delete.txt"
    test_file.write_text("This will be deleted.")
    service.stage_files(["to_delete.txt"])
    service.commit("Add file to delete")

    # Delete file
    service.delete_file("to_delete.txt", stage=True)

    return service


@pytest.fixture
def git_service_with_renamed_files(temp_git_repo: Path) -> GitService:
    """GitService instance with renamed files."""
    service = GitService(temp_git_repo)

    # Create file and commit
    old_file = temp_git_repo / "old_name.txt"
    old_file.write_text("This file will be renamed.")
    service.stage_files(["old_name.txt"])
    service.commit("Add file to rename")

    # Rename file
    service.rename_file("old_name.txt", "new_name.txt", stage=True)

    return service


@pytest.fixture
def git_service_with_task_commits(temp_git_repo: Path) -> GitService:
    """GitService instance with commits containing task references."""
    service = GitService(temp_git_repo)

    # Commit with task references
    task_file = temp_git_repo / "task_feature.py"
    task_file.write_text("def feature():\n    pass")
    service.stage_files(["task_feature.py"])
    service.commit("feat: Implement TAS-001 feature")

    # Commit with closing keyword
    fix_file = temp_git_repo / "bug_fix.py"
    fix_file.write_text("def fix():\n    pass")
    service.stage_files(["bug_fix.py"])
    service.commit("fix: Closes TAS-002 bug fix")

    # Commit with multiple task references
    update_file = temp_git_repo / "update.py"
    update_file.write_text("def update():\n    pass")
    service.stage_files(["update.py"])
    service.commit("chore: Update TAS-003, TAS-004, and fixes #123")

    return service
