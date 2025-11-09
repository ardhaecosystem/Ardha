# Ardha Backend

FastAPI-based backend for the Ardha AI-Native Project Management Platform.

## Technology Stack

- **Python**: 3.12.3
- **Framework**: FastAPI 0.115.4
- **ORM**: SQLAlchemy 2.0.35 (async)
- **Database**: PostgreSQL 15
- **Cache**: Redis 7.2
- **Vector DB**: Qdrant 1.7.4
- **AI**: LangChain 0.3.7, LangGraph 0.2.45
- **Package Manager**: Poetry

## Development Setup

### Prerequisites

- Python 3.11 or higher
- Poetry (package manager)
- Docker and Docker Compose (for databases)
- Git

### Initial Setup

```bash
cd backend

# Install Poetry (if not installed)
curl -sSL https://install.python-poetry.org | python3 -

# Configure Poetry to use shared cache
poetry config cache-dir ../.poetry-cache

# Install dependencies
poetry install --no-root

# Activate virtual environment
poetry shell

# Verify installation
python --version  # Should be 3.12.3
```

### Pre-commit Hooks

Install pre-commit hooks for automatic code quality checks:

```bash
# Install pre-commit (already in dev dependencies)
poetry install --with dev

# Install git hooks
poetry run pre-commit install

# Run manually on all files
poetry run pre-commit run --all-files
```

The hooks will automatically run before each commit and check:
- **Python code formatting** (Black, isort)
- **Linting** (flake8, mypy)
- **Security issues** (Bandit)
- **Common file issues** (trailing whitespace, large files, etc.)
- **Frontend formatting** (Prettier)

### Environment Variables

Create a `.env` file in the backend directory:

```bash
# Database
DATABASE__URL=postgresql+asyncpg://ardha_user:ardha_password@localhost:5432/ardha_dev

# Redis
REDIS__URL=redis://localhost:6379/0

# Qdrant
QDRANT__URL=http://localhost:6333

# Security
SECURITY__JWT_SECRET_KEY=your-secret-key-here-min-32-chars
SECURITY__JWT_ALGORITHM=HS256
SECURITY__JWT_ACCESS_TOKEN_EXPIRE_MINUTES=15
SECURITY__JWT_REFRESH_TOKEN_EXPIRE_DAYS=7

# AI
AI__OPENROUTER_API_KEY=your-openrouter-api-key

# OAuth (optional)
OAUTH__GITHUB_CLIENT_ID=your-github-client-id
OAUTH__GITHUB_CLIENT_SECRET=your-github-client-secret
OAUTH__GOOGLE_CLIENT_ID=your-google-client-id
OAUTH__GOOGLE_CLIENT_SECRET=your-google-client-secret

# Email (optional)
EMAIL__HOST=smtp.gmail.com
EMAIL__PORT=587
EMAIL__USER=your-email@gmail.com
EMAIL__PASSWORD=your-app-password
```

**Note**: The double underscore (`__`) is required because Pydantic Settings uses `env_nested_delimiter="__"` to map nested config like `database.url`.

### Running the Development Server

```bash
# Start all services (PostgreSQL, Redis, Qdrant)
docker-compose up -d

# Run development server with auto-reload
poetry run uvicorn ardha.main:app --reload --host 0.0.0.0 --port 8000

# API will be available at:
# - http://localhost:8000
# - OpenAPI docs: http://localhost:8000/docs
# - ReDoc: http://localhost:8000/redoc
```

### Database Migrations

```bash
# Create new migration (auto-generate from model changes)
DATABASE__URL="postgresql+asyncpg://ardha_user:ardha_password@localhost:5432/ardha_dev" \
  poetry run alembic revision --autogenerate -m "description"

# Apply migrations
DATABASE__URL="postgresql+asyncpg://ardha_user:ardha_password@localhost:5432/ardha_dev" \
  poetry run alembic upgrade head

# Rollback one migration
DATABASE__URL="postgresql+asyncpg://ardha_user:ardha_password@localhost:5432/ardha_dev" \
  poetry run alembic downgrade -1

# Check current migration
DATABASE__URL="postgresql+asyncpg://ardha_user:ardha_password@localhost:5432/ardha_dev" \
  poetry run alembic current

# View migration history
DATABASE__URL="postgresql+asyncpg://ardha_user:ardha_password@localhost:5432/ardha_dev" \
  poetry run alembic history
```

## Testing

### Running Tests

