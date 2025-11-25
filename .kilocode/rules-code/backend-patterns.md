# Ardha Backend Code Patterns (Python/FastAPI)

> **Purpose**: Establish consistent backend patterns following Clean Architecture principles.
>
> **Why This Matters**: Consistent patterns make code predictable, testable, and maintainable. This file serves as both AI guidance and developer documentation.
>
> **Open-Source Note**: These patterns demonstrate professional FastAPI development. Adapt for your Python projects!

---

## 🎯 Backend Technology Stack

**Core Framework:**
- **Python**: 3.12.3 (strict type hints required)
- **FastAPI**: 0.115.4 (async/await throughout)
- **Pydantic**: 2.x (request/response validation)
- **SQLAlchemy**: 2.0.35 (async ORM)
- **Alembic**: 1.13.3 (database migrations)

**Databases:**
- **PostgreSQL**: 15 (primary database, 2GB RAM limit)
- **Qdrant**: 1.7.4 (vector database, 2.5GB RAM limit)
- **Redis**: 7.2 (cache, 512MB RAM limit)

**AI & ML:**
- **LangChain**: 0.3.7 (AI orchestration)
- **LangGraph**: 0.2.45 (deterministic workflows)
- **OpenAI SDK**: (OpenRouter compatible)

**Testing:**
- **pytest**: Unit and integration tests
- **pytest-asyncio**: Async test support
- **httpx**: API testing client
- **Coverage Target**: 80%+ for business logic, 100% for API routes

---

## 📁 Backend Directory Structure

```
backend/src/ardha/
├── api/
│   ├── routes/           # FastAPI route definitions
│   │   ├── __init__.py
│   │   ├── auth.py       # Authentication endpoints
│   │   ├── users.py      # User management
│   │   ├── projects.py   # Project CRUD
│   │   └── tasks.py      # Task management
│   └── dependencies/     # Shared dependencies
│       ├── __init__.py
│       ├── auth.py       # JWT authentication dependency
│       └── database.py   # Database session dependency
│
├── core/
│   ├── config/
│   │   ├── __init__.py
│   │   └── settings.py   # Pydantic Settings
│   ├── security/
│   │   ├── __init__.py
│   │   ├── jwt.py        # JWT token handling
│   │   └── password.py   # Password hashing (bcrypt)
│   └── exceptions/
│       ├── __init__.py
│       └── handlers.py   # Custom exception handlers
│
├── db/
│   ├── __init__.py
│   ├── base.py           # SQLAlchemy declarative base
│   └── session.py        # Database session factory
│
├── models/               # SQLAlchemy ORM models
│   ├── __init__.py
│   ├── user.py
│   ├── project.py
│   ├── task.py
│   └── chat.py
│
├── schemas/
│   ├── requests/         # Pydantic request models
│   │   ├── __init__.py
│   │   ├── auth.py
│   │   ├── user.py
│   │   ├── project.py
│   │   └── task.py
│   └── responses/        # Pydantic response models
│       ├── __init__.py
│       ├── auth.py
│       ├── user.py
│       ├── project.py
│       └── task.py
│
├── services/             # Business logic layer
│   ├── __init__.py
│   ├── auth_service.py
│   ├── user_service.py
│   ├── project_service.py
│   └── task_service.py
│
├── repositories/         # Data access layer
│   ├── __init__.py
│   ├── user_repository.py
│   ├── project_repository.py
│   └── task_repository.py
│
├── workflows/            # LangGraph workflow definitions
│   ├── __init__.py
│   └── (Phase 2)
│
├── migrations/           # Alembic migration files
│   ├── env.py
│   ├── script.py.mako
│   └── versions/
│
├── __init__.py
└── main.py               # FastAPI app entry point
```

---

## 🏗️ Architecture Layers (Clean Architecture)

### **Layer 1: API Routes (Presentation)**

**Responsibility**: HTTP request/response handling, route definition, input validation

