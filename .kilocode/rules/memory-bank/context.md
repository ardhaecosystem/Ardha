# Current Context

**Last Updated:** November 8, 2025
**Current Branch:** `feature/initial-setup`
**Active Phase:** Phase 1 - Backend Foundation (Weeks 1-3)
**Next Phase:** Phase 2 - AI Integration & LangGraph (Weeks 4-6)

## Recent Achievements

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
Current Migration: b4e31b4c9224 (head)
Users table: ✅ Created with 13 columns
Indexes: ✅ email, username, github_id, google_id (all unique)
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
**Status**: Week 1 Authentication System COMPLETE! ✅

**Completed:**
- ✅ SQLAlchemy 2.0 async engine and session factory
- ✅ Base models with mixins (BaseModel, SoftDeleteMixin)
- ✅ User model with OAuth support
- ✅ Authentication request/response schemas
- ✅ Alembic migration system configured
- ✅ Initial migration applied (users table created)
- ✅ User Repository (complete data access layer)
- ✅ Authentication Service (complete business logic)
- ✅ JWT Security utilities (token generation/validation)
- ✅ Authentication API routes (all 6 endpoints)
- ✅ Password hashing with bcrypt (cost factor 12)
- ✅ FastAPI integration (auth router registered)

**Next Immediate Steps (Week 2):**
1. Write comprehensive tests for authentication system
   - Unit tests for UserRepository methods
   - Unit tests for AuthService logic
   - Integration tests for API endpoints
   - Test fixtures in tests/conftest.py
2. Implement GitHub OAuth flow
3. Implement Google OAuth flow
4. Add email verification system
5. Implement password reset functionality
6. Add logging and error handling improvements

## Recent Decisions & Patterns

### Database Architecture
- Using SQLAlchemy 2.0 async exclusively (no sync code)
- UUID primary keys for all models (default uuid4)
- Timezone-aware timestamps (created_at, updated_at)
- Soft delete support via SoftDeleteMixin (optional per model)
- Connection pooling: 20 connections max, no overflow (2GB PostgreSQL limit)

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
- [`backend/src/ardha/models/user.py`](../../../backend/src/ardha/models/user.py:1) - User model
- [`backend/src/ardha/db/base.py`](../../../backend/src/ardha/db/base.py:1) - Model imports for Alembic
- [`backend/alembic/env.py`](../../../backend/alembic/env.py:1) - Alembic async configuration
- [`backend/alembic/versions/b4e31b4c9224_initial_migration_users_table.py`](../../../backend/alembic/versions/b4e31b4c9224_initial_migration_users_table.py:1) - Users table migration

### Schema Layer (Complete)
- [`backend/src/ardha/schemas/requests/auth.py`](../../../backend/src/ardha/schemas/requests/auth.py:1) - Auth request validation
- [`backend/src/ardha/schemas/responses/user.py`](../../../backend/src/ardha/schemas/responses/user.py:1) - User response formatting

### Authentication System (Complete)
- [`backend/src/ardha/repositories/user_repository.py`](../../../backend/src/ardha/repositories/user_repository.py:1) - User data access
- [`backend/src/ardha/services/auth_service.py`](../../../backend/src/ardha/services/auth_service.py:1) - Authentication business logic
- [`backend/src/ardha/core/security.py`](../../../backend/src/ardha/core/security.py:1) - JWT utilities and dependencies
- [`backend/src/ardha/api/v1/routes/auth.py`](../../../backend/src/ardha/api/v1/routes/auth.py:1) - Authentication API endpoints
- [`backend/src/ardha/main.py`](../../../backend/src/ardha/main.py:1) - FastAPI app with auth integration

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
- ✅ Database foundation complete (SQLAlchemy, User model, migrations)
- ✅ Complete authentication system (repository, service, security, routes)
- ✅ Docker containers running (postgres, redis, qdrant, backend, frontend)
- ✅ Users table created and validated in PostgreSQL
- ✅ JWT authentication working (access + refresh tokens)
- ✅ 6 authentication endpoints functional and documented
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
**Week 1: Infrastructure & Auth** - COMPLETE ✅
- ✅ Database foundation (SQLAlchemy, migrations)
- ✅ User model and schemas
- ✅ Authentication system (complete)
  - ✅ User Repository (data access)
  - ✅ Authentication Service (business logic)
  - ✅ JWT Security (token management)
  - ✅ API Routes (6 endpoints)
  - ✅ FastAPI integration
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