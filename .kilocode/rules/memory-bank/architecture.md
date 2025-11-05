# Ardha System Architecture

## High-Level Architecture

Ardha follows a modern web application architecture with three primary layers:

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

## System Constraints (8GB RAM Total)

**Critical Memory Limits:**
- PostgreSQL: 2GB container limit
- Qdrant: 2.5GB limit (scalar quantization enabled)
- Redis: 512MB limit (LRU eviction policy)
- Backend: 2GB container limit
- Frontend: 1GB container limit

## Source Code Structure

### Backend (`/home/veda/ardha-projects/Ardha/backend/src/ardha/`)

**Planned Directory Structure:**
```
backend/src/ardha/
├── __init__.py
├── main.py                    # FastAPI app entry point
│
├── api/                       # API layer
│   ├── __init__.py
│   ├── routes/               # API endpoints
│   │   ├── auth.py          # Authentication routes
│   │   ├── projects.py      # Project CRUD
│   │   ├── tasks.py         # Task CRUD
│   │   ├── chat.py          # Chat endpoints
│   │   ├── files.py         # File operations
│   │   ├── git.py           # Git operations
│   │   ├── openspec.py      # OpenSpec proposals
│   │   ├── databases.py     # Notion-style databases
│   │   └── ai.py            # AI model selection
│   └── dependencies.py       # FastAPI dependencies
│
├── core/                      # Core utilities
│   ├── config.py             # Pydantic settings
│   ├── security.py           # JWT, OAuth, hashing
│   ├── exceptions.py         # Custom exceptions
│   └── logging.py            # Structured logging
│
├── db/                        # Database layer
│   ├── base.py               # SQLAlchemy base
│   ├── session.py            # Database sessions
│   └── init_db.py            # Database initialization
│
├── models/                    # SQLAlchemy models
│   ├── user.py               # User, OAuth
│   ├── project.py            # Project, ProjectMember
│   ├── task.py               # Task, TaskDependency
│   ├── chat.py               # Chat, Message
│   ├── file.py               # File
│   ├── milestone.py          # Milestone
│   ├── openspec.py           # OpenSpecProposal
│   ├── database.py           # Database, Property, Entry
│   └── notification.py       # Notification
│
├── schemas/                   # Pydantic schemas
│   ├── requests/             # Request models
│   │   ├── auth.py
│   │   ├── project.py
│   │   ├── task.py
│   │   └── ...
│   └── responses/            # Response models
│       ├── auth.py
│       ├── project.py
│       ├── task.py
│       └── ...
│
├── services/                  # Business logic
│   ├── ai_service.py         # OpenRouter client
│   ├── langgraph_service.py  # Workflow orchestration
│   ├── memory_service.py     # Qdrant operations
│   ├── embedding_service.py  # Text → vectors
│   ├── openspec_service.py   # OpenSpec parsing
│   ├── git_service.py        # Git operations
│   ├── github_service.py     # GitHub API
│   ├── file_service.py       # File CRUD
│   ├── notification_service.py # Notifications
│   ├── email_service.py      # Email sending
│   └── websocket_manager.py  # WebSocket connections
│
├── workflows/                 # LangGraph workflows
│   ├── research.py           # Idea → Research
│   ├── prd_generation.py     # Research → PRD
│   ├── task_generation.py    # PRD → Tasks
│   ├── implementation.py     # Tasks → Code
│   └── state.py              # Shared workflow state
│
├── migrations/                # Alembic migrations
│   ├── env.py
│   ├── script.py.mako
│   └── versions/
│
└── tests/                     # Test suite
    ├── unit/
    ├── integration/
    └── conftest.py
```

### Frontend (`/home/veda/ardha-projects/Ardha/frontend/src/`)

