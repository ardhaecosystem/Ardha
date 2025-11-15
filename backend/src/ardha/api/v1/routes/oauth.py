"""
OAuth authentication routes for GitHub and Google login.

This module provides endpoints for OAuth-based authentication, allowing users
to sign in or register using their GitHub or Google accounts.
"""

import logging
from typing import Annotated

import httpx
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from ardha.core.config import settings
from ardha.core.database import get_db
from ardha.core.security import create_access_token, create_refresh_token
from ardha.repositories.user_repository import UserRepository
from ardha.services.auth_service import AuthService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth/oauth", tags=["oauth"])


# Request/Response Models
class OAuthCodeRequest(BaseModel):
    """OAuth authorization code from provider callback."""

    code: str = Field(..., description="Authorization code from OAuth provider")


class TokenResponse(BaseModel):
    """JWT token response after successful OAuth."""

    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user: dict


# GitHub OAuth Configuration
GITHUB_TOKEN_URL = "https://github.com/login/oauth/access_token"
GITHUB_USER_URL = "https://api.github.com/user"

# Google OAuth Configuration
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_USER_URL = "https://www.googleapis.com/oauth2/v2/userinfo"


@router.post(
    "/github",
    response_model=TokenResponse,
    status_code=status.HTTP_200_OK,
    summary="GitHub OAuth Login",
    description="Exchange GitHub authorization code for access token and user data",
)
async def github_oauth(
    request: OAuthCodeRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> TokenResponse:
    """
    Handle GitHub OAuth login/registration.

    Flow:
    1. Exchange authorization code for GitHub access token
    2. Fetch user info from GitHub API
    3. Login existing user or create new user
    4. Return JWT tokens

    Args:
        request: OAuth code from GitHub callback
        db: Database session

    Returns:
        JWT access and refresh tokens with user data

    Raises:
        HTTPException 400: Invalid authorization code
        HTTPException 500: GitHub API error or missing OAuth credentials
        HTTPException 502: GitHub API unavailable
    """
    # Check if GitHub OAuth is configured
    if not settings.oauth.github_client_id or not settings.oauth.github_client_secret:
        logger.error("GitHub OAuth credentials not configured")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="GitHub OAuth is not configured on this server",
        )

    try:
        # Exchange code for access token
        async with httpx.AsyncClient() as client:
            token_response = await client.post(
                GITHUB_TOKEN_URL,
                json={
                    "client_id": settings.oauth.github_client_id,
                    "client_secret": settings.oauth.github_client_secret,
                    "code": request.code,
                },
                headers={"Accept": "application/json"},
                timeout=10.0,
            )

            if token_response.status_code != 200:
                logger.warning(f"GitHub token exchange failed: {token_response.text}")
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid authorization code",
                )

            token_data = token_response.json()
            access_token = token_data.get("access_token")

            if not access_token:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Failed to obtain access token from GitHub",
                )

            # Fetch user info from GitHub
            user_response = await client.get(
                GITHUB_USER_URL,
                headers={
                    "Authorization": f"Bearer {access_token}",
                    "Accept": "application/json",
                },
                timeout=10.0,
            )

            if user_response.status_code != 200:
                logger.error(f"GitHub user info fetch failed: {user_response.text}")
                raise HTTPException(
                    status_code=status.HTTP_502_BAD_GATEWAY,
                    detail="Failed to fetch user info from GitHub",
                )

            github_user = user_response.json()

    except httpx.TimeoutException:
        logger.error("GitHub API timeout")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="GitHub API is currently unavailable",
        )
    except httpx.RequestError as e:
        logger.error(f"GitHub API request error: {e}")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Failed to communicate with GitHub API",
        )

    # Extract user data
    github_id = str(github_user.get("id"))
    email = github_user.get("email")
    username = github_user.get("login", f"github_{github_id}")
    full_name = github_user.get("name")
    avatar_url = github_user.get("avatar_url")

    if not email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="GitHub account must have a public email address",
        )

    # Login or create user
    user_repository = UserRepository(db)
    auth_service = AuthService(user_repository)

    try:
        user = await auth_service.oauth_login_or_create(
            provider="github",
            oauth_id=github_id,
            email=email,
            username=username,
            full_name=full_name,
            avatar_url=avatar_url,
        )

        # Commit the transaction
        await db.commit()

        # Generate JWT tokens
        access_token_jwt = create_access_token(data={"sub": str(user.id)})
        refresh_token_jwt = create_refresh_token(data={"sub": str(user.id)})

        logger.info(f"GitHub OAuth successful for user: {user.email}")

        return TokenResponse(
            access_token=access_token_jwt,
            refresh_token=refresh_token_jwt,
            token_type="bearer",
            user={
                "id": str(user.id),
                "email": user.email,
                "username": user.username,
                "full_name": user.full_name,
                "avatar_url": user.avatar_url,
            },
        )

    except Exception as e:
        await db.rollback()
        logger.error(f"Error during GitHub OAuth: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to process GitHub OAuth login",
        )


