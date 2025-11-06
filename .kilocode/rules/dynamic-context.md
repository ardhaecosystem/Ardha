# Ardha Dynamic Context Loading

> **Purpose**: Automatically detect task type and load appropriate context without user intervention.
>
> **Why This Matters**: Manual file selection is tedious and error-prone. Automated detection ensures correct context every time while maintaining token efficiency.
>
> **Open-Source Note**: This demonstrates advanced AI prompt engineering - teaching AI to make intelligent decisions about what context it needs!

---

## 🎯 Automatic Task Type Detection

**The Goal**: AI analyzes user request and automatically determines:
1. Which package is affected (backend / frontend / both)
2. What type of task it is (API / UI / database / debugging)
3. Which files to load (3-4 maximum)

**No Manual Intervention Required!**

---

## 🔍 Detection Patterns

### **Pattern 1: Keyword Detection**

**Backend Task Indicators:**
```
Keywords in user request:
- "API endpoint", "route", "REST API"
- "database", "model", "migration"
- "service", "repository", "business logic"
- "FastAPI", "SQLAlchemy", "Pydantic"
- "pytest", "test backend"

Action: Load backend context only
```

**Frontend Task Indicators:**
```
Keywords in user request:
- "component", "page", "UI", "interface"
- "form", "button", "modal", "dialog"
- "Next.js", "React", "Tailwind"
- "styling", "layout", "responsive"
- "Vitest", "test component"

Action: Load frontend context only
```

**Full-Stack Indicators:**
```
Keywords in user request:
- "full-stack feature"
- "API and UI"
- "backend and frontend"
- "end-to-end"

Action: Work sequentially (backend first, then frontend)
```

---

### **Pattern 2: File Path Detection**

**Automatic Package Detection from Mentions:**

```python
# If user mentions file paths:
"Update backend/src/ardha/api/routes/users.py"
→ Detected: Backend task
→ Load: backend context only

"Fix frontend/src/app/dashboard/page.tsx"
→ Detected: Frontend task
→ Load: frontend context only

"Both backend/services/user.py and frontend/components/UserProfile.tsx"
→ Detected: Full-stack task
→ Strategy: Sequential sessions (backend → frontend)
```

---

### **Pattern 3: Technology Stack Detection**

**Backend Technologies Mentioned:**
```
Python, FastAPI, Pydantic, SQLAlchemy, Alembic,
PostgreSQL, Redis, Qdrant, LangChain, pytest

→ Backend task
```

**Frontend Technologies Mentioned:**
```
TypeScript, Next.js, React, Tailwind, shadcn/ui,
Radix, Zustand, SWR, TanStack Query, Vitest

→ Frontend task
```

---

## 📋 Task Type Classification

### **Backend Task Types**

#### **Type 1: API Endpoint (New or Modification)**

**Detection:**
```
User request contains:
- "create endpoint", "add API", "new route"
- "modify endpoint", "update API"
- HTTP methods: "GET", "POST", "PUT", "DELETE"
- "/api/", "/users", "/projects" (URL paths)
```

**Context Loading:**
```yaml
Tier 1: brief.md, project.md (cached)
Tier 2: architecture.md (backend), backend-patterns.md (cached)
Tier 3:
  - Similar existing route (reference pattern)
  - Related service (business logic)
  - Related model (if database interaction)

Example: "Add POST /api/v1/projects endpoint"
Load:
  - backend/api/routes/projects.py (reference)
  - backend/services/project_service.py
  - backend/models/project.py
```

---

#### **Type 2: Database Model or Migration**

**Detection:**
```
User request contains:
- "database model", "ORM model", "SQLAlchemy"
- "migration", "alembic", "schema change"
- "add column", "create table", "relationship"
```

**Context Loading:**
```yaml
Tier 1 + 2: Standard (cached)
Tier 3:
  - Model being modified/created
  - Related models (foreign keys, relationships)
  - Recent migration (if modifying)

Example: "Add avatar_url column to User model"
Load:
  - backend/models/user.py
  - backend/migrations/versions/latest.py (reference)
```

---

#### **Type 3: Business Logic (Service Layer)**

**Detection:**
```
User request contains:
- "business logic", "validation", "service"
- "calculate", "process", "generate"
- "authentication", "authorization", "permissions"
```

**Context Loading:**
```yaml
Tier 1 + 2: Standard (cached)
Tier 3:
  - Service being modified
  - Repository used by service
  - Related models

Example: "Add email verification logic to auth service"
Load:
  - backend/services/auth_service.py
  - backend/repositories/user_repository.py
  - backend/models/user.py
```

---

#### **Type 4: Testing (Backend)**

**Detection:**
```
User request contains:
- "test", "pytest", "unit test", "integration test"
- "test coverage", "add tests for"
```

