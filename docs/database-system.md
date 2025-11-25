# Ardha Database System Documentation

## Overview

The Ardha Database System provides Notion-style database functionality within projects, enabling users to create custom databases with dynamic properties, multiple views, and powerful data relationships. This comprehensive system supports text, numbers, dates, select options, formulas, rollups, and relations between databases.

## Architecture

### Three-Layer Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    API Layer                             │
│  FastAPI Routes (databases.py) - 25 REST endpoints      │
│  - Request/Response validation                          │
│  - Permission checking                                  │
│  - Error handling                                       │
└─────────────────────────────────────────────────────────┘
                           ↕
┌─────────────────────────────────────────────────────────┐
│                  Service Layer                            │
│  Business Logic (database_service.py)                   │
│  - Database operations                                  │
│  - Property management                                  │
│  - Entry validation                                     │
│  - Formula evaluation                                   │
└─────────────────────────────────────────────────────────┘
                           ↕
┌─────────────────────────────────────────────────────────┐
│                Repository Layer                           │
│  Data Access (database_repository.py)                    │
│  - SQLAlchemy operations                               │
│  - Query optimization                                  │
│  - Relationship loading                                │
│  - Transaction management                              │
└─────────────────────────────────────────────────────────┘
```

### Core Models

1. **Database** - Container for data with metadata
2. **DatabaseProperty** - Column/field definitions with types
3. **DatabaseView** - Different ways to visualize data
4. **DatabaseEntry** - Individual rows/records
5. **DatabaseEntryValue** - Cell values with type validation

## Database Models

### Database Model

```python
class Database:
    id: UUID                    # Primary key
    project_id: UUID            # Parent project
    name: str                   # Display name (1-200 chars)
    description: str | None     # Optional description
    icon: str | None           # Emoji icon (single char)
    color: str | None          # Hex color (#3b82f6)
    is_template: bool          # Template flag
    template_id: UUID | None   # Source template
    is_archived: bool          # Soft delete flag
    archived_at: datetime | None
    created_by_user_id: UUID   # Creator
    created_at: datetime
    updated_at: datetime
```

**Key Features:**
- Unique name constraint within project
- Template system for quick database creation
- Soft delete with archival
- Automatic timestamp tracking

### DatabaseProperty Model

```python
class DatabaseProperty:
    id: UUID                    # Primary key
    database_id: UUID           # Parent database
    name: str                   # Property name (unique within DB)
    property_type: PropertyType # Type enum
    config: dict                # Type-specific configuration
    position: int               # Display order
    is_required: bool           # Validation flag
    is_visible: bool            # UI visibility
    created_at: datetime
    updated_at: datetime
```

**Property Types:**
- `text` - Plain text with optional validation
- `number` - Numeric values with formatting
- `date` - Date/datetime values
- `select` - Predefined options with colors
- `formula` - Calculated values with expressions
- `rollup` - Aggregated values from relations
- `relation` - Links to other databases

### DatabaseView Model

```python
class DatabaseView:
    id: UUID                    # Primary key
    database_id: UUID           # Parent database
    name: str                   # View name
    view_type: ViewType         # Display type
    config: dict                # View configuration
    position: int               # Display order
    is_default: bool            # Default view flag
    created_by_user_id: UUID   # Creator
    created_at: datetime
    updated_at: datetime
```

**View Types:**
- `table` - Spreadsheet-like grid
- `board` - Kanban-style cards
- `list` - Compact list view
- `calendar` - Date-based layout
- `gallery` - Visual card grid

### DatabaseEntry Model

```python
class DatabaseEntry:
    id: UUID                    # Primary key
    database_id: UUID           # Parent database
    position: int               # Display order
    is_archived: bool          # Soft delete flag
    archived_at: datetime | None
    created_by_user_id: UUID   # Creator
    last_edited_by_user_id: UUID # Last editor
    created_at: datetime
    last_edited_at: datetime
```

### DatabaseEntryValue Model

```python
class DatabaseEntryValue:
    id: UUID                    # Primary key
    entry_id: UUID              # Parent entry
    property_id: UUID           # Parent property
    value: dict                 # Typed value data
    created_at: datetime
    updated_at: datetime
```

**Value Structure:**
```python
# Text property
{"text": "Sample text"}

# Number property
{"number": 42.5}

# Date property
{"date": "2024-11-19"}

# Select property
{"select": {"name": "In Progress", "color": "#3B82F6"}}