**Pattern:**
```python
# backend/src/ardha/api/routes/users.py
from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_db, get_current_user
from app.services.user_service import UserService
from app.schemas.requests.user import UserCreate, UserUpdate
from app.schemas.responses.user import UserResponse
from app.models.user import User

router = APIRouter(prefix="/users", tags=["users"])


@router.post(
    "/",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new user",
    description="Register a new user account with email and password.",
)
async def create_user(
    user_data: UserCreate,
    db: AsyncSession = Depends(get_db),
) -> UserResponse:
    """
    Create a new user account.

    - **email**: Valid email address (unique)
    - **password**: Minimum 8 characters
    - **full_name**: User's display name

    Returns the created user (excluding password).
    """
    service = UserService(db)
    user = await service.create_user(user_data)
    return UserResponse.model_validate(user)


@router.get(
    "/me",
    response_model=UserResponse,
    summary="Get current user",
)
async def get_current_user_profile(
    current_user: User = Depends(get_current_user),
) -> UserResponse:
    """Get the currently authenticated user's profile."""
    return UserResponse.model_validate(current_user)
```

**Key Rules:**
- ✅ Routes only handle HTTP concerns (request/response)
- ✅ Use dependency injection for database sessions
- ✅ All business logic in service layer
- ✅ Comprehensive OpenAPI documentation (summary, description, docstrings)
- ✅ Pydantic models for validation
- ❌ NO database queries in route handlers
- ❌ NO business logic in routes

---

### **Layer 2: Services (Business Logic)**

**Responsibility**: Business rules, orchestration, validation

**Pattern:**
```python
# backend/src/ardha/services/user_service.py
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException, status

from app.repositories.user_repository import UserRepository
from app.schemas.requests.user import UserCreate, UserUpdate
from app.models.user import User
from app.core.security.password import get_password_hash, verify_password


class UserService:
    """Business logic for user management."""

    def __init__(self, db: AsyncSession):
        self.repository = UserRepository(db)

    async def create_user(self, user_data: UserCreate) -> User:
        """
        Create a new user with hashed password.

        Raises:
            HTTPException: If email already exists
        """
        # Check if email already exists
        existing_user = await self.repository.get_by_email(user_data.email)
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered"
            )

        # Hash password
        hashed_password = get_password_hash(user_data.password)

        # Create user
        user = await self.repository.create(
            email=user_data.email,
            full_name=user_data.full_name,
            hashed_password=hashed_password,
        )

        return user

    async def authenticate(self, email: str, password: str) -> User | None:
        """
        Authenticate user with email and password.

        Returns:
            User if authenticated, None otherwise
        """
        user = await self.repository.get_by_email(email)
        if not user:
            return None

        if not verify_password(password, user.hashed_password):
            return None

        return user
```

**Key Rules:**
- ✅ Services contain ALL business logic
- ✅ Use repositories for database access
- ✅ Raise HTTPException for business rule violations
- ✅ Type hints on all methods
- ✅ Comprehensive docstrings
- ❌ NO SQLAlchemy queries in services (use repositories)
- ❌ NO direct database session access

---

### **Layer 3: Repositories (Data Access)**

**Responsibility**: Database queries, data persistence

**Pattern:**
```python
# backend/src/ardha/repositories/user_repository.py
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional

from app.models.user import User


class UserRepository:
    """Data access layer for User model."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(
        self,
        email: str,
        full_name: str,
        hashed_password: str,
    ) -> User:
        """Create a new user."""
        user = User(
            email=email,
            full_name=full_name,
            hashed_password=hashed_password,
        )
        self.db.add(user)
        await self.db.commit()
        await self.db.refresh(user)
        return user

    async def get_by_email(self, email: str) -> Optional[User]:
        """Get user by email address."""
        stmt = select(User).where(User.email == email)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_id(self, user_id: int) -> Optional[User]:
        """Get user by ID."""
        stmt = select(User).where(User.id == user_id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def update(self, user: User, **kwargs) -> User:
        """Update user fields."""
        for key, value in kwargs.items():
            if hasattr(user, key):
                setattr(user, key, value)

        await self.db.commit()
        await self.db.refresh(user)
        return user
```

