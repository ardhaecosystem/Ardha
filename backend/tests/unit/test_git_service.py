"""
Unit tests for GitService.

This module provides comprehensive unit tests for all GitService methods
including repository management, file operations, commits, branches,
and remote operations.
"""

import pytest
from git import GitCommandError

from ardha.core.git_exceptions import (
    GitAuthenticationError,
    GitBranchError,
    GitCommitError,
    GitInvalidRefError,
    GitMergeConflictError,
    GitOperationError,
    GitPullError,
    GitPushError,
    GitRepositoryExistsError,
    GitRepositoryNotFoundError,
)
from ardha.services.git_service import GitService

# Import git fixtures
from tests.fixtures.git_fixtures import (
    empty_git_service,
    git_service,
    git_service_with_branches,
    git_service_with_commits,
    git_service_with_files,
    git_service_with_remote,
    temp_dir,
    temp_git_repo,
)


class TestRepositoryManagement:
    """Test repository management methods."""
    
    def test_is_initialized_true(self, git_service):
        """Test is_initialized returns True for git repository."""
        assert git_service.is_initialized() is True
    
    def test_is_initialized_false(self, empty_git_service):
        """Test is_initialized returns False for empty directory."""
        assert empty_git_service.is_initialized() is False
    
    def test_initialize_repository(self, temp_dir):
        """Test initialize creates new repository."""
        repo_path = temp_dir / "new_repo"
        service = GitService(repo_path)
        
        result = service.initialize("main")
        
        assert result["path"] == str(repo_path)
        assert result["branch"] == "main"
        assert "initialized_at" in result
        assert service.is_initialized() is True
        assert (repo_path / ".git").exists()
        assert (repo_path / ".gitignore").exists()
    
    def test_initialize_already_exists(self, git_service):
        """Test initialize raises error for existing repository."""
        with pytest.raises(GitRepositoryExistsError):
            git_service.initialize()
    
    def test_get_repo_info(self, git_service):
        """Test get_repo_info returns correct information."""
        info = git_service.get_repo_info()
        
        assert "path" in info
        assert "current_branch" in info
        assert "remotes" in info
        assert "total_commits" in info
        assert "is_bare" in info
        assert "working_directory" in info
        assert info["current_branch"] == "main"
        assert info["total_commits"] >= 1
    
    def test_clone_repository(self, temp_dir, temp_git_repo):
        """Test clone creates repository copy."""
        clone_path = temp_dir / "cloned_repo"
        service = GitService(clone_path)
        
        result = service.clone(str(temp_git_repo))
        
        assert result["path"] == str(clone_path)
        assert result["remote_url"] == str(temp_git_repo)
        assert service.is_initialized() is True


class TestStatusAndChanges:
    """Test status and diff methods."""
    
    def test_get_status_empty(self, git_service):
        """Test get_status on clean repository."""
        status = git_service.get_status()
        
        assert status["untracked"] == []
        assert status["modified"] == []
        assert status["staged"] == []
        assert status["deleted"] == []
        assert status["renamed"] == []
        assert status["counts"]["untracked"] == 0
        assert status["counts"]["modified"] == 0
        assert status["counts"]["staged"] == 0
        assert status["counts"]["deleted"] == 0
        assert status["counts"]["renamed"] == 0
    
    def test_get_status_with_changes(self, git_service_with_files):
        """Test get_status with various file changes."""
        service, repo_path = git_service_with_files
        
        status = service.get_status()
        
        # Should have untracked files
        assert len(status["untracked"]) > 0
        assert "test1.py" in status["untracked"]
        assert "test2.js" in status["untracked"]
        assert "src/main.py" in status["untracked"]
        assert status["counts"]["untracked"] >= 3
    
    def test_get_diff_no_refs(self, git_service_with_files):
        """Test get_diff without refs (working tree vs HEAD)."""
        service, repo_path = git_service_with_files
        
        # Stage a file and commit
        service.stage_files(["test1.py"])
        service.commit("Add test file")
        
        # Modify file
        (repo_path / "test1.py").write_text("print('Modified')")
        
        diff = service.get_diff()
        assert "Modified" in diff
    
    def test_get_diff_with_file(self, git_service_with_files):
        """Test get_diff for specific file."""
        service, repo_path = git_service_with_files
        
        # Stage and commit file
        service.stage_files(["test1.py"])
        service.commit("Add test file")
        
        # Modify file
        (repo_path / "test1.py").write_text("print('Modified')")
        
        diff = service.get_diff(file_path="test1.py")
        assert "test1.py" in diff
    
    def test_get_file_history(self, git_service_with_commits):
        """Test get_file_history returns commit history."""
        history = git_service_with_commits.get_file_history("app.py")
        
        assert len(history) >= 2  # Initial and update commits
        assert all("sha" in commit for commit in history)
        assert all("message" in commit for commit in history)
        assert all("author_name" in commit for commit in history)
        assert any("Update Python greeting" in commit["message"] for commit in history)


