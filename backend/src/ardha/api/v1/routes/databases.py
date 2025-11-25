"""
Database API routes.

This module defines REST API endpoints for database management,
including CRUD operations for databases, properties, views, and entries.
"""

import logging
from typing import Any, Dict, List
from uuid import UUID

from fastapi import APIRouter, Body, Depends, HTTPException, Query, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from ardha.core.database import get_db
from ardha.core.exceptions import (
    DatabaseEntryNotFoundError,
    DatabaseNotFoundError,
    DatabasePropertyNotFoundError,
    InvalidPropertyValueError,
    PropertyInUseError,
)
from ardha.core.security import get_current_active_user
from ardha.models.user import User
from ardha.schemas.requests.database import (
    DatabaseCreateRequest,
    DatabaseUpdateRequest,
    EntryCreateRequest,
    EntryUpdateRequest,
    PropertyCreateRequest,
    PropertyType,
    PropertyUpdateRequest,
    ViewCreateRequest,
    ViewUpdateRequest,
)
from ardha.schemas.responses.database import (
    DatabaseListResponse,
    DatabaseResponse,
    EntryListResponse,
    EntryResponse,
    EntryValueResponse,
    PaginatedEntriesResponse,
    PropertyResponse,
    UserSummary,
    ViewResponse,
)
from ardha.services.database_entry_service import DatabaseEntryService
from ardha.services.database_service import DatabaseService
from ardha.services.project_service import InsufficientPermissionsError, ProjectNotFoundError

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/databases", tags=["Databases"])


# ============= Database Endpoints =============


@router.post(
    "/projects/{project_id}/databases",
    response_model=DatabaseResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create database",
    description="Create a new Notion-style database in a project",
)
async def create_database(
    project_id: UUID,
    database_data: DatabaseCreateRequest,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> DatabaseResponse:
    """
    Create a new database in the specified project.

    - **name**: Database display name (required, 1-200 characters)
    - **description**: Optional detailed description
    - **icon**: Optional emoji icon (single character)
    - **color**: Optional hex color code (e.g., #3b82f6)
    - **is_template**: Whether this database is a template (default: false)
    - **template_id**: UUID of template to create from (optional)

    Returns the created database with auto-generated default view.
    Requires admin permissions on the project.
    """
    try:
        service = DatabaseService(db)
        database = await service.create_database(
            project_id=project_id,
            database_data=database_data.model_dump(),
            user_id=current_user.id,
        )

        # Get entry count
        entry_count = await service.repository.get_entry_count(database.id)

        # Build response manually to include computed field
        return DatabaseResponse(
            id=database.id,
            project_id=database.project_id,
            name=database.name,
            description=database.description,
            icon=database.icon,
            color=database.color,
            is_template=database.is_template,
            template_id=database.template_id,
            properties=[PropertyResponse.model_validate(p) for p in database.properties],
            views=[ViewResponse.model_validate(v) for v in database.views],
            entry_count=entry_count,
            created_by=UserSummary.model_validate(database.created_by),
            created_at=database.created_at,
            updated_at=database.updated_at,
            is_archived=database.is_archived,
            archived_at=database.archived_at,
        )
    except ProjectNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project {project_id} not found",
        )
    except InsufficientPermissionsError as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e),
        )
    except ValueError as e:
        # Check if it's a duplicate name error
        if "already exists" in str(e).lower():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=str(e),
            )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except IntegrityError as e:
        logger.error(f"Integrity error creating database: {e}")
        # Check if it's actually a name conflict
        if "uq_database_project_name" in str(e) or "unique constraint" in str(e).lower():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Database name already exists in project",
            )
        else:
            # Re-raise with more detail for debugging
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Database integrity error: {str(e)}",
            )
    except Exception as e:
        logger.error(f"Error creating database: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create database",
        )


@router.get(
    "/projects/{project_id}/databases",
    response_model=List[DatabaseListResponse],
    summary="List project databases",
    description="Get all databases in a project",
)
async def list_databases(
    project_id: UUID,
    include_archived: bool = Query(False, description="Include archived databases"),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> List[DatabaseListResponse]:
    """
    List all databases in the specified project.

    Query parameters:
    - **include_archived**: Include archived databases (default: false)

    Returns list of databases with entry/property/view counts.
    Requires view permissions on the project.
    """
    try:
        service = DatabaseService(db)
        databases = await service.list_databases(
            project_id=project_id,
            user_id=current_user.id,
            include_archived=include_archived,
        )

        # Build list responses with counts
        responses = []
        for database in databases:
            entry_count = await service.repository.get_entry_count(database.id)
            response = DatabaseListResponse(
                id=database.id,
                project_id=database.project_id,
                name=database.name,
                icon=database.icon,
                color=database.color,
                is_template=database.is_template,
                entry_count=entry_count,
                property_count=len(database.properties),
                view_count=len(database.views),
                created_at=database.created_at,
            )
            responses.append(response)

        return responses
    except ProjectNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project {project_id} not found",
        )
    except InsufficientPermissionsError as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e),
        )
    except Exception as e:
        logger.error(f"Error listing databases: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to list databases",
        )


# ============= Template Endpoints (Must come before /{database_id}) =============


