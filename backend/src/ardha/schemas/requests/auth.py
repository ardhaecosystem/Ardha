"""
Authentication request schemas.

Pydantic models for validating authentication-related requests including:
- User registration
- User login
- Password reset
"""

import re
from typing import Any

from pydantic import BaseModel, EmailStr, field_validator


class UserRegisterRequest(BaseModel):
    """
    Schema for user registration request.

    Validates:
    - Email format using EmailStr
    - Username: 3-50 chars, alphanumeric + underscore only
    - Password: min 8 chars, 1 uppercase, 1 lowercase, 1 number
    - Full name is required
    """

    email: EmailStr
    username: str
    full_name: str
    password: str

    @field_validator("username")
    @classmethod
    def validate_username(cls, v: str) -> str:
        """
        Validate username format.

        Rules:
        - 3-50 characters
        - Alphanumeric and underscore only
        - Cannot start with underscore

        Args:
            v: Username to validate

        Returns:
            str: Validated username

        Raises:
            ValueError: If username doesn't meet requirements
        """
        if len(v) < 3:
            raise ValueError("Username must be at least 3 characters long")

        if len(v) > 50:
            raise ValueError("Username must be at most 50 characters long")

        if not re.match(r"^[a-zA-Z0-9_]+$", v):
            raise ValueError("Username can only contain letters, numbers, and underscores")

        if v.startswith("_"):
            raise ValueError("Username cannot start with underscore")

        return v.lower()  # Normalize to lowercase

    @field_validator("password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        """
        Validate password strength.

        Rules:
        - Minimum 8 characters
        - At least 1 uppercase letter
        - At least 1 lowercase letter
        - At least 1 number

        Args:
            v: Password to validate

        Returns:
            str: Validated password

        Raises:
            ValueError: If password doesn't meet requirements
        """
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters long")

        if not re.search(r"[A-Z]", v):
            raise ValueError("Password must contain at least one uppercase letter")

        if not re.search(r"[a-z]", v):
            raise ValueError("Password must contain at least one lowercase letter")

        if not re.search(r"\d", v):
            raise ValueError("Password must contain at least one number")

        return v

    @field_validator("full_name")
    @classmethod
    def validate_full_name(cls, v: str) -> str:
        """
        Validate full name is not empty.

        Args:
            v: Full name to validate

        Returns:
            str: Validated full name

        Raises:
            ValueError: If full name is empty
        """
        if not v or not v.strip():
            raise ValueError("Full name cannot be empty")

        return v.strip()


class UserLoginRequest(BaseModel):
    """
    Schema for user login request.

    Simple email and password authentication.
    """

    email: EmailStr
    password: str


class PasswordResetRequest(BaseModel):
    """
    Schema for password reset request.

    User provides their email to receive a reset token.
    """

    email: EmailStr


class PasswordResetConfirm(BaseModel):
    """
    Schema for password reset confirmation.

    User provides reset token and new password.
    """

    token: str
    new_password: str

    @field_validator("token")
    @classmethod
    def validate_token(cls, v: str) -> str:
        """
        Validate reset token is not empty.

        Args:
            v: Token to validate

        Returns:
            str: Validated token

        Raises:
            ValueError: If token is empty
        """
        if not v or not v.strip():
            raise ValueError("Reset token cannot be empty")

        return v.strip()

    @field_validator("new_password")
    @classmethod
    def validate_new_password(cls, v: str) -> str:
        """
        Validate new password strength (same rules as registration).

        Rules:
        - Minimum 8 characters
        - At least 1 uppercase letter
        - At least 1 lowercase letter
        - At least 1 number

        Args:
            v: Password to validate

        Returns:
            str: Validated password

        Raises:
            ValueError: If password doesn't meet requirements
        """
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters long")

        if not re.search(r"[A-Z]", v):
            raise ValueError("Password must contain at least one uppercase letter")

        if not re.search(r"[a-z]", v):
            raise ValueError("Password must contain at least one lowercase letter")

        if not re.search(r"\d", v):
            raise ValueError("Password must contain at least one number")

        return v
