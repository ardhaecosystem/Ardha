"""
Custom exceptions for the Ardha application.

This module defines custom exception classes for different
types of errors that can occur in the application.
"""

from typing import Any, List, Optional


class ArdhaException(Exception):
    """Base exception for all Ardha application errors."""

    def __init__(self, message: str, details: Optional[dict] = None):
        """
        Initialize base exception.

        Args:
            message: Error message
            details: Optional error details
        """
        super().__init__(message)
        self.message = message
        self.details = details or {}


class RepositoryError(ArdhaException):
    """Exception raised for repository-related errors."""

    def __init__(
        self, message: str, operation: Optional[str] = None, details: Optional[dict] = None
    ):
        """
        Initialize repository exception.

        Args:
            message: Error message
            operation: Optional operation that failed
            details: Optional error details
        """
        super().__init__(message, details)
        self.operation = operation


class ServiceError(ArdhaException):
    """Exception raised for service layer errors."""

    def __init__(self, message: str, service: Optional[str] = None, details: Optional[dict] = None):
        """
        Initialize service exception.

        Args:
            message: Error message
            service: Optional service name
            details: Optional error details
        """
        super().__init__(message, details)
        self.service = service


class ValidationError(ArdhaException):
    """Exception raised for validation errors."""

    def __init__(self, message: str, field: Optional[str] = None, value: Any = None):
        """
        Initialize validation exception.

        Args:
            message: Error message
            field: Optional field that failed validation
            value: Optional value that failed validation
        """
        super().__init__(message)
        self.field = field
        self.value = value


class AuthenticationError(ArdhaException):
    """Exception raised for authentication errors."""

    pass


class AuthorizationError(ArdhaException):
    """Exception raised for authorization errors."""

    pass


class NotFoundError(ArdhaException):
    """Exception raised when a resource is not found."""

    def __init__(
        self,
        message: str,
        resource_type: Optional[str] = None,
        resource_id: Optional[str] = None,
    ):
        """
        Initialize not found exception.

        Args:
            message: Error message
            resource_type: Optional type of resource
            resource_id: Optional ID of resource
        """
        super().__init__(message)
        self.resource_type = resource_type
        self.resource_id = resource_id


class ConflictError(ArdhaException):
    """Exception raised when a conflict occurs."""

    pass


class RateLimitError(ArdhaException):
    """Exception raised when rate limit is exceeded."""

    def __init__(self, message: str, limit: Optional[int] = None, window: Optional[int] = None):
        """
        Initialize rate limit exception.

        Args:
            message: Error message
            limit: Optional rate limit
            window: Optional time window
        """
        super().__init__(message)
        self.limit = limit
        self.window = window


class ExternalServiceError(ArdhaException):
    """Exception raised for external service errors."""

    def __init__(
        self,
        message: str,
        service: Optional[str] = None,
        status_code: Optional[int] = None,
    ):
        """
        Initialize external service exception.

        Args:
            message: Error message
            service: Optional external service name
            status_code: Optional HTTP status code
        """
        super().__init__(message)
        self.service = service
        self.status_code = status_code


# ============= OpenSpec Exceptions =============


class OpenSpecParseError(ArdhaException):
    """
    Exception raised when OpenSpec file parsing fails.

    This includes errors reading files, parsing markdown,
    or processing JSON content.
    """

    def __init__(
        self,
        message: str,
        file_path: Optional[str] = None,
        details: Optional[dict] = None,
    ):
        """
        Initialize OpenSpec parse exception.

        Args:
            message: Error message
            file_path: Optional path to file that failed to parse
            details: Optional error details
        """
        super().__init__(message, details)
        self.file_path = file_path


class OpenSpecValidationError(ArdhaException):
    """
    Exception raised when OpenSpec content validation fails.

    This includes missing required sections, invalid task formats,
    or structural issues in proposal content.
    """

    def __init__(
        self,
        message: str,
        validation_errors: Optional[List[str]] = None,
        details: Optional[dict] = None,
    ):
        """
        Initialize OpenSpec validation exception.

        Args:
            message: Error message
            validation_errors: List of specific validation errors
            details: Optional error details
        """
        super().__init__(message, details)
        self.validation_errors = validation_errors or []


class OpenSpecFileNotFoundError(ArdhaException):
    """
    Exception raised when required OpenSpec files are missing.

    This includes missing proposal directories or required markdown files.
    """

    def __init__(
        self,
        message: str,
        file_path: Optional[str] = None,
        missing_files: Optional[List[str]] = None,
    ):
        """
        Initialize OpenSpec file not found exception.

        Args:
            message: Error message
            file_path: Path that was not found
            missing_files: List of missing file names
        """
        super().__init__(message)
        self.file_path = file_path
        self.missing_files = missing_files or []
