# Current Context

**Last Updated:** November 8, 2025
**Current Branch:** `feature/initial-setup`
**Active Phase:** Phase 1 - Backend Foundation (Weeks 1-3)
**Next Phase:** Phase 2 - AI Integration & LangGraph (Weeks 4-6)

## Recent Achievements

### Session 4 - Complete Project Management System (November 8, 2025) ✅

**Project & ProjectMember Models:**
- ✅ Created [`backend/src/ardha/models/project.py`](../../../backend/src/ardha/models/project.py:1) (164 lines)
  - 13 fields: name, description, slug, owner_id, visibility, tech_stack, git_repo_url, git_branch, openspec_enabled, openspec_path, is_archived, archived_at, timestamps
  - Relationships: owner (User), members (ProjectMember list)
  - Indexes: name, slug (unique), owner_id, is_archived
  - Cascade delete support

- ✅ Created [`backend/src/ardha/models/project_member.py`](../../../backend/src/ardha/models/project_member.py:1) (107 lines)
  - Association table for many-to-many user-project relationship
  - Role-based permissions: owner, admin, member, viewer
  - Unique constraint on (project_id, user_id)
  - joined_at timestamp tracking

**Project Repository (Data Access Layer):**
- ✅ Created [`backend/src/ardha/repositories/project_repository.py`](../../../backend/src/ardha/repositories/project_repository.py:1) (594 lines)
  - **CRUD Operations (8 methods):**
    - get_by_id(), get_by_slug(), get_by_owner(), get_user_projects()
    - create() with auto-slug generation, update(), archive(), delete()
  - **Member Management (5 methods):**
    - add_member(), remove_member(), update_member_role()
    - get_project_members() with eager user loading, get_member_role()
  - **Smart Features:**
    - _generate_unique_slug() - Auto-appends random suffix if duplicate
    - Eager loading with selectinload() to prevent lazy loading errors
    - Owner protection (cannot remove owner)

**Project Service (Business Logic):**
- ✅ Created [`backend/src/ardha/services/project_service.py`](../../../backend/src/ardha/services/project_service.py:1) (491 lines)
  - **Role Hierarchy System:** owner (4) > admin (3) > member (2) > viewer (1)
  - **Custom Exceptions:** ProjectNotFoundError, InsufficientPermissionsError, ProjectSlugExistsError
  - **11 Business Logic Methods:**
    - create_project(), get_project(), get_project_by_slug(), get_user_projects()
    - update_project(), archive_project(), delete_project()
    - add_member(), remove_member(), update_member_role(), get_project_members()
    - check_permission(), get_member_count()
  - Permission checks enforce hierarchical access control

**Project Schemas:**
- ✅ Created [`backend/src/ardha/schemas/requests/project.py`](../../../backend/src/ardha/schemas/requests/project.py:1) (184 lines)
  - ProjectCreateRequest: Name validation (no whitespace-only), visibility pattern, tech_stack cleaning
  - ProjectUpdateRequest: All fields optional for partial updates
  - ProjectMemberAddRequest, ProjectMemberUpdateRequest: Role validation (admin/member/viewer only)

- ✅ Created [`backend/src/ardha/schemas/responses/project.py`](../../../backend/src/ardha/schemas/responses/project.py:1) (100 lines)
  - ProjectResponse: Complete project data with computed member_count
  - ProjectMemberResponse: Member data with user information
  - ProjectListResponse: Paginated results with total count

**Project API Routes:**
- ✅ Created [`backend/src/ardha/api/v1/routes/projects.py`](../../../backend/src/ardha/api/v1/routes/projects.py:1) (689 lines)
  - **11 REST Endpoints (all tested and working):**
    - POST /api/v1/projects/ - Create (201)
    - GET /api/v1/projects/ - List with pagination (200)
    - GET /api/v1/projects/{id} - Get by ID (200, 403, 404)
    - GET /api/v1/projects/slug/{slug} - Get by slug (200, 403, 404)
    - PATCH /api/v1/projects/{id} - Update (200, 403, 404)
    - POST /api/v1/projects/{id}/archive - Archive (200, 403, 404)
    - DELETE /api/v1/projects/{id} - Delete (200, 403, 404)
    - GET /api/v1/projects/{id}/members - List members (200, 403)
    - POST /api/v1/projects/{id}/members - Add (201, 400, 403, 404)
    - DELETE /api/v1/projects/{id}/members/{user_id} - Remove (200, 400, 403, 404)
    - PATCH /api/v1/projects/{id}/members/{user_id} - Update role (200, 403, 404)