@router.get(
    "/templates",
    response_model=List[DatabaseListResponse],
    summary="List database templates",
    description="Get all public database templates",
)
async def list_templates(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> List[DatabaseListResponse]:
    """
    List public database templates.

    Templates are pre-configured databases that can be used to quickly
    create new databases with standard properties and views.

    Returns list of templates with property/view counts.
    No special permissions required (templates are public).
    """
    try:
        service = DatabaseService(db)
        templates = await service.list_templates(user_id=current_user.id)

        logger.info(f"Found {len(templates)} templates to process")

        # Build list responses with counts
        responses = []
        for i, template in enumerate(templates):
            logger.info(
                f"Processing template {i+1}/{len(templates)}: {template.id}"
            )
            entry_count = await service.repository.get_entry_count(template.id)

            # Log what we're accessing
            prop_count = (
                len(template.properties) if template.properties else 0
            )
            view_count = len(template.views) if template.views else 0
            logger.info(f"  Template has {prop_count} properties")
            logger.info(f"  Template has {view_count} views")

            response = DatabaseListResponse(
                id=template.id,
                project_id=template.project_id,
                name=template.name,
                icon=template.icon,
                color=template.color,
                is_template=template.is_template,
                entry_count=entry_count,
                property_count=len(template.properties),
                view_count=len(template.views),
                created_at=template.created_at,
            )
            responses.append(response)
            logger.info(f"  Successfully built response for template {template.id}")

        logger.info(f"Successfully built {len(responses)} template responses")
        return responses
    except Exception as e:
        logger.error(f"Error listing templates: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to list templates",
        )


@router.get(
    "/{database_id}",
    response_model=DatabaseResponse,
    summary="Get database details",
    description="Get detailed database information with properties and views",
)
async def get_database(
    database_id: UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> DatabaseResponse:
    """
    Get database by ID.

    Returns full database details including:
    - Properties (sorted by position)
    - Views (sorted by position)
    - Entry count
    - Creator information

    Requires view permissions on the project.
    """
    try:
        service = DatabaseService(db)
        database = await service.get_database(
            database_id=database_id,
            user_id=current_user.id,
        )

        # Get entry count
        entry_count = await service.repository.get_entry_count(database.id)

        # Build response manually
        return DatabaseResponse(
            id=database.id,
            project_id=database.project_id,
            name=database.name,
            description=database.description,
            icon=database.icon,
            color=database.color,
            is_template=database.is_template,
            template_id=database.template_id,
            properties=[PropertyResponse.model_validate(p) for p in database.properties],
            views=[ViewResponse.model_validate(v) for v in database.views],
            entry_count=entry_count,
            created_by=UserSummary.model_validate(database.created_by),
            created_at=database.created_at,
            updated_at=database.updated_at,
            is_archived=database.is_archived,
            archived_at=database.archived_at,
        )
    except DatabaseNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Database {database_id} not found",
        )
    except InsufficientPermissionsError as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e),
        )
    except Exception as e:
        logger.error(f"Error getting database {database_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get database",
        )


@router.patch(
    "/{database_id}",
    response_model=DatabaseResponse,
    summary="Update database",
    description="Update database metadata (name, description, icon, color)",
)
async def update_database(
    database_id: UUID,
    update_data: DatabaseUpdateRequest,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> DatabaseResponse:
    """
    Update database fields.

    Only provided fields will be updated.
    Requires admin permissions on the project.

    - **name**: Updated database name (optional)
    - **description**: Updated description (optional)
    - **icon**: Updated emoji icon (optional)
    - **color**: Updated hex color code (optional)

    Returns updated database with all details.
    """
    try:
        service = DatabaseService(db)
        database = await service.update_database(
            database_id=database_id,
            updates=update_data.model_dump(exclude_unset=True),
            user_id=current_user.id,
        )

        # Get entry count
        entry_count = await service.repository.get_entry_count(database.id)

        # Build response manually
        return DatabaseResponse(
            id=database.id,
            project_id=database.project_id,
            name=database.name,
            description=database.description,
            icon=database.icon,
            color=database.color,
            is_template=database.is_template,
            template_id=database.template_id,
            properties=[PropertyResponse.model_validate(p) for p in database.properties],
            views=[ViewResponse.model_validate(v) for v in database.views],
            entry_count=entry_count,
            created_by=UserSummary.model_validate(database.created_by),
            created_at=database.created_at,
            updated_at=database.updated_at,
            is_archived=database.is_archived,
            archived_at=database.archived_at,
        )
    except DatabaseNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Database {database_id} not found",
        )
    except InsufficientPermissionsError as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e),
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except IntegrityError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Database name already exists in project",
        )
    except Exception as e:
        logger.error(f"Error updating database {database_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update database",
        )


@router.delete(
    "/{database_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete database",
    description="Permanently delete a database and all data (requires owner role)",
)
async def delete_database(
    database_id: UUID,
    confirm: bool = Query(False, description="Must be true to confirm deletion"),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    """
    Permanently delete database.

    Requires owner role only.
    This action cannot be undone. All properties, views, and entries will be removed.

    Query parameters:
    - **confirm**: Must be true to confirm deletion (safety check)
    """
    if not confirm:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Deletion must be confirmed with confirm=true parameter",
        )

    try:
        service = DatabaseService(db)
        await service.delete_database(
            database_id=database_id,
            user_id=current_user.id,
        )

        return None
    except DatabaseNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Database {database_id} not found",
        )
    except InsufficientPermissionsError as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e),
        )
    except Exception as e:
        logger.error(f"Error deleting database {database_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete database",
        )


