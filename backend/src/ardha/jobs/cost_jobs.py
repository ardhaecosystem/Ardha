"""
Cost tracking and analytics background jobs.

This module provides Celery tasks for AI cost reporting,
usage analytics, and project metrics.
"""

import logging
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import Integer, and_, cast, func, select

from ardha.core.celery_app import celery_app
from ardha.core.database import async_session_factory
from ardha.models.ai_usage import AIUsage
from ardha.models.project import Project
from ardha.models.task import Task
from ardha.models.user import User

logger = logging.getLogger(__name__)


@celery_app.task(
    name="cost.generate_daily_cost_report",
    queue="analytics",
    time_limit=600,  # 10 minutes
    soft_time_limit=540,  # 9 minutes
)
async def generate_daily_cost_report() -> dict[str, Any]:
    """
    Generate daily AI cost report.

    Creates comprehensive cost report for previous day including:
    - Total costs
    - Per-user breakdown
    - Per-project breakdown
    - Per-operation breakdown
    - Token usage statistics

    Returns:
        Dict with report data and summary
    """
    logger.info("Starting daily cost report generation")

    try:
        async with async_session_factory() as db:
            # Get yesterday's date range
            now = datetime.now(timezone.utc)
            yesterday_start = (now - timedelta(days=1)).replace(
                hour=0, minute=0, second=0, microsecond=0
            )
            yesterday_end = yesterday_start + timedelta(days=1)

            # Total costs (aggregate across all users)
            stmt_total = select(func.coalesce(func.sum(AIUsage.cost), 0)).where(
                and_(
                    AIUsage.created_at >= yesterday_start,
                    AIUsage.created_at < yesterday_end,
                )
            )
            result = await db.execute(stmt_total)
            total_cost = result.scalar()

            # Total tokens
            stmt_tokens = select(
                func.sum(AIUsage.tokens_input).label("input"),
                func.sum(AIUsage.tokens_output).label("output"),
            ).where(
                and_(
                    AIUsage.created_at >= yesterday_start,
                    AIUsage.created_at < yesterday_end,
                )
            )
            result = await db.execute(stmt_tokens)
            tokens = result.one()
            total_input_tokens = tokens.input or 0
            total_output_tokens = tokens.output or 0
            total_tokens = total_input_tokens + total_output_tokens

            # Operation breakdown
            stmt_operations = (
                select(
                    AIUsage.operation,
                    func.count(AIUsage.id).label("count"),
                    func.sum(AIUsage.cost).label("cost"),
                    func.sum(AIUsage.tokens_input).label("input_tokens"),
                    func.sum(AIUsage.tokens_output).label("output_tokens"),
                )
                .where(
                    and_(
                        AIUsage.created_at >= yesterday_start,
                        AIUsage.created_at < yesterday_end,
                    )
                )
                .group_by(AIUsage.operation)
            )
            result = await db.execute(stmt_operations)
            operations = result.all()

            operation_breakdown = [
                {
                    "operation": op.operation.value,
                    "count": op.count,
                    "cost": float(op.cost or 0),
                    "input_tokens": op.input_tokens or 0,
                    "output_tokens": op.output_tokens or 0,
                    "total_tokens": ((op.input_tokens or 0) + (op.output_tokens or 0)),
                }
                for op in operations
            ]

            # Model breakdown
            stmt_models = (
                select(
                    AIUsage.model_name,
                    func.count(AIUsage.id).label("count"),
                    func.sum(AIUsage.cost).label("cost"),
                )
                .where(
                    and_(
                        AIUsage.created_at >= yesterday_start,
                        AIUsage.created_at < yesterday_end,
                    )
                )
                .group_by(AIUsage.model_name)
            )
            result = await db.execute(stmt_models)
            models = result.all()

            model_breakdown = [
                {
                    "model": model.model_name,
                    "count": model.count,
                    "cost": float(model.cost or 0),
                }
                for model in models
            ]

            # User breakdown (top 10)
            stmt_users = (
                select(
                    AIUsage.user_id,
                    User.username,
                    User.email,
                    func.count(AIUsage.id).label("count"),
                    func.sum(AIUsage.cost).label("cost"),
                )
                .join(User, AIUsage.user_id == User.id)
                .where(
                    and_(
                        AIUsage.created_at >= yesterday_start,
                        AIUsage.created_at < yesterday_end,
                    )
                )
                .group_by(AIUsage.user_id, User.username, User.email)
                .order_by(func.sum(AIUsage.cost).desc())
                .limit(10)
            )
            result = await db.execute(stmt_users)
            users = result.all()

            user_breakdown = [
                {
                    "user_id": str(user.user_id),
                    "username": user.username,
                    "email": user.email,
                    "operations": user.count,
                    "cost": float(user.cost or 0),
                }
                for user in users
            ]

            # Project breakdown (top 10)
            stmt_projects = (
                select(
                    AIUsage.project_id,
                    Project.name,
                    func.count(AIUsage.id).label("count"),
                    func.sum(AIUsage.cost).label("cost"),
                )
                .join(Project, AIUsage.project_id == Project.id, isouter=True)
                .where(
                    and_(
                        AIUsage.created_at >= yesterday_start,
                        AIUsage.created_at < yesterday_end,
                        AIUsage.project_id.isnot(None),
                    )
                )
                .group_by(AIUsage.project_id, Project.name)
                .order_by(func.sum(AIUsage.cost).desc())
                .limit(10)
            )
            result = await db.execute(stmt_projects)
            projects = result.all()

            project_breakdown = [
                {
                    "project_id": str(proj.project_id),
                    "project_name": proj.name,
                    "operations": proj.count,
                    "cost": float(proj.cost or 0),
                }
                for proj in projects
            ]

            # Build report
            total_operations = sum(op["count"] for op in operation_breakdown)
            report = {
                "date": yesterday_start.date().isoformat(),
                "generated_at": now.isoformat(),
                "summary": {
                    "total_cost": float(total_cost or 0),
                    "total_operations": total_operations,
                    "total_tokens": total_tokens,
                    "input_tokens": total_input_tokens,
                    "output_tokens": total_output_tokens,
                    "average_cost_per_operation": (
                        float(total_cost or 0) / total_operations if total_operations > 0 else 0
                    ),
                },
                "operation_breakdown": operation_breakdown,
                "model_breakdown": model_breakdown,
                "user_breakdown": user_breakdown,
                "project_breakdown": project_breakdown,
            }

            logger.info(
                f"Daily cost report generated: "
                f"${report['summary']['total_cost']:.4f} for "
                f"{report['summary']['total_operations']} operations"
            )

            # TODO: Send email notification with report
            # This would use EmailService when implemented

            # TODO: Store report in database for historical tracking
            # This would require a CostReport model

            return {
                "success": True,
                "report": report,
            }

    except Exception as e:
        logger.error(f"Error generating daily cost report: {e}")
        raise