**Database Migration:**
- ✅ Generated migration: `fa93e28de77f_add_project_and_project_member_tables.py`
- ✅ Applied successfully: Current migration is fa93e28de77f (head)
- ✅ Tables created: projects (13 columns), project_members (7 columns)

**Dependencies Added:**
- ✅ Added python-slugify 8.0.4 to pyproject.toml
- ✅ Updated poetry.lock and installed successfully

**Main App Integration:**
- ✅ Updated [`backend/src/ardha/main.py`](../../../backend/src/ardha/main.py:1)
  - Integrated projects router with /api/v1 prefix
  - All 11 project endpoints now accessible
  - Total API endpoints: 13 (6 auth + 6 projects + health/root)

**Updated User Model:**
- ✅ Added relationships to [`backend/src/ardha/models/user.py`](../../../backend/src/ardha/models/user.py:1)
  - owned_projects: Projects user created
  - project_memberships: All project memberships

**Complete Project Management Validation (End-to-End Tests):**
```
✅ Project CRUD: Create, Read (by ID & slug), Update, Archive, List
✅ Slug generation: Auto-generates from name, handles duplicates with random suffix
✅ Member management: Add, remove, update role, list with user data
✅ Permission system: Hierarchical checks (owner > admin > member > viewer)
✅ Data protection: Cannot remove owner, duplicate member prevention
✅ Validation: Empty names rejected, pattern validation on visibility/role
✅ Pagination: Working with total counts and skip/limit
✅ Archive filtering: Excluded from default queries
✅ Eager loading: User data loaded to prevent lazy loading errors
✅ All 11 endpoints tested with real HTTP requests
```

##

### Session 3 - Complete Authentication System (November 8, 2025) ✅

**User Repository (Data Access Layer):**
- ✅ Created [`backend/src/ardha/repositories/user_repository.py`](../../../backend/src/ardha/repositories/user_repository.py:1) (277 lines)
  - All CRUD operations: get_by_id, get_by_email, get_by_username, get_by_oauth_id
  - Create, update, delete (soft delete) operations
  - Paginated list_users with include_inactive filter
  - Comprehensive error handling and logging
  - SQLAlchemy 2.0 async patterns throughout

**Authentication Service (Business Logic):**
- ✅ Created [`backend/src/ardha/services/auth_service.py`](../../../backend/src/ardha/services/auth_service.py:1) (254 lines)
  - User registration with duplicate checking
  - Email/password authentication flow
  - Bcrypt password hashing (cost factor 12)
  - Password verification with constant-time comparison
  - Last login timestamp updates
  - Custom exceptions: UserAlreadyExistsError, InvalidCredentialsError

**JWT Security Utilities:**
- ✅ Created [`backend/src/ardha/core/security.py`](../../../backend/src/ardha/core/security.py:1) (282 lines)
  - create_access_token() - 15 minute expiration
  - create_refresh_token() - 7 day expiration
  - decode_token() and verify_token() functions
  - OAuth2PasswordBearer scheme for token extraction
  - FastAPI dependencies: get_current_user, get_current_active_user, get_current_superuser
  - HTTPException handling for 401/403 errors

**Authentication API Routes:**
- ✅ Created [`backend/src/ardha/api/v1/routes/auth.py`](../../../backend/src/ardha/api/v1/routes/auth.py:1) (406 lines)
  - POST /api/v1/auth/register - User registration (201 Created)
  - POST /api/v1/auth/login - JWT token generation
  - POST /api/v1/auth/refresh - Token refresh
  - POST /api/v1/auth/logout - Stateless logout
  - GET /api/v1/auth/me - Current user profile
  - PATCH /api/v1/auth/me - Update profile
  - OAuth2-compliant endpoints with proper error handling