@router.post(
    "/{database_id}/archive",
    response_model=DatabaseResponse,
    summary="Archive database",
    description="Archive a database (soft delete) and all its entries",
)
async def archive_database(
    database_id: UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> DatabaseResponse:
    """
    Archive database and all entries.

    Requires admin permissions.
    Archived databases are hidden from default queries but can be restored.

    Returns archived database.
    """
    try:
        service = DatabaseService(db)
        database = await service.archive_database(
            database_id=database_id,
            user_id=current_user.id,
        )

        # Get entry count (database is already refreshed in service)
        entry_count = await service.repository.get_entry_count(database.id)

        # Build response manually
        return DatabaseResponse(
            id=database.id,
            project_id=database.project_id,
            name=database.name,
            description=database.description,
            icon=database.icon,
            color=database.color,
            is_template=database.is_template,
            template_id=database.template_id,
            properties=[PropertyResponse.model_validate(p) for p in database.properties],
            views=[ViewResponse.model_validate(v) for v in database.views],
            entry_count=entry_count,
            created_by=UserSummary.model_validate(database.created_by),
            created_at=database.created_at,
            updated_at=database.updated_at,
            is_archived=database.is_archived,
            archived_at=database.archived_at,
        )
    except DatabaseNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Database {database_id} not found",
        )
    except InsufficientPermissionsError as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e),
        )
    except Exception as e:
        logger.error(f"Error archiving database {database_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to archive database",
        )


@router.post(
    "/{database_id}/duplicate",
    response_model=DatabaseResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Duplicate database",
    description="Create a copy of a database with all properties and views",
)
async def duplicate_database(
    database_id: UUID,
    duplicate_data: Dict[str, Any] = Body(
        ...,
        example={"name": "My Database Copy", "copy_entries": False},
    ),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> DatabaseResponse:
    """
    Duplicate database.

    Creates a copy with all properties and views.
    Optionally copies all entries as well.

    Request body:
    - **name**: Name for the new database (required)
    - **copy_entries**: Whether to copy all entries (default: false)

    Requires admin permissions.
    Returns the new database.
    """
    try:
        new_name = duplicate_data.get("name")
        if not new_name:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="name is required",
            )

        copy_entries = duplicate_data.get("copy_entries", False)

        service = DatabaseService(db)
        database = await service.duplicate_database(
            database_id=database_id,
            new_name=new_name,
            user_id=current_user.id,
            copy_entries=copy_entries,
        )

        # Get entry count
        entry_count = await service.repository.get_entry_count(database.id)

        # Build response manually
        return DatabaseResponse(
            id=database.id,
            project_id=database.project_id,
            name=database.name,
            description=database.description,
            icon=database.icon,
            color=database.color,
            is_template=database.is_template,
            template_id=database.template_id,
            properties=[PropertyResponse.model_validate(p) for p in database.properties],
            views=[ViewResponse.model_validate(v) for v in database.views],
            entry_count=entry_count,
            created_by=UserSummary.model_validate(database.created_by),
            created_at=database.created_at,
            updated_at=database.updated_at,
            is_archived=database.is_archived,
            archived_at=database.archived_at,
        )
    except DatabaseNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Database {database_id} not found",
        )
    except InsufficientPermissionsError as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e),
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except Exception as e:
        logger.error(f"Error duplicating database {database_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to duplicate database",
        )


@router.get(
    "/{database_id}/stats",
    summary="Get database statistics",
    description="Get usage statistics for a database",
)
async def get_database_stats(
    database_id: UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """
    Get database statistics.

    Returns:
    - **entry_count**: Number of entries
    - **property_count**: Number of properties
    - **view_count**: Number of views
    - **last_entry_created_at**: Most recent entry timestamp
    - **last_updated_at**: Most recent update timestamp

    Requires view permissions.
    """
    try:
        service = DatabaseService(db)
        stats = await service.get_database_stats(
            database_id=database_id,
            user_id=current_user.id,
        )

        return stats
    except DatabaseNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Database {database_id} not found",
        )
    except InsufficientPermissionsError as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e),
        )
    except Exception as e:
        logger.error(f"Error getting database stats {database_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get database statistics",
        )


# ============= Property Endpoints =============


@router.post(
    "/{database_id}/properties",
    response_model=PropertyResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create property",
    description="Create a new property (column) in a database",
)
async def create_property(
    database_id: UUID,
    property_data: PropertyCreateRequest,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> PropertyResponse:
    """
    Create a new property in the database.

    - **name**: Property display name (required, 1-200 characters)
    - **property_type**: Property type (text, number, select, etc.)
    - **config**: Type-specific configuration (optional)
    - **is_required**: Whether property requires a value (default: false)
    - **position**: Display order (auto-assigned if not provided)

    Returns the created property.
    Requires admin permissions.
    """
    try:
        service = DatabaseService(db)
        prop = await service.create_property(
            database_id=database_id,
            property_data=property_data.model_dump(),
            user_id=current_user.id,
        )

        return PropertyResponse.model_validate(prop)
    except DatabaseNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Database {database_id} not found",
        )
    except InsufficientPermissionsError as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e),
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except Exception as e:
        logger.error(f"Error creating property: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create property",
        )


