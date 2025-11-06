# Ardha Monorepo Navigation Rules

> **Purpose**: Establish clear package boundaries and prevent wasteful context loading in AI-assisted development.
> 
> **Why This Matters**: Without these rules, AI loads the entire 50K+ LOC monorepo (150K-300K tokens) on every request. With these rules, AI loads only relevant context (5-15K tokens) - **saving 95% of tokens!**
>
> **Open-Source Note**: These rules demonstrate best practices for AI-assisted monorepo development. Feel free to adapt for your own projects!

---

## 🏗️ Ardha Monorepo Structure

Ardha follows a **clean monorepo architecture** with strict package boundaries:

```
Ardha/
├── backend/          # Python/FastAPI API server (40+ files)
├── frontend/         # Next.js/React web app (60+ files)
├── openspec/         # Specifications (living documentation)
└── .kilocode/        # AI development rules and memory bank
```

---

## 🚫 Critical Dependency Rules

### **Package Isolation Principle**

Each package is **self-contained** with minimal cross-dependencies:

**Frontend → Shared**
- ✅ Can import: Type definitions from `@ardha/shared-types` (if exists)
- ❌ Cannot import: Backend implementation code
- ❌ Cannot import: Backend services, models, or repositories

**Backend → Shared**
- ✅ Can import: Type definitions from `@ardha/shared-types` (if exists)
- ❌ Cannot import: Frontend components or pages
- ❌ Cannot import: Frontend hooks or utilities

**Mobile (Future) → Shared**
- ✅ Can import: Type definitions only
- ❌ Cannot import: Backend or Frontend implementation

### **Why This Matters**

Cross-package imports create:
- 🐛 Deployment complexity (backend depends on frontend build)
- 📦 Bundle size bloat (frontend includes backend code)
- 🔄 Circular dependencies
- 💰 Token waste (AI loads unnecessary context)

---

## 📋 When Working in One Package

### **Backend Development Tasks**

When implementing backend features (API endpoints, database models, services):

**ONLY load files from:**
1. ✅ `backend/` directory (current package)
2. ✅ `openspec/project.md` (project-wide conventions)
3. ✅ Root-level configs: `pyproject.toml`, `.env.example`

**DO NOT load:**
- ❌ `frontend/` directory files
- ❌ Frontend `package.json` or `pnpm-lock.yaml`
- ❌ Frontend components, pages, or hooks

**Example Context Loading:**
```
Working on: User authentication API endpoint

Load:
- backend/src/ardha/api/routes/auth.py (if exists)
- backend/src/ardha/services/auth_service.py (if exists)
- backend/src/ardha/models/user.py
- openspec/project.md (conventions)

Do NOT load:
- frontend/src/app/(auth)/login/page.tsx
- frontend/src/components/LoginForm.tsx
```

---

### **Frontend Development Tasks**

When implementing frontend features (pages, components, UI):

**ONLY load files from:**
1. ✅ `frontend/` directory (current package)
2. ✅ `openspec/project.md` (project-wide conventions)
3. ✅ Root-level configs: `package.json`, `tailwind.config.ts`

**DO NOT load:**
- ❌ `backend/` directory files
- ❌ Backend `pyproject.toml` or `poetry.lock`
- ❌ Backend services, models, or repositories

**Example Context Loading:**
```
Working on: Login page component

Load:
- frontend/src/app/(auth)/login/page.tsx
- frontend/src/components/ui/button.tsx
- frontend/src/lib/api/auth.ts (API client)
- openspec/project.md (design system)

Do NOT load:
- backend/src/ardha/api/routes/auth.py
- backend/src/ardha/services/auth_service.py
```

---

## 🔗 Cross-Package Coordination

### **When Changes Affect Multiple Packages**

Some features span both backend and frontend (e.g., new API endpoint + UI to consume it):

**Workflow:**
1. **Backend First** (API-first design philosophy):
   - Design API contract (OpenAPI specification)
   - Implement backend endpoint
   - Write backend tests
   - Commit and push

2. **Frontend Second** (develops against stable API):
   - Create API client types (based on OpenAPI spec)
   - Implement frontend component
   - Write frontend tests
   - Commit and push

**Context Loading Strategy:**
- When working on **backend**, load only backend files
- When working on **frontend**, load only frontend files
- **Never load both simultaneously** unless reviewing API contract alignment

### **API Contract as Bridge**

The **OpenAPI specification** is the single source of truth connecting packages:

```
Backend OpenAPI Spec (source of truth)
         ↓
    openapi.json
         ↓
Frontend API Client (auto-generated types)
```

**When reviewing API contracts**, you may load:
- ✅ `backend/openapi.json` or endpoint decorator
- ✅ `frontend/src/lib/api/types.ts` (generated types)
- ✅ **Purpose**: Verify alignment only, not implementation

---

## 📚 OpenSpec Integration

### **When Creating OpenSpec Proposals**

OpenSpec change proposals may affect one or both packages:

**Single-Package Changes:**
```
openspec/changes/add-user-profile-api/
├── proposal.md
├── tasks.md
└── specs/
    └── backend/
        └── user-profile-spec.md
```
**Context Loading**: Load only backend/ files

**Multi-Package Changes:**
```
openspec/changes/add-chat-interface/
├── proposal.md
├── tasks.md
└── specs/
    ├── backend/
    │   └── chat-api-spec.md
    └── frontend/
        └── chat-ui-spec.md
```
**Context Loading**: 
- During backend tasks: Load only backend/ files
- During frontend tasks: Load only frontend/ files
- During proposal review: Load specs only (no implementation)