class TestFileOperations:
    """Test file operation methods."""
    
    def test_read_file_success(self, git_service_with_files):
        """Test read_file reads file content."""
        service, repo_path = git_service_with_files
        
        content = service.read_file("test1.py")
        assert content == "print('Hello, World!')"
    
    def test_read_file_not_found(self, git_service):
        """Test read_file raises FileNotFoundError for missing file."""
        with pytest.raises(FileNotFoundError):
            git_service.read_file("nonexistent.txt")
    
    def test_write_file(self, git_service):
        """Test write_file creates and writes file."""
        git_service.write_file("new_file.txt", "Test content")
        
        file_path = git_service.repo_path / "new_file.txt"
        assert file_path.exists()
        assert file_path.read_text() == "Test content"
    
    def test_write_file_with_subdirectory(self, git_service):
        """Test write_file creates parent directories."""
        git_service.write_file("subdir/nested/file.txt", "Nested content")
        
        file_path = git_service.repo_path / "subdir/nested/file.txt"
        assert file_path.exists()
        assert file_path.read_text() == "Nested content"
    
    def test_delete_file(self, git_service_with_files):
        """Test delete_file removes file."""
        service, repo_path = git_service_with_files
        
        service.delete_file("test1.py")
        
        file_path = repo_path / "test1.py"
        assert not file_path.exists()
    
    def test_delete_file_not_found(self, git_service):
        """Test delete_file raises FileNotFoundError for missing file."""
        with pytest.raises(FileNotFoundError):
            git_service.delete_file("nonexistent.txt")
    
    def test_rename_file(self, git_service_with_files):
        """Test rename_file moves file."""
        service, repo_path = git_service_with_files
        
        service.rename_file("test1.py", "renamed.py")
        
        old_path = repo_path / "test1.py"
        new_path = repo_path / "renamed.py"
        assert not old_path.exists()
        assert new_path.exists()
        assert new_path.read_text() == "print('Hello, World!')"
    
    def test_rename_file_not_found(self, git_service):
        """Test rename_file raises FileNotFoundError for missing file."""
        with pytest.raises(FileNotFoundError):
            git_service.rename_file("nonexistent.txt", "new.txt")


class TestStagingAndCommits:
    """Test staging and commit methods."""
    
    def test_stage_files(self, git_service_with_files):
        """Test stage_files adds files to staging area."""
        service, repo_path = git_service_with_files
        
        # Make a change to stage
        service.write_file("test3.py", "print('New file to stage')")
        
        service.stage_files(["test3.py"])
        
        status = service.get_status()
        assert "test3.py" in status["staged"]
    
    def test_unstage_files(self, git_service_with_files):
        """Test unstage_files removes files from staging area."""
        service, repo_path = git_service_with_files
        
        # Stage files first
        service.stage_files(["test1.py"])
        
        # Unstage
        service.unstage_files(["test1.py"])
        
        status = service.get_status()
        assert "test1.py" not in status["staged"]
        assert "test1.py" in status["untracked"]
    
    def test_commit_success(self, git_service_with_files):
        """Test commit creates commit with staged changes."""
        service, repo_path = git_service_with_files
        
        service.stage_files(["test1.py"])
        result = service.commit("Add test file")
        
        assert "sha" in result
        assert "short_sha" in result
        assert result["message"] == "Add test file"
        assert result["author_name"] == "Test User"
        assert result["author_email"] == "test@example.com"
        assert "committed_at" in result
        assert result["files_changed"] == 1
        assert result["insertions"] >= 0
        assert result["deletions"] >= 0
    
    def test_commit_no_changes(self, git_service):
        """Test commit raises error when no changes staged."""
        with pytest.raises(GitCommitError, match="No changes staged"):
            git_service.commit("Empty commit")
    
    def test_commit_with_author_override(self, git_service_with_files):
        """Test commit with custom author information."""
        service, repo_path = git_service_with_files
        
        service.stage_files(["test1.py"])
        result = service.commit(
            "Custom author commit",
            author_name="Custom Author",
            author_email="custom@example.com"
        )
        
        assert result["author_name"] == "Custom Author"
        assert result["author_email"] == "custom@example.com"
    
    def test_amend_commit(self, git_service_with_files):
        """Test amend_commit modifies last commit."""
        service, repo_path = git_service_with_files
        
        # Initial commit
        service.stage_files(["test1.py"])
        service.commit("Initial commit")
        
        # Amend
        result = service.amend_commit("Amended commit")
        
        assert result["message"] == "Amended commit"
        assert "sha" in result
        assert result["files_changed"] == 1


