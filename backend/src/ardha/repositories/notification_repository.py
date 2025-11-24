"""
Repository for Notification data access operations.

This module provides data access methods for Notification entities,
including CRUD operations, filtering, bulk operations, and maintenance tasks.
"""

import logging
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID

from sqlalchemy import and_, delete, func, or_, select, update
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ardha.models.notification import Notification

logger = logging.getLogger(__name__)


class NotificationRepository:
    """Repository for notification data access operations."""

    def __init__(self, db: AsyncSession):
        """
        Initialize repository with database session.

        Args:
            db: SQLAlchemy async session
        """
        self.db = db

    # ============= CRUD Operations =============

    async def create(self, notification_data: dict[str, Any]) -> Notification:
        """
        Create new notification.

        Args:
            notification_data: Notification data dictionary

        Returns:
            Created notification

        Raises:
            IntegrityError: If user_id foreign key constraint fails
        """
        try:
            notification = Notification(**notification_data)
            self.db.add(notification)
            await self.db.commit()
            await self.db.refresh(notification, ["user"])
            logger.info(
                f"Created notification {notification.id} " f"for user {notification.user_id}"
            )
            return notification
        except IntegrityError as e:
            await self.db.rollback()
            logger.error(f"Failed to create notification: {e}")
            raise
        except SQLAlchemyError as e:
            await self.db.rollback()
            logger.error(f"Database error creating notification: {e}")
            raise

    async def get_by_id(self, notification_id: UUID) -> Notification | None:
        """
        Get notification by ID with eager loading.

        Args:
            notification_id: Notification UUID

        Returns:
            Notification if found, None otherwise
        """
        try:
            stmt = (
                select(Notification)
                .where(Notification.id == notification_id)
                .options(selectinload(Notification.user))
            )
            result = await self.db.execute(stmt)
            return result.scalar_one_or_none()
        except SQLAlchemyError as e:
            logger.error(f"Database error fetching notification {notification_id}: {e}")
            return None

    async def get_by_user(
        self,
        user_id: UUID,
        skip: int = 0,
        limit: int = 50,
    ) -> list[Notification]:
        """
        Get notifications for user with pagination.

        Args:
            user_id: User UUID
            skip: Number of records to skip
            limit: Maximum records to return (max 100)

        Returns:
            List of notifications ordered by created_at desc

        Raises:
            ValueError: If skip < 0 or limit > 100
        """
        if skip < 0:
            raise ValueError("skip must be >= 0")
        if limit < 1 or limit > 100:
            raise ValueError("limit must be between 1 and 100")

        try:
            stmt = (
                select(Notification)
                .where(Notification.user_id == user_id)
                .order_by(Notification.created_at.desc())
                .offset(skip)
                .limit(limit)
                .options(selectinload(Notification.user))
            )
            result = await self.db.execute(stmt)
            return list(result.scalars().all())
        except SQLAlchemyError as e:
            logger.error(f"Database error fetching user notifications: {e}")
            return []

    async def update(self, notification_id: UUID, updates: dict[str, Any]) -> Notification | None:
        """
        Update notification fields.

        Args:
            notification_id: Notification UUID
            updates: Dictionary of fields to update

        Returns:
            Updated notification if found, None otherwise
        """
        try:
            notification = await self.get_by_id(notification_id)
            if not notification:
                return None

            for key, value in updates.items():
                if hasattr(notification, key):
                    setattr(notification, key, value)

            await self.db.commit()
            await self.db.refresh(notification, ["user"])
            logger.info(f"Updated notification {notification_id}")
            return notification
        except SQLAlchemyError as e:
            await self.db.rollback()
            logger.error(f"Database error updating notification: {e}")
            raise

    async def delete(self, notification_id: UUID) -> None:
        """
        Hard delete notification.

        Args:
            notification_id: Notification UUID to delete
        """
        try:
            stmt = delete(Notification).where(Notification.id == notification_id)
            await self.db.execute(stmt)
            await self.db.commit()
            logger.info(f"Deleted notification {notification_id}")
        except SQLAlchemyError as e:
            await self.db.rollback()
            logger.error(f"Database error deleting notification: {e}")
            raise

    # ============= Specialized Queries =============

    async def get_unread_by_user(self, user_id: UUID) -> list[Notification]:
        """
        Get all unread notifications for user.

        Args:
            user_id: User UUID

        Returns:
            List of unread notifications ordered by created_at desc
        """
        try:
            stmt = (
                select(Notification)
                .where(
                    and_(
                        Notification.user_id == user_id,
                        Notification.is_read.is_(False),
                    )
                )
                .order_by(Notification.created_at.desc())
                .options(selectinload(Notification.user))
            )
            result = await self.db.execute(stmt)
            return list(result.scalars().all())
        except SQLAlchemyError as e:
            logger.error(f"Database error fetching unread notifications: {e}")
            return []

    async def get_unread_count(self, user_id: UUID) -> int:
        """
        Get count of unread notifications for user.

        Args:
            user_id: User UUID

        Returns:
            Count of unread notifications
        """
        try:
            stmt = select(func.count(Notification.id)).where(
                and_(
                    Notification.user_id == user_id,
                    Notification.is_read.is_(False),
                )
            )
            result = await self.db.execute(stmt)
            return result.scalar() or 0
        except SQLAlchemyError as e:
            logger.error(f"Database error counting unread notifications: {e}")
            return 0

    async def mark_as_read(self, notification_id: UUID) -> Notification | None:
        """
        Mark notification as read with timestamp.

        Args:
            notification_id: Notification UUID

        Returns:
            Updated notification if found, None otherwise
        """
        try:
            notification = await self.get_by_id(notification_id)
            if not notification:
                return None

            notification.mark_as_read()  # Uses helper method from model
            await self.db.commit()
            await self.db.refresh(notification, ["user"])
            logger.info(f"Marked notification {notification_id} as read")
            return notification
        except SQLAlchemyError as e:
            await self.db.rollback()
            logger.error(f"Database error marking notification as read: {e}")
            raise

    async def mark_all_as_read(self, user_id: UUID) -> int:
        """
        Mark all notifications as read for user.

        Args:
            user_id: User UUID

        Returns:
            Number of notifications marked as read
        """
        try:
            now = datetime.now(UTC)
            stmt = (
                update(Notification)
                .where(
                    and_(
                        Notification.user_id == user_id,
                        Notification.is_read.is_(False),
                    )
                )
                .values(is_read=True, read_at=now)
            )
            result = await self.db.execute(stmt)
            await self.db.commit()
            count = result.rowcount or 0
            logger.info(f"Marked {count} notifications as read for user {user_id}")
            return count
        except SQLAlchemyError as e:
            await self.db.rollback()
            logger.error(f"Database error marking all as read: {e}")
            raise

    async def bulk_create(self, notifications: list[dict[str, Any]]) -> list[Notification]:
        """
        Create multiple notifications in batch.

        Args:
            notifications: List of notification data dictionaries (max 100)

        Returns:
            List of created notifications

        Raises:
            ValueError: If more than 100 notifications provided
        """
        if len(notifications) > 100:
            raise ValueError("Cannot bulk create more than 100 notifications")

        try:
            notification_objects = [Notification(**data) for data in notifications]
            self.db.add_all(notification_objects)
            await self.db.commit()

            # Refresh all with user relationship
            for notif in notification_objects:
                await self.db.refresh(notif, ["user"])

            logger.info(f"Bulk created {len(notification_objects)} notifications")
            return notification_objects
        except IntegrityError as e:
            await self.db.rollback()
            logger.error(f"Failed to bulk create notifications: {e}")
            raise
        except SQLAlchemyError as e:
            await self.db.rollback()
            logger.error(f"Database error in bulk create: {e}")
            raise

    # ============= Maintenance Operations =============

    async def delete_old_notifications(self, days: int = 30) -> int:
        """
        Delete notifications older than specified days.

        Args:
            days: Number of days (default: 30)

        Returns:
            Number of notifications deleted
        """
        try:
            cutoff_date = datetime.now(UTC) - timedelta(days=days)
            stmt = delete(Notification).where(Notification.created_at < cutoff_date)
            result = await self.db.execute(stmt)
            await self.db.commit()
            count = result.rowcount or 0
            logger.info(f"Deleted {count} old notifications (older than {days} days)")
            return count
        except SQLAlchemyError as e:
            await self.db.rollback()
            logger.error(f"Database error deleting old notifications: {e}")
            raise

    async def delete_expired_notifications(self) -> int:
        """
        Delete expired notifications based on expires_at field.

        Returns:
            Number of notifications deleted
        """
        try:
            now = datetime.now(UTC)
            stmt = delete(Notification).where(
                and_(
                    Notification.expires_at.isnot(None),
                    Notification.expires_at < now,
                )
            )
            result = await self.db.execute(stmt)
            await self.db.commit()
            count = result.rowcount or 0
            logger.info(f"Deleted {count} expired notifications")
            return count
        except SQLAlchemyError as e:
            await self.db.rollback()
            logger.error(f"Database error deleting expired notifications: {e}")
            raise

    async def get_by_link(self, link_type: str, link_id: UUID) -> list[Notification]:
        """
        Get notifications linked to specific entity.

        Args:
            link_type: Type of linked entity (task, project, database, chat)
            link_id: UUID of linked entity

        Returns:
            List of notifications for the linked entity
        """
        try:
            stmt = (
                select(Notification)
                .where(
                    and_(
                        Notification.link_type == link_type,
                        Notification.link_id == link_id,
                    )
                )
                .order_by(Notification.created_at.desc())
                .options(selectinload(Notification.user))
            )
            result = await self.db.execute(stmt)
            return list(result.scalars().all())
        except SQLAlchemyError as e:
            logger.error(f"Database error fetching notifications by link: {e}")
            return []

    async def get_recent_by_type(
        self,
        user_id: UUID,
        notification_type: str,
        limit: int = 10,
    ) -> list[Notification]:
        """
        Get recent notifications of specific type for user.

        Args:
            user_id: User UUID
            notification_type: Notification type to filter
            limit: Maximum records to return (max 100)

        Returns:
            List of notifications ordered by created_at desc

        Raises:
            ValueError: If limit > 100
        """
        if limit < 1 or limit > 100:
            raise ValueError("limit must be between 1 and 100")

        try:
            stmt = (
                select(Notification)
                .where(
                    and_(
                        Notification.user_id == user_id,
                        Notification.type == notification_type,
                    )
                )
                .order_by(Notification.created_at.desc())
                .limit(limit)
                .options(selectinload(Notification.user))
            )
            result = await self.db.execute(stmt)
            return list(result.scalars().all())
        except SQLAlchemyError as e:
            logger.error(f"Database error fetching notifications by type: {e}")
            return []

    async def search_notifications(self, user_id: UUID, query: str) -> list[Notification]:
        """
        Search notifications by title or message content.

        Args:
            user_id: User UUID
            query: Search query string

        Returns:
            List of matching notifications ordered by created_at desc
        """
        if not query or not query.strip():
            return []

        try:
            search_pattern = f"%{query.strip()}%"
            stmt = (
                select(Notification)
                .where(
                    and_(
                        Notification.user_id == user_id,
                        or_(
                            Notification.title.ilike(search_pattern),
                            Notification.message.ilike(search_pattern),
                        ),
                    )
                )
                .order_by(Notification.created_at.desc())
                .limit(100)
                .options(selectinload(Notification.user))
            )
            result = await self.db.execute(stmt)
            return list(result.scalars().all())
        except SQLAlchemyError as e:
            logger.error(f"Database error searching notifications: {e}")
            return []