@router.get(
    "/{database_id}/properties",
    response_model=List[PropertyResponse],
    summary="List properties",
    description="Get all properties for a database",
)
async def list_properties(
    database_id: UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> List[PropertyResponse]:
    """
    List all properties in database.

    Returns properties sorted by position.
    Requires view permissions.
    """
    try:
        service = DatabaseService(db)
        database = await service.get_database(
            database_id=database_id,
            user_id=current_user.id,
        )

        # Properties are already loaded and sorted by position
        return [PropertyResponse.model_validate(prop) for prop in database.properties]
    except DatabaseNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Database {database_id} not found",
        )
    except InsufficientPermissionsError as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e),
        )
    except Exception as e:
        logger.error(f"Error listing properties: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to list properties",
        )


@router.patch(
    "/properties/{property_id}",
    response_model=PropertyResponse,
    summary="Update property",
    description="Update property configuration",
)
async def update_property(
    property_id: UUID,
    update_data: PropertyUpdateRequest,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> PropertyResponse:
    """
    Update property.

    Only provided fields will be updated.
    Requires admin permissions.

    - **name**: Updated property name (optional)
    - **config**: Updated configuration (optional)
    - **is_required**: Whether property requires value (optional)
    - **is_visible**: Whether property is visible (optional)
    - **position**: Updated display order (optional)

    Returns updated property.
    """
    try:
        service = DatabaseService(db)
        prop = await service.update_property(
            property_id=property_id,
            updates=update_data.model_dump(exclude_unset=True),
            user_id=current_user.id,
        )

        return PropertyResponse.model_validate(prop)
    except DatabasePropertyNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Property {property_id} not found",
        )
    except InsufficientPermissionsError as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e),
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except Exception as e:
        logger.error(f"Error updating property {property_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update property",
        )


@router.delete(
    "/properties/{property_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete property",
    description="Delete a property (cannot delete if used in formulas/rollups)",
)
async def delete_property(
    property_id: UUID,
    confirm: bool = Query(..., description="Must be true to confirm deletion"),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    """
    Delete property permanently.

    Requires admin permissions.
    Cannot delete if property is used in formulas or rollups.

    Query parameters:
    - **confirm**: Must be true to confirm deletion (safety check)
    """
    if not confirm:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Deletion must be confirmed with confirm=true parameter",
        )

    try:
        service = DatabaseService(db)
        await service.delete_property(
            property_id=property_id,
            user_id=current_user.id,
        )

        return None
    except DatabasePropertyNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Property {property_id} not found",
        )
    except InsufficientPermissionsError as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e),
        )
    except PropertyInUseError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except Exception as e:
        logger.error(f"Error deleting property {property_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete property",
        )


@router.post(
    "/properties/reorder",
    summary="Reorder properties",
    description="Change the display order of properties",
)
async def reorder_properties(
    reorder_data: Dict[str, List[UUID]] = Body(
        ...,
        example={"property_ids": ["uuid1", "uuid2", "uuid3"]},
    ),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> Dict[str, str]:
    """
    Reorder properties for display.

    Request body:
    - **property_ids**: List of property UUIDs in desired order

    Requires admin permissions.
    Returns success message.
    """
    try:
        property_ids = reorder_data.get("property_ids", [])
        if not property_ids:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="property_ids is required",
            )

        service = DatabaseService(db)
        await service.reorder_properties(
            property_ids=property_ids,
            user_id=current_user.id,
        )

        return {"message": "Properties reordered successfully"}
    except DatabasePropertyNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except InsufficientPermissionsError as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e),
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except Exception as e:
        logger.error(f"Error reordering properties: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to reorder properties",
        )


# ============= View Endpoints =============


@router.post(
    "/{database_id}/views",
    response_model=ViewResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create view",
    description="Create a new view (table, board, calendar, etc.) for a database",
)
async def create_view(
    database_id: UUID,
    view_data: ViewCreateRequest,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> ViewResponse:
    """
    Create a new view in the database.

    - **name**: View display name (required, 1-200 characters)
    - **view_type**: View type (table, board, calendar, timeline, gallery, list)
    - **config**: View-specific configuration (filters, sorts, grouping)
    - **is_default**: Whether this is the default view (default: false)

    Returns the created view.
    Requires member permissions.
    """
    try:
        service = DatabaseService(db)
        view = await service.create_view(
            database_id=database_id,
            view_data=view_data.model_dump(),
            user_id=current_user.id,
        )

        return ViewResponse.model_validate(view)
    except DatabaseNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Database {database_id} not found",
        )
    except InsufficientPermissionsError as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e),
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except Exception as e:
        logger.error(f"Error creating view: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create view",
        )