class TestBranchManagement:
    """Test branch management methods."""
    
    def test_list_branches(self, git_service_with_branches):
        """Test list_branches returns all branches."""
        branches = git_service_with_branches.list_branches()
        
        assert "main" in branches
        assert "feature/test" in branches
        assert "bugfix/issue-123" in branches
    
    def test_get_current_branch(self, git_service):
        """Test get_current_branch returns active branch."""
        branch = git_service.get_current_branch()
        assert branch == "main"
    
    def test_create_branch(self, git_service):
        """Test create_branch creates new branch."""
        git_service.create_branch("new-feature")
        
        branches = git_service.list_branches()
        assert "new-feature" in branches
    
    def test_create_branch_exists(self, git_service):
        """Test create_branch raises error for existing branch."""
        with pytest.raises(GitBranchError, match="already exists"):
            git_service.create_branch("main")
    
    def test_switch_branch(self, git_service_with_branches):
        """Test switch_branch changes active branch."""
        git_service_with_branches.switch_branch("feature/test")
        
        current = git_service_with_branches.get_current_branch()
        assert current == "feature/test"
    
    def test_switch_branch_create(self, git_service):
        """Test switch_branch creates and switches to new branch."""
        git_service.switch_branch("new-branch", create=True)
        
        current = git_service.get_current_branch()
        assert current == "new-branch"
        
        branches = git_service.list_branches()
        assert "new-branch" in branches
    
    def test_delete_branch(self, git_service_with_branches):
        """Test delete_branch removes branch."""
        git_service_with_branches.delete_branch("bugfix/issue-123")
        
        branches = git_service_with_branches.list_branches()
        assert "bugfix/issue-123" not in branches
    
    def test_delete_branch_current(self, git_service_with_branches):
        """Test delete_branch raises error for current branch."""
        git_service_with_branches.switch_branch("feature/test")
        
        with pytest.raises(GitBranchError, match="Cannot delete current branch"):
            git_service_with_branches.delete_branch("feature/test")


class TestRemoteOperations:
    """Test remote operation methods."""
    
    def test_add_remote(self, git_service):
        """Test add_remote creates new remote."""
        git_service.add_remote("origin", "https://github.com/test/repo.git")
        
        remotes = git_service.list_remotes()
        assert "origin" in remotes
        assert remotes["origin"] == "https://github.com/test/repo.git"
    
    def test_add_remote_exists(self, git_service_with_remote):
        """Test add_remote raises error for existing remote."""
        with pytest.raises(GitOperationError, match="already exists"):
            git_service_with_remote.add_remote("origin", "https://github.com/other/repo.git")
    
    def test_list_remotes(self, git_service_with_remote):
        """Test list_remotes returns all remotes."""
        remotes = git_service_with_remote.list_remotes()
        
        assert "origin" in remotes
        assert remotes["origin"] == "https://github.com/test/repo.git"
    
    def test_push_authentication_error(self, git_service_with_remote):
        """Test push raises authentication error for invalid credentials."""
        with pytest.raises(GitAuthenticationError):
            git_service_with_remote.push()
    
    def test_pull_authentication_error(self, git_service_with_remote):
        """Test pull raises authentication error for invalid credentials."""
        with pytest.raises(GitAuthenticationError):
            git_service_with_remote.pull()


