# Ardha Context Loading Strategy

> **Purpose**: Implement hierarchical context loading to achieve 95% token reduction and stay within $60/month AI budget.
>
> **Why This Matters**: Loading entire 50K+ LOC monorepo costs 150K-300K tokens per request ($0.45-$0.90). Hierarchical loading costs 5-15K tokens ($0.015-$0.045). **That's 95% savings!**
>
> **Open-Source Note**: This strategy demonstrates how to build AI-assisted projects on tight budgets. Essential for indie developers and startups!

---

## 🎯 Core Principle: Never Load Everything

**The Problem:**
- Full monorepo scan: 150K-300K tokens per request
- $60/month budget = 66 requests at full scan rate
- **Project would be impossible to complete!**

**The Solution:**
- Hierarchical loading: 5-15K tokens per request
- $60/month budget = 4,000 requests at optimized rate
- **Enables 20-week development timeline!**

---

## 📊 Three-Tier Loading Strategy

### **Tier 1: Always-Loaded Context (2-5K tokens)**

**What**: Project-wide fundamentals that apply to ALL tasks

**Files Loaded:**
- ✅ `.kilocode/rules/memory-bank/brief.md` (project overview)
- ✅ `openspec/project.md` (conventions and standards)
- ✅ Root `.gitignore`, `.env.example` (if relevant to task)

**When**: Automatically loaded at start of EVERY task

**Cost**: ~2-5K tokens (cached after first load = $0.006-$0.015)

---

### **Tier 2: Package-Specific Context (3-8K tokens)**

**What**: Package-level architecture and patterns

**Load ONE of these based on task:**

**Backend Task:**
- ✅ `.kilocode/rules/memory-bank/architecture.md` (backend section)
- ✅ `.kilocode/rules-code/backend-patterns.md`
- ✅ `backend/pyproject.toml` (dependencies, if relevant)

**Frontend Task:**
- ✅ `.kilocode/rules/memory-bank/architecture.md` (frontend section)
- ✅ `.kilocode/rules-code/frontend-patterns.md`
- ✅ `frontend/package.json` (dependencies, if relevant)

**When**: Loaded when working in specific package

**Cost**: ~3-8K tokens (cached = $0.009-$0.024)

---

### **Tier 3: Task-Specific Context (2-10K tokens)**

**What**: Only files directly relevant to current task

**Maximum Files**: 3-4 files per prompt

**Selection Criteria:**
1. Files being modified
2. Files with similar patterns (reference)
3. Related files (dependencies)
4. Test files (if writing tests)

**When**: Loaded for specific implementation

**Cost**: ~2-10K tokens ($0.006-$0.030)

---

## 📋 Context Loading Decision Tree

```
┌──────────────────────────────────┐
│ Start Task                       │
└───────────┬──────────────────────┘
            │
            ▼
┌──────────────────────────────────┐
│ Load Tier 1 (Always)             │
│ - brief.md (2K cached)           │
│ - project.md (3K cached)         │
└───────────┬──────────────────────┘
            │
            ▼
┌──────────────────────────────────┐
│ Which package?                   │
└───────┬──────────────────────────┘
        │
    ┌───┴────┐
    ▼        ▼
┌────────┐ ┌──────────┐
│Backend │ │ Frontend │
└───┬────┘ └────┬─────┘
    │           │
    ▼           ▼
┌──────────────────────────────────┐
│ Load Tier 2 (Package)            │
│ - architecture.md section (3K)   │
│ - patterns.md (5K cached)        │
└───────────┬──────────────────────┘
            │
            ▼
┌──────────────────────────────────┐
│ What type of task?               │
└───────┬──────────────────────────┘
        │
    ┌───┴────┬──────┬──────┐
    ▼        ▼      ▼      ▼
┌─────┐ ┌──────┐ ┌────┐ ┌─────┐
│ New │ │ Mod  │ │Bug │ │Test │
│ API │ │ UI   │ │Fix │ │Gen  │
└──┬──┘ └───┬──┘ └─┬──┘ └──┬──┘
   │        │      │       │
   └────┬───┴──────┴───────┘
        │
        ▼
┌──────────────────────────────────┐
│ Load Tier 3 (Task-Specific)      │
│ - Relevant files only (3-4)      │
│ - Max 10K tokens                 │
└──────────────────────────────────┘
```

