"""
Integration tests for authentication flow.

Tests the complete authentication workflow including registration,
login, token refresh, and protected route access.
"""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_user_registration_and_login(client: AsyncClient) -> None:
    """Test complete registration and login flow."""
    # Register new user
    register_response = await client.post(
        "/api/v1/auth/register",
        json={
            "email": "newuser@example.com",
            "username": "newuser",
            "password": "SecurePass123!",
            "full_name": "New User",
        },
    )
    assert register_response.status_code == 201
    register_data = register_response.json()
    assert register_data["email"] == "newuser@example.com"
    assert register_data["username"] == "newuser"
    assert "password_hash" not in register_data
    assert "id" in register_data
    
    # Login with credentials
    login_response = await client.post(
        "/api/v1/auth/login",
        data={
            "username": "newuser@example.com",
            "password": "SecurePass123!",
        },
    )
    assert login_response.status_code == 200
    login_data = login_response.json()
    assert "access_token" in login_data
    assert "refresh_token" in login_data
    assert login_data["token_type"] == "bearer"
    
    # Verify token works by getting user profile
    me_response = await client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {login_data['access_token']}"},
    )
    assert me_response.status_code == 200
    assert me_response.json()["email"] == "newuser@example.com"


@pytest.mark.asyncio
async def test_duplicate_user_registration(client: AsyncClient, test_user: dict) -> None:
    """Test that duplicate registration fails."""
    # Attempt to register with same email
    response = await client.post(
        "/api/v1/auth/register",
        json={
            "email": "test@example.com",
            "username": "differentuser",
            "password": "Test123!@#",
            "full_name": "Test User",
        },
    )
    assert response.status_code == 400
    assert "already exists" in response.json()["detail"].lower()
    
    # Attempt to register with same username
    response = await client.post(
        "/api/v1/auth/register",
        json={
            "email": "different@example.com",
            "username": "testuser",
            "password": "Test123!@#",
            "full_name": "Test User",
        },
    )
    assert response.status_code == 400
    assert "already" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_invalid_login_credentials(client: AsyncClient, test_user: dict) -> None:
    """Test login with wrong password."""
    response = await client.post(
        "/api/v1/auth/login",
        data={
            "username": "test@example.com",
            "password": "WrongPassword123!",
        },
    )
    assert response.status_code == 401
    assert "incorrect" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_protected_route_without_token(client: AsyncClient) -> None:
    """Test accessing protected route without token."""
    response = await client.get("/api/v1/auth/me")
    assert response.status_code == 401
    assert "not authenticated" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_protected_route_with_valid_token(
    client: AsyncClient,
    test_user: dict,
) -> None:
    """Test accessing protected route with valid token."""
    response = await client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {test_user['token']}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["email"] == "test@example.com"
    assert data["username"] == "testuser"
    assert "password_hash" not in data


@pytest.mark.asyncio
async def test_token_refresh(client: AsyncClient, test_user: dict) -> None:
    """Test refreshing access token."""
    # Use refresh token to get new access token
    response = await client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": test_user["refresh_token"]},
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    
    # Verify new access token works
    me_response = await client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {data['access_token']}"},
    )
    assert me_response.status_code == 200
    assert me_response.json()["email"] == "test@example.com"


@pytest.mark.asyncio
async def test_logout(client: AsyncClient, test_user: dict) -> None:
    """Test logout endpoint (stateless)."""
    response = await client.post(
        "/api/v1/auth/logout",
        headers={"Authorization": f"Bearer {test_user['token']}"},
    )
    assert response.status_code == 200
    assert "logged out" in response.json()["message"].lower()


@pytest.mark.asyncio
async def test_update_profile(client: AsyncClient, test_user: dict) -> None:
    """Test updating user profile."""
    response = await client.patch(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {test_user['token']}"},
        json={
            "full_name": "Updated Name",
            "avatar_url": "https://example.com/avatar.jpg",
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["full_name"] == "Updated Name"
    assert data["avatar_url"] == "https://example.com/avatar.jpg"
    
    # Verify changes persisted
    me_response = await client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {test_user['token']}"},
    )
    assert me_response.status_code == 200
    assert me_response.json()["full_name"] == "Updated Name"