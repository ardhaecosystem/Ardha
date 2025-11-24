"""
Broadcast service for multi-user notifications.

This module provides high-level notification broadcasting to groups:
- Project member notifications
- Task assignee notifications
- System-wide announcements
- Mention notifications
"""

import logging
from typing import Any, List, Optional
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from ardha.models.notification import Notification
from ardha.repositories.project_repository import ProjectRepository
from ardha.repositories.task_repository import TaskRepository
from ardha.repositories.user_repository import UserRepository
from ardha.services.notification_service import NotificationService

logger = logging.getLogger(__name__)


class BroadcastService:
    """
    Service for broadcasting notifications to multiple users.

    Provides convenience methods for common notification patterns
    like notifying all project members or task assignees.

    Attributes:
        db: SQLAlchemy async session
        notification_service: NotificationService for creating notifications
        project_repo: ProjectRepository for project member queries
        task_repo: TaskRepository for task assignee queries
        user_repo: UserRepository for user data access
    """

    def __init__(self, db: AsyncSession):
        """
        Initialize BroadcastService with database session.

        Args:
            db: SQLAlchemy async session for database operations
        """
        self.db = db
        self.notification_service = NotificationService(db)
        self.project_repo = ProjectRepository(db)
        self.task_repo = TaskRepository(db)
        self.user_repo = UserRepository(db)

    async def notify_user(
        self,
        user_id: UUID,
        notification_type: str,
        title: str,
        message: str,
        **kwargs: Any,
    ) -> Notification:
        """
        Send notification to single user.

        Convenience wrapper around NotificationService.create_notification()
        for consistent API across broadcast methods.

        Args:
            user_id: User UUID to notify
            notification_type: Type of notification
            title: Notification title
            message: Notification message
            **kwargs: Additional arguments (data, link_type, link_id, expires_at)

        Returns:
            Created Notification object

        Raises:
            ValueError: If invalid notification type or parameters
        """
        return await self.notification_service.create_notification(
            user_id=user_id,
            notification_type=notification_type,
            title=title,
            message=message,
            data=kwargs.get("data"),
            link_type=kwargs.get("link_type"),
            link_id=kwargs.get("link_id"),
            expires_at=kwargs.get("expires_at"),
        )

    async def notify_project_members(
        self,
        project_id: UUID,
        notification_type: str,
        title: str,
        message: str,
        exclude_user: Optional[UUID] = None,
        **kwargs: Any,
    ) -> List[Notification]:
        """
        Send notification to all project members.

        Excludes the specified user (usually the user who triggered the action).
        Each member receives an individual notification that respects their
        personal preferences and quiet hours.

        Args:
            project_id: Project UUID
            notification_type: Type of notification
            title: Notification title
            message: Notification message
            exclude_user: User UUID to exclude from notification (optional)
            **kwargs: Additional arguments (data, link_type, link_id, expires_at)

        Returns:
            List of created Notification objects

        Raises:
            ValueError: If project not found or invalid parameters
        """
        try:
            # Get all project members
            members = await self.project_repo.get_project_members(project_id)

            if not members:
                logger.warning(f"No members found for project {project_id}")
                return []

            # Filter out excluded user
            target_members = [m for m in members if m.user_id != exclude_user]

            if not target_members:
                logger.debug(f"No members to notify for project {project_id} after exclusion")
                return []

            # Create notifications for each member
            notifications: List[Notification] = []
            for member in target_members:
                try:
                    notif = await self.notification_service.create_notification(
                        user_id=member.user_id,
                        notification_type=notification_type,
                        title=title,
                        message=message,
                        data=kwargs.get("data"),
                        link_type=kwargs.get("link_type", "project"),
                        link_id=kwargs.get("link_id", project_id),
                        expires_at=kwargs.get("expires_at"),
                    )
                    notifications.append(notif)

                except Exception as e:
                    logger.warning(f"Failed to notify project member {member.user_id}: {e}")

            logger.info(
                f"Broadcast notification to {len(notifications)} project members "
                f"(project {project_id})"
            )

            return notifications

        except Exception as e:
            logger.error(f"Error broadcasting to project members: {e}", exc_info=True)
            raise

    async def notify_task_assignees(
        self,
        task_id: UUID,
        notification_type: str,
        title: str,
        message: str,
        exclude_user: Optional[UUID] = None,
        **kwargs: Any,
    ) -> List[Notification]:
        """
        Send notification to task assignees.

        Args:
            task_id: Task UUID
            notification_type: Type of notification
            title: Notification title
            message: Notification message
            exclude_user: User UUID to exclude from notification (optional)
            **kwargs: Additional arguments (data, link_type, link_id, expires_at)

        Returns:
            List of created Notification objects

        Raises:
            ValueError: If task not found or invalid parameters
        """
        try:
            # Get task
            task = await self.task_repo.get_by_id(task_id)
            if not task:
                logger.warning(f"Task {task_id} not found for assignee notification")
                return []

            # Get assignee(s)
            assignees: List[UUID] = []
            if task.assignee_id and task.assignee_id != exclude_user:
                assignees.append(task.assignee_id)

            if not assignees:
                logger.debug(f"No assignees to notify for task {task_id}")
                return []

            # Create notifications for each assignee
            notifications: List[Notification] = []
            for assignee_id in assignees:
                try:
                    notif = await self.notification_service.create_notification(
                        user_id=assignee_id,
                        notification_type=notification_type,
                        title=title,
                        message=message,
                        data=kwargs.get("data"),
                        link_type=kwargs.get("link_type", "task"),
                        link_id=kwargs.get("link_id", task_id),
                        expires_at=kwargs.get("expires_at"),
                    )
                    notifications.append(notif)

                except Exception as e:
                    logger.warning(f"Failed to notify task assignee {assignee_id}: {e}")

            logger.info(
                f"Broadcast notification to {len(notifications)} task assignees "
                f"(task {task_id})"
            )

            return notifications

        except Exception as e:
            logger.error(f"Error broadcasting to task assignees: {e}", exc_info=True)
            raise

    async def broadcast_system_notification(
        self,
        title: str,
        message: str,
        user_ids: Optional[List[UUID]] = None,
    ) -> List[Notification]:
        """
        Broadcast system notification to users.

        If user_ids is None, sends to all active users. System notifications
        are always of type "system" and typically for maintenance announcements,
        security alerts, or important updates.

        Args:
            title: Notification title
            message: Notification message
            user_ids: Optional list of user UUIDs (if None, broadcast to all)

        Returns:
            List of created Notification objects
        """
        try:
            # Get target users
            if user_ids is None:
                # Get all active users
                all_users = await self.user_repo.list_users(
                    skip=0, limit=10000, include_inactive=False
                )
                user_ids = [user.id for user in all_users]

            if not user_ids:
                logger.warning("No users found for system broadcast")
                return []

            # Create notifications for each user
            notifications: List[Notification] = []
            for user_id in user_ids:
                try:
                    notif = await self.notification_service.create_notification(
                        user_id=user_id,
                        notification_type="system",
                        title=title,
                        message=message,
                    )
                    notifications.append(notif)

                except Exception as e:
                    logger.warning(f"Failed to notify user {user_id}: {e}")

            logger.info(f"Broadcast system notification to {len(notifications)} users")

            return notifications

        except Exception as e:
            logger.error(f"Error broadcasting system notification: {e}", exc_info=True)
            raise

    async def notify_mention(
        self,
        mentioned_user_id: UUID,
        mentioning_user_id: UUID,
        context: str,
        link_type: str,
        link_id: UUID,
    ) -> Notification:
        """
        Send notification for user mention.

        When a user is mentioned in a comment, chat message, or other context,
        this creates a personalized mention notification.

        Args:
            mentioned_user_id: UUID of user who was mentioned
            mentioning_user_id: UUID of user who mentioned them
            context: Context where mention occurred (e.g., "in a task comment")
            link_type: Type of entity where mention occurred (task, project, chat, etc.)
            link_id: UUID of entity where mention occurred

        Returns:
            Created Notification object

        Example:
            "@john please review this task" in a task comment would trigger:
            notify_mention(
                mentioned_user_id=john_id,
                mentioning_user_id=current_user_id,
                context="in a task comment",
                link_type="task",
                link_id=task_id,
            )
        """
        try:
            # Get mentioning user's name for personalized message
            mentioning_user = await self.user_repo.get_by_id(mentioning_user_id)
            mentioning_name = "Someone"
            if mentioning_user:
                mentioning_name = mentioning_user.full_name or mentioning_user.username

            # Create mention notification
            notification = await self.notification_service.create_notification(
                user_id=mentioned_user_id,
                notification_type="mention",
                title=f"{mentioning_name} mentioned you",
                message=f"{mentioning_name} mentioned you {context}",
                link_type=link_type,
                link_id=link_id,
                data={
                    "mentioning_user_id": str(mentioning_user_id),
                    "mentioning_user_name": mentioning_name,
                    "context": context,
                },
            )

            logger.info(
                f"Created mention notification for user {mentioned_user_id} "
                f"from user {mentioning_user_id}"
            )

            return notification

        except Exception as e:
            logger.error(f"Error creating mention notification: {e}", exc_info=True)
            raise
