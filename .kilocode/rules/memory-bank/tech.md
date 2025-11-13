# Technology Stack & Development Setup

## Core Technologies

### Backend Stack

**Runtime & Framework:**
- Python 3.12.3 (locked version)
- FastAPI 0.115.4 - Modern async web framework
- Uvicorn 0.32.0 - ASGI server with auto-reload
- Pydantic 2.9.2 - Data validation and settings
- Pydantic Settings 2.6.0 - Environment configuration

**Database & ORM:**
- PostgreSQL 15 - Primary relational database
- SQLAlchemy 2.0.35 - Async ORM
- Alembic 1.13.3 - Database migrations
- asyncpg 0.29.0 - Async PostgreSQL driver
- psycopg2-binary 2.9.9 - Sync PostgreSQL driver (for Alembic)

**Caching & Message Queue:**
- Redis 7.2 - Caching and session storage
- redis 5.1.1 (Python client) - Redis connectivity
- Celery 5.4.0 - Background task processing

**AI & Machine Learning:**
- LangChain 0.3.7 - LLM framework ✅
- LangGraph 0.2.45 - Workflow orchestration ✅
- LangChain-OpenAI 0.2.8 - OpenAI/OpenRouter integration ✅
- OpenAI SDK 1.54.3 - API client (OpenRouter compatible) ✅
- Qdrant Client 1.12.1 - Vector database client ✅
- sentence-transformers 2.7.0 - Text embedding generation ✅

**Authentication & Security:**
- python-jose 3.3.0 - JWT token handling
- passlib 1.7.4 - Password hashing
- bcrypt (included with passlib)
- email-validator 2.3.0 - Email validation for Pydantic EmailStr

**Utilities:**
- httpx 0.27.2 - Async HTTP client
- aiofiles 24.1.0 - Async file operations
- python-dotenv 1.0.1 - Environment variables
- websockets 13.1 - WebSocket support
- GitPython 3.1.43 - Git operations

**Development Tools:**
- pytest 8.3.3 - Testing framework
- pytest-asyncio 0.24.0 - Async test support
- pytest-cov 5.0.0 - Coverage reporting
- black 24.10.0 - Code formatting
- isort 5.13.2 - Import sorting
- mypy 1.13.0 - Type checking
- ruff 0.7.3 - Fast linter

### Frontend Stack

**Runtime & Framework:**
- Node.js 20.10.0 LTS
- Next.js 15.0.2 - React framework with App Router
- React 19.0.0-rc - UI library (Release Candidate)
- TypeScript 5.6.3 - Type safety

**UI Components:**
- Radix UI - Unstyled accessible components:
  - @radix-ui/react-dialog 1.1.2
  - @radix-ui/react-dropdown-menu 2.1.2
  - @radix-ui/react-select 2.1.2
  - @radix-ui/react-toast 1.2.2
  - @radix-ui/react-tooltip 1.1.3
- Tailwind CSS 3.4.14 - Utility-first CSS
- class-variance-authority 0.7.0 - Component variants
- clsx 2.1.1 - Conditional classes
- tailwind-merge 2.5.4 - Merge Tailwind classes

**Code Editor & Terminal:**
- CodeMirror 6 - Code editor:
  - @uiw/react-codemirror 4.23.5 - React wrapper
  - @codemirror/lang-javascript 6.2.2
  - @codemirror/lang-python 6.1.6
  - @codemirror/lang-html 6.4.11
  - @codemirror/lang-css 6.3.1
  - @codemirror/lang-json 6.0.2
  - @codemirror/lang-markdown 6.5.0
  - @lezer/yaml 1.0.3 - YAML support
- xterm.js 5.3.0 - Terminal emulator
- xterm-addon-fit 0.8.0 - Terminal auto-sizing

**Animation & Icons:**
- Framer Motion 11.11.7 - Animation library
- Lucide React 0.451.0 - Icon library

**Utilities:**
- date-fns 4.1.0 - Date manipulation