```bash
# Run all tests
poetry run pytest

# Run with coverage report
poetry run pytest --cov=ardha --cov-report=html --cov-report=term-missing

# Run specific test file
poetry run pytest tests/unit/test_services/test_auth_service.py

# Run specific test
poetry run pytest tests/unit/test_services/test_auth_service.py::test_register_user

# Run with verbose output
poetry run pytest -v

# Run and stop on first failure
poetry run pytest -x

# Run tests in parallel (faster)
poetry run pytest -n auto
```

### Test Structure

```
tests/
├── conftest.py           # Shared fixtures
├── unit/                 # Fast unit tests
│   ├── test_models/
│   ├── test_services/
│   └── test_repositories/
└── integration/          # Slower integration tests
    ├── test_auth_flow.py
    ├── test_project_flow.py
    ├── test_task_flow.py
    └── test_milestone_flow.py
```

## Code Quality

### Formatting

```bash
# Format code with Black
poetry run black .

# Sort imports with isort
poetry run isort .

# Run both
poetry run black . && poetry run isort .
```

### Type Checking

```bash
# Run mypy type checker
poetry run mypy src/ardha
```

### Linting

```bash
# Run flake8 linter
poetry run flake8 src/ardha

# Run ruff (faster alternative)
poetry run ruff check .

# Auto-fix with ruff
poetry run ruff check . --fix
```

### Security Checks

```bash
# Run bandit security scanner
poetry run bandit -r src/ardha -c pyproject.toml
```

### All Quality Checks

```bash
# Run all checks at once
poetry run black . && \
poetry run isort . && \
poetry run flake8 src/ardha && \
poetry run mypy src/ardha && \
poetry run bandit -r src/ardha -c pyproject.toml
```

## Project Structure

```
backend/
├── src/ardha/
│   ├── api/              # API layer
│   │   └── v1/routes/   # API endpoints
│   ├── core/            # Core utilities
│   ├── db/              # Database configuration
│   ├── models/          # SQLAlchemy models
│   ├── repositories/    # Data access layer
│   ├── schemas/         # Pydantic schemas
│   ├── services/        # Business logic
│   └── workflows/       # LangGraph workflows
├── tests/               # Test suite
├── alembic/             # Database migrations
├── pyproject.toml       # Dependencies and config
└── README.md            # This file
```

## API Documentation

Once the server is running, visit:
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

## Common Development Tasks

### Adding a New API Endpoint

1. Define Pydantic schemas in `schemas/requests/` and `schemas/responses/`
2. Create route in `api/v1/routes/`
3. Implement service logic in `services/`
4. Add repository methods in `repositories/` (if database access needed)
5. Add database model in `models/` (if new table needed)
6. Write tests in `tests/`
7. Run tests and quality checks

### Creating a Database Migration

```bash
# After modifying models in src/ardha/models/
DATABASE__URL="postgresql+asyncpg://ardha_user:ardha_password@localhost:5432/ardha_dev" \
  poetry run alembic revision --autogenerate -m "add user avatar field"

# Review the generated migration in alembic/versions/
# Edit if needed, then apply:
DATABASE__URL="postgresql+asyncpg://ardha_user:ardha_password@localhost:5432/ardha_dev" \
  poetry run alembic upgrade head
```

## Troubleshooting

### Database Connection Issues

```bash
# Check if PostgreSQL is running
docker ps | grep postgres

# View PostgreSQL logs
docker logs ardha-postgres

# Connect to database directly
docker exec -it ardha-postgres psql -U ardha_user -d ardha_dev
```

### Import Errors

```bash
# Reinstall dependencies
poetry install --no-root

# Clear cache and reinstall
rm -rf .venv
poetry install --no-root
```

### Migration Issues

```bash
# Check current migration status
DATABASE__URL="postgresql+asyncpg://ardha_user:ardha_password@localhost:5432/ardha_dev" \
  poetry run alembic current

# View migration history
DATABASE__URL="postgresql+asyncpg://ardha_user:ardha_password@localhost:5432/ardha_dev" \
  poetry run alembic history

# Rollback to specific revision
DATABASE__URL="postgresql+asyncpg://ardha_user:ardha_password@localhost:5432/ardha_dev" \
  poetry run alembic downgrade <revision_id>
```

## Contributing

1. Create a feature branch from `dev`
2. Make your changes
3. Run all quality checks and tests
4. Commit with conventional commit format
5. Push and create pull request

## License

MIT License - See LICENSE file for details