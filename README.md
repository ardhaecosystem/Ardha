<div align="center">
  <h1>Ardha</h1>
  <p><strong>AI-Native Project Management Platform</strong></p>

  <p>
    <a href="#features">Features</a> •
    <a href="#quick-start">Quick Start</a> •
    <a href="#documentation">Documentation</a> •
    <a href="#contributing">Contributing</a>
  </p>

  <p>
    <img src="https://img.shields.io/badge/License-MIT-blue.svg" alt="License">
    <img src="https://img.shields.io/badge/Python-3.11+-green.svg" alt="Python">
    <img src="https://img.shields.io/badge/FastAPI-0.115+-red.svg" alt="FastAPI">
    <img src="https://img.shields.io/badge/Next.js-15+-black.svg" alt="Next.js">
  </p>
</div>

---

## 🎯 Vision

Ardha transforms project management by integrating AI at every step - from ideation to deployment. Built for developers who want intelligent assistance without sacrificing control.

**Key Differentiators:**
- 🤖 **AI-First Design** - 400+ models via OpenRouter, intelligent workflows
- 🧠 **Semantic Memory** - Local vector database (Qdrant) with zero-cost embeddings
- 📊 **Notion-Style Databases** - Flexible data models with formulas and rollups
- 🔄 **Git Integration** - Automatic task synchronization with commits and PRs
- 🎨 **Real-Time Everything** - WebSocket notifications, live updates
- 💰 **Cost-Conscious** - Local embeddings, prompt caching, budget controls

---

## ✨ Features

### 🤖 AI Integration
- **Multi-Model Support** - GPT-4, Claude, Gemini, Mistral, and 400+ models
- **Intelligent Workflows** - Research, PRD generation, task breakdown
- **Semantic Search** - Find anything using natural language
- **Cost Tracking** - Real-time budget management ($2/day, $60/month limits)
- **Local Embeddings** - Zero-cost semantic memory with sentence-transformers

### 📋 Project Management
- **Tasks** - Linear-inspired task system with dependencies
- **Projects** - Team collaboration with role-based access
- **Milestones** - Track progress with automatic calculations
- **Custom Databases** - Notion-style databases with 11 property types
- **Multiple Views** - Table, Board, Calendar, List, Gallery

### 🔄 Git Integration
- **Automatic Sync** - Tasks linked to commits and PRs
- **Branch Management** - Create, merge, delete branches
- **Commit Intelligence** - AI extracts insights from code changes
- **GitHub Integration** - Create PRs, sync issues, webhooks

### 🔔 Notifications
- **Real-Time** - WebSocket notifications for instant updates
- **Email Digests** - Daily/weekly summaries
- **Smart Preferences** - Quiet hours, per-type controls
- **Broadcast System** - Team-wide announcements

### 🏗️ Architecture
- **FastAPI Backend** - Python 3.11+ with async/await
- **PostgreSQL** - Relational data with optimized indexes
- **Redis** - Caching and Celery broker
- **Qdrant** - Vector database for semantic memory
- **Celery** - Background jobs for heavy operations
- **Next.js Frontend** - React 18 with Server Components

---

## 🚀 Quick Start

**Prerequisites:**
- Docker & Docker Compose (>= 2.20)
- Git

**5-Minute Setup:**
```bash
# 1. Clone repository
git clone https://github.com/ardhaecosystem/Ardha.git
cd Ardha

# 2. Copy environment file
cp backend/.env.example backend/.env

# 3. Start all services
docker-compose up -d

# 4. Run migrations
docker-compose exec backend poetry run alembic upgrade head

# 5. Access application
# Backend API: http://localhost:8000
# API Docs: http://localhost:8000/docs
# Frontend: http://localhost:3000 (when Phase 5 complete)
```

**First Steps:**
1. Create account: `POST /api/v1/auth/register`
2. Login: `POST /api/v1/auth/login`
3. Create project: `POST /api/v1/projects`
4. Start AI chat: `POST /api/v1/chats`

---

## 📚 Documentation

### Core Documentation
- [**Architecture**](docs/ARCHITECTURE.md) - System design and technical overview
- [**Setup Guide**](docs/SETUP.md) - Installation and configuration
- [**API Reference**](docs/API_REFERENCE.md) - Complete API documentation
- [**Development Guide**](docs/DEVELOPMENT.md) - Contributing to Ardha
- [**Testing Guide**](docs/TESTING.md) - Testing strategies and practices
- [**Security Policy**](docs/SECURITY.md) - Security considerations and policies
- [**Contributing**](docs/CONTRIBUTING.md) - How to contribute
- [**Changelog**](docs/CHANGELOG.md) - Version history and changes

