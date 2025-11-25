# Ardha System Architecture

## Overview

Ardha follows a modern, scalable architecture designed for AI-native project management. The system is built around three primary layers with clear separation of concerns, enabling independent development, testing, and deployment of each component.

## High-Level Architecture

```
┌─────────────────────────────────────────────────────────┐
│                     FRONTEND LAYER                       │
│  Next.js 15 App Router (React 19 RC, TypeScript)        │
│  - Pages: Auth, Dashboard, Projects, Tasks, Chat        │
│  - WebSocket for real-time updates                      │
│  - CodeMirror 6 editor + xterm.js terminal              │
│  - Radix UI components + Tailwind CSS                   │
└─────────────────────────────────────────────────────────┘
                           ↕ HTTP/WebSocket
┌─────────────────────────────────────────────────────────┐
│                     BACKEND LAYER                        │
│  FastAPI (Python 3.12, async/await)                     │
│  - RESTful API (JWT auth, OAuth2)                       │
│  - LangGraph workflow orchestration                     │
│  - WebSocket server for collaboration                   │
│  - Celery background jobs                               │
└─────────────────────────────────────────────────────────┘
                           ↕
┌─────────────────────────────────────────────────────────┐
│                      DATA LAYER                          │
│  PostgreSQL 15  │  Qdrant  │  Redis 7  │  File System   │
│  (Relational)   │ (Vectors) │ (Cache)   │  (Git repos)   │
└─────────────────────────────────────────────────────────┘
```

## System Constraints

### Memory Constraints (8GB Total)

**Critical Memory Limits:**
- PostgreSQL: 2GB container limit
- Qdrant: 2.5GB limit (scalar quantization enabled)
- Redis: 512MB limit (LRU eviction policy)
- Backend: 2GB container limit
- Frontend: 1GB container limit

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

## Backend Architecture

### Core Components

#### 1. FastAPI Application Layer
```python
# Main application structure
ardha/
├── main.py                    # FastAPI app entry point
├── api/                       # API layer
│   ├── v1/
│   │   ├── routes/           # API endpoints
│   │   └── dependencies.py    # FastAPI dependencies
├── core/                      # Core utilities
│   ├── config.py             # Pydantic settings
│   ├── security.py           # JWT, OAuth, hashing
│   ├── exceptions.py         # Custom exceptions
│   └── logging.py            # Structured logging
├── db/                        # Database layer
│   ├── base.py               # SQLAlchemy base
│   ├── session.py            # Database sessions
│   └── init_db.py            # Database initialization
├── models/                    # SQLAlchemy models
├── schemas/                   # Pydantic schemas
├── services/                  # Business logic
├── workflows/                 # LangGraph workflows
└── tests/                     # Test suite
```

#### 2. API Layer Design

**RESTful API Principles:**
- Resource-based URLs (`/api/v1/projects/{id}`)
- HTTP method semantics (GET, POST, PATCH, DELETE)
- Consistent response formats
- Proper HTTP status codes
- API versioning via URL path

**Authentication & Authorization:**
- JWT-based authentication
- Role-based access control (RBAC)
- OAuth2 integration (GitHub, Google)
- Permission-based endpoint protection

**Request/Response Validation:**
- Pydantic schemas for validation
- Automatic error handling
- Request/response serialization
- OpenAPI documentation generation

#### 3. Service Layer Architecture

**Business Logic Separation:**
```python
# Service layer pattern
class ProjectService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.project_repo = ProjectRepository(db)
        self.task_repo = TaskRepository(db)

    async def create_project(self, project_data: ProjectCreate):
        # Business logic, validation, orchestration
        pass
```

**Key Services:**
- **AuthService**: Authentication, authorization, token management
- **ProjectService**: Project CRUD, member management
- **TaskService**: Task management, dependencies, status updates
- **ChatService**: AI chat orchestration, context management
- **WorkflowService**: AI workflow execution, state management
- **GitService**: Git operations, commit tracking
- **NotificationService**: Real-time notifications, email delivery

#### 4. Database Layer

**SQLAlchemy 2.0 Async:**
```python
# Repository pattern
class ProjectRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, project: Project) -> Project:
        self.db.add(project)
        await self.db.commit()
        await self.db.refresh(project)
        return project
```

**Database Design Principles:**
- Foreign key constraints with proper cascading
- Strategic indexes for performance
- Soft deletes for data retention
- Audit fields (created_at, updated_at)
- UUID primary keys for security

