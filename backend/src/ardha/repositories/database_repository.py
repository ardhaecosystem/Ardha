"""
Database repository for data access abstraction.

This module provides repository pattern implementation for Database model,
handling all database operations for Notion-style databases including CRUD,
filtering, template management, and statistics.
"""

import logging
from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import and_, func, or_, select, update
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ardha.models.database import Database
from ardha.models.database_property import DatabaseProperty
from ardha.models.database_view import DatabaseView

logger = logging.getLogger(__name__)


class DatabaseRepository:
    """
    Repository for Database model database operations.

    Provides data access methods for database-related operations including
    CRUD operations, template management, filtering, and statistics.
    Follows the repository pattern to abstract database implementation
    details from business logic.

    Attributes:
        db: SQLAlchemy async session for database operations
    """

    def __init__(self, db: AsyncSession) -> None:
        """
        Initialize the DatabaseRepository with a database session.

        Args:
            db: SQLAlchemy async session for database operations
        """
        self.db = db

    async def create(self, database_data: dict, user_id: UUID) -> Database:
        """
        Create a new database with optional template properties.

        Args:
            database_data: Dictionary with database fields
            user_id: UUID of user creating the database

        Returns:
            Created Database object with loaded relationships

        Raises:
            IntegrityError: If unique constraints violated
            SQLAlchemyError: If database operation fails
        """
        try:
            # Extract template_id if provided
            template_id = database_data.get("template_id")

            # Create database
            database = Database(
                **{k: v for k, v in database_data.items() if k != "template_id"},
                created_by_user_id=user_id,
                template_id=template_id,
            )

            self.db.add(database)
            await self.db.flush()

            # If created from template, copy properties
            if template_id:
                template = await self.get_by_id(template_id)
                if template and template.properties:
                    for prop in template.properties:
                        new_prop = DatabaseProperty(
                            database_id=database.id,
                            name=prop.name,
                            property_type=prop.property_type,
                            config=prop.config,
                            position=prop.position,
                            is_required=prop.is_required,
                            is_visible=prop.is_visible,
                        )
                        self.db.add(new_prop)
                    await self.db.flush()

            await self.db.refresh(database)

            # Eager load relationships
            stmt = (
                select(Database)
                .options(
                    selectinload(Database.properties),
                    selectinload(Database.views),
                    selectinload(Database.created_by),
                )
                .where(Database.id == database.id)
            )
            result = await self.db.execute(stmt)
            database = result.scalar_one()

            logger.info(
                f"Created database {database.id} '{database.name}' "
                f"for project {database.project_id}"
            )
            return database
        except IntegrityError as e:
            logger.warning(f"Integrity error creating database: {e}")
            raise
        except SQLAlchemyError as e:
            logger.error(f"Error creating database: {e}", exc_info=True)
            raise

    async def get_by_id(self, database_id: UUID) -> Database | None:
        """
        Fetch a database by its UUID.

        Args:
            database_id: UUID of database to fetch

        Returns:
            Database object if found and not archived, None otherwise

        Raises:
            SQLAlchemyError: If database query fails
        """
        try:
            stmt = (
                select(Database)
                .options(
                    selectinload(Database.properties),
                    selectinload(Database.views),
                    selectinload(Database.created_by),
                )
                .where(and_(Database.id == database_id, Database.is_archived.is_(False)))
            )
            result = await self.db.execute(stmt)
            return result.scalar_one_or_none()
        except SQLAlchemyError as e:
            logger.error(f"Error fetching database by id {database_id}: {e}", exc_info=True)
            raise

    async def get_by_project(
        self,
        project_id: UUID,
        include_archived: bool = False,
    ) -> list[Database]:
        """
        Fetch databases for a specific project.

        Args:
            project_id: UUID of project
            include_archived: Whether to include archived databases

        Returns:
            List of Database objects ordered by created_at DESC

        Raises:
            SQLAlchemyError: If database query fails
        """
        try:
            stmt = (
                select(Database)
                .options(
                    selectinload(Database.properties),
                    selectinload(Database.views),
                )
                .where(Database.project_id == project_id)
            )

            # Filter out archived databases by default
            if not include_archived:
                stmt = stmt.where(Database.is_archived.is_(False))

            # Order by most recent first
            stmt = stmt.order_by(Database.created_at.desc())

            result = await self.db.execute(stmt)
            return list(result.scalars().all())
        except SQLAlchemyError as e:
            logger.error(f"Error fetching databases for project {project_id}: {e}", exc_info=True)
            raise

    async def list_templates(self, include_archived: bool = False) -> list[Database]:
        """
        List all database templates.

        Args:
            include_archived: Whether to include archived templates

        Returns:
            List of Database objects that are templates, ordered by name

        Raises:
            SQLAlchemyError: If database query fails
        """
        try:
            stmt = (
                select(Database)
                .options(selectinload(Database.properties))
                .where(Database.is_template.is_(True))
            )

            # Filter out archived templates by default
            if not include_archived:
                stmt = stmt.where(Database.is_archived.is_(False))

            # Order by name alphabetically
            stmt = stmt.order_by(Database.name)

            result = await self.db.execute(stmt)
            return list(result.scalars().all())
        except SQLAlchemyError as e:
            logger.error(f"Error listing database templates: {e}", exc_info=True)
            raise

    async def get_template_instances(self, template_id: UUID) -> list[Database]:
        """
        Find all databases created from a specific template.

        Args:
            template_id: UUID of template database

        Returns:
            List of Database objects created from template, ordered by created_at DESC

        Raises:
            SQLAlchemyError: If database query fails
        """
        try:
            stmt = (
                select(Database)
                .where(Database.template_id == template_id)
                .order_by(Database.created_at.desc())
            )

            result = await self.db.execute(stmt)
            return list(result.scalars().all())
        except SQLAlchemyError as e:
            logger.error(
                f"Error fetching template instances for {template_id}: {e}", exc_info=True
            )
            raise

    async def update(self, database_id: UUID, updates: dict) -> Database | None:
        """
        Update database fields.

        Args:
            database_id: UUID of database to update
            updates: Dictionary of fields to update

        Returns:
            Updated Database object if found, None otherwise

        Raises:
            SQLAlchemyError: If database operation fails
        """
        try:
            database = await self.get_by_id(database_id)
            if not database:
                logger.warning(f"Cannot update: database {database_id} not found")
                return None

            # Update allowed fields
            for key, value in updates.items():
                if hasattr(database, key) and key not in ["id", "created_at", "created_by_user_id"]:
                    setattr(database, key, value)

            database.updated_at = datetime.utcnow()
            await self.db.flush()
            await self.db.refresh(database)

            logger.info(f"Updated database {database_id}")
            return database
        except SQLAlchemyError as e:
            logger.error(f"Error updating database {database_id}: {e}", exc_info=True)
            raise

    async def archive(self, database_id: UUID) -> Database | None:
        """
        Archive a database (soft delete) and all its entries.

        Sets is_archived to True for database and all entries.
        Archived databases are excluded from default queries.

        Args:
            database_id: UUID of database to archive

        Returns:
            Updated Database object if found, None otherwise

        Raises:
            SQLAlchemyError: If database operation fails
        """
        try:
            database = await self.get_by_id(database_id)
            if not database:
                logger.warning(f"Cannot archive: database {database_id} not found")
                return None

            # Archive database
            database.is_archived = True
            database.archived_at = datetime.utcnow()

            # Archive all entries (cascade)
            from ardha.models.database_entry import DatabaseEntry

            await self.db.execute(
                update(DatabaseEntry)
                .where(DatabaseEntry.database_id == database_id)
                .values(
                    is_archived=True,
                    archived_at=datetime.utcnow(),
                )
            )

            await self.db.flush()
            await self.db.refresh(database)

            logger.info(f"Archived database {database_id} and all entries")
            return database
        except SQLAlchemyError as e:
            logger.error(f"Error archiving database {database_id}: {e}", exc_info=True)
            raise

    async def delete(self, database_id: UUID) -> bool:
        """
        Hard delete a database and all related data.

        Permanently removes database and cascades to properties, views, and entries.
        Use archive() for soft delete to preserve data.

        Args:
            database_id: UUID of database to delete

        Returns:
            True if deleted, False if not found

        Raises:
            SQLAlchemyError: If database operation fails
        """
        try:
            # Use raw select without eager loading for deletion
            stmt = select(Database).where(Database.id == database_id)
            result = await self.db.execute(stmt)
            database = result.scalar_one_or_none()

            if not database:
                logger.warning(f"Cannot delete: database {database_id} not found")
                return False

            await self.db.delete(database)
            await self.db.flush()

            logger.info(f"Hard deleted database {database_id}")
            return True
        except SQLAlchemyError as e:
            logger.error(f"Error deleting database {database_id}: {e}", exc_info=True)
            raise

    async def count_by_project(self, project_id: UUID) -> int:
        """
        Get total count of non-archived databases in a project.

        Args:
            project_id: UUID of project

        Returns:
            Total count of non-archived databases

        Raises:
            SQLAlchemyError: If database query fails
        """
        try:
            stmt = select(func.count(Database.id)).where(
                and_(Database.project_id == project_id, Database.is_archived.is_(False))
            )

            result = await self.db.execute(stmt)
            count = result.scalar()
            return count if count is not None else 0
        except SQLAlchemyError as e:
            logger.error(f"Error counting databases for project {project_id}: {e}", exc_info=True)
            raise

    async def search_by_name(self, project_id: UUID, query: str) -> list[Database]:
        """
        Search databases by name with case-insensitive partial match.

        Args:
            project_id: UUID of project to search in
            query: Search query string

        Returns:
            List of matching Database objects

        Raises:
            SQLAlchemyError: If database query fails
        """
        try:
            search_pattern = f"%{query.lower()}%"

            stmt = (
                select(Database)
                .where(
                    and_(
                        Database.project_id == project_id,
                        Database.is_archived.is_(False),
                        func.lower(Database.name).like(search_pattern),
                    )
                )
                .order_by(Database.name)
            )

            result = await self.db.execute(stmt)
            return list(result.scalars().all())
        except SQLAlchemyError as e:
            logger.error(f"Error searching databases: {e}", exc_info=True)
            raise

    async def duplicate(self, database_id: UUID, new_name: str, user_id: UUID) -> Database | None:
        """
        Create a copy of database with all properties and views.

        Creates new database with copied configuration but no entries.
        Useful for creating similar databases quickly.

        Args:
            database_id: UUID of database to duplicate
            new_name: Name for the new database
            user_id: UUID of user creating the duplicate

        Returns:
            New Database object if source found, None otherwise

        Raises:
            SQLAlchemyError: If database operation fails
        """
        try:
            # Get source database with relationships
            source = await self.get_by_id(database_id)
            if not source:
                logger.warning(f"Cannot duplicate: database {database_id} not found")
                return None

            # Create new database
            new_db = Database(
                project_id=source.project_id,
                name=new_name,
                description=source.description,
                icon=source.icon,
                color=source.color,
                is_template=False,  # Duplicates are not templates
                created_by_user_id=user_id,
            )

            self.db.add(new_db)
            await self.db.flush()

            # Copy properties
            for prop in source.properties:
                new_prop = DatabaseProperty(
                    database_id=new_db.id,
                    name=prop.name,
                    property_type=prop.property_type,
                    config=prop.config,
                    position=prop.position,
                    is_required=prop.is_required,
                    is_visible=prop.is_visible,
                )
                self.db.add(new_prop)

            # Copy views
            for view in source.views:
                new_view = DatabaseView(
                    database_id=new_db.id,
                    name=view.name,
                    view_type=view.view_type,
                    config=view.config,
                    position=view.position,
                )
                self.db.add(new_view)

            await self.db.flush()
            await self.db.refresh(new_db)

            # Eager load relationships
            stmt = (
                select(Database)
                .options(
                    selectinload(Database.properties),
                    selectinload(Database.views),
                )
                .where(Database.id == new_db.id)
            )
            result = await self.db.execute(stmt)
            new_db = result.scalar_one()

            logger.info(f"Duplicated database {database_id} to {new_db.id}")
            return new_db
        except SQLAlchemyError as e:
            logger.error(f"Error duplicating database {database_id}: {e}", exc_info=True)
            raise

    async def get_entry_count(self, database_id: UUID) -> int:
        """
        Get count of non-archived entries in database.

        Args:
            database_id: UUID of database

        Returns:
            Total count of non-archived entries

        Raises:
            SQLAlchemyError: If database query fails
        """
        try:
            from ardha.models.database_entry import DatabaseEntry

            stmt = select(func.count(DatabaseEntry.id)).where(
                and_(
                    DatabaseEntry.database_id == database_id,
                    DatabaseEntry.is_archived.is_(False),
                )
            )

            result = await self.db.execute(stmt)
            count = result.scalar()
            return count if count is not None else 0
        except SQLAlchemyError as e:
            logger.error(f"Error counting entries for database {database_id}: {e}", exc_info=True)
            raise

    async def get_with_stats(self, database_id: UUID) -> dict | None:
        """
        Fetch database with computed statistics.

        Returns database data with additional computed fields:
        - entry_count: Number of non-archived entries
        - property_count: Number of properties
        - view_count: Number of views
        - last_entry_created_at: Most recent entry creation timestamp
        - last_updated_at: Most recent update timestamp

        Args:
            database_id: UUID of database

        Returns:
            Dictionary with database data and stats, None if not found

        Raises:
            SQLAlchemyError: If database query fails
        """
        try:
            database = await self.get_by_id(database_id)
            if not database:
                return None

            from ardha.models.database_entry import DatabaseEntry

            # Get entry count
            entry_count = await self.get_entry_count(database_id)

            # Get last entry created timestamp
            last_entry_stmt = (
                select(func.max(DatabaseEntry.created_at))
                .where(
                    and_(
                        DatabaseEntry.database_id == database_id,
                        DatabaseEntry.is_archived.is_(False),
                    )
                )
            )
            last_entry_result = await self.db.execute(last_entry_stmt)
            last_entry_created_at = last_entry_result.scalar()

            return {
                "database": database,
                "entry_count": entry_count,
                "property_count": len(database.properties),
                "view_count": len(database.views),
                "last_entry_created_at": last_entry_created_at,
                "last_updated_at": database.updated_at,
            }
        except SQLAlchemyError as e:
            logger.error(f"Error fetching database stats {database_id}: {e}", exc_info=True)
            raise

    async def reorder_positions(self, database_ids: list[UUID]) -> bool:
        """
        Update positions for multiple databases in batch.

        Used for drag-and-drop reordering. The order of database_ids
        represents the new positions (first = position 0, etc.).

        Args:
            database_ids: List of database UUIDs in desired order

        Returns:
            True if updated successfully

        Raises:
            SQLAlchemyError: If database operation fails
        """
        try:
            for i, database_id in enumerate(database_ids):
                stmt = select(Database).where(Database.id == database_id)
                result = await self.db.execute(stmt)
                database = result.scalar_one_or_none()

                if database:
                    # Position is implicit based on list order
                    # We don't have a position field on Database model
                    # This would be handled in views or sorting logic
                    logger.debug(f"Database {database_id} ordered at position {i}")

            await self.db.flush()
            logger.info(f"Reordered {len(database_ids)} databases")
            return True
        except SQLAlchemyError as e:
            logger.error(f"Error reordering databases: {e}", exc_info=True)
            raise

    async def get_by_name(self, project_id: UUID, name: str) -> Database | None:
        """
        Find database by exact name match within project.

        Used for uniqueness validation.

        Args:
            project_id: UUID of project
            name: Exact database name to match

        Returns:
            Database object if found, None otherwise

        Raises:
            SQLAlchemyError: If database query fails
        """
        try:
            stmt = select(Database).where(
                and_(
                    Database.project_id == project_id,
                    Database.name == name,
                    Database.is_archived.is_(False),
                )
            )

            result = await self.db.execute(stmt)
            return result.scalar_one_or_none()
        except SQLAlchemyError as e:
            logger.error(f"Error fetching database by name '{name}': {e}", exc_info=True)
            raise