"""
User repository for data access abstraction.

This module provides the repository pattern implementation for User model,
handling all database operations related to users. It abstracts SQLAlchemy
queries and provides a clean interface for the service layer.
"""

import logging
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from ardha.models.user import User

logger = logging.getLogger(__name__)


class UserRepository:
    """
    Repository for User model database operations.
    
    Provides data access methods for user-related operations including
    CRUD operations, OAuth lookups, and pagination. Follows the repository
    pattern to abstract database implementation details from business logic.
    
    Attributes:
        db: SQLAlchemy async session for database operations
    """
    
    def __init__(self, db: AsyncSession) -> None:
        """
        Initialize the UserRepository with a database session.
        
        Args:
            db: SQLAlchemy async session for database operations
        """
        self.db = db
    
    async def get_by_id(self, user_id: UUID) -> User | None:
        """
        Fetch a user by their UUID.
        
        Args:
            user_id: UUID of the user to fetch
            
        Returns:
            User object if found, None otherwise
            
        Raises:
            SQLAlchemyError: If database query fails
        """
        try:
            stmt = select(User).where(User.id == user_id)
            result = await self.db.execute(stmt)
            return result.scalar_one_or_none()
        except SQLAlchemyError as e:
            logger.error(f"Error fetching user by id {user_id}: {e}", exc_info=True)
            raise
    
    async def get_by_email(self, email: str) -> User | None:
        """
        Fetch a user by their email address.
        
        Used primarily for login lookups and email uniqueness validation.
        
        Args:
            email: Email address to search for
            
        Returns:
            User object if found, None otherwise
            
        Raises:
            SQLAlchemyError: If database query fails
        """
        try:
            stmt = select(User).where(User.email == email)
            result = await self.db.execute(stmt)
            return result.scalar_one_or_none()
        except SQLAlchemyError as e:
            logger.error(f"Error fetching user by email {email}: {e}", exc_info=True)
            raise
    
    async def get_by_username(self, username: str) -> User | None:
        """
        Fetch a user by their username.
        
        Used for username uniqueness checks during registration.
        
        Args:
            username: Username to search for
            
        Returns:
            User object if found, None otherwise
            
        Raises:
            SQLAlchemyError: If database query fails
        """
        try:
            stmt = select(User).where(User.username == username)
            result = await self.db.execute(stmt)
            return result.scalar_one_or_none()
        except SQLAlchemyError as e:
            logger.error(f"Error fetching user by username {username}: {e}", exc_info=True)
            raise
    
    async def get_by_oauth_id(self, provider: str, oauth_id: str) -> User | None:
        """
        Fetch a user by their OAuth provider ID.
        
        Supports GitHub and Google OAuth lookups for authentication flow.
        
        Args:
            provider: OAuth provider name ('github' or 'google')
            oauth_id: OAuth user ID from the provider
            
        Returns:
            User object if found, None otherwise
            
        Raises:
            ValueError: If provider is not 'github' or 'google'
            SQLAlchemyError: If database query fails
        """
        try:
            if provider == "github":
                stmt = select(User).where(User.github_id == oauth_id)
            elif provider == "google":
                stmt = select(User).where(User.google_id == oauth_id)
            else:
                raise ValueError(
                    f"Invalid OAuth provider: {provider}. Must be 'github' or 'google'"
                )
            
            result = await self.db.execute(stmt)
            return result.scalar_one_or_none()
        except SQLAlchemyError as e:
            logger.error(
                f"Error fetching user by {provider} OAuth ID {oauth_id}: {e}",
                exc_info=True,
            )
            raise
    
    async def create(self, user_data: dict) -> User:
        """
        Create a new user record.
        
        Args:
            user_data: Dictionary containing user fields (email, username, etc.)
            
        Returns:
            Created User object with generated ID and timestamps
            
        Raises:
            IntegrityError: If unique constraint violated (duplicate email/username)
            SQLAlchemyError: If database operation fails
        """
        try:
            user = User(**user_data)
            self.db.add(user)
            await self.db.flush()  # Flush to get ID without committing
            await self.db.refresh(user)  # Refresh to get generated fields
            return user
        except IntegrityError as e:
            logger.warning(f"Integrity error creating user: {e}")
            raise
        except SQLAlchemyError as e:
            logger.error(f"Error creating user: {e}", exc_info=True)
            raise
    
    async def update(self, user_id: UUID, **kwargs) -> User | None:
        """
        Update user fields.
        
        Updates specified fields for a user identified by UUID.
        Only updates fields provided in kwargs.
        
        Args:
            user_id: UUID of user to update
            **kwargs: Fields to update (e.g., full_name="John Doe", is_active=False)
            
        Returns:
            Updated User object if found, None if user doesn't exist
            
        Raises:
            IntegrityError: If update violates unique constraints
            SQLAlchemyError: If database operation fails
        """
        try:
            user = await self.get_by_id(user_id)
            if not user:
                logger.warning(f"Cannot update: user {user_id} not found")
                return None
            
            # Update only provided fields
            for key, value in kwargs.items():
                if hasattr(user, key):
                    setattr(user, key, value)
                else:
                    logger.warning(f"Skipping unknown field: {key}")
            
            await self.db.flush()
            await self.db.refresh(user)
            return user
        except IntegrityError as e:
            logger.warning(f"Integrity error updating user {user_id}: {e}")
            raise
        except SQLAlchemyError as e:
            logger.error(f"Error updating user {user_id}: {e}", exc_info=True)
            raise
    
    async def delete(self, user_id: UUID) -> bool:
        """
        Soft delete a user by setting is_active to False.
        
        Implements soft delete for audit trail preservation. User remains
        in database but is marked as inactive.
        
        Args:
            user_id: UUID of user to delete
            
        Returns:
            True if user was deleted, False if user not found
            
        Raises:
            SQLAlchemyError: If database operation fails
        """
        try:
            user = await self.get_by_id(user_id)
            if not user:
                logger.warning(f"Cannot delete: user {user_id} not found")
                return False
            
            user.is_active = False
            await self.db.flush()
            logger.info(f"Soft deleted user {user_id}")
            return True
        except SQLAlchemyError as e:
            logger.error(f"Error deleting user {user_id}: {e}", exc_info=True)
            raise
    
    async def list_users(
        self,
        skip: int = 0,
        limit: int = 100,
        include_inactive: bool = False,
    ) -> list[User]:
        """
        Fetch paginated list of users.
        
        Args:
            skip: Number of records to skip (for pagination)
            limit: Maximum number of records to return (capped at 100)
            include_inactive: Whether to include inactive users (default: False)
            
        Returns:
            List of User objects
            
        Raises:
            SQLAlchemyError: If database query fails
        """
        try:
            stmt = select(User)
            
            # Filter out inactive users by default
            if not include_inactive:
                stmt = stmt.where(User.is_active == True)
            
            # Apply pagination (enforce max limit of 100)
            stmt = stmt.offset(skip).limit(min(limit, 100))
            
            result = await self.db.execute(stmt)
            return list(result.scalars().all())
        except SQLAlchemyError as e:
            logger.error(f"Error listing users: {e}", exc_info=True)
            raise