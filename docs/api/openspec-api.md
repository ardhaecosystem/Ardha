# OpenSpec API Documentation

## Overview

The OpenSpec API provides endpoints for managing AI-generated project specifications through a complete lifecycle from creation to archival. OpenSpec proposals bridge the gap between project planning and implementation by storing structured specifications, tasks, and metadata that can be synchronized with the project management system.

## Base URL

```
/api/v1/openspec
```

## Authentication

All OpenSpec API endpoints require authentication via JWT token. Include the token in the Authorization header:

```
Authorization: Bearer <your-jwt-token>
```

## Core Concepts

### Proposal Structure

Each OpenSpec proposal consists of:

- **proposal.md**: Main proposal document with summary, motivation, and implementation plan
- **tasks.md**: Detailed task breakdown with identifiers, estimates, and acceptance criteria
- **spec-delta.md**: Changes to project specifications
- **metadata.json**: Structured metadata with proposal details

### Proposal Statuses

- `pending`: Initial state, awaiting review
- `approved`: Proposal approved, ready for task synchronization
- `rejected`: Proposal rejected with reason
- `in_progress`: Tasks being implemented
- `completed`: All tasks completed
- `archived`: Proposal archived and moved to archive directory

### Task Sync Statuses

- `not_synced`: Tasks not yet synchronized to database
- `syncing`: Task synchronization in progress
- `synced`: Tasks successfully synchronized
- `sync_failed`: Task synchronization failed

## Endpoints

### 1. Create Proposal from Filesystem

**POST** `/projects/{project_id}/proposals`

Creates an OpenSpec proposal by reading from the filesystem directory `openspec/changes/{proposal_name}`.

#### Request

```json
{
  "proposal_name": "user-auth-system"
}
```

#### Path Parameters

- `project_id` (UUID): Project ID to associate the proposal with

#### Response

```json
{
  "id": "123e4567-e89b-12d3-a456-426614174000",
  "project_id": "123e4567-e89b-12d3-a456-426614174001",
  "name": "user-auth-system",
  "directory_path": "/home/veda/ardha-projects/Ardha/openspec/changes/user-auth-system",
  "status": "pending",
  "created_by_user_id": "123e4567-e89b-12d3-a456-426614174002",
  "created_by_username": "john_doe",
  "created_by_full_name": "John Doe",
  "proposal_content": "# User Authentication System\n\n## Summary\n...",
  "tasks_content": "## Task Breakdown\n\n### TAS-001: Implement login endpoint...",
  "spec_delta_content": "## API Changes\n\n...",
  "metadata_json": {
    "proposal_id": "user-auth-001",
    "title": "User Authentication System",
    "author": "John Doe",
    "created_at": "2025-11-15T10:00:00Z"
  },
  "approved_by_user_id": null,
  "approved_by_username": null,
  "approved_by_full_name": null,
  "approved_at": null,
  "archived_at": null,
  "completion_percentage": 0,
  "task_sync_status": "not_synced",
  "last_sync_at": null,
  "sync_error_message": null,
  "created_at": "2025-11-15T10:00:00Z",
  "updated_at": "2025-11-15T10:00:00Z",
  "is_editable": true,
  "can_approve": true
}
```

#### Error Responses

- `400`: Validation error or invalid proposal structure
- `403`: Forbidden (insufficient permissions)
- `404`: Proposal directory not found on filesystem
- `409`: Conflict (proposal name already exists in database)

---

### 2. List Project Proposals

**GET** `/projects/{project_id}/proposals`

Retrieves a paginated list of proposals for a project with optional filtering.

#### Query Parameters

- `status` (string, optional): Filter by proposal status
  - Values: `pending`, `approved`, `rejected`, `in_progress`, `completed`, `archived`
- `skip` (integer, default: 0): Pagination offset
- `limit` (integer, default: 100, max: 100): Page size

#### Response

```json
{
  "proposals": [
    {
      "id": "123e4567-e89b-12d3-a456-426614174000",
      "project_id": "123e4567-e89b-12d3-a456-426614174001",
      "name": "user-auth-system",
      "status": "pending",
      "created_by_user_id": "123e4567-e89b-12d3-a456-426614174002",
      "created_by_username": "john_doe",
      "approved_by_user_id": null,
      "approved_by_username": null,
      "completion_percentage": 0,
      "task_sync_status": "not_synced",
      "created_at": "2025-11-15T10:00:00Z",
      "updated_at": "2025-11-15T10:00:00Z"
    }
  ],
  "total": 1,
  "skip": 0,
  "limit": 100
}
```

#### Error Responses

- `403`: Forbidden (insufficient permissions)

---

### 3. Get Proposal Details

**GET** `/proposals/{proposal_id}`

Retrieves complete OpenSpec proposal with all content fields.

#### Path Parameters

- `proposal_id` (UUID): Proposal ID

