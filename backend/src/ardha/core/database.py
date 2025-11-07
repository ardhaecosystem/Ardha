"""
Database configuration and session management.

This module provides:
- Async SQLAlchemy engine configured for PostgreSQL
- Async session factory for dependency injection
- Database session dependency for FastAPI routes
- Proper connection lifecycle management
"""

import logging
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy import text

from ardha.core.config import settings

logger = logging.getLogger(__name__)


# Create async engine with connection pooling
# pool_size=20, max_overflow=0 respects 2GB PostgreSQL container limit
engine: AsyncEngine = create_async_engine(
    settings.database.url,
    echo=settings.debug,  # Log SQL queries in debug mode
    pool_pre_ping=True,  # Verify connections before using
    pool_size=settings.database.pool_size,  # Default: 20
    max_overflow=settings.database.max_overflow,  # Default: 0 (no overflow)
    pool_recycle=3600,  # Recycle connections after 1 hour
    pool_timeout=30,  # Wait 30s for connection from pool
)


# Create async session factory
# expire_on_commit=False keeps objects usable after commit
async_session_factory: async_sessionmaker[AsyncSession] = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
    autocommit=False,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    FastAPI dependency that provides a database session.
    
    Yields an async database session and handles proper cleanup.
    Automatically commits on success or rolls back on exception.
    
    Usage:
        @router.get("/users")
        async def get_users(db: AsyncSession = Depends(get_db)):
            result = await db.execute(select(User))
            return result.scalars().all()
    
    Yields:
        AsyncSession: Database session for the request
    
    Raises:
        Exception: Any exception from database operations (after rollback)
    """
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception as e:
            await session.rollback()
            logger.error(f"Database session error: {e}", exc_info=True)
            raise
        finally:
            await session.close()


async def init_db() -> None:
    """
    Initialize database connection and verify connectivity.
    
    This function should be called on application startup to:
    - Verify database connection works
    - Log connection status
    
    Note: Does NOT create tables - use Alembic migrations for that.
    
    Raises:
        Exception: If database connection fails
    """
    try:
        async with engine.begin() as conn:
            # Test connection with a simple query
            await conn.execute(text("SELECT 1"))
        logger.info("Database connection initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize database connection: {e}", exc_info=True)
        raise


async def close_db() -> None:
    """
    Close database connections gracefully.
    
    This function should be called on application shutdown to:
    - Close all active connections
    - Release resources properly
    """
    await engine.dispose()
    logger.info("Database connections closed")