**Development Tools:**
- eslint 9.13.0 - Linting
- eslint-config-next 15.0.2 - Next.js ESLint config
- autoprefixer 10.4.20 - CSS vendor prefixes
- postcss 8.4.47 - CSS transformations

### Infrastructure Stack

**Containerization:**
- Docker 24.0+ - Container runtime
- Docker Compose 2.20+ - Multi-container orchestration

**Databases:**
- postgres:15.5-alpine - PostgreSQL container
- qdrant/qdrant:v1.7.4 - Vector database container
- redis:7.2-alpine - Cache container

**Web Server:**
- Caddy 2.7-alpine - Automatic HTTPS reverse proxy

**CI/CD:**
- GitHub Actions - Automated testing and deployment

## Development Environment Setup

### System Requirements

**Minimum:**
- 8GB RAM (critical constraint!)
- 20GB disk space
- Linux, macOS, or Windows with WSL2
- Docker and Docker Compose installed
- Git 2.40+

**Recommended:**
- 16GB RAM (for comfortable development)
- 50GB disk space
- SSD for faster I/O
- Modern multi-core processor

### Repository Structure

**Monorepo Layout:**
```
/home/veda/ardha-projects/Ardha/
├── .poetry-cache/        # Shared Poetry cache (206MB)
├── .pnpm-store/          # Shared pnpm cache (206MB)
├── backend/              # Python/FastAPI backend
│   ├── .venv/           # Virtual environment (per branch)
│   ├── src/ardha/       # Source code
│   ├── poetry.lock      # Locked dependencies
│   └── pyproject.toml   # Package configuration
├── frontend/            # Next.js frontend
│   ├── node_modules/   # Dependencies (per branch)
│   ├── src/            # Source code
│   ├── package.json    # Package configuration
│   └── pnpm-lock.yaml  # Locked dependencies
└── openspec/           # Specifications
```

### Backend Development Setup

**Initial Setup:**
```bash
cd ~/ardha-projects/Ardha/backend

# Install Poetry (if not installed)
curl -sSL https://install.python-poetry.org | python3 -

# Configure Poetry to use shared cache
poetry config cache-dir ../.poetry-cache

# Install dependencies (uses cache, very fast)
poetry install --no-root

# Activate virtual environment
poetry shell

# Verify installation
python --version  # Should be 3.12.3
```

**Daily Development:**
```bash
cd ~/ardha-projects/Ardha/backend

# Activate environment
poetry shell

# Run development server
uvicorn ardha.main:app --reload --port 8000

# Run tests
pytest

# Format code
black .

# Sort imports
isort .

# Type checking
mypy .

# Linting
ruff check .
```

**Database Migrations:**
```bash
# Create new migration (must set DATABASE__URL)
DATABASE__URL="postgresql+asyncpg://ardha_user:ardha_password@localhost:5432/ardha_dev" \
  alembic revision --autogenerate -m "description"

# Apply migrations
DATABASE__URL="postgresql+asyncpg://ardha_user:ardha_password@localhost:5432/ardha_dev" \
  alembic upgrade head

# Rollback one migration
DATABASE__URL="postgresql+asyncpg://ardha_user:ardha_password@localhost:5432/ardha_dev" \
  alembic downgrade -1

# Check current migration
DATABASE__URL="postgresql+asyncpg://ardha_user:ardha_password@localhost:5432/ardha_dev" \
  alembic current

# View migration history
DATABASE__URL="postgresql+asyncpg://ardha_user:ardha_password@localhost:5432/ardha_dev" \
  alembic history
```

**Note**: The `DATABASE__URL` environment variable uses double underscores (`__`) because Pydantic Settings maps nested config like `database.url` using `env_nested_delimiter="__"`.

### Frontend Development Setup

**Initial Setup:**
```bash
cd ~/ardha-projects/Ardha/frontend

# Install pnpm (if not installed)
npm install -g pnpm

# Configure pnpm to use shared store
echo "store-dir=../.pnpm-store" > .npmrc

# Install dependencies (uses cache, very fast)
pnpm install

# Verify installation
pnpm list
```

