"""
Repository for NotificationPreference data access operations.

This module provides data access methods for NotificationPreference entities,
including CRUD operations and specialized preference checking methods.
"""

import logging
from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ardha.models.notification_preference import NotificationPreference

logger = logging.getLogger(__name__)


class NotificationPreferenceRepository:
    """Repository for notification preference data access operations."""

    def __init__(self, db: AsyncSession):
        """
        Initialize repository with database session.

        Args:
            db: SQLAlchemy async session
        """
        self.db = db

    # ============= CRUD Operations =============

    async def create(self, preference_data: dict[str, Any]) -> NotificationPreference:
        """
        Create new notification preference.

        Args:
            preference_data: Preference data dictionary

        Returns:
            Created notification preference

        Raises:
            IntegrityError: If user_id already has preferences
        """
        try:
            preference = NotificationPreference(**preference_data)
            self.db.add(preference)
            await self.db.commit()
            await self.db.refresh(preference, ["user"])
            logger.info(f"Created notification preferences for user {preference.user_id}")
            return preference
        except IntegrityError as e:
            await self.db.rollback()
            logger.error(f"Failed to create preferences (likely duplicate): {e}")
            raise
        except SQLAlchemyError as e:
            await self.db.rollback()
            logger.error(f"Database error creating preferences: {e}")
            raise

    async def get_by_user(self, user_id: UUID) -> NotificationPreference | None:
        """
        Get notification preferences for user.

        Args:
            user_id: User UUID

        Returns:
            Notification preference if found, None otherwise
        """
        try:
            stmt = (
                select(NotificationPreference)
                .where(NotificationPreference.user_id == user_id)
                .options(selectinload(NotificationPreference.user))
            )
            result = await self.db.execute(stmt)
            return result.scalar_one_or_none()
        except SQLAlchemyError as e:
            logger.error(f"Database error fetching preferences for user {user_id}: {e}")
            return None

    async def update(self, user_id: UUID, updates: dict[str, Any]) -> NotificationPreference | None:
        """
        Update notification preferences for user.

        Args:
            user_id: User UUID
            updates: Dictionary of fields to update

        Returns:
            Updated preferences if found, None otherwise
        """
        try:
            preference = await self.get_by_user(user_id)
            if not preference:
                return None

            for key, value in updates.items():
                if hasattr(preference, key):
                    setattr(preference, key, value)

            await self.db.commit()
            await self.db.refresh(preference, ["user"])
            logger.info(f"Updated notification preferences for user {user_id}")
            return preference
        except SQLAlchemyError as e:
            await self.db.rollback()
            logger.error(f"Database error updating preferences: {e}")
            raise

    async def delete(self, user_id: UUID) -> None:
        """
        Delete notification preferences for user.

        Args:
            user_id: User UUID
        """
        try:
            stmt = delete(NotificationPreference).where(NotificationPreference.user_id == user_id)
            await self.db.execute(stmt)
            await self.db.commit()
            logger.info(f"Deleted notification preferences for user {user_id}")
        except SQLAlchemyError as e:
            await self.db.rollback()
            logger.error(f"Database error deleting preferences: {e}")
            raise

    # ============= Specialized Methods =============

    async def get_or_create_default(self, user_id: UUID) -> NotificationPreference:
        """
        Get existing preferences or create with defaults.

        Args:
            user_id: User UUID

        Returns:
            Existing or newly created notification preference
        """
        try:
            # Try to get existing preferences
            preference = await self.get_by_user(user_id)
            if preference:
                return preference

            # Create default preferences
            default_data = {
                "user_id": user_id,
                "email_enabled": True,
                "push_enabled": True,
                "task_assigned": True,
                "task_completed": True,
                "task_overdue": True,
                "mentions": True,
                "project_invites": True,
                "database_updates": False,
                "system_notifications": True,
                "email_frequency": "instant",
            }
            return await self.create(default_data)
        except IntegrityError:
            # Race condition: another process created preferences
            # Fetch and return the newly created one
            preference = await self.get_by_user(user_id)
            if preference:
                return preference
            raise

    async def is_notification_enabled(self, user_id: UUID, notification_type: str) -> bool:
        """
        Check if specific notification type is enabled for user.

        Args:
            user_id: User UUID
            notification_type: Type to check

        Returns:
            True if enabled, False otherwise (defaults to True if no prefs)
        """
        try:
            preference = await self.get_by_user(user_id)
            if not preference:
                return True  # Default: enabled if no preferences set

            return preference.is_enabled(notification_type)
        except SQLAlchemyError as e:
            logger.error(f"Database error checking notification enabled status: {e}")
            return True  # Fail open: send notification on error

    async def is_in_quiet_hours(self, user_id: UUID, check_time: datetime | None = None) -> bool:
        """
        Check if user is currently in quiet hours.

        Args:
            user_id: User UUID
            check_time: Time to check (defaults to now)

        Returns:
            True if in quiet hours, False otherwise
        """
        try:
            preference = await self.get_by_user(user_id)
            if not preference:
                return False  # No quiet hours if no preferences

            return preference.is_quiet_hours(check_time)
        except SQLAlchemyError as e:
            logger.error(f"Database error checking quiet hours: {e}")
            return False  # Fail open: allow notifications on error

    async def get_email_frequency(self, user_id: UUID) -> str:
        """
        Get email frequency setting for user.

        Args:
            user_id: User UUID

        Returns:
            Email frequency: 'instant', 'daily', 'weekly', or 'never'
            Defaults to 'instant' if no preferences found
        """
        try:
            preference = await self.get_by_user(user_id)
            if not preference:
                return "instant"  # Default frequency

            return preference.email_frequency
        except SQLAlchemyError as e:
            logger.error(f"Database error getting email frequency: {e}")
            return "instant"  # Default on error
