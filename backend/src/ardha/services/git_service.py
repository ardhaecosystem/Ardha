"""
Git service for repository operations using GitPython.

This module provides a comprehensive service layer for git operations
including repository management, file operations, commits, branches,
and remote operations with proper error handling and async compatibility.
"""

import logging
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional
from uuid import UUID

from git import Git, GitCommandError, Repo
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

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

logger = logging.getLogger(__name__)


class GitService:
    """
    Service for git operations using GitPython.
    Provides async-compatible interface for repository management.
    """

    def __init__(self, repo_path: Path):
        """
        Initialize GitService with repository path.

        Args:
            repo_path: Path to git repository root
        """
        self.repo_path = Path(repo_path)
        self._repo: Optional[Repo] = None
        self._git: Optional[Git] = None

    @property
    def repo(self) -> Repo:
        """Lazy-load git repository."""
        if self._repo is None:
            if not self.is_initialized():
                raise GitRepositoryNotFoundError(f"Git repository not found at {self.repo_path}")
            self._repo = Repo(self.repo_path)
            self._git = self._repo.git
        return self._repo

    # ============= Repository Management =============

    def is_initialized(self) -> bool:
        """
        Check if git repository exists.

        Returns:
            True if .git directory exists, False otherwise
        """
        git_dir = self.repo_path / ".git"
        return git_dir.exists() and git_dir.is_dir()

    def initialize(self, initial_branch: str = "main") -> Dict:
        """
        Initialize new git repository.

        Args:
            initial_branch: Name of initial branch (default: "main")

        Returns:
            Dictionary with repository info

        Raises:
            GitRepositoryExistsError: If repository already exists
        """
        if self.is_initialized():
            raise GitRepositoryExistsError(f"Git repository already exists at {self.repo_path}")

        try:
            # Create repository
            self._repo = Repo.init(self.repo_path, initial_branch=initial_branch)
            self._git = self._repo.git

            # Create .gitignore if not exists
            gitignore_path = self.repo_path / ".gitignore"
            if not gitignore_path.exists():
                gitignore_path.write_text(
                    "# Python\n__pycache__/\n*.py[cod]\n*$py.class\n"
                    "# Virtual environments\n.venv/\nvenv/\n"
                    "# IDE\n.vscode/\n.idea/\n"
                    "# OS\n.DS_Store\nThumbs.db\n"
                )
                self._repo.index.add([".gitignore"])
                self._repo.index.commit("Initial commit: Add .gitignore")

            return {
                "path": str(self.repo_path),
                "branch": initial_branch,
                "initialized_at": datetime.now(timezone.utc).isoformat(),
            }

        except GitCommandError as e:
            logger.error(f"Failed to initialize repository: {e}")
            raise GitOperationError(f"Failed to initialize repository: {e}", git_error=e)

    def clone(self, remote_url: str, branch: Optional[str] = None) -> Dict:
        """
        Clone repository from remote.

        Args:
            remote_url: URL of remote repository
            branch: Optional branch to clone

        Returns:
            Dictionary with clone info

        Raises:
            GitOperationError: If clone fails
        """
        try:
            if branch:
                self._repo = Repo.clone_from(remote_url, self.repo_path, branch=branch)
            else:
                self._repo = Repo.clone_from(remote_url, self.repo_path)

            self._git = self._repo.git

            return {
                "path": str(self.repo_path),
                "remote_url": remote_url,
                "branch": branch or self._repo.active_branch.name,
                "cloned_at": datetime.now(timezone.utc).isoformat(),
            }

        except GitCommandError as e:
            logger.error(f"Failed to clone repository: {e}")
            raise GitOperationError(f"Failed to clone repository: {e}", git_error=e)

    def get_repo_info(self) -> Dict:
        """
        Return repository information.

        Returns:
            Dictionary with repository details
        """
        try:
            current_branch = self.get_current_branch()

            # Get remote URLs
            remotes = {}
            for remote in self.repo.remotes:
                remotes[remote.name] = list(remote.urls)[0] if remote.urls else None

            # Count commits
            commit_count = len(list(self.repo.iter_commits()))

            return {
                "path": str(self.repo_path),
                "current_branch": current_branch,
                "remotes": remotes,
                "total_commits": commit_count,
                "is_bare": self.repo.bare,
                "working_directory": str(self.repo.working_dir),
            }

        except Exception as e:
            logger.error(f"Failed to get repository info: {e}")
            raise GitOperationError(f"Failed to get repository info: {e}", git_error=e)

    # ============= Status & Changes =============

    def get_status(self) -> Dict:
        """
        Get repository status.

        Returns:
            Dictionary with status information
        """
        try:
            # Ensure git is available
            if self._git is None:
                self._git = self.repo.git

            # Get status using git command
            status_output = self._git.status("--porcelain=v1", "-z").strip()

            if not status_output:
                return {
                    "untracked": [],
                    "modified": [],
                    "staged": [],
                    "deleted": [],
                    "renamed": [],
                    "counts": {
                        "untracked": 0,
                        "modified": 0,
                        "staged": 0,
                        "deleted": 0,
                        "renamed": 0,
                    },
                }

            # Parse status output
            untracked = []
            modified = []
            staged = []
            deleted = []
            renamed = []

            for line in status_output.split("\x00") if status_output else []:
                if not line:
                    continue

                status_code = line[:2]
                file_path = line[3:]

                if status_code == "??":
                    untracked.append(file_path)
                elif status_code[0] in ["M", "A", "D", "R"]:
                    staged.append(file_path)
                elif status_code[1] in ["M", "D"]:
                    modified.append(file_path)
                elif status_code.startswith("R"):
                    # Renamed files have format: R100 -> old_path\x00new_path
                    parts = file_path.split("\x00")
                    if len(parts) == 2:
                        renamed.append((parts[0], parts[1]))

            return {
                "untracked": untracked,
                "modified": modified,
                "staged": staged,
                "deleted": deleted,
                "renamed": renamed,
                "counts": {
                    "untracked": len(untracked),
                    "modified": len(modified),
                    "staged": len(staged),
                    "deleted": len(deleted),
                    "renamed": len(renamed),
                },
            }

        except GitCommandError as e:
            logger.error(f"Failed to get repository status: {e}")
            raise GitOperationError(f"Failed to get repository status: {e}", git_error=e)

    def get_diff(
        self,
        ref1: Optional[str] = None,
        ref2: Optional[str] = None,
        file_path: Optional[str] = None,
    ) -> str:
        """
        Get diff between refs or working tree.

        Args:
            ref1: First reference (commit, branch)
            ref2: Second reference (commit, branch)
            file_path: Optional file path for specific file diff

        Returns:
            Unified diff format string
        """
        try:
            # Ensure git is available
            if self._git is None:
                self._git = self.repo.git

            args = []

            if ref1 and ref2:
                args.extend([f"{ref1}..{ref2}"])
            elif ref1:
                args.append(ref1)

            if file_path:
                args.extend(["--", file_path])

            # Get diff
            diff_output = self._git.diff(*args, unified=True)

            return diff_output

        except GitCommandError as e:
            logger.error(f"Failed to get diff: {e}")
            raise GitOperationError(f"Failed to get diff: {e}", git_error=e)

    def get_file_history(self, file_path: str, max_count: int = 50) -> List[Dict]:
        """
        Get commit history for specific file.

        Args:
            file_path: Path to file
            max_count: Maximum number of commits to return

        Returns:
            List of commit dictionaries
        """
        try:
            commits = []

            for commit in self.repo.iter_commits(paths=[file_path], max_count=max_count):
                commits.append(
                    {
                        "sha": commit.hexsha,
                        "short_sha": commit.hexsha[:7],
                        "message": commit.message.strip(),
                        "author_name": commit.author.name,
                        "author_email": commit.author.email,
                        "date": datetime.fromtimestamp(commit.committed_date).isoformat(),
                        "changes": commit.stats.files.get(file_path, {}),
                    }
                )

            return commits

        except Exception as e:
            logger.error(f"Failed to get file history: {e}")
            raise GitOperationError(f"Failed to get file history: {e}", git_error=e)

    # ============= File Operations =============

    def read_file(self, file_path: str, ref: str = "HEAD") -> str:
        """
        Read file content at specific ref.

        Args:
            file_path: Path to file
            ref: Git reference (default: HEAD)

        Returns:
            File content as string

        Raises:
            FileNotFoundError: If file doesn't exist
        """
        try:
            # Get file content from git
            blob = self.repo.git.show(f"{ref}:{file_path}")
            return blob

        except GitCommandError as e:
            if "does not exist" in str(e) or "invalid path" in str(e):
                raise FileNotFoundError(f"File not found: {file_path} at {ref}")
            logger.error(f"Failed to read file: {e}")
            raise GitOperationError(f"Failed to read file: {e}", git_error=e)

    def write_file(self, file_path: str, content: str, encoding: str = "utf-8") -> None:
        """
        Write content to file.

        Args:
            file_path: Path to file
            content: File content
            encoding: Text encoding
        """
        try:
            full_path = self.repo_path / file_path

            # Create parent directories if needed
            full_path.parent.mkdir(parents=True, exist_ok=True)

            # Write file
            full_path.write_text(content, encoding=encoding)

            # Stage file if in git repo
            if self.is_initialized():
                self.repo.index.add([file_path])

        except Exception as e:
            logger.error(f"Failed to write file: {e}")
            raise GitOperationError(f"Failed to write file: {e}", git_error=e)

    def delete_file(self, file_path: str, stage: bool = True) -> None:
        """
        Delete file from working directory.

        Args:
            file_path: Path to file
            stage: Whether to stage deletion

        Raises:
            FileNotFoundError: If file doesn't exist
        """
        try:
            full_path = self.repo_path / file_path

            if not full_path.exists():
                raise FileNotFoundError(f"File not found: {file_path}")

            # Delete file
            full_path.unlink()

            # Stage deletion if requested
            if stage and self.is_initialized():
                try:
                    self.repo.index.remove([file_path], working_tree=True, r=True)
                except GitCommandError:
                    # File might not be tracked, that's okay
                    pass

        except FileNotFoundError:
            # Re-raise FileNotFoundError as-is
            raise
        except Exception as e:
            logger.error(f"Failed to delete file: {e}")
            raise GitOperationError(f"Failed to delete file: {e}", git_error=e)

    def rename_file(self, old_path: str, new_path: str, stage: bool = True) -> None:
        """
        Rename/move file.

        Args:
            old_path: Current file path
            new_path: New file path
            stage: Whether to stage rename
        """
        try:
            old_full_path = self.repo_path / old_path
            new_full_path = self.repo_path / new_path

            if not old_full_path.exists():
                raise FileNotFoundError(f"File not found: {old_path}")

            # Create parent directories for new path
            new_full_path.parent.mkdir(parents=True, exist_ok=True)

            # Move file
            old_full_path.rename(new_full_path)

            # Stage rename if requested
            if stage and self.is_initialized():
                try:
                    self.repo.index.remove([old_path], working_tree=True, r=True)
                except GitCommandError:
                    # File might not be tracked, that's okay
                    pass
                self.repo.index.add([new_path])

        except FileNotFoundError:
            # Re-raise FileNotFoundError as-is
            raise
        except Exception as e:
            logger.error(f"Failed to rename file: {e}")
            raise GitOperationError(f"Failed to rename file: {e}", git_error=e)

    # ============= Staging & Commits =============

    def stage_files(self, file_paths: List[str]) -> None:
        """
        Add files to staging area.

        Args:
            file_paths: List of file paths or patterns
        """
        try:
            self.repo.index.add(file_paths)

        except GitCommandError as e:
            logger.error(f"Failed to stage files: {e}")
            raise GitOperationError(f"Failed to stage files: {e}", git_error=e)

    def unstage_files(self, file_paths: List[str]) -> None:
        """
        Remove files from staging area.

        Args:
            file_paths: List of file paths
        """
        try:
            self.repo.index.reset(paths=file_paths)

        except GitCommandError as e:
            logger.error(f"Failed to unstage files: {e}")
            raise GitOperationError(f"Failed to unstage files: {e}", git_error=e)

    def commit(
        self,
        message: str,
        author_name: Optional[str] = None,
        author_email: Optional[str] = None,
    ) -> Dict:
        """
        Create git commit with staged changes.

        Args:
            message: Commit message
            author_name: Optional author name override
            author_email: Optional author email override

        Returns:
            Dictionary with commit info

        Raises:
            GitCommitError: If no changes staged
        """
        try:
            # Check if there are staged changes
            if not self.repo.index.diff("HEAD"):
                raise GitCommitError("No changes staged for commit")

            # Configure author if provided
            if author_name and author_email:
                with self.repo.config_writer() as config:
                    config.set_value("user.name", author_name)
                    config.set_value("user.email", author_email)

            # Create commit
            commit = self.repo.index.commit(message)

            # Get commit stats
            stats = commit.stats

            return {
                "sha": commit.hexsha,
                "short_sha": commit.hexsha[:7],
                "message": message,
                "author_name": commit.author.name,
                "author_email": commit.author.email,
                "committed_at": datetime.fromtimestamp(commit.committed_date).isoformat(),
                "files_changed": stats.total["files"],
                "insertions": stats.total["insertions"],
                "deletions": stats.total["deletions"],
            }

        except GitCommitError:
            raise
        except GitCommandError as e:
            logger.error(f"Failed to create commit: {e}")
            raise GitCommitError(f"Failed to create commit: {e}", git_error=e)

    def amend_commit(self, message: Optional[str] = None) -> Dict:
        """
        Amend last commit.

        Args:
            message: Optional new commit message

        Returns:
            Dictionary with updated commit info
        """
        try:
            # Amend commit

            # Amend commit
            if message:
                self.repo.git.commit("--amend", "-m", message)
            else:
                self.repo.git.commit("--amend")

            # Get amended commit
            amended_commit = self.repo.head.commit

            return {
                "sha": amended_commit.hexsha,
                "short_sha": amended_commit.hexsha[:7],
                "message": amended_commit.message.strip(),
                "author_name": amended_commit.author.name,
                "author_email": amended_commit.author.email,
                "committed_at": datetime.fromtimestamp(amended_commit.committed_date).isoformat(),
                "files_changed": amended_commit.stats.total["files"],
                "insertions": amended_commit.stats.total["insertions"],
                "deletions": amended_commit.stats.total["deletions"],
            }

        except GitCommandError as e:
            logger.error(f"Failed to amend commit: {e}")
            raise GitCommitError(f"Failed to amend commit: {e}", git_error=e)

    # ============= Branch Management =============

    def list_branches(self, remote: bool = False) -> List[str]:
        """
        List all branches.

        Args:
            remote: Whether to list remote branches

        Returns:
            List of branch names
        """
        try:
            if remote:
                branches = [ref.name for ref in self.repo.remotes]
            else:
                branches = [branch.name for branch in self.repo.branches]

            return branches

        except GitCommandError as e:
            logger.error(f"Failed to list branches: {e}")
            raise GitBranchError(f"Failed to list branches: {e}", git_error=e)

    def get_current_branch(self) -> str:
        """
        Get active branch name.

        Returns:
            Current branch name
        """
        try:
            if self.repo.head.is_detached:
                return f"DETACHED:{self.repo.head.commit.hexsha[:7]}"
            return self.repo.active_branch.name

        except Exception as e:
            logger.error(f"Failed to get current branch: {e}")
            raise GitBranchError(f"Failed to get current branch: {e}", git_error=e)

    def create_branch(self, branch_name: str, start_point: Optional[str] = None) -> None:
        """
        Create new branch.

        Args:
            branch_name: Name of new branch
            start_point: Optional start point (commit, branch)

        Raises:
            GitBranchError: If branch already exists
        """
        try:
            # Check if branch already exists
            if branch_name in self.repo.branches:
                raise GitBranchError(f"Branch '{branch_name}' already exists")

            # Create branch
            if start_point:
                self.repo.create_head(branch_name, start_point)
            else:
                self.repo.create_head(branch_name)

        except GitBranchError:
            raise
        except GitCommandError as e:
            logger.error(f"Failed to create branch: {e}")
            raise GitBranchError(f"Failed to create branch: {e}", git_error=e)

    def switch_branch(self, branch_name: str, create: bool = False) -> None:
        """
        Switch to branch.

        Args:
            branch_name: Branch name to switch to
            create: Whether to create branch if doesn't exist

        Raises:
            GitBranchError: If operation fails
        """
        try:
            # Check for uncommitted changes
            if self.repo.is_dirty(untracked_files=True):
                raise GitBranchError("Working directory has uncommitted changes")

            # Switch branch
            if create:
                self.repo.git.checkout("-b", branch_name)
            else:
                self.repo.git.checkout(branch_name)

        except GitBranchError:
            raise
        except GitCommandError as e:
            logger.error(f"Failed to switch branch: {e}")
            raise GitBranchError(f"Failed to switch branch: {e}", git_error=e)

    def delete_branch(self, branch_name: str, force: bool = False) -> None:
        """
        Delete branch.

        Args:
            branch_name: Branch name to delete
            force: Whether to force delete even if not merged

        Raises:
            GitBranchError: If trying to delete current branch
        """
        try:
            # Check if trying to delete current branch
            if not self.repo.head.is_detached and self.repo.active_branch.name == branch_name:
                raise GitBranchError("Cannot delete current branch")

            # Delete branch
            if force:
                self.repo.git.branch("-D", branch_name)
            else:
                self.repo.git.branch("-d", branch_name)

        except GitBranchError:
            raise
        except GitCommandError as e:
            logger.error(f"Failed to delete branch: {e}")
            raise GitBranchError(f"Failed to delete branch: {e}", git_error=e)

    # ============= Remote Operations =============

    def add_remote(self, name: str, url: str) -> None:
        """
        Add remote repository.

        Args:
            name: Remote name
            url: Remote URL

        Raises:
            GitOperationError: If remote already exists
        """
        try:
            # Check if remote already exists
            if name in self.repo.remotes:
                raise GitOperationError(f"Remote '{name}' already exists")

            # Add remote
            self.repo.create_remote(name, url)

        except GitOperationError:
            raise
        except GitCommandError as e:
            logger.error(f"Failed to add remote: {e}")
            raise GitOperationError(f"Failed to add remote: {e}", git_error=e)

    def list_remotes(self) -> Dict[str, str]:
        """
        List all remotes.

        Returns:
            Dictionary of {name: url}
        """
        try:
            remotes = {}
            for remote in self.repo.remotes:
                remotes[remote.name] = list(remote.urls)[0] if remote.urls else None
            return remotes

        except Exception as e:
            logger.error(f"Failed to list remotes: {e}")
            raise GitOperationError(f"Failed to list remotes: {e}", git_error=e)

    def push(
        self,
        remote: str = "origin",
        branch: Optional[str] = None,
        force: bool = False,
    ) -> None:
        """
        Push commits to remote.

        Args:
            remote: Remote name
            branch: Branch to push (default: current)
            force: Whether to force push

        Raises:
            GitPushError: If push fails
        """
        try:
            if branch is None:
                branch = self.get_current_branch()

            # Push to remote
            if force:
                self.repo.git.push("--force", remote, branch)
            else:
                self.repo.git.push(remote, branch)

        except GitCommandError as e:
            logger.error(f"Failed to push: {e}")
            error_msg = str(e).lower()
            if any(keyword in error_msg for keyword in ["authentication", "credential", "username", "password", "could not read"]):
                raise GitAuthenticationError(f"Authentication failed for push: {e}")
            raise GitPushError(f"Failed to push: {e}")

    def pull(
        self,
        remote: str = "origin",
        branch: Optional[str] = None,
        rebase: bool = False,
    ) -> None:
        """
        Pull changes from remote.

        Args:
            remote: Remote name
            branch: Branch to pull
            rebase: Whether to rebase instead of merge

        Raises:
            GitPullError: If pull fails
            GitMergeConflictError: If merge conflicts occur
        """
        try:
            if branch is None:
                branch = self.get_current_branch()

            # Pull from remote
            if rebase:
                result = self.repo.git.pull(remote, branch, "--rebase")
            else:
                result = self.repo.git.pull(remote, branch)

            # Check for merge conflicts
            if "CONFLICT" in result:
                conflicted_files = []
                # Ensure git is available
                if self._git is None:
                    self._git = self.repo.git

                try:
                    conflicted_output = self._git.diff("--name-only", "--diff-filter=U")
                    if conflicted_output:
                        conflicted_files = conflicted_output.splitlines()
                except GitCommandError:
                    pass

                raise GitMergeConflictError(
                    "Pull resulted in merge conflicts",
                    conflicted_files=conflicted_files,
                )

        except GitMergeConflictError:
            raise
        except GitCommandError as e:
            logger.error(f"Failed to pull: {e}")
            error_msg = str(e).lower()
            if any(keyword in error_msg for keyword in ["authentication", "credential", "username", "password", "could not read"]):
                raise GitAuthenticationError(f"Authentication failed for pull: {e}")
            raise GitPullError(f"Failed to pull: {e}")

    # ============= History & Logs =============

    def get_commit_history(
        self,
        branch: Optional[str] = None,
        max_count: int = 50,
        skip: int = 0,
        file_path: Optional[str] = None,
    ) -> List[Dict]:
        """
        Get commit history.

        Args:
            branch: Optional branch (default: current)
            max_count: Maximum number of commits
            skip: Number of commits to skip
            file_path: Optional file filter

        Returns:
            List of commit dictionaries
        """
        try:
            commits = []

            # Determine revision range
            revision = branch or "HEAD"

            # Get commits
            if file_path:
                commit_iter = self.repo.iter_commits(
                    revision, max_count=max_count + skip, paths=[file_path]
                )
            else:
                commit_iter = self.repo.iter_commits(revision, max_count=max_count + skip)

            for i, commit in enumerate(commit_iter):
                if i < skip:
                    continue

                commits.append(
                    {
                        "sha": commit.hexsha,
                        "short_sha": commit.hexsha[:7],
                        "message": commit.message.strip(),
                        "author_name": commit.author.name,
                        "author_email": commit.author.email,
                        "committed_at": datetime.fromtimestamp(commit.committed_date).isoformat(),
                        "files_changed": commit.stats.total["files"],
                        "insertions": commit.stats.total["insertions"],
                        "deletions": commit.stats.total["deletions"],
                    }
                )

            return commits

        except Exception as e:
            logger.error(f"Failed to get commit history: {e}")
            raise GitOperationError(f"Failed to get commit history: {e}", git_error=e)

    def get_commit_details(self, sha: str) -> Dict:
        """
        Get detailed commit information.

        Args:
            sha: Commit SHA

        Returns:
            Comprehensive commit dictionary

        Raises:
            GitInvalidRefError: If commit doesn't exist
        """
        try:
            # Get commit
            commit = self.repo.commit(sha)

            # Get file changes
            files_changed = []
            for diff in commit.diff(commit.parents[0] if commit.parents else None):
                files_changed.append(
                    {
                        "path": diff.a_path if diff.a_path else diff.b_path,
                        "change_type": diff.change_type,
                        "insertions": diff.diff.count(b"+") if diff.diff else 0,
                        "deletions": diff.diff.count(b"-") if diff.diff else 0,
                    }
                )

            # Parse commit message for task IDs
            message = commit.message
            if isinstance(message, (bytes, bytearray, memoryview)):
                message = str(message, encoding="utf-8", errors="replace")
            task_info = self.parse_commit_message(message)

            return {
                "sha": commit.hexsha,
                "short_sha": commit.hexsha[:7],
                "message": commit.message.strip(),
                "author_name": commit.author.name,
                "author_email": commit.author.email,
                "committed_at": datetime.fromtimestamp(commit.committed_date).isoformat(),
                "files_changed": commit.stats.total["files"],
                "insertions": commit.stats.total["insertions"],
                "deletions": commit.stats.total["deletions"],
                "files": files_changed,
                "task_info": task_info,
                "parents": [p.hexsha for p in commit.parents],
            }

        except Exception as e:
            logger.error(f"Failed to get commit details: {e}")
            if "not found" in str(e).lower() or "invalid" in str(e).lower():
                raise GitInvalidRefError(f"Invalid commit reference: {sha}")
            raise GitOperationError(f"Failed to get commit details: {e}", git_error=e)

    # ============= Helper Methods =============

    def parse_commit_message(self, message: str) -> Dict[str, List[str]]:
        """
        Extract task IDs from commit message.

        Args:
            message: Commit message

        Returns:
            Dictionary with extracted task IDs
        """
        if not message:
            return {
                "mentioned": [],
                "closes": [],
                "fixes": [],
                "resolves": [],
            }

        # Patterns for task IDs
        task_pattern = r"(?:TAS|TASK|ARD)-\d+|#\d+"

        # Find all mentioned task IDs
        mentioned = re.findall(task_pattern, message, re.IGNORECASE)
        mentioned = [id.upper() for id in mentioned]

        # Find closing keywords
        closing_patterns = [
            (r"closes?\s+(" + task_pattern + r")", "closes"),
            (r"fixes?\s+(" + task_pattern + r")", "fixes"),
            (r"resolves?\s+(" + task_pattern + r")", "resolves"),
        ]

        closes = []
        fixes = []
        resolves = []

        for pattern, category in closing_patterns:
            matches = re.findall(pattern, message, re.IGNORECASE)
            for match in matches:
                task_id = match.upper() if isinstance(match, str) else match[0].upper()
                if category == "closes":
                    closes.append(task_id)
                elif category == "fixes":
                    fixes.append(task_id)
                elif category == "resolves":
                    resolves.append(task_id)

        return {
            "mentioned": list(set(mentioned)),
            "closes": list(set(closes)),
            "fixes": list(set(fixes)),
            "resolves": list(set(resolves)),
        }

    async def map_git_author_to_user(
        self,
        author_email: str,
        session: AsyncSession,
    ) -> Optional[UUID]:
        """
        Map git author email to Ardha user.

        Args:
            author_email: Git author email
            session: Database session

        Returns:
            User ID or None
        """
        try:
            # Query user by email

            # Query user by email
            result = await session.execute(
                text("SELECT id FROM users WHERE email = :email"), {"email": author_email}
            )
            user_row = result.fetchone()

            return UUID(user_row[0]) if user_row else None

        except Exception as e:
            logger.error(f"Failed to map git author to user: {e}")
            return None