**Daily Development:**
```bash
cd ~/ardha-projects/Ardha/frontend

# Run development server
pnpm dev  # http://localhost:3000

# Build for production
pnpm build

# Type checking
pnpm type-check

# Linting
pnpm lint
```

### Docker Development Environment

**Starting All Services:**
```bash
cd ~/ardha-projects/Ardha

# Start all containers
docker-compose up -d

# View logs
docker-compose logs -f

# Stop all containers
docker-compose down

# Stop and remove volumes (clean slate)
docker-compose down -v
```

**Container Configuration:**
```yaml
# Memory limits enforced in docker-compose.yml
services:
  postgres:
    mem_limit: 2g
  qdrant:
    mem_limit: 2.5g
  redis:
    mem_limit: 512m
  backend:
    mem_limit: 2g
  frontend:
    mem_limit: 1g
```

## Critical Technical Constraints

### Memory Constraints (8GB Total)

**Container Memory Budget:**
- PostgreSQL: 2GB (tuned with shared_buffers=512MB)
- Qdrant: 2.5GB (scalar quantization enabled)
- Redis: 512MB (LRU eviction, maxmemory-policy=allkeys-lru)
- Backend: 2GB (Python process limits)
- Frontend: 1GB (Node.js process limits)
- System overhead: ~0.5-1GB

**Optimization Strategies:**
- Qdrant: Use scalar quantization (40% memory reduction)
- Redis: LRU eviction for cache management
- PostgreSQL: Tune shared_buffers, work_mem conservatively
- Backend: Limit worker processes (4 max)
- Frontend: SSR with minimal client bundle

### AI Cost Constraints ($60/month)

**Cost Management:**
- Hard budget limit: $60/month total
- Daily limit: $2/day
- Alert at 80% of budget
- Automatic throttling at 90%
- Block at 100%

**Token Efficiency:**
- Prompt caching: 78-90% cost reduction
- Hierarchical context: Load only needed files
- Model routing: Simple tasks → cheap models
- Session limits: Stop after 3 failed attempts
- Context pruning: Remove irrelevant history

**Model Cost Structure:**
```
Gemini Flash (~35% of usage):
  - $0.15-0.30 per 1M tokens
  - Simple queries, summaries

Claude Sonnet 4.5 (~45% of usage):
  - $3.00 per 1M input tokens
  - $15.00 per 1M output tokens
  - Medium complexity tasks

Claude Opus 4.1 (~20% of usage):
  - $15.00 per 1M input tokens
  - $75.00 per 1M output tokens
  - Complex architecture decisions
```

### Performance Targets

**Backend API:**
- Response time: <500ms (95th percentile)
- Throughput: 100 req/s per endpoint
- Database queries: <100ms
- Memory usage: <2GB steady state

**Frontend:**
- Page load: <2s (90th percentile)
- Time to Interactive: <3s
- Bundle size: <200KB gzipped
- Lighthouse score: >90

**Database:**
- PostgreSQL: <100 concurrent connections
- Redis: <50K keys in memory
- Qdrant: <1M vectors per collection

## Configuration Management

### Environment Variables

**Backend (.env):**
```bash
# Database
DATABASE_URL=postgresql+asyncpg://user:pass@localhost:5432/ardha
REDIS_URL=redis://localhost:6379
QDRANT_URL=http://localhost:6333

# Security
SECRET_KEY=your-secret-key-here
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=15
REFRESH_TOKEN_EXPIRE_DAYS=7

# AI
OPENROUTER_API_KEY=your-openrouter-key
AI_BUDGET_DAILY=2.0
AI_BUDGET_MONTHLY=60.0

# OAuth
GITHUB_CLIENT_ID=your-github-client-id
GITHUB_CLIENT_SECRET=your-github-client-secret
GOOGLE_CLIENT_ID=your-google-client-id
GOOGLE_CLIENT_SECRET=your-google-client-secret

# Email (optional)
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your-email@gmail.com
SMTP_PASSWORD=your-app-password
```