#### 5. AI Workflow System

**LangGraph Integration:**
```python
# Workflow orchestration
class ResearchWorkflow(BaseWorkflow):
    def __init__(self):
        super().__init__()
        self.add_node("research", ResearchNode())
        self.add_node("analyze", AnalyzeNode())
        self.add_node("report", ReportNode())
        self.add_edge("research", "analyze")
        self.add_edge("analyze", "report")
```

**Workflow Features:**
- StateGraph for complex workflows
- Checkpoint system with Redis
- Human-in-the-loop approval gates
- Concurrent execution support
- Real-time progress streaming

## Frontend Architecture

### Next.js 15 App Router

**Directory Structure:**
```
frontend/src/
├── app/                       # Next.js App Router
│   ├── layout.tsx            # Root layout with theme
│   ├── page.tsx              # Home/landing page
│   ├── auth/                 # Authentication pages
│   ├── dashboard/            # Main dashboard
│   ├── projects/             # Project management
│   ├── chat/                 # AI chat interface
│   └── settings/             # User settings
├── components/                # React components
│   ├── ui/                   # Base UI components
│   ├── layouts/              # Layout components
│   ├── forms/                # Form components
│   ├── task/                 # Task components
│   ├── chat/                 # Chat components
│   └── editor/               # Code editor
├── lib/                       # Utilities and helpers
│   ├── api/                  # API client
│   ├── hooks/                # Custom React hooks
│   ├── stores/               # Zustand stores
│   └── utils/                # Utility functions
└── types/                     # TypeScript types
```

### Component Architecture

**Design System:**
- **Radix UI**: Unstyled accessible components
- **Tailwind CSS**: Utility-first styling
- **Class Variance Authority**: Component variants
- **Lucide React**: Icon library
- **Framer Motion**: Animations

**State Management:**
- **Zustand**: Lightweight state management
- **React Query**: Server state management
- **Local Storage**: User preferences
- **URL State**: Shareable application state

### Real-Time Features

**WebSocket Integration:**
```typescript
// WebSocket hook
const useWebSocket = (url: string) => {
  const [socket, setSocket] = useState<WebSocket | null>(null);
  const [isConnected, setIsConnected] = useState(false);

  useEffect(() => {
    const ws = new WebSocket(url);
    ws.onopen = () => setIsConnected(true);
    ws.onclose = () => setIsConnected(false);
    setSocket(ws);

    return () => ws.close();
  }, [url]);

  return { socket, isConnected };
};
```

**Real-Time Updates:**
- Live task status updates
- Real-time chat streaming
- Project activity feeds
- Notification delivery
- Collaborative editing

## Data Layer Architecture

### PostgreSQL 15

**Database Design:**
```sql
-- Core tables
users                 # User accounts and profiles
projects              # Project containers
tasks                 # Task management
milestones            # Timeline management
chat_sessions         # AI chat sessions
messages              # Chat messages
git_commits           # Git commit tracking
databases             # Notion-style databases
database_entries      # Database records
notifications         # Notification queue
```

**Performance Optimizations:**
- Strategic indexes on foreign keys
- Partial indexes for common queries
- Composite indexes for complex filters
- Connection pooling (asyncpg)
- Query optimization with EXPLAIN ANALYZE

### Qdrant Vector Database

**Semantic Memory:**
```python
# Vector storage and retrieval
class MemoryService:
    def __init__(self):
        self.client = QdrantClient()
        self.embedding_model = SentenceTransformer('all-MiniLM-L6-v2')

    async def store_memory(self, content: str, metadata: dict):
        vector = self.embedding_model.encode(content)
        await self.client.upsert(
            collection_name="memories",
            points=[PointStruct(
                id=uuid4(),
                vector=vector.tolist(),
                payload={"content": content, **metadata}
            )]
        )
```

**Memory Tiers:**
- **Short-term**: Redis (1-2 hours, session context)
- **Long-term**: Qdrant (permanent, project-specific)
- **Organizational**: Qdrant (cross-project patterns)

### Redis 7

**Caching Strategy:**
```python
# Redis caching patterns
class CacheService:
    async def get_project(self, project_id: str):
        # Try cache first
        cached = await self.redis.get(f"project:{project_id}")
        if cached:
            return json.loads(cached)

        # Fallback to database
        project = await self.db.get_project(project_id)
        await self.redis.setex(f"project:{project_id}", 3600, json.dumps(project))
        return project
```