@celery_app.task(
    name="cost.analyze_ai_usage_patterns",
    queue="analytics",
    time_limit=600,  # 10 minutes
    soft_time_limit=540,  # 9 minutes
)
async def analyze_ai_usage_patterns() -> dict[str, Any]:
    """
    Analyze AI usage patterns to identify trends and optimization opportunities.

    Analyzes:
    - High-cost operations
    - Usage spikes
    - Model distribution
    - Cost optimization opportunities

    Returns:
        Dict with analysis results
    """
    logger.info("Starting AI usage pattern analysis")

    try:
        async with async_session_factory() as db:
            # Get last 7 days of data
            now = datetime.now(timezone.utc)
            week_ago = now - timedelta(days=7)

            # Find high-cost operations (top 10)
            stmt_expensive = (
                select(
                    AIUsage.operation,
                    AIUsage.model_name,
                    func.avg(AIUsage.cost).label("avg_cost"),
                    func.count(AIUsage.id).label("count"),
                    func.sum(AIUsage.cost).label("total_cost"),
                )
                .where(AIUsage.created_at >= week_ago)
                .group_by(AIUsage.operation, AIUsage.model_name)
                .order_by(func.avg(AIUsage.cost).desc())
                .limit(10)
            )
            result = await db.execute(stmt_expensive)
            expensive_ops = result.all()

            high_cost_operations = [
                {
                    "operation": op.operation.value,
                    "model": op.model_name,
                    "average_cost": float(op.avg_cost or 0),
                    "count": op.count,
                    "total_cost": float(op.total_cost or 0),
                }
                for op in expensive_ops
            ]

            # Detect usage spikes (daily comparison)
            daily_costs = []
            for i in range(7):
                day_start = (now - timedelta(days=i + 1)).replace(
                    hour=0, minute=0, second=0, microsecond=0
                )
                day_end = day_start + timedelta(days=1)

                stmt_day = select(
                    func.sum(AIUsage.cost).label("cost"),
                    func.count(AIUsage.id).label("count"),
                ).where(
                    and_(
                        AIUsage.created_at >= day_start,
                        AIUsage.created_at < day_end,
                    )
                )
                result = await db.execute(stmt_day)
                day_data = result.one()

                daily_costs.append(
                    {
                        "date": day_start.date().isoformat(),
                        "cost": float(day_data.cost or 0),
                        "operations": day_data.count or 0,
                    }
                )

            # Calculate average and detect spikes
            avg_daily_cost = (
                sum(d["cost"] for d in daily_costs) / len(daily_costs) if daily_costs else 0
            )
            spikes = [
                day
                for day in daily_costs
                if day["cost"] > avg_daily_cost * 1.5  # 50% above average
            ]

            # Model usage distribution
            stmt_model_dist = (
                select(
                    AIUsage.model_name,
                    func.count(AIUsage.id).label("usage_count"),
                    func.sum(AIUsage.cost).label("total_cost"),
                )
                .where(AIUsage.created_at >= week_ago)
                .group_by(AIUsage.model_name)
            )
            result = await db.execute(stmt_model_dist)
            model_dist = result.all()

            # Calculate total count for percentage
            total_model_count = sum(row.usage_count for row in model_dist) or 0

            model_distribution = [
                {
                    "model": row.model_name,
                    "usage_count": row.usage_count,
                    "total_cost": float(row.total_cost or 0),
                    "percentage": (
                        (row.usage_count / total_model_count * 100) if total_model_count > 0 else 0
                    ),
                }
                for row in model_dist
            ]

            # Generate recommendations
            recommendations = []

            # Check if expensive models are overused
            expensive_model_threshold = avg_daily_cost * 0.3
            for op in high_cost_operations:
                if op["total_cost"] > expensive_model_threshold:
                    recommendations.append(
                        {
                            "type": "cost_optimization",
                            "priority": "high",
                            "message": (
                                f"Consider using cheaper model for "
                                f"{op['operation']} operations "
                                f"(currently ${op['average_cost']:.4f} per op)"
                            ),
                        }
                    )

            # Check for usage spikes
            if spikes:
                recommendations.append(
                    {
                        "type": "usage_spike",
                        "priority": "medium",
                        "message": (
                            f"Detected {len(spikes)} usage spike(s) "
                            f"in last 7 days. "
                            f"Review activity on: "
                            f"{', '.join(s['date'] for s in spikes)}"
                        ),
                    }
                )

            analysis = {
                "analyzed_at": now.isoformat(),
                "period": "last_7_days",
                "high_cost_operations": high_cost_operations,
                "daily_costs": daily_costs,
                "average_daily_cost": round(avg_daily_cost, 4),
                "usage_spikes": spikes,
                "model_distribution": model_distribution,
                "recommendations": recommendations,
            }

            logger.info(
                f"Usage pattern analysis complete: "
                f"{len(recommendations)} recommendations generated"
            )

            return {
                "success": True,
                "analysis": analysis,
            }

    except Exception as e:
        logger.error(f"Error analyzing AI usage patterns: {e}")
        raise