**Frontend (.env.local):**
```bash
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_WS_URL=ws://localhost:8000/ws
```

### Package Management

**Backend (Poetry):**
```toml
[tool.poetry]
name = "ardha-backend"
version = "0.1.0"
python = "^3.11"

# All dependencies locked in poetry.lock
# Use: poetry install --no-root
```

**Frontend (pnpm):**
```json
{
  "name": "ardha-frontend",
  "version": "0.1.0",
  "packageManager": "pnpm@8.0.0",
  "engines": {
    "node": ">=20.10.0"
  }
}
```

## Testing Infrastructure

### Backend Testing

**Test Structure:**
```
backend/tests/
├── conftest.py           # Shared fixtures ✅
├── fixtures/             # Test fixtures ✅
│   ├── auth_fixtures.py  # Auth test data ✅
│   ├── chat_fixtures.py  # Chat test data ✅
│   └── workflow_fixtures.py # Workflow test data ✅
├── unit/                 # Fast unit tests ✅
│   ├── test_models.py
│   ├── test_services.py
│   ├── test_chat_repository.py  # Chat repository tests ✅
│   ├── test_chat_service.py     # Chat service tests ✅
│   ├── test_workflow_state.py   # Workflow state tests ✅
│   ├── test_workflow_orchestrator.py  # Orchestration tests ✅
│   ├── test_workflow_orchestrator_simple.py  # Simple orchestration tests ✅
│   ├── test_research_workflow.py # Research workflow unit tests ✅
│   └── test_task_generation_unit.py # Task generation unit tests ✅
└── integration/          # Slower integration tests ✅
    ├── test_api.py
    ├── test_auth.py
    ├── test_auth_flow.py      # Auth integration tests ✅
    ├── test_project_flow.py   # Project integration tests ✅
    ├── test_task_flow.py      # Task integration tests ✅
    ├── test_milestone_flow.py # Milestone integration tests ✅
    ├── test_chat_api.py       # Chat API tests ✅
    ├── test_workflow_api.py   # Workflow API tests ✅
    └── e2e/                   # End-to-end tests ✅
        ├── test_workflow_execution.py  # Workflow E2E tests ✅
        └── test_prd_workflow_execution.py # PRD Workflow E2E tests ✅
```

**Running Tests:**
```bash
# All tests (105 tests total: 16 Phase 1 + 57 Phase 2 chat + 33 research workflow + 2 task generation + 29 PRD)
pytest

# With coverage (80%+ coverage on core workflow files)
pytest --cov=ardha --cov-report=html

# Specific test file
pytest tests/unit/test_models.py

# Chat system tests
pytest tests/unit/test_chat_repository.py -v
pytest tests/unit/test_chat_service.py -v
pytest tests/integration/test_chat_api.py -v

# Workflow system tests
pytest tests/unit/test_workflow_state.py -v
pytest tests/unit/test_workflow_orchestrator.py -v
pytest tests/unit/test_workflow_orchestrator_simple.py -v
pytest tests/unit/test_research_workflow.py -v
pytest tests/integration/test_workflow_api.py -v
pytest tests/e2e/test_workflow_execution.py -v
pytest tests/e2e/test_prd_workflow_execution.py -v

# Task generation workflow tests
pytest tests/unit/test_task_generation_unit.py -v

# Specific test
pytest tests/unit/test_models.py::test_user_creation

# Parallel execution
pytest -n auto
```

### Frontend Testing

**Test Structure:**
```
frontend/__tests__/
├── unit/                 # Component tests
│   ├── components/
│   └── utils/
├── integration/          # Feature tests
│   ├── auth.test.tsx
│   └── tasks.test.tsx
└── e2e/                 # Playwright tests
    ├── auth.spec.ts
    └── projects.spec.ts
```

**Running Tests:**
```bash
# Unit tests
pnpm test

# With coverage
pnpm test:coverage

# E2E tests
pnpm test:e2e

# Specific test
pnpm test auth.test.tsx
```

## Code Quality Tools

### Backend Quality

