"""
Database entry service for business logic.

This module provides business logic for database entry management, including CRUD operations,
value validation, formula/rollup recalculation, bulk operations, and permission checks.
"""

import logging
import re
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
                raise DatabasePropertyNotFoundError(
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

        # Validate updated values
        if "values" in updates:
            is_valid, error = await self.validate_entry_values(entry.database_id, updates["values"])
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
    ) -> Tuple[bool, Optional[str]]:
        """
        Validate all values against property types.

        Args:
            database_id: UUID of the database
            values: Dictionary mapping property_id (str) to value

        Returns:
            Tuple of (is_valid, error_message)
                - (True, None) if valid
                - (False, error_message) if invalid
        """
        try:
            # Get all properties for database
            properties = await self.property_repository.get_by_database(database_id)
            property_map = {str(p.id): p for p in properties}

            # Get required properties
            required_props = await self.property_repository.get_required_properties(database_id)
            required_ids = {str(p.id) for p in required_props}

            # Check required properties are present
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
                if not self._validate_value_for_type(prop.property_type, value, prop.config):
                    return (
                        False,
                        f"Invalid value for property '{prop.name}' of type {prop.property_type}",
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
    ) -> bool:
        """
        Validate value against property type.

        Args:
            property_type: Type of property
            value: Value to validate
            config: Optional property configuration

        Returns:
            True if valid, False otherwise
        """
        if value is None:
            return True

        if not isinstance(value, dict):
            return False

        # Validate based on property type
        if property_type == "text":
            if "text" not in value:
                return False
            text = value["text"]
            if not isinstance(text, str):
                return False
            # Max length 5000
            if len(text) > 5000:
                return False
            return True

        elif property_type == "number":
            if "number" not in value:
                return False
            return isinstance(value["number"], (int, float))

        elif property_type == "select":
            if "select" not in value:
                return False
            if value["select"] is None:
                return True
            if not isinstance(value["select"], dict):
                return False
            # Check if value is in options (if config provided)
            if config and "options" in config:
                option_names = [opt["name"] for opt in config["options"]]
                return value["select"].get("name") in option_names
            return True

        elif property_type == "multiselect":
            if "multiselect" not in value:
                return False
            if not isinstance(value["multiselect"], list):
                return False
            # Check all values are in options (if config provided)
            if config and "options" in config:
                option_names = [opt["name"] for opt in config["options"]]
                for item in value["multiselect"]:
                    if not isinstance(item, dict) or item.get("name") not in option_names:
                        return False
            return True

        elif property_type == "date":
            if "date" not in value:
                return False
            date_val = value["date"]
            if not isinstance(date_val, dict):
                return False
            # Should have "start" and optionally "end" for date range
            if "start" not in date_val:
                return False
            # Validate ISO date format
            try:
                from datetime import datetime

                datetime.fromisoformat(date_val["start"].replace("Z", "+00:00"))
                if "end" in date_val:
                    datetime.fromisoformat(date_val["end"].replace("Z", "+00:00"))
            except (ValueError, AttributeError):
                return False
            return True

        elif property_type == "checkbox":
            if "checkbox" not in value:
                return False
            return isinstance(value["checkbox"], bool)

        elif property_type == "url":
            if "url" not in value:
                return False
            url = value["url"]
            if not isinstance(url, str):
                return False
            # Basic URL validation
            url_pattern = re.compile(
                r"^https?://"  # http:// or https://
                r"(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|"  # domain...
                r"localhost|"  # localhost...
                r"\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})"  # ...or ip
                r"(?::\d+)?"  # optional port
                r"(?:/?|[/?]\S+)$",
                re.IGNORECASE,
            )
            return bool(url_pattern.match(url))

        elif property_type == "email":
            if "email" not in value:
                return False
            email = value["email"]
            if not isinstance(email, str):
                return False
            # Basic email validation
            email_pattern = re.compile(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$")
            return bool(email_pattern.match(email))

        elif property_type == "phone":
            if "phone" not in value:
                return False
            phone = value["phone"]
            if not isinstance(phone, str):
                return False
            # Basic phone validation (flexible format)
            # Allows: +1234567890, (123) 456-7890, 123-456-7890, etc.
            phone_clean = re.sub(r"[^\d]", "", phone)
            return len(phone_clean) >= 10 and len(phone_clean) <= 15

        elif property_type == "relation":
            if "relations" not in value:
                return False
            relations = value["relations"]
            if not isinstance(relations, list):
                return False
            # Each relation should be a UUID string
            for rel in relations:
                try:
                    UUID(rel)
                except (ValueError, TypeError):
                    return False
            return True

        # Auto-populated fields are always valid
        elif property_type in ["created_time", "created_by", "last_edited_time", "last_edited_by"]:
            return True

        # Unknown type
        return False
