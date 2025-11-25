"""
GitHub-specific exceptions for the Ardha application.

This module defines exception classes for GitHub API operations including:
- Authentication errors
- Rate limiting
- Repository access
- Pull request operations
- Webhook operations
"""

from datetime import datetime
from typing import Dict, Optional


class GitHubError(Exception):
    """Base exception for all GitHub-related errors."""

    def __init__(self, message: str, details: Optional[Dict] = None):
        """
        Initialize GitHub error.

        Args:
            message: Error message
            details: Optional error details
        """
        super().__init__(message)
        self.message = message
        self.details = details or {}


class GitHubAuthenticationError(GitHubError):
    """
    Exception raised when GitHub authentication fails.

    This includes invalid tokens, expired tokens, or insufficient scopes.
    """

    def __init__(self, message: str, status_code: Optional[int] = None):
        """
        Initialize authentication error.

        Args:
            message: Error message
            status_code: HTTP status code (401, 403, etc.)
        """
        super().__init__(message)
        self.status_code = status_code


class GitHubRateLimitError(GitHubError):
    """
    Exception raised when GitHub API rate limit is exceeded.

    Includes information about when the rate limit resets.
    """

    def __init__(self, message: str, reset_at: Optional[datetime] = None):
        """
        Initialize rate limit error.

        Args:
            message: Error message
            reset_at: When rate limit resets (UTC)
        """
        super().__init__(message)
        self.reset_at = reset_at


class GitHubRepositoryNotFoundError(GitHubError):
    """
    Exception raised when a repository does not exist or is not accessible.

    This may indicate:
    - Repository doesn't exist
    - User doesn't have permission to access it
    - Repository was deleted
    """

    def __init__(self, message: str, owner: Optional[str] = None, repo: Optional[str] = None):
        """
        Initialize repository not found error.

        Args:
            message: Error message
            owner: Repository owner
            repo: Repository name
        """
        super().__init__(message)
        self.owner = owner
        self.repo = repo


class GitHubPullRequestError(GitHubError):
    """
    Exception raised when a pull request operation fails.

    This includes:
    - PR not found
    - PR not mergeable
    - Invalid PR state transitions
    - Review failures
    """

    def __init__(
        self,
        message: str,
        pr_number: Optional[int] = None,
        operation: Optional[str] = None,
    ):
        """
        Initialize pull request error.

        Args:
            message: Error message
            pr_number: PR number (if applicable)
            operation: Operation that failed (create, merge, update, etc.)
        """
        super().__init__(message)
        self.pr_number = pr_number
        self.operation = operation


class GitHubWebhookError(GitHubError):
    """
    Exception raised when a webhook operation fails.

    This includes:
    - Webhook creation failed
    - Invalid webhook signature
    - Webhook processing failed
    """

    def __init__(
        self,
        message: str,
        webhook_id: Optional[int] = None,
        operation: Optional[str] = None,
    ):
        """
        Initialize webhook error.

        Args:
            message: Error message
            webhook_id: Webhook ID (if applicable)
            operation: Operation that failed (create, update, delete, etc.)
        """
        super().__init__(message)
        self.webhook_id = webhook_id
        self.operation = operation


class GitHubPermissionError(GitHubError):
    """
    Exception raised when user has insufficient permissions.

    This includes:
    - Read-only access when write is needed
    - Missing admin permissions
    - Insufficient OAuth scopes
    """

    def __init__(
        self,
        message: str,
        required_scope: Optional[str] = None,
        current_scopes: Optional[list[str]] = None,
    ):
        """
        Initialize permission error.

        Args:
            message: Error message
            required_scope: Scope needed for operation
            current_scopes: Scopes currently available
        """
        super().__init__(message)
        self.required_scope = required_scope
        self.current_scopes = current_scopes or []


class GitHubAPIError(GitHubError):
    """
    Generic GitHub API error for uncategorized errors.

    Includes full response data for debugging.
    """

    def __init__(
        self,
        message: str,
        status_code: Optional[int] = None,
        response: Optional[Dict] = None,
    ):
        """
        Initialize API error.

        Args:
            message: Error message
            status_code: HTTP status code
            response: Full API response data
        """
        super().__init__(message, details=response)
        self.status_code = status_code
        self.response = response or {}
