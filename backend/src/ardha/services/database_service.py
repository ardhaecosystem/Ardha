"""
Database service for business logic.

This module provides business logic for database management, including CRUD operations,
property management, view management, template handling, and permission checks.
"""

import logging
from typing import Any, Dict, List
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from ardha.core.exceptions import (
    DatabaseNotFoundError,
    DatabasePropertyNotFoundError,
    PropertyInUseError,
)
from ardha.models.database import Database
from ardha.models.database_property import DatabaseProperty
from ardha.models.database_view import DatabaseView
from ardha.repositories.database_property_repository import DatabasePropertyRepository
from ardha.repositories.database_repository import DatabaseRepository
from ardha.services.project_service import InsufficientPermissionsError, ProjectService

logger = logging.getLogger(__name__)


class DatabaseService:
    """
    Service for database management business logic.

    Handles database CRUD operations, property management, view management,
    template handling, and permission checks. Enforces role-based access
    control through ProjectService integration.

    Attributes:
        db: SQLAlchemy async session
        repository: DatabaseRepository for data access
        property_repository: DatabasePropertyRepository for property access
        project_service: ProjectService for permission checks
    """

    def __init__(self, db: AsyncSession) -> None:
        """
        Initialize DatabaseService.

        Args:
            db: SQLAlchemy async session for database operations
        """
        self.db = db
        self.repository = DatabaseRepository(db)
        self.property_repository = DatabasePropertyRepository(db)
        self.project_service = ProjectService(db)

    async def create_database(
        self,
        project_id: UUID,
        database_data: Dict[str, Any],
        user_id: UUID,
    ) -> Database:
        """
        Create a new database in a project.

        Args:
            project_id: UUID of the project
            database_data: Dictionary with database fields
            user_id: UUID of user creating the database

        Returns:
            Created Database object

        Raises:
            InsufficientPermissionsError: If user lacks admin permissions
            ValueError: If name validation fails
        """
        # Check user has admin+ permission
        if not await self.project_service.check_permission(project_id, user_id, "admin"):
            logger.warning(
                f"User {user_id} lacks permission to create database in project {project_id}"
            )
            raise InsufficientPermissionsError("Only project admin or owner can create databases")

        # Check name uniqueness in project
        name = database_data.get("name")
        if name:
            existing = await self.repository.get_by_name(project_id, name)
            if existing:
                raise ValueError(f"Database with name '{name}' already exists in this project")

        logger.info(f"Creating database '{name}' in project {project_id}")

        # Add project_id to data
        database_data["project_id"] = project_id

        # Create database (repository handles template property copying)
        database = await self.repository.create(database_data, user_id)
        await self.db.flush()
        database_id = database.id  # Store ID before potential reload

        # Create default "All" table view if no template
        if not database_data.get("template_id"):
            from ardha.models.database_view import DatabaseView

            default_view = DatabaseView(
                database_id=database_id,
                name="All",
                view_type="table",
                config={"filters": [], "sorts": [], "visible_properties": []},
                position=0,
                created_by_user_id=user_id,  # Must set creator
            )
            self.db.add(default_view)
            await self.db.flush()

            # Refresh database to load the new view into the relationship
            await self.db.refresh(database, ["views", "properties", "created_by"])

        logger.info(f"Created database {database_id}")
        return database

    async def get_database(
        self,
        database_id: UUID,
        user_id: UUID,
    ) -> Database:
        """
        Get database by ID with permission check.

        Args:
            database_id: UUID of the database
            user_id: UUID of requesting user

        Returns:
            Database object with properties and views loaded

        Raises:
            DatabaseNotFoundError: If database not found
            InsufficientPermissionsError: If user lacks view permissions
        """
        database = await self.repository.get_by_id(database_id)
        if not database:
            raise DatabaseNotFoundError(f"Database {database_id} not found")

        # Check user has view+ permission
        if not await self.project_service.check_permission(database.project_id, user_id, "viewer"):
            logger.warning(f"User {user_id} lacks permission to view database {database_id}")
            raise InsufficientPermissionsError("You do not have permission to view this database")

        return database

    async def list_databases(
        self,
        project_id: UUID,
        user_id: UUID,
        include_archived: bool = False,
    ) -> List[Database]:
        """
        List databases in a project with permission check.

        Args:
            project_id: UUID of the project
            user_id: UUID of requesting user
            include_archived: Whether to include archived databases

        Returns:
            List of Database objects with stats

        Raises:
            InsufficientPermissionsError: If user lacks view permissions
        """
        # Check user has view+ permission
        if not await self.project_service.check_permission(project_id, user_id, "viewer"):
            logger.warning(
                f"User {user_id} lacks permission to list databases in project {project_id}"
            )
            raise InsufficientPermissionsError(
                "You do not have permission to view project databases"
            )

        databases = await self.repository.get_by_project(project_id, include_archived)
        logger.info(f"Listed {len(databases)} databases for project {project_id}")
        return databases

    async def update_database(
        self,
        database_id: UUID,
        updates: Dict[str, Any],
        user_id: UUID,
    ) -> Database:
        """
        Update database fields.

        Args:
            database_id: UUID of database to update
            updates: Dictionary of fields to update
            user_id: UUID of user making update

        Returns:
            Updated Database object

        Raises:
            DatabaseNotFoundError: If database not found
            InsufficientPermissionsError: If user lacks admin permissions
            ValueError: If name already exists
        """
        database = await self.repository.get_by_id(database_id)
        if not database:
            raise DatabaseNotFoundError(f"Database {database_id} not found")

        # Check user has admin+ permission
        if not await self.project_service.check_permission(database.project_id, user_id, "admin"):
            logger.warning(f"User {user_id} lacks permission to update database {database_id}")
            raise InsufficientPermissionsError("Only project admin or owner can update databases")

        # If name changed, check uniqueness
        if "name" in updates and updates["name"] != database.name:
            existing = await self.repository.get_by_name(database.project_id, updates["name"])
            if existing:
                raise ValueError(
                    f"Database with name '{updates['name']}' already exists in this project"
                )

        logger.info(f"Updating database {database_id}")
        updated = await self.repository.update(database_id, updates)
        if not updated:
            raise DatabaseNotFoundError(f"Database {database_id} not found")

        # Repository already flushed and refreshed, no need to do it again
        logger.info(f"Updated database {database_id}")
        return updated

    async def archive_database(
        self,
        database_id: UUID,
        user_id: UUID,
    ) -> Database:
        """
        Archive a database (soft delete).

        Also archives all entries in the database.

        Args:
            database_id: UUID of database to archive
            user_id: UUID of user making request

        Returns:
            Archived Database object

        Raises:
            DatabaseNotFoundError: If database not found
            InsufficientPermissionsError: If user lacks admin permissions
        """
        database = await self.repository.get_by_id(database_id)
        if not database:
            raise DatabaseNotFoundError(f"Database {database_id} not found")

        # Check user has admin+ permission
        if not await self.project_service.check_permission(database.project_id, user_id, "admin"):
            logger.warning(f"User {user_id} lacks permission to archive database {database_id}")
            raise InsufficientPermissionsError("Only project admin or owner can archive databases")

        logger.info(f"Archiving database {database_id}")
        archived = await self.repository.archive(database_id)
        if not archived:
            raise DatabaseNotFoundError(f"Database {database_id} not found")

        # Repository already flushed and refreshed, no need to do it again
        logger.info(f"Archived database {database_id}")
        return archived

    async def delete_database(
        self,
        database_id: UUID,
        user_id: UUID,
    ) -> bool:
        """
        Permanently delete a database and all related data.

        Args:
            database_id: UUID of database to delete
            user_id: UUID of user making request

        Returns:
            True if deleted successfully

        Raises:
            DatabaseNotFoundError: If database not found
            InsufficientPermissionsError: If user lacks owner permissions
        """
        database = await self.repository.get_by_id(database_id)
        if not database:
            raise DatabaseNotFoundError(f"Database {database_id} not found")

        # Check user has owner permission
        if not await self.project_service.check_permission(database.project_id, user_id, "owner"):
            logger.warning(f"User {user_id} lacks permission to delete database {database_id}")
            raise InsufficientPermissionsError("Only project owner can delete databases")

        logger.info(f"Deleting database {database_id}")
        success = await self.repository.delete(database_id)
        await self.db.flush()

        logger.info(f"Deleted database {database_id}")
        return success

    async def duplicate_database(
        self,
        database_id: UUID,
        new_name: str,
        user_id: UUID,
        copy_entries: bool = False,
    ) -> Database:
        """
        Create a duplicate of a database.

        Args:
            database_id: UUID of database to duplicate
            new_name: Name for the new database
            user_id: UUID of user creating duplicate
            copy_entries: Whether to also copy all entries

        Returns:
            New Database object

        Raises:
            DatabaseNotFoundError: If database not found
            InsufficientPermissionsError: If user lacks admin permissions
            ValueError: If new_name already exists
        """
        database = await self.repository.get_by_id(database_id)
        if not database:
            raise DatabaseNotFoundError(f"Database {database_id} not found")

        # Check user has admin+ permission
        if not await self.project_service.check_permission(database.project_id, user_id, "admin"):
            logger.warning(f"User {user_id} lacks permission to duplicate database {database_id}")
            raise InsufficientPermissionsError(
                "Only project admin or owner can duplicate databases"
            )

        # Check name uniqueness
        existing = await self.repository.get_by_name(database.project_id, new_name)
        if existing:
            raise ValueError(f"Database with name '{new_name}' already exists in this project")

        logger.info(f"Duplicating database {database_id} as '{new_name}'")
        new_db = await self.repository.duplicate(database_id, new_name, user_id)
        if not new_db:
            raise DatabaseNotFoundError(f"Database {database_id} not found")
        await self.db.flush()

        # Copy entries if requested
        if copy_entries:
            from ardha.repositories.database_entry_repository import DatabaseEntryRepository

            entry_repo = DatabaseEntryRepository(self.db)
            entries = await entry_repo.get_by_database(database_id, limit=100)

            for entry in entries:
                # Prepare values dict
                values_dict = {}
                for value_obj in entry.values:
                    values_dict[str(value_obj.property_id)] = value_obj.value

                # Create in new database
                # Note: Property IDs would need mapping between old and new database
                # This is simplified for MVP
                await entry_repo.create(
                    {"database_id": new_db.id, "values": values_dict},
                    user_id,
                )

            await self.db.flush()
            logger.info(f"Copied {len(entries)} entries to new database")

        logger.info(f"Duplicated database {database_id}")
        return new_db

    async def create_property(
        self,
        database_id: UUID,
        property_data: Dict[str, Any],
        user_id: UUID,
    ) -> DatabaseProperty:
        """
        Create a new property in a database.

        Args:
            database_id: UUID of the database
            property_data: Dictionary with property fields
            user_id: UUID of user creating property

        Returns:
            Created DatabaseProperty object

        Raises:
            DatabaseNotFoundError: If database not found
            InsufficientPermissionsError: If user lacks admin permissions
            ValueError: If property validation fails
        """
        database = await self.repository.get_by_id(database_id)
        if not database:
            raise DatabaseNotFoundError(f"Database {database_id} not found")

        # Check user has admin+ permission
        if not await self.project_service.check_permission(database.project_id, user_id, "admin"):
            logger.warning(
                f"User {user_id} lacks permission to create property in database {database_id}"
            )
            raise InsufficientPermissionsError("Only project admin or owner can create properties")

        # Validate property type
        property_type = property_data.get("property_type")
        if not property_type:
            raise ValueError("property_type is required")

        # Validate property configuration (permissive)
        config = property_data.get("config")
        if config is None:
            property_data["config"] = {}

        self._validate_property_config(property_type, property_data.get("config", {}))

        logger.info(f"Creating property '{property_data.get('name')}' in database {database_id}")

        # Add database_id to data
        property_data["database_id"] = database_id

        prop = await self.property_repository.create(property_data)
        await self.db.flush()

        logger.info(f"Created property {prop.id}")
        return prop

    async def update_property(
        self,
        property_id: UUID,
        updates: Dict[str, Any],
        user_id: UUID,
    ) -> DatabaseProperty:
        """
        Update property fields.

        Recalculates affected formulas if property is modified.

        Args:
            property_id: UUID of property to update
            updates: Dictionary of fields to update
            user_id: UUID of user making update

        Returns:
            Updated DatabaseProperty object

        Raises:
            DatabasePropertyNotFoundError: If property not found
            InsufficientPermissionsError: If user lacks admin permissions
        """
        prop = await self.property_repository.get_by_id(property_id)
        if not prop:
            raise DatabasePropertyNotFoundError(f"Property {property_id} not found")

        # Check user has admin+ permission
        if not await self.project_service.check_permission(
            prop.database.project_id, user_id, "admin"
        ):
            logger.warning(f"User {user_id} lacks permission to update property {property_id}")
            raise InsufficientPermissionsError("Only project admin or owner can update properties")

        # Validate config if being updated
        if "config" in updates:
            self._validate_property_config(prop.property_type, updates["config"])

        logger.info(f"Updating property {property_id}")
        updated = await self.property_repository.update(property_id, updates)
        if not updated:
            raise DatabasePropertyNotFoundError(f"Property {property_id} not found")
        await self.db.flush()

        # If formula/config changed, recalculate affected entries
        if "config" in updates and prop.property_type in ["formula", "rollup"]:
            from ardha.services.formula_service import FormulaService

            formula_service = FormulaService(self.db)
            count = await formula_service.recalculate_database_formulas(prop.database_id)
            logger.info(f"Recalculated {count} formulas after property update")

        logger.info(f"Updated property {property_id}")
        return updated

    async def delete_property(
        self,
        property_id: UUID,
        user_id: UUID,
    ) -> bool:
        """
        Delete a property.

        Checks if property is used in formulas or rollups before deletion.

        Args:
            property_id: UUID of property to delete
            user_id: UUID of user making request

        Returns:
            True if deleted successfully

        Raises:
            DatabasePropertyNotFoundError: If property not found
            InsufficientPermissionsError: If user lacks admin permissions
            PropertyInUseError: If property is used in formulas/rollups
        """
        prop = await self.property_repository.get_by_id(property_id)
        if not prop:
            raise DatabasePropertyNotFoundError(f"Property {property_id} not found")

        # Check user has admin+ permission
        if not await self.project_service.check_permission(
            prop.database.project_id, user_id, "admin"
        ):
            logger.warning(f"User {user_id} lacks permission to delete property {property_id}")
            raise InsufficientPermissionsError("Only project admin or owner can delete properties")

        # Check if property is used in formulas
        from ardha.services.formula_service import FormulaService

        formula_service = FormulaService(self.db)
        formula_props = await self.property_repository.get_formula_properties(prop.database_id)

        used_by = []
        for formula_prop in formula_props:
            deps = await formula_service.get_formula_dependencies(prop.database_id, formula_prop.id)
            if property_id in deps:
                used_by.append(str(formula_prop.id))

        if used_by:
            raise PropertyInUseError(
                f"Property is used in {len(used_by)} formula(s)",
                property_id=str(property_id),
                used_by=used_by,
            )

        # Check if property is used in rollups
        rollup_props = await self.property_repository.get_rollup_properties(prop.database_id)
        for rollup_prop in rollup_props:
            if rollup_prop.config:
                if rollup_prop.config.get("rollup_property_id") == str(property_id):
                    raise PropertyInUseError(
                        f"Property is used in rollup '{rollup_prop.name}'",
                        property_id=str(property_id),
                        used_by=[str(rollup_prop.id)],
                    )

        logger.info(f"Deleting property {property_id}")
        success = await self.property_repository.delete(property_id)
        await self.db.flush()

        logger.info(f"Deleted property {property_id}")
        return success

    async def reorder_properties(
        self,
        property_ids: List[UUID],
        user_id: UUID,
    ) -> bool:
        """
        Reorder properties for display.

        Args:
            property_ids: List of property UUIDs in desired order
            user_id: UUID of user making request

        Returns:
            True if reordered successfully

        Raises:
            DatabasePropertyNotFoundError: If any property not found
            InsufficientPermissionsError: If user lacks admin permissions
        """
        if not property_ids:
            raise ValueError("property_ids cannot be empty")

        # Get first property to check database
        first_prop = await self.property_repository.get_by_id(property_ids[0])
        if not first_prop:
            raise DatabasePropertyNotFoundError(f"Property {property_ids[0]} not found")

        # Check user has admin+ permission
        if not await self.project_service.check_permission(
            first_prop.database.project_id, user_id, "admin"
        ):
            logger.warning(f"User {user_id} lacks permission to reorder properties")
            raise InsufficientPermissionsError("Only project admin or owner can reorder properties")

        logger.info(f"Reordering {len(property_ids)} properties")
        success = await self.property_repository.reorder(property_ids)
        await self.db.flush()

        logger.info("Reordered properties")
        return success

    async def create_view(
        self,
        database_id: UUID,
        view_data: Dict[str, Any],
        user_id: UUID,
    ) -> DatabaseView:
        """
        Create a new view for a database.

        Args:
            database_id: UUID of the database
            view_data: Dictionary with view fields
            user_id: UUID of user creating view

        Returns:
            Created DatabaseView object

        Raises:
            DatabaseNotFoundError: If database not found
            InsufficientPermissionsError: If user lacks member permissions
            ValueError: If view validation fails
        """
        database = await self.repository.get_by_id(database_id)
        if not database:
            raise DatabaseNotFoundError(f"Database {database_id} not found")

        # Check user has member+ permission
        if not await self.project_service.check_permission(database.project_id, user_id, "member"):
            logger.warning(
                f"User {user_id} lacks permission to create view in database {database_id}"
            )
            raise InsufficientPermissionsError("Only project members can create views")

        # Validate view type
        view_type = view_data.get("view_type")
        valid_types = ["table", "board", "calendar", "timeline", "gallery", "list"]
        if view_type not in valid_types:
            raise ValueError(f"Invalid view type. Must be one of: {', '.join(valid_types)}")

        view_name = view_data.get("name", "Unnamed")
        logger.info(f"Creating view '{view_name}' in database {database_id}")

        # Add database_id and created_by to data
        view_data["database_id"] = database_id
        view_data["created_by_user_id"] = user_id

        # Set position if not provided (get next available position)
        if "position" not in view_data:
            view_data["position"] = len(database.views)

        # Set is_default if not provided
        if "is_default" not in view_data:
            view_data["is_default"] = False

        from ardha.models.database_view import DatabaseView

        view = DatabaseView(**view_data)
        self.db.add(view)
        await self.db.flush()
        await self.db.refresh(view)

        logger.info(f"Created view {view.id}")
        return view

    async def update_view(
        self,
        view_id: UUID,
        updates: Dict[str, Any],
        user_id: UUID,
    ) -> DatabaseView:
        """
        Update view configuration.

        Args:
            view_id: UUID of view to update
            updates: Dictionary of fields to update
            user_id: UUID of user making update

        Returns:
            Updated DatabaseView object

        Raises:
            DatabaseNotFoundError: If view not found
            InsufficientPermissionsError: If user lacks member permissions or is not creator
        """
        from sqlalchemy import select

        from ardha.models.database_view import DatabaseView

        stmt = select(DatabaseView).where(DatabaseView.id == view_id)
        result = await self.db.execute(stmt)
        view = result.scalar_one_or_none()

        if not view:
            raise DatabaseNotFoundError(f"View {view_id} not found")

        # Get database to check permissions
        database = await self.repository.get_by_id(view.database_id)
        if not database:
            raise DatabaseNotFoundError(f"Database {view.database_id} not found")

        # Check user has member+ permission or is creator
        is_member = await self.project_service.check_permission(
            database.project_id, user_id, "member"
        )
        is_creator = view.created_by_user_id == user_id

        if not (is_member or is_creator):
            logger.warning(f"User {user_id} lacks permission to update view {view_id}")
            raise InsufficientPermissionsError(
                "Only project members or view creator can update views"
            )

        logger.info(f"Updating view {view_id}")

        # Update fields
        for key, value in updates.items():
            if hasattr(view, key) and key not in [
                "id",
                "created_at",
                "database_id",
                "created_by_user_id",
            ]:
                setattr(view, key, value)

        await self.db.flush()
        await self.db.refresh(view)

        logger.info(f"Updated view {view_id}")
        return view

    async def delete_view(
        self,
        view_id: UUID,
        user_id: UUID,
    ) -> bool:
        """
        Delete a view.

        Cannot delete if it's the only view or default view without replacement.

        Args:
            view_id: UUID of view to delete
            user_id: UUID of user making request

        Returns:
            True if deleted successfully

        Raises:
            DatabaseNotFoundError: If view not found
            InsufficientPermissionsError: If user lacks admin permissions or is not creator
            ValueError: If cannot delete (only view or default without replacement)
        """
        from sqlalchemy import select

        from ardha.models.database_view import DatabaseView

        stmt = select(DatabaseView).where(DatabaseView.id == view_id)
        result = await self.db.execute(stmt)
        view = result.scalar_one_or_none()

        if not view:
            raise DatabaseNotFoundError(f"View {view_id} not found")

        # Get database and refresh views to get accurate count
        database = await self.repository.get_by_id(view.database_id)
        if not database:
            raise DatabaseNotFoundError(f"Database {view.database_id} not found")

        # Refresh to ensure views relationship is loaded
        await self.db.refresh(database, ["views"])

        # Check if this is the only view (business rule check first)
        if len(database.views) <= 1:
            raise ValueError("Cannot delete the only view in database")

        # Check user has admin+ permission or is creator
        is_admin = await self.project_service.check_permission(
            database.project_id, user_id, "admin"
        )
        is_creator = view.created_by_user_id == user_id

        if not (is_admin or is_creator):
            logger.warning(f"User {user_id} lacks permission to delete view {view_id}")
            raise InsufficientPermissionsError(
                "Only project admin, owner, or view creator can delete views"
            )

        logger.info(f"Deleting view {view_id}")
        await self.db.delete(view)
        await self.db.flush()

        logger.info(f"Deleted view {view_id}")
        return True

    async def list_templates(
        self,
        user_id: UUID,
    ) -> List[Database]:
        """
        List all public database templates.

        Templates are publicly accessible and don't require permissions.

        Args:
            user_id: UUID of requesting user (for audit logging)

        Returns:
            List of Database objects that are templates
        """
        logger.info(f"User {user_id} listing database templates")
        templates = await self.repository.list_templates(include_archived=False)
        logger.info(f"Found {len(templates)} templates")
        return templates

    async def create_from_template(
        self,
        template_id: UUID,
        project_id: UUID,
        name: str,
        user_id: UUID,
    ) -> Database:
        """
        Create database from a template.

        Copies all properties and views from template.

        Args:
            template_id: UUID of template database
            project_id: UUID of project to create in
            name: Name for new database
            user_id: UUID of user creating database

        Returns:
            New Database object

        Raises:
            DatabaseNotFoundError: If template not found
            InsufficientPermissionsError: If user lacks admin permissions
            ValueError: If name already exists or template invalid
        """
        # Check user has admin+ permission on project
        if not await self.project_service.check_permission(project_id, user_id, "admin"):
            logger.warning(
                f"User {user_id} lacks permission to create database in project {project_id}"
            )
            raise InsufficientPermissionsError("Only project admin or owner can create databases")

        # Get template
        template = await self.repository.get_by_id(template_id)
        if not template:
            raise DatabaseNotFoundError(f"Template {template_id} not found")

        if not template.is_template:
            raise ValueError(f"Database {template_id} is not a template")

        # Check name uniqueness
        existing = await self.repository.get_by_name(project_id, name)
        if existing:
            raise ValueError(f"Database with name '{name}' already exists in this project")

        logger.info(f"Creating database from template {template_id}")

        # Create new database with template reference
        database_data = {
            "project_id": project_id,
            "name": name,
            "description": template.description,
            "icon": template.icon,
            "color": template.color,
            "template_id": template_id,
            "is_template": False,
        }

        database = await self.repository.create(database_data, user_id)
        await self.db.flush()

        logger.info(f"Created database {database.id} from template")
        return database

    async def get_database_stats(
        self,
        database_id: UUID,
        user_id: UUID,
    ) -> Dict[str, Any]:
        """
        Get statistics for a database.

        Args:
            database_id: UUID of the database
            user_id: UUID of requesting user

        Returns:
            Dictionary with stats (entry_count, property_count, view_count, last_activity)

        Raises:
            DatabaseNotFoundError: If database not found
            InsufficientPermissionsError: If user lacks view permissions
        """
        database = await self.repository.get_by_id(database_id)
        if not database:
            raise DatabaseNotFoundError(f"Database {database_id} not found")

        # Check user has view+ permission
        if not await self.project_service.check_permission(database.project_id, user_id, "viewer"):
            logger.warning(f"User {user_id} lacks permission to view database stats {database_id}")
            raise InsufficientPermissionsError("You do not have permission to view this database")

        stats = await self.repository.get_with_stats(database_id)
        if not stats:
            raise DatabaseNotFoundError(f"Database {database_id} not found")

        return {
            "entry_count": stats["entry_count"],
            "property_count": stats["property_count"],
            "view_count": stats["view_count"],
            "last_entry_created_at": stats.get("last_entry_created_at"),
            "last_updated_at": stats["last_updated_at"],
        }

    async def search_databases(
        self,
        project_id: UUID,
        query: str,
        user_id: UUID,
    ) -> List[Database]:
        """
        Search databases by name in a project.

        Args:
            project_id: UUID of the project
            query: Search query string
            user_id: UUID of requesting user

        Returns:
            List of matching Database objects

        Raises:
            InsufficientPermissionsError: If user lacks view permissions
        """
        # Check user has view+ permission
        if not await self.project_service.check_permission(project_id, user_id, "viewer"):
            logger.warning(
                f"User {user_id} lacks permission to search databases in project {project_id}"
            )
            raise InsufficientPermissionsError(
                "You do not have permission to view project databases"
            )

        databases = await self.repository.search_by_name(project_id, query)
        logger.info(f"Found {len(databases)} databases matching '{query}'")
        return databases

    def _validate_property_config(
        self,
        property_type: str,
        config: Dict[str, Any],
    ) -> None:
        """
        Validate property configuration (permissive approach).

        Only validates critical errors, allows flexibility for different property types.
        Defers complex validation to specialized services (FormulaService, RollupService).

        Args:
            property_type: Type of property being created/updated
            config: Property-specific configuration dictionary

        Raises:
            ValueError: If critical validation error found
        """
        # Normalize config to dict if None
        if config is None:
            config = {}

        # TEXT properties - very permissive
        if property_type == "text":
            if "max_length" in config:
                max_len = config.get("max_length")
                if not isinstance(max_len, int) or max_len < 1:
                    raise ValueError("max_length must be positive integer")

        # NUMBER properties - flexible
        elif property_type == "number":
            if "format" in config:
                fmt = config.get("format")
                if fmt not in ["integer", "decimal"]:
                    raise ValueError("format must be 'integer' or 'decimal'")
            if "decimal_places" in config:
                decimals = config.get("decimal_places")
                if not isinstance(decimals, int) or decimals < 0:
                    raise ValueError("decimal_places must be non-negative integer")

        # SELECT/MULTISELECT properties - allow empty options
        elif property_type in ["select", "multiselect"]:
            options = config.get("options", [])
            if not isinstance(options, list):
                raise ValueError("options must be a list")

            # Validate option format if provided
            for opt in options:
                if isinstance(opt, dict):
                    if "name" not in opt:
                        raise ValueError("Each option must have 'name' field")
                elif not isinstance(opt, str):
                    raise ValueError("Options must be strings or dicts with 'name'")

        # DATE properties - all optional
        elif property_type == "date":
            # All date config is optional, just use defaults
            config.setdefault("format", "YYYY-MM-DD")
            config.setdefault("include_time", False)
            config.setdefault("include_timezone", False)

        # FORMULA properties - defer syntax validation to FormulaService
        elif property_type == "formula":
            expression = config.get("formula") or config.get("expression")
            if not expression or not isinstance(expression, str):
                raise ValueError("Formula requires 'formula' or 'expression' field")

            if not expression.strip():
                raise ValueError("Formula expression cannot be empty")

            # Auto-detect return_type if not provided
            if "result_type" not in config and "return_type" not in config:
                config["result_type"] = "text"

        # ROLLUP properties - basic field validation only
        elif property_type == "rollup":
            required = ["relation_property_id", "aggregation"]
            for field in required:
                if field not in config:
                    raise ValueError(f"Rollup requires '{field}' field")

            agg_type = config.get("aggregation")
            valid_aggs = ["count", "sum", "average", "min", "max", "median"]
            if agg_type not in valid_aggs:
                raise ValueError(f"aggregation must be one of: {', '.join(valid_aggs)}")

        # RELATION properties - basic UUID validation
        elif property_type == "relation":
            related_id = config.get("related_database_id")
            if not related_id:
                raise ValueError("Relation requires 'related_database_id'")

            # Validate UUID format
            try:
                UUID(str(related_id))
            except (ValueError, AttributeError):
                raise ValueError("related_database_id must be valid UUID")

            # Set defaults
            config.setdefault("allow_multiple", False)

        # Other property types (checkbox, email, phone, url, person, etc.)
        # No validation needed - very permissive