**Formatting:**
```bash
# Black - opinionated formatter
black . --line-length 100

# isort - import sorting
isort . --profile black
```

**Type Checking:**
```bash
# mypy - static type checker
mypy . --strict
```

**Linting:**
```bash
# ruff - fast Python linter
ruff check .

# Auto-fix
ruff check . --fix
```

### Frontend Quality

**Formatting:**
```bash
# Prettier (via Next.js)
pnpm format
```

**Type Checking:**
```bash
# TypeScript
pnpm type-check
```

**Linting:**
```bash
# ESLint
pnpm lint
```

## Git Workflow

### Branch Strategy

**Three-Branch Model:**
```
main (production)
  ↑ merge when stable
dev (integration)
  ↑ merge when feature complete
feature/* (development)
```

**Branch Commands:**
```bash
# Create feature branch
git checkout dev
git checkout -b feature/task-board

# Work and commit
git add .
git commit -m "feat: add task board component"

# Push to remote
git push origin feature/task-board

# Merge to dev (after PR approval)
git checkout dev
git merge feature/task-board
git push origin dev
```

### Commit Convention

**Format:** `type(scope): subject`

**Types:**
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation
- `style`: Code style (formatting)
- `refactor`: Code refactoring
- `test`: Adding tests
- `chore`: Maintenance

**Examples:**
```bash
git commit -m "feat(auth): implement GitHub OAuth login"
git commit -m "fix(tasks): prevent duplicate task IDs"
git commit -m "docs(readme): add installation instructions"
```

## Performance Monitoring

### Key Metrics to Track

**Backend:**
- Request latency (p50, p95, p99)
- Error rate
- Memory usage
- CPU usage
- Active connections
- Queue depth

**Frontend:**
- Page load time
- Time to Interactive
- First Contentful Paint
- Bundle size
- API call latency

**AI:**
- Token usage (input/output)
- Cost per request
- Model distribution
- Cache hit rate
- Response quality score

### Monitoring Tools (Future)

**Application Monitoring:**
- Prometheus - Metrics collection
- Grafana - Visualization
- Loki - Log aggregation

**Error Tracking:**
- Sentry - Error monitoring
- Stack traces
- User context

## Deployment Preparation

### Production Checklist

**Backend:**
- [ ] Environment variables configured
- [ ] Database migrations applied
- [ ] Static files served via CDN
- [ ] HTTPS enforced
- [ ] Rate limiting enabled
- [ ] Logging configured
- [ ] Monitoring active

**Frontend:**
- [ ] Production build tested
- [ ] Environment variables set
- [ ] CDN configured
- [ ] Bundle optimized
- [ ] PWA manifest (if applicable)
- [ ] Analytics configured

**Database:**
- [ ] Backups configured
- [ ] Connection pooling tuned
- [ ] Indexes created
- [ ] Query performance validated

## Common Development Tasks

### Adding New Backend Endpoint

1. Define Pydantic schema in `schemas/requests/` and `schemas/responses/`
2. Create route in `api/routes/`
3. Implement service logic in `services/`
4. Add database model if needed in `models/`
5. Write tests in `tests/unit/` and `tests/integration/`
6. Update OpenAPI docs (auto-generated)

### Adding New LangGraph Workflow

1. Create workflow class in `workflows/` inheriting from `BaseWorkflow`
2. Define workflow state in `workflows/state.py`
3. Implement workflow nodes in `workflows/nodes.py`
4. Add workflow configuration in `workflows/config.py`
5. Create API endpoints in `api/routes/workflows.py`
6. Write comprehensive tests (unit + integration + e2e)
7. Test with Redis checkpoints and Qdrant memory

### Adding New Frontend Page

1. Create page in `app/`
2. Create components in `components/`
3. Add to navigation
4. Create API client functions
5. Add TypeScript types
6. Write tests

### Running Database Migration