@celery_app.task(
    name="cost.calculate_project_analytics",
    queue="analytics",
    time_limit=600,  # 10 minutes
    soft_time_limit=540,  # 9 minutes
)
async def calculate_project_analytics() -> dict[str, Any]:
    """
    Calculate comprehensive project-level analytics.

    Calculates:
    - Tasks completed per project
    - AI operations per project
    - Cost per project
    - Activity trends

    Returns:
        Dict with project analytics
    """
    logger.info("Starting project analytics calculation")

    try:
        async with async_session_factory() as db:
            # Get last 30 days
            now = datetime.now(timezone.utc)
            month_ago = now - timedelta(days=30)

            # Get all active projects
            stmt_projects = select(Project).where(Project.is_archived.is_(False))
            result = await db.execute(stmt_projects)
            projects = result.scalars().all()

            project_analytics = []

            for project in projects:
                # Task metrics
                stmt_tasks = select(
                    func.count(Task.id).label("total"),
                    func.sum(cast(Task.status == "done", Integer)).label("completed"),
                ).where(
                    and_(
                        Task.project_id == project.id,
                        Task.created_at >= month_ago,
                    )
                )
                result = await db.execute(stmt_tasks)
                task_stats = result.one()

                # AI usage metrics - project-specific cost
                stmt_project_cost = select(func.coalesce(func.sum(AIUsage.cost), 0)).where(
                    and_(
                        AIUsage.project_id == project.id,
                        AIUsage.created_at >= month_ago,
                    )
                )
                result_cost = await db.execute(stmt_project_cost)
                project_cost = result_cost.scalar()

                stmt_ai_ops = select(func.count(AIUsage.id)).where(
                    and_(
                        AIUsage.project_id == project.id,
                        AIUsage.created_at >= month_ago,
                    )
                )
                ai_operations = await db.scalar(stmt_ai_ops) or 0

                # Calculate completion rate
                total_tasks = task_stats.total or 0
                completed_tasks = task_stats.completed or 0
                completion_rate = (completed_tasks / total_tasks * 100) if total_tasks > 0 else 0

                project_analytics.append(
                    {
                        "project_id": str(project.id),
                        "project_name": project.name,
                        "period": "last_30_days",
                        "task_metrics": {
                            "total_tasks": total_tasks,
                            "completed_tasks": completed_tasks,
                            "completion_rate": round(completion_rate, 2),
                        },
                        "ai_metrics": {
                            "total_operations": ai_operations,
                            "total_cost": float(project_cost or 0),
                            "average_cost_per_task": (
                                float(project_cost or 0) / total_tasks if total_tasks > 0 else 0
                            ),
                        },
                    }
                )

            logger.info(f"Project analytics calculated for " f"{len(project_analytics)} projects")

            return {
                "success": True,
                "calculated_at": now.isoformat(),
                "project_count": len(project_analytics),
                "analytics": project_analytics,
            }

    except Exception as e:
        logger.error(f"Error calculating project analytics: {e}")
        raise