# Formula property (calculated)
{"formula": {"result": 100, "error": null}}
```

## API Endpoints

### Database Management

#### Create Database
```http
POST /api/v1/databases/projects/{project_id}/databases
Content-Type: application/json

{
    "name": "Task Tracker",
    "description": "Track project tasks",
    "icon": "📋",
    "color": "#3b82f6",
    "is_template": false,
    "template_id": null
}
```

**Response:** `201 Created` with full database details including default view

#### List Databases
```http
GET /api/v1/databases/projects/{project_id}/databases?include_archived=false
```

**Response:** Array of database summaries with entry/property/view counts

#### Get Database Details
```http
GET /api/v1/databases/{database_id}
```

**Response:** Complete database with properties, views, and entry count

#### Update Database
```http
PATCH /api/v1/databases/{database_id}
Content-Type: application/json

{
    "name": "Updated Name",
    "description": "New description"
}
```

#### Archive Database
```http
POST /api/v1/databases/{database_id}/archive
```

**Note:** Soft deletes database and all entries

#### Delete Database
```http
DELETE /api/v1/databases/{database_id}?confirm=true
```

**Note:** Hard delete requires owner role and confirmation

### Property Management

#### Create Property
```http
POST /api/v1/databases/{database_id}/properties
Content-Type: application/json

{
    "name": "Status",
    "property_type": "select",
    "config": {
        "options": [
            {"name": "To Do", "color": "#6B7280"},
            {"name": "In Progress", "color": "#3B82F6"},
            {"name": "Done", "color": "#10B981"}
        ]
    },
    "is_required": false,
    "is_visible": true
}
```

#### Update Property
```http
PATCH /api/v1/databases/properties/{property_id}
Content-Type: application/json

{
    "name": "Updated Name",
    "is_required": true
}
```

#### Delete Property
```http
DELETE /api/v1/databases/properties/{property_id}?confirm=true
```

**Note:** Cascades to delete all entry values

#### Reorder Properties
```http
POST /api/v1/databases/properties/reorder
Content-Type: application/json

{
    "property_ids": ["uuid1", "uuid2", "uuid3"]
}
```

### View Management

#### Create View
```http
POST /api/v1/databases/{database_id}/views
Content-Type: application/json

{
    "name": "Kanban Board",
    "view_type": "board",
    "config": {
        "group_by_property": "status",
        "filters": [],
        "sorts": []
    }
}
```

#### List Views
```http
GET /api/v1/databases/{database_id}/views
```

#### Update View
```http
PATCH /api/v1/databases/views/{view_id}
Content-Type: application/json

{
    "name": "Updated Board",
    "config": {
        "group_by_property": "priority"
    }
}
```

#### Delete View
```http
DELETE /api/v1/databases/views/{view_id}
```

**Note:** Cannot delete the last remaining view

### Entry Management

#### Create Entry
```http
POST /api/v1/databases/{database_id}/entries
Content-Type: application/json

{
    "values": {
        "property_uuid": {"text": "New Task"},
        "property_uuid": {"select": {"name": "To Do", "color": "#6B7280"}},
        "property_uuid": {"number": 5}
    }
}
```

#### List Entries
```http
GET /api/v1/databases/{database_id}/entries?limit=50&offset=0
```

**Response:** Paginated entries with values and metadata

#### Get Entry
```http
GET /api/v1/databases/entries/{entry_id}
```

#### Update Entry
```http
PATCH /api/v1/databases/entries/{entry_id}
Content-Type: application/json

{
    "values": {
        "property_uuid": {"select": {"name": "Done", "color": "#10B981"}}
    }
}
```

#### Delete Entry
```http
DELETE /api/v1/databases/entries/{entry_id}
```

#### Archive Entry
```http
POST /api/v1/databases/entries/{entry_id}/archive
```

#### Duplicate Entry
```http
POST /api/v1/databases/entries/{entry_id}/duplicate
```

### Bulk Operations

#### Bulk Create Entries
```http
POST /api/v1/databases/{database_id}/entries/bulk
Content-Type: application/json

{
    "entries": [
        {"values": {"prop_id": {"text": "Task 1"}}},
        {"values": {"prop_id": {"text": "Task 2"}}}
    ]
}
```

#### Bulk Update Entries
```http
POST /api/v1/databases/entries/bulk-update
Content-Type: application/json

{
    "updates": [
        {"id": "uuid1", "values": {"prop_id": {"text": "Updated"}}},
        {"id": "uuid2", "values": {"prop_id": {"text": "Updated"}}}
    ]
}
```

#### Reorder Entries
```http
POST /api/v1/databases/entries/reorder
Content-Type: application/json

