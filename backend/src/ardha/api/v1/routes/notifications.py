"""
Notification API routes.

This module provides REST API endpoints for notification management including:
- Listing notifications with pagination and filtering
- Marking notifications as read (single and bulk)
- Deleting notifications
- Notification statistics
- Notification preference management
"""

import logging
from typing import Any, Dict
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from ardha.core.database import get_db
from ardha.core.security import get_current_user
from ardha.models.user import User
from ardha.schemas.requests.notification import (
    NotificationPreferenceUpdateRequest,
)
from ardha.schemas.responses.notification import (
    NotificationListResponse,
    NotificationPreferenceResponse,
    NotificationResponse,
    NotificationStatsResponse,
)
from ardha.services.notification_service import (
    InsufficientNotificationPermissionsError,
    NotificationNotFoundError,
    NotificationService,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/notifications", tags=["notifications"])


# ============= Notification Management Endpoints =============


@router.get(
    "",
    response_model=NotificationListResponse,
    summary="List notifications",
    description="Get current user's notifications with pagination and filtering.",
)
async def list_notifications(
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(50, ge=1, le=100, description="Maximum records to return"),
    unread_only: bool = Query(False, description="Filter to unread notifications only"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> NotificationListResponse:
    """
    Get current user's notifications with pagination.

    Args:
        skip: Number of records to skip for pagination
        limit: Maximum records to return (max 100)
        unread_only: If True, return only unread notifications
        current_user: Authenticated user from JWT token
        db: Database session

    Returns:
        Paginated notification list with stats
    """
    service = NotificationService(db)

    try:
        result = await service.get_user_notifications(
            user_id=current_user.id,
            skip=skip,
            limit=limit,
            unread_only=unread_only,
        )

        # Build response
        return NotificationListResponse(
            notifications=[
                NotificationResponse(
                    id=n.id,
                    user_id=n.user_id,
                    type=n.type,
                    title=n.title,
                    message=n.message,
                    data=n.data,
                    link_type=n.link_type,
                    link_id=n.link_id,
                    is_read=n.is_read,
                    read_at=n.read_at,
                    created_at=n.created_at,
                    expires_at=n.expires_at,
                )
                for n in result["notifications"]
            ],
            total=result["total"],
            unread_count=result["unread_count"],
            page=skip // limit + 1,
            page_size=limit,
        )

    except Exception as e:
        logger.error(f"Error listing notifications: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to list notifications",
        )


@router.patch(
    "/{notification_id}/read",
    response_model=NotificationResponse,
    summary="Mark notification as read",
    description="Mark a specific notification as read.",
)
async def mark_notification_read(
    notification_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> NotificationResponse:
    """
    Mark notification as read.

    Args:
        notification_id: Notification UUID
        current_user: Authenticated user from JWT token
        db: Database session

    Returns:
        Updated notification with read_at timestamp

    Raises:
        404: Notification not found
        403: Not user's notification
    """
    service = NotificationService(db)

    try:
        notification = await service.mark_notification_read(
            notification_id=notification_id,
            user_id=current_user.id,
        )

        return NotificationResponse(
            id=notification.id,
            user_id=notification.user_id,
            type=notification.type,
            title=notification.title,
            message=notification.message,
            data=notification.data,
            link_type=notification.link_type,
            link_id=notification.link_id,
            is_read=notification.is_read,
            read_at=notification.read_at,
            created_at=notification.created_at,
            expires_at=notification.expires_at,
        )

    except NotificationNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except InsufficientNotificationPermissionsError as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e),
        )


@router.post(
    "/mark-all-read",
    summary="Mark all notifications as read",
    description="Mark all user's notifications as read.",
)
async def mark_all_notifications_read(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """
    Mark all user's notifications as read.

    Args:
        current_user: Authenticated user from JWT token
        db: Database session

    Returns:
        Dictionary with count of notifications marked as read
    """
    service = NotificationService(db)

    try:
        marked_count = await service.mark_all_read(user_id=current_user.id)

        return {
            "marked_count": marked_count,
            "message": f"Marked {marked_count} notifications as read",
        }

    except Exception as e:
        logger.error(f"Error marking all notifications as read: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to mark all notifications as read",
        )


@router.delete(
    "/{notification_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete notification",
    description="Delete a specific notification.",
)
async def delete_notification(
    notification_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    """
    Delete notification.

    Args:
        notification_id: Notification UUID
        current_user: Authenticated user from JWT token
        db: Database session

    Returns:
        204 No Content on success

    Raises:
        404: Notification not found
        403: Not user's notification
    """
    service = NotificationService(db)

    try:
        await service.delete_notification(
            notification_id=notification_id,
            user_id=current_user.id,
        )

    except NotificationNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except InsufficientNotificationPermissionsError as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e),
        )


@router.get(
    "/stats",
    response_model=NotificationStatsResponse,
    summary="Get notification statistics",
    description="Get notification statistics for current user.",
)
async def get_notification_stats(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> NotificationStatsResponse:
    """
    Get notification statistics.

    Args:
        current_user: Authenticated user from JWT token
        db: Database session

    Returns:
        Notification statistics including counts and recent notifications
    """
    service = NotificationService(db)

    try:
        stats = await service.get_notification_stats(user_id=current_user.id)

        # Convert recent notifications to NotificationResponse objects
        recent_notifications = []
        for notif_data in stats["recent_notifications"]:
            # Get full notification from database for complete data
            from ardha.repositories.notification_repository import (
                NotificationRepository,
            )

            repo = NotificationRepository(db)
            notif = await repo.get_by_id(UUID(notif_data["id"]))
            if notif:
                recent_notifications.append(
                    NotificationResponse(
                        id=notif.id,
                        user_id=notif.user_id,
                        type=notif.type,
                        title=notif.title,
                        message=notif.message,
                        data=notif.data,
                        link_type=notif.link_type,
                        link_id=notif.link_id,
                        is_read=notif.is_read,
                        read_at=notif.read_at,
                        created_at=notif.created_at,
                        expires_at=notif.expires_at,
                    )
                )

        return NotificationStatsResponse(
            total_count=stats["total_count"],
            unread_count=stats["unread_count"],
            by_type=stats["by_type"],
            recent_notifications=recent_notifications,
        )

    except Exception as e:
        logger.error(f"Error getting notification stats: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get notification statistics",
        )


# ============= Preference Management Endpoints =============


@router.get(
    "/preferences",
    response_model=NotificationPreferenceResponse,
    summary="Get notification preferences",
    description="Get current user's notification preferences (creates default if not exists).",
)
async def get_notification_preferences(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> NotificationPreferenceResponse:
    """
    Get current user's notification preferences.

    Auto-creates default preferences if they don't exist yet.

    Args:
        current_user: Authenticated user from JWT token
        db: Database session

    Returns:
        User's notification preferences
    """
    service = NotificationService(db)

    try:
        preferences = await service.get_user_preferences(user_id=current_user.id)

        return NotificationPreferenceResponse(
            id=preferences.id,
            user_id=preferences.user_id,
            email_enabled=preferences.email_enabled,
            push_enabled=preferences.push_enabled,
            task_assigned=preferences.task_assigned,
            task_completed=preferences.task_completed,
            task_overdue=preferences.task_overdue,
            mentions=preferences.mentions,
            project_invites=preferences.project_invites,
            database_updates=preferences.database_updates,
            system_notifications=preferences.system_notifications,
            email_frequency=preferences.email_frequency,
            quiet_hours_start=preferences.quiet_hours_start,
            quiet_hours_end=preferences.quiet_hours_end,
            created_at=preferences.created_at,
            updated_at=preferences.updated_at,
        )

    except Exception as e:
        logger.error(f"Error getting notification preferences: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get notification preferences",
        )


@router.patch(
    "/preferences",
    response_model=NotificationPreferenceResponse,
    summary="Update notification preferences",
    description="Update current user's notification preferences (partial update).",
)
async def update_notification_preferences(
    updates: NotificationPreferenceUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> NotificationPreferenceResponse:
    """
    Update notification preferences.

    All fields are optional - only provided fields will be updated.

    Args:
        updates: Preference fields to update
        current_user: Authenticated user from JWT token
        db: Database session

    Returns:
        Updated notification preferences
    """
    service = NotificationService(db)

    try:
        # Convert request to dict, excluding None values
        update_dict = updates.model_dump(exclude_none=True)

        if not update_dict:
            # No changes, just return current preferences
            preferences = await service.get_user_preferences(user_id=current_user.id)
        else:
            # Update preferences
            preferences = await service.update_user_preferences(
                user_id=current_user.id,
                updates=update_dict,
            )

        return NotificationPreferenceResponse(
            id=preferences.id,
            user_id=preferences.user_id,
            email_enabled=preferences.email_enabled,
            push_enabled=preferences.push_enabled,
            task_assigned=preferences.task_assigned,
            task_completed=preferences.task_completed,
            task_overdue=preferences.task_overdue,
            mentions=preferences.mentions,
            project_invites=preferences.project_invites,
            database_updates=preferences.database_updates,
            system_notifications=preferences.system_notifications,
            email_frequency=preferences.email_frequency,
            quiet_hours_start=preferences.quiet_hours_start,
            quiet_hours_end=preferences.quiet_hours_end,
            created_at=preferences.created_at,
            updated_at=preferences.updated_at,
        )

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except Exception as e:
        logger.error(f"Error updating notification preferences: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update notification preferences",
        )