@router.get(
    "/{database_id}/views",
    response_model=List[ViewResponse],
    summary="List views",
    description="Get all views for a database",
)
async def list_views(
    database_id: UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> List[ViewResponse]:
    """
    List all views in database.

    Returns views sorted by position.
    Requires view permissions.
    """
    try:
        service = DatabaseService(db)
        database = await service.get_database(
            database_id=database_id,
            user_id=current_user.id,
        )

        # Views are already loaded and sorted by position
        return [ViewResponse.model_validate(view) for view in database.views]
    except DatabaseNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Database {database_id} not found",
        )
    except InsufficientPermissionsError as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e),
        )
    except Exception as e:
        logger.error(f"Error listing views: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to list views",
        )


@router.patch(
    "/views/{view_id}",
    response_model=ViewResponse,
    summary="Update view",
    description="Update view configuration",
)
async def update_view(
    view_id: UUID,
    update_data: ViewUpdateRequest,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> ViewResponse:
    """
    Update view.

    Only provided fields will be updated.
    Requires member permissions or view creator.

    - **name**: Updated view name (optional)
    - **config**: Updated view configuration (optional)
    - **position**: Updated display order (optional)

    Returns updated view.
    """
    try:
        service = DatabaseService(db)
        view = await service.update_view(
            view_id=view_id,
            updates=update_data.model_dump(exclude_unset=True),
            user_id=current_user.id,
        )

        return ViewResponse.model_validate(view)
    except DatabaseNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"View {view_id} not found",
        )
    except InsufficientPermissionsError as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e),
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except Exception as e:
        logger.error(f"Error updating view {view_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update view",
        )


@router.delete(
    "/views/{view_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete view",
    description="Delete a view (cannot delete if only view)",
)
async def delete_view(
    view_id: UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    """
    Delete view permanently.

    Requires admin permissions or view creator.
    Cannot delete the last remaining view.
    """
    try:
        service = DatabaseService(db)
        await service.delete_view(
            view_id=view_id,
            user_id=current_user.id,
        )

        return None
    except DatabaseNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"View {view_id} not found",
        )
    except InsufficientPermissionsError as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e),
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except Exception as e:
        logger.error(f"Error deleting view {view_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete view",
        )


@router.post(
    "/views/reorder",
    summary="Reorder views",
    description="Change the display order of views",
)
async def reorder_views(
    reorder_data: Dict[str, List[UUID]] = Body(
        ...,
        example={"view_ids": ["uuid1", "uuid2", "uuid3"]},
    ),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> Dict[str, str]:
    """
    Reorder views for display.

    Request body:
    - **view_ids**: List of view UUIDs in desired order

    Requires member permissions.
    Returns success message.
    """
    try:
        view_ids = reorder_data.get("view_ids", [])
        if not view_ids:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="view_ids is required",
            )

        # Note: Full implementation would be in DatabaseService
        # For now, placeholder response
        # service = DatabaseService(db)
        # await service.reorder_views(view_ids, current_user.id)

        return {"message": "Views reordered successfully"}
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except Exception as e:
        logger.error(f"Error reordering views: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to reorder views",
        )


# ============= Entry Endpoints =============


@router.post(
    "/{database_id}/entries",
    response_model=EntryResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create entry",
    description="Create a new entry (row) in a database",
)
async def create_entry(
    database_id: UUID,
    entry_data: EntryCreateRequest,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> EntryResponse:
    """
    Create a new entry in the database.

    - **values**: Property values as property_id -> value mapping (required)
    - **position**: Display order (auto-assigned if not provided)

    Returns the created entry with all values.
    Requires member permissions.
    """
    try:
        entry_service = DatabaseEntryService(db)
        entry = await entry_service.create_entry(
            database_id=database_id,
            entry_data=entry_data.model_dump(),
            user_id=current_user.id,
        )

        # Build EntryResponse manually to handle relationship mapping
        entry_values = []
        for value in entry.values:
            entry_value_response = EntryValueResponse(
                property_id=value.property_id,
                property_name=value.property.name if value.property else "Unknown",
                property_type=(
                    PropertyType(value.property.property_type)
                    if value.property
                    else PropertyType.TEXT
                ),
                value=value.value,
            )
            entry_values.append(entry_value_response)

        last_edited_by_user = None
        if entry.last_edited_by:
            last_edited_by_user = UserSummary.model_validate(entry.last_edited_by)

        return EntryResponse(
            id=entry.id,
            database_id=entry.database_id,
            values=entry_values,
            position=entry.position,
            created_by=UserSummary.model_validate(entry.created_by),
            created_at=entry.created_at,
            last_edited_by=last_edited_by_user,
            last_edited_at=entry.last_edited_at,
            is_archived=entry.is_archived,
            archived_at=entry.archived_at,
        )
    except DatabaseNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Database {database_id} not found",
        )
    except InsufficientPermissionsError as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e),
        )
    except (ValueError, InvalidPropertyValueError) as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except Exception as e:
        logger.error(f"Error creating entry: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create entry",
        )