**Main App Integration:**
- ✅ Updated [`backend/src/ardha/main.py`](../../../backend/src/ardha/main.py:1)
  - Integrated auth router with /api/v1 prefix
  - All authentication endpoints now accessible
  - OpenAPI documentation at /docs and /redoc

**Dependencies Added:**
- ✅ Added bcrypt 4.1.2 to pyproject.toml for password hashing
- ✅ Updated poetry.lock with new dependency
- ✅ All authentication packages working (passlib, python-jose, bcrypt)

**Complete Authentication Stack Validation:**
```
✅ Password hashing produces valid bcrypt hashes ($2b$12$...)
✅ Password verification correctly validates matches/mismatches
✅ JWT tokens created with proper format (3 parts, valid payload)
✅ Token expiration properly enforced
✅ All API endpoints registered and accessible
✅ FastAPI dependencies working correctly
✅ Custom exceptions defined and used
```

### Session 2 - Database Foundation (November 7-8, 2025) ✅

**SQLAlchemy 2.0 Async Database Infrastructure:**
- ✅ Created [`backend/src/ardha/core/database.py`](../../../backend/src/ardha/core/database.py:1) (113 lines)
  - Async SQLAlchemy engine with connection pooling (pool_size=20, max_overflow=0)
  - Async session factory with `expire_on_commit=False`
  - `get_db()` FastAPI dependency for route injection
  - Lifecycle management: `init_db()`, `close_db()`
  
- ✅ Created [`backend/src/ardha/models/base.py`](../../../backend/src/ardha/models/base.py:1) (89 lines)
  - `Base`: DeclarativeBase for all models
  - `BaseModel`: Mixin with id (UUID), created_at, updated_at
  - `SoftDeleteMixin`: is_deleted, deleted_at fields
  - All using SQLAlchemy 2.0 `Mapped[type]` syntax

**User Model Implementation:**
- ✅ Created [`backend/src/ardha/models/user.py`](../../../backend/src/ardha/models/user.py:1) (125 lines)
  - 13 columns: email, username, full_name, password_hash, is_active, is_superuser, avatar_url, github_id, google_id, last_login_at, id, created_at, updated_at
  - Unique indexes on email, username, github_id, google_id
  - OAuth support (nullable password_hash)
  - Inherits from Base and BaseModel

**Authentication Schemas:**
- ✅ Created [`backend/src/ardha/schemas/requests/auth.py`](../../../backend/src/ardha/schemas/requests/auth.py:1) (212 lines)
  - `UserRegisterRequest`: Email, username (3-50 chars, alphanumeric), password (8+ chars, mixed case + numbers)
  - `UserLoginRequest`: Email and password
  - `PasswordResetRequest`, `PasswordResetConfirm`
  - Comprehensive Pydantic validators

- ✅ Created [`backend/src/ardha/schemas/responses/user.py`](../../../backend/src/ardha/schemas/responses/user.py:1) (56 lines)
  - `UserResponse`: Safe user data (no password_hash)
  - `UserListResponse`: Paginated user lists
  - `ConfigDict(from_attributes=True)` for ORM compatibility

**Alembic Migration System:**
- ✅ Created [`backend/alembic/env.py`](../../../backend/alembic/env.py:1) (109 lines) - Async Alembic configuration
- ✅ Created [`backend/alembic.ini`](../../../backend/alembic.ini:1) (126 lines) - Alembic settings
- ✅ Created [`backend/alembic/script.py.mako`](../../../backend/alembic/script.py.mako:1) (26 lines) - Migration template
- ✅ Generated migration: `b4e31b4c9224_initial_migration_users_table.py`
- ✅ Applied migration: Users table created in PostgreSQL
- ✅ Added `email-validator` package dependency (v2.3.0)