#### Response

Same as Create Proposal response, with all content fields populated.

#### Error Responses

- `403`: Forbidden (insufficient permissions)
- `404`: Proposal not found

---

### 4. Update Proposal Content

**PATCH** `/proposals/{proposal_id}`

Updates proposal content fields. Only proposals with status 'pending' or 'rejected' can be updated.

#### Request

```json
{
  "proposal_content": "# Updated User Authentication System\n\n## Summary\n...",
  "tasks_content": "## Updated Task Breakdown\n\n### TAS-001: ...",
  "spec_delta_content": "## Updated API Changes\n\n...",
  "metadata_json": {
    "proposal_id": "user-auth-001",
    "title": "Updated User Authentication System",
    "author": "John Doe",
    "created_at": "2025-11-15T10:00:00Z"
  }
}
```

All fields are optional for partial updates.

#### Response

Updated proposal object with new content.

#### Error Responses

- `400`: Bad request (proposal not editable)
- `403`: Forbidden (insufficient permissions)
- `404`: Proposal not found

---

### 5. Approve Proposal

**POST** `/proposals/{proposal_id}/approve`

Approves a pending proposal. Requires project admin permissions.

#### Path Parameters

- `proposal_id` (UUID): Proposal ID

#### Response

Approved proposal object with status set to 'approved' and approval metadata.

#### Error Responses

- `400`: Bad request (proposal not approvable)
- `403`: Forbidden (insufficient permissions)
- `404`: Proposal not found

---

### 6. Reject Proposal

**POST** `/proposals/{proposal_id}/reject`

Rejects a proposal with a reason. Requires project admin permissions.

#### Request

```json
{
  "reason": "The proposed implementation conflicts with existing architecture patterns and would require significant refactoring of the authentication module."
}
```

#### Path Parameters

- `proposal_id` (UUID): Proposal ID

#### Response

Rejected proposal object with status set to 'rejected'.

#### Error Responses

- `403`: Forbidden (insufficient permissions)
- `404`: Proposal not found

---

### 7. Sync Tasks to Database

**POST** `/proposals/{proposal_id}/sync-tasks`

Creates tasks from proposal's tasks.md content and links them to the proposal. Only works for approved proposals.

#### Path Parameters

- `proposal_id` (UUID): Proposal ID

#### Response

```json
{
  "proposal_id": "123e4567-e89b-12d3-a456-426614174000",
  "tasks_created": 5,
  "tasks_updated": 0,
  "sync_status": "synced",
  "error_message": null,
  "synced_at": "2025-11-15T11:00:00Z"
}
```

#### Error Responses

- `400`: Bad request (proposal not approved or sync error)
- `403`: Forbidden (insufficient permissions)
- `404`: Proposal not found

---

### 8. Refresh from Filesystem

**POST** `/proposals/{proposal_id}/refresh`

Re-reads proposal content from filesystem and updates database. Sets task_sync_status to 'not_synced' if tasks.md changes.

#### Path Parameters

- `proposal_id` (UUID): Proposal ID

#### Response

Updated proposal object with refreshed content.

#### Error Responses

- `400`: Bad request (parse error)
- `403`: Forbidden (insufficient permissions)
- `404`: Proposal or filesystem directory not found

---

### 9. Archive Proposal

**POST** `/proposals/{proposal_id}/archive`

Archives a completed proposal and moves filesystem directory to archive/. Requires project admin permissions.

#### Path Parameters

- `proposal_id` (UUID): Proposal ID

#### Response

Archived proposal object with status set to 'archived'.

#### Error Responses

- `403`: Forbidden (insufficient permissions)
- `404`: Proposal not found

---

### 10. Delete Proposal

**DELETE** `/proposals/{proposal_id}`

Deletes a proposal permanently. Cannot delete proposals with synced tasks - archive them instead.

#### Path Parameters

- `proposal_id` (UUID): Proposal ID

#### Response

```json
{
  "message": "Proposal deleted successfully"
}
```

#### Error Responses

- `400`: Bad request (proposal has synced tasks)
- `403`: Forbidden (insufficient permissions)
- `404`: Proposal not found

## File System Integration

### Directory Structure

```
openspec/
├── changes/           # Active proposals
│   ├── proposal-1/
│   │   ├── proposal.md
│   │   ├── tasks.md
│   │   ├── spec-delta.md
│   │   ├── metadata.json
│   │   ├── README.md (optional)
│   │   └── risk-assessment.md (optional)
│   └── proposal-2/
└── archive/           # Archived proposals
    ├── proposal-1/
    └── proposal-3/
```

### Required Files

#### proposal.md
Must contain these sections:
- Summary
- Motivation
- Implementation Plan

#### tasks.md
Contains task breakdown with identifiers like:
- `## TAS-001: Implement login endpoint`
- `## TASK-002: Create user registration`

