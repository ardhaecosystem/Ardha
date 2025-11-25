"""
Database entry service for business logic.

This module provides business logic for database entry management, including CRUD operations,
value validation, formula/rollup recalculation, bulk operations, and permission checks.
"""

import logging
from typing import Any, Dict, List, Optional, Tuple
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from ardha.core.exceptions import (
    DatabaseEntryNotFoundError,
    DatabaseNotFoundError,
    DatabasePropertyNotFoundError,
    InvalidPropertyValueError,
)
from ardha.models.database_entry import DatabaseEntry
from ardha.repositories.database_entry_repository import DatabaseEntryRepository
from ardha.repositories.database_property_repository import DatabasePropertyRepository
from ardha.repositories.database_repository import DatabaseRepository
from ardha.services.project_service import InsufficientPermissionsError, ProjectService

logger = logging.getLogger(__name__)


class DatabaseEntryService:
    """
    Service for database entry management business logic.

    Handles entry CRUD operations, value validation, formula/rollup recalculation,
    bulk operations, and permission checks. Enforces role-based access control
    through ProjectService integration.

    Attributes:
        db: SQLAlchemy async session
        entry_repository: DatabaseEntryRepository for data access
        property_repository: DatabasePropertyRepository for validation
        database_repository: DatabaseRepository for database access
        project_service: ProjectService for permission checks
    """

    def __init__(self, db: AsyncSession) -> None:
        """
        Initialize DatabaseEntryService.

        Args:
            db: SQLAlchemy async session for database operations
        """
        self.db = db
        self.entry_repository = DatabaseEntryRepository(db)
        self.property_repository = DatabasePropertyRepository(db)
        self.database_repository = DatabaseRepository(db)
        self.project_service = ProjectService(db)

    async def create_entry(
        self,
        database_id: UUID,
        entry_data: Dict[str, Any],
        user_id: UUID,
    ) -> DatabaseEntry:
        """
        Create a new database entry with validated values.

        Args:
            database_id: UUID of the database
            entry_data: Dictionary with "values" dict mapping property_id to value
            user_id: UUID of user creating entry

        Returns:
            Created DatabaseEntry object with values

        Raises:
            DatabaseNotFoundError: If database not found
            InsufficientPermissionsError: If user lacks member permissions
            DatabasePropertyNotFoundError: If required property missing
            InvalidPropertyValueError: If value validation fails
        """
        # Get database
        database = await self.database_repository.get_by_id(database_id)
        if not database:
            raise DatabaseNotFoundError(f"Database {database_id} not found")

        # Check user has member+ permission
        if not await self.project_service.check_permission(database.project_id, user_id, "member"):
            logger.warning(
                f"User {user_id} lacks permission to create entry in database {database_id}"
            )
            raise InsufficientPermissionsError("Only project members can create entries")

        # Get required properties
        required_props = await self.property_repository.get_required_properties(database_id)
        values = entry_data.get("values", {})

        # Check all required properties are provided
        for prop in required_props:
            prop_id_str = str(prop.id)
            if prop_id_str not in values or values[prop_id_str] is None:
                raise InvalidPropertyValueError(
                    f"Required property '{prop.name}' (ID: {prop.id}) must be provided"
                )

        # Validate all provided values
        is_valid, error = await self.validate_entry_values(database_id, values)
        if not is_valid:
            raise InvalidPropertyValueError(error or "Invalid entry values")

        logger.info(f"Creating entry in database {database_id}")

        # Prepare entry data
        entry_dict = {
            "database_id": database_id,
            "values": values,
        }

        # Create entry
        entry = await self.entry_repository.create(entry_dict, user_id)
        await self.db.flush()

        # Calculate formulas and rollups for new entry
        from ardha.services.formula_service import FormulaService

        formula_service = FormulaService(self.db)
        await formula_service.recalculate_entry_formulas(entry.id)

        # Update any rollups that reference this entry
        # Note: RollupService would be used here in full implementation
        # For MVP, this is a placeholder

        await self.db.refresh(entry)

        # Ensure relationships are loaded for Pydantic validation
        await self.db.refresh(entry, ["values", "created_by", "last_edited_by"])

        logger.info(f"Created entry {entry.id}")
        return entry

    async def get_entry(
        self,
        entry_id: UUID,
        user_id: UUID,
    ) -> DatabaseEntry:
        """
        Get entry by ID with permission check.

        Args:
            entry_id: UUID of the entry
            user_id: UUID of requesting user

        Returns:
            DatabaseEntry object with values loaded

        Raises:
            DatabaseEntryNotFoundError: If entry not found
            InsufficientPermissionsError: If user lacks view permissions
        """
        entry = await self.entry_repository.get_by_id(entry_id)
        if not entry:
            raise DatabaseEntryNotFoundError(f"Entry {entry_id} not found")

        # Get database to check permissions
        database = await self.database_repository.get_by_id(entry.database_id)
        if not database:
            raise DatabaseNotFoundError(f"Database {entry.database_id} not found")

        # Check user has view+ permission
        if not await self.project_service.check_permission(database.project_id, user_id, "viewer"):
            logger.warning(f"User {user_id} lacks permission to view entry {entry_id}")
            raise InsufficientPermissionsError("You do not have permission to view this entry")

        return entry

    async def list_entries(
        self,
        database_id: UUID,
        filters: Optional[List[Dict]] = None,
        sorts: Optional[List[Dict]] = None,
        limit: int = 50,
        offset: int = 0,
        user_id: Optional[UUID] = None,
    ) -> Tuple[List[DatabaseEntry], int]:
        """
        List entries in a database with filtering and sorting.

        Args:
            database_id: UUID of the database
            filters: Optional list of filter conditions
            sorts: Optional list of sort conditions
            limit: Maximum entries to return (max 100)
            offset: Number of entries to skip
            user_id: UUID of requesting user

        Returns:
            Tuple of (List of DatabaseEntry objects, total count)

        Raises:
            DatabaseNotFoundError: If database not found
            InsufficientPermissionsError: If user lacks view permissions
        """
        # Get database
        database = await self.database_repository.get_by_id(database_id)
        if not database:
            raise DatabaseNotFoundError(f"Database {database_id} not found")

        # Check user has view+ permission
        if user_id:
            if not await self.project_service.check_permission(
                database.project_id, user_id, "viewer"
            ):
                logger.warning(
                    f"User {user_id} lacks permission to list entries in database {database_id}"
                )
                raise InsufficientPermissionsError("You do not have permission to view entries")

        # Get entries with filters
        entries = await self.entry_repository.get_by_database(
            database_id,
            filters=filters,
            sorts=sorts,
            limit=limit,
            offset=offset,
        )

        # Get total count
        total = await self.entry_repository.count_by_database(database_id, filters=filters)

        logger.info(f"Listed {len(entries)} entries for database {database_id}")
        return entries, total

    async def update_entry(
        self,
        entry_id: UUID,
        updates: Dict[str, Any],
        user_id: UUID,
    ) -> DatabaseEntry:
        """
        Update entry and recalculate dependent formulas/rollups.

        Args:
            entry_id: UUID of entry to update
            updates: Dictionary with "values" dict to update
            user_id: UUID of user making update

        Returns:
            Updated DatabaseEntry object

        Raises:
            DatabaseEntryNotFoundError: If entry not found
            InsufficientPermissionsError: If user lacks member permissions
            InvalidPropertyValueError: If value validation fails
        """
        entry = await self.entry_repository.get_by_id(entry_id)
        if not entry:
            raise DatabaseEntryNotFoundError(f"Entry {entry_id} not found")

        # Get database to check permissions
        database = await self.database_repository.get_by_id(entry.database_id)
        if not database:
            raise DatabaseNotFoundError(f"Database {entry.database_id} not found")

        # Check user has member+ permission
        if not await self.project_service.check_permission(database.project_id, user_id, "member"):
            logger.warning(f"User {user_id} lacks permission to update entry {entry_id}")
            raise InsufficientPermissionsError("Only project members can update entries")

        # Validate updated values (skip required check for updates)
        if "values" in updates:
            is_valid, error = await self.validate_entry_values(
                entry.database_id, updates["values"], check_required=False
            )
            if not is_valid:
                raise InvalidPropertyValueError(error or "Invalid entry values")

        logger.info(f"Updating entry {entry_id}")

        # Update entry
        updated = await self.entry_repository.update(entry_id, updates, user_id)
        if not updated:
            raise DatabaseEntryNotFoundError(f"Entry {entry_id} not found")
        await self.db.flush()

        # Recalculate formulas that depend on changed values
        from ardha.services.formula_service import FormulaService

        formula_service = FormulaService(self.db)
        await formula_service.recalculate_entry_formulas(entry_id)

        # Update rollups that reference this entry
        # Note: RollupService would be used here in full implementation

        await self.db.refresh(updated)

        # Ensure relationships are loaded for Pydantic validation
        await self.db.refresh(updated, ["values", "created_by", "last_edited_by"])

        logger.info(f"Updated entry {entry_id}")
        return updated

    async def archive_entry(
        self,
        entry_id: UUID,
        user_id: UUID,
    ) -> DatabaseEntry:
        """
        Archive an entry (soft delete).

        Args:
            entry_id: UUID of entry to archive
            user_id: UUID of user making request

        Returns:
            Archived DatabaseEntry object

        Raises:
            DatabaseEntryNotFoundError: If entry not found
            InsufficientPermissionsError: If user lacks member permissions
        """
        entry = await self.entry_repository.get_by_id(entry_id)
        if not entry:
            raise DatabaseEntryNotFoundError(f"Entry {entry_id} not found")

        # Get database to check permissions
        database = await self.database_repository.get_by_id(entry.database_id)
        if not database:
            raise DatabaseNotFoundError(f"Database {entry.database_id} not found")

        # Check user has member+ permission
        if not await self.project_service.check_permission(database.project_id, user_id, "member"):
            logger.warning(f"User {user_id} lacks permission to archive entry {entry_id}")
            raise InsufficientPermissionsError("Only project members can archive entries")

        logger.info(f"Archiving entry {entry_id}")
        archived = await self.entry_repository.archive(entry_id)
        if not archived:
            raise DatabaseEntryNotFoundError(f"Entry {entry_id} not found")
        await self.db.flush()

        # Ensure relationships are loaded for Pydantic validation
        await self.db.refresh(archived, ["values", "created_by", "last_edited_by"])

        logger.info(f"Archived entry {entry_id}")
        return archived

    async def delete_entry(
        self,
        entry_id: UUID,
        user_id: UUID,
    ) -> bool:
        """
        Permanently delete an entry.

        Updates any rollups that referenced this entry.

        Args:
            entry_id: UUID of entry to delete
            user_id: UUID of user making request

        Returns:
            True if deleted successfully

        Raises:
            DatabaseEntryNotFoundError: If entry not found
            InsufficientPermissionsError: If user lacks admin permissions
        """
        entry = await self.entry_repository.get_by_id(entry_id)
        if not entry:
            raise DatabaseEntryNotFoundError(f"Entry {entry_id} not found")

        # Get database to check permissions
        database = await self.database_repository.get_by_id(entry.database_id)
        if not database:
            raise DatabaseNotFoundError(f"Database {entry.database_id} not found")

        # Check user has admin+ permission
        if not await self.project_service.check_permission(database.project_id, user_id, "admin"):
            logger.warning(f"User {user_id} lacks permission to delete entry {entry_id}")
            raise InsufficientPermissionsError("Only project admin or owner can delete entries")

        logger.info(f"Deleting entry {entry_id}")

        # Update any rollups that reference this entry
        # Note: RollupService would be used here in full implementation

        success = await self.entry_repository.delete(entry_id)
        await self.db.flush()

        logger.info(f"Deleted entry {entry_id}")
        return success

    async def bulk_create_entries(
        self,
        database_id: UUID,
        entries_data: List[Dict[str, Any]],
        user_id: UUID,
    ) -> List[DatabaseEntry]:
        """
        Create multiple entries efficiently.

        Args:
            database_id: UUID of the database
            entries_data: List of entry data dictionaries
            user_id: UUID of user creating entries

        Returns:
            List of created DatabaseEntry objects

        Raises:
            DatabaseNotFoundError: If database not found
            InsufficientPermissionsError: If user lacks member permissions
            InvalidPropertyValueError: If any value validation fails
        """
        # Get database
        database = await self.database_repository.get_by_id(database_id)
        if not database:
            raise DatabaseNotFoundError(f"Database {database_id} not found")

        # Check user has member+ permission
        if not await self.project_service.check_permission(database.project_id, user_id, "member"):
            logger.warning(
                f"User {user_id} lacks permission to create entries in database {database_id}"
            )
            raise InsufficientPermissionsError("Only project members can create entries")

        # Validate all entries before creating
        for i, entry_dict in enumerate(entries_data):
            values = entry_dict.get("values", {})
            is_valid, error = await self.validate_entry_values(database_id, values)
            if not is_valid:
                raise InvalidPropertyValueError(f"Entry {i}: {error}")

        logger.info(f"Bulk creating {len(entries_data)} entries in database {database_id}")

        # Add database_id to each entry
        for entry_dict in entries_data:
            entry_dict["database_id"] = database_id

        # Bulk create
        entries = await self.entry_repository.bulk_create(entries_data, user_id)
        await self.db.flush()

        # Batch calculate formulas and rollups
        from ardha.services.formula_service import FormulaService

        formula_service = FormulaService(self.db)
        for entry in entries:
            await formula_service.recalculate_entry_formulas(entry.id)

        logger.info(f"Bulk created {len(entries)} entries")
        return entries

    async def bulk_update_entries(
        self,
        updates: List[Tuple[UUID, Dict[str, Any]]],
        user_id: UUID,
    ) -> int:
        """
        Update multiple entries.

        Args:
            updates: List of tuples (entry_id, updates_dict)
            user_id: UUID of user making updates

        Returns:
            Count of entries updated

        Raises:
            InsufficientPermissionsError: If user lacks member permissions
            InvalidPropertyValueError: If any value validation fails
        """
        if not updates:
            return 0

        # Get first entry to check database and permissions
        first_entry_id = updates[0][0]
        first_entry = await self.entry_repository.get_by_id(first_entry_id)
        if not first_entry:
            raise DatabaseEntryNotFoundError(f"Entry {first_entry_id} not found")

        database = await self.database_repository.get_by_id(first_entry.database_id)
        if not database:
            raise DatabaseNotFoundError(f"Database {first_entry.database_id} not found")

        # Check user has member+ permission
        if not await self.project_service.check_permission(database.project_id, user_id, "member"):
            logger.warning(f"User {user_id} lacks permission to update entries")
            raise InsufficientPermissionsError("Only project members can update entries")

        logger.info(f"Bulk updating {len(updates)} entries")

        # Convert to repository format
        update_dicts = []
        for entry_id, update_data in updates:
            update_dict = {"entry_id": entry_id, **update_data}
            update_dicts.append(update_dict)

        # Bulk update
        count = await self.entry_repository.bulk_update(update_dicts, user_id)
        await self.db.flush()

        # Batch recalculate formulas/rollups
        from ardha.services.formula_service import FormulaService

        formula_service = FormulaService(self.db)
        for entry_id, _ in updates:
            await formula_service.recalculate_entry_formulas(entry_id)

        logger.info(f"Bulk updated {count} entries")
        return count

    async def bulk_delete_entries(
        self,
        entry_ids: List[UUID],
        user_id: UUID,
    ) -> int:
        """
        Delete multiple entries.

        Args:
            entry_ids: List of entry UUIDs to delete
            user_id: UUID of user making request

        Returns:
            Count of entries deleted

        Raises:
            InsufficientPermissionsError: If user lacks admin permissions
        """
        if not entry_ids:
            return 0

        # Get first entry to check database and permissions
        first_entry = await self.entry_repository.get_by_id(entry_ids[0])
        if not first_entry:
            raise DatabaseEntryNotFoundError(f"Entry {entry_ids[0]} not found")

        database = await self.database_repository.get_by_id(first_entry.database_id)
        if not database:
            raise DatabaseNotFoundError(f"Database {first_entry.database_id} not found")

        # Check user has admin+ permission
        if not await self.project_service.check_permission(database.project_id, user_id, "admin"):
            logger.warning(f"User {user_id} lacks permission to delete entries")
            raise InsufficientPermissionsError("Only project admin or owner can delete entries")

        logger.info(f"Bulk deleting {len(entry_ids)} entries")

        # Bulk delete
        count = await self.entry_repository.bulk_delete(entry_ids)
        await self.db.flush()

        # Update affected rollups
        # Note: RollupService would be used here

        logger.info(f"Bulk deleted {count} entries")
        return count

    async def duplicate_entry(
        self,
        entry_id: UUID,
        user_id: UUID,
    ) -> DatabaseEntry:
        """
        Create a duplicate of an entry.

        Args:
            entry_id: UUID of entry to duplicate
            user_id: UUID of user creating duplicate

        Returns:
            New DatabaseEntry object

        Raises:
            DatabaseEntryNotFoundError: If entry not found
            InsufficientPermissionsError: If user lacks member permissions
        """
        entry = await self.entry_repository.get_by_id(entry_id)
        if not entry:
            raise DatabaseEntryNotFoundError(f"Entry {entry_id} not found")

        # Get database to check permissions
        database = await self.database_repository.get_by_id(entry.database_id)
        if not database:
            raise DatabaseNotFoundError(f"Database {entry.database_id} not found")

        # Check user has member+ permission
        if not await self.project_service.check_permission(database.project_id, user_id, "member"):
            logger.warning(f"User {user_id} lacks permission to duplicate entry {entry_id}")
            raise InsufficientPermissionsError("Only project members can duplicate entries")

        logger.info(f"Duplicating entry {entry_id}")
        new_entry = await self.entry_repository.duplicate_entry(entry_id, user_id)
        if not new_entry:
            raise DatabaseEntryNotFoundError(f"Entry {entry_id} not found")
        await self.db.flush()

        # Recalculate formulas for new entry
        from ardha.services.formula_service import FormulaService

        formula_service = FormulaService(self.db)
        await formula_service.recalculate_entry_formulas(new_entry.id)

        # Ensure relationships are loaded for Pydantic validation
        await self.db.refresh(new_entry, ["values", "created_by", "last_edited_by"])

        logger.info(f"Duplicated entry {entry_id}")
        return new_entry

    async def set_entry_value(
        self,
        entry_id: UUID,
        property_id: UUID,
        value: Any,
        user_id: UUID,
    ) -> DatabaseEntry:
        """
        Set a single property value for an entry.

        Args:
            entry_id: UUID of the entry
            property_id: UUID of the property
            value: Value to set (in property format)
            user_id: UUID of user making change

        Returns:
            Updated DatabaseEntry object

        Raises:
            DatabaseEntryNotFoundError: If entry not found
            DatabasePropertyNotFoundError: If property not found
            InsufficientPermissionsError: If user lacks member permissions
            InvalidPropertyValueError: If value validation fails
        """
        entry = await self.entry_repository.get_by_id(entry_id)
        if not entry:
            raise DatabaseEntryNotFoundError(f"Entry {entry_id} not found")

        # Get property
        prop = await self.property_repository.get_by_id(property_id)
        if not prop:
            raise DatabasePropertyNotFoundError(f"Property {property_id} not found")

        # Verify property belongs to same database
        if prop.database_id != entry.database_id:
            raise InvalidPropertyValueError(
                f"Property {property_id} does not belong to database {entry.database_id}"
            )

        # Get database to check permissions
        database = await self.database_repository.get_by_id(entry.database_id)
        if not database:
            raise DatabaseNotFoundError(f"Database {entry.database_id} not found")

        # Check user has member+ permission
        if not await self.project_service.check_permission(database.project_id, user_id, "member"):
            logger.warning(f"User {user_id} lacks permission to update entry {entry_id}")
            raise InsufficientPermissionsError("Only project members can update entries")

        # Validate value for property type
        if not prop.validate_value(value):
            raise InvalidPropertyValueError(
                f"Invalid value for property '{prop.name}' of type {prop.property_type}",
                property_name=prop.name,
                property_type=prop.property_type,
                value=value,
            )

        logger.info(f"Setting value for entry {entry_id}, property {property_id}")

        # Set value
        await self.entry_repository.set_value(entry_id, property_id, value, user_id)
        await self.db.flush()

        # Recalculate dependent formulas/rollups
        from ardha.services.formula_service import FormulaService

        formula_service = FormulaService(self.db)
        await formula_service.recalculate_entry_formulas(entry_id)

        # Reload entry
        updated_entry = await self.entry_repository.get_by_id(entry_id)
        if not updated_entry:
            raise DatabaseEntryNotFoundError(f"Entry {entry_id} not found")

        # Ensure relationships are loaded for Pydantic validation
        await self.db.refresh(updated_entry, ["values", "created_by", "last_edited_by"])

        logger.info(f"Set value for entry {entry_id}")
        return updated_entry

    async def reorder_entries(
        self,
        entry_ids: List[UUID],
        user_id: UUID,
    ) -> bool:
        """
        Reorder entries for display.

        Args:
            entry_ids: List of entry UUIDs in desired order
            user_id: UUID of user making request

        Returns:
            True if reordered successfully

        Raises:
            InsufficientPermissionsError: If user lacks member permissions
        """
        if not entry_ids:
            return True

        # Get first entry to check permissions
        first_entry = await self.entry_repository.get_by_id(entry_ids[0])
        if not first_entry:
            raise DatabaseEntryNotFoundError(f"Entry {entry_ids[0]} not found")

        database = await self.database_repository.get_by_id(first_entry.database_id)
        if not database:
            raise DatabaseNotFoundError(f"Database {first_entry.database_id} not found")

        # Check user has member+ permission
        if not await self.project_service.check_permission(database.project_id, user_id, "member"):
            logger.warning(f"User {user_id} lacks permission to reorder entries")
            raise InsufficientPermissionsError("Only project members can reorder entries")

        logger.info(f"Reordering {len(entry_ids)} entries")
        success = await self.entry_repository.reorder_entries(entry_ids)
        await self.db.flush()

        logger.info("Reordered entries")
        return success

    async def search_entries(
        self,
        database_id: UUID,
        query: str,
        user_id: UUID,
    ) -> List[DatabaseEntry]:
        """
        Search entries by text content.

        Args:
            database_id: UUID of the database
            query: Search query string
            user_id: UUID of requesting user

        Returns:
            List of matching DatabaseEntry objects

        Raises:
            DatabaseNotFoundError: If database not found
            InsufficientPermissionsError: If user lacks view permissions
        """
        # Get database
        database = await self.database_repository.get_by_id(database_id)
        if not database:
            raise DatabaseNotFoundError(f"Database {database_id} not found")

        # Check user has view+ permission
        if not await self.project_service.check_permission(database.project_id, user_id, "viewer"):
            logger.warning(
                f"User {user_id} lacks permission to search entries in database {database_id}"
            )
            raise InsufficientPermissionsError("You do not have permission to search entries")

        entries = await self.entry_repository.search_entries(database_id, query)
        logger.info(f"Found {len(entries)} entries matching '{query}'")
        return entries

    async def get_entries_by_creator(
        self,
        database_id: UUID,
        creator_user_id: UUID,
        requesting_user_id: UUID,
    ) -> List[DatabaseEntry]:
        """
        Get entries created by a specific user.

        Args:
            database_id: UUID of the database
            creator_user_id: UUID of user who created entries
            requesting_user_id: UUID of user making request

        Returns:
            List of DatabaseEntry objects created by user

        Raises:
            DatabaseNotFoundError: If database not found
            InsufficientPermissionsError: If requesting user lacks view permissions
        """
        # Get database
        database = await self.database_repository.get_by_id(database_id)
        if not database:
            raise DatabaseNotFoundError(f"Database {database_id} not found")

        # Check requesting user has view+ permission
        if not await self.project_service.check_permission(
            database.project_id, requesting_user_id, "viewer"
        ):
            logger.warning(
                f"User {requesting_user_id} lacks permission to view entries "
                f"in database {database_id}"
            )
            raise InsufficientPermissionsError("You do not have permission to view entries")

        entries = await self.entry_repository.get_created_by_user(database_id, creator_user_id)
        logger.info(f"Found {len(entries)} entries created by user {creator_user_id}")
        return entries

    async def validate_entry_values(
        self,
        database_id: UUID,
        values: Dict[str, Any],
        check_required: bool = True,
    ) -> Tuple[bool, Optional[str]]:
        """
        Validate all values against property types.

        Args:
            database_id: UUID of the database
            values: Dictionary mapping property_id (str) to value
            check_required: Whether to check for required fields (False for updates)

        Returns:
            Tuple of (is_valid, error_message)
                - (True, None) if valid
                - (False, error_message) if invalid
        """
        try:
            # Get all properties for database
            properties = await self.property_repository.get_by_database(database_id)
            property_map = {str(p.id): p for p in properties}

            # Check required properties only if check_required=True (for creates)
            if check_required:
                required_props = await self.property_repository.get_required_properties(database_id)
                required_ids = {str(p.id) for p in required_props}

                for req_id in required_ids:
                    if req_id not in values or values[req_id] is None:
                        prop = property_map[req_id]
                        return (False, f"Required property '{prop.name}' must be provided")

            # Validate each provided value
            for property_id_str, value in values.items():
                if property_id_str not in property_map:
                    return (False, f"Property {property_id_str} not found in database")

                prop = property_map[property_id_str]

                # Skip validation for computed properties (formula, rollup)
                if prop.property_type in ["formula", "rollup"]:
                    continue

                # Validate value type
                is_valid, error_msg = self._validate_value_for_type(
                    prop.property_type, value, prop.config, prop.name
                )
                if not is_valid:
                    return (
                        False,
                        error_msg
                        or f"Invalid value for property '{prop.name}' of type {prop.property_type}",
                    )

            return (True, None)

        except Exception as e:
            logger.error(f"Error validating entry values: {e}", exc_info=True)
            return (False, f"Validation error: {str(e)}")

    def _validate_value_for_type(
        self,
        property_type: str,
        value: Any,
        config: Optional[Dict] = None,
        property_name: Optional[str] = None,
    ) -> Tuple[bool, Optional[str]]:
        """
        Validate value against property type with detailed error messages.

        Args:
            property_type: Type of property
            value: Value to validate
            config: Optional property configuration
            property_name: Optional property name for error messages

        Returns:
            Tuple of (is_valid, error_message)
        """
        if value is None:
            return True, None

        # Handle both dict format and plain values
        if not isinstance(value, dict):
            # Try to convert plain value to dict format
            return self._convert_and_validate(property_type, value, config, property_name)

        # Validate based on property type
        if property_type == "text":
            return self._validate_text_value(value, config, property_name)

        elif property_type == "number":
            return self._validate_number_value(value, config, property_name)

        elif property_type == "select":
            return self._validate_select_value(value, config, property_name)

        elif property_type == "multiselect":
            return self._validate_multiselect_value(value, config, property_name)

        elif property_type == "date":
            return self._validate_date_value(value, config, property_name)

        elif property_type == "checkbox":
            return self._validate_checkbox_value(value, config, property_name)

        elif property_type == "url":
            return self._validate_url_value(value, config, property_name)

        elif property_type == "email":
            return self._validate_email_value(value, config, property_name)

        elif property_type == "phone":
            return self._validate_phone_value(value, config, property_name)

        elif property_type == "relation":
            return self._validate_relation_value(value, config, property_name)

        # Auto-populated fields are always valid
        elif property_type in [
            "created_time",
            "created_by",
            "last_edited_time",
            "last_edited_by",
        ]:
            return True, None

        # Unknown type
        return False, f"Unknown property type: {property_type}"

    def _convert_and_validate(
        self,
        property_type: str,
        value: Any,
        config: Optional[Dict] = None,
        property_name: Optional[str] = None,
    ) -> Tuple[bool, Optional[str]]:
        """
        Convert plain value to dict format and validate.

        Args:
            property_type: Type of property
            value: Plain value to convert and validate
            config: Optional property configuration
            property_name: Optional property name for error messages

        Returns:
            Tuple of (is_valid, error_message)
        """
        try:
            if property_type == "text":
                # Accept anything convertible to string
                try:
                    text_str = str(value).strip() if value is not None else ""
                    converted = {"text": text_str}
                    return self._validate_text_value(converted, config, property_name)
                except Exception:
                    prop_display = f"'{property_name}'" if property_name else "Text"
                    return False, f"{prop_display} value must be convertible to string"

            elif property_type == "number":
                # Try to convert to number
                if isinstance(value, (int, float)) and not isinstance(value, bool):
                    converted = {"number": value}
                    return self._validate_number_value(converted, config, property_name)
                # Try to convert string to number
                if isinstance(value, str):
                    value_stripped = value.strip()
                    if not value_stripped:
                        return True, None  # Empty is ok for optional
                    try:
                        # Try int first, then float
                        try:
                            num = int(value_stripped)
                        except ValueError:
                            num = float(value_stripped)
                        converted = {"number": num}
                        return self._validate_number_value(converted, config, property_name)
                    except ValueError:
                        prop_display = f"'{property_name}'" if property_name else "Number"
                        return (
                            False,
                            f"{prop_display}: Cannot convert '{value}' to number",
                        )
                prop_display = f"'{property_name}'" if property_name else "Number"
                return False, f"{prop_display} expects a numeric value"

            elif property_type == "checkbox":
                # Convert to bool
                if isinstance(value, bool):
                    converted = {"checkbox": value}
                    return self._validate_checkbox_value(converted, config, property_name)
                # Try to convert string or int to bool
                if isinstance(value, (str, int)):
                    if isinstance(value, str):
                        lowered = value.lower().strip()
                        if lowered in ["true", "1", "yes", "on"]:
                            converted = {"checkbox": True}
                            return self._validate_checkbox_value(converted, config, property_name)
                        elif lowered in ["false", "0", "no", "off", ""]:
                            converted = {"checkbox": False}
                            return self._validate_checkbox_value(converted, config, property_name)
                    elif value == 1:
                        converted = {"checkbox": True}
                        return self._validate_checkbox_value(converted, config, property_name)
                    elif value == 0:
                        converted = {"checkbox": False}
                        return self._validate_checkbox_value(converted, config, property_name)
                prop_display = f"'{property_name}'" if property_name else "Checkbox"
                return False, f"{prop_display} expects a boolean value"

            elif property_type in ["url", "email", "phone"]:
                # Convert to string
                try:
                    str_val = str(value).strip() if value is not None else ""
                    converted = {property_type: str_val}
                    return self._validate_value_for_type(
                        property_type, converted, config, property_name
                    )
                except Exception:
                    prop_display = f"'{property_name}'" if property_name else property_type.title()
                    return False, f"{prop_display} value must be a string"

            prop_display = f"'{property_name}'" if property_name else property_type.title()
            return False, f"Invalid value format for {prop_display}"

        except Exception as e:
            logger.error(f"Error converting value for {property_type}: {e}")
            prop_display = f"'{property_name}'" if property_name else property_type.title()
            return False, f"Failed to process {prop_display} value"

    def _validate_text_value(
        self,
        value: Dict[str, Any],
        config: Optional[Dict] = None,
        property_name: Optional[str] = None,
    ) -> Tuple[bool, Optional[str]]:
        """Validate text property value."""
        if "text" not in value:
            prop_display = f"'{property_name}'" if property_name else "Text"
            return False, f"{prop_display} must have 'text' field"

        text = value["text"]

        # Accept None for optional fields
        if text is None:
            return True, None

        # Try to convert to string
        try:
            text_str = str(text).strip()
        except Exception:
            prop_display = f"'{property_name}'" if property_name else "Text"
            return False, f"{prop_display} value must be convertible to string"

        # Max length 5000
        if len(text_str) > 5000:
            prop_display = f"'{property_name}'" if property_name else "Text"
            return (
                False,
                f"{prop_display} exceeds maximum length of 5000 characters",
            )

        return True, None

    def _validate_number_value(
        self,
        value: Dict[str, Any],
        config: Optional[Dict] = None,
        property_name: Optional[str] = None,
    ) -> Tuple[bool, Optional[str]]:
        """Validate number property value."""
        if "number" not in value:
            prop_display = f"'{property_name}'" if property_name else "Number"
            return False, f"{prop_display} must have 'number' field"

        num = value["number"]

        # Accept None for optional fields
        if num is None:
            return True, None

        # Try to convert to number if needed
        if isinstance(num, (int, float)):
            return True, None

        # Try to parse string as number
        if isinstance(num, str):
            try:
                # Try int first
                int(num)
                return True, None
            except ValueError:
                try:
                    # Try float
                    float(num)
                    return True, None
                except ValueError:
                    prop_display = f"'{property_name}'" if property_name else "Number"
                    return (
                        False,
                        f"{prop_display} value '{num}' cannot be converted to number",
                    )

        prop_display = f"'{property_name}'" if property_name else "Number"
        return False, f"{prop_display} value must be numeric"

    def _validate_select_value(
        self,
        value: Dict[str, Any],
        config: Optional[Dict] = None,
        property_name: Optional[str] = None,
    ) -> Tuple[bool, Optional[str]]:
        """Validate select property value."""
        if "select" not in value:
            prop_display = f"'{property_name}'" if property_name else "Select"
            return False, f"{prop_display} must have 'select' field"

        select_val = value["select"]
        if select_val is None:
            return True, None  # Empty select is valid

        if not isinstance(select_val, dict):
            prop_display = f"'{property_name}'" if property_name else "Select"
            return False, f"{prop_display} value must be an object"

        if "name" not in select_val:
            prop_display = f"'{property_name}'" if property_name else "Select"
            return False, f"{prop_display} option must have 'name' field"

        # Check if value is in options (case-insensitive if config provided)
        if config and "options" in config:
            option_names = [opt["name"].lower() for opt in config["options"]]
            select_name = str(select_val.get("name", "")).lower().strip()

            if select_name and select_name not in option_names:
                # Be lenient - only fail if the option list is not empty
                if option_names:
                    available = ", ".join([opt["name"] for opt in config["options"]])
                    prop_display = f"'{property_name}'" if property_name else "Select"
                    return (
                        False,
                        f"{prop_display}: '{select_val.get('name')}' is not valid. "
                        f"Available: {available}",
                    )

        return True, None

    def _validate_multiselect_value(
        self,
        value: Dict[str, Any],
        config: Optional[Dict] = None,
        property_name: Optional[str] = None,
    ) -> Tuple[bool, Optional[str]]:
        """Validate multiselect property value."""
        if "multiselect" not in value:
            return False, "Multiselect property must have 'multiselect' field"

        multiselect_val = value["multiselect"]
        if not isinstance(multiselect_val, list):
            return False, "Multiselect value must be an array"

        # Check all values are in options (if config provided)
        if config and "options" in config:
            option_names = [opt["name"].lower() for opt in config["options"]]
            for item in multiselect_val:
                if not isinstance(item, dict) or "name" not in item:
                    return False, "Each multiselect option must be an object with 'name' field"
                item_name = item.get("name", "").lower()
                if item_name not in option_names:
                    available = ", ".join([opt["name"] for opt in config["options"]])
                    return (
                        False,
                        f"'{item.get('name')}' is not a valid option. "
                        f"Available options: {available}",
                    )

        return True, None

    def _validate_date_value(
        self,
        value: Dict[str, Any],
        config: Optional[Dict] = None,
        property_name: Optional[str] = None,
    ) -> Tuple[bool, Optional[str]]:
        """Validate date property value."""
        if "date" not in value:
            return False, "Date property must have 'date' field"

        date_val = value["date"]
        if not isinstance(date_val, dict):
            return False, "Date value must be an object"

        # Should have "start" and optionally "end" for date range
        if "start" not in date_val:
            return False, "Date must have 'start' field"

        # Validate ISO date format (support multiple formats)
        start_date = date_val["start"]
        if not isinstance(start_date, str):
            return False, "Date start must be a string"

        if not self._is_valid_date_string(start_date):
            return (
                False,
                f"Invalid date format: '{start_date}'. "
                f"Expected ISO format (YYYY-MM-DD or YYYY-MM-DDTHH:MM:SS)",
            )

        if "end" in date_val:
            end_date = date_val["end"]
            if not isinstance(end_date, str):
                return False, "Date end must be a string"
            if not self._is_valid_date_string(end_date):
                return (
                    False,
                    f"Invalid date format: '{end_date}'. "
                    f"Expected ISO format (YYYY-MM-DD or YYYY-MM-DDTHH:MM:SS)",
                )

        return True, None

    def _is_valid_date_string(self, date_str: str) -> bool:
        """Check if string is a valid date in multiple ISO formats."""
        try:
            from datetime import datetime

            # Try different ISO formats
            formats = [
                "%Y-%m-%dT%H:%M:%S",
                "%Y-%m-%dT%H:%M:%S.%f",
                "%Y-%m-%d",
                "%Y-%m-%dT%H:%M:%SZ",
                "%Y-%m-%dT%H:%M:%S.%fZ",
            ]

            # Handle Z timezone indicator
            cleaned = date_str.replace("Z", "+00:00")

            # Try direct ISO parsing first
            try:
                datetime.fromisoformat(cleaned)
                return True
            except ValueError:
                pass

            # Try specific formats
            for fmt in formats:
                try:
                    datetime.strptime(date_str, fmt)
                    return True
                except ValueError:
                    continue

            return False
        except Exception:
            return False

    def _validate_checkbox_value(
        self,
        value: Dict[str, Any],
        config: Optional[Dict] = None,
        property_name: Optional[str] = None,
    ) -> Tuple[bool, Optional[str]]:
        """Validate checkbox property value."""
        if "checkbox" not in value:
            return False, "Checkbox property must have 'checkbox' field"

        checkbox_val = value["checkbox"]
        if not isinstance(checkbox_val, bool):
            return False, "Checkbox value must be true or false"

        return True, None

    def _validate_url_value(
        self,
        value: Dict[str, Any],
        config: Optional[Dict] = None,
        property_name: Optional[str] = None,
    ) -> Tuple[bool, Optional[str]]:
        """Validate URL property value."""
        if "url" not in value:
            prop_display = f"'{property_name}'" if property_name else "URL"
            return False, f"{prop_display} must have 'url' field"

        url = value["url"]

        # Allow None
        if url is None:
            return True, None

        # Try to convert to string
        try:
            url_str = str(url).strip()
        except Exception:
            prop_display = f"'{property_name}'" if property_name else "URL"
            return False, f"{prop_display} value must be a string"

        # Allow empty URLs
        if not url_str:
            return True, None

        # Basic URL validation (permissive - just check for protocol)
        valid_protocols = ["http://", "https://", "ftp://"]
        if not any(url_str.lower().startswith(p) for p in valid_protocols):
            prop_display = f"'{property_name}'" if property_name else "URL"
            return (
                False,
                f"{prop_display} must start with http://, https://, or ftp://",
            )

        return True, None

    def _validate_email_value(
        self,
        value: Dict[str, Any],
        config: Optional[Dict] = None,
        property_name: Optional[str] = None,
    ) -> Tuple[bool, Optional[str]]:
        """Validate email property value."""
        if "email" not in value:
            prop_display = f"'{property_name}'" if property_name else "Email"
            return False, f"{prop_display} must have 'email' field"

        email = value["email"]

        # Allow None
        if email is None:
            return True, None

        # Try to convert to string
        try:
            email_str = str(email).strip()
        except Exception:
            prop_display = f"'{property_name}'" if property_name else "Email"
            return False, f"{prop_display} value must be a string"

        # Allow empty emails
        if not email_str:
            return True, None

        # Basic email validation - just check for @ and domain
        if "@" not in email_str:
            prop_display = f"'{property_name}'" if property_name else "Email"
            return False, f"{prop_display} must contain '@' symbol"

        # Very basic validation - has @ and something after it
        parts = email_str.split("@")
        if len(parts) != 2 or not parts[0] or not parts[1]:
            prop_display = f"'{property_name}'" if property_name else "Email"
            return False, f"{prop_display} format invalid: '{email_str}'"

        return True, None

    def _validate_phone_value(
        self,
        value: Dict[str, Any],
        config: Optional[Dict] = None,
        property_name: Optional[str] = None,
    ) -> Tuple[bool, Optional[str]]:
        """Validate phone property value."""
        if "phone" not in value:
            prop_display = f"'{property_name}'" if property_name else "Phone"
            return False, f"{prop_display} must have 'phone' field"

        phone = value["phone"]

        # Allow None
        if phone is None:
            return True, None

        # Try to convert to string
        try:
            phone_str = str(phone).strip()
        except Exception:
            prop_display = f"'{property_name}'" if property_name else "Phone"
            return False, f"{prop_display} value must be a string"

        # Allow empty phones
        if not phone_str:
            return True, None

        # Very permissive - just accept any string
        # International formats vary too much to validate strictly
        # Just check it's not too long
        if len(phone_str) > 50:
            prop_display = f"'{property_name}'" if property_name else "Phone"
            return False, f"{prop_display} exceeds maximum length of 50 characters"

        return True, None

    def _validate_relation_value(
        self,
        value: Dict[str, Any],
        config: Optional[Dict] = None,
        property_name: Optional[str] = None,
    ) -> Tuple[bool, Optional[str]]:
        """Validate relation property value."""
        if "relations" not in value:
            return False, "Relation property must have 'relations' field"

        relations = value["relations"]
        if not isinstance(relations, list):
            return False, "Relations value must be an array"

        # Each relation should be a UUID string
        for rel in relations:
            try:
                UUID(str(rel))
            except (ValueError, TypeError):
                return False, f"Invalid relation ID: '{rel}'. Must be a valid UUID."

        return True, None
