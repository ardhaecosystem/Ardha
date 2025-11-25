"""
Database system request schemas.

This module defines Pydantic request models for the database system API,
including databases, properties, views, and entries.
"""

import re
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

# ============= Enums =============


class PropertyType(str, Enum):
    """Supported property types in Notion-style databases."""

    TEXT = "text"
    NUMBER = "number"
    SELECT = "select"
    MULTISELECT = "multiselect"
    DATE = "date"
    CHECKBOX = "checkbox"
    URL = "url"
    EMAIL = "email"
    PHONE = "phone"
    FORMULA = "formula"
    ROLLUP = "rollup"
    RELATION = "relation"
    CREATED_TIME = "created_time"
    CREATED_BY = "created_by"
    LAST_EDITED_TIME = "last_edited_time"
    LAST_EDITED_BY = "last_edited_by"


class ViewType(str, Enum):
    """Supported view types in Notion-style databases."""

    TABLE = "table"
    BOARD = "board"
    CALENDAR = "calendar"
    LIST = "list"
    GALLERY = "gallery"
    TIMELINE = "timeline"


class FilterOperator(str, Enum):
    """Filter operators for entry queries."""

    EQUALS = "equals"
    NOT_EQUALS = "not_equals"
    CONTAINS = "contains"
    NOT_CONTAINS = "not_contains"
    STARTS_WITH = "starts_with"
    ENDS_WITH = "ends_with"
    IS_EMPTY = "is_empty"
    IS_NOT_EMPTY = "is_not_empty"
    GREATER_THAN = "greater_than"
    LESS_THAN = "less_than"
    GREATER_THAN_OR_EQUAL = "greater_than_or_equal"
    LESS_THAN_OR_EQUAL = "less_than_or_equal"
    IS_BEFORE = "is_before"
    IS_AFTER = "is_after"
    IS_ON_OR_BEFORE = "is_on_or_before"
    IS_ON_OR_AFTER = "is_on_or_after"


class SortDirection(str, Enum):
    """Sort direction for entry queries."""

    ASC = "asc"
    DESC = "desc"


# ============= Helper Schemas =============


class FilterCondition(BaseModel):
    """Filter condition for querying database entries."""

    model_config = ConfigDict(protected_namespaces=())

    property_id: UUID = Field(..., description="Property to filter by")
    operator: FilterOperator = Field(..., description="Filter operator")
    value: Optional[Any] = Field(None, description="Value to compare against")


class SortCondition(BaseModel):
    """Sort condition for ordering database entries."""

    model_config = ConfigDict(protected_namespaces=())

    property_id: UUID = Field(..., description="Property to sort by")
    direction: SortDirection = Field(
        default=SortDirection.ASC, description="Sort direction (asc or desc)"
    )


# ============= Database Schemas =============


class DatabaseCreateRequest(BaseModel):
    """Request schema for creating a new database."""

    model_config = ConfigDict(protected_namespaces=())

    name: str = Field(
        ...,
        min_length=1,
        max_length=200,
        description="Database display name",
    )
    description: Optional[str] = Field(None, description="Optional detailed description")
    icon: Optional[str] = Field(None, description="Optional emoji icon (single character)")
    color: Optional[str] = Field(None, description="Optional hex color code (#RRGGBB)")
    is_template: bool = Field(default=False, description="Whether this database is a template")
    template_id: Optional[UUID] = Field(None, description="UUID of template to create from")

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        """Validate database name is not empty after stripping whitespace."""
        if not v or not v.strip():
            raise ValueError("Database name cannot be empty or whitespace only")
        # Allow alphanumeric + spaces, hyphens, underscores
        if not re.match(r"^[a-zA-Z0-9\s\-_]+$", v.strip()):
            raise ValueError(
                "Database name can only contain letters, numbers, spaces, hyphens, and underscores"
            )
        return v.strip()

    @field_validator("icon")
    @classmethod
    def validate_icon(cls, v: Optional[str]) -> Optional[str]:
        """Validate icon is a single emoji character if provided."""
        if v is None:
            return v
        # Simple emoji validation - check length
        if len(v) > 10:  # Allow for multi-byte emoji characters
            raise ValueError("Icon must be a single emoji character")
        return v

    @field_validator("color")
    @classmethod
    def validate_color(cls, v: Optional[str]) -> Optional[str]:
        """Validate color is a valid hex color code if provided."""
        if v is None:
            return v
        if not re.match(r"^#[0-9A-Fa-f]{6}$", v):
            raise ValueError("Color must be a valid hex color code (e.g., #3b82f6)")
        return v.lower()


