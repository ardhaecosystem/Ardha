"""
Notification service for managing user notifications.

This module provides business logic for notifications including:
- Creating and sending notifications
- Checking user preferences and quiet hours
- Managing read/unread status
- Integration with WebSocket and email delivery
- Statistics and maintenance operations
"""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from ardha.core.email_service import EmailService
from ardha.core.websocket_manager import get_websocket_manager
from ardha.models.notification import Notification
from ardha.models.notification_preference import NotificationPreference
from ardha.repositories.notification_preference_repository import (
    NotificationPreferenceRepository,
)
from ardha.repositories.notification_repository import NotificationRepository
from ardha.repositories.user_repository import UserRepository

logger = logging.getLogger(__name__)


# ============= Custom Exceptions =============


class NotificationNotFoundError(Exception):
    """Raised when notification is not found."""

    pass


class InsufficientNotificationPermissionsError(Exception):
    """Raised when user lacks permissions for notification operations."""

    pass


# ============= Service Class =============


class NotificationService:
    """
    Service for notification operations.

    Handles notification creation, delivery via multiple channels
    (WebSocket, email), permission enforcement, and preference management.

    Attributes:
        db: SQLAlchemy async session
        notification_repo: Notification repository for data access
        preference_repo: NotificationPreference repository for data access
        user_repo: User repository for user data access
        ws_manager: WebSocketManager for real-time delivery
        email_service: EmailService for email delivery
    """

    def __init__(self, db: AsyncSession):
        """
        Initialize NotificationService with database session and dependencies.

        Args:
            db: SQLAlchemy async session for database operations
        """
        self.db = db
        self.notification_repo = NotificationRepository(db)
        self.preference_repo = NotificationPreferenceRepository(db)
        self.user_repo = UserRepository(db)
        self.ws_manager = get_websocket_manager()
        self.email_service = EmailService()

    # ============= Creation & Sending =============

    async def create_notification(
        self,
        user_id: UUID,
        notification_type: str,
        title: str,
        message: str,
        data: Optional[Dict[str, Any]] = None,
        link_type: Optional[str] = None,
        link_id: Optional[UUID] = None,
        expires_at: Optional[datetime] = None,
    ) -> Notification:
        """
        Create and send notification to user.

        Checks user preferences, creates notification in database,
        sends via WebSocket for real-time delivery, and queues email
        if enabled based on user's email frequency setting.

        Args:
            user_id: Target user UUID
            notification_type: Type of notification
            title: Notification title (max 200 chars)
            message: Notification message (max 1000 chars)
            data: Additional context data (optional)
            link_type: Type of linked entity (optional)
            link_id: UUID of linked entity (optional)
            expires_at: Expiration datetime (optional)

        Returns:
            Created Notification object

        Raises:
            ValueError: If invalid notification type or link type
            SQLAlchemyError: If database operation fails
        """
        try:
            # Check user preferences
            preferences = await self.preference_repo.get_or_create_default(user_id)

            # Check if notification type is enabled
            is_enabled = await self.preference_repo.is_notification_enabled(
                user_id, notification_type
            )

            if not is_enabled:
                logger.info(f"Notification type {notification_type} disabled for user {user_id}")
                # Still create notification but mark internal note
                if not data:
                    data = {}
                data["_preference_disabled"] = True

            # Check quiet hours
            in_quiet_hours = await self.preference_repo.is_in_quiet_hours(user_id)

            # Create notification in database
            notification = await self.notification_repo.create(
                {
                    "user_id": user_id,
                    "type": notification_type,
                    "title": title,
                    "message": message,
                    "data": data,
                    "link_type": link_type,
                    "link_id": link_id,
                    "expires_at": expires_at,
                }
            )

            # Send via WebSocket if enabled and not in quiet hours
            if is_enabled and not in_quiet_hours:
                await self._send_websocket_notification(notification)

            # Queue email if enabled and appropriate frequency
            if (
                is_enabled
                and preferences.email_enabled
                and not in_quiet_hours
                and preferences.email_frequency == "instant"
            ):
                await self._send_email_notification(notification)
            elif (
                is_enabled
                and preferences.email_enabled
                and preferences.email_frequency in ["daily", "weekly"]
            ):
                logger.debug(
                    f"Queuing notification {notification.id} for "
                    f"{preferences.email_frequency} digest"
                )

            logger.info(f"Created notification {notification.id} for user {user_id}")

            return notification

        except Exception as e:
            logger.error(f"Error creating notification: {e}", exc_info=True)
            raise

    async def send_notification(self, notification: Notification) -> bool:
        """
        Send existing notification via all enabled channels.

        Args:
            notification: Notification object to send

        Returns:
            True if sent via at least one channel, False otherwise
        """
        sent_any = False

        try:
            # Check preferences
            preferences = await self.preference_repo.get_or_create_default(notification.user_id)

            is_enabled = await self.preference_repo.is_notification_enabled(
                notification.user_id, notification.type
            )

            in_quiet_hours = await self.preference_repo.is_in_quiet_hours(notification.user_id)

            # Send via WebSocket
            if is_enabled and not in_quiet_hours:
                if await self._send_websocket_notification(notification):
                    sent_any = True

            # Send via email
            if (
                is_enabled
                and preferences.email_enabled
                and not in_quiet_hours
                and preferences.email_frequency == "instant"
            ):
                if await self._send_email_notification(notification):
                    sent_any = True

            return sent_any

        except Exception as e:
            logger.error(f"Error sending notification {notification.id}: {e}")
            return False

    async def bulk_create_notifications(
        self, notifications: List[Dict[str, Any]]
    ) -> List[Notification]:
        """
        Create multiple notifications efficiently.

        Args:
            notifications: List of notification data dictionaries (max 100)

        Returns:
            List of created Notification objects

        Raises:
            ValueError: If more than 100 notifications or invalid data
        """
        if len(notifications) > 100:
            raise ValueError("Cannot bulk create more than 100 notifications")

        try:
            created_notifications = await self.notification_repo.bulk_create(notifications)

            # Send via WebSocket for all enabled notifications
            for notif in created_notifications:
                try:
                    is_enabled = await self.preference_repo.is_notification_enabled(
                        notif.user_id, notif.type
                    )
                    in_quiet_hours = await self.preference_repo.is_in_quiet_hours(notif.user_id)

                    if is_enabled and not in_quiet_hours:
                        await self._send_websocket_notification(notif)

                except Exception as e:
                    logger.warning(f"Error sending notification {notif.id}: {e}")

            logger.info(f"Bulk created {len(created_notifications)} notifications")
            return created_notifications

        except Exception as e:
            logger.error(f"Error bulk creating notifications: {e}", exc_info=True)
            raise

    # ============= Management =============

    async def get_user_notifications(
        self,
        user_id: UUID,
        skip: int = 0,
        limit: int = 50,
        unread_only: bool = False,
    ) -> Dict[str, Any]:
        """
        Get user's notifications with pagination.

        Args:
            user_id: User UUID
            skip: Number of records to skip for pagination
            limit: Maximum records to return (max 100)
            unread_only: If True, return only unread notifications

        Returns:
            Dictionary with notifications list, total count, and unread count

        Raises:
            ValueError: If skip or limit are invalid
        """
        try:
            if unread_only:
                all_unread = await self.notification_repo.get_unread_by_user(user_id)
                # Apply pagination manually for unread filter
                notifications = all_unread[skip : skip + limit]
                total = len(all_unread)
            else:
                notifications = await self.notification_repo.get_by_user(user_id, skip, limit)
                # Get total count (approximate from returned list)
                total = skip + len(notifications)

            unread_count = await self.notification_repo.get_unread_count(user_id)

            return {
                "notifications": notifications,
                "total": total,
                "unread_count": unread_count,
            }

        except Exception as e:
            logger.error(f"Error getting user notifications: {e}", exc_info=True)
            raise

    async def mark_notification_read(self, notification_id: UUID, user_id: UUID) -> Notification:
        """
        Mark notification as read with permission check.

        Args:
            notification_id: Notification UUID
            user_id: User UUID (must be notification owner)

        Returns:
            Updated Notification object

        Raises:
            NotificationNotFoundError: If notification doesn't exist
            InsufficientNotificationPermissionsError: If user doesn't own notification
        """
        try:
            # Get notification
            notification = await self.notification_repo.get_by_id(notification_id)
            if not notification:
                raise NotificationNotFoundError(f"Notification {notification_id} not found")

            # Check ownership
            if notification.user_id != user_id:
                raise InsufficientNotificationPermissionsError(
                    f"User {user_id} does not own notification {notification_id}"
                )

            # Mark as read
            updated_notification = await self.notification_repo.mark_as_read(notification_id)
            if not updated_notification:
                raise NotificationNotFoundError(f"Notification {notification_id} not found")

            logger.info(f"Marked notification {notification_id} as read")
            return updated_notification

        except (NotificationNotFoundError, InsufficientNotificationPermissionsError):
            raise
        except Exception as e:
            logger.error(f"Error marking notification as read: {e}", exc_info=True)
            raise

    async def mark_all_read(self, user_id: UUID) -> int:
        """
        Mark all notifications as read for user.

        Args:
            user_id: User UUID

        Returns:
            Number of notifications marked as read
        """
        try:
            count = await self.notification_repo.mark_all_as_read(user_id)
            logger.info(f"Marked {count} notifications as read for user {user_id}")
            return count

        except Exception as e:
            logger.error(f"Error marking all notifications as read: {e}", exc_info=True)
            raise

    async def delete_notification(self, notification_id: UUID, user_id: UUID) -> None:
        """
        Delete notification with permission check.

        Args:
            notification_id: Notification UUID
            user_id: User UUID (must be notification owner)

        Raises:
            NotificationNotFoundError: If notification doesn't exist
            InsufficientNotificationPermissionsError: If user doesn't own notification
        """
        try:
            # Get notification
            notification = await self.notification_repo.get_by_id(notification_id)
            if not notification:
                raise NotificationNotFoundError(f"Notification {notification_id} not found")

            # Check ownership
            if notification.user_id != user_id:
                raise InsufficientNotificationPermissionsError(
                    f"User {user_id} does not own notification {notification_id}"
                )

            # Delete notification
            await self.notification_repo.delete(notification_id)
            logger.info(f"Deleted notification {notification_id}")

        except (NotificationNotFoundError, InsufficientNotificationPermissionsError):
            raise
        except Exception as e:
            logger.error(f"Error deleting notification: {e}", exc_info=True)
            raise

    # ============= Preferences =============

    async def get_user_preferences(self, user_id: UUID) -> NotificationPreference:
        """
        Get or create user's notification preferences.

        Args:
            user_id: User UUID

        Returns:
            NotificationPreference object with current settings
        """
        try:
            return await self.preference_repo.get_or_create_default(user_id)

        except Exception as e:
            logger.error(f"Error getting user preferences: {e}", exc_info=True)
            raise

    async def update_user_preferences(
        self, user_id: UUID, updates: Dict[str, Any]
    ) -> NotificationPreference:
        """
        Update user's notification preferences.

        Args:
            user_id: User UUID
            updates: Dictionary of fields to update

        Returns:
            Updated NotificationPreference object

        Raises:
            ValueError: If invalid preference fields provided
        """
        try:
            # Get or create preferences
            existing_prefs = await self.preference_repo.get_or_create_default(user_id)

            # Update preferences
            updated_prefs = await self.preference_repo.update(user_id, updates)
            if not updated_prefs:
                # Should not happen since we just ensured they exist
                logger.error(f"Failed to update preferences for user {user_id}")
                return existing_prefs

            logger.info(f"Updated notification preferences for user {user_id}")
            return updated_prefs

        except Exception as e:
            logger.error(f"Error updating user preferences: {e}", exc_info=True)
            raise

    # ============= Statistics =============

    async def get_notification_stats(self, user_id: UUID) -> Dict[str, Any]:
        """
        Get notification statistics for user.

        Args:
            user_id: User UUID

        Returns:
            Dictionary with notification statistics
        """
        try:
            # Get all notifications for counting
            all_notifications = await self.notification_repo.get_by_user(user_id, skip=0, limit=100)

            # Get unread count
            unread_count = await self.notification_repo.get_unread_count(user_id)

            # Count by type
            by_type: Dict[str, int] = {}
            for notif in all_notifications:
                by_type[notif.type] = by_type.get(notif.type, 0) + 1

            # Get recent notifications (last 5)
            recent_notifications = await self.notification_repo.get_by_user(
                user_id, skip=0, limit=5
            )

            return {
                "total_count": len(all_notifications),
                "unread_count": unread_count,
                "by_type": by_type,
                "recent_notifications": [
                    {
                        "id": str(notif.id),
                        "type": notif.type,
                        "title": notif.title,
                        "is_read": notif.is_read,
                        "created_at": notif.created_at.isoformat(),
                    }
                    for notif in recent_notifications
                ],
            }

        except Exception as e:
            logger.error(f"Error getting notification stats: {e}", exc_info=True)
            raise

    # ============= Maintenance =============

    async def cleanup_old_notifications(self, days: int = 30) -> int:
        """
        Delete notifications older than specified days.

        Args:
            days: Number of days (default: 30)

        Returns:
            Number of notifications deleted
        """
        try:
            count = await self.notification_repo.delete_old_notifications(days)
            logger.info(f"Cleaned up {count} old notifications (older than {days} days)")
            return count

        except Exception as e:
            logger.error(f"Error cleaning up old notifications: {e}", exc_info=True)
            raise

    async def cleanup_expired_notifications(self) -> int:
        """
        Delete expired notifications.

        Returns:
            Number of notifications deleted
        """
        try:
            count = await self.notification_repo.delete_expired_notifications()
            logger.info(f"Cleaned up {count} expired notifications")
            return count

        except Exception as e:
            logger.error(f"Error cleaning up expired notifications: {e}", exc_info=True)
            raise

    # ============= Internal Methods =============

    async def _send_websocket_notification(self, notification: Notification) -> bool:
        """
        Send notification via WebSocket for real-time delivery.

        Args:
            notification: Notification object to send

        Returns:
            True if sent successfully, False otherwise
        """
        try:
            message = {
                "type": "notification",
                "data": {
                    "id": str(notification.id),
                    "type": notification.type,
                    "title": notification.title,
                    "message": notification.message,
                    "data": notification.data,
                    "link_type": notification.link_type,
                    "link_id": str(notification.link_id) if notification.link_id else None,
                    "created_at": notification.created_at.isoformat(),
                    "is_read": notification.is_read,
                },
            }

            success = await self.ws_manager.send_personal_message(notification.user_id, message)

            if success:
                logger.debug(f"Sent WebSocket notification {notification.id}")
            else:
                logger.debug(f"User {notification.user_id} not connected via WebSocket")

            return success

        except Exception as e:
            logger.error(f"Error sending WebSocket notification {notification.id}: {e}")
            return False

    async def _send_email_notification(self, notification: Notification) -> bool:
        """
        Send notification via email.

        Args:
            notification: Notification object to send

        Returns:
            True if email sent successfully, False otherwise
        """
        try:
            # Get user for email address
            user = await self.user_repo.get_by_id(notification.user_id)
            if not user:
                logger.warning(f"User {notification.user_id} not found for email notification")
                return False

            # Send notification email
            success = await self.email_service.send_notification_email(user, notification)

            if success:
                logger.debug(f"Sent email notification {notification.id} to {user.email}")
            else:
                logger.warning(f"Failed to send email notification {notification.id}")

            return success

        except Exception as e:
            logger.error(f"Error sending email notification {notification.id}: {e}")
            return False