**Key Rules:**
- ✅ Repositories handle ALL database operations
- ✅ Use async SQLAlchemy queries
- ✅ Return Optional[Model] for single results
- ✅ Use explicit select() statements (not raw SQL)
- ✅ Always commit and refresh after mutations
- ❌ NO business logic in repositories
- ❌ NO raising HTTPException (return None instead)

---

## 🔍 File Selection Logic for Backend Tasks

### **When Working on a Backend Feature:**

**1. Identify the Layer:**
- Is it a **route** (HTTP handling)?
- Is it **business logic** (validation, orchestration)?
- Is it a **database operation** (queries)?

**2. Load Only Relevant Files:**

**For New API Endpoint:**
```
✅ Load similar existing endpoint (pattern reference)
✅ Load related service (business logic)
✅ Load related repository (if new queries needed)
✅ Load related models (database schema)
✅ Load request/response schemas

Example: Creating "password reset" endpoint
- api/routes/auth.py (existing auth routes)
- services/auth_service.py
- repositories/user_repository.py
- models/user.py
- schemas/requests/auth.py (PasswordResetRequest)
- schemas/responses/auth.py (PasswordResetResponse)
```

**For New Business Logic:**
```
✅ Load service file being modified
✅ Load repository being used
✅ Load related models

Example: Adding "send welcome email" logic
- services/user_service.py
- repositories/user_repository.py
- models/user.py
```

**For Database Query:**
```
✅ Load repository file
✅ Load model definition

Example: Adding "find users by role" query
- repositories/user_repository.py
- models/user.py
```

---

## 📐 Code Standards

### **Type Hints (Required)**

**All functions MUST have type hints:**
```python
# ✅ CORRECT
async def create_user(
    user_data: UserCreate,
    db: AsyncSession,
) -> User:
    ...

# ❌ INCORRECT (missing type hints)
async def create_user(user_data, db):
    ...
```

---

### **Async/Await (Required)**

**All I/O operations MUST use async/await:**
```python
# ✅ CORRECT
async def get_user(db: AsyncSession, user_id: int) -> Optional[User]:
    stmt = select(User).where(User.id == user_id)
    result = await db.execute(stmt)
    return result.scalar_one_or_none()

# ❌ INCORRECT (blocking sync code)
def get_user(db: Session, user_id: int) -> Optional[User]:
    return db.query(User).filter(User.id == user_id).first()
```

---

### **Error Handling**

**Use HTTPException for API errors:**
```python
# ✅ CORRECT
from fastapi import HTTPException, status

async def get_project(self, project_id: int) -> Project:
    project = await self.repository.get_by_id(project_id)
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project {project_id} not found"
        )
    return project

# ❌ INCORRECT (generic exception)
async def get_project(self, project_id: int) -> Project:
    project = await self.repository.get_by_id(project_id)
    if not project:
        raise ValueError("Project not found")
    return project
```

---

### **Pydantic Models**

**Request and response models are separate:**
```python
# schemas/requests/user.py
from pydantic import BaseModel, EmailStr, Field

class UserCreate(BaseModel):
    """Request model for user creation."""
    email: EmailStr
    password: str = Field(..., min_length=8)
    full_name: str = Field(..., min_length=1)


# schemas/responses/user.py
from pydantic import BaseModel, EmailStr
from datetime import datetime

class UserResponse(BaseModel):
    """Response model for user data."""
    id: int
    email: EmailStr
    full_name: str
    created_at: datetime

    model_config = {"from_attributes": True}  # Enable ORM mode
```

**Key Rules:**
- ✅ Request models: Validation rules (min_length, etc.)
- ✅ Response models: No sensitive data (passwords)
- ✅ Use `model_config = {"from_attributes": True}` for ORM models
- ❌ NEVER expose `hashed_password` in responses

---