**Planned Directory Structure:**
```
frontend/src/
├── app/                       # Next.js App Router
│   ├── layout.tsx            # Root layout with theme
│   ├── page.tsx              # Home/landing page
│   │
│   ├── auth/                 # Authentication pages
│   │   ├── login/
│   │   ├── register/
│   │   └── forgot-password/
│   │
│   ├── dashboard/            # Main dashboard
│   │   └── page.tsx
│   │
│   ├── projects/             # Project management
│   │   ├── page.tsx          # Projects list
│   │   └── [id]/             # Project detail
│   │       ├── page.tsx      # Overview
│   │       ├── tasks/
│   │       ├── board/
│   │       ├── calendar/
│   │       ├── timeline/
│   │       ├── chat/         # Project chat
│   │       ├── files/
│   │       ├── git/
│   │       ├── openspec/
│   │       └── settings/
│   │
│   ├── chat/                 # Normal chat
│   │   └── page.tsx
│   │
│   └── settings/             # User settings
│       └── page.tsx
│
├── components/                # React components
│   ├── ui/                   # Base UI components
│   │   ├── button.tsx
│   │   ├── input.tsx
│   │   ├── dialog.tsx
│   │   ├── dropdown.tsx
│   │   ├── toast.tsx
│   │   └── ...
│   │
│   ├── layouts/              # Layout components
│   │   ├── app-layout.tsx
│   │   ├── sidebar.tsx
│   │   ├── header.tsx
│   │   └── command-palette.tsx
│   │
│   ├── forms/                # Form components
│   │   ├── login-form.tsx
│   │   ├── task-form.tsx
│   │   └── ...
│   │
│   ├── task/                 # Task components
│   │   ├── task-board.tsx
│   │   ├── task-card.tsx
│   │   ├── task-detail.tsx
│   │   └── task-list.tsx
│   │
│   ├── chat/                 # Chat components
│   │   ├── chat-message.tsx
│   │   ├── chat-input.tsx
│   │   └── chat-history.tsx
│   │
│   ├── editor/               # Code editor
│   │   ├── code-editor.tsx
│   │   ├── file-tree.tsx
│   │   └── terminal.tsx
│   │
│   └── database/             # Database components
│       ├── database-view.tsx
│       ├── database-table.tsx
│       └── property-editor.tsx
│
├── lib/                       # Utilities and helpers
│   ├── api/                  # API client
│   │   ├── client.ts         # Base API client
│   │   ├── auth.ts
│   │   ├── projects.ts
│   │   ├── tasks.ts
│   │   └── ...
│   │
│   ├── hooks/                # Custom React hooks
│   │   ├── use-auth.ts
│   │   ├── use-websocket.ts
│   │   ├── use-theme.ts
│   │   └── ...
│   │
│   ├── stores/               # Zustand stores
│   │   ├── auth-store.ts
│   │   ├── project-store.ts
│   │   └── ui-store.ts
│   │
│   └── utils/                # Utility functions
│       ├── cn.ts             # className merger
│       ├── format.ts
│       └── validation.ts
│
├── styles/                    # Global styles
│   └── globals.css           # Tailwind + custom CSS
│
└── types/                     # TypeScript types
    ├── api.ts                # API response types
    ├── models.ts             # Data model types
    └── ui.ts                 # UI component types
```

## Key Architectural Decisions

### 1. Backend-First Development Strategy
**Decision**: Build complete backend API before frontend development  
**Rationale**:
- Stable API contracts enable parallel development
- Faster debugging with direct API testing
- Frontend can use mock data until backend ready
- Reduces integration issues

**Implementation**:
- Define all endpoints in OpenAPI spec first
- Implement with 100% test coverage
- Document with examples
- Frontend team starts after Week 3

### 2. Monorepo Structure
**Decision**: Single repository with backend/ and frontend/ directories  
**Rationale**:
- Shared configurations and tooling
- Consistent versioning
- Simplified dependency management
- Easier to maintain

**Implementation**:
- Shared caches (.poetry-cache/, .pnpm-store/)
- Root .gitignore for all exclusions
- Independent package managers (Poetry, pnpm)