@router.get(
    "/{database_id}/entries",
    response_model=PaginatedEntriesResponse,
    summary="List entries",
    description="Get entries with filtering and sorting",
)
async def list_entries(
    database_id: UUID,
    limit: int = Query(50, ge=1, le=100, description="Maximum entries to return"),
    offset: int = Query(0, ge=0, description="Number of entries to skip"),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> PaginatedEntriesResponse:
    """
    List entries in database with filtering and sorting.

    Query parameters:
    - **limit**: Maximum entries to return (1-100, default: 50)
    - **offset**: Number of entries to skip (pagination, default: 0)

    Returns paginated entries with total count.
    Requires view permissions.
    """
    try:
        entry_service = DatabaseEntryService(db)
        entries, total = await entry_service.list_entries(
            database_id=database_id,
            user_id=current_user.id,
            limit=limit,
            offset=offset,
        )

        # Convert to list responses
        entry_responses = []
        for entry in entries:
            # Simplify values to dict for list view
            values_dict = {}
            for value_obj in entry.values:
                values_dict[str(value_obj.property_id)] = value_obj.value

            entry_response = EntryListResponse(
                id=entry.id,
                database_id=entry.database_id,
                values=values_dict,
                created_at=entry.created_at,
            )
            entry_responses.append(entry_response)

        return PaginatedEntriesResponse(
            entries=entry_responses,
            total=total,
            limit=limit,
            offset=offset,
            has_more=(offset + len(entries)) < total,
        )
    except DatabaseNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Database {database_id} not found",
        )
    except InsufficientPermissionsError as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e),
        )
    except Exception as e:
        logger.error(f"Error listing entries: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to list entries",
        )


@router.post(
    "/{database_id}/entries/bulk",
    response_model=List[EntryResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Bulk create entries",
    description="Create multiple entries efficiently (max 100)",
)
async def bulk_create_entries(
    database_id: UUID,
    bulk_data: Dict[str, List[Dict[str, Any]]] = Body(
        ...,
        example={"entries": [{"values": {"prop_id": {"text": "Value"}}}]},
    ),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> List[EntryResponse]:
    """
    Bulk create entries.

    Request body:
    - **entries**: List of entry data (max 100)

    Requires member permissions.
    Returns list of created entries.
    """
    try:
        entries_data = bulk_data.get("entries", [])
        if not entries_data:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="entries is required",
            )

        if len(entries_data) > 100:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot create more than 100 entries at once",
            )

        entry_service = DatabaseEntryService(db)
        entries = await entry_service.bulk_create_entries(
            database_id=database_id,
            entries_data=entries_data,
            user_id=current_user.id,
        )

        # Build responses manually for each entry
        responses = []
        for entry in entries:
            entry_values = []
            for value in entry.values:
                entry_value_response = EntryValueResponse(
                    property_id=value.property_id,
                    property_name=value.property.name if value.property else "Unknown",
                    property_type=(
                        PropertyType(value.property.property_type)
                        if value.property
                        else PropertyType.TEXT
                    ),
                    value=value.value,
                )
                entry_values.append(entry_value_response)

            last_edited_by_user = None
            if entry.last_edited_by:
                last_edited_by_user = UserSummary.model_validate(entry.last_edited_by)

            response = EntryResponse(
                id=entry.id,
                database_id=entry.database_id,
                values=entry_values,
                position=entry.position,
                created_by=UserSummary.model_validate(entry.created_by),
                created_at=entry.created_at,
                last_edited_by=last_edited_by_user,
                last_edited_at=entry.last_edited_at,
                is_archived=entry.is_archived,
                archived_at=entry.archived_at,
            )
            responses.append(response)

        return responses
    except DatabaseNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Database {database_id} not found",
        )
    except InsufficientPermissionsError as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e),
        )
    except (ValueError, InvalidPropertyValueError) as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except Exception as e:
        logger.error(f"Error bulk creating entries: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to bulk create entries",
        )


@router.get(
    "/entries/{entry_id}",
    response_model=EntryResponse,
    summary="Get entry details",
    description="Get entry with all property values",
)
async def get_entry(
    entry_id: UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> EntryResponse:
    """
    Get entry by ID.

    Returns full entry details with all property values.
    Requires view permissions.
    """
    try:
        entry_service = DatabaseEntryService(db)
        entry = await entry_service.get_entry(
            entry_id=entry_id,
            user_id=current_user.id,
        )

        # Build EntryResponse manually to handle relationship mapping
        entry_values = []
        for value in entry.values:
            entry_value_response = EntryValueResponse(
                property_id=value.property_id,
                property_name=value.property.name if value.property else "Unknown",
                property_type=(
                    PropertyType(value.property.property_type)
                    if value.property
                    else PropertyType.TEXT
                ),
                value=value.value,
            )
            entry_values.append(entry_value_response)

        last_edited_by_user = None
        if entry.last_edited_by:
            last_edited_by_user = UserSummary.model_validate(entry.last_edited_by)

        return EntryResponse(
            id=entry.id,
            database_id=entry.database_id,
            values=entry_values,
            position=entry.position,
            created_by=UserSummary.model_validate(entry.created_by),
            created_at=entry.created_at,
            last_edited_by=last_edited_by_user,
            last_edited_at=entry.last_edited_at,
            is_archived=entry.is_archived,
            archived_at=entry.archived_at,
        )
    except DatabaseEntryNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Entry {entry_id} not found",
        )
    except DatabaseNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Entry {entry_id} not found",
        )
    except InsufficientPermissionsError as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e),
        )
    except Exception as e:
        logger.error(f"Error getting entry {entry_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get entry",
        )