## 🧪 Testing Standards

### **Test File Organization**

```
backend/tests/
├── unit/
│   ├── test_services/
│   │   └── test_user_service.py
│   └── test_repositories/
│       └── test_user_repository.py
│
├── integration/
│   └── test_api/
│       └── test_auth_routes.py
│
└── conftest.py  # Shared fixtures
```

### **Test Patterns**

**Service Tests (Unit):**
```python
# tests/unit/test_services/test_user_service.py
import pytest
from unittest.mock import AsyncMock

from app.services.user_service import UserService
from app.schemas.requests.user import UserCreate


@pytest.mark.asyncio
async def test_create_user_success(mock_db_session):
    """Test successful user creation."""
    # Arrange
    service = UserService(mock_db_session)
    user_data = UserCreate(
        email="test@example.com",
        password="SecurePass123!",
        full_name="Test User"
    )

    # Act
    user = await service.create_user(user_data)

    # Assert
    assert user.email == "test@example.com"
    assert user.full_name == "Test User"
    assert user.hashed_password != "SecurePass123!"  # Password hashed
```

**API Tests (Integration):**
```python
# tests/integration/test_api/test_auth_routes.py
import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_register_user(client: AsyncClient):
    """Test user registration endpoint."""
    # Arrange
    user_data = {
        "email": "newuser@example.com",
        "password": "SecurePass123!",
        "full_name": "New User"
    }

    # Act
    response = await client.post("/api/v1/users/", json=user_data)

    # Assert
    assert response.status_code == 201
    data = response.json()
    assert data["email"] == "newuser@example.com"
    assert "password" not in data  # Password not in response
    assert "hashed_password" not in data
```

---

## ⚡ Performance Considerations

### **Database Query Optimization**

**Use eager loading to prevent N+1 queries:**
```python
# ✅ CORRECT (eager loading)
from sqlalchemy.orm import selectinload

async def get_project_with_tasks(self, project_id: int) -> Optional[Project]:
    stmt = (
        select(Project)
        .options(selectinload(Project.tasks))
        .where(Project.id == project_id)
    )
    result = await self.db.execute(stmt)
    return result.scalar_one_or_none()

# ❌ INCORRECT (N+1 query problem)
async def get_project_with_tasks(self, project_id: int) -> Optional[Project]:
    project = await self.get_by_id(project_id)
    # Accessing project.tasks triggers N additional queries!
    for task in project.tasks:
        ...
```

---

### **Memory Management**

**Respect 2GB container limit:**
- ✅ Use pagination for large datasets
- ✅ Limit query results (`.limit(100)`)
- ✅ Stream large responses
- ❌ NO loading entire tables into memory

---

## 🔒 Security Standards

### **Environment Variables**

**ALL secrets in `.env` file:**
```python
# core/config/settings.py
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # Database
    database_url: str

    # Redis
    redis_url: str

    # JWT
    secret_key: str
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 15

    # OpenRouter
    openrouter_api_key: str

    class Config:
        env_file = ".env"
        case_sensitive = False
```

**Key Rules:**
- ✅ Use Pydantic Settings for configuration
- ✅ All secrets from environment variables
- ✅ Provide sensible defaults where possible
- ❌ NEVER hardcode secrets in code
- ❌ NEVER commit `.env` file

---

## 🛠️ Common Development Tasks

### **Create Database Migration**
```bash
cd backend
poetry run alembic revision --autogenerate -m "Add user table"
```

### **Apply Migrations**
```bash
poetry run alembic upgrade head
```

### **Run Tests**
```bash
# All tests
poetry run pytest

# With coverage
poetry run pytest --cov=app --cov-report=term-missing

# Specific test file
poetry run pytest tests/unit/test_services/test_user_service.py
```

### **Run Development Server**
```bash
poetry run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### **Code Quality Checks**
```bash
# Format code
poetry run black .

# Sort imports
poetry run isort .

# Type checking
poetry run mypy .