class DatabaseUpdateRequest(BaseModel):
    """Request schema for updating a database."""

    model_config = ConfigDict(protected_namespaces=())

    name: Optional[str] = Field(
        None,
        min_length=1,
        max_length=200,
        description="Updated database name",
    )
    description: Optional[str] = Field(None, description="Updated description")
    icon: Optional[str] = Field(None, description="Updated emoji icon")
    color: Optional[str] = Field(None, description="Updated hex color code")

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: Optional[str]) -> Optional[str]:
        """Validate database name if provided."""
        if v is None:
            return v
        if not v.strip():
            raise ValueError("Database name cannot be empty or whitespace only")
        if not re.match(r"^[a-zA-Z0-9\s\-_]+$", v.strip()):
            raise ValueError(
                "Database name can only contain letters, numbers, spaces, hyphens, and underscores"
            )
        return v.strip()

    @field_validator("icon")
    @classmethod
    def validate_icon(cls, v: Optional[str]) -> Optional[str]:
        """Validate icon is a single emoji character if provided."""
        if v is None:
            return v
        if len(v) > 10:
            raise ValueError("Icon must be a single emoji character")
        return v

    @field_validator("color")
    @classmethod
    def validate_color(cls, v: Optional[str]) -> Optional[str]:
        """Validate color is a valid hex color code if provided."""
        if v is None:
            return v
        if not re.match(r"^#[0-9A-Fa-f]{6}$", v):
            raise ValueError("Color must be a valid hex color code (e.g., #3b82f6)")
        return v.lower()

    @model_validator(mode="after")
    def check_at_least_one_field(self):
        """Ensure at least one field is provided for update."""
        if not any([self.name, self.description, self.icon, self.color]):
            raise ValueError("At least one field must be provided for update")
        return self


# ============= Property Schemas =============


class PropertyCreateRequest(BaseModel):
    """Request schema for creating a new database property."""

    model_config = ConfigDict(protected_namespaces=())

    name: str = Field(
        ...,
        min_length=1,
        max_length=200,
        description="Property display name",
    )
    property_type: PropertyType = Field(..., description="Property type")
    config: Optional[Dict[str, Any]] = Field(
        None, description="Type-specific configuration in JSON format"
    )
    is_required: bool = Field(default=False, description="Whether this property requires a value")
    position: Optional[int] = Field(
        None,
        ge=0,
        description="Display order (auto-assigned if not provided)",
    )

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        """Validate property name is not empty after stripping whitespace."""
        if not v or not v.strip():
            raise ValueError("Property name cannot be empty or whitespace only")
        return v.strip()


class PropertyUpdateRequest(BaseModel):
    """Request schema for updating a database property."""

    model_config = ConfigDict(protected_namespaces=())

    name: Optional[str] = Field(
        None,
        min_length=1,
        max_length=200,
        description="Updated property name",
    )
    config: Optional[Dict[str, Any]] = Field(
        None, description="Updated type-specific configuration"
    )
    is_required: Optional[bool] = Field(None, description="Whether this property requires a value")
    is_visible: Optional[bool] = Field(
        None, description="Whether this property is visible by default"
    )
    position: Optional[int] = Field(None, ge=0, description="Updated display order")

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: Optional[str]) -> Optional[str]:
        """Validate property name if provided."""
        if v is None:
            return v
        if not v.strip():
            raise ValueError("Property name cannot be empty or whitespace only")
        return v.strip()

    @model_validator(mode="after")
    def check_at_least_one_field(self):
        """Ensure at least one field is provided for update."""
        if not any([self.name, self.config, self.is_required, self.is_visible, self.position]):
            raise ValueError("At least one field must be provided for update")
        return self