**Cache Use Cases:**
- Session storage (JWT tokens)
- API response caching
- Database query results
- AI model responses
- Real-time state

## AI Integration Architecture

### Multi-Model Support

**OpenRouter Integration:**
```python
# Model routing based on complexity
class AIService:
    def select_model(self, complexity: str) -> str:
        models = {
            "simple": "google/gemini-flash",
            "medium": "anthropic/claude-sonnet-4.5",
            "complex": "anthropic/claude-opus-4.1"
        }
        return models.get(complexity, "anthropic/claude-sonnet-4.5")
```

**Model Distribution:**
- **Simple (35%)**: Gemini Flash for basic queries
- **Medium (45%)**: Claude Sonnet 4.5 for general tasks
- **Complex (20%)**: Claude Opus 4.1 for architecture

### LangGraph Workflows

**Workflow Architecture:**
```python
# Base workflow class
class BaseWorkflow:
    def __init__(self):
        self.graph = StateGraph(WorkflowState)
        self.checkpointer = RedisCheckpointer()
        self.memory = QdrantMemory()

    def execute(self, inputs: dict) -> AsyncIterator[dict]:
        return self.graph.astream(
            inputs,
            checkpoint=self.checkpointer,
            interrupt_before=["human_approval"]
        )
```

**Workflow Types:**
- **ResearchWorkflow**: Market research, competitive analysis
- **PRDWorkflow**: Product requirements generation
- **TaskGenerationWorkflow**: Automated task breakdown
- **ImplementationWorkflow**: Code generation and testing
- **DebugWorkflow**: Error analysis and resolution

### Prompt Engineering

**Context Management:**
```python
# Hierarchical context loading
class ContextLoader:
    async def load_context(self, project_id: str, task_id: str):
        # Load in priority order
        context = {
            "task": await self.load_task(task_id),
            "project": await self.load_project_summary(project_id),
            "recent_commits": await self.load_recent_commits(project_id, 5),
            "relevant_docs": await self.search_relevant_docs(task_id)
        }
        return context
```

**Prompt Caching:**
- Static context marked as cacheable
- 5-minute cache duration
- Hierarchical loading (5-15K vs 150-300K tokens)
- Cost reduction: 78-90%

## Security Architecture

### Authentication System

**JWT Token Management:**
```python
# JWT token handling
class AuthService:
    def create_access_token(self, user_id: str) -> str:
        payload = {
            "sub": user_id,
            "exp": datetime.utcnow() + timedelta(minutes=15),
            "type": "access"
        }
        return jwt.encode(payload, SECRET_KEY, algorithm="HS256")

    def create_refresh_token(self, user_id: str) -> str:
        payload = {
            "sub": user_id,
            "exp": datetime.utcnow() + timedelta(days=7),
            "type": "refresh"
        }
        return jwt.encode(payload, SECRET_KEY, algorithm="HS256")
```

**OAuth Integration:**
- GitHub OAuth App integration
- Google OAuth 2.0 support
- Secure token exchange
- User profile synchronization

### Authorization System

**Role-Based Access Control:**
```python
# Permission checking
class PermissionService:
    async def check_permission(
        self,
        user_id: str,
        project_id: str,
        required_role: str
    ) -> bool:
        membership = await self.get_project_membership(user_id, project_id)
        if not membership:
            return False

        role_hierarchy = {"viewer": 1, "member": 2, "admin": 3, "owner": 4}
        user_level = role_hierarchy.get(membership.role, 0)
        required_level = role_hierarchy.get(required_role, 0)

        return user_level >= required_level
```

**Permission Levels:**
- **Viewer**: Read-only access
- **Member**: Full project access
- **Admin**: Administrative functions
- **Owner**: Full control

### Data Protection

**Encryption Strategy:**
- **At Rest**: PostgreSQL encryption, file system encryption
- **In Transit**: TLS 1.3 for all communications
- **Secrets Management**: Environment variables, Docker secrets
- **PII Protection**: Data minimization, anonymization

## Performance Architecture

### Database Optimization

**Query Optimization:**
```sql
-- Strategic indexing
CREATE INDEX CONCURRENTLY idx_tasks_project_status
ON tasks(project_id, status)
WHERE is_archived = false;

CREATE INDEX CONCURRENTLY idx_commits_project_created
ON git_commits(project_id, created_at DESC);

-- Partial indexes for common queries
CREATE INDEX CONCURRENTLY idx_active_projects
ON projects(id)
WHERE is_archived = false;
```