**Database Validation:**
```
Current Migration: fa93e28de77f (head)
Users table: ✅ Created with 13 columns
Projects table: ✅ Created with 13 columns
Project Members table: ✅ Created with 7 columns
Indexes: ✅ All unique and foreign key indexes created
```

### Session 1 - Infrastructure Setup (November 1, 2025) ✅

**Infrastructure Setup:**
- Created monorepo at `/home/veda/ardha-projects/Ardha`
- Configured Git with proper branching strategy (main, dev, feature/initial-setup)
- Set up shared dependency caches to save 900MB disk space
- Published to GitHub: https://github.com/ardhaecosystem/Ardha

**Backend Setup:**
- Initialized Poetry project with Python 3.12.3
- Locked all dependencies in `backend/poetry.lock` (444KB)
- Configured shared cache at `.poetry-cache/` (206MB)
- Installed packages: FastAPI, LangChain, LangGraph, SQLAlchemy, Qdrant, Redis, etc.
- Created virtual environment in `backend/.venv/` (80MB, not committed)

**Frontend Setup:**
- Initialized Next.js 15.0.2 project with React 19 RC
- Locked all dependencies in `frontend/pnpm-lock.yaml` (188KB)
- Configured shared pnpm store at `.pnpm-store/` (206MB)
- Installed packages: Next.js, React, CodeMirror 6, xterm.js, Radix UI, etc.
- Fixed xterm version to 5.3.0 (was incorrectly 5.5.0)

**OpenSpec Integration:**
- Initialized OpenSpec in dev branch
- Created `.kilocode/workflows/` with 3 workflow files
- Created `openspec/AGENTS.md` (15KB instructions)
- Created `openspec/project.md` with full Ardha PRD (123KB)
- Created root `AGENTS.md` pointer file

## Current Work Focus

### Phase 1 - Backend Foundation (In Progress)
**Status**: Week 1 COMPLETE! Authentication + Project Management ✅

**Completed:**
- ✅ SQLAlchemy 2.0 async engine and session factory
- ✅ Base models with mixins (BaseModel, SoftDeleteMixin)
- ✅ User model with OAuth support + project relationships
- ✅ Project & ProjectMember models (roles, permissions)
- ✅ Authentication request/response schemas
- ✅ Project request/response schemas
- ✅ Alembic migration system configured
- ✅ 2 migrations applied (users, projects, project_members tables)
- ✅ User Repository (6 methods)
- ✅ Project Repository (13 methods - CRUD + member management)
- ✅ Authentication Service (registration, login, JWT)
- ✅ Project Service (11 methods - CRUD, members, permissions)
- ✅ JWT Security utilities (token generation/validation)
- ✅ Authentication API routes (6 endpoints)
- ✅ Project API routes (11 endpoints)
- ✅ Password hashing with bcrypt (cost factor 12)
- ✅ FastAPI integration (auth + projects routers)
- ✅ End-to-end testing of all 17 endpoints

**Next Immediate Steps (Week 2):**
1. Write comprehensive tests for authentication and project systems
   - Unit tests for UserRepository and ProjectRepository
   - Unit tests for AuthService and ProjectService
   - Integration tests for all API endpoints
   - Test fixtures in tests/conftest.py
2. Implement GitHub OAuth flow
3. Implement Google OAuth flow
4. Add email verification system
5. Implement password reset functionality
6. Begin Task model design

## Recent Decisions & Patterns

### Database Architecture
- Using SQLAlchemy 2.0 async exclusively (no sync code)
- UUID primary keys for all models (default uuid4)
- Timezone-aware timestamps (created_at, updated_at)
- Soft delete support via SoftDeleteMixin (optional per model)
- Connection pooling: 20 connections max, no overflow (2GB PostgreSQL limit)
- **Session Management:** Services use `flush()` not `commit()` - FastAPI manages session lifecycle
- **Eager Loading:** Use `selectinload()` for relationships to prevent lazy loading errors in async context
- **Relationship Pattern:** Load user data separately in API responses to avoid lazy loading issues

### Schema Validation
- Pydantic v2 with `ConfigDict(from_attributes=True)` for ORM compatibility
- Strict validation on all user input (email format, password strength, username format)
- Never expose sensitive data in response schemas
- Request and response schemas are separate