---

## 🔍 Package-Specific Loading Rules

### **When Working in Backend**

**Always Load (Tier 1 + Tier 2):**
1. Brief.md (cached)
2. Project.md (cached)
3. Backend patterns.md (cached)
4. Architecture.md backend section (cached)

**Then Load Task-Specific (Tier 3):**
- Maximum 3-4 files from `backend/` directory only
- Related test files (if applicable)

**Never Load:**
- ❌ Any `frontend/` directory files
- ❌ Frontend package.json or configs
- ❌ All other backend files (just what's needed)

**Example: Adding password reset endpoint**
```
Tier 1 (5K cached):
- brief.md
- project.md

Tier 2 (8K cached):
- architecture.md (backend)
- backend-patterns.md

Tier 3 (6K):
- backend/src/ardha/api/routes/auth.py
- backend/src/ardha/services/auth_service.py
- backend/src/ardha/models/user.py

Total: 19K tokens ($0.057 with caching)
Without strategy: 220K tokens ($0.66)
Savings: 91% cheaper!
```

---

### **When Working in Frontend**

**Always Load (Tier 1 + Tier 2):**
1. Brief.md (cached)
2. Project.md (cached)
3. Frontend patterns.md (cached)
4. Architecture.md frontend section (cached)

**Then Load Task-Specific (Tier 3):**
- Maximum 3-4 files from `frontend/` directory only
- Related component files (if applicable)

**Never Load:**
- ❌ Any `backend/` directory files
- ❌ Backend pyproject.toml or configs
- ❌ All other frontend files (just what's needed)

**Example: Creating login page component**
```
Tier 1 (5K cached):
- brief.md
- project.md

Tier 2 (8K cached):
- architecture.md (frontend)
- frontend-patterns.md

Tier 3 (5K):
- frontend/src/app/(auth)/login/page.tsx
- frontend/src/components/ui/button.tsx
- frontend/src/lib/api/auth.ts

Total: 18K tokens ($0.054 with caching)
Without strategy: 220K tokens ($0.66)
Savings: 92% cheaper!
```

---

## ⚠️ Critical Loading Rules

### **Rule 1: Maximum 3-4 Files Per Prompt**

**Why**: Beyond 4 files, AI's attention diffuses
- 1-2 files: Excellent focus
- 3-4 files: Good focus
- 5+ files: Diminishing returns
- 10+ files: Lost context

**Enforcement:**
```
Before loading files, count them:
1. Primary file being modified
2. Reference file (similar pattern)
3. Related dependency file
4. Test file (if writing tests)

If count > 4:
→ Stop and ask user which files to prioritize
→ Or break task into smaller subtasks
```

---

### **Rule 2: Use Codebase Search, Not Full Load**

**When You Need to Find Something:**

**❌ INCORRECT:**
```
Load ALL files in backend/ to find where user authentication is handled
→ Costs 70K tokens, takes time, context overflow
```

**✅ CORRECT:**
```
Use codebase_search or @codebase to find "user authentication"
→ Returns 3-5 relevant files (5K tokens)
→ Then load only those specific files
```

---

### **Rule 3: Rely on Memory Bank, Not File Scanning**

**❌ INCORRECT Workflow:**
```
User: "Create a new API endpoint for user profiles"
AI: "Let me scan all backend files first..."
→ Loads 40 files, 70K tokens
```

**✅ CORRECT Workflow:**
```
User: "Create a new API endpoint for user profiles"
AI: [Reads memory bank - already has architecture knowledge]
→ Loads only:
  - api/routes/users.py (reference pattern)
  - services/user_service.py
  - models/user.py
→ 6K tokens total
```

---

## 🎯 Context Loading Examples

### **Example 1: Backend API Endpoint**

**Task**: "Add endpoint to update user profile (name, bio)"

**Correct Loading:**
```yaml
Tier 1 (cached):
  - brief.md
  - project.md

Tier 2 (cached):
  - architecture.md (backend)
  - backend-patterns.md

Tier 3 (fresh):
  - backend/src/ardha/api/routes/users.py       # Reference pattern
  - backend/src/ardha/services/user_service.py  # Business logic
  - backend/src/ardha/schemas/requests/user.py  # Request model

Total: 5K + 8K + 6K = 19K tokens
Cost: $0.057 (with caching)
```

**Incorrect Loading:**
```yaml
# Don't do this!
- ALL files in backend/api/routes/
- ALL files in backend/services/
- ALL files in backend/models/
- frontend/ files (irrelevant!)

Total: 150K tokens
Cost: $0.45
```

---

### **Example 2: Frontend Component**

**Task**: "Create a sidebar navigation component with active state"

**Correct Loading:**
```yaml
Tier 1 (cached):
  - brief.md
  - project.md

Tier 2 (cached):
  - architecture.md (frontend)
  - frontend-patterns.md

Tier 3 (fresh):
  - frontend/src/components/layouts/Sidebar.tsx  # If exists
  - frontend/src/components/ui/button.tsx        # UI primitive
  - frontend/src/app/layout.tsx                  # Where it's used

Total: 5K + 8K + 5K = 18K tokens
Cost: $0.054 (with caching)
```

---

### **Example 3: Full-Stack Feature**

**Task**: "Implement user avatar upload (API + UI)"

**Correct Workflow (Two Sessions):**

**Session 1 - Backend:**
```yaml
Tier 1 + 2: 13K cached
Tier 3:
  - backend/api/routes/users.py
  - backend/services/user_service.py
  - backend/models/user.py

Total: 19K tokens
Cost: $0.057
```

**Session 2 - Frontend:**
```yaml
Tier 1 + 2: 13K cached
Tier 3:
  - frontend/app/settings/profile/_components/AvatarUpload.tsx
  - frontend/lib/api/users.ts
  - frontend/components/ui/avatar.tsx

Total: 18K tokens
Cost: $0.054
```

**Total: $0.111 for full-stack feature**

**Incorrect Workflow (One Session):**
```yaml
Load both backend/ and frontend/ simultaneously
Total: 220K tokens
Cost: $0.66

Savings with strategy: 83% cheaper!
```

---

## 📊 Monthly Budget Breakdown

**$60/month budget with hierarchical loading:**

```
Average Task Cost: $0.05-0.10 per feature
Monthly Capacity:
- Simple tasks (backend or frontend): 600-1200 features
- Complex tasks (full-stack): 300-600 features
- Mixed workflow (realistic): 400-800 features

20-Week Project Needs:
- Phase 1-3 (Backend): ~50 features = $5-10
- Phase 4-6 (Frontend): ~50 features = $5-10
- Testing & Polish: ~30 features = $3-5
- Architecture Sessions: ~10 sessions = $5-10
- Total: $18-40 (well within budget!)
```

---

## ✅ Validation Checklist

**Before Processing Any Task, Verify:**

- [ ] Have I loaded Tier 1 (brief.md, project.md)?
- [ ] Have I loaded Tier 2 (package-specific patterns)?
- [ ] Am I loading ONLY files from the relevant package?
- [ ] Have I limited Tier 3 to 3-4 files maximum?
- [ ] Have I used codebase search instead of full scan?
- [ ] Is my total token count under 20K?

**If any answer is "no", stop and adjust file selection!**

---

## 🛡️ Emergency Context Cleanup

**If context exceeds 50K tokens:**

1. **Stop immediately** - don't continue request
2. **Identify bloat** - what files were loaded unnecessarily?
3. **Update memory bank** - document learnings from this session
4. **Start fresh task** - clean slate with correct file selection
5. **Use /newtask** - Kilo Code command for new context

**Context overflow is expensive!**
- 50K excess tokens = $0.15 wasted
- 10 overflows = $1.50 = 2.5% of monthly budget gone

---

## 🌟 Open-Source Best Practices

This strategy demonstrates:

✨ **Budget-Conscious Development** - $60/month can build complex projects
✨ **Token Efficiency** - 95% reduction through smart loading
✨ **Scalable Patterns** - Works for any monorepo size
✨ **Predictable Costs** - Clear cost per feature
✨ **Reproducible Results** - Consistent AI performance

**Learn more**: https://github.com/ardhaecosystem/Ardha

---

**Version**: 1.0
**Last Updated**: November 5, 2025
**Maintained By**: Ardha Development Team
**License**: MIT (Open Source)