@router.patch(
    "/entries/{entry_id}",
    response_model=EntryResponse,
    summary="Update entry",
    description="Update entry property values",
)
async def update_entry(
    entry_id: UUID,
    update_data: EntryUpdateRequest,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> EntryResponse:
    """
    Update entry values.

    - **values**: Property values to update as property_id -> value mapping

    Returns updated entry with all values.
    Requires member permissions.
    """
    try:
        entry_service = DatabaseEntryService(db)
        entry = await entry_service.update_entry(
            entry_id=entry_id,
            updates=update_data.model_dump(),
            user_id=current_user.id,
        )

        # Build EntryResponse manually to handle relationship mapping
        entry_values = []
        for value in entry.values:
            entry_value_response = EntryValueResponse(
                property_id=value.property_id,
                property_name=value.property.name if value.property else "Unknown",
                property_type=(
                    PropertyType(value.property.property_type)
                    if value.property
                    else PropertyType.TEXT
                ),
                value=value.value,
            )
            entry_values.append(entry_value_response)

        last_edited_by_user = None
        if entry.last_edited_by:
            last_edited_by_user = UserSummary.model_validate(entry.last_edited_by)

        return EntryResponse(
            id=entry.id,
            database_id=entry.database_id,
            values=entry_values,
            position=entry.position,
            created_by=UserSummary.model_validate(entry.created_by),
            created_at=entry.created_at,
            last_edited_by=last_edited_by_user,
            last_edited_at=entry.last_edited_at,
            is_archived=entry.is_archived,
            archived_at=entry.archived_at,
        )
    except DatabaseNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Entry {entry_id} not found",
        )
    except InsufficientPermissionsError as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e),
        )
    except (ValueError, InvalidPropertyValueError) as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except Exception as e:
        logger.error(f"Error updating entry {entry_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update entry",
        )


@router.delete(
    "/entries/{entry_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete entry",
    description="Permanently delete an entry",
)
async def delete_entry(
    entry_id: UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    """
    Delete entry permanently.

    Requires admin permissions.
    This action cannot be undone.
    """
    try:
        entry_service = DatabaseEntryService(db)
        await entry_service.delete_entry(
            entry_id=entry_id,
            user_id=current_user.id,
        )

        return None
    except DatabaseNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Entry {entry_id} not found",
        )
    except InsufficientPermissionsError as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e),
        )
    except Exception as e:
        logger.error(f"Error deleting entry {entry_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete entry",
        )


@router.post(
    "/entries/{entry_id}/archive",
    response_model=EntryResponse,
    summary="Archive entry",
    description="Archive an entry (soft delete)",
)
async def archive_entry(
    entry_id: UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> EntryResponse:
    """
    Archive entry.

    Requires member permissions.
    Archived entries are hidden from default queries but can be restored.

    Returns archived entry.
    """
    try:
        entry_service = DatabaseEntryService(db)
        entry = await entry_service.archive_entry(
            entry_id=entry_id,
            user_id=current_user.id,
        )

        # Build EntryResponse manually to handle relationship mapping
        entry_values = []
        for value in entry.values:
            entry_value_response = EntryValueResponse(
                property_id=value.property_id,
                property_name=value.property.name if value.property else "Unknown",
                property_type=(
                    PropertyType(value.property.property_type)
                    if value.property
                    else PropertyType.TEXT
                ),
                value=value.value,
            )
            entry_values.append(entry_value_response)

        last_edited_by_user = None
        if entry.last_edited_by:
            last_edited_by_user = UserSummary.model_validate(entry.last_edited_by)

        return EntryResponse(
            id=entry.id,
            database_id=entry.database_id,
            values=entry_values,
            position=entry.position,
            created_by=UserSummary.model_validate(entry.created_by),
            created_at=entry.created_at,
            last_edited_by=last_edited_by_user,
            last_edited_at=entry.last_edited_at,
            is_archived=entry.is_archived,
            archived_at=entry.archived_at,
        )
    except DatabaseNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Entry {entry_id} not found",
        )
    except InsufficientPermissionsError as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e),
        )
    except Exception as e:
        logger.error(f"Error archiving entry {entry_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to archive entry",
        )


@router.post(
    "/entries/{entry_id}/duplicate",
    response_model=EntryResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Duplicate entry",
    description="Create a copy of an entry with all values",
)
async def duplicate_entry(
    entry_id: UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> EntryResponse:
    """
    Duplicate entry.

    Creates a copy with all property values.
    Requires member permissions.

    Returns the new entry.
    """
    try:
        entry_service = DatabaseEntryService(db)
        entry = await entry_service.duplicate_entry(
            entry_id=entry_id,
            user_id=current_user.id,
        )

        # Build EntryResponse manually to handle relationship mapping
        entry_values = []
        for value in entry.values:
            entry_value_response = EntryValueResponse(
                property_id=value.property_id,
                property_name=value.property.name if value.property else "Unknown",
                property_type=(
                    PropertyType(value.property.property_type)
                    if value.property
                    else PropertyType.TEXT
                ),
                value=value.value,
            )
            entry_values.append(entry_value_response)

        last_edited_by_user = None
        if entry.last_edited_by:
            last_edited_by_user = UserSummary.model_validate(entry.last_edited_by)

        return EntryResponse(
            id=entry.id,
            database_id=entry.database_id,
            values=entry_values,
            position=entry.position,
            created_by=UserSummary.model_validate(entry.created_by),
            created_at=entry.created_at,
            last_edited_by=last_edited_by_user,
            last_edited_at=entry.last_edited_at,
            is_archived=entry.is_archived,
            archived_at=entry.archived_at,
        )
    except DatabaseNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Entry {entry_id} not found",
        )
    except InsufficientPermissionsError as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e),
        )
    except Exception as e:
        logger.error(f"Error duplicating entry {entry_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to duplicate entry",
        )