**Connection Management:**
- Connection pooling (asyncpg)
- Read replicas for read-heavy operations
- Query timeout management
- Slow query logging

### Caching Architecture

**Multi-Level Caching:**
```
┌─────────────────┐
│   Application    │ ← In-memory cache (Python)
└─────────┬───────┘
          │
┌─────────▼───────┐
│     Redis       │ ← Distributed cache
└─────────┬───────┘
          │
┌─────────▼───────┐
│   PostgreSQL    │ ← Persistent storage
└─────────────────┘
```

**Cache Strategies:**
- **Write-through**: Immediate cache updates
- **Write-behind**: Async cache updates
- **Cache-aside**: Application-managed cache
- **TTL-based**: Automatic expiration

### API Performance

**Response Optimization:**
- Async/await throughout
- Connection pooling
- Response compression
- Pagination for large datasets
- Selective field loading

**Rate Limiting:**
```python
# Rate limiting implementation
class RateLimiter:
    def __init__(self, redis_client):
        self.redis = redis_client

    async def is_allowed(self, key: str, limit: int, window: int) -> bool:
        current = await self.redis.incr(key)
        if current == 1:
            await self.redis.expire(key, window)
        return current <= limit
```

## Monitoring & Observability

### Logging Architecture

**Structured Logging:**
```python
# Logging configuration
LOGGING_CONFIG = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "json": {
            "format": "%(asctime)s %(name)s %(levelname)s %(message)s",
            "class": "pythonjsonlogger.jsonlogger.JsonFormatter"
        }
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "json"
        }
    },
    "loggers": {
        "ardha": {
            "handlers": ["console"],
            "level": "INFO",
            "propagate": False
        }
    }
}
```

**Log Levels:**
- **DEBUG**: Detailed debugging information
- **INFO**: General information messages
- **WARNING**: Warning messages
- **ERROR**: Error messages
- **CRITICAL**: Critical errors

### Metrics Collection

**Key Metrics:**
- API response times (p50, p95, p99)
- Database query performance
- AI token usage and costs
- Cache hit rates
- Error rates by endpoint
- User activity patterns

**Health Checks:**
```python
# Health check endpoints
@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "version": "0.1.0",
        "checks": {
            "database": await check_database(),
            "redis": await check_redis(),
            "qdrant": await check_qdrant()
        }
    }
```

## Deployment Architecture

### Container Strategy

**Docker Compose:**
```yaml
# Multi-container deployment
services:
  backend:
    build: ./backend
    environment:
      - DATABASE_URL=postgresql+asyncpg://...
      - REDIS_URL=redis://redis:6379
    depends_on:
      - postgres
      - redis
      - qdrant

  frontend:
    build: ./frontend
    environment:
      - NEXT_PUBLIC_API_URL=http://localhost:8000
    depends_on:
      - backend

  postgres:
    image: postgres:15-alpine
    environment:
      - POSTGRES_DB=ardha
      - POSTGRES_USER=ardha_user
      - POSTGRES_PASSWORD=ardha_password
    volumes:
      - postgres_data:/var/lib/postgresql/data
```

### Environment Management

**Configuration Strategy:**
- **Development**: Local Docker Compose
- **Staging**: Cloud-based staging environment
- **Production**: Kubernetes cluster
- **Testing**: Isolated test environment

**Environment Variables:**
```bash
# Core configuration
DATABASE_URL=postgresql+asyncpg://...
REDIS_URL=redis://localhost:6379
QDRANT_URL=http://localhost:6333
SECRET_KEY=your-secret-key-here

# AI Configuration
OPENROUTER_API_KEY=your-openrouter-key
AI_BUDGET_DAILY=2.0
AI_BUDGET_MONTHLY=60.0

# OAuth Configuration
GITHUB_CLIENT_ID=your-github-client-id
GITHUB_CLIENT_SECRET=your-github-client-secret
GOOGLE_CLIENT_ID=your-google-client-id
GOOGLE_CLIENT_SECRET=your-google-client-secret
```

## Scalability Architecture

### Horizontal Scaling

**Backend Scaling:**
- Stateless API design
- Load balancer distribution
- Database connection pooling
- Redis cluster for caching
- Container orchestration

**Frontend Scaling:**
- Static asset CDN
- Edge caching
- Progressive loading
- Code splitting
- Service workers

### Database Scaling