### 3. OpenSpec-Driven Development
**Decision**: All features start with OpenSpec proposals  
**Rationale**:
- Prevents "vibe coding" and scope creep
- 59% fewer errors in implementation
- Saves 100K-200K tokens per feature
- Clear approval gates

**Implementation**:
- Proposals in openspec/changes/
- Visual UI for review (not just markdown)
- Auto-sync tasks to PostgreSQL
- Archive when complete

### 4. Project-Based Memory System
**Decision**: Three-tier memory (short/long/organizational)  
**Rationale**:
- AI learns from project history
- Context retrieval efficiency
- Organizational knowledge compounds
- Enables ACE framework

**Implementation**:
- Short-term: Redis (1-2 hours)
- Long-term: Qdrant vectors (permanent per project)
- Organizational: Qdrant (cross-project patterns)

### 5. LangGraph for AI Workflows
**Decision**: Use LangGraph instead of naive LLM chaining  
**Rationale**:
- Deterministic control flow
- State persistence for resumption
- Human-in-the-loop approval gates
- No "prompt spaghetti"

**Implementation**:
- Workflows as directed graphs
- Pure functions as nodes
- State stored in PostgreSQL
- Streaming updates via WebSocket

### 6. Complexity-Based Model Routing
**Decision**: Auto-select AI model based on task complexity  
**Rationale**:
- Cost optimization (simple tasks use cheap models)
- Quality for complex tasks
- Budget control
- Transparent to user

**Implementation**:
- Simple: Gemini Flash (~35%)
- Medium: Claude Sonnet 4.5 (~45%)
- Complex: Claude Opus 4.1 (~20%)
- User can override manually

### 7. Prompt Caching Strategy
**Decision**: Mark large static context as cacheable  
**Rationale**:
- 90% cost reduction on cached content
- 5-minute cache duration
- Massive savings on project context

**Implementation**:
- Cache project files, specs, docs
- Auto cache warming for active projects
- Hierarchical context loading (5-15K vs 150-300K tokens)

### 8. Real-Time Collaboration (WebSocket)
**Decision**: WebSocket for all real-time updates  
**Rationale**:
- Instant sync across users
- Live code sharing in project chat
- Real-time task updates from commits
- Collaborative editing support

**Implementation**:
- WebSocket manager in backend
- Client reconnection logic
- Optimistic UI updates
- Conflict resolution (last-write-wins)

## Component Relationships

### Authentication Flow
```
User → Frontend Login → JWT Token → Backend Auth
                                    ↓
                                PostgreSQL (verify)
                                    ↓
                                Access Token (15min)
                                Refresh Token (7 days)
```

### AI Workflow (Idea → Implementation)
```
User Idea → Research Mode (LangGraph)
              ↓
        PRD Generation (LangGraph)
              ↓
        Task Generation (OpenSpec)
              ↓
        Human Approval ←──────────┐
              ↓                    │
        Implementation Mode         │
              ↓                    │
        Code + Commits             │
              ↓                    │
        Tests + Review              │
              ↓                    │
        GitHub PR                  │
              ↓                    │
        Merge & Archive ───────────┘
```

### Memory Ingestion Pipeline
```
Chat Message → Summarize → Extract Decisions → Embed
                                                 ↓
                                             Qdrant
                                                 
Commit → Generate Explanation → Extract Patterns → Embed
                                                      ↓
                                                  Qdrant
```

### Database Query Path
```
Frontend → API Request → FastAPI Route
              ↓
        SQLAlchemy Service
              ↓
        PostgreSQL Query
              ↓
        Pydantic Response
              ↓
        Frontend Update
```

## Critical Implementation Paths