{
    "entry_ids": ["uuid1", "uuid2", "uuid3"]
}
```

### Template System

#### List Templates
```http
GET /api/v1/databases/templates
```

#### Create from Template
```http
POST /api/v1/databases/templates/{template_id}/create
Content-Type: application/json

{
    "project_id": "project_uuid",
    "name": "My Database"
}
```

### Statistics

#### Get Database Stats
```http
GET /api/v1/databases/{database_id}/stats
```

**Response:**
```json
{
    "entry_count": 150,
    "property_count": 8,
    "view_count": 3,
    "last_entry_created_at": "2024-11-19T14:00:00Z"
}
```

## Property Types

### Text Properties

```json
{
    "name": "Description",
    "property_type": "text",
    "config": {
        "placeholder": "Enter description...",
        "max_length": 1000,
        "multiline": true
    }
}
```

**Value Format:**
```json
{"text": "Sample text content"}
```

### Number Properties

```json
{
    "name": "Effort",
    "property_type": "number",
    "config": {
        "format": "number",
        "min": 1,
        "max": 100,
        "precision": 0
    }
}
```

**Value Format:**
```json
{"number": 42.5}
```

### Date Properties

```json
{
    "name": "Due Date",
    "property_type": "date",
    "config": {
        "format": "date",
        "include_time": false
    }
}
```

**Value Format:**
```json
{"date": "2024-11-19"}
```

### Select Properties

```json
{
    "name": "Priority",
    "property_type": "select",
    "config": {
        "options": [
            {"name": "Low", "color": "#6B7280"},
            {"name": "Medium", "color": "#F59E0B"},
            {"name": "High", "color": "#EF4444"}
        ],
        "multiple": false
    }
}
```

**Value Format:**
```json
{"select": {"name": "High", "color": "#EF4444"}}
```

### Formula Properties

```json
{
    "name": "Progress",
    "property_type": "formula",
    "config": {
        "formula": "if(prop('status') == 'Done', 100, 0)",
        "result_type": "number"
    }
}
```

**Formula Functions:**
- `prop(id)` - Get property value
- `if(condition, true_value, false_value)` - Conditional
- `sum(values)` - Sum array
- `count(values)` - Count items
- `date(value)` - Date operations

**Value Format:**
```json
{"formula": {"result": 100, "error": null}}
```

### Relation Properties

```json
{
    "name": "Related Tasks",
    "property_type": "relation",
    "config": {
        "related_database_id": "database_uuid",
        "multiple": true
    }
}
```

**Value Format:**
```json
{"relation": ["entry_uuid1", "entry_uuid2"]}
```

### Rollup Properties

```json
{
    "name": "Total Effort",
    "property_type": "rollup",
    "config": {
        "relation_property_id": "relation_uuid",
        "rollup_property_id": "effort_uuid",
        "aggregation": "sum"
    }
}
```

**Aggregation Types:**
- `count` - Number of related items
- `sum` - Sum of numeric values
- `avg` - Average of numeric values
- `min` - Minimum value
- `max` - Maximum value

## View Types

### Table View

```json
{
    "name": "Table",
    "view_type": "table",
    "config": {
        "filters": [],
        "sorts": [
            {"property_id": "uuid", "direction": "desc"}
        ],
        "column_widths": {
            "property_uuid": 200
        }
    }
}
```

### Board View

```json
{
    "name": "Kanban",
    "view_type": "board",
    "config": {
        "group_by_property": "status_uuid",
        "filters": [],
        "card_size": "medium"
    }
}
```

### List View

```json
{
    "name": "List",
    "view_type": "list",
    "config": {
        "primary_property": "title_uuid",
        "secondary_properties": ["status_uuid"],
        "filters": []
    }
}
```

### Calendar View

```json
{
    "name": "Calendar",
    "view_type": "calendar",
    "config": {
        "date_property": "due_date_uuid",
        "title_property": "title_uuid",
        "filters": []
    }
}
```

### Gallery View

```json
{
    "name": "Gallery",
    "view_type": "gallery",
    "config": {
        "title_property": "title_uuid",
        "image_property": "image_uuid",
        "card_size": "medium",
        "filters": []
    }
}
```

## Permission System

### Role-Based Access Control

| Role | Database CRUD | Property CRUD | Entry CRUD | View CRUD |
|------|---------------|---------------|------------|-----------|
| Owner | ✅ Full | ✅ Full | ✅ Full | ✅ Full |
| Admin | ✅ Full | ✅ Full | ✅ Full | ✅ Full |
| Member | ❌ Create | ✅ Full | ✅ Full | ✅ Full |
| Viewer | ❌ Create | ❌ Create | ✅ Read | ✅ Read |

### Permission Checks

All endpoints verify:
1. **Project Membership** - User must be project member
2. **Role Requirements** - Minimum role for operation
3. **Resource Ownership** - For sensitive operations

## Validation Rules

### Database Validation

- **Name**: 1-200 characters, unique within project
- **Color**: Valid hex color if provided
- **Icon**: Single emoji character if provided

### Property Validation

- **Name**: 1-100 characters, unique within database
- **Type**: Valid PropertyType enum value
- **Config**: Type-specific validation
- **Position**: Non-negative integer

### Entry Validation

- **Required Properties**: All required properties must have values
- **Value Types**: Values must match property type
- **Select Options**: Must be from property's option list
- **Number Range**: Must respect min/max constraints

### Formula Validation

- **Syntax**: Valid formula expression
- **Dependencies**: No circular references
- **Functions**: Valid function calls
- **Types**: Compatible return type

## Performance Optimizations

### Database Indexes

```sql
-- Primary keys
CREATE INDEX pk_databases ON databases(id);
CREATE INDEX pk_properties ON database_properties(id);
CREATE INDEX pk_entries ON database_entries(id);
CREATE INDEX pk_values ON database_entry_values(id);