**Read Replicas:**
```python
# Read replica configuration
class DatabaseService:
    def __init__(self):
        self.write_db = AsyncSession(write_engine)
        self.read_db = AsyncSession(read_engine)

    async def get_project(self, project_id: str):
        # Use read replica for queries
        return await self.read_db.get(Project, project_id)

    async def create_project(self, project_data: dict):
        # Use primary for writes
        project = Project(**project_data)
        self.write_db.add(project)
        await self.write_db.commit()
        return project
```

**Sharding Strategy:**
- Project-based sharding
- Geographic distribution
- Time-based partitioning
- Hot/cold data separation

## Integration Architecture

### Third-Party Integrations

**GitHub Integration:**
```python
# GitHub API client
class GitHubService:
    def __init__(self, token: str):
        self.client = AsyncGitHubClient(token)

    async def create_pull_request(
        self,
        repo: str,
        title: str,
        head: str,
        base: str
    ) -> dict:
        return await self.client.create_pull_request(
            repo=repo,
            title=title,
            head=head,
            base=base
        )
```

**OAuth Providers:**
- GitHub OAuth App
- Google OAuth 2.0
- Token refresh handling
- Profile synchronization

### API Integration Patterns

**Webhook Processing:**
```python
# Webhook handler
class WebhookService:
    async def handle_github_webhook(self, payload: dict, signature: str):
        # Verify signature
        if not self.verify_signature(payload, signature):
            raise SecurityError("Invalid webhook signature")

        # Process event
        event_type = payload.get("event_type")
        if event_type == "push":
            await self.handle_push_event(payload)
        elif event_type == "pull_request":
            await self.handle_pr_event(payload)
```

**Event-Driven Architecture:**
- Async event processing
- Event sourcing patterns
- CQRS (Command Query Responsibility Segregation)
- Message queues for decoupling

## Testing Architecture

### Test Strategy

**Test Pyramid:**
```
        /\
       /  \  E2E Tests (5%)
      /____\
     /      \    Integration Tests (25%)
    /________\
   /          \ Unit Tests (70%)
  /____________\
```

**Test Categories:**
- **Unit Tests**: Fast, isolated component tests
- **Integration Tests**: API endpoint tests
- **E2E Tests**: Complete workflow tests
- **Performance Tests**: Load and stress testing

### Test Infrastructure

**Testing Tools:**
```python
# Test configuration
@pytest.fixture
async def test_db():
    # Create test database
    engine = create_async_engine(TEST_DATABASE_URL)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # Provide session
    async with AsyncSession(engine) as session:
        yield session

    # Cleanup
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
```

**Test Data Management:**
- Factory patterns for test data
- Database transactions for isolation
- Mock services for external APIs
- Fixtures for common test scenarios

## Future Architecture Plans

### Phase 4: Advanced Features

**Microservices Transition:**
- Service decomposition
- API gateway implementation
- Service mesh for communication
- Distributed tracing

**AI Enhancements:**
- Multi-agent workflows
- Custom model fine-tuning
- Advanced prompt engineering
- Real-time collaboration AI

### Phase 5: Enterprise Features

**Enterprise Architecture:**
- Multi-tenant support
- Advanced security features
- Compliance reporting
- Custom integrations

**Performance Optimizations:**
- GraphQL API implementation
- Advanced caching strategies
- Database optimization
- CDN integration

---

## Architecture Decision Records (ADRs)

### ADR-001: Backend-First Development
**Decision**: Build complete backend API before frontend development
**Status**: Accepted
**Consequences**: Stable API contracts, parallel development, reduced integration issues

### ADR-002: Monorepo Structure
**Decision**: Single repository with backend/ and frontend/ directories
**Status**: Accepted
**Consequences**: Shared configurations, consistent versioning, simplified dependency management

### ADR-003: OpenSpec-Driven Development
**Decision**: All features start with OpenSpec proposals
**Status**: Accepted
**Consequences**: Prevents scope creep, reduces errors, saves tokens

### ADR-004: Project-Based Memory System
**Decision**: Three-tier memory (short/long/organizational)
**Status**: Accepted
**Consequences**: AI learns from history, efficient retrieval, organizational knowledge

### ADR-005: LangGraph for AI Workflows
**Decision**: Use LangGraph instead of naive LLM chaining
**Status**: Accepted
**Consequences**: Deterministic control flow, state persistence, human-in-the-loop

---

**Version**: 1.0
**Last Updated**: November 24, 2024
**Maintained By**: Ardha Development Team