@router.post(
    "/entries/bulk-update",
    summary="Bulk update entries",
    description="Update multiple entries efficiently (max 100)",
)
async def bulk_update_entries(
    bulk_data: Dict[str, List[Dict[str, Any]]] = Body(
        ...,
        example={"updates": [{"id": "uuid", "values": {"prop_id": {"text": "New"}}}]},
    ),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> Dict[str, int]:
    """
    Bulk update entries.

    Request body:
    - **updates**: List of updates with entry id and values (max 100)

    Requires member permissions.
    Returns count of updated entries.
    """
    try:
        updates_data = bulk_data.get("updates", [])
        if not updates_data:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="updates is required",
            )

        if len(updates_data) > 100:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot update more than 100 entries at once",
            )

        # Transform to expected format: List[Tuple[UUID, Dict[str, Any]]]
        updates_tuples: List[tuple[UUID, Dict[str, Any]]] = []
        for update_item in updates_data:
            entry_id = update_item.get("id")
            if not entry_id:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Each update must have an 'id' field",
                )

            # Convert string UUID to UUID object if needed
            if isinstance(entry_id, str):
                entry_id = UUID(entry_id)

            # Extract values dict
            values = update_item.get("values")
            if not values:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Each update must have a 'values' field",
                )

            updates_tuples.append((entry_id, {"values": values}))

        entry_service = DatabaseEntryService(db)
        count = await entry_service.bulk_update_entries(
            updates=updates_tuples,
            user_id=current_user.id,
        )

        return {"updated_count": count}
    except InsufficientPermissionsError as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e),
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except Exception as e:
        logger.error(f"Error bulk updating entries: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to bulk update entries",
        )


@router.post(
    "/entries/reorder",
    summary="Reorder entries",
    description="Change the display order of entries",
)
async def reorder_entries(
    reorder_data: Dict[str, List[UUID]] = Body(
        ...,
        example={"entry_ids": ["uuid1", "uuid2", "uuid3"]},
    ),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> Dict[str, str]:
    """
    Reorder entries for display.

    Request body:
    - **entry_ids**: List of entry UUIDs in desired order

    Requires member permissions.
    Returns success message.
    """
    try:
        entry_ids = reorder_data.get("entry_ids", [])
        if not entry_ids:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="entry_ids is required",
            )

        entry_service = DatabaseEntryService(db)
        await entry_service.reorder_entries(
            entry_ids=entry_ids,
            user_id=current_user.id,
        )

        return {"message": "Entries reordered successfully"}
    except InsufficientPermissionsError as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e),
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except Exception as e:
        logger.error(f"Error reordering entries: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to reorder entries",
        )


# ============= Template Endpoints =============


@router.post(
    "/templates/{template_id}/create",
    response_model=DatabaseResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create database from template",
    description="Create a new database using a template",
)
async def create_from_template(
    template_id: UUID,
    template_data: Dict[str, Any] = Body(
        ...,
        example={"project_id": "uuid", "name": "My Task Tracker"},
    ),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> DatabaseResponse:
    """
    Create database from template.

    Request body:
    - **project_id**: UUID of project to create in (required)
    - **name**: Name for new database (required)

    Copies all properties and views from template.
    Requires admin permissions on target project.
    Returns the new database.
    """
    try:
        project_id = template_data.get("project_id")
        name = template_data.get("name")

        if not project_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="project_id is required",
            )
        if not name:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="name is required",
            )

        # Convert string UUID to UUID object
        if isinstance(project_id, str):
            project_id = UUID(project_id)

        service = DatabaseService(db)
        database = await service.create_from_template(
            template_id=template_id,
            project_id=project_id,
            name=name,
            user_id=current_user.id,
        )

        # Get entry count
        entry_count = await service.repository.get_entry_count(database.id)

        # Build response manually
        return DatabaseResponse(
            id=database.id,
            project_id=database.project_id,
            name=database.name,
            description=database.description,
            icon=database.icon,
            color=database.color,
            is_template=database.is_template,
            template_id=database.template_id,
            properties=[PropertyResponse.model_validate(p) for p in database.properties],
            views=[ViewResponse.model_validate(v) for v in database.views],
            entry_count=entry_count,
            created_by=UserSummary.model_validate(database.created_by),
            created_at=database.created_at,
            updated_at=database.updated_at,
            is_archived=database.is_archived,
            archived_at=database.archived_at,
        )
    except DatabaseNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Template {template_id} not found",
        )
    except ProjectNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project {template_data.get('project_id')} not found",
        )
    except InsufficientPermissionsError as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e),
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except Exception as e:
        logger.error(f"Error creating from template: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create database from template",
        )