-- Foreign keys
CREATE INDEX fk_databases_project ON databases(project_id);
CREATE INDEX fk_properties_database ON database_properties(database_id);
CREATE INDEX fk_entries_database ON database_entries(database_id);
CREATE INDEX fk_values_entry ON database_entry_values(entry_id);
CREATE INDEX fk_values_property ON database_entry_values(property_id);

-- Unique constraints
CREATE UNIQUE INDEX uq_database_project_name ON databases(project_id, name) WHERE is_archived = false;
CREATE UNIQUE INDEX uq_property_database_name ON database_properties(database_id, name);

-- Performance indexes
CREATE INDEX idx_entries_created ON database_entries(created_at DESC);
CREATE INDEX idx_entries_position ON database_entries(database_id, position);
CREATE INDEX idx_properties_position ON database_properties(database_id, position);
CREATE INDEX idx_views_position ON database_views(database_id, position);
```

### Query Optimization

1. **Eager Loading** - Use `selectinload()` for relationships
2. **Pagination** - Limit queries to 100 records max
3. **Filtering** - Apply database filters early
4. **Caching** - Cache frequently accessed data

### Bulk Operations

- **Batch Size**: Maximum 100 items per bulk operation
- **Transaction Management**: Single transaction per bulk operation
- **Error Handling**: Continue on individual failures

## Error Handling

### HTTP Status Codes

| Code | Usage | Example |
|------|-------|---------|
| 200 | Success | GET database |
| 201 | Created | POST database |
| 204 | No Content | DELETE database |
| 400 | Bad Request | Invalid data |
| 401 | Unauthorized | Missing auth |
| 403 | Forbidden | Insufficient permissions |
| 404 | Not Found | Resource missing |
| 409 | Conflict | Duplicate name |
| 422 | Validation Error | Invalid property value |
| 500 | Server Error | Database failure |

### Error Response Format

```json
{
    "detail": "Database name already exists in project",
    "error_code": "DATABASE_NAME_EXISTS",
    "field": "name",
    "timestamp": "2024-11-19T14:00:00Z"
}
```

### Common Errors

1. **Database Name Exists** - 409 Conflict
2. **Property Name Exists** - 409 Conflict
3. **Required Property Missing** - 422 Validation Error
4. **Invalid Value Type** - 422 Validation Error
5. **Circular Formula** - 422 Validation Error
6. **Insufficient Permissions** - 403 Forbidden
7. **Resource Not Found** - 404 Not Found

## Testing

### Test Coverage

- **Unit Tests**: Repository layer methods
- **Integration Tests**: API endpoints with real database
- **Fixtures**: Comprehensive test data setup
- **Edge Cases**: Error conditions and validation

### Key Test Scenarios

1. **CRUD Operations** - All create/read/update/delete flows
2. **Permission Enforcement** - Role-based access control
3. **Data Validation** - Input validation and constraints
4. **Bulk Operations** - Efficiency and error handling
5. **Formula Evaluation** - Calculation accuracy
6. **Template System** - Database creation from templates

### Running Tests

```bash
# Database API tests
pytest tests/integration/test_database_api.py -v

