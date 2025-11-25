"""
Authentication API routes.

This module provides RESTful endpoints for user authentication including:
- User registration
- Login with JWT tokens
- Token refresh
- Logout
- User profile management
"""

import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel, EmailStr
from sqlalchemy.ext.asyncio import AsyncSession

from ardha.core.database import get_db
from ardha.core.security import (
    create_access_token,
    create_refresh_token,
    get_current_active_user,
    verify_token,
)
from ardha.models.user import User
from ardha.repositories.user_repository import UserRepository
from ardha.schemas.requests.auth import UserRegisterRequest
from ardha.schemas.responses.user import UserResponse
from ardha.services.auth_service import AuthService, UserAlreadyExistsError

logger = logging.getLogger(__name__)

# Create router with prefix and tags
router = APIRouter(prefix="/auth", tags=["Authentication"])


# Request/Response schemas for specific endpoints
class TokenResponse(BaseModel):
    """Response schema for login endpoint."""

    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class RefreshTokenRequest(BaseModel):
    """Request schema for refresh token endpoint."""

    refresh_token: str


class RefreshTokenResponse(BaseModel):
    """Response schema for refresh token endpoint."""

    access_token: str
    token_type: str = "bearer"


class LogoutResponse(BaseModel):
    """Response schema for logout endpoint."""

    message: str


class UpdateProfileRequest(BaseModel):
    """Request schema for profile update endpoint."""

    full_name: str | None = None
    avatar_url: str | None = None


