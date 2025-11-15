"""
User response schemas.

Pydantic models for user data in API responses.
Never includes sensitive data like password_hash.
"""

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr


class UserResponse(BaseModel):
    """
    Schema for user data in API responses.

    Excludes sensitive data like password_hash.
    Uses ConfigDict(from_attributes=True) for SQLAlchemy model conversion.

    Attributes:
        id: User's UUID
        email: User's email address
        username: User's username
        full_name: User's full name (optional)
        is_active: Whether the account is active
        avatar_url: URL to profile picture (optional)
        created_at: When the account was created
        last_login_at: Last successful login timestamp (optional)
    """

    id: UUID
    email: EmailStr
    username: str
    full_name: str | None
    is_active: bool
    avatar_url: str | None
    created_at: datetime
    last_login_at: datetime | None

    model_config = ConfigDict(from_attributes=True)


class UserListResponse(BaseModel):
    """
    Schema for paginated list of users.

    Used for endpoints that return multiple users.

    Attributes:
        users: List of user objects
        total: Total number of users (for pagination)
    """

    users: list[UserResponse]
    total: int