@router.post(
    "/google",
    response_model=TokenResponse,
    status_code=status.HTTP_200_OK,
    summary="Google OAuth Login",
    description="Exchange Google authorization code for access token and user data",
)
async def google_oauth(
    request: OAuthCodeRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> TokenResponse:
    """
    Handle Google OAuth login/registration.

    Flow:
    1. Exchange authorization code for Google access token
    2. Fetch user info from Google API
    3. Login existing user or create new user
    4. Return JWT tokens

    Args:
        request: OAuth code from Google callback
        db: Database session

    Returns:
        JWT access and refresh tokens with user data

    Raises:
        HTTPException 400: Invalid authorization code
        HTTPException 500: Google API error or missing OAuth credentials
        HTTPException 502: Google API unavailable
    """
    # Check if Google OAuth is configured
    if not settings.oauth.google_client_id or not settings.oauth.google_client_secret:
        logger.error("Google OAuth credentials not configured")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Google OAuth is not configured on this server",
        )

    try:
        # Exchange code for access token
        async with httpx.AsyncClient() as client:
            token_response = await client.post(
                GOOGLE_TOKEN_URL,
                data={
                    "client_id": settings.oauth.google_client_id,
                    "client_secret": settings.oauth.google_client_secret,
                    "code": request.code,
                    "grant_type": "authorization_code",
                    "redirect_uri": "http://localhost:3000/auth/callback/google",
                },
                headers={"Content-Type": "application/x-www-form-urlencoded"},
                timeout=10.0,
            )

            if token_response.status_code != 200:
                logger.warning(f"Google token exchange failed: {token_response.text}")
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid authorization code",
                )

            token_data = token_response.json()
            access_token = token_data.get("access_token")

            if not access_token:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Failed to obtain access token from Google",
                )

            # Fetch user info from Google
            user_response = await client.get(
                GOOGLE_USER_URL,
                headers={
                    "Authorization": f"Bearer {access_token}",
                },
                timeout=10.0,
            )

            if user_response.status_code != 200:
                logger.error(f"Google user info fetch failed: {user_response.text}")
                raise HTTPException(
                    status_code=status.HTTP_502_BAD_GATEWAY,
                    detail="Failed to fetch user info from Google",
                )

            google_user = user_response.json()

    except httpx.TimeoutException:
        logger.error("Google API timeout")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Google API is currently unavailable",
        )
    except httpx.RequestError as e:
        logger.error(f"Google API request error: {e}")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Failed to communicate with Google API",
        )

    # Extract user data
    google_id = google_user.get("id")
    email = google_user.get("email")
    username = email.split("@")[0] if email else f"google_{google_id}"
    full_name = google_user.get("name")
    avatar_url = google_user.get("picture")

    if not email or not google_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to retrieve required user information from Google",
        )

    # Login or create user
    user_repository = UserRepository(db)
    auth_service = AuthService(user_repository)

    try:
        user = await auth_service.oauth_login_or_create(
            provider="google",
            oauth_id=google_id,
            email=email,
            username=username,
            full_name=full_name,
            avatar_url=avatar_url,
        )

        # Commit the transaction
        await db.commit()

        # Generate JWT tokens
        access_token_jwt = create_access_token(data={"sub": str(user.id)})
        refresh_token_jwt = create_refresh_token(data={"sub": str(user.id)})

        logger.info(f"Google OAuth successful for user: {user.email}")

        return TokenResponse(
            access_token=access_token_jwt,
            refresh_token=refresh_token_jwt,
            token_type="bearer",
            user={
                "id": str(user.id),
                "email": user.email,
                "username": user.username,
                "full_name": user.full_name,
                "avatar_url": user.avatar_url,
            },
        )

    except Exception as e:
        await db.rollback()
        logger.error(f"Error during Google OAuth: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to process Google OAuth login",
        )
