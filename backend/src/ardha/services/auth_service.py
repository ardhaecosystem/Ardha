"""
Authentication service for user registration and authentication.

This module provides the business logic layer for user authentication,
including registration, login, password management, and OAuth support.
Uses bcrypt for secure password hashing with cost factor 12.
"""

import logging
from datetime import datetime, timezone
from uuid import UUID

from passlib.context import CryptContext

from ardha.models.user import User
from ardha.repositories.user_repository import UserRepository
from ardha.schemas.requests.auth import UserRegisterRequest

logger = logging.getLogger(__name__)


# Custom exceptions for authentication business logic
class UserAlreadyExistsError(Exception):
    """Raised when attempting to register with an existing email or username."""

    pass


class InvalidCredentialsError(Exception):
    """Raised when authentication fails due to invalid credentials."""

    pass


# Password hashing context with bcrypt (cost factor 12)
pwd_context = CryptContext(
    schemes=["bcrypt"],
    deprecated="auto",
    bcrypt__rounds=12,  # Cost factor for security/performance balance
)


class AuthService:
    """
    Service for user authentication and management.

    Handles user registration, login, password verification, and account
    management. Uses UserRepository for all database operations and bcrypt
    for secure password hashing.

    Attributes:
        user_repository: Repository for user data access
    """

    def __init__(self, user_repository: UserRepository) -> None:
        """
        Initialize AuthService with a user repository.

        Args:
            user_repository: Repository for user database operations
        """
        self.user_repository = user_repository

    def hash_password(self, password: str) -> str:
        """
        Hash a plain text password using bcrypt.

        Uses bcrypt with cost factor 12 for security. The resulting hash
        will start with $2b$ prefix and be approximately 60 characters.

        Args:
            password: Plain text password to hash

        Returns:
            Bcrypt password hash (starts with $2b$, ~60 chars)

        Example:
            >>> hash = auth_service.hash_password("SecurePass123")
            >>> hash.startswith("$2b$")
            True
        """
        return pwd_context.hash(password)

    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """
        Verify a plain password against a bcrypt hash.

        Uses constant-time comparison via passlib to prevent timing attacks.

        Args:
            plain_password: Plain text password to verify
            hashed_password: Bcrypt hash to compare against

        Returns:
            True if password matches, False otherwise

        Example:
            >>> hash = auth_service.hash_password("SecurePass123")
            >>> auth_service.verify_password("SecurePass123", hash)
            True
            >>> auth_service.verify_password("WrongPass", hash)
            False
        """
        return pwd_context.verify(plain_password, hashed_password)

    async def register_user(self, user_data: UserRegisterRequest) -> User:
        """
        Register a new user account.

        Registration flow:
        1. Check if email already exists (raise error if exists)
        2. Check if username already exists (raise error if exists)
        3. Hash the password using bcrypt
        4. Create user via repository
        5. Return created user

        Args:
            user_data: Validated user registration data

        Returns:
            Created User object with hashed password

        Raises:
            UserAlreadyExistsError: If email or username already taken

        Example:
            >>> from ardha.schemas.requests.auth import UserRegisterRequest
            >>> request = UserRegisterRequest(
            ...     email="user@example.com",
            ...     username="john_doe",
            ...     full_name="John Doe",
            ...     password="SecurePass123"
            ... )
            >>> user = await auth_service.register_user(request)
            >>> print(user.email)
            'user@example.com'
        """
        # Check if email already exists
        existing_user = await self.user_repository.get_by_email(user_data.email)
        if existing_user:
            logger.warning(f"Registration failed: email {user_data.email} already exists")
            raise UserAlreadyExistsError(f"User with email {user_data.email} already exists")

        # Check if username already exists
        existing_username = await self.user_repository.get_by_username(user_data.username)
        if existing_username:
            logger.warning(f"Registration failed: username {user_data.username} already exists")
            raise UserAlreadyExistsError(f"Username {user_data.username} is already taken")

        # Hash the password (never store plain text)
        hashed_password = self.hash_password(user_data.password)

        # Create user via repository
        user_dict = {
            "email": user_data.email,
            "username": user_data.username,
            "full_name": user_data.full_name,
            "password_hash": hashed_password,
            "is_active": True,
            "is_superuser": False,
        }

        user = await self.user_repository.create(user_dict)
        logger.info(f"User registered successfully: {user.email} (ID: {user.id})")

        return user

    async def authenticate_user(self, email: str, password: str) -> User | None:
        """
        Authenticate a user with email and password.

        Authentication flow:
        1. Fetch user by email
        2. Return None if user not found
        3. Return None if user is inactive
        4. Verify password hash matches
        5. Update last_login_at timestamp if successful
        6. Return user or None

        Args:
            email: User's email address
            password: Plain text password to verify

        Returns:
            User object if authentication successful, None otherwise

        Raises:
            InvalidCredentialsError: Never raised (returns None instead for security)

        Example:
            >>> user = await auth_service.authenticate_user(
            ...     "user@example.com",
            ...     "SecurePass123"
            ... )
            >>> if user:
            ...     print(f"Login successful: {user.email}")
            ... else:
            ...     print("Invalid credentials")
        """
        # Fetch user by email
        user = await self.user_repository.get_by_email(email)

        if not user:
            # Don't reveal whether email exists (security)
            logger.warning(f"Login attempt for non-existent email: {email}")
            return None

        # Check if user is active
        if not user.is_active:
            logger.warning(f"Login attempt for inactive user: {email}")
            return None

        # OAuth users may not have password_hash
        if not user.password_hash:
            logger.warning(f"Login attempt with password for OAuth user: {email}")
            return None

        # Verify password
        if not self.verify_password(password, user.password_hash):
            logger.warning(f"Failed login attempt for user: {email}")
            return None

        # Authentication successful - update last login timestamp
        await self.update_last_login(user.id)

        logger.info(f"User authenticated successfully: {email} (ID: {user.id})")
        return user

    async def get_user_by_email(self, email: str) -> User | None:
        """
        Fetch a user by email address.

        Delegates to repository for data access.

        Args:
            email: Email address to search for

        Returns:
            User object if found, None otherwise
        """
        return await self.user_repository.get_by_email(email)

    async def get_user_by_id(self, user_id: UUID) -> User | None:
        """
        Fetch a user by UUID.

        Delegates to repository for data access.

        Args:
            user_id: UUID of user to fetch

        Returns:
            User object if found, None otherwise
        """
        return await self.user_repository.get_by_id(user_id)

    async def update_last_login(self, user_id: UUID) -> None:
        """
        Update user's last login timestamp to current UTC time.

        Called automatically on successful authentication.

        Args:
            user_id: UUID of user to update

        Raises:
            ValueError: If user not found
        """
        user = await self.user_repository.get_by_id(user_id)
        if not user:
            raise ValueError(f"Cannot update last login: user {user_id} not found")

        # Update timestamp to current UTC time
        await self.user_repository.update(user_id, last_login_at=datetime.now(timezone.utc))

        logger.debug(f"Updated last login for user {user_id}")

    async def oauth_login_or_create(
        self,
        provider: str,
        oauth_id: str,
        email: str,
        username: str,
        full_name: str | None,
        avatar_url: str | None,
    ) -> User:
        """
        Handle OAuth login or registration.

        Flow:
        1. Check if user exists by OAuth ID (provider-specific)
        2. If exists: Update last login and return user
        3. If not exists: Check if email already registered
        4. If email exists: Link OAuth account to existing user
        5. If email doesn't exist: Create new user with OAuth data

        Args:
            provider: OAuth provider name ('github' or 'google')
            oauth_id: OAuth user ID from provider
            email: User's email from OAuth provider
            username: Username from OAuth provider
            full_name: Full name from OAuth provider (optional)
            avatar_url: Avatar URL from OAuth provider (optional)

        Returns:
            User object (existing or newly created)

        Raises:
            ValueError: If provider is invalid

        Example:
            >>> user = await auth_service.oauth_login_or_create(
            ...     provider="github",
            ...     oauth_id="12345",
            ...     email="user@example.com",
            ...     username="githubuser",
            ...     full_name="John Doe",
            ...     avatar_url="https://avatars.githubusercontent.com/..."
            ... )
        """
        # Validate provider
        if provider not in ("github", "google"):
            raise ValueError(f"Invalid OAuth provider: {provider}")

        # Check if user exists by OAuth ID
        user = await self.user_repository.get_by_oauth_id(provider, oauth_id)

        if user:
            # Existing OAuth user - update last login
            await self.update_last_login(user.id)
            logger.info(f"OAuth login successful for existing user: {email} ({provider})")
            return user

        # Check if email already exists (account linking scenario)
        existing_user = await self.user_repository.get_by_email(email)

        if existing_user:
            # Link OAuth account to existing user
            update_data = {}

            if provider == "github":
                update_data["github_id"] = oauth_id
            else:  # google
                update_data["google_id"] = oauth_id

            # Update avatar if user doesn't have one
            if not existing_user.avatar_url and avatar_url:
                update_data["avatar_url"] = avatar_url

            updated_user = await self.user_repository.update(existing_user.id, **update_data)
            if updated_user:
                await self.update_last_login(updated_user.id)
                logger.info(
                    f"Linked {provider} account to existing user: {email} (ID: {updated_user.id})"
                )
                return updated_user

        # Create new user with OAuth data
        # Generate unique username if needed
        base_username = username
        counter = 1
        while await self.user_repository.get_by_username(username):
            username = f"{base_username}{counter}"
            counter += 1

        user_data = {
            "email": email,
            "username": username,
            "full_name": full_name,
            "avatar_url": avatar_url,
            "is_active": True,
            "is_superuser": False,
            "password_hash": None,  # No password for OAuth-only users
        }

        if provider == "github":
            user_data["github_id"] = oauth_id
        else:  # google
            user_data["google_id"] = oauth_id

        user = await self.user_repository.create(user_data)
        logger.info(f"Created new user via {provider} OAuth: {email} (ID: {user.id})")

        return user
