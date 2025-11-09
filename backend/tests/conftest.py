"""
Shared test fixtures for Ardha backend tests.

This module provides pytest fixtures for database setup, test clients,
and common test data used across unit and integration tests.
"""

import asyncio
from typing import AsyncGenerator

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from ardha.core.database import get_db
from ardha.main import app
from ardha.models.base import Base

# Test database URL (separate from development database)
TEST_DATABASE_URL = "postgresql+asyncpg://ardha_user:ardha_password@localhost:5432/ardha_test"


@pytest.fixture(scope="session")
def event_loop():
    """
    Create event loop for async tests.
    
    This fixture ensures all async tests share the same event loop
    for the entire test session, preventing event loop conflicts.
    """
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="function")
async def test_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Create test database and provide session.
    
    This fixture:
    1. Creates a fresh database engine for each test
    2. Drops all tables (clean slate)
    3. Creates all tables from models
    4. Provides an async session
    5. Cleans up after test completes
    
    Yields:
        AsyncSession for database operations
    """
    # Create async engine for test database
    engine = create_async_engine(
        TEST_DATABASE_URL,
        echo=False,  # Set to True for SQL query debugging
        pool_pre_ping=True,
    )
    
    # Drop and recreate all tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    
    # Create session factory
    async_session_factory = async_sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )
    
    # Provide session for test
    async with async_session_factory() as session:
        yield session
    
    # Cleanup
    await engine.dispose()


@pytest_asyncio.fixture
async def client(test_db: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """
    Create test client with database override.
    
    This fixture:
    1. Overrides the get_db dependency to use test database
    2. Creates an AsyncClient for making HTTP requests
    3. Cleans up dependency overrides after test
    
    Args:
        test_db: Test database session from test_db fixture
        
    Yields:
        AsyncClient for making API requests
    """
    
    async def override_get_db() -> AsyncGenerator[AsyncSession, None]:
        """Override get_db to use test database."""
        yield test_db
    
    # Override dependency
    app.dependency_overrides[get_db] = override_get_db
    
    # Create test client
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
        follow_redirects=True,
    ) as ac:
        yield ac
    
    # Clear overrides
    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def test_user(client: AsyncClient) -> dict:
    """
    Create test user and return authentication data.
    
    This fixture:
    1. Registers a new test user
    2. Logs in the user
    3. Returns user data with JWT token
    
    Args:
        client: Test client from client fixture
        
    Returns:
        Dictionary with 'token' (JWT) and 'user' (user data)
    """
    # Register user
    register_response = await client.post(
        "/api/v1/auth/register",
        json={
            "email": "test@example.com",
            "username": "testuser",
            "password": "Test123!@#",
            "full_name": "Test User",
        },
    )
    assert register_response.status_code == 201
    
    # Login user
    login_response = await client.post(
        "/api/v1/auth/login",
        data={
            "username": "test@example.com",
            "password": "Test123!@#",
        },
    )
    assert login_response.status_code == 200
    
    token_data = login_response.json()
    access_token = token_data["access_token"]
    
    # Get user profile
    me_response = await client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {access_token}"},
    )
    assert me_response.status_code == 200
    user_data = me_response.json()
    
    return {
        "token": access_token,
        "refresh_token": token_data["refresh_token"],
        "user": user_data,
    }


@pytest_asyncio.fixture
async def test_project(client: AsyncClient, test_user: dict) -> dict:
    """
    Create test project for testing.
    
    Args:
        client: Test client
        test_user: Authenticated test user
        
    Returns:
        Dictionary with project data
    """
    response = await client.post(
        "/api/v1/projects",
        headers={"Authorization": f"Bearer {test_user['token']}"},
        json={
            "name": "Test Project",
            "description": "A test project for integration tests",
            "visibility": "private",
            "tech_stack": ["Python", "FastAPI"],
        },
    )
    assert response.status_code == 201
    return response.json()


@pytest_asyncio.fixture
async def test_milestone(
    client: AsyncClient,
    test_user: dict,
    test_project: dict,
) -> dict:
    """
    Create test milestone for testing.
    
    Args:
        client: Test client
        test_user: Authenticated test user
        test_project: Test project
        
    Returns:
        Dictionary with milestone data
    """
    from datetime import datetime, timedelta
    
    due_date = (datetime.now() + timedelta(days=30)).isoformat()
    
    response = await client.post(
        f"/api/v1/milestones/projects/{test_project['id']}/milestones",
        headers={"Authorization": f"Bearer {test_user['token']}"},
        json={
            "name": "Test Milestone",
            "description": "A test milestone",
            "due_date": due_date,
            "status": "in_progress",
        },
    )
    assert response.status_code == 201
    return response.json()


@pytest_asyncio.fixture
async def test_task(
    client: AsyncClient,
    test_user: dict,
    test_project: dict,
) -> dict:
    """
    Create test task for testing.
    
    Args:
        client: Test client
        test_user: Authenticated test user
        test_project: Test project
        
    Returns:
        Dictionary with task data
    """
    response = await client.post(
        f"/api/v1/tasks/projects/{test_project['id']}/tasks",
        headers={"Authorization": f"Bearer {test_user['token']}"},
        json={
            "title": "Test Task",
            "description": "A test task",
            "priority": "medium",
            "tags": ["testing"],
        },
    )
    assert response.status_code == 201
    return response.json()