@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new user",
    description="Create a new user account with email, username, and password.",
)
async def register(
    user_data: UserRegisterRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> UserResponse:
    """
    Register a new user account.

    Creates a new user with the provided registration data. The password
    is automatically hashed using bcrypt before storage.

    Args:
        user_data: User registration data (email, username, password, full_name)
        db: Database session

    Returns:
        Created user data (excluding password)

    Raises:
        HTTPException 400: If email or username already exists

    Example:
        POST /api/v1/auth/register
        {
            "email": "user@example.com",
            "username": "john_doe",
            "full_name": "John Doe",
            "password": "SecurePass123"
        }
    """
    # Initialize service
    user_repository = UserRepository(db)
    auth_service = AuthService(user_repository)

    try:
        # Register user
        user = await auth_service.register_user(user_data)
        logger.info(f"New user registered: {user.email} (ID: {user.id})")

        return UserResponse.model_validate(user)

    except UserAlreadyExistsError as e:
        logger.warning(f"Registration failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.post(
    "/login",
    response_model=TokenResponse,
    summary="Login to get access tokens",
    description="Authenticate with email and password to receive JWT tokens.",
)
async def login(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> TokenResponse:
    """
    Authenticate user and return JWT tokens.

    Uses OAuth2PasswordRequestForm which expects 'username' and 'password'
    fields. For this API, the 'username' field should contain the user's email.

    Args:
        form_data: OAuth2 form with username (email) and password
        db: Database session

    Returns:
        Access token and refresh token

    Raises:
        HTTPException 401: If email or password is incorrect

    Example:
        POST /api/v1/auth/login
        Form data:
            username: user@example.com (email)
            password: SecurePass123
    """
    # Initialize service
    user_repository = UserRepository(db)
    auth_service = AuthService(user_repository)

    # Authenticate user (username field contains email)
    user = await auth_service.authenticate_user(
        email=form_data.username,
        password=form_data.password,
    )

    if not user:
        # Return generic error (don't reveal if email exists)
        logger.warning(f"Failed login attempt for: {form_data.username}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Create access token
    access_token_data = {
        "sub": str(user.id),
        "email": user.email,
    }
    access_token = create_access_token(access_token_data)

    # Create refresh token
    refresh_token_data = {
        "sub": str(user.id),
    }
    refresh_token = create_refresh_token(refresh_token_data)

    logger.info(f"User logged in: {user.email} (ID: {user.id})")

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
    )


@router.post(
    "/refresh",
    response_model=RefreshTokenResponse,
    summary="Refresh access token",
    description="Use a refresh token to obtain a new access token.",
)
async def refresh_token(
    token_request: RefreshTokenRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> RefreshTokenResponse:
    """
    Refresh an access token using a refresh token.

    Validates the refresh token and issues a new access token if valid.
    The refresh token itself is not renewed.

    Args:
        token_request: Refresh token request with refresh_token
        db: Database session

    Returns:
        New access token

    Raises:
        HTTPException 401: If refresh token is invalid or expired

    Example:
        POST /api/v1/auth/refresh
        {
            "refresh_token": "eyJhbGciOiJIUzI1NiIs..."
        }
    """
    # Verify refresh token
    payload = verify_token(token_request.refresh_token)

    if not payload:
        logger.warning("Invalid refresh token attempt")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Verify it's actually a refresh token
    if payload.get("type") != "refresh":
        logger.warning("Access token used as refresh token")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token type",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Get user ID from token
    user_id_str = payload.get("sub")
    if not user_id_str:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Verify user still exists and is active
    user_repository = UserRepository(db)
    try:
        from uuid import UUID

        user_id = UUID(user_id_str)
        user = await user_repository.get_by_id(user_id)
    except (ValueError, Exception):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user or not user.is_active:
        logger.warning(f"Refresh attempt for inactive/deleted user: {user_id_str}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User account is inactive",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Create new access token
    access_token_data = {
        "sub": str(user.id),
        "email": user.email,
    }
    access_token = create_access_token(access_token_data)

    logger.info(f"Access token refreshed for user: {user.email}")

    return RefreshTokenResponse(access_token=access_token)


@router.post(
    "/logout",
    response_model=LogoutResponse,
    summary="Logout current user",
    description="Logout the current user (token will expire naturally).",
)
async def logout(
    current_user: Annotated[User, Depends(get_current_active_user)],
) -> LogoutResponse:
    """
    Logout the current user.

    This is a stateless logout - the token will continue to be valid until
    it expires naturally (15 minutes for access tokens). For immediate
    invalidation, implement a token blacklist in Redis (future enhancement).

    Args:
        current_user: Current authenticated user

    Returns:
        Success message

    Example:
        POST /api/v1/auth/logout
        Headers:
            Authorization: Bearer <access_token>
    """
    logger.info(f"User logged out: {current_user.email} (ID: {current_user.id})")

    return LogoutResponse(message="Successfully logged out. Token will expire in 15 minutes.")


@router.get(
    "/me",
    response_model=UserResponse,
    summary="Get current user profile",
    description="Retrieve the profile of the currently authenticated user.",
)
async def get_current_user_profile(
    current_user: Annotated[User, Depends(get_current_active_user)],
) -> UserResponse:
    """
    Get the current user's profile.

    Returns the authenticated user's profile information based on the
    JWT token in the Authorization header.

    Args:
        current_user: Current authenticated user

    Returns:
        User profile data (excluding password)

    Example:
        GET /api/v1/auth/me
        Headers:
            Authorization: Bearer <access_token>
    """
    return UserResponse.model_validate(current_user)


@router.patch(
    "/me",
    response_model=UserResponse,
    summary="Update current user profile",
    description="Update allowed fields of the current user's profile.",
)
async def update_current_user_profile(
    profile_data: UpdateProfileRequest,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> UserResponse:
    """
    Update the current user's profile.

    Allows updating specific profile fields (full_name, avatar_url).
    Other fields like email and username require separate endpoints
    with additional verification.

    Args:
        profile_data: Fields to update (only non-None fields are updated)
        current_user: Current authenticated user
        db: Database session

    Returns:
        Updated user profile data

    Example:
        PATCH /api/v1/auth/me
        Headers:
            Authorization: Bearer <access_token>
        Body:
        {
            "full_name": "John Smith",
            "avatar_url": "https://example.com/avatar.jpg"
        }
    """
    # Initialize repository
    user_repository = UserRepository(db)

    # Build update dict (only include non-None fields)
    update_data = {}
    if profile_data.full_name is not None:
        update_data["full_name"] = profile_data.full_name
    if profile_data.avatar_url is not None:
        update_data["avatar_url"] = profile_data.avatar_url

    # Update user if there's data to update
    if update_data:
        updated_user = await user_repository.update(current_user.id, **update_data)
        if not updated_user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found",
            )
        logger.info(f"User profile updated: {updated_user.email} (ID: {updated_user.id})")
        return UserResponse.model_validate(updated_user)

    # No updates requested, return current user
    return UserResponse.model_validate(current_user)