# ============= View Schemas =============


class ViewCreateRequest(BaseModel):
    """Request schema for creating a new database view."""

    model_config = ConfigDict(protected_namespaces=())

    name: str = Field(
        ...,
        min_length=1,
        max_length=200,
        description="View display name",
    )
    view_type: ViewType = Field(..., description="View type")
    config: Dict[str, Any] = Field(..., description="View-specific configuration")
    is_default: bool = Field(default=False, description="Whether this is the default view")

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        """Validate view name is not empty after stripping whitespace."""
        if not v or not v.strip():
            raise ValueError("View name cannot be empty or whitespace only")
        return v.strip()


class ViewUpdateRequest(BaseModel):
    """Request schema for updating a database view."""

    model_config = ConfigDict(protected_namespaces=())

    name: Optional[str] = Field(
        None,
        min_length=1,
        max_length=200,
        description="Updated view name",
    )
    config: Optional[Dict[str, Any]] = Field(None, description="Updated view configuration")
    position: Optional[int] = Field(None, ge=0, description="Updated display order")

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: Optional[str]) -> Optional[str]:
        """Validate view name if provided."""
        if v is None:
            return v
        if not v.strip():
            raise ValueError("View name cannot be empty or whitespace only")
        return v.strip()

    @model_validator(mode="after")
    def check_at_least_one_field(self):
        """Ensure at least one field is provided for update."""
        if not any([self.name, self.config, self.position]):
            raise ValueError("At least one field must be provided for update")
        return self


# ============= Entry Schemas =============


class EntryCreateRequest(BaseModel):
    """Request schema for creating a new database entry."""

    model_config = ConfigDict(protected_namespaces=())

    values: Dict[str, Any] = Field(
        ...,
        description="Property values as property_id -> value mapping",
    )
    position: Optional[int] = Field(
        None,
        ge=0,
        description="Display order (auto-assigned if not provided)",
    )

    @field_validator("values")
    @classmethod
    def validate_values(cls, v: Dict[str, Any]) -> Dict[str, Any]:
        """Validate values dictionary is not empty."""
        if not v:
            raise ValueError("At least one property value must be provided")
        # Validate all keys are valid UUIDs (property IDs)
        for key in v.keys():
            try:
                UUID(key)
            except ValueError:
                raise ValueError(f"Invalid property ID format: {key}")
        return v


class EntryUpdateRequest(BaseModel):
    """Request schema for updating a database entry."""

    model_config = ConfigDict(protected_namespaces=())

    values: Dict[str, Any] = Field(
        ...,
        description="Property values to update as property_id -> value mapping",
    )

    @field_validator("values")
    @classmethod
    def validate_values(cls, v: Dict[str, Any]) -> Dict[str, Any]:
        """Validate values dictionary is not empty and has valid UUIDs."""
        if not v:
            raise ValueError("At least one property value must be provided for update")
        # Validate all keys are valid UUIDs
        for key in v.keys():
            try:
                UUID(key)
            except ValueError:
                raise ValueError(f"Invalid property ID format: {key}")
        return v


class EntryFilterRequest(BaseModel):
    """Request schema for filtering database entries."""

    model_config = ConfigDict(protected_namespaces=())

    filters: List[FilterCondition] = Field(
        default_factory=list, description="List of filter conditions"
    )
    sorts: List[SortCondition] = Field(default_factory=list, description="List of sort conditions")
    limit: int = Field(
        default=50,
        ge=1,
        le=100,
        description="Maximum number of entries to return (max 100)",
    )
    offset: int = Field(default=0, ge=0, description="Number of entries to skip for pagination")