**Context Loading:**
```yaml
Tier 1 + 2: Standard (cached)
Tier 3:
  - Code being tested
  - Existing test file (if adding to existing)
  - Test fixtures (conftest.py)

Example: "Write tests for user service"
Load:
  - backend/services/user_service.py (code under test)
  - backend/tests/unit/test_services/test_user_service.py
  - backend/tests/conftest.py (fixtures)
```

---

### **Frontend Task Types**

#### **Type 1: Page Component (Route)**

**Detection:**
```
User request contains:
- "page", "route", "URL", "navigation"
- "/dashboard", "/login", "/projects" (routes)
- "App Router", "page.tsx"
```

**Context Loading:**
```yaml
Tier 1 + 2: Standard (cached)
Tier 3:
  - Similar page (reference pattern)
  - Layout component (if page uses it)
  - API client (if data fetching)

Example: "Create projects listing page"
Load:
  - frontend/app/dashboard/page.tsx (reference)
  - frontend/app/layout.tsx (root layout)
  - frontend/lib/api/projects.ts (API client)
```

---

#### **Type 2: Shared Component**

**Detection:**
```
User request contains:
- "component", "button", "form", "modal"
- "reusable", "shared component"
- UI library names: "shadcn", "Radix"
```

**Context Loading:**
```yaml
Tier 1 + 2: Standard (cached)
Tier 3:
  - Similar existing component (reference)
  - UI primitives being used
  - Design system (project.md already loaded)

Example: "Create a file upload component"
Load:
  - frontend/components/ui/input.tsx (similar)
  - frontend/components/ui/button.tsx (UI primitive)
  - openspec/project.md (design tokens - cached)
```

---

#### **Type 3: Styling / Design**

**Detection:**
```
User request contains:
- "styling", "CSS", "Tailwind", "design"
- "theme", "colors", "spacing", "layout"
- "responsive", "mobile", "dark mode"
```

**Context Loading:**
```yaml
Tier 1 + 2: Standard (cached)
Tier 3:
  - Component being styled
  - Design system (project.md - already cached)
  - Global styles (if modifying theme)

Example: "Update button colors to match brand"
Load:
  - frontend/components/ui/button.tsx
  - openspec/project.md (design system - cached)
  - frontend/styles/globals.css (if theme changes)
```

---

#### **Type 4: API Integration**

**Detection:**
```
User request contains:
- "API integration", "fetch data", "API call"
- "hook", "useSWR", "TanStack Query"
- Backend endpoint references
```

**Context Loading:**
```yaml
Tier 1 + 2: Standard (cached)
Tier 3:
  - API client module
  - Hook using that API
  - Component consuming the hook

Example: "Add hook for fetching user projects"
Load:
  - frontend/lib/api/projects.ts (API client)
  - frontend/lib/hooks/useProjects.ts (existing hook)
  - frontend/types/project.ts (TypeScript types)
```

---

### **Debugging Tasks**

#### **Type: Bug Fix / Error Resolution**

**Detection:**
```
User request contains:
- "error", "bug", "fix", "not working"
- "TypeError", "undefined", stack traces
- "@problems" (Kilo Code diagnostics)
```

**Context Loading:**
```yaml
Tier 1 + 2: Standard (cached)
Tier 3:
  - File with error (from stack trace or @problems)
  - Related files (dependencies)
  - ONLY files mentioned in error

Example: "Fix undefined error in auth service"
Load:
  - backend/services/auth_service.py (error location)
  - backend/repositories/user_repository.py (if called)
  
DO NOT LOAD: All other files!
Strategy: Start minimal, expand only if needed
```

**Special Rule for Debugging:**
- ✅ Use @problems to see diagnostics first
- ✅ Load only files mentioned in error traces
- ✅ Use codebase_search to find related code
- ❌ Do NOT load entire package "just in case"
- ❌ Limit to 2-3 files maximum initially

---

## 🤖 Decision Automation

### **Automated Decision Flow**

```python
def determine_context(user_request: str) -> ContextLoadingPlan:
    # 1. Detect package
    if contains_backend_indicators(user_request):
        package = "backend"
    elif contains_frontend_indicators(user_request):
        package = "frontend"
    elif contains_fullstack_indicators(user_request):
        package = "sequential"  # backend first, then frontend
    else:
        package = "ask_user"  # Ambiguous, ask for clarification
    
    # 2. Detect task type
    task_type = classify_task_type(user_request)
    
    # 3. Build file list (max 3-4 files)
    files = select_relevant_files(package, task_type, user_request)
    
    # 4. Validate token budget
    if estimated_tokens(files) > 20000:
        files = prioritize_files(files, limit=4)
    
    return ContextLoadingPlan(
        package=package,
        task_type=task_type,
        files=files,
        estimated_tokens=estimated_tokens(files)
    )
```

---

## 📊 Example Scenarios

### **Scenario 1: Simple Backend Task**

**User Request:**
```
"Add an endpoint to delete a project by ID"
```