---

## ⚡ Context Loading Efficiency

### **Token Budget Comparison**

**WITHOUT these rules:**
```
Request: "Implement login API endpoint"

AI loads:
- backend/ (30 files, ~70K tokens)
- frontend/ (50 files, ~120K tokens)
- openspec/ (10 files, ~30K tokens)
Total: ~220K tokens
Cost: $0.66 per request (Claude Sonnet 4.5)
```

**WITH these rules:**
```
Request: "Implement login API endpoint"

AI loads:
- backend/api/routes/auth.py (~2K tokens)
- backend/services/auth_service.py (~3K tokens)
- backend/models/user.py (~2K tokens)
- openspec/project.md (cached, ~1K tokens)
Total: ~8K tokens
Cost: $0.024 per request (Claude Sonnet 4.5 with caching)
```

**Savings: 96% fewer tokens, 27x cheaper!**

---

## 🎯 Decision Tree for File Selection

Use this decision tree when AI asks "What files should I load?"

```
┌─────────────────────────────────────┐
│ What package does the task affect?  │
└─────────┬───────────────────────────┘
          │
    ┌─────┴─────┐
    ▼           ▼
┌────────┐  ┌──────────┐
│Backend │  │ Frontend │
└───┬────┘  └────┬─────┘
    │            │
    ▼            ▼
┌────────────┐ ┌─────────────┐
│Load ONLY:  │ │Load ONLY:   │
│- backend/  │ │- frontend/  │
│- openspec/ │ │- openspec/  │
│- root      │ │- root       │
│  configs   │ │  configs    │
└────────────┘ └─────────────┘
```

**Both packages?** → Work sequentially:
1. Complete backend changes first
2. Start NEW task for frontend changes
3. Load only relevant package each time

---

## 🔍 Package Detection

### **Automatic Package Detection from File Paths**

AI should detect the working package from file paths:

**Backend indicators:**
- File path contains: `backend/`, `src/ardha/`, `.py` extension
- Commands reference: `poetry`, `pytest`, `uvicorn`, `alembic`
- Imports reference: `fastapi`, `sqlalchemy`, `pydantic`

**Frontend indicators:**
- File path contains: `frontend/`, `src/app/`, `.tsx`, `.ts` extension
- Commands reference: `pnpm`, `next`, `npm`
- Imports reference: `react`, `next`, `@radix-ui`

**OpenSpec indicators:**
- File path contains: `openspec/`, `changes/`, `specs/`
- Working on proposals, specs, or task lists

---

## 📖 Examples for AI Community

### **Example 1: Backend API Endpoint**

**Task**: "Add password reset endpoint to auth API"

**Correct Context Loading:**
```
✅ backend/src/ardha/api/routes/auth.py
✅ backend/src/ardha/services/auth_service.py
✅ backend/src/ardha/models/user.py
✅ backend/src/ardha/schemas/requests/auth.py
✅ openspec/project.md (security requirements)
```

**Incorrect Context Loading:**
```
❌ frontend/src/app/(auth)/reset-password/page.tsx
❌ frontend/src/components/PasswordResetForm.tsx
❌ ALL other backend files (just load what's needed!)
```

---

### **Example 2: Frontend Component**

**Task**: "Create a reusable button component with variants"

**Correct Context Loading:**
```
✅ frontend/src/components/ui/button.tsx (if exists, to extend)
✅ frontend/tailwind.config.ts (design tokens)
✅ openspec/project.md (design system: colors, spacing)
```

**Incorrect Context Loading:**
```
❌ backend/ (any files)
❌ ALL other frontend components (just load similar component if needed)
```

---

### **Example 3: Full-Stack Feature**

**Task**: "Implement user profile feature (API + UI)"

**Correct Workflow:**
```
Session 1 - Backend:
✅ Load only backend/ files
✅ Implement API endpoints
✅ Commit changes

Session 2 - Frontend:
✅ Load only frontend/ files
✅ Implement UI components
✅ Commit changes
```

**Incorrect Workflow:**
```
❌ Load both backend/ and frontend/ simultaneously
❌ Try to implement both in one session
❌ Mix backend and frontend file references
```

---

## 🛡️ Validation Checklist

Before processing any task, AI should validate:

- [ ] Have I identified which package this task affects?
- [ ] Am I loading ONLY files from that package?
- [ ] Have I excluded the other package's files?
- [ ] Am I loading the minimum necessary files (max 3-4)?
- [ ] Have I checked openspec/project.md for conventions?

**If any answer is "no", stop and re-evaluate file selection!**

---

## 🌟 Community Contribution

These rules are part of **Ardha's commitment to open-source excellence**. We're demonstrating:

✨ **Token-efficient AI development** - How to stay within budget constraints  
✨ **Monorepo best practices** - Clear boundaries prevent architectural drift  
✨ **Reproducible workflows** - Other projects can adapt these rules  
✨ **Transparent AI usage** - Every decision documented and explainable

**Learn more about Ardha**: https://github.com/ardhaecosystem/Ardha

---

## 📚 Further Reading

- **Kilo Code Memory Bank**: https://kilocode.ai/docs/advanced-usage/memory-bank
- **OpenSpec Documentation**: https://github.com/Fission-AI/OpenSpec
- **Ardha PRD**: `openspec/project.md`
- **Architecture Details**: `.kilocode/rules/memory-bank/architecture.md`

---

**Version**: 1.0  
**Last Updated**: November 5, 2025  
**Maintained By**: Ardha Development Team  
**License**: MIT (Open Source)