# Repository tests
pytest tests/unit/test_database_repository.py -v

# All database-related tests
pytest tests/ -k "database" -v
```

## Migration Strategy

### Database Schema

The database system uses PostgreSQL with the following schema:

```sql
-- Databases table
CREATE TABLE databases (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id UUID NOT NULL REFERENCES projects(id),
    name VARCHAR(200) NOT NULL,
    description TEXT,
    icon VARCHAR(10),
    color VARCHAR(7),
    is_template BOOLEAN DEFAULT false,
    template_id UUID REFERENCES databases(id),
    is_archived BOOLEAN DEFAULT false,
    archived_at TIMESTAMP WITH TIME ZONE,
    created_by_user_id UUID NOT NULL REFERENCES users(id),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now()
);

-- Properties table
CREATE TABLE database_properties (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    database_id UUID NOT NULL REFERENCES databases(id) ON DELETE CASCADE,
    name VARCHAR(100) NOT NULL,
    property_type VARCHAR(20) NOT NULL,
    config JSONB DEFAULT '{}',
    position INTEGER NOT NULL,
    is_required BOOLEAN DEFAULT false,
    is_visible BOOLEAN DEFAULT true,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now()
);

-- Views table
CREATE TABLE database_views (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    database_id UUID NOT NULL REFERENCES databases(id) ON DELETE CASCADE,
    name VARCHAR(100) NOT NULL,
    view_type VARCHAR(20) NOT NULL,
    config JSONB DEFAULT '{}',
    position INTEGER NOT NULL,
    is_default BOOLEAN DEFAULT false,
    created_by_user_id UUID NOT NULL REFERENCES users(id),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now()
);

-- Entries table
CREATE TABLE database_entries (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    database_id UUID NOT NULL REFERENCES databases(id) ON DELETE CASCADE,
    position INTEGER NOT NULL,
    is_archived BOOLEAN DEFAULT false,
    archived_at TIMESTAMP WITH TIME ZONE,
    created_by_user_id UUID NOT NULL REFERENCES users(id),
    last_edited_by_user_id UUID NOT NULL REFERENCES users(id),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
    last_edited_at TIMESTAMP WITH TIME ZONE DEFAULT now()
);

-- Entry values table
CREATE TABLE database_entry_values (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    entry_id UUID NOT NULL REFERENCES database_entries(id) ON DELETE CASCADE,
    property_id UUID NOT NULL REFERENCES database_properties(id) ON DELETE CASCADE,
    value JSONB NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now()
);
```

### Migration Files

Note: Migration files are not present in the current codebase but would be created using Alembic:

```bash
# Create initial migration
alembic revision --autogenerate -m "Create database tables"

# Apply migrations
alembic upgrade head
```

## Usage Examples

### Creating a Task Tracker

```python
# 1. Create database
database = await client.post("/api/v1/databases/projects/project_id/databases", json={
    "name": "Task Tracker",
    "description": "Project task management",
    "icon": "📋",
    "color": "#3b82f6"
})

# 2. Add properties
properties = [
    {"name": "Title", "property_type": "text", "is_required": True},
    {"name": "Status", "property_type": "select", "config": {
        "options": [
            {"name": "To Do", "color": "#6B7280"},
            {"name": "In Progress", "color": "#3B82F6"},
            {"name": "Done", "color": "#10B981"}
        ]
    }},
    {"name": "Priority", "property_type": "select", "config": {
        "options": [
            {"name": "Low", "color": "#6B7280"},
            {"name": "Medium", "color": "#F59E0B"},
            {"name": "High", "color": "#EF4444"}
        ]
    }},
    {"name": "Due Date", "property_type": "date"},
    {"name": "Effort", "property_type": "number", "config": {"min": 1, "max": 10}}
]

for prop in properties:
    await client.post(f"/api/v1/databases/{database['id']}/properties", json=prop)

# 3. Create views
views = [
    {"name": "Board", "view_type": "board", "config": {"group_by_property": "status"}},
    {"name": "Calendar", "view_type": "calendar", "config": {"date_property": "due_date"}}
]

for view in views:
    await client.post(f"/api/v1/databases/{database['id']}/views", json=view)

