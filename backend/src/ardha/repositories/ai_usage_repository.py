"""
AI Usage repository for data access abstraction.

This module provides repository pattern implementation for AIUsage model,
handling all database operations related to AI operation tracking and analytics.
"""

import logging
from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import List
from uuid import UUID

from sqlalchemy import select, func, and_, or_
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ardha.models.ai_usage import AIUsage, AIOperation

logger = logging.getLogger(__name__)


class AIUsageRepository:
    """
    Repository for AIUsage model database operations.
    
    Provides data access methods for AI usage tracking including
    CRUD operations, analytics, and cost management. Follows the 
    repository pattern to abstract database implementation details from business logic.
    
    Attributes:
        db: SQLAlchemy async session for database operations
    """
    
    def __init__(self, db: AsyncSession) -> None:
        """
        Initialize the AIUsageRepository with a database session.
        
        Args:
            db: SQLAlchemy async session for database operations
        """
        self.db = db
    
    async def create(
        self,
        user_id: UUID,
        model_name: str,
        operation: str,
        tokens_input: int,
        tokens_output: int,
        cost: Decimal,
        project_id: UUID | None = None,
        usage_date: date | None = None,
    ) -> AIUsage:
        """
        Create a new AI usage record.
        
        Args:
            user_id: UUID of user who performed the operation
            model_name: Name of AI model used
            operation: Type of AI operation performed
            tokens_input: Number of input tokens consumed
            tokens_output: Number of output tokens generated
            cost: Cost of the operation
            project_id: UUID of associated project (optional)
            usage_date: Date for the operation (defaults to today)
            
        Returns:
            Created AIUsage object with generated ID and timestamp
            
        Raises:
            ValueError: If operation is invalid or required fields are missing
            IntegrityError: If foreign key constraint violated
            SQLAlchemyError: If database operation fails
        """
        try:
            # Validate operation
            if operation not in [op.value for op in AIOperation]:
                raise ValueError(f"Invalid operation: {operation}. Must be one of: {[op.value for op in AIOperation]}")
            
            if not model_name or model_name.strip() == "":
                raise ValueError("model_name cannot be empty")
            
            if tokens_input < 0 or tokens_output < 0:
                raise ValueError("token counts must be non-negative")
            
            if cost < 0:
                raise ValueError("cost must be non-negative")
            
            # Default to today if no date provided
            if usage_date is None:
                usage_date = date.today()
            
            ai_usage = AIUsage(
                user_id=user_id,
                model_name=model_name.strip(),
                operation=operation,
                tokens_input=tokens_input,
                tokens_output=tokens_output,
                cost=cost,
                project_id=project_id,
                usage_date=usage_date,
            )
            
            self.db.add(ai_usage)
            await self.db.flush()
            await self.db.refresh(ai_usage)
            
            logger.info(f"Created AI usage record for user {user_id}: {model_name} {operation}")
            return ai_usage
        except IntegrityError as e:
            logger.warning(f"Integrity error creating AI usage: {e}")
            raise
        except SQLAlchemyError as e:
            logger.error(f"Error creating AI usage: {e}", exc_info=True)
            raise
    
    async def get_daily_usage(self, user_id: UUID, usage_date: date) -> List[AIUsage]:
        """
        Get all AI usage records for a user on a specific date.
        
        Args:
            user_id: UUID of user
            usage_date: Date to fetch usage for
            
        Returns:
            List of AIUsage objects for the specified date
            
        Raises:
            SQLAlchemyError: If database query fails
        """
        try:
            stmt = (
                select(AIUsage)
                .options(
                    selectinload(AIUsage.user),
                    selectinload(AIUsage.project),
                )
                .where(
                    and_(
                        AIUsage.user_id == user_id,
                        AIUsage.usage_date == usage_date,
                    )
                )
                .order_by(AIUsage.created_at.desc())
            )
            
            result = await self.db.execute(stmt)
            return list(result.scalars().all())
        except SQLAlchemyError as e:
            logger.error(f"Error fetching daily usage for user {user_id} on {usage_date}: {e}", exc_info=True)
            raise
    
    async def get_project_usage(
        self,
        project_id: UUID,
        start_date: date,
        end_date: date,
    ) -> List[AIUsage]:
        """
        Get AI usage records for a project within a date range.
        
        Args:
            project_id: UUID of project
            start_date: Start date (inclusive)
            end_date: End date (inclusive)
            
        Returns:
            List of AIUsage objects for the specified date range
            
        Raises:
            ValueError: If date range is invalid
            SQLAlchemyError: If database query fails
        """
        if start_date > end_date:
            raise ValueError("start_date must be before or equal to end_date")
        
        try:
            stmt = (
                select(AIUsage)
                .options(
                    selectinload(AIUsage.user),
                    selectinload(AIUsage.project),
                )
                .where(
                    and_(
                        AIUsage.project_id == project_id,
                        AIUsage.usage_date >= start_date,
                        AIUsage.usage_date <= end_date,
                    )
                )
                .order_by(AIUsage.usage_date.desc(), AIUsage.created_at.desc())
            )
            
            result = await self.db.execute(stmt)
            return list(result.scalars().all())
        except SQLAlchemyError as e:
            logger.error(f"Error fetching project usage for {project_id} from {start_date} to {end_date}: {e}", exc_info=True)
            raise
    
    async def get_user_total_cost(
        self,
        user_id: UUID,
        start_date: date,
        end_date: date,
    ) -> Decimal:
        """
        Get total cost for a user within a date range.
        
        Args:
            user_id: UUID of user
            start_date: Start date (inclusive)
            end_date: End date (inclusive)
            
        Returns:
            Total cost as Decimal
            
        Raises:
            ValueError: If date range is invalid
            SQLAlchemyError: If database query fails
        """
        if start_date > end_date:
            raise ValueError("start_date must be before or equal to end_date")
        
        try:
            stmt = (
                select(func.coalesce(func.sum(AIUsage.cost), 0))
                .where(
                    and_(
                        AIUsage.user_id == user_id,
                        AIUsage.usage_date >= start_date,
                        AIUsage.usage_date <= end_date,
                    )
                )
            )
            
            result = await self.db.execute(stmt)
            total_cost = result.scalar()
            return total_cost if total_cost is not None else Decimal("0.00")
        except SQLAlchemyError as e:
            logger.error(f"Error calculating total cost for user {user_id} from {start_date} to {end_date}: {e}", exc_info=True)
            raise
    
    async def get_user_usage_stats(
        self,
        user_id: UUID,
        start_date: date,
        end_date: date,
    ) -> dict:
        """
        Get comprehensive usage statistics for a user within a date range.
        
        Args:
            user_id: UUID of user
            start_date: Start date (inclusive)
            end_date: End date (inclusive)
            
        Returns:
            Dictionary with usage statistics:
            - total_cost: Total cost
            - total_tokens_input: Total input tokens
            - total_tokens_output: Total output tokens
            - operation_counts: Count by operation type
            - model_usage: Usage by model
            
        Raises:
            ValueError: If date range is invalid
            SQLAlchemyError: If database query fails
        """
        if start_date > end_date:
            raise ValueError("start_date must be before or equal to end_date")
        
        try:
            # Get aggregate stats
            agg_stmt = (
                select(
                    func.coalesce(func.sum(AIUsage.cost), 0).label('total_cost'),
                    func.coalesce(func.sum(AIUsage.tokens_input), 0).label('total_tokens_input'),
                    func.coalesce(func.sum(AIUsage.tokens_output), 0).label('total_tokens_output'),
                )
                .where(
                    and_(
                        AIUsage.user_id == user_id,
                        AIUsage.usage_date >= start_date,
                        AIUsage.usage_date <= end_date,
                    )
                )
            )
            
            agg_result = await self.db.execute(agg_stmt)
            agg_row = agg_result.first()
            
            # Get operation counts
            op_stmt = (
                select(
                    AIUsage.operation,
                    func.count(AIUsage.id).label('count'),
                )
                .where(
                    and_(
                        AIUsage.user_id == user_id,
                        AIUsage.usage_date >= start_date,
                        AIUsage.usage_date <= end_date,
                    )
                )
                .group_by(AIUsage.operation)
            )
            
            op_result = await self.db.execute(op_stmt)
            operation_counts = {row.operation: row.count for row in op_result}
            
            # Get model usage
            model_stmt = (
                select(
                    AIUsage.model_name,
                    func.count(AIUsage.id).label('count'),
                    func.coalesce(func.sum(AIUsage.cost), 0).label('cost'),
                )
                .where(
                    and_(
                        AIUsage.user_id == user_id,
                        AIUsage.usage_date >= start_date,
                        AIUsage.usage_date <= end_date,
                    )
                )
                .group_by(AIUsage.model_name)
            )
            
            model_result = await self.db.execute(model_stmt)
            model_usage = {row.model_name: {'count': row.count, 'cost': row.cost} for row in model_result}
            
            return {
                'total_cost': agg_row.total_cost if agg_row else Decimal("0.00"),
                'total_tokens_input': agg_row.total_tokens_input if agg_row else 0,
                'total_tokens_output': agg_row.total_tokens_output if agg_row else 0,
                'operation_counts': operation_counts,
                'model_usage': model_usage,
            }
        except SQLAlchemyError as e:
            logger.error(f"Error getting usage stats for user {user_id}: {e}", exc_info=True)
            raise
    
    async def get_project_usage_stats(
        self,
        project_id: UUID,
        start_date: date,
        end_date: date,
    ) -> dict:
        """
        Get comprehensive usage statistics for a project within a date range.
        
        Args:
            project_id: UUID of project
            start_date: Start date (inclusive)
            end_date: End date (inclusive)
            
        Returns:
            Dictionary with usage statistics (same structure as user stats)
            
        Raises:
            ValueError: If date range is invalid
            SQLAlchemyError: If database query fails
        """
        if start_date > end_date:
            raise ValueError("start_date must be before or equal to end_date")
        
        try:
            # Get aggregate stats
            agg_stmt = (
                select(
                    func.coalesce(func.sum(AIUsage.cost), 0).label('total_cost'),
                    func.coalesce(func.sum(AIUsage.tokens_input), 0).label('total_tokens_input'),
                    func.coalesce(func.sum(AIUsage.tokens_output), 0).label('total_tokens_output'),
                )
                .where(
                    and_(
                        AIUsage.project_id == project_id,
                        AIUsage.usage_date >= start_date,
                        AIUsage.usage_date <= end_date,
                    )
                )
            )
            
            agg_result = await self.db.execute(agg_stmt)
            agg_row = agg_result.first()
            
            # Get operation counts
            op_stmt = (
                select(
                    AIUsage.operation,
                    func.count(AIUsage.id).label('count'),
                )
                .where(
                    and_(
                        AIUsage.project_id == project_id,
                        AIUsage.usage_date >= start_date,
                        AIUsage.usage_date <= end_date,
                    )
                )
                .group_by(AIUsage.operation)
            )
            
            op_result = await self.db.execute(op_stmt)
            operation_counts = {row.operation: row.count for row in op_result}
            
            # Get model usage
            model_stmt = (
                select(
                    AIUsage.model_name,
                    func.count(AIUsage.id).label('count'),
                    func.coalesce(func.sum(AIUsage.cost), 0).label('cost'),
                )
                .where(
                    and_(
                        AIUsage.project_id == project_id,
                        AIUsage.usage_date >= start_date,
                        AIUsage.usage_date <= end_date,
                    )
                )
                .group_by(AIUsage.model_name)
            )
            
            model_result = await self.db.execute(model_stmt)
            model_usage = {row.model_name: {'count': row.count, 'cost': row.cost} for row in model_result}
            
            return {
                'total_cost': agg_row.total_cost if agg_row else Decimal("0.00"),
                'total_tokens_input': agg_row.total_tokens_input if agg_row else 0,
                'total_tokens_output': agg_row.total_tokens_output if agg_row else 0,
                'operation_counts': operation_counts,
                'model_usage': model_usage,
            }
        except SQLAlchemyError as e:
            logger.error(f"Error getting usage stats for project {project_id}: {e}", exc_info=True)
            raise
    
    async def get_daily_cost_summary(self, user_id: UUID, days: int = 30) -> List[dict]:
        """
        Get daily cost summary for a user over the last N days.
        
        Args:
            user_id: UUID of user
            days: Number of days to look back (max 365)
            
        Returns:
            List of dictionaries with date and cost
            
        Raises:
            ValueError: If days is invalid
            SQLAlchemyError: If database query fails
        """
        if days <= 0 or days > 365:
            raise ValueError("days must be between 1 and 365")
        
        try:
            end_date = date.today()
            start_date = end_date - timedelta(days=days-1)
            
            stmt = (
                select(
                    AIUsage.usage_date,
                    func.coalesce(func.sum(AIUsage.cost), 0).label('daily_cost'),
                )
                .where(
                    and_(
                        AIUsage.user_id == user_id,
                        AIUsage.usage_date >= start_date,
                        AIUsage.usage_date <= end_date,
                    )
                )
                .group_by(AIUsage.usage_date)
                .order_by(AIUsage.usage_date.desc())
            )
            
            result = await self.db.execute(stmt)
            return [{'date': row.usage_date, 'cost': row.daily_cost} for row in result]
        except SQLAlchemyError as e:
            logger.error(f"Error getting daily cost summary for user {user_id}: {e}", exc_info=True)
            raise