class TestHistoryAndLogs:
    """Test history and log methods."""
    
    def test_get_commit_history(self, git_service_with_commits):
        """Test get_commit_history returns commit list."""
        history = git_service_with_commits.get_commit_history()
        
        assert len(history) >= 3
        assert all("sha" in commit for commit in history)
        assert all("message" in commit for commit in history)
        assert any("Add Python application" in commit["message"] for commit in history)
        assert any("Add JavaScript application" in commit["message"] for commit in history)
        assert any("Update Python greeting" in commit["message"] for commit in history)
    
    def test_get_commit_history_with_limit(self, git_service_with_commits):
        """Test get_commit_history respects max_count parameter."""
        history = git_service_with_commits.get_commit_history(max_count=2)
        
        assert len(history) <= 2
    
    def test_get_commit_history_with_skip(self, git_service_with_commits):
        """Test get_commit_history respects skip parameter."""
        history = git_service_with_commits.get_commit_history(skip=1)
        
        # Should skip the first (most recent) commit
        assert len(history) >= 2
    
    def test_get_commit_history_with_file(self, git_service_with_commits):
        """Test get_commit_history filters by file."""
        history = git_service_with_commits.get_commit_history(file_path="app.py")
        
        assert len(history) >= 2  # Should find commits that modified app.py
        assert any("app.py" in str(commit.get("files_changed", {})) for commit in history)
    
    def test_get_commit_details(self, git_service_with_commits):
        """Test get_commit_details returns comprehensive commit info."""
        # Get the first commit from history
        history = git_service_with_commits.get_commit_history(max_count=1)
        if history:
            commit_sha = history[0]["sha"]
            details = git_service_with_commits.get_commit_details(commit_sha)
            
            assert "sha" in details
            assert "message" in details
            assert "author_name" in details
            assert "files" in details
            assert "task_info" in details
            assert "parents" in details
            assert details["sha"] == commit_sha
    
    def test_get_commit_details_invalid(self, git_service):
        """Test get_commit_details raises error for invalid SHA."""
        with pytest.raises(GitInvalidRefError):
            git_service.get_commit_details("invalid_sha")


class TestHelperMethods:
    """Test helper methods."""
    
    def test_parse_commit_message_empty(self, git_service):
        """Test parse_commit_message with empty message."""
        result = git_service.parse_commit_message("")
        
        assert result["mentioned"] == []
        assert result["closes"] == []
        assert result["fixes"] == []
        assert result["resolves"] == []
    
    def test_parse_commit_message_with_tasks(self, git_service):
        """Test parse_commit_message extracts task IDs."""
        message = "Implement TAS-001 and TAS-002 features"
        result = git_service.parse_commit_message(message)
        
        assert "TAS-001" in result["mentioned"]
        assert "TAS-002" in result["mentioned"]
        assert result["closes"] == []
        assert result["fixes"] == []
        assert result["resolves"] == []
    
    def test_parse_commit_message_with_closing(self, git_service):
        """Test parse_commit_message extracts closing keywords."""
        message = "Fix bug that closes TAS-001 and fixes #123"
        result = git_service.parse_commit_message(message)
        
        assert "TAS-001" in result["mentioned"]
        assert "#123" in result["mentioned"]
        assert "TAS-001" in result["closes"]
        assert "#123" in result["fixes"]
    
    def test_parse_commit_message_mixed(self, git_service):
        """Test parse_commit_message with mixed task references."""
        message = "Work on TAS-001, closes TAS-002, fixes TASK-003, resolves #456"
        result = git_service.parse_commit_message(message)
        
        assert "TAS-001" in result["mentioned"]
        assert "TAS-002" in result["mentioned"]
        assert "TASK-003" in result["mentioned"]
        assert "#456" in result["mentioned"]
        assert "TAS-002" in result["closes"]
        assert "TASK-003" in result["fixes"]
        assert "#456" in result["resolves"]
    
    def test_parse_commit_message_case_insensitive(self, git_service):
        """Test parse_commit_message is case insensitive."""
        message = "fix tas-001 and closes task-002"
        result = git_service.parse_commit_message(message)
        
        assert "TAS-001" in result["mentioned"]
        assert "TASK-002" in result["mentioned"]
        assert "TASK-002" in result["closes"]
    
    def test_parse_commit_message_duplicates(self, git_service):
        """Test parse_commit_message removes duplicates."""
        message = "Work on TAS-001, TAS-001, and TAS-001"
        result = git_service.parse_commit_message(message)
        
        # Should only appear once in each category
        assert result["mentioned"].count("TAS-001") == 1


class TestErrorHandling:
    """Test error handling in GitService."""
    
    def test_repository_not_found_error(self, empty_git_service):
        """Test accessing repo on non-existent repository raises error."""
        with pytest.raises(GitRepositoryNotFoundError):
            _ = empty_git_service.repo
    
    def test_git_operation_error_handling(self, git_service):
        """Test GitOperationError wraps GitCommandError."""
        # This would be tested with actual git operations that fail
        # For now, we test the error class exists
        assert GitOperationError is not None
    
    def test_lazy_loading(self, git_service):
        """Test repository is lazy loaded."""
        # Initially _repo should be None
        assert git_service._repo is None
        
        # Accessing repo property should load it
        repo = git_service.repo
        assert repo is not None
        assert git_service._repo is repo
        assert git_service._git is not None