# Linting
poetry run ruff check .
```

---

## 💻 Development Workflow & Coding Standards

### **Poetry Dependency Management**

**Adding Dependencies:**
```bash
cd backend

# Add production dependency
poetry add package-name

# Add dev dependency
poetry add --group dev package-name

# Install all dependencies
poetry install

# Update lock file
poetry update
```

**Key Rules:**
- ✅ ALWAYS use `poetry add` (never edit pyproject.toml manually)
- ✅ Lock ALL dependencies with exact versions
- ✅ Use `--group dev` for development-only packages
- ✅ Test after adding dependencies (`poetry run pytest`)
- ❌ NEVER commit with unlocked dependencies
- ❌ NEVER use `pip install` (breaks Poetry lock)

---

### **Git Commit Standards**

**Conventional Commits Format:**
```bash
<type>(<scope>): <subject>

<body>

<footer>
```

**Types:**
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation only
- `style`: Code formatting (no logic change)
- `refactor`: Code restructuring (no behavior change)
- `test`: Adding or updating tests
- `chore`: Maintenance tasks

**Examples:**
```bash
# ✅ GOOD commits
git commit -m "feat(auth): add GitHub OAuth login"
git commit -m "fix(tasks): prevent duplicate task identifiers"
git commit -m "refactor(files): extract file validation to helper method"

# ❌ BAD commits
git commit -m "Update files"          # Too vague
git commit -m "WIP"                   # Work in progress
git commit -m "Fixed bug"             # What bug?
```

**Pre-Commit Hooks:**
Ardha uses automated pre-commit hooks (`.pre-commit-config.yaml`):
- **black**: Auto-formats code
- **isort**: Sorts imports
- **flake8**: Linting (PEP 8 compliance)
- **mypy**: Type checking
- **bandit**: Security checks

**If hooks fail:**
```bash
# View what failed
git commit -m "your message"  # Hooks run automatically

# Fix issues manually
poetry run black .
poetry run isort .
poetry run flake8 .

# Or bypass (ONLY if hooks have false positives)
git commit --no-verify -m "your message"
```

---

### **Flake8 Coding Standards**

**Configuration** (`.flake8`):
```ini
[flake8]
max-line-length = 100
max-complexity = 10
exclude = .git,__pycache__,.venv,build,dist,*.egg-info,alembic/versions
ignore = W503,E203
per-file-ignores = __init__.py:F401
```

**Common Flake8 Errors & Fixes:**

**E712: Comparison to False (SQLAlchemy-specific)**
```python
# ❌ WRONG
stmt = select(File).where(File.is_deleted == False)

# ✅ CORRECT (use .is_() for SQLAlchemy)
stmt = select(File).where(File.is_deleted.is_(False))
```

**F401: Unused Import**
```python
# ❌ WRONG
from ardha.core.config import get_settings
import tempfile  # Imported but never used

# ✅ CORRECT (remove unused imports)
from ardha.core.config import get_settings
```

**E501: Line Too Long**
```python
# ❌ WRONG (>100 characters)
user = await self.repository.create_user_with_profile_and_settings(email="test@example.com", full_name="Test User")

# ✅ CORRECT (split long lines)
user = await self.repository.create_user_with_profile_and_settings(
    email="test@example.com",
    full_name="Test User"
)
```

**W293: Blank Line Contains Whitespace**
```python
# ❌ WRONG (spaces on blank line)
def method1():
    pass

def method2():  # <-- blank line above has spaces

# ✅ CORRECT (Black auto-fixes this)
poetry run black .
```

---

### **SQLAlchemy Best Practices**

**Boolean Comparisons:**
```python
# ❌ WRONG
.where(Model.is_active == True)
.where(Model.is_deleted == False)

# ✅ CORRECT
.where(Model.is_active.is_(True))
.where(Model.is_deleted.is_(False))