### Feature Guides
- [**Authentication System**](docs/guides/authentication.md) - User management and OAuth
- [**AI Integration**](docs/guides/ai-integration.md) - AI workflows and models
- [**Database System**](docs/guides/database-system.md) - Notion-style databases
- [**Git Integration**](docs/guides/git-integration.md) - Version control integration
- [**Notifications**](docs/guides/notifications.md) - Real-time notifications
- [**Background Jobs**](docs/guides/background-jobs.md) - Celery task processing

### API Documentation
- [**Authentication API**](docs/api/auth-api.md) - User authentication endpoints
- [**Project API**](docs/api/project-api.md) - Project management endpoints
- [**Task API**](docs/api/task-api.md) - Task management endpoints
- [**Chat API**](docs/api/chat-api.md) - AI chat endpoints
- [**Workflow API**](docs/api/workflow-api.md) - AI workflow endpoints
- [**OpenSpec API**](docs/api/openspec-api.md) - Specification management

---

## 🏗️ Architecture

### High-Level System Design

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

### Key Technologies

**Backend Stack:**
- **FastAPI 0.115** - Modern async web framework
- **PostgreSQL 15** - Primary relational database
- **Qdrant 1.7** - Vector database for semantic search
- **Redis 7.2** - Caching and message broker
- **Celery 5.4** - Background task processing
- **LangGraph 0.2** - AI workflow orchestration

**Frontend Stack:**
- **Next.js 15** - React framework with App Router
- **React 19 RC** - UI library with Server Components
- **TypeScript 5.6** - Type safety
- **Tailwind CSS 3.4** - Utility-first styling
- **Radix UI** - Accessible component primitives

**AI/ML Stack:**
- **OpenRouter** - 400+ AI model access
- **LangChain 0.3** - LLM framework
- **Sentence Transformers** - Local embeddings
- **OpenAI SDK** - Model client compatibility

---

## 🤖 AI Workflows

Ardha features sophisticated AI workflows powered by LangGraph:

### Research Mode
- Market research and competitive analysis
- Technology stack recommendations
- Feasibility studies and risk assessment

### Architect Mode
- Product Requirements Document (PRD) generation
- System architecture design
- Technical specifications

### Implementation Mode
- Code generation and implementation
- Task breakdown and estimation
- Automated testing and debugging

### Debug Mode
- Error analysis and resolution
- Performance optimization
- Code review and quality checks

### Chat Mode
- General assistance and Q&A
- Project-specific context
- Real-time collaboration

---

## 📊 Database System

Ardha includes a powerful Notion-style database system:

### Property Types
- **Text** - Rich text with validation
- **Number** - Numeric values with formatting
- **Date** - Date/datetime with time zones
- **Select** - Predefined options with colors
- **Formula** - Calculated values with expressions
- **Rollup** - Aggregated values from relations
- **Relation** - Links between databases

### View Types
- **Table** - Spreadsheet-like grid view
- **Board** - Kanban-style card layout
- **List** - Compact list view
- **Calendar** - Date-based calendar view
- **Gallery** - Visual card grid

---

## 🔄 Git Integration

Comprehensive Git integration bridges version control with project management:

### Features
- **Repository Management** - Initialize, clone, and manage repos
- **Commit Tracking** - Automatic task linking from commits
- **Branch Operations** - Create, switch, and manage branches
- **Remote Sync** - Push/pull with conflict resolution
- **Task Integration** - Automatic status updates from commits

