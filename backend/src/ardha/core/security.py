"""
JWT token utilities and authentication dependencies.

This module provides JWT token generation, validation, and FastAPI
dependencies for extracting and validating the current authenticated user
from request headers. Uses python-jose for JWT operations with HS256.
"""

import logging
from datetime import datetime, timedelta, timezone
from typing import Annotated
from uuid import UUID

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from sqlalchemy.ext.asyncio import AsyncSession

from ardha.core.config import settings
from ardha.core.database import get_db
from ardha.models.user import User
from ardha.repositories.user_repository import UserRepository

logger = logging.getLogger(__name__)

# OAuth2 scheme for token extraction from Authorization header
# tokenUrl points to the login endpoint that will issue tokens
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


def create_access_token(data: dict, expires_delta: timedelta | None = None) -> str:
    """
    Create a JWT access token with expiration.
    
    Access tokens are short-lived (default 15 minutes) and used for
    authenticating API requests. They contain user identification data.
    
    Args:
        data: Payload data to encode in the token (typically {"sub": user_id, "email": email})
        expires_delta: Optional custom expiration time (default: 15 minutes from settings)
        
    Returns:
        Encoded JWT token string
        
    Example:
        >>> token_data = {"sub": str(user.id), "email": user.email}
        >>> token = create_access_token(token_data)
        >>> print(token[:20])  # First 20 chars of the token
        'eyJhbGciOiJIUzI1NiIs...'
    """
    to_encode = data.copy()
    
    # Set expiration time
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(
            minutes=settings.security.jwt_access_token_expire_minutes
        )
    
    to_encode["exp"] = expire
    
    # Encode the JWT token
    encoded_jwt = jwt.encode(
        to_encode,
        settings.security.jwt_secret_key,
        algorithm=settings.security.jwt_algorithm,
    )
    
    logger.debug(f"Created access token for subject: {data.get('sub')}")
    return encoded_jwt


def create_refresh_token(data: dict) -> str:
    """
    Create a JWT refresh token with long expiration.
    
    Refresh tokens are long-lived (default 7 days) and used to obtain
    new access tokens without requiring the user to re-authenticate.
    
    Args:
        data: Payload data to encode (typically {"sub": user_id, "type": "refresh"})
        
    Returns:
        Encoded JWT refresh token string
        
    Example:
        >>> token_data = {"sub": str(user.id), "type": "refresh"}
        >>> refresh_token = create_refresh_token(token_data)
    """
    to_encode = data.copy()
    
    # Set expiration time (7 days by default)
    expire = datetime.now(timezone.utc) + timedelta(
        days=settings.security.jwt_refresh_token_expire_days
    )
    
    to_encode["exp"] = expire
    to_encode["type"] = "refresh"  # Mark as refresh token
    
    # Encode the JWT token
    encoded_jwt = jwt.encode(
        to_encode,
        settings.security.jwt_secret_key,
        algorithm=settings.security.jwt_algorithm,
    )
    
    logger.debug(f"Created refresh token for subject: {data.get('sub')}")
    return encoded_jwt


def decode_token(token: str) -> dict:
    """
    Decode and validate a JWT token.
    
    This function decodes the token and validates its signature and expiration.
    Raises JWTError if the token is invalid or expired.
    
    Args:
        token: JWT token string to decode
        
    Returns:
        Decoded token payload as dictionary
        
    Raises:
        JWTError: If token is invalid, expired, or signature verification fails
        
    Example:
        >>> payload = decode_token(token)
        >>> user_id = payload.get("sub")
    """
    try:
        payload = jwt.decode(
            token,
            settings.security.jwt_secret_key,
            algorithms=[settings.security.jwt_algorithm],
        )
        return payload
    except JWTError as e:
        logger.warning(f"JWT decode error: {e}")
        raise


def verify_token(token: str) -> dict | None:
    """
    Verify and decode a JWT token, returning None if invalid.
    
    This is a safer version of decode_token that returns None instead
    of raising an exception for invalid tokens.
    
    Args:
        token: JWT token string to verify
        
    Returns:
        Decoded token payload if valid, None if invalid or expired
        
    Example:
        >>> payload = verify_token(token)
        >>> if payload:
        ...     user_id = payload.get("sub")
        ... else:
        ...     print("Invalid token")
    """
    try:
        return decode_token(token)
    except JWTError:
        return None


async def get_current_user(
    token: Annotated[str, Depends(oauth2_scheme)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> User:
    """
    FastAPI dependency to extract and validate the current user from JWT token.
    
    This dependency:
    1. Extracts the Bearer token from the Authorization header
    2. Decodes and validates the JWT token
    3. Fetches the user from the database
    4. Returns the User object if valid
    
    Args:
        token: JWT token extracted from Authorization header
        db: Database session for user lookup
        
    Returns:
        User object for the authenticated user
        
    Raises:
        HTTPException: 401 if token is invalid, expired, or user not found
        
    Usage:
        @router.get("/me")
        async def get_me(current_user: Annotated[User, Depends(get_current_user)]):
            return current_user
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        # Decode and validate token
        payload = decode_token(token)
        user_id_str: str | None = payload.get("sub")
        
        if user_id_str is None:
            logger.warning("Token missing 'sub' claim")
            raise credentials_exception
        
        # Convert string UUID to UUID object
        try:
            user_id = UUID(user_id_str)
        except ValueError:
            logger.warning(f"Invalid UUID in token: {user_id_str}")
            raise credentials_exception
        
    except JWTError as e:
        logger.warning(f"JWT validation failed: {e}")
        raise credentials_exception
    
    # Fetch user from database
    user_repository = UserRepository(db)
    user = await user_repository.get_by_id(user_id)
    
    if user is None:
        logger.warning(f"User not found for ID: {user_id}")
        raise credentials_exception
    
    logger.debug(f"Authenticated user: {user.email} (ID: {user.id})")
    return user


async def get_current_active_user(
    current_user: Annotated[User, Depends(get_current_user)],
) -> User:
    """
    FastAPI dependency to ensure the current user is active.
    
    This dependency builds on get_current_user to add an additional
    check that the user account is active (not disabled).
    
    Args:
        current_user: User object from get_current_user dependency
        
    Returns:
        User object if active
        
    Raises:
        HTTPException: 403 if user account is inactive
        
    Usage:
        @router.get("/protected")
        async def protected_route(
            current_user: Annotated[User, Depends(get_current_active_user)]
        ):
            return {"message": f"Hello {current_user.email}"}
    """
    if not current_user.is_active:
        logger.warning(f"Inactive user attempted access: {current_user.email}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Inactive user account",
        )
    
    return current_user


async def get_current_superuser(
    current_user: Annotated[User, Depends(get_current_user)],
) -> User:
    """
    FastAPI dependency to ensure the current user is a superuser.
    
    This dependency checks that the authenticated user has superuser
    privileges. Used for admin-only endpoints.
    
    Args:
        current_user: User object from get_current_user dependency
        
    Returns:
        User object if superuser
        
    Raises:
        HTTPException: 403 if user is not a superuser
        
    Usage:
        @router.delete("/users/{user_id}")
        async def delete_user(
            user_id: UUID,
            admin: Annotated[User, Depends(get_current_superuser)]
        ):
            # Only superusers can access this endpoint
            ...
    """
    if not current_user.is_superuser:
        logger.warning(
            f"Non-superuser attempted admin access: {current_user.email}"
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient privileges",
        )
    
    return current_user