Each task can include:
- Description
- Phase (e.g., "Phase 1", "Week 2")
- Estimated hours (e.g., "2-4 hours", "1 day")
- Dependencies (e.g., "Depends on: TAS-001")
- Acceptance criteria (bullet points)

#### spec-delta.md
Changes to project specifications.

#### metadata.json
Required fields:
- `proposal_id`: Unique identifier
- `title`: Proposal title
- `author`: Author name
- `created_at`: ISO timestamp

Optional fields:
- `priority`: "low", "medium", "high", "critical"
- `estimated_effort`: e.g., "2-4 weeks"
- `tags`: Array of strings

## Task Parsing

The parser extracts tasks from tasks.md using these patterns:

### Task Identifiers
- `## TAS-001: Task title`
- `### TASK-002: Task title`
- `## T001: Task title`

### Estimated Hours
- `2-4 hours` (uses upper bound: 4)
- `4 hours` (uses: 4)
- `1 day` (converts to 8 hours)
- `4h` (uses: 4)

### Dependencies
- `Depends on: TAS-001, TAS-002`
- `Depends on TAS-001`

### Acceptance Criteria
```markdown
## Acceptance Criteria
- Returns valid JWT tokens
- Validates credentials
- Handles errors gracefully
```

## Permissions

### Project Roles
- **viewer**: Can view proposals
- **member**: Can view and create proposals, update own proposals
- **admin**: Can approve/reject/archive/delete proposals, update any proposal

### Proposal Editability
Proposals are editable when:
- Status is `pending` or `rejected`
- User is the creator (member role) or has admin role

### Proposal Approvability
Proposals are approvable when:
- Status is `pending`
- User has admin role
- Proposal has no validation errors

## Error Handling

### Common Error Formats

```json
{
  "detail": "Error message describing the issue"
}
```

### Validation Errors
- Missing required files
- Invalid proposal structure
- Malformed metadata.json
- Parse errors in markdown files

### Permission Errors
- User not in project
- Insufficient role for operation
- Proposal not editable/approvable

### File System Errors
- Proposal directory not found
- File read/parse errors
- Permission denied accessing files

## Rate Limiting

- Standard API rate limits apply
- File-intensive operations (create, refresh) may have additional limits
- Bulk operations should be spaced out

## Monitoring

### Key Metrics
- Proposal creation rate
- Approval/rejection ratios
- Task sync success rates
- File system operation performance

### Logging Levels
- `INFO`: Proposal lifecycle events
- `WARN`: File system warnings, validation issues
- `ERROR`: Parse failures, database errors
- `DEBUG`: Detailed parsing information

## Best Practices

### Proposal Creation
1. Ensure all required files exist before creating
2. Validate markdown structure
3. Use consistent task identifier format
4. Include meaningful metadata

### Task Management
1. Sync tasks only after approval
2. Use descriptive task titles
3. Include acceptance criteria
4. Estimate hours realistically

### File System
1. Use descriptive directory names
2. Keep proposals in changes/ until archived
3. Include optional files for completeness
4. Maintain consistent formatting

### API Usage
1. Check permissions before operations
2. Handle validation errors gracefully
3. Use pagination for large lists
4. Cache proposal data where appropriate

## Integration Examples

### Creating a Proposal from AI Workflow

```python
# After AI generates proposal files
proposal_name = "user-auth-system"
project_id = "your-project-uuid"

response = requests.post(
    f"{API_BASE}/projects/{project_id}/proposals",
    json={"proposal_name": proposal_name},
    headers={"Authorization": f"Bearer {token}"}
)

if response.status_code == 201:
    proposal = response.json()
    print(f"Created proposal: {proposal['id']}")
```

### Syncing Tasks After Approval

```python
# After proposal is approved
proposal_id = "proposal-uuid"

response = requests.post(
    f"{API_BASE}/proposals/{proposal_id}/sync-tasks",
    headers={"Authorization": f"Bearer {token}"}
)

if response.status_code == 200:
    result = response.json()
    print(f"Created {result['tasks_created']} tasks")
```

### Monitoring Proposal Progress

```python
# Get proposal with completion status
response = requests.get(
    f"{API_BASE}/proposals/{proposal_id}",
    headers={"Authorization": f"Bearer {token}"}
)

proposal = response.json()
print(f"Progress: {proposal['completion_percentage']}%")
print(f"Sync status: {proposal['task_sync_status']}")
```

## Version History

- **v1.0**: Initial OpenSpec API implementation
- **v1.1**: Added task parsing improvements
- **v1.2**: Enhanced validation and error handling
- **v1.3**: Added proposal refresh functionality
- **v1.4**: Improved metadata parsing and validation

## Support

For issues with the OpenSpec API:
1. Check the error messages for specific issues
2. Verify file system permissions and structure
3. Review proposal validation requirements
4. Contact the development team for persistent issues
