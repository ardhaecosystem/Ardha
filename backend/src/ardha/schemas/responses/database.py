"""
Database system response schemas.

This module defines Pydantic response models for the database system API,
including databases, properties, views, and entries.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from ardha.schemas.requests.database import PropertyType, ViewType

# ============= User Summary Schema =============


class UserSummary(BaseModel):
    """Lightweight user information for response nesting."""

    model_config = ConfigDict(from_attributes=True, protected_namespaces=())

    id: UUID = Field(..., description="User UUID")
    email: str = Field(..., description="User email")
    full_name: str = Field(..., description="User full name")
    avatar_url: Optional[str] = Field(None, description="User avatar URL")


# ============= Property Response =============


class PropertyResponse(BaseModel):
    """Response schema for database property."""

    model_config = ConfigDict(from_attributes=True, protected_namespaces=())

    id: UUID = Field(..., description="Property UUID")
    database_id: UUID = Field(..., description="Database UUID")
    name: str = Field(..., description="Property display name")
    property_type: PropertyType = Field(..., description="Property type")
    config: Optional[Dict[str, Any]] = Field(None, description="Type-specific configuration")
    position: int = Field(..., description="Display order (0-based)")
    is_required: bool = Field(..., description="Whether property requires a value")
    is_visible: bool = Field(..., description="Whether property is visible by default")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")


# ============= View Response =============


class ViewResponse(BaseModel):
    """Response schema for database view."""

    model_config = ConfigDict(from_attributes=True, protected_namespaces=())

    id: UUID = Field(..., description="View UUID")
    database_id: UUID = Field(..., description="Database UUID")
    name: str = Field(..., description="View display name")
    view_type: ViewType = Field(..., description="View type")
    config: Dict[str, Any] = Field(..., description="View-specific configuration")
    position: int = Field(..., description="Display order (0-based)")
    is_default: bool = Field(..., description="Whether this is the default view")
    created_by: UserSummary = Field(..., description="User who created this view")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")


# ============= Database Response =============


class DatabaseResponse(BaseModel):
    """Response schema for database with all details."""

    model_config = ConfigDict(from_attributes=True, protected_namespaces=())

    id: UUID = Field(..., description="Database UUID")
    project_id: UUID = Field(..., description="Project UUID")
    name: str = Field(..., description="Database display name")
    description: Optional[str] = Field(None, description="Database description")
    icon: Optional[str] = Field(None, description="Emoji icon")
    color: Optional[str] = Field(None, description="Hex color code")
    is_template: bool = Field(..., description="Whether this is a template")
    template_id: Optional[UUID] = Field(None, description="Template UUID if created from template")
    properties: List[PropertyResponse] = Field(
        default_factory=list, description="Database properties"
    )
    views: List[ViewResponse] = Field(default_factory=list, description="Database views")
    entry_count: int = Field(..., description="Number of entries (computed)")
    created_by: UserSummary = Field(..., description="User who created this database")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")
    is_archived: bool = Field(..., description="Whether database is archived")


class DatabaseListResponse(BaseModel):
    """Lightweight response schema for database list views."""

    model_config = ConfigDict(from_attributes=True, protected_namespaces=())

    id: UUID = Field(..., description="Database UUID")
    project_id: UUID = Field(..., description="Project UUID")
    name: str = Field(..., description="Database display name")
    icon: Optional[str] = Field(None, description="Emoji icon")
    color: Optional[str] = Field(None, description="Hex color code")
    is_template: bool = Field(..., description="Whether this is a template")
    entry_count: int = Field(..., description="Number of entries")
    property_count: int = Field(..., description="Number of properties")
    view_count: int = Field(..., description="Number of views")
    created_at: datetime = Field(..., description="Creation timestamp")


# ============= Entry Response =============


class EntryValueResponse(BaseModel):
    """Response schema for entry property value with metadata."""

    model_config = ConfigDict(from_attributes=True, protected_namespaces=())

    property_id: UUID = Field(..., description="Property UUID")
    property_name: str = Field(..., description="Property display name")
    property_type: PropertyType = Field(..., description="Property type")
    value: Optional[Dict[str, Any]] = Field(
        None, description="Property value in type-specific format"
    )


class EntryResponse(BaseModel):
    """Response schema for database entry with all details."""

    model_config = ConfigDict(from_attributes=True, protected_namespaces=())

    id: UUID = Field(..., description="Entry UUID")
    database_id: UUID = Field(..., description="Database UUID")
    values: List[EntryValueResponse] = Field(
        default_factory=list, description="Property values with metadata"
    )
    position: int = Field(..., description="Display order (0-based)")
    created_by: UserSummary = Field(..., description="User who created this entry")
    created_at: datetime = Field(..., description="Creation timestamp")
    last_edited_by: UserSummary = Field(..., description="User who last edited")
    last_edited_at: datetime = Field(..., description="Last edit timestamp")


class EntryListResponse(BaseModel):
    """Lightweight response schema for entry list views."""

    model_config = ConfigDict(from_attributes=True, protected_namespaces=())

    id: UUID = Field(..., description="Entry UUID")
    database_id: UUID = Field(..., description="Database UUID")
    values: Dict[str, Any] = Field(
        ..., description="Simplified property values as property_id -> value mapping"
    )
    created_at: datetime = Field(..., description="Creation timestamp")


class PaginatedEntriesResponse(BaseModel):
    """Response schema for paginated entry lists."""

    model_config = ConfigDict(protected_namespaces=())

    entries: List[EntryListResponse] = Field(default_factory=list, description="List of entries")
    total: int = Field(..., description="Total number of entries matching filters")
    limit: int = Field(..., description="Number of entries requested per page")
    offset: int = Field(..., description="Number of entries skipped")
    has_more: bool = Field(..., description="Whether more entries exist")


# ============= Database Pagination Response =============


class PaginatedDatabasesResponse(BaseModel):
    """Response schema for paginated database lists."""

    model_config = ConfigDict(protected_namespaces=())

    databases: List[DatabaseListResponse] = Field(
        default_factory=list, description="List of databases"
    )
    total: int = Field(..., description="Total number of databases")
    limit: int = Field(..., description="Number of databases per page")
    offset: int = Field(..., description="Number of databases skipped")
    has_more: bool = Field(..., description="Whether more databases exist")
