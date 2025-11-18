# Ardha Git Integration Guide

## Overview

Ardha provides comprehensive Git integration that bridges version control with project management. This integration enables automatic task linking, commit tracking, and seamless collaboration between Git operations and Ardha's project workflow.

## Architecture

### Three-Layer Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    API Layer (FastAPI)                        │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐│
│  │   Git Routes    │  │  Commit Routes  │  │ Status Routes   ││
│  │   /git/*        │  │  /commits/*     │  │  /status/*      ││
│  └─────────────────┘  └─────────────────┘  └─────────────────┘│
└─────────────────────────────────────────────────────────────┘
                                │
┌─────────────────────────────────────────────────────────────┐
│                  Service Layer (Business Logic)              │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐│
│  │   GitService    │  │GitCommitService │  │ProjectService  ││
│  │ (GitPython)     │  │ (Database)      │  │ (Permissions)   ││
│  └─────────────────┘  └─────────────────┘  └─────────────────┘│
└─────────────────────────────────────────────────────────────┘
                                │
┌─────────────────────────────────────────────────────────────┐
│                   Data Layer (Storage)                       │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐│
│  │  Git Repository │  │   PostgreSQL    │  │  File System    ││
│  │  (.git)         │  │  (Commits)      │  │  (Working Dir)   ││
│  └─────────────────┘  └─────────────────┘  └─────────────────┘│
└─────────────────────────────────────────────────────────────┘
```

### Core Components

1. **GitService** - Low-level Git operations using GitPython
2. **GitCommitService** - Business logic for commit management
3. **GitCommit Model** - Database representation of commits
4. **Git API Routes** - REST endpoints for Git operations

## Features

### ✅ Commit Management
- Create commits with automatic task linking
- Track commit metadata (SHA, author, message, stats)
- Link commits to tasks via commit message parsing
- Store commit history in database

### ✅ Repository Operations
- Initialize Git repositories
- Clone from remote repositories
- Get repository status and information
- Manage branches (create, switch, delete)

### ✅ File Operations
- Stage, unstage, and commit files
- Track file changes across commits
- Get file history and blame information
- Read/write files with Git integration

### ✅ Remote Operations
- Push commits to remote repositories
- Pull changes from remote
- Manage remote repositories
- Handle authentication and conflicts

### ✅ Task Integration
- Automatic task ID extraction from commit messages
- Support for multiple task ID formats (TAS-001, #123, ARD-001)
- Link commits to tasks with relationship types
- Close tasks automatically via commit messages

### ✅ Permission System
- Role-based access control for Git operations
- Project-level permissions (viewer, member, admin, owner)
- Secure Git operations with user context

## API Endpoints

### Repository Management

#### Initialize Repository
```http
POST /api/v1/git/repositories/{project_id}/initialize
Content-Type: application/json

{
  "initial_branch": "main"
}
```

#### Clone Repository
```http
POST /api/v1/git/repositories/{project_id}/clone
Content-Type: application/json

{
  "remote_url": "https://github.com/user/repo.git",
  "branch": "main"
}
```

#### Get Repository Status
```http
GET /api/v1/git/projects/{project_id}/status
Authorization: Bearer <token>
```

#### Get Repository Info
```http
GET /api/v1/git/repositories/{project_id}/info
Authorization: Bearer <token>
```

### Commit Operations

#### Create Commit
```http
POST /api/v1/git/commits
Content-Type: application/json
Authorization: Bearer <token>

{
  "project_id": "uuid",
  "message": "feat: Add user authentication TAS-001",
  "author_name": "John Doe",
  "author_email": "john@example.com",
  "file_ids": ["uuid1", "uuid2"]
}
```

#### Get Commit Details
```http
GET /api/v1/git/commits/{commit_id}
Authorization: Bearer <token>
```

#### List Commits
```http
GET /api/v1/git/projects/{project_id}/commits?branch=main&limit=50
Authorization: Bearer <token>
```

#### Get Commit with Files
```http
GET /api/v1/git/commits/{commit_id}/files
Authorization: Bearer <token>
```

#### Get Commit Diff
```http
GET /api/v1/git/commits/{commit_id}/diff
Authorization: Bearer <token>
```

### Task Linking

#### Link Commit to Tasks
```http
POST /api/v1/git/commits/{commit_id}/link-tasks
Content-Type: application/json
Authorization: Bearer <token>

{
  "task_ids": ["TAS-001", "TAS-002"],
  "link_type": "closes"
}
```

### Branch Management

#### List Branches
```http
GET /api/v1/git/projects/{project_id}/branches
Authorization: Bearer <token>
```

#### Create Branch
```http
POST /api/v1/git/projects/{project_id}/branches?branch_name=feature/auth
Authorization: Bearer <token>
```

#### Switch Branch
```http
POST /api/v1/git/projects/{project_id}/checkout?branch_name=feature/auth
Authorization: Bearer <token>
```

### Remote Operations

#### Push Commits
```http
POST /api/v1/git/projects/{project_id}/push?branch=main&remote=origin
Authorization: Bearer <token>
```

#### Pull Commits
```http
POST /api/v1/git/projects/{project_id}/pull?branch=main&remote=origin
Authorization: Bearer <token>
```

#### Sync Commits
```http
POST /api/v1/git/projects/{project_id}/sync-commits
Content-Type: application/json
Authorization: Bearer <token>

{
  "branch": "main",
  "since": "2024-01-01T00:00:00Z"
}
```

### Statistics

#### Get Commit Statistics
```http
GET /api/v1/git/projects/{project_id}/stats?branch=main
Authorization: Bearer <token>
```

## Task Integration

### Commit Message Parsing

Ardha automatically parses commit messages to extract task IDs and establish relationships:

#### Supported Task ID Formats

```bash
# Ardha Task Format
feat: Implement user login TAS-001
fix: Resolve authentication issue TAS-002

# GitHub Issue Format
feat: Add user profile #123
fix: Fix profile display #456

# Custom Project Formats
feat: Create dashboard ARD-001
fix: Update charts TASK-001
```

#### Closing Keywords

```bash
# Tasks will be automatically closed
feat: Implement user authentication closes TAS-001
fix: Resolve login issue fixes #123
refactor: Update user model resolves ARD-001
```

#### Link Types

- **mentioned**: Task referenced in commit
- **closes**: Task marked as completed
- **fixes**: Task marked as fixed
- **resolves**: Task marked as resolved

### Automatic Task Status Updates

When commits are linked with closing keywords:
1. Task status is automatically updated to "completed"
2. Task completion date is set to commit date
3. Activity log records the closure
4. Project progress metrics are updated

## Permission System

### Role-Based Access

| Role | Commit Operations | Repository Management | Task Linking |
|------|-------------------|----------------------|--------------|
| Viewer | Read commits | Read status | View links |
| Member | Create commits | Push/Pull | Link tasks |
| Admin | All operations | Sync commits | Close tasks |
| Owner | Full control | Full control | Full control |

### Permission Checks

All Git operations include permission verification:

```python
# Example: Create commit requires member role
if not await project_service.check_permission(
    project_id=project_id,
    user_id=user_id,
    required_role="member"
):
    raise GitCommitPermissionError("Insufficient permissions")
```

## Database Schema

### GitCommit Model

```sql
CREATE TABLE git_commits (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    sha VARCHAR(40) NOT NULL,
    short_sha VARCHAR(7) NOT NULL,
    message TEXT NOT NULL,
    author_name VARCHAR(255) NOT NULL,
    author_email VARCHAR(255) NOT NULL,
    committed_at TIMESTAMP WITH TIME ZONE NOT NULL,
    pushed_at TIMESTAMP WITH TIME ZONE,
    branch VARCHAR(255) NOT NULL,
    is_merge BOOLEAN DEFAULT FALSE,
    parent_shas JSON,
    files_changed INTEGER DEFAULT 0,
    insertions INTEGER DEFAULT 0,
    deletions INTEGER DEFAULT 0,
    linked_task_ids JSON,
    closes_task_ids JSON,
    ardha_user_id UUID REFERENCES users(id) ON DELETE SET NULL,
    synced_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

    CONSTRAINT uq_commit_project_sha UNIQUE (project_id, sha)
);
```

### Association Tables

```sql
-- File-Commit Relationship
CREATE TABLE file_commits (
    file_id UUID REFERENCES files(id) ON DELETE CASCADE,
    commit_id UUID REFERENCES git_commits(id) ON DELETE CASCADE,
    change_type VARCHAR(20) NOT NULL,
    old_path VARCHAR(1024),
    insertions INTEGER DEFAULT 0,
    deletions INTEGER DEFAULT 0,
    PRIMARY KEY (file_id, commit_id)
);

-- Task-Commit Relationship
CREATE TABLE task_commits (
    task_id UUID REFERENCES tasks(id) ON DELETE CASCADE,
    commit_id UUID REFERENCES git_commits(id) ON DELETE CASCADE,
    linked_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    link_type VARCHAR(20) NOT NULL,
    PRIMARY KEY (task_id, commit_id)
);
```

## Usage Examples

### Basic Git Workflow

```python
import httpx

# 1. Get repository status
response = httpx.get(
    "http://localhost:8000/api/v1/git/projects/{project_id}/status",
    headers={"Authorization": "Bearer <token>"}
)
status = response.json()

# 2. Stage files (via Git service)
# Files are automatically staged when creating commits

# 3. Create commit with task linking
response = httpx.post(
    "http://localhost:8000/api/v1/git/commits",
    headers={"Authorization": "Bearer <token>"},
    json={
        "project_id": "project-uuid",
        "message": "feat: Add user authentication TAS-001",
        "author_name": "John Doe",
        "author_email": "john@example.com"
    }
)
commit = response.json()

# 4. Push to remote
response = httpx.post(
    "http://localhost:8000/api/v1/git/projects/{project_id}/push",
    headers={"Authorization": "Bearer <token>"},
    params={"branch": "main"}
)
```

### Task Integration

```python
# Create commit that closes tasks
response = httpx.post(
    "http://localhost:8000/api/v1/git/commits",
    headers={"Authorization": "Bearer <token>"},
    json={
        "project_id": "project-uuid",
        "message": "feat: Implement user authentication closes TAS-001 fixes #123",
        "author_name": "John Doe",
        "author_email": "john@example.com"
    }
)

# Tasks TAS-001 and #123 will be automatically closed
```

### Branch Management

```python
# Create new branch
response = httpx.post(
    "http://localhost:8000/api/v1/git/projects/{project_id}/branches",
    headers={"Authorization": "Bearer <token>"},
    params={"branch_name": "feature/user-auth"}
)

# Switch to branch
response = httpx.post(
    "http://localhost:8000/api/v1/git/projects/{project_id}/checkout",
    headers={"Authorization": "Bearer <token>"},
    params={"branch_name": "feature/user-auth"}
)
```

## Error Handling

### Custom Exceptions

```python
# Git Operation Errors
class GitRepositoryNotFoundError(Exception)
class GitOperationError(Exception)
class GitAuthenticationError(Exception)
class GitBranchError(Exception)
class GitCommitError(Exception)
class GitPushError(Exception)
class GitPullError(Exception)
class GitMergeConflictError(Exception)

# Service Layer Errors
class GitCommitNotFoundError(Exception)
class GitCommitPermissionError(Exception)
class GitCommitValidationError(Exception)
class GitCommitOperationError(Exception)
```

### HTTP Status Codes

| Status Code | Description |
|-------------|-------------|
| 200 | Successful operation |
| 201 | Resource created (commit) |
| 400 | Bad request (validation error) |
| 403 | Permission denied |
| 404 | Resource not found |
| 409 | Conflict (duplicate commit) |
| 500 | Internal server error |

## Configuration

### Environment Variables

```bash
# Git Configuration
GIT_USER_NAME="Ardha Bot"
GIT_USER_EMAIL="bot@ardha.local"
GIT_DEFAULT_BRANCH="main"

# Project Root (for Git operations)
PROJECT_ROOT="/path/to/project"

# Remote Configuration
GIT_DEFAULT_REMOTE="origin"
GIT_PUSH_DEFAULT="current"
```

### Git Service Settings

```python
# GitService initialization
git_service = GitService(
    repo_path=Path(settings.files.project_root)
)

# GitCommitService initialization
git_commit_service = GitCommitService(
    db=db_session,
    project_root=settings.files.project_root
)
```

## Testing

### Unit Tests

```bash
# Test Git service
pytest tests/unit/test_git_service.py -v

# Test Git commit service
pytest tests/unit/test_git_commit_service.py -v

# Test Git commit repository
pytest tests/unit/test_git_commit_repository.py -v
```

### Integration Tests

```bash
# Test Git API endpoints
pytest tests/integration/test_git_api.py -v

# Test Git workflows
pytest tests/integration/test_git_workflows.py -v
```

### Test Fixtures

```python
# Git repository fixture
@pytest.fixture
async def git_repo(tmp_path):
    repo_path = tmp_path / "test_repo"
    repo_path.mkdir()

    git_service = GitService(repo_path)
    git_service.initialize("main")

    return git_service

# Git commit fixture
@pytest.fixture
async def git_commit(db_session, test_project, test_user):
    commit = GitCommit(
        project_id=test_project.id,
        sha="abc123def456",
        short_sha="abc123d",
        message="Test commit TAS-001",
        author_name="Test User",
        author_email="test@example.com",
        branch="main",
        committed_at=datetime.now(timezone.utc),
        ardha_user_id=test_user.id
    )

    db_session.add(commit)
    await db_session.commit()
    await db_session.refresh(commit)

    return commit
```

## Performance Considerations

### Database Optimization

1. **Indexes**: Strategic indexes on common query patterns
2. **Pagination**: Limit results for large commit histories
3. **Caching**: Cache frequently accessed commit data

### Git Operations

1. **Lazy Loading**: Git repository loaded on demand
2. **Batch Operations**: Process multiple commits efficiently
3. **Async Compatibility**: Non-blocking Git operations

### Memory Management

1. **Streaming**: Large diffs streamed rather than loaded entirely
2. **Cleanup**: Proper cleanup of Git objects
3. **Limits**: Reasonable limits on commit history queries

## Security

### Access Control

1. **Project Permissions**: All operations require project membership
2. **Role-Based Restrictions**: Higher-risk operations require elevated roles
3. **User Context**: Git operations tracked with user attribution

### Git Security

1. **Path Validation**: Prevent directory traversal attacks
2. **Command Sanitization**: Safe Git command execution
3. **Authentication**: Secure remote repository access

### Data Protection

1. **Input Validation**: Sanitize all user inputs
2. **SQL Injection Prevention**: Use parameterized queries
3. **Error Information**: Avoid exposing sensitive system information

## Troubleshooting

### Common Issues

#### Repository Not Found
```bash
Error: GitRepositoryNotFoundError
Solution: Ensure Git repository is initialized before operations
```

#### Permission Denied
```bash
Error: GitCommitPermissionError
Solution: Check user has required project role
```

#### Authentication Failed
```bash
Error: GitAuthenticationError
Solution: Verify remote repository credentials
```

#### Merge Conflicts
```bash
Error: GitMergeConflictError
Solution: Resolve conflicts manually or use conflict resolution tools
```

### Debugging

```python
# Enable debug logging
import logging
logging.getLogger("ardha.services.git_service").setLevel(logging.DEBUG)
logging.getLogger("ardha.services.git_commit_service").setLevel(logging.DEBUG)

# Check Git repository status
status = git_service.get_status()
print(f"Repository status: {status}")

# Verify permissions
has_permission = await project_service.check_permission(
    project_id=project_id,
    user_id=user_id,
    required_role="member"
)
print(f"Has permission: {has_permission}")
```

## Best Practices

### Commit Messages

1. **Clear Descriptions**: Use conventional commit format
2. **Task References**: Include relevant task IDs
3. **Closing Keywords**: Use appropriate closing keywords
4. **Context**: Provide sufficient context for changes

### Branch Management

1. **Descriptive Names**: Use meaningful branch names
2. **Short-Lived**: Keep branches focused and short-lived
3. **Regular Sync**: Sync branches regularly with main
4. **Clean Up**: Delete merged branches promptly

### Task Integration

1. **Consistent Format**: Use consistent task ID formats
2. **Automatic Closing**: Leverage automatic task closure
3. **Traceability**: Maintain clear commit-to-task traceability
4. **Status Updates**: Ensure task status reflects reality

## Future Enhancements

### Planned Features

1. **Git Hooks**: Automated Git hooks for task updates
2. **Pull Request Integration**: GitHub/GitLab PR integration
3. **Code Review Workflow**: Integrated code review process
4. **Advanced Analytics**: Commit analytics and insights
5. **Webhook Support**: Git webhook integration
6. **Multi-Repository**: Support for multiple repositories per project

### Performance Improvements

1. **Background Sync**: Asynchronous commit synchronization
2. **Caching Layer**: Redis caching for frequent operations
3. **Database Optimization**: Advanced query optimization
4. **Git LFS**: Large File Storage support

### Integration Expansion

1. **CI/CD Pipeline**: Integrated continuous deployment
2. **Issue Tracking**: Enhanced issue tracking integration
3. **Documentation**: Auto-generated documentation from commits
4. **Release Management**: Automated release management

## API Reference

### Response Schemas

#### GitCommitResponse
```json
{
  "id": "uuid",
  "project_id": "uuid",
  "sha": "abc123def4567890...",
  "short_sha": "abc123d",
  "message": "feat: Add user authentication TAS-001",
  "author_name": "John Doe",
  "author_email": "john@example.com",
  "branch": "main",
  "committed_at": "2024-01-15T10:30:00Z",
  "is_merge": false,
  "files_changed": 5,
  "insertions": 150,
  "deletions": 20,
  "linked_task_ids": ["TAS-001"],
  "closes_task_ids": ["TAS-001"],
  "ardha_user_id": "uuid"
}
```

#### GitStatusResponse
```json
{
  "untracked": ["src/new_file.py"],
  "modified": ["src/existing_file.py"],
  "staged": ["docs/README.md"],
  "deleted": ["old_file.py"],
  "renamed": [["old_name.py", "new_name.py"]],
  "counts": {
    "untracked": 1,
    "modified": 1,
    "staged": 1,
    "deleted": 1,
    "renamed": 1
  },
  "is_clean": false,
  "current_branch": "main"
}
```

#### GitStatsResponse
```json
{
  "total_commits": 150,
  "total_insertions": 15000,
  "total_deletions": 2000,
  "total_files_changed": 300,
  "branches": ["main", "develop", "feature/auth"],
  "top_contributors": [
    {
      "name": "John Doe",
      "email": "john@example.com",
      "commit_count": 75,
      "insertions": 8000,
      "deletions": 1000
    }
  ]
}
```

---

**Version**: 1.0
**Last Updated**: November 18, 2024
**Maintained By**: Ardha Development Team

For more information, visit the [Ardha Documentation](../README.md) or check the [API Reference](api/README.md).