```bash
# Create migration (must set DATABASE__URL)
DATABASE__URL="postgresql+asyncpg://ardha_user:ardha_password@localhost:5432/ardha_dev" \
  alembic revision --autogenerate -m "add user table"

# Review generated migration
# Edit if needed

# Apply migration
DATABASE__URL="postgresql+asyncpg://ardha_user:ardha_password@localhost:5432/ardha_dev" \
  alembic upgrade head

# Rollback if needed
DATABASE__URL="postgresql+asyncpg://ardha_user:ardha_password@localhost:5432/ardha_dev" \
  alembic downgrade -1
```

### Testing LangGraph Workflows

```bash
# Test workflow state management
pytest tests/unit/test_workflow_state.py -v

# Test workflow orchestration
pytest tests/unit/test_workflow_orchestrator.py -v

# Test workflow API endpoints
pytest tests/integration/test_workflow_api.py -v

# Test end-to-end workflow execution
pytest tests/e2e/test_workflow_execution.py -v

# Test all workflow-related tests
pytest tests/ -k "workflow" -v

# Test all task generation-related tests
pytest tests/ -k "task_generation" -v
```

### Debugging Tips

**Backend:**
- Use `breakpoint()` for debugging
- Check logs: `docker-compose logs backend`
- Use FastAPI docs: `http://localhost:8000/docs`
- Test with `httpx` or `curl`

**Frontend:**
- Use React DevTools
- Check Network tab in browser
- Use `console.log()` strategically
- Test with browser debugger

## Completed Technical Implementations ✅

1. **LangGraph Workflow System**: ✅ StateGraph with abstract base class, checkpoint system
2. **Qdrant Vector Database**: ✅ Async client with embedding generation and semantic search
3. **Redis Checkpoint System**: ✅ Workflow state persistence with 7-day TTL
4. **AI Node Architecture**: ✅ Five specialized nodes (research, architect, implement, debug, memory)
5. **Workflow Execution Tracking**: ✅ Real-time monitoring with concurrent execution support
6. **Comprehensive Test Suite**: ✅ 105 tests (100% pass rate) with unit, integration, and e2e coverage
7. **Memory Ingestion Pipeline**: ✅ Automatic context ingestion with pattern extraction
8. **Server-Sent Events**: ✅ Real-time workflow progress streaming
9. **Research Workflow Implementation**: ✅ Multi-agent research system with 5 specialized nodes
10. **Research State Management**: ✅ ResearchState schema with comprehensive tracking
11. **Research Node Infrastructure**: ✅ Base node class with AI integration and memory
12. **Research Workflow Testing**: ✅ 33 comprehensive tests with 100% pass rate
13. **PRD Workflow Implementation**: ✅ Multi-agent PRD generation system with 5 specialized nodes
14. **PRD State Management**: ✅ PRDState schema with comprehensive tracking
15. **PRD Node Infrastructure**: ✅ Specialized PRD nodes with AI integration
16. **PRD Workflow Testing**: ✅ 29 comprehensive tests with 100% pass rate
17. **Task Generation Workflow Implementation**: ✅ Multi-agent task generation system with 5 specialized nodes
18. **Task Generation State Management**: ✅ TaskGenerationState schema with comprehensive tracking
19. **Task Generation Node Infrastructure**: ✅ Specialized task generation nodes with AI integration
20. **Task Generation Workflow Testing**: ✅ 2 comprehensive tests with 100% pass rate
21. **OpenSpec Service Implementation**: ✅ Complete OpenSpec management with file generation, validation, and archival
22. **OpenSpec Integration Testing**: ✅ End-to-end OpenSpec workflow tests with 100% pass rate

## Next Technical Decisions

1. **CI/CD Pipeline**: Define exact GitHub Actions workflow
2. **Monitoring Stack**: Prometheus + Grafana setup
3. **Backup Strategy**: Automated PostgreSQL backups
4. **CDN Configuration**: For static assets
5. **Logging Format**: Structured JSON logging standards
6. **Error Handling**: Centralized error handling strategy
7. **API Versioning**: Versioning strategy for breaking changes
8. **Multi-Agent Workflows**: Advanced AI agent coordination patterns
9. **Workflow Templates**: Reusable workflow definitions for common tasks