### Alembic Workflow
- Async-compatible configuration using `async_engine_from_config`
- Auto-discovery of models via `db/base.py` imports
- Database URL from settings (environment variable)
- Must set `DATABASE__URL` environment variable when running Alembic commands

### Git Workflow
- Using three-branch model: main → dev → feature/*
- Feature branches for all work (currently on `feature/initial-setup`)
- Conventional commit messages enforced
- All branches share same directory (no separate directories per branch)

### Dependency Management
- Backend: Poetry with shared cache at `.poetry-cache/`
- Frontend: pnpm with shared store at `.pnpm-store/`
- All dependencies locked to exact versions for reproducibility
- Caches excluded from Git to save space (900MB saved)

### OpenSpec Workflow
- Start in dev branch, feature branches inherit setup
- Create proposals in `openspec/changes/` directory
- Review and approve before implementation
- Archive completed changes to `openspec/changes/archive/`

## Project Structure (Current State)

```
Ardha/
├── .git/                      # Git repository
├── .gitignore                 # Comprehensive exclusions
├── .pnpm-store/              # Shared pnpm cache (NOT in Git)
├── .poetry-cache/            # Shared poetry cache (NOT in Git)
├── AGENTS.md                 # OpenSpec integration pointer
├── README.md                 # Project documentation
├── LICENSE                   # MIT License
├── docker-compose.yml        # Container orchestration
│
├── .kilocode/
│   ├── rules/
│   │   └── memory-bank/      # Memory bank files
│   │       ├── brief.md      # ✅ Created
│   │       ├── product.md    # ✅ Created
│   │       ├── context.md    # 🔄 This file
│   │       ├── architecture.md # ✅ Created
│   │       └── tech.md       # ✅ Created
│   └── workflows/            # OpenSpec workflows
│
├── backend/
│   ├── .venv/                # Virtual environment (NOT in Git)
│   ├── poetry.lock           # ✅ Locked dependencies (+ email-validator)
│   ├── pyproject.toml        # ✅ All PRD packages
│   ├── alembic.ini          # ✅ Alembic configuration
│   ├── alembic/
│   │   ├── env.py           # ✅ Async Alembic environment
│   │   ├── script.py.mako   # ✅ Migration template
│   │   └── versions/
│   │       └── b4e31b4c9224_initial_migration_users_table.py
│   └── src/ardha/
│       ├── core/
│       │   ├── config.py    # ✅ Pydantic settings
│       │   └── database.py  # ✅ Async engine & sessions
│       ├── db/
│       │   └── base.py      # ✅ Model imports for Alembic
│       ├── models/
│       │   ├── base.py      # ✅ Base, BaseModel, SoftDeleteMixin
│       │   └── user.py      # ✅ User model (13 columns)
│       └── schemas/
│           ├── requests/
│           │   └── auth.py  # ✅ Auth request schemas
│           └── responses/
│               └── user.py  # ✅ User response schemas
│
├── frontend/
│   ├── node_modules/         # Symlinks to .pnpm-store (NOT in Git)
│   ├── package.json          # ✅ All PRD packages
│   └── src/                  # Empty (ready for Phase 5)
│
└── openspec/
    ├── AGENTS.md             # Full OpenSpec instructions
    └── project.md            # Complete Ardha PRD (123KB)
```

## Key Files & Locations

### Database Layer (Complete)
- [`backend/src/ardha/core/database.py`](../../../backend/src/ardha/core/database.py:1) - Engine, sessions, dependencies
- [`backend/src/ardha/models/base.py`](../../../backend/src/ardha/models/base.py:1) - Base classes and mixins
- [`backend/src/ardha/models/user.py`](../../../backend/src/ardha/models/user.py:1) - User model with project relationships
- [`backend/src/ardha/models/project.py`](../../../backend/src/ardha/models/project.py:1) - Project model
- [`backend/src/ardha/models/project_member.py`](../../../backend/src/ardha/models/project_member.py:1) - Project membership association
- [`backend/src/ardha/db/base.py`](../../../backend/src/ardha/db/base.py:1) - Model imports for Alembic
- [`backend/alembic/env.py`](../../../backend/alembic/env.py:1) - Alembic async configuration
- [`backend/alembic/versions/b4e31b4c9224_initial_migration_users_table.py`](../../../backend/alembic/versions/b4e31b4c9224_initial_migration_users_table.py:1) - Users table migration
- [`backend/alembic/versions/fa93e28de77f_add_project_and_project_member_tables.py`](../../../backend/alembic/versions/fa93e28de77f_add_project_and_project_member_tables.py:1) - Projects tables migration

### Schema Layer (Complete)
- [`backend/src/ardha/schemas/requests/auth.py`](../../../backend/src/ardha/schemas/requests/auth.py:1) - Auth request validation
- [`backend/src/ardha/schemas/requests/project.py`](../../../backend/src/ardha/schemas/requests/project.py:1) - Project request validation
- [`backend/src/ardha/schemas/responses/user.py`](../../../backend/src/ardha/schemas/responses/user.py:1) - User response formatting
- [`backend/src/ardha/schemas/responses/project.py`](../../../backend/src/ardha/schemas/responses/project.py:1) - Project response formatting

### Authentication System (Complete)
- [`backend/src/ardha/repositories/user_repository.py`](../../../backend/src/ardha/repositories/user_repository.py:1) - User data access
- [`backend/src/ardha/services/auth_service.py`](../../../backend/src/ardha/services/auth_service.py:1) - Authentication business logic
- [`backend/src/ardha/core/security.py`](../../../backend/src/ardha/core/security.py:1) - JWT utilities and dependencies
- [`backend/src/ardha/api/v1/routes/auth.py`](../../../backend/src/ardha/api/v1/routes/auth.py:1) - Authentication API endpoints

### Project Management System (Complete)
- [`backend/src/ardha/repositories/project_repository.py`](../../../backend/src/ardha/repositories/project_repository.py:1) - Project data access
- [`backend/src/ardha/services/project_service.py`](../../../backend/src/ardha/services/project_service.py:1) - Project business logic
- [`backend/src/ardha/api/v1/routes/projects.py`](../../../backend/src/ardha/api/v1/routes/projects.py:1) - Project API endpoints

### Main Application
- [`backend/src/ardha/main.py`](../../../backend/src/ardha/main.py:1) - FastAPI app with auth + projects routers

### Configuration Files
- `backend/pyproject.toml` - Python dependencies and tool config
- `frontend/package.json` - Node dependencies and scripts
- `.gitignore` - Comprehensive exclusion list
- `docker-compose.yml` - Container definitions
- `backend/alembic.ini` - Alembic configuration

### Directories Ready for Next Implementation
- `backend/tests/unit/` - Unit tests (next priority)
- `backend/tests/integration/` - Integration tests (next priority)
- `backend/src/ardha/api/v1/routes/` - Additional API routes (projects, tasks)
- `frontend/src/` - Frontend code (Phase 5)

## Known Issues & Limitations

### Fixed Issues ✅
- xterm version corrected from 5.5.0 to 5.3.0 (5.5.0 doesn't exist)
- Added missing CodeMirror language extensions (HTML, CSS, JSON, Markdown, YAML)
- Added email-validator package for Pydantic EmailStr support
- Configured Alembic for async SQLAlchemy operations

### Current Status
- ✅ Database foundation complete (SQLAlchemy, User + Project + ProjectMember models, migrations)
- ✅ Complete authentication system (repository, service, security, routes)
- ✅ Complete project management system (repository, service, routes)
- ✅ Docker containers running (postgres, redis, qdrant, backend, frontend)
- ✅ 3 database tables created: users, projects, project_members
- ✅ JWT authentication working (access + refresh tokens)
- ✅ 17 API endpoints functional and tested (6 auth + 11 projects)
- ✅ Role-based permissions enforced
- ⏳ No tests written yet (next priority)
- ⏳ No CI/CD pipeline configured
- ⏳ No frontend implementation yet

## Next Steps (Detailed)

### Immediate (Next Session)
**Week 1 Completion: Authentication System**
1. Implement User Repository (`repositories/user_repository.py`)
   - `get_by_email()`, `get_by_username()`, `get_by_id()`
   - `create()`, `update()`, `delete()`
   - OAuth lookup methods
   
2. Implement Authentication Service (`services/auth_service.py`)
   - User registration with password hashing
   - Email/password authentication
   - JWT token generation and validation
   - Token refresh logic
   - Password reset functionality
   
3. Implement Security Utilities (`core/security.py`)
   - Password hashing with bcrypt (cost 12)
   - JWT token encoding/decoding
   - OAuth token validation
   
4. Create Auth API Routes (`api/v1/routes/auth.py`)
   - `POST /api/v1/auth/register`
   - `POST /api/v1/auth/login`
   - `POST /api/v1/auth/refresh`
   - `POST /api/v1/auth/logout`
   - `POST /api/v1/auth/password-reset`
   
5. ✅ Write comprehensive tests (moved to Week 2)

### Phase 1 - Backend Foundation (Weeks 1-3)
**Week 1: Infrastructure & Auth & Projects** - COMPLETE ✅
- ✅ Database foundation (SQLAlchemy, migrations)
- ✅ User model and schemas + project relationships
- ✅ Project & ProjectMember models with associations
- ✅ Authentication system (complete)
  - ✅ User Repository (data access)
  - ✅ Authentication Service (business logic)
  - ✅ JWT Security (token management)
  - ✅ API Routes (6 endpoints)
  - ✅ FastAPI integration
- ✅ Project management system (complete)
  - ✅ Project Repository (CRUD + member management)
  - ✅ Project Service (business logic + permissions)
  - ✅ API Routes (11 endpoints)
  - ✅ End-to-end testing validated
- ⏳ Comprehensive tests (moved to Week 2)
- ⏳ Logging improvements (ongoing)

**Week 2: OAuth & User Management**
- Implement GitHub OAuth flow
- Implement Google OAuth flow
- User profile endpoints (GET, PUT)
- Avatar upload functionality
- Email verification system

**Week 3: Core Project & Task Models**
- Design project and task database schema
- Create SQLAlchemy models (Project, Task, ProjectMember, TaskDependency)
- Generate Alembic migrations
- Implement project CRUD endpoints
- Implement task CRUD endpoints

## Important Environment Configuration

### Alembic Commands Require Database URL

When running Alembic commands, you must set the `DATABASE__URL` environment variable:

```bash
# Example Alembic commands
DATABASE__URL="postgresql+asyncpg://ardha_user:ardha_password@localhost:5432/ardha_dev" poetry run alembic upgrade head

# Or create .env file in backend/ directory
echo 'DATABASE__URL=postgresql+asyncpg://ardha_user:ardha_password@localhost:5432/ardha_dev' > backend/.env
```

The double underscore (`__`) is required because Pydantic Settings uses `env_nested_delimiter="__"` to map nested config like `database.url`.

## Memory Bank Status

This memory bank is now actively maintained across all development sessions. Updates occur:
- After completing major milestones ✅ (just completed database foundation)
- When discovering important patterns
- When making architectural decisions
- When the user explicitly requests "update memory bank"

The memory bank serves as the AI's context across sessions, ensuring continuity and preventing context drift over the 20-week development timeline.

## Docker Container Status

All containers are running and healthy:
- `ardha-postgres` - PostgreSQL 15.5-alpine (5 hours uptime)
- `ardha-redis` - Redis 7.2-alpine (5 hours uptime)
- `ardha-qdrant` - Qdrant v1.7.4 (4 hours uptime)
- `ardha-backend` - FastAPI application (3 minutes uptime, healthy)
- `ardha-frontend` - Next.js application (3 hours uptime, healthy)

Port mappings:
- Backend API: http://localhost:8000
- Frontend: http://localhost:3000
- PostgreSQL: localhost:5432
- Redis: localhost:6379
- Qdrant: http://localhost:6333