# ✅ EVEN BETTER (for False checks)
.where(~Model.is_deleted)  # Negation operator
```

**Avoid N+1 Queries:**
```python
# ❌ WRONG (N+1 query problem)
async def get_project_with_tasks(project_id):
    project = await self.get_by_id(project_id)
    for task in project.tasks:  # Triggers N queries!
        print(task.name)

# ✅ CORRECT (eager loading)
from sqlalchemy.orm import selectinload

async def get_project_with_tasks(project_id):
    stmt = (
        select(Project)
        .options(selectinload(Project.tasks))
        .where(Project.id == project_id)
    )
    result = await self.db.execute(stmt)
    return result.scalar_one_or_none()
```

---

### **Common Mistakes to Avoid**

**1. Tempfile Memory Leaks:**
```python
# ❌ WRONG (creates orphaned temp directories)
import tempfile
service = FileService(db, Path(tempfile.mkdtemp(prefix="ardha-")))

# ✅ CORRECT (use project root from config)
from ardha.core.config import get_settings
settings = get_settings()
project_root = Path(settings.files.project_root)
service = FileService(db, project_root)
```

**2. Test Mocks in Production Code:**
```python
# ❌ WRONG (test code in production service)
class MyService:
    def production_method(self):
        pass

class MockMyService:  # DON'T PUT THIS HERE!
    def mock_method(self):
        pass

# ✅ CORRECT (mocks in tests/fixtures/)
# File: tests/fixtures/my_fixtures.py
class MockMyService:
    def mock_method(self):
        pass
```

**3. Missing Type Hints:**
```python
# ❌ WRONG
async def get_user(user_id):
    return await self.repository.get_by_id(user_id)

# ✅ CORRECT
async def get_user(self, user_id: UUID) -> Optional[User]:
    return await self.repository.get_by_id(user_id)
```

**4. Hardcoded Configuration:**
```python
# ❌ WRONG
DATABASE_URL = "postgresql://user:pass@localhost/db"

# ✅ CORRECT
from ardha.core.config import get_settings
settings = get_settings()
database_url = settings.database.url  # From environment
```

---

### **Code Review Checklist**

Before committing, verify:

- [ ] All functions have type hints
- [ ] All async I/O operations use `await`
- [ ] No hardcoded secrets or configuration
- [ ] Boolean comparisons use `.is_(True/False)` for SQLAlchemy
- [ ] Imports are used (no F401 errors)
- [ ] Lines are <100 characters
- [ ] Tests pass (`poetry run pytest`)
- [ ] Flake8 clean (`poetry run flake8 .`)
- [ ] Black formatted (`poetry run black .`)
- [ ] No test code in production files
- [ ] No temporary directory creation in request handlers

---

### **When Pre-Commit Hooks Fail**

**Step-by-Step Fix Process:**

1. **Read the error carefully** - Pre-commit shows exactly what's wrong
2. **Fix the specific files** mentioned in the error
3. **Re-run the commit** - Hooks run automatically

**Common Scenarios:**

**Black/isort failures:**
```bash
# Hooks already fixed files, just add and retry
git add -u
git commit -m "your message"  # Will pass now
```

**Flake8 failures:**
```bash
# Fix the specific errors shown
# Example: Remove unused import from line 42
vim src/ardha/services/my_service.py  # Remove import

# Then commit again
git commit -m "your message"
```

**Mypy failures in unrelated files:**
```bash
# If errors are in files YOU didn't modify, use --no-verify
# (These are pre-existing issues to fix later)
git commit --no-verify -m "feat: your changes"
```

---

## 🌟 Open-Source Best Practices

These patterns demonstrate:

✨ **Clean Architecture** - Clear separation of concerns
✨ **Type Safety** - Full type hints for IDE support
✨ **Async Performance** - Non-blocking I/O throughout
✨ **Testability** - Every layer independently testable
✨ **Documentation** - OpenAPI specs + code comments

**Learn more**: https://github.com/ardhaecosystem/Ardha

---

**Version**: 1.1
**Last Updated**: November 17, 2025
**Maintained By**: Ardha Development Team
**License**: MIT (Open Source)
