"""
DatabaseProperty repository for data access abstraction.

This module provides repository pattern implementation for DatabaseProperty model,
handling all database operations for database column/field definitions.
"""

import logging
from typing import Any
from uuid import UUID

from sqlalchemy import and_, func, select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ardha.models.database_property import DatabaseProperty

logger = logging.getLogger(__name__)


class DatabasePropertyRepository:
    """
    Repository for DatabaseProperty model database operations.

    Provides data access methods for database property-related operations including
    CRUD operations, reordering, and filtering by type.
    Follows the repository pattern to abstract database implementation
    details from business logic.

    Attributes:
        db: SQLAlchemy async session for database operations
    """

    def __init__(self, db: AsyncSession) -> None:
        """
        Initialize the DatabasePropertyRepository with a database session.

        Args:
            db: SQLAlchemy async session for database operations
        """
        self.db = db

    async def create(self, property_data: dict) -> DatabaseProperty:
        """
        Create a new database property.

        Auto-assigns position if not provided (max position + 1).

        Args:
            property_data: Dictionary with property fields

        Returns:
            Created DatabaseProperty object

        Raises:
            ValueError: If property_type is invalid or required fields missing
            IntegrityError: If unique constraints violated
            SQLAlchemyError: If database operation fails
        """
        try:
            database_id = property_data.get("database_id")
            if not database_id:
                raise ValueError("database_id is required")

            # Auto-assign position if not provided
            if "position" not in property_data:
                max_position_stmt = select(func.max(DatabaseProperty.position)).where(
                    DatabaseProperty.database_id == database_id
                )
                result = await self.db.execute(max_position_stmt)
                max_position = result.scalar()
                property_data["position"] = (max_position or -1) + 1

            # Validate config for property_type if provided
            property_type = property_data.get("property_type")
            config = property_data.get("config")

            if property_type and config:
                # Basic validation that config is a dict
                if not isinstance(config, dict):
                    raise ValueError("config must be a dictionary")

            prop = DatabaseProperty(**property_data)

            self.db.add(prop)
            await self.db.flush()
            await self.db.refresh(prop)

            logger.info(
                f"Created property {prop.id} '{prop.name}' "
                f"for database {database_id}"
            )
            return prop
        except IntegrityError as e:
            logger.warning(f"Integrity error creating property: {e}")
            raise
        except SQLAlchemyError as e:
            logger.error(f"Error creating property: {e}", exc_info=True)
            raise

    async def get_by_id(self, property_id: UUID) -> DatabaseProperty | None:
        """
        Fetch a property by its UUID.

        Args:
            property_id: UUID of property to fetch

        Returns:
            DatabaseProperty object if found, None otherwise

        Raises:
            SQLAlchemyError: If database query fails
        """
        try:
            stmt = (
                select(DatabaseProperty)
                .options(selectinload(DatabaseProperty.database))
                .where(DatabaseProperty.id == property_id)
            )
            result = await self.db.execute(stmt)
            return result.scalar_one_or_none()
        except SQLAlchemyError as e:
            logger.error(f"Error fetching property by id {property_id}: {e}", exc_info=True)
            raise

    async def get_by_database(
        self,
        database_id: UUID,
        visible_only: bool = False,
    ) -> list[DatabaseProperty]:
        """
        Fetch properties for a specific database.

        Args:
            database_id: UUID of database
            visible_only: If True, only return visible properties

        Returns:
            List of DatabaseProperty objects ordered by position ASC

        Raises:
            SQLAlchemyError: If database query fails
        """
        try:
            stmt = select(DatabaseProperty).where(DatabaseProperty.database_id == database_id)

            if visible_only:
                stmt = stmt.where(DatabaseProperty.is_visible.is_(True))

            # Order by position for consistent ordering
            stmt = stmt.order_by(DatabaseProperty.position.asc())

            result = await self.db.execute(stmt)
            return list(result.scalars().all())
        except SQLAlchemyError as e:
            logger.error(
                f"Error fetching properties for database {database_id}: {e}", exc_info=True
            )
            raise

    async def update(self, property_id: UUID, updates: dict) -> DatabaseProperty | None:
        """
        Update property fields including config.

        Args:
            property_id: UUID of property to update
            updates: Dictionary of fields to update

        Returns:
            Updated DatabaseProperty object if found, None otherwise

        Raises:
            SQLAlchemyError: If database operation fails
        """
        try:
            prop = await self.get_by_id(property_id)
            if not prop:
                logger.warning(f"Cannot update: property {property_id} not found")
                return None

            # Update allowed fields
            for key, value in updates.items():
                if hasattr(prop, key) and key not in ["id", "created_at", "database_id"]:
                    setattr(prop, key, value)

            await self.db.flush()
            await self.db.refresh(prop)

            logger.info(f"Updated property {property_id}")
            return prop
        except SQLAlchemyError as e:
            logger.error(f"Error updating property {property_id}: {e}", exc_info=True)
            raise

    async def delete(self, property_id: UUID) -> bool:
        """
        Delete a property and cascade to all entry values.

        Args:
            property_id: UUID of property to delete

        Returns:
            True if deleted, False if not found

        Raises:
            SQLAlchemyError: If database operation fails
        """
        try:
            stmt = select(DatabaseProperty).where(DatabaseProperty.id == property_id)
            result = await self.db.execute(stmt)
            prop = result.scalar_one_or_none()

            if not prop:
                logger.warning(f"Cannot delete: property {property_id} not found")
                return False

            await self.db.delete(prop)
            await self.db.flush()

            logger.info(f"Deleted property {property_id}")
            return True
        except SQLAlchemyError as e:
            logger.error(f"Error deleting property {property_id}: {e}", exc_info=True)
            raise

    async def reorder(self, property_ids: list[UUID]) -> bool:
        """
        Update positions for multiple properties in batch.

        Args:
            property_ids: List of property UUIDs in desired order

        Returns:
            True if updated successfully

        Raises:
            SQLAlchemyError: If database operation fails
        """
        try:
            for i, property_id in enumerate(property_ids):
                stmt = select(DatabaseProperty).where(DatabaseProperty.id == property_id)
                result = await self.db.execute(stmt)
                prop = result.scalar_one_or_none()

                if prop:
                    prop.position = i

            await self.db.flush()
            logger.info(f"Reordered {len(property_ids)} properties")
            return True
        except SQLAlchemyError as e:
            logger.error(f"Error reordering properties: {e}", exc_info=True)
            raise

    async def get_by_type(
        self,
        database_id: UUID,
        property_type: str,
    ) -> list[DatabaseProperty]:
        """
        Get properties of a specific type in a database.

        Args:
            database_id: UUID of database
            property_type: Property type to filter by

        Returns:
            List of DatabaseProperty objects of specified type

        Raises:
            SQLAlchemyError: If database query fails
        """
        try:
            stmt = (
                select(DatabaseProperty)
                .where(
                    and_(
                        DatabaseProperty.database_id == database_id,
                        DatabaseProperty.property_type == property_type,
                    )
                )
                .order_by(DatabaseProperty.position.asc())
            )

            result = await self.db.execute(stmt)
            return list(result.scalars().all())
        except SQLAlchemyError as e:
            logger.error(
                f"Error fetching properties of type {property_type}: {e}", exc_info=True
            )
            raise

    async def get_formula_properties(self, database_id: UUID) -> list[DatabaseProperty]:
        """
        Get all formula properties for a database.

        Used for recalculation when dependent properties change.

        Args:
            database_id: UUID of database

        Returns:
            List of formula DatabaseProperty objects

        Raises:
            SQLAlchemyError: If database query fails
        """
        return await self.get_by_type(database_id, "formula")

    async def get_rollup_properties(self, database_id: UUID) -> list[DatabaseProperty]:
        """
        Get all rollup properties for a database.

        Used for recalculation when related entries change.

        Args:
            database_id: UUID of database

        Returns:
            List of rollup DatabaseProperty objects

        Raises:
            SQLAlchemyError: If database query fails
        """
        return await self.get_by_type(database_id, "rollup")

    async def get_relation_properties(self, database_id: UUID) -> list[DatabaseProperty]:
        """
        Get all relation properties for a database.

        Used for managing relationships between databases.

        Args:
            database_id: UUID of database

        Returns:
            List of relation DatabaseProperty objects

        Raises:
            SQLAlchemyError: If database query fails
        """
        return await self.get_by_type(database_id, "relation")

    async def get_required_properties(self, database_id: UUID) -> list[DatabaseProperty]:
        """
        Get properties where is_required=True.

        Used for entry validation to ensure required fields are filled.

        Args:
            database_id: UUID of database

        Returns:
            List of required DatabaseProperty objects

        Raises:
            SQLAlchemyError: If database query fails
        """
        try:
            stmt = (
                select(DatabaseProperty)
                .where(
                    and_(
                        DatabaseProperty.database_id == database_id,
                        DatabaseProperty.is_required.is_(True),
                    )
                )
                .order_by(DatabaseProperty.position.asc())
            )

            result = await self.db.execute(stmt)
            return list(result.scalars().all())
        except SQLAlchemyError as e:
            logger.error(f"Error fetching required properties: {e}", exc_info=True)
            raise

    async def count_by_database(self, database_id: UUID) -> int:
        """
        Get count of properties in a database.

        Args:
            database_id: UUID of database

        Returns:
            Total count of properties

        Raises:
            SQLAlchemyError: If database query fails
        """
        try:
            stmt = select(func.count(DatabaseProperty.id)).where(
                DatabaseProperty.database_id == database_id
            )

            result = await self.db.execute(stmt)
            count = result.scalar()
            return count if count is not None else 0
        except SQLAlchemyError as e:
            logger.error(f"Error counting properties for database {database_id}: {e}", exc_info=True)
            raise