**Automated Detection:**
```yaml
Package: backend (keyword "endpoint" detected)
Task Type: API Endpoint (HTTP operation "delete")
Files to Load:
  - backend/api/routes/projects.py (has similar endpoints)
  - backend/services/project_service.py (business logic)
  - backend/repositories/project_repository.py (database)

Reasoning:
- "endpoint" → Backend API task
- "delete" → HTTP DELETE operation
- "project" → Projects resource
- Load pattern: Route → Service → Repository
```

---

### **Scenario 2: Frontend Component**

**User Request:**
```
"Create a task card component for the Kanban board with drag-and-drop"
```

**Automated Detection:**
```yaml
Package: frontend (keyword "component" detected)
Task Type: Shared Component (reusable UI element)
Files to Load:
  - frontend/components/ui/card.tsx (base card component)
  - frontend/app/projects/[id]/_components/TaskBoard.tsx (context)
  - openspec/project.md (design system - already cached)

Reasoning:
- "component" → Frontend task
- "card" → UI component
- "Kanban board" → Context where it's used
- Load pattern: Similar component → Usage context → Design system
```

---

### **Scenario 3: Debugging Task**

**User Request:**
```
"Fix the 500 error when creating a project with empty name"
```

**Automated Detection:**
```yaml
Package: backend (500 = server error)
Task Type: Debugging / Bug Fix
Files to Load:
  - Use @problems to see exact error location
  - Load only file with error (likely API route or service)
  - Load validation schema (Pydantic model)

Reasoning:
- "500 error" → Backend issue
- "creating project" → Projects API
- "empty name" → Validation issue
- Load pattern: Minimal (error location only)
```

---

### **Scenario 4: Full-Stack Feature**

**User Request:**
```
"Implement user profile editing (API + UI)"
```

**Automated Detection:**
```yaml
Package: sequential (both backend and frontend)
Task Type: Full-stack feature

Session 1 - Backend:
  Files to Load:
    - backend/api/routes/users.py
    - backend/services/user_service.py
    - backend/schemas/requests/user.py

Session 2 - Frontend:
  Files to Load:
    - frontend/app/settings/profile/page.tsx
    - frontend/lib/api/users.ts
    - frontend/components/forms/ProfileForm.tsx

Reasoning:
- "API + UI" → Full-stack task
- Strategy: Sequential implementation (backend first)
- Each session: Only relevant package
```

---

## ⚠️ Ambiguity Handling

### **When Task is Unclear:**

**Scenario: Ambiguous Request**
```
User: "Add profile feature"
```

**AI Response:**
```
I need clarification to load the right context:

1. Is this backend (API) or frontend (UI)?
   - Backend: Add user profile API endpoint
   - Frontend: Create user profile page
   - Both: Implement full profile feature

2. What specifically should the profile feature do?
   - Display existing profile data
   - Edit profile information
   - Upload profile picture
   - All of the above

Please specify so I can load the appropriate files efficiently.
```

**Key Principle: Ask Before Loading Everything!**

---

## ✅ Validation Before Loading

**Pre-Flight Checklist:**

```python
def validate_context_loading():
    checks = {
        "Package identified?": package != "unknown",
        "Task type classified?": task_type != "unknown",
        "Files selected (max 4)?": len(files) <= 4,
        "Token budget OK (<20K)?": estimated_tokens < 20000,
        "Excluded other package?": not mixed_packages,
    }
    
    if not all(checks.values()):
        return "STOP: Missing information or budget exceeded"
    
    return "PROCEED: Context loading validated"
```

---

## 🎯 Success Metrics

**Effective Dynamic Context Loading:**

✅ **95%+ tasks**: Correct package detected automatically  
✅ **90%+ tasks**: Optimal file selection (3-4 files)  
✅ **<20K tokens**: Average context size per task  
✅ **<5% retries**: Due to incorrect context loaded  
✅ **$0.05-0.10**: Average cost per task  

---

## 🛠️ Continuous Improvement

### **Learning from Mistakes:**

**If context was wrong:**
1. Document what went wrong (user feedback)
2. Update detection patterns
3. Add to memory bank (context.md)
4. Adjust automation rules

**Example Learning:**
```
Task: "Update user authentication flow"
Initial Detection: Frontend (saw "flow" keyword)
Correct: Backend (authentication is backend concern)

Learning: "authentication" always indicates backend,
          even with UI-like terms like "flow"
          
Action: Update backend indicators to prioritize
        authentication-related keywords
```

---

## 🌟 Open-Source Best Practices

This automation demonstrates:

✨ **Intelligent Context Management** - AI makes smart decisions  
✨ **Token Efficiency** - Automated optimization  
✨ **User Experience** - No manual file selection needed  
✨ **Error Handling** - Graceful fallback to clarification  
✨ **Continuous Learning** - Patterns improve over time  

**Learn more**: https://github.com/ardhaecosystem/Ardha

---

**Version**: 1.0  
**Last Updated**: November 5, 2025  
**Maintained By**: Ardha Development Team  
**License**: MIT (Open Source)