### Path 1: User Registration
1. Frontend: `app/auth/register/page.tsx` → Registration form
2. API: `POST /api/v1/auth/register`
3. Backend: `api/routes/auth.py` → Validation
4. Service: `services/auth_service.py` → Hash password
5. Model: `models/user.py` → Create user
6. PostgreSQL: Insert user record
7. Response: JWT tokens
8. Frontend: Redirect to dashboard

### Path 2: AI Chat Message
1. Frontend: `components/chat/chat-input.tsx` → Send message
2. WebSocket: Connect to `/api/v1/chats/{id}/ws`
3. Backend: `services/websocket_manager.py` → Receive
4. Service: `services/ai_service.py` → OpenRouter API
5. LangGraph: Workflow orchestration (if needed)
6. Stream: Response chunks via WebSocket
7. Memory: `services/memory_service.py` → Ingest to Qdrant
8. Frontend: Display in `components/chat/chat-message.tsx`

### Path 3: Git Commit → Task Update
1. Backend: `services/git_service.py` → Detect commit
2. Parser: Extract task IDs from commit message
3. Model: `models/task.py` → Update task status
4. OpenSpec: Update task status in markdown
5. WebSocket: Broadcast update to all viewers
6. Frontend: Real-time task card update

### Path 4: OpenSpec Proposal → Implementation
1. AI: Generate proposal files (proposal.md, tasks.md, spec-delta.md)
2. Backend: `services/openspec_service.py` → Parse markdown
3. Model: `models/openspec.py` → Store proposal
4. Frontend: `app/projects/[id]/openspec/page.tsx` → Display
5. User: Review and approve
6. Service: `services/task_service.py` → Sync tasks to PostgreSQL
7. WebSocket: Broadcast new tasks
8. Frontend: Tasks appear in board view

## Performance Optimization Strategies

### Database Optimization
- PostgreSQL connection pooling (max 20 connections)
- Query optimization (N+1 prevention)
- Strategic indexes on foreign keys, search fields
- Materialized views for complex queries
- Query result caching in Redis

### Frontend Optimization
- Code splitting (route-based)
- Lazy loading for heavy components
- Virtual scrolling for large lists
- Image optimization (Next.js Image)
- Bundle size monitoring (<200KB gzipped)

### AI Cost Optimization
- Prompt caching (90% reduction)
- Model routing by complexity
- Context hierarchy (load only needed)
- Batch processing where possible
- Hard budget limits ($60/month)

### Memory Management
- Qdrant scalar quantization (40% reduction)
- Redis LRU eviction
- PostgreSQL shared_buffers tuning
- Container memory limits enforced
- Graceful degradation on limits

## Security Architecture

### Authentication
- JWT access tokens (15min, in-memory)
- Refresh tokens (7 days, httpOnly cookie)
- Token rotation on refresh
- OAuth2 for GitHub, Google

### Authorization
- Role-based access control (RBAC)
- Project-level permissions
- API endpoint guards
- Row-level security in PostgreSQL

### Data Protection
- Environment variables for secrets
- Password hashing (bcrypt, cost 12)
- SQL injection prevention (ORM)
- XSS prevention (sanitization)
- CORS configuration
- Rate limiting (100 req/min per user)

## Deployment Architecture

### Development
- Docker Compose locally
- Hot reload for backend/frontend
- Test databases (separate from prod)

### Production (Future)
- Load balancer (Caddy)
- Multiple app servers
- Database replication
- Redis Sentinel (HA)
- Qdrant cluster
- CDN for static assets (Cloudflare)
- Monitoring (Prometheus + Grafana)
- Logging (Loki)

## Next Architecture Decisions Needed

1. **Caching Strategy**: Define what to cache and for how long
2. **Search Implementation**: PostgreSQL full-text vs Elasticsearch
3. **File Storage**: Local filesystem vs S3-compatible
4. **Background Jobs**: Celery task priorities and queues
5. **Testing Strategy**: Integration test database seeding approach
6. **Monitoring**: What metrics to track and alert on
7. **Backup Strategy**: Frequency and retention policies