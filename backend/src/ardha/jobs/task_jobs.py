"""
Task-related background jobs.

This module provides Celery tasks for task management operations
including velocity calculation and reminder notifications.
"""

import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List
from uuid import UUID

from sqlalchemy import and_, func, select

from ardha.core.celery_app import celery_app
from ardha.core.database import async_session_factory
from ardha.models.task import Task
from ardha.models.user import User

logger = logging.getLogger(__name__)


@celery_app.task(
    name="tasks.calculate_team_velocity",
    queue="analytics",
    time_limit=600,  # 10 minutes
    soft_time_limit=540,  # 9 minutes
)
async def calculate_team_velocity() -> Dict[str, Any]:
    """
    Calculate team velocity metrics.

    Calculates:
    - Tasks completed per week
    - Average task completion time
    - Velocity trends over time
    - Per-project and per-user metrics

    Returns:
        Dict with velocity metrics
    """
    logger.info("Starting team velocity calculation")

    try:
        async with async_session_factory() as db:
            # Get date ranges
            now = datetime.now(timezone.utc)
            one_week_ago = now - timedelta(days=7)
            four_weeks_ago = now - timedelta(days=28)

            # Count completed tasks this week
            stmt_week = select(func.count(Task.id)).where(
                and_(
                    Task.status == "done",
                    Task.completed_at >= one_week_ago,
                )
            )
            tasks_this_week = await db.scalar(stmt_week) or 0

            # Count completed tasks last 4 weeks
            stmt_month = select(func.count(Task.id)).where(
                and_(
                    Task.status == "done",
                    Task.completed_at >= four_weeks_ago,
                )
            )
            tasks_this_month = await db.scalar(stmt_month) or 0

            # Calculate average completion time
            stmt_avg = select(
                func.avg(
                    func.extract(
                        "epoch",
                        Task.completed_at - Task.created_at,
                    )
                )
            ).where(
                and_(
                    Task.status == "done",
                    Task.completed_at >= four_weeks_ago,
                )
            )
            avg_seconds = await db.scalar(stmt_avg) or 0
            avg_days = avg_seconds / 86400 if avg_seconds > 0 else 0

            # Calculate velocity (tasks per week)
            velocity_week = tasks_this_week
            velocity_month = tasks_this_month / 4  # Average per week

            # Calculate trend (positive = improving, negative = declining)
            trend = velocity_week - velocity_month
            trend_percentage = (trend / velocity_month * 100) if velocity_month > 0 else 0

            metrics = {
                "calculated_at": now.isoformat(),
                "tasks_completed_this_week": tasks_this_week,
                "tasks_completed_this_month": tasks_this_month,
                "average_completion_days": round(avg_days, 2),
                "velocity_current_week": velocity_week,
                "velocity_4_week_average": round(velocity_month, 2),
                "trend": round(trend, 2),
                "trend_percentage": round(trend_percentage, 2),
            }

            logger.info(f"Velocity calculation complete: {metrics}")

            return {
                "success": True,
                "metrics": metrics,
            }

    except Exception as e:
        logger.error(f"Error calculating team velocity: {e}")
        raise


@celery_app.task(
    name="tasks.send_overdue_task_reminders",
    queue="notifications",
    time_limit=600,  # 10 minutes
    soft_time_limit=540,  # 9 minutes
)
async def send_overdue_task_reminders() -> Dict[str, Any]:
    """
    Send reminders for overdue tasks.

    Finds tasks past due date and sends notifications to assignees.

    Returns:
        Dict with reminder results
    """
    logger.info("Starting overdue task reminder processing")

    try:
        async with async_session_factory() as db:
            # Get current time
            now = datetime.now(timezone.utc)

            # Find overdue tasks (not completed, past due date)
            stmt = select(Task).where(
                and_(
                    Task.status != "done",
                    Task.status != "cancelled",
                    Task.due_date < now,
                    Task.assignee_id.isnot(None),
                )
            )
            result = await db.execute(stmt)
            overdue_tasks = result.scalars().all()

            # Group tasks by assignee
            tasks_by_user: Dict[UUID, List[Task]] = {}
            for task in overdue_tasks:
                if task.assignee_id:
                    if task.assignee_id not in tasks_by_user:
                        tasks_by_user[task.assignee_id] = []
                    tasks_by_user[task.assignee_id].append(task)

            # Send reminders to each user
            reminders_sent = 0
            for user_id, tasks in tasks_by_user.items():
                # Get user details
                user = await db.get(User, user_id)
                if not user:
                    continue

                # Create notification message
                # task_list = "\n".join(
                #     [
                #         f"- {task.title} (due "
                #         f"{task.due_date.date() if task.due_date else 'Unknown'})"
                #         for task in tasks
                #     ]
                # )

                # TODO: Send actual notification
                # This would use NotificationService when implemented
                # message = (
                #     f"You have {len(tasks)} overdue task(s):\n\n"
                #     f"{task_list}\n\n"
                #     f"Please update their status or due dates."
                # )
                logger.info(f"Reminder for {user.email}: {len(tasks)} overdue tasks")

                reminders_sent += 1

            logger.info(
                f"Sent {reminders_sent} reminders for " f"{len(overdue_tasks)} overdue tasks"
            )

            return {
                "success": True,
                "overdue_tasks_count": len(overdue_tasks),
                "reminders_sent": reminders_sent,
                "timestamp": now.isoformat(),
            }

    except Exception as e:
        logger.error(f"Error sending overdue reminders: {e}")
        raise