# 4. Add entries
entries = [
    {"values": {
        "title": {"text": "Implement user authentication"},
        "status": {"select": {"name": "In Progress", "color": "#3B82F6"}},
        "priority": {"select": {"name": "High", "color": "#EF4444"}},
        "due_date": {"date": "2024-12-01"},
        "effort": {"number": 8}
    }},
    {"values": {
        "title": {"text": "Design database schema"},
        "status": {"select": {"name": "Done", "color": "#10B981"}},
        "priority": {"select": {"name": "Medium", "color": "#F59E0B"}},
        "due_date": {"date": "2024-11-15"},
        "effort": {"number": 5}
    }}
]

for entry in entries:
    await client.post(f"/api/v1/databases/{database['id']}/entries", json=entry)
```

### Creating a Formula Property

```python
# Add progress formula
formula_prop = {
    "name": "Progress",
    "property_type": "formula",
    "config": {
        "formula": "if(prop('status') == 'Done', 100, if(prop('status') == 'In Progress', 50, 0))",
        "result_type": "number"
    }
}

await client.post(f"/api/v1/databases/{database['id']}/properties", json=formula_prop)
```

### Creating Database Relations

```python
# Create projects database
projects_db = await client.post("/api/v1/databases/projects/project_id/databases", json={
    "name": "Projects",
    "icon": "🚀"
})

# Add relation property to tasks
relation_prop = {
    "name": "Project",
    "property_type": "relation",
    "config": {
        "related_database_id": projects_db['id'],
        "multiple": false
    }
}

await client.post(f"/api/v1/databases/{database['id']}/properties", json=relation_prop)

# Add rollup to projects
rollup_prop = {
    "name": "Task Count",
    "property_type": "rollup",
    "config": {
        "relation_property_id": relation_prop['id'],
        "rollup_property_id": "title_uuid",  # Count tasks
        "aggregation": "count"
    }
}

await client.post(f"/api/v1/databases/{projects_db['id']}/properties", json=rollup_prop)
```

## Best Practices

### Database Design

1. **Property Planning** - Define properties before creating entries
2. **Type Selection** - Choose appropriate property types
3. **Validation Rules** - Use required fields and constraints
4. **View Configuration** - Create views for different use cases

### Performance

1. **Limit Entries** - Use pagination for large datasets
2. **Optimize Queries** - Apply filters early
3. **Bulk Operations** - Use bulk endpoints for efficiency
4. **Caching** - Cache frequently accessed data

### Security

1. **Permission Checks** - Always verify user permissions
2. **Input Validation** - Validate all user input
3. **SQL Injection** - Use parameterized queries
4. **Data Sanitization** - Clean user-provided data

### Maintenance

1. **Regular Backups** - Backup database regularly
2. **Archive Old Data** - Use archival for unused data
3. **Monitor Performance** - Track query performance
4. **Update Dependencies** - Keep libraries updated

## Troubleshooting

### Common Issues

1. **Database Name Conflict**
   - Error: "Database name already exists in project"
   - Solution: Choose a unique name or archive existing database

2. **Property Validation Error**
   - Error: "Invalid value type for property"
   - Solution: Check property type and provide correct value format

3. **Formula Calculation Error**
   - Error: "Formula evaluation failed"
   - Solution: Check formula syntax and property references

4. **Permission Denied**
   - Error: "Insufficient permissions"
   - Solution: Check user role in project

5. **Circular Reference**
   - Error: "Circular formula reference detected"
   - Solution: Remove circular dependencies in formulas

### Debugging Tips

1. **Check API Responses** - Review error messages and status codes
2. **Verify Data Types** - Ensure values match property types
3. **Test with Small Data** - Start with minimal test data
4. **Use Database Logs** - Check PostgreSQL logs for errors
5. **Validate Permissions** - Confirm user has required role

## Future Enhancements

### Planned Features

1. **Advanced Formulas** - More formula functions and operations
2. **File Attachments** - File upload and management
3. **Real-time Collaboration** - WebSocket-based updates
4. **Import/Export** - CSV, Excel import/export
5. **Advanced Filtering** - Complex filter conditions
6. **Custom Views** - User-defined view configurations

### Performance Improvements

1. **Query Optimization** - Advanced query optimization
2. **Caching Layer** - Redis caching for frequently accessed data
3. **Database Partitioning** - Partition large tables
4. **Connection Pooling** - Optimize database connections

### Integration Features

1. **API Webhooks** - External system integration
2. **Third-party Connectors** - Integration with popular tools
3. **Custom Properties** - User-defined property types
4. **Automation Rules** - Trigger-based automation

---

**Version**: 1.0
**Last Updated**: November 19, 2024
**Maintained By**: Ardha Development Team
**License**: MIT (Open Source)

For more information, visit: https://github.com/ardhaecosystem/Ardha
