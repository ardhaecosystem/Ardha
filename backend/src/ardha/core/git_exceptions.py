"""
Custom exceptions for git operations.

This module defines comprehensive exception hierarchy for git-related errors
in the Ardha platform. All git operations should raise these exceptions
to provide consistent error handling and user feedback.
"""

from typing import List, Optional


class GitError(Exception):
    """Base exception for all git-related errors."""

    pass


class GitRepositoryNotFoundError(GitError):
    """Repository does not exist or is not initialized."""

    pass


class GitRepositoryExistsError(GitError):
    """Repository already exists at location."""

    pass


class GitOperationError(GitError):
    """Generic git operation failed."""

    def __init__(self, message: str, git_error: Optional[Exception] = None):
        self.git_error = git_error
        super().__init__(message)


class GitCommitError(GitOperationError):
    """Commit operation failed."""

    pass


class GitPushError(GitOperationError):
    """Push operation failed."""

    pass


class GitPullError(GitOperationError):
    """Pull operation failed."""

    pass


class GitBranchError(GitOperationError):
    """Branch operation failed."""

    pass


class GitMergeConflictError(GitError):
    """Merge resulted in conflicts."""

    def __init__(self, message: str, conflicted_files: List[str]):
        self.conflicted_files = conflicted_files
        super().__init__(message)


class GitAuthenticationError(GitError):
    """Authentication failed for remote operation."""

    pass


class GitInvalidRefError(GitError):
    """Invalid reference (branch, tag, commit)."""

    pass
