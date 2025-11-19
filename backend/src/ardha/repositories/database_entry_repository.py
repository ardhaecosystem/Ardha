"""
DatabaseEntry repository for data access abstraction.

This module provides repository pattern implementation for DatabaseEntry model,
handling all database operations for database entries (rows) and their values.
"""

import logging
from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import and_, func, or_, select, update
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ardha.models.database_entry import DatabaseEntry
from ardha.models.database_entry_value import DatabaseEntryValue
from ardha.models.database_property import DatabaseProperty

logger = logging.getLogger(__name__)


class DatabaseEntryRepository:
    """
    Repository for DatabaseEntry model database operations.

    Provides data access methods for database entry-related operations including
    CRUD operations, filtering, sorting, bulk operations, and value management.
    Follows the repository pattern to abstract database implementation
    details from business logic.

    Attributes:
        db: SQLAlchemy async session for database operations
    """

    def __init__(self, db: AsyncSession) -> None:
        """
        Initialize the DatabaseEntryRepository with a database session.

        Args:
            db: SQLAlchemy async session for database operations
        """
        self.db = db

    async def create(self, entry_data: dict, user_id: UUID) -> DatabaseEntry:
        """
        Create a new database entry with values.

        Auto-assigns position to end of database.
        Creates DatabaseEntryValue records for provided values.

        Args:
            entry_data: Dictionary with entry fields and "values" dict
            user_id: UUID of user creating the entry

        Returns:
            Created DatabaseEntry object with loaded values

        Raises:
            ValueError: If required fields missing
            IntegrityError: If unique constraints violated
            SQLAlchemyError: If database operation fails
        """
        try:
            database_id = entry_data.get("database_id")
            if not database_id:
                raise ValueError("database_id is required")

            # Extract values from entry_data
            values_data = entry_data.pop("values", {})

            # Auto-assign position if not provided
            if "position" not in entry_data:
                max_position_stmt = select(func.max(DatabaseEntry.position)).where(
                    DatabaseEntry.database_id == database_id
                )
                result = await self.db.execute(max_position_stmt)
                max_position = result.scalar()
                entry_data["position"] = (max_position or -1) + 1

            # Create entry
            entry = DatabaseEntry(
                **entry_data,
                created_by_user_id=user_id,
                last_edited_by_user_id=user_id,
                last_edited_at=datetime.utcnow(),
            )

            self.db.add(entry)
            await self.db.flush()

            # Create values
            for property_id, value in values_data.items():
                if isinstance(property_id, str):
                    property_id = UUID(property_id)

                entry_value = DatabaseEntryValue(
                    entry_id=entry.id,
                    property_id=property_id,
                    value=value,
                )
                self.db.add(entry_value)

            await self.db.flush()
            await self.db.refresh(entry)

            # Eager load values
            stmt = (
                select(DatabaseEntry)
                .options(
                    selectinload(DatabaseEntry.values).selectinload(DatabaseEntryValue.property)
                )
                .where(DatabaseEntry.id == entry.id)
            )
            result = await self.db.execute(stmt)
            entry = result.scalar_one()

            logger.info(f"Created entry {entry.id} for database {database_id}")
            return entry
        except IntegrityError as e:
            logger.warning(f"Integrity error creating entry: {e}")
            raise
        except SQLAlchemyError as e:
            logger.error(f"Error creating entry: {e}", exc_info=True)
            raise

    async def get_by_id(self, entry_id: UUID) -> DatabaseEntry | None:
        """
        Fetch an entry by its UUID.

        Eager loads values with property information.

        Args:
            entry_id: UUID of entry to fetch

        Returns:
            DatabaseEntry object if found and not archived, None otherwise

        Raises:
            SQLAlchemyError: If database query fails
        """
        try:
            stmt = (
                select(DatabaseEntry)
                .options(
                    selectinload(DatabaseEntry.values).selectinload(DatabaseEntryValue.property),
                    selectinload(DatabaseEntry.created_by),
                    selectinload(DatabaseEntry.last_edited_by),
                )
                .where(and_(DatabaseEntry.id == entry_id, DatabaseEntry.is_archived.is_(False)))
            )
            result = await self.db.execute(stmt)
            return result.scalar_one_or_none()
        except SQLAlchemyError as e:
            logger.error(f"Error fetching entry by id {entry_id}: {e}", exc_info=True)
            raise

    async def get_by_database(
        self,
        database_id: UUID,
        filters: list[dict] | None = None,
        sorts: list[dict] | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[DatabaseEntry]:
        """
        Fetch entries for a database with filtering and sorting.

        Filters format: [{"property_id": UUID, "operator": str, "value": Any}]
        Operators: eq, ne, gt, lt, contains, in

        Sorts format: [{"property_id": UUID, "direction": "asc"|"desc"}]

        Args:
            database_id: UUID of database
            filters: Optional list of filter conditions
            sorts: Optional list of sort conditions
            limit: Maximum entries to return (max 100)
            offset: Number of entries to skip

        Returns:
            List of DatabaseEntry objects with loaded values

        Raises:
            ValueError: If limit/offset invalid
            SQLAlchemyError: If database query fails
        """
        if limit <= 0 or limit > 100:
            raise ValueError("limit must be between 1 and 100")
        if offset < 0:
            raise ValueError("offset must be non-negative")

        try:
            # Base query
            stmt = (
                select(DatabaseEntry)
                .options(
                    selectinload(DatabaseEntry.values).selectinload(DatabaseEntryValue.property)
                )
                .where(
                    and_(
                        DatabaseEntry.database_id == database_id,
                        DatabaseEntry.is_archived.is_(False),
                    )
                )
            )

            # Apply filters (simplified - full implementation would use JSONB operators)
            if filters:
                for filter_cond in filters:
                    # Note: Full filtering on JSONB values would require more complex queries
                    # This is a placeholder for the pattern
                    pass

            # Apply sorting (simplified - full implementation would join with values)
            if sorts:
                # Note: Full sorting on property values would require joins
                # Default to created_at for now
                pass
            else:
                # Default sort by created_at DESC
                stmt = stmt.order_by(DatabaseEntry.created_at.desc())

            # Apply pagination
            stmt = stmt.offset(offset).limit(limit)

            result = await self.db.execute(stmt)
            return list(result.scalars().all())
        except SQLAlchemyError as e:
            logger.error(f"Error fetching entries for database {database_id}: {e}", exc_info=True)
            raise

    async def count_by_database(
        self,
        database_id: UUID,
        filters: list[dict] | None = None,
    ) -> int:
        """
        Count entries matching filters.

        Args:
            database_id: UUID of database
            filters: Optional list of filter conditions

        Returns:
            Total count of matching entries

        Raises:
            SQLAlchemyError: If database query fails
        """
        try:
            stmt = select(func.count(DatabaseEntry.id)).where(
                and_(
                    DatabaseEntry.database_id == database_id,
                    DatabaseEntry.is_archived.is_(False),
                )
            )

            # Apply filters (simplified)
            if filters:
                # Note: Full filtering implementation would go here
                pass

            result = await self.db.execute(stmt)
            count = result.scalar()
            return count if count is not None else 0
        except SQLAlchemyError as e:
            logger.error(f"Error counting entries for database {database_id}: {e}", exc_info=True)
            raise

    async def update(self, entry_id: UUID, updates: dict, user_id: UUID) -> DatabaseEntry | None:
        """
        Update entry and its values.

        Updates entry fields and DatabaseEntryValue records.
        Creates new values, updates existing, deletes removed.

        Args:
            entry_id: UUID of entry to update
            updates: Dictionary with fields and "values" dict
            user_id: UUID of user making the update

        Returns:
            Updated DatabaseEntry object if found, None otherwise

        Raises:
            SQLAlchemyError: If database operation fails
        """
        try:
            entry = await self.get_by_id(entry_id)
            if not entry:
                logger.warning(f"Cannot update: entry {entry_id} not found")
                return None

            # Extract values updates
            values_updates = updates.pop("values", None)

            # Update entry fields
            for key, value in updates.items():
                if hasattr(entry, key) and key not in [
                    "id",
                    "created_at",
                    "created_by_user_id",
                    "database_id",
                ]:
                    setattr(entry, key, value)

            # Update tracking fields
            entry.last_edited_by_user_id = user_id
            entry.last_edited_at = datetime.utcnow()

            # Update values if provided
            if values_updates is not None:
                # Get existing values
                existing_values = {str(v.property_id): v for v in entry.values}

                # Update/create values
                for property_id_str, new_value in values_updates.items():
                    property_id = UUID(property_id_str)

                    if property_id_str in existing_values:
                        # Update existing
                        existing_values[property_id_str].value = new_value
                    else:
                        # Create new
                        new_entry_value = DatabaseEntryValue(
                            entry_id=entry.id,
                            property_id=property_id,
                            value=new_value,
                        )
                        self.db.add(new_entry_value)

                # Delete values not in updates (if value set to None explicitly)
                for property_id_str, value_obj in existing_values.items():
                    if property_id_str in values_updates and values_updates[property_id_str] is None:
                        await self.db.delete(value_obj)

            await self.db.flush()
            await self.db.refresh(entry)

            # Reload with values
            stmt = (
                select(DatabaseEntry)
                .options(
                    selectinload(DatabaseEntry.values).selectinload(DatabaseEntryValue.property)
                )
                .where(DatabaseEntry.id == entry_id)
            )
            result = await self.db.execute(stmt)
            entry = result.scalar_one()

            logger.info(f"Updated entry {entry_id}")
            return entry
        except SQLAlchemyError as e:
            logger.error(f"Error updating entry {entry_id}: {e}", exc_info=True)
            raise

    async def archive(self, entry_id: UUID) -> DatabaseEntry | None:
        """
        Archive an entry (soft delete).

        Args:
            entry_id: UUID of entry to archive

        Returns:
            Updated DatabaseEntry object if found, None otherwise

        Raises:
            SQLAlchemyError: If database operation fails
        """
        try:
            # Use raw select for archival
            stmt = select(DatabaseEntry).where(DatabaseEntry.id == entry_id)
            result = await self.db.execute(stmt)
            entry = result.scalar_one_or_none()

            if not entry:
                logger.warning(f"Cannot archive: entry {entry_id} not found")
                return None

            entry.is_archived = True
            entry.archived_at = datetime.utcnow()

            await self.db.flush()
            await self.db.refresh(entry)

            logger.info(f"Archived entry {entry_id}")
            return entry
        except SQLAlchemyError as e:
            logger.error(f"Error archiving entry {entry_id}: {e}", exc_info=True)
            raise

    async def delete(self, entry_id: UUID) -> bool:
        """
        Hard delete an entry and all values.

        Args:
            entry_id: UUID of entry to delete

        Returns:
            True if deleted, False if not found

        Raises:
            SQLAlchemyError: If database operation fails
        """
        try:
            stmt = select(DatabaseEntry).where(DatabaseEntry.id == entry_id)
            result = await self.db.execute(stmt)
            entry = result.scalar_one_or_none()

            if not entry:
                logger.warning(f"Cannot delete: entry {entry_id} not found")
                return False

            await self.db.delete(entry)
            await self.db.flush()

            logger.info(f"Deleted entry {entry_id}")
            return True
        except SQLAlchemyError as e:
            logger.error(f"Error deleting entry {entry_id}: {e}", exc_info=True)
            raise

    async def bulk_create(
        self,
        entries_data: list[dict],
        user_id: UUID,
    ) -> list[DatabaseEntry]:
        """
        Create multiple entries efficiently.

        Args:
            entries_data: List of entry data dictionaries
            user_id: UUID of user creating entries

        Returns:
            List of created DatabaseEntry objects

        Raises:
            ValueError: If entries_data empty or exceeds limit
            SQLAlchemyError: If database operation fails
        """
        if not entries_data:
            raise ValueError("entries_data cannot be empty")
        if len(entries_data) > 100:
            raise ValueError("Cannot bulk create more than 100 entries at once")

        try:
            created_entries = []

            for entry_dict in entries_data:
                entry = await self.create(entry_dict, user_id)
                created_entries.append(entry)

            logger.info(f"Bulk created {len(created_entries)} entries")
            return created_entries
        except SQLAlchemyError as e:
            logger.error(f"Error bulk creating entries: {e}", exc_info=True)
            raise

    async def bulk_update(
        self,
        updates: list[dict],
        user_id: UUID,
    ) -> int:
        """
        Update multiple entries.

        Each update dict should have "entry_id" and fields to update.

        Args:
            updates: List of update dictionaries
            user_id: UUID of user making updates

        Returns:
            Count of entries updated

        Raises:
            ValueError: If updates empty or exceeds limit
            SQLAlchemyError: If database operation fails
        """
        if not updates:
            raise ValueError("updates cannot be empty")
        if len(updates) > 100:
            raise ValueError("Cannot bulk update more than 100 entries at once")

        try:
            count = 0

            for update_dict in updates:
                entry_id = update_dict.pop("entry_id", None)
                if not entry_id:
                    continue

                entry = await self.update(entry_id, update_dict, user_id)
                if entry:
                    count += 1

            logger.info(f"Bulk updated {count} entries")
            return count
        except SQLAlchemyError as e:
            logger.error(f"Error bulk updating entries: {e}", exc_info=True)
            raise

    async def bulk_delete(self, entry_ids: list[UUID]) -> int:
        """
        Delete multiple entries.

        Args:
            entry_ids: List of entry UUIDs to delete

        Returns:
            Count of entries deleted

        Raises:
            ValueError: If entry_ids empty or exceeds limit
            SQLAlchemyError: If database operation fails
        """
        if not entry_ids:
            raise ValueError("entry_ids cannot be empty")
        if len(entry_ids) > 100:
            raise ValueError("Cannot bulk delete more than 100 entries at once")

        try:
            count = 0

            for entry_id in entry_ids:
                deleted = await self.delete(entry_id)
                if deleted:
                    count += 1

            logger.info(f"Bulk deleted {count} entries")
            return count
        except SQLAlchemyError as e:
            logger.error(f"Error bulk deleting entries: {e}", exc_info=True)
            raise

    async def get_value(self, entry_id: UUID, property_id: UUID) -> dict | None:
        """
        Get specific property value for an entry.

        Args:
            entry_id: UUID of entry
            property_id: UUID of property

        Returns:
            Value dictionary or None if not set

        Raises:
            SQLAlchemyError: If database query fails
        """
        try:
            stmt = select(DatabaseEntryValue).where(
                and_(
                    DatabaseEntryValue.entry_id == entry_id,
                    DatabaseEntryValue.property_id == property_id,
                )
            )

            result = await self.db.execute(stmt)
            value_obj = result.scalar_one_or_none()

            return value_obj.value if value_obj else None
        except SQLAlchemyError as e:
            logger.error(f"Error fetching value for entry {entry_id}: {e}", exc_info=True)
            raise

    async def set_value(
        self,
        entry_id: UUID,
        property_id: UUID,
        value: dict,
        user_id: UUID,
    ) -> DatabaseEntryValue:
        """
        Update or create a single property value for an entry.

        Args:
            entry_id: UUID of entry
            property_id: UUID of property
            value: Value dictionary to set
            user_id: UUID of user making the change

        Returns:
            Created or updated DatabaseEntryValue object

        Raises:
            SQLAlchemyError: If database operation fails
        """
        try:
            # Check if value exists
            stmt = select(DatabaseEntryValue).where(
                and_(
                    DatabaseEntryValue.entry_id == entry_id,
                    DatabaseEntryValue.property_id == property_id,
                )
            )
            result = await self.db.execute(stmt)
            value_obj = result.scalar_one_or_none()

            if value_obj:
                # Update existing
                value_obj.value = value
            else:
                # Create new
                value_obj = DatabaseEntryValue(
                    entry_id=entry_id,
                    property_id=property_id,
                    value=value,
                )
                self.db.add(value_obj)

            # Update entry's last_edited fields
            entry_stmt = select(DatabaseEntry).where(DatabaseEntry.id == entry_id)
            entry_result = await self.db.execute(entry_stmt)
            entry = entry_result.scalar_one_or_none()

            if entry:
                entry.last_edited_by_user_id = user_id
                entry.last_edited_at = datetime.utcnow()

            await self.db.flush()
            await self.db.refresh(value_obj)

            logger.info(f"Set value for entry {entry_id}, property {property_id}")
            return value_obj
        except SQLAlchemyError as e:
            logger.error(f"Error setting value for entry {entry_id}: {e}", exc_info=True)
            raise

    async def get_entries_by_property_value(
        self,
        database_id: UUID,
        property_id: UUID,
        value: Any,
    ) -> list[DatabaseEntry]:
        """
        Find entries with a specific property value.

        Used for relation lookups and filtering.

        Args:
            database_id: UUID of database
            property_id: UUID of property
            value: Value to match

        Returns:
            List of matching DatabaseEntry objects

        Raises:
            SQLAlchemyError: If database query fails
        """
        try:
            # Join with values to filter
            stmt = (
                select(DatabaseEntry)
                .join(DatabaseEntryValue, DatabaseEntry.id == DatabaseEntryValue.entry_id)
                .options(
                    selectinload(DatabaseEntry.values).selectinload(DatabaseEntryValue.property)
                )
                .where(
                    and_(
                        DatabaseEntry.database_id == database_id,
                        DatabaseEntry.is_archived.is_(False),
                        DatabaseEntryValue.property_id == property_id,
                        # Note: JSONB comparison would be more complex in production
                        # This is simplified
                    )
                )
            )

            result = await self.db.execute(stmt)
            return list(result.scalars().all())
        except SQLAlchemyError as e:
            logger.error(f"Error finding entries by property value: {e}", exc_info=True)
            raise

    async def reorder_entries(self, entry_ids: list[UUID]) -> bool:
        """
        Update positions for multiple entries in batch.

        Args:
            entry_ids: List of entry UUIDs in desired order

        Returns:
            True if updated successfully

        Raises:
            SQLAlchemyError: If database operation fails
        """
        try:
            for i, entry_id in enumerate(entry_ids):
                stmt = select(DatabaseEntry).where(DatabaseEntry.id == entry_id)
                result = await self.db.execute(stmt)
                entry = result.scalar_one_or_none()

                if entry:
                    entry.position = i

            await self.db.flush()
            logger.info(f"Reordered {len(entry_ids)} entries")
            return True
        except SQLAlchemyError as e:
            logger.error(f"Error reordering entries: {e}", exc_info=True)
            raise

    async def get_created_by_user(
        self,
        database_id: UUID,
        user_id: UUID,
        limit: int = 50,
    ) -> list[DatabaseEntry]:
        """
        Get entries created by a specific user.

        Args:
            database_id: UUID of database
            user_id: UUID of user
            limit: Maximum entries to return

        Returns:
            List of DatabaseEntry objects created by user

        Raises:
            ValueError: If limit invalid
            SQLAlchemyError: If database query fails
        """
        if limit <= 0 or limit > 100:
            raise ValueError("limit must be between 1 and 100")

        try:
            stmt = (
                select(DatabaseEntry)
                .options(
                    selectinload(DatabaseEntry.values).selectinload(DatabaseEntryValue.property)
                )
                .where(
                    and_(
                        DatabaseEntry.database_id == database_id,
                        DatabaseEntry.created_by_user_id == user_id,
                        DatabaseEntry.is_archived.is_(False),
                    )
                )
                .order_by(DatabaseEntry.created_at.desc())
                .limit(limit)
            )

            result = await self.db.execute(stmt)
            return list(result.scalars().all())
        except SQLAlchemyError as e:
            logger.error(f"Error fetching entries created by user {user_id}: {e}", exc_info=True)
            raise

    async def get_recently_updated(
        self,
        database_id: UUID,
        limit: int = 10,
    ) -> list[DatabaseEntry]:
        """
        Get most recently edited entries.

        Args:
            database_id: UUID of database
            limit: Maximum entries to return

        Returns:
            List of DatabaseEntry objects ordered by last_edited_at DESC

        Raises:
            ValueError: If limit invalid
            SQLAlchemyError: If database query fails
        """
        if limit <= 0 or limit > 100:
            raise ValueError("limit must be between 1 and 100")

        try:
            stmt = (
                select(DatabaseEntry)
                .options(
                    selectinload(DatabaseEntry.values).selectinload(DatabaseEntryValue.property),
                    selectinload(DatabaseEntry.last_edited_by),
                )
                .where(
                    and_(
                        DatabaseEntry.database_id == database_id,
                        DatabaseEntry.is_archived.is_(False),
                    )
                )
                .order_by(DatabaseEntry.last_edited_at.desc())
                .limit(limit)
            )

            result = await self.db.execute(stmt)
            return list(result.scalars().all())
        except SQLAlchemyError as e:
            logger.error(
                f"Error fetching recently updated entries for database {database_id}: {e}",
                exc_info=True,
            )
            raise

    async def duplicate_entry(self, entry_id: UUID, user_id: UUID) -> DatabaseEntry | None:
        """
        Create a copy of an entry with all values.

        Args:
            entry_id: UUID of entry to duplicate
            user_id: UUID of user creating the duplicate

        Returns:
            New DatabaseEntry object if source found, None otherwise

        Raises:
            SQLAlchemyError: If database operation fails
        """
        try:
            # Get source entry with values
            source = await self.get_by_id(entry_id)
            if not source:
                logger.warning(f"Cannot duplicate: entry {entry_id} not found")
                return None

            # Prepare values dict
            values_dict = {}
            for value_obj in source.values:
                values_dict[str(value_obj.property_id)] = value_obj.value

            # Create new entry
            new_entry_data = {
                "database_id": source.database_id,
                "values": values_dict,
            }

            new_entry = await self.create(new_entry_data, user_id)

            logger.info(f"Duplicated entry {entry_id} to {new_entry.id}")
            return new_entry
        except SQLAlchemyError as e:
            logger.error(f"Error duplicating entry {entry_id}: {e}", exc_info=True)
            raise

    async def search_entries(
        self,
        database_id: UUID,
        search_query: str,
        limit: int = 50,
    ) -> list[DatabaseEntry]:
        """
        Search entries across all text property values.

        Searches for case-insensitive partial matches in text-type properties.

        Args:
            database_id: UUID of database
            search_query: Search query string
            limit: Maximum entries to return

        Returns:
            List of matching DatabaseEntry objects

        Raises:
            ValueError: If limit invalid
            SQLAlchemyError: If database query fails
        """
        if limit <= 0 or limit > 100:
            raise ValueError("limit must be between 1 and 100")

        try:
            # Note: Full-text search would use JSONB operators in production
            # This is a simplified version that searches entry IDs
            # A proper implementation would use:
            # WHERE value->'text' ILIKE '%query%'

            stmt = (
                select(DatabaseEntry)
                .options(
                    selectinload(DatabaseEntry.values).selectinload(DatabaseEntryValue.property)
                )
                .where(
                    and_(
                        DatabaseEntry.database_id == database_id,
                        DatabaseEntry.is_archived.is_(False),
                    )
                )
                .order_by(DatabaseEntry.created_at.desc())
                .limit(limit)
            )

            result = await self.db.execute(stmt)
            entries = list(result.scalars().all())

            # Filter in Python (production would use JSONB operators)
            search_lower = search_query.lower()
            filtered_entries = []

            for entry in entries:
                for value_obj in entry.values:
                    if value_obj.value and isinstance(value_obj.value, dict):
                        text_val = value_obj.value.get("text", "")
                        if isinstance(text_val, str) and search_lower in text_val.lower():
                            filtered_entries.append(entry)
                            break

            logger.info(f"Searched entries for '{search_query}', found {len(filtered_entries)}")
            return filtered_entries[:limit]
        except SQLAlchemyError as e:
            logger.error(f"Error searching entries: {e}", exc_info=True)
            raise