### Task Linking
- Support for multiple task ID formats (TAS-001, #123, ARD-001)
- Automatic task closure via commit messages
- Commit-to-task relationship tracking
- Activity logging and progress updates

---

## 🔐 Security

### Authentication & Authorization
- **JWT Tokens** - Secure token-based authentication
- **OAuth Integration** - GitHub and Google login support
- **Role-Based Access Control** - Granular permissions (Viewer, Member, Admin, Owner)
- **Session Management** - Secure session handling with refresh tokens

### Data Protection
- **Encryption** - Data encryption at rest and in transit
- **Input Validation** - Comprehensive input sanitization
- **SQL Injection Prevention** - Parameterized queries
- **XSS Protection** - Content Security Policy and sanitization

### Infrastructure Security
- **Container Security** - Minimal Docker images
- **Network Isolation** - Secure network configuration
- **Secret Management** - Environment-based configuration
- **Audit Logging** - Complete audit trails

---

## 📈 Performance

### Optimization Strategies
- **Database Indexing** - Strategic indexes for optimal queries
- **Caching Layer** - Redis caching for frequent operations
- **Async Operations** - Non-blocking I/O throughout
- **Connection Pooling** - Optimized database connections
- **CDN Integration** - Static asset delivery

### Monitoring & Metrics
- **Application Performance** - Response time tracking
- **Database Performance** - Query optimization
- **AI Usage** - Token and cost monitoring
- **Error Tracking** - Comprehensive error logging
- **Health Checks** - System health monitoring

---

## 🧪 Testing

### Test Coverage
- **Unit Tests** - 80%+ coverage on core components
- **Integration Tests** - API endpoint testing
- **End-to-End Tests** - Complete workflow testing
- **Performance Tests** - Load and stress testing
- **Security Tests** - Vulnerability scanning

### Testing Tools
- **Pytest** - Python testing framework
- **Jest** - JavaScript testing framework
- **Playwright** - E2E testing
- **Locust** - Load testing
- **Bandit** - Security scanning

---

## 🚀 Deployment

### Development Environment
```bash
# Local development
docker-compose up -d
poetry install  # Backend dependencies
pnpm install   # Frontend dependencies
```

### Production Deployment
- **Docker Containers** - Containerized deployment
- **Kubernetes** - Orchestration support
- **CI/CD Pipeline** - Automated testing and deployment
- **Environment Management** - Multi-environment support
- **Monitoring** - Production monitoring and alerting

---

## 🤝 Contributing

We welcome contributions from the community! See our [Contributing Guide](docs/CONTRIBUTING.md) for details.

### How to Contribute
1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

### Development Areas
- **Backend Development** - FastAPI, PostgreSQL, AI workflows
- **Frontend Development** - Next.js, React, UI components
- **AI/ML** - Workflow design, prompt engineering
- **Documentation** - Guides, API docs, tutorials
- **Testing** - Test coverage, quality assurance

---

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

## 🙏 Acknowledgments

- **OpenAI** - For the GPT models and API
- **Anthropic** - For Claude models
- **Google** - For Gemini models
- **FastAPI** - Excellent web framework
- **Next.js** - Amazing React framework
- **PostgreSQL** - Reliable database
- **Qdrant** - Vector database
- **Redis** - In-memory data store

---

## 📞 Support

### Documentation
- [Documentation](docs/) - Complete documentation
- [API Reference](docs/api/) - API endpoint documentation
- [Guides](docs/guides/) - Step-by-step guides

### Community
- [GitHub Discussions](https://github.com/ardhaecosystem/Ardha/discussions) - Community forum
- [Discord](https://discord.gg/ardha) - Real-time chat
- [Stack Overflow](https://stackoverflow.com/questions/tagged/ardha) - Q&A

### Issues & Support
- [GitHub Issues](https://github.com/ardhaecosystem/Ardha/issues) - Bug reports
- [Feature Requests](https://github.com/ardhaecosystem/Ardha/discussions/categories/feature-requests) - Feature suggestions
- [Security Issues](https://github.com/ardhaecosystem/Ardha/security) - Security concerns

---

## 🗺️ Roadmap

### Phase 1: Backend Foundation ✅
- [x] FastAPI backend with PostgreSQL
- [x] Authentication and authorization
- [x] Project and task management
- [x] AI integration with LangGraph
- [x] Git integration

### Phase 2: Documentation ✅
- [x] Comprehensive documentation
- [x] API reference
- [x] Development guides
- [x] Deployment instructions

### Phase 3: Frontend Development 🚧
- [ ] Next.js frontend with React 19
- [ ] Real-time WebSocket integration
- [ ] AI chat interface
- [ ] Project management UI

### Phase 4: Advanced Features 📋
- [ ] GitHub API integration
- [ ] Advanced analytics
- [ ] Mobile applications
- [ ] Enterprise features

### Phase 5: Ecosystem 🎯
- [ ] Plugin marketplace
- [ ] Third-party integrations
- [ ] Community templates
- [ ] Open-source ecosystem

---

<div align="center">
  <p><strong>Built with ❤️ by the Ardha team</strong></p>
  <p><em>Transforming project management with AI</em></p>
</div>
