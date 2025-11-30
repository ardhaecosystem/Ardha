# Current Context

**Last Updated:** November 30, 2025
**Current Branch:** `feature/initial-setup`
**Active Phase:** Phase 5 - Frontend Development (Week 13-16)
**Previous Phase:** Phase 4 - Databases & Background Jobs ✅ COMPLETE
**Recent Achievement:** Protected Routes & Navigation System ✅ COMPLETE

## Project Overview

**Ardha** is a unified AI-powered project management platform that eliminates the boundary between planning and execution.

### Core Architecture
```
Frontend (Next.js 15) ←→ Backend (FastAPI) ←→ Data Layer (PostgreSQL, Qdrant, Redis)
```

### Key Features for Frontend
- **Project Management**: Tasks, milestones, databases, files
- **AI Chat**: Multi-mode conversations (research, architect, implement, debug)
- **Git Integration**: Repository management, commits, task linking
- **OpenSpec**: Proposal-driven development workflow
- **Real-time Collaboration**: WebSocket updates, live editing

## Frontend Technology Stack

### Core Framework
- **Next.js 15** with App Router
- **React 19 RC** with TypeScript
- **Tailwind CSS** for styling
- **Radix UI** for accessible components

### Key Libraries
- **CodeMirror 6** - Code editor with syntax highlighting
- **xterm.js** - Terminal emulator
- **Framer Motion** - Animations
- **Lucide React** - Icons
- **Zustand** - State management
- **React Query** - Server state management

### Development Tools
- **pnpm** - Package manager
- **ESLint** - Linting
- **TypeScript** - Type checking

## API Integration

### Base Configuration
```typescript
// frontend/src/lib/api/client.ts
const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'
const WS_BASE_URL = process.env.NEXT_PUBLIC_WS_URL || 'ws://localhost:8000/ws'
```

### Authentication
- JWT-based authentication
- OAuth providers: GitHub, Google
- Token refresh mechanism
- Protected routes with middleware

### Key API Endpoints

#### Authentication
- `POST /api/v1/auth/login` - Email/password login
- `POST /api/v1/auth/oauth/github` - GitHub OAuth
- `POST /api/v1/auth/oauth/google` - Google OAuth
- `POST /api/v1/auth/refresh` - Refresh token

#### Projects
- `GET /api/v1/projects` - List projects
- `POST /api/v1/projects` - Create project
- `GET /api/v1/projects/{id}` - Get project details
- `PUT /api/v1/projects/{id}` - Update project

#### Tasks
- `GET /api/v1/projects/{id}/tasks` - List tasks
- `POST /api/v1/projects/{id}/tasks` - Create task
- `PUT /api/v1/tasks/{id}` - Update task
- `DELETE /api/v1/tasks/{id}` - Delete task

#### Chat
- `GET /api/v1/chats` - List chats
- `POST /api/v1/chats` - Create chat
- `POST /api/v1/chats/{id}/messages` - Send message
- `WebSocket /ws` - Real-time chat streaming

#### Git
- `GET /api/v1/projects/{id}/status` - Repository status
- `POST /api/v1/commits` - Create commit
- `GET /api/v1/projects/{id}/commits` - List commits

#### Databases
- `GET /api/v1/projects/{id}/databases` - List databases
- `POST /api/v1/projects/{id}/databases` - Create database
- `GET /api/v1/databases/{id}/entries` - List entries

## Component Architecture

### Directory Structure
```
frontend/src/
├── app/                    # Next.js App Router pages
├── components/             # Reusable components
│   ├── ui/                # Base UI components
│   ├── forms/             # Form components
│   ├── layouts/           # Layout components
│   └── features/          # Feature-specific components
├── lib/                   # Utilities and helpers
│   ├── api/               # API client functions
│   ├── hooks/             # Custom React hooks
│   ├── stores/            # Zustand stores
│   └── utils/             # Utility functions
├── types/                 # TypeScript type definitions
└── styles/                # Global styles
```

### Key Components

#### UI Components (`components/ui/`)
- `Button` - Styled button with variants
- `Input` - Form input with validation
- `Dialog` - Modal dialog component
- `Dropdown` - Dropdown menu
- `Toast` - Notification system

#### Layout Components (`components/layouts/`)
- `AppLayout` - Main application layout
- `Sidebar` - Navigation sidebar
- `Header` - Top navigation bar
- `CommandPalette` - Quick command interface

#### Feature Components
- `TaskBoard` - Kanban-style task board
- `TaskCard` - Individual task card
- `ChatInterface` - AI chat interface
- `CodeEditor` - Integrated code editor
- `DatabaseView` - Notion-style database view

## State Management

### Client State (Zustand)
```typescript
// lib/stores/auth-store.ts
interface AuthState {
  user: User | null
  token: string | null
  isAuthenticated: boolean
  login: (credentials: LoginCredentials) => Promise<void>
  logout: () => void
}

// lib/stores/project-store.ts
interface ProjectState {
  currentProject: Project | null
  projects: Project[]
  setCurrentProject: (project: Project) => void
  refreshProjects: () => Promise<void>
}
```

### Server State (React Query)
```typescript
// lib/api/queries.ts
export const useProjects = () => {
  return useQuery({
    queryKey: ['projects'],
    queryFn: () => apiClient.get('/projects'),
  })
}

export const useTasks = (projectId: string) => {
  return useQuery({
    queryKey: ['tasks', projectId],
    queryFn: () => apiClient.get(`/projects/${projectId}/tasks`),
  })
}
```

## Design System

### Theme Configuration
```typescript
// tailwind.config.ts
const theme = {
  colors: {
    primary: {
      50: '#f5f3ff',
      500: '#8b5cf6',
      900: '#4c1d95',
    },
    neutral: {
      50: '#fafafa',
      500: '#737373',
      900: '#171717',
    },
  },
  spacing: {
    // 4px grid system
  },
}
```

### Component Variants
```typescript
// lib/utils/cn.ts
import { clsx, type ClassValue } from 'clsx'
import { twMerge } from 'tailwind-merge'

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}
```

## Real-time Features

### WebSocket Integration
```typescript
// lib/hooks/use-websocket.ts
export const useWebSocket = (url: string) => {
  const [socket, setSocket] = useState<WebSocket | null>(null)
  const [isConnected, setIsConnected] = useState(false)

  useEffect(() => {
    const ws = new WebSocket(url)

    ws.onopen = () => setIsConnected(true)
    ws.onclose = () => setIsConnected(false)

    setSocket(ws)

    return () => ws.close()
  }, [url])

  return { socket, isConnected }
}
```

### Real-time Updates
- Chat message streaming
- Task status updates
- Project activity feed
- Live collaboration cursors

## Performance Optimization

### Code Splitting
```typescript
// Dynamic imports for heavy components
const CodeEditor = dynamic(() => import('@/components/editor/CodeEditor'), {
  loading: () => <div>Loading editor...</div>,
  ssr: false,
})
```

### Image Optimization
- Next.js Image component for all images
- Responsive images with proper sizing
- Lazy loading for below-fold images

### Caching Strategy
- React Query for API caching
- Service Worker for static assets
- Local storage for user preferences

## Security Considerations

### Client-Side Security
- XSS prevention with proper sanitization
- CSRF protection with same-site cookies
- Secure token storage (httpOnly cookies)
- Content Security Policy (CSP)

### API Security
- Request validation with TypeScript
- Error handling without data leakage
- Rate limiting on client side
- Secure headers configuration

## Testing Strategy

### Unit Tests
```typescript
// __tests__/components/Button.test.tsx
import { render, screen } from '@testing-library/react'
import { Button } from '@/components/ui/Button'

test('renders button with text', () => {
  render(<Button>Click me</Button>)
  expect(screen.getByText('Click me')).toBeInTheDocument()
})
```

### Integration Tests
- API integration testing
- User flow testing with Playwright
- Component integration testing

## Deployment

### Environment Variables
```bash
# .env.local
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_WS_URL=ws://localhost:8000/ws
NEXT_PUBLIC_APP_URL=http://localhost:3000
```

### Build Configuration
```json
// package.json
{
  "scripts": {
    "dev": "next dev",
    "build": "next build",
    "start": "next start",
    "lint": "next lint",
    "type-check": "tsc --noEmit"
  }
}
```

## Authentication Pages (November 29, 2025)

### Login & Register Pages Complete ✅

**Login Page** ([`app/(auth)/login/page.tsx`](frontend/app/(auth)/login/page.tsx:1)):
- Email/password authentication with validation
- OAuth buttons for GitHub and Google
- "Remember me" checkbox
- "Forgot password" link
- Auto-redirect after registration
- Beautiful prismatic aurora gradient background
- Glass morphism card with glowing border

**Register Page** ([`app/(auth)/register/page.tsx`](frontend/app/(auth)/register/page.tsx:1)):
- Full name, email, username, password fields
- Client-side validation (email format, password strength)
- Auto-login after successful registration
- OAuth providers (GitHub, Google)
- Terms of service agreement
- Matching gradient design system

**Auth Features:**
- ✅ JWT token storage in Zustand + localStorage
- ✅ Automatic token refresh mechanism
- ✅ Protected route middleware
- ✅ OAuth callback handling
- ✅ Error display with styled alerts

---

## Recent Work: Frontend Integration Fix (November 29, 2025)

### Major Achievement: Frontend Authentication Flow Complete ✅

Successfully debugged and fixed 4 critical issues blocking frontend functionality:

#### Issue 1: Tailwind CSS Not Loading
**Problem:**
- Registration page showed black background instead of gradient
- No styling applied to any components
- Missing configuration files

**Root Cause:**
- No `tailwind.config.ts` - Tailwind couldn't compile
- No `postcss.config.js` - PostCSS couldn't process directives
- Generic CSS without design system

**Fix:**
- Created [`tailwind.config.ts`](frontend/tailwind.config.ts:1) (59 lines) with complete color system
- Created [`postcss.config.js`](frontend/postcss.config.js:1) with Tailwind + Autoprefixer
- Updated [`globals.css`](frontend/app/globals.css:1) with CSS variables and gradient

**Result:** Beautiful blue-to-indigo gradient, complete design system working

#### Issue 2: "Failed to Fetch" API Errors
**Problem:**
- User registration failed with network errors
- Browser couldn't connect to backend
- Console showed "Failed to fetch"

**Root Cause:**
- Frontend JavaScript trying to call `http://localhost:8000`
- User's browser can't resolve `localhost` to backend container
- `NEXT_PUBLIC_*` env vars baked in at build time, not runtime
- Build used default value instead of public IP

**Fix:**
- Updated [`frontend/Dockerfile`](frontend/Dockerfile:19-22) with ARG for `NEXT_PUBLIC_API_URL`
- Updated [`docker-compose.yml`](docker-compose.yml:159-161) to pass public IP as build args
- JavaScript bundle now contains `http://82.29.164.29:8000`

**Result:** Browser successfully calls backend API from any location

#### Issue 3: CORS Blocking Requests
**Problem:**
- Backend rejecting requests with "Disallowed CORS origin"
- CORS preflight (OPTIONS) failing
- Registration API returning 400 errors

**Root Cause:**
- Backend CORS only allowed `localhost:3000` and `127.0.0.1:3000`
- Frontend accessed at `http://82.29.164.29:3000`
- Pydantic Settings couldn't parse .env JSON array format

**Fix:**
- Modified [`main.py`](backend/src/ardha/main.py:40-52) to allow all origins in debug mode
- Added: `if settings.debug: cors_origins = ["*"]`
- Commented out problematic .env CORS config

**Result:** All CORS requests accepted, registration working

#### Issue 4: Dashboard 404 Error
**Problem:**
- After successful login, `/dashboard` redirect showed 404
- Dashboard components existed but weren't accessible

**Root Cause:**
- Folder named `app/(dashboard)` with parentheses
- Next.js route groups `(folder)` don't create URL routes
- Only organize files, don't affect routing

**Fix:**
- Renamed `app/(dashboard)` → `app/dashboard`
- Next.js build now includes `/dashboard` in route manifest
- Layout and page components preserved

**Result:** Dashboard accessible, login redirect working

### Technical Insights Gained

**1. Next.js Environment Variables:**
- `NEXT_PUBLIC_*` vars are embedded during webpack build
- Must set via Dockerfile ARG before `pnpm run build`
- Can't change at runtime without rebuild
- Browser executes bundled JS (not Node.js)

**2. Docker Networking:**
- Container-to-container: Use service names (`backend:8000`)
- Browser-to-container: Use public IP (`82.29.164.29:8000`)
- Different networks require different URLs

**3. CORS Best Practices:**
- Development: Use permissive (`["*"]`) for ease
- Production: Restrict to specific domains
- Never use `["*"]` with `allow_credentials=true` in production

**4. Next.js Routing:**
- `(folder)` = Route group (organization only)
- `folder` = URL segment that creates route
- Test routes in build output manifest

### Files Modified

**Frontend Configuration (8 files):**
- `tailwind.config.ts` (NEW) - 59 lines
- `postcss.config.js` (NEW) - 6 lines
- `.dockerignore` (NEW) - 41 lines
- `Dockerfile` - Added build args
- `globals.css` - Complete CSS system
- `next.config.js` - Environment handling
- `package.json` - Version updates
- `app/dashboard/` - Renamed from (dashboard)

**Backend (2 files):**
- `main.py` - CORS allows all in debug
- `Dockerfile` - Added curl for health checks

**Docker (1 file):**
- `docker-compose.yml` - Public IP configuration

**VSCode (1 file - not committed, gitignored):**
- `.vscode/settings.json` - Suppress false warnings

**Total: 13 files (4 new, 7 modified, 2 renamed)**
**Commits: 2 commits on feature/initial-setup**
**Git Status: Clean working tree**

### Verification Results

**Services Status:**
```
✅ Frontend:   HEALTHY (http://82.29.164.29:3000)
✅ Backend:    HEALTHY (http://82.29.164.29:8000)
✅ PostgreSQL: HEALTHY
✅ Redis:      HEALTHY
✅ Qdrant:     RUNNING
```

**User Flow Testing:**
```
✅ Registration: Creating users (201 Created)
✅ Login:        Auto-login after registration
✅ Dashboard:    Displaying stats and navigation
✅ Styling:      Gradient background, Tailwind working
✅ CORS:         All origins allowed in debug mode
```

**Build Artifacts:**
```
✅ Tailwind CSS:    16KB bundle (cf23d152a68895ba.css)
✅ Dashboard Route: Present in build manifest
✅ API URL:         http://82.29.164.29:8000 in JS bundle
```

### Lessons for Team

1. **Always verify environment variable behavior** - Runtime vs build-time
2. **Test CORS with actual Origin headers** - Not just direct API calls
3. **Check Next.js build output** - Confirms routes are actually created
4. **Use code-based config when .env parsing fails** - More reliable
5. **Docker networking differs from browser networking** - Document both patterns

---

## Recent Work: Navigation System Implementation (November 30, 2025)

### Achievement: Protected Routes & Premium Navigation ✅

Successfully implemented a comprehensive navigation system with route protection, premium dark theme design, and seamless user experience.

#### Components Created (3 new files):

**1. Protected Route Component** ([`components/auth/protected-route.tsx`](frontend/components/auth/protected-route.tsx:1))
- Automatic redirect to `/login` for unauthenticated users
- SessionStorage preserves intended destination
- Redirects back after successful login
- Loading spinner prevents content flash

**2. Navigation Bar** ([`components/navigation/navbar.tsx`](frontend/components/navigation/navbar.tsx:1))
- Glass morphism design with backdrop blur
- Active route highlighting (Dashboard, Projects, Tasks, Chat)
- User avatar with dropdown menu (Profile, Settings, Logout)
- Search button placeholder for command palette
- Notifications icon with badge indicator

**3. Breadcrumbs** ([`components/navigation/breadcrumbs.tsx`](frontend/components/navigation/breadcrumbs.tsx:1))
- Auto-generated from route path
- Clickable navigation hierarchy
- Hidden on root-level pages

#### Files Modified (3 files):
- [`dashboard/layout.tsx`](frontend/app/dashboard/layout.tsx:1) - Integrated navigation components
- [`dashboard/page.tsx`](frontend/app/dashboard/page.tsx:1) - Updated with premium dark theme
- [`login/page.tsx`](frontend/app/(auth)/login/page.tsx:44) - Added redirect logic

#### Navigation Features:
- ✅ Route protection with auth validation
- ✅ Sticky navigation with active states
- ✅ User menu with profile/settings/logout
- ✅ Breadcrumb navigation for deep routes
- ✅ Glass morphism design system
- ✅ Purple/pink gradient accents
- ✅ Smooth transitions and hover effects

#### Build Results:
- ✅ No TypeScript errors
- ✅ Dashboard route: ~104KB First Load JS
- ✅ All components rendering correctly
- ✅ No runtime errors

---

## Current Development Status

### Completed Features
- ✅ Authentication system (JWT + OAuth + Login/Register pages)
- ✅ Protected routes with automatic redirect
- ✅ Premium navigation bar (glass morphism design)
- ✅ User menu with profile/settings/logout
- ✅ Breadcrumb navigation system
- ✅ Dashboard with welcome screen

### In Progress
- 🔄 Projects listing and detail pages
- 🔄 Tasks management interface
- 🔄 AI chat interface
- 🔄 Command palette (Cmd+K)

### Next Immediate Tasks
1. **Task #5** - Dashboard with real data and stats
2. **Projects Pages** - List, create, detail views
3. **Tasks Interface** - Kanban board, list views
4. **Chat Interface** - AI conversation UI
5. **Command Palette** - Quick navigation and actions

## Backend Context for Frontend

### Backend Architecture
- **Framework**: FastAPI with Python 3.12
- **Database**: PostgreSQL 15 with SQLAlchemy 2.0
- **Vector DB**: Qdrant for AI memory and search
- **Cache**: Redis 7 for sessions and caching
- **AI Integration**: OpenRouter API with multiple models

### Data Models Overview

#### Core Entities
```typescript
// User Model
interface User {
  id: string
  email: string
  username: string
  full_name?: string
  avatar_url?: string
  role: 'owner' | 'admin' | 'member' | 'viewer'
  created_at: string
  updated_at: string
}

// Project Model
interface Project {
  id: string
  name: string
  description?: string
  status: 'active' | 'archived' | 'completed'
  owner_id: string
  created_at: string
  updated_at: string
  // Relations: members, tasks, milestones, databases, files
}

// Task Model
interface Task {
  id: string
  title: string
  description?: string
  status: 'todo' | 'in_progress' | 'in_review' | 'done'
  priority: 'low' | 'medium' | 'high' | 'urgent'
  assignee_id?: string
  project_id: string
  milestone_id?: string
  due_date?: string
  created_at: string
  updated_at: string
  // Relations: assignee, project, milestone, dependencies, tags
}

// Chat Model
interface Chat {
  id: string
  title: string
  mode: 'chat' | 'research' | 'architect' | 'implement' | 'debug'
  project_id?: string
  user_id: string
  total_tokens: number
  total_cost: number
  is_archived: boolean
  created_at: string
  updated_at: string
  // Relations: messages, project, user
}

// Database Model (Notion-style)
interface Database {
  id: string
  name: string
  description?: string
  project_id: string
  created_by: string
  is_archived: boolean
  created_at: string
  updated_at: string
  // Relations: properties, views, entries
}
```

### API Response Formats
```typescript
// Standard API response
interface ApiResponse<T> {
  data: T
  message?: string
  success: boolean
}

// Paginated response
interface PaginatedResponse<T> {
  items: T[]
  total: number
  page: number
  limit: number
  hasMore: boolean
}

// Error response
interface ApiError {
  error: string
  code: string
  details?: Record<string, any>
  status_code: number
}
```

### Authentication System
```typescript
// JWT Token structure
interface JWTPayload {
  sub: string  // user_id
  email: string
  exp: number  // expiration
  iat: number  // issued at
  type: 'access' | 'refresh'
}

// Login response
interface LoginResponse {
  access_token: string
  refresh_token: string
  token_type: 'bearer'
  expires_in: number
  user: User
}

// OAuth providers
interface OAuthProvider {
  name: 'github' | 'google'
  client_id: string
  redirect_uri: string
  scopes: string[]
}
```

### WebSocket Events
```typescript
// Chat events
interface ChatMessageEvent {
  type: 'chat.message'
  data: {
    chat_id: string
    message: {
      id: string
      role: 'user' | 'assistant' | 'system'
      content: string
      model_used?: string
      tokens_input?: number
      tokens_output?: number
      cost?: number
      created_at: string
    }
  }
}

// Task events
interface TaskUpdateEvent {
  type: 'task.updated'
  data: {
    task_id: string
    changes: Partial<Task>
    updated_by: string
    timestamp: string
  }
}

// Project events
interface ProjectActivityEvent {
  type: 'project.activity'
  data: {
    project_id: string
    activity: {
      id: string
      type: 'task_created' | 'task_updated' | 'member_added' | 'file_uploaded'
      description: string
      user_id: string
      metadata?: Record<string, any>
      created_at: string
    }
  }
}

// Workflow events
interface WorkflowUpdateEvent {
  type: 'workflow.update'
  data: {
    workflow_id: string
    execution_id: string
    status: 'pending' | 'running' | 'completed' | 'failed' | 'cancelled'
    progress: number
    current_node?: string
    error?: string
  }
}
```

### Key Business Logic

#### Task Status Transitions
```typescript
// Valid status transitions
const TASK_STATUS_FLOW = {
  'todo': ['in_progress'],
  'in_progress': ['in_review', 'todo'],
  'in_review': ['done', 'in_progress'],
  'done': ['in_review']  // Can reopen for changes
}

// Task dependencies
interface TaskDependency {
  id: string
  task_id: string
  depends_on_task_id: string
  dependency_type: 'blocks' | 'depends_on'
  created_at: string
}
```

#### Project Permissions
```typescript
// Role-based permissions
const PROJECT_PERMISSIONS = {
  'owner': ['*'],  // All permissions
  'admin': ['read', 'write', 'delete', 'manage_members', 'manage_settings'],
  'member': ['read', 'write', 'comment'],
  'viewer': ['read']
}

// Permission check function
function hasPermission(userRole: string, requiredPermission: string): boolean {
  const permissions = PROJECT_PERMISSIONS[userRole] || []
  return permissions.includes('*') || permissions.includes(requiredPermission)
}
```

#### AI Chat System
```typescript
// Chat modes and their system prompts
const CHAT_MODES = {
  'chat': 'General conversation and assistance',
  'research': 'Market research and competitive analysis',
  'architect': 'System design and architecture decisions',
  'implement': 'Code generation and implementation',
  'debug': 'Error analysis and troubleshooting'
}

// Model routing based on complexity
const MODEL_ROUTING = {
  'simple': 'z-ai/glm-4.6',      // $0.15-0.30/M tokens
  'medium': 'anthropic/claude-sonnet-4.5',  // $3.00/M input, $15.00/M output
  'complex': 'anthropic/claude-opus-4.1'    // $15.00/M input, $75.00/M output
}
```

### Database Schema Insights

#### Important Relationships
```typescript
// Project relationships
interface ProjectRelations {
  owner: User                    // One-to-one
  members: User[]                // One-to-many
  tasks: Task[]                  // One-to-many
  milestones: Milestone[]        // One-to-many
  databases: Database[]          // One-to-many
  files: File[]                  // One-to-many
  chats: Chat[]                  // One-to-many
}

// Task relationships
interface TaskRelations {
  assignee: User                 // Many-to-one
  project: Project               // Many-to-one
  milestone: Milestone           // Many-to-one (optional)
  dependencies: Task[]           // Many-to-many
  dependents: Task[]             // Many-to-many
  tags: TaskTag[]                // One-to-many
  activities: TaskActivity[]     // One-to-many
}
```

#### Database Properties System
```typescript
// Property types for Notion-style databases
type PropertyType =
  | 'text'       // Plain text
  | 'number'     // Numeric values
  | 'date'       // Date/datetime
  | 'select'     // Single choice from options
  | 'multi_select' // Multiple choices
  | 'formula'    // Calculated values
  | 'rollup'     // Aggregated from related database
  | 'relation'   // Link to another database
  | 'boolean'    // True/false
  | 'url'        // URL links
  | 'email'      // Email addresses
  | 'phone'      // Phone numbers

interface DatabaseProperty {
  id: string
  name: string
  type: PropertyType
  config: Record<string, any>  // Type-specific configuration
  order: number
  created_at: string
}
```

### File System Integration
```typescript
// File model
interface File {
  id: string
  name: string
  path: string
  size: number
  mime_type: string
  project_id: string
  uploaded_by: string
  is_directory: boolean
  parent_id?: string
  created_at: string
  updated_at: string
}

// Supported file operations
const FILE_OPERATIONS = {
  'upload': ['*'],                    // All file types
  'download': ['*'],
  'preview': ['image/*', 'text/*', 'pdf'],
  'edit': ['text/*', 'md', 'json', 'yaml', 'yml'],
  'delete': ['*']
}
```

### Git Integration Details
```typescript
// Git commit model
interface GitCommit {
  id: string
  project_id: string
  sha: string
  short_sha: string
  message: string
  author_name: string
  author_email: string
  committed_at: string
  branch: string
  files_changed: number
  insertions: number
  deletions: number
  linked_task_ids: string[]      // Tasks mentioned in commit
  closes_task_ids: string[]      // Tasks closed by commit
  ardha_user_id?: string         // Ardha user who made commit
  created_at: string
}

// Task linking patterns
const TASK_PATTERNS = {
  'mention': [/(TAS|TASK|T|ARD)-\d+/gi, /#\d+/g],
  'closes': [/closes?\s+(TAS|TASK|T|ARD)-\d+/gi, /fixes?\s+(TAS|TASK|T|ARD)-\d+/gi]
}
```

### OpenSpec Integration
```typescript
// OpenSpec proposal model
interface OpenSpecProposal {
  id: string
  name: string
  status: 'pending' | 'approved' | 'rejected' | 'in_progress' | 'completed' | 'archived'
  project_id: string
  created_by: string
  approved_by?: string
  proposal_content: string      // proposal.md content
  tasks_content: string         // tasks.md content
  spec_delta: string            // spec-delta.md content
  completion_percentage: number
  synced_task_count: number
  total_task_count: number
  created_at: string
  updated_at: string
}
```

### Error Codes Reference
```typescript
// Common error codes for frontend handling
const ERROR_CODES = {
  // Authentication errors
  'AUTH_001': 'Invalid credentials',
  'AUTH_002': 'Token expired',
  'AUTH_003': 'Insufficient permissions',

  // Validation errors
  'VAL_001': 'Required field missing',
  'VAL_002': 'Invalid email format',
  'VAL_003': 'Password too weak',

  // Resource errors
  'RES_001': 'Resource not found',
  'RES_002': 'Resource already exists',
  'RES_003': 'Resource access denied',

  // Business logic errors
  'BIZ_001': 'Invalid task status transition',
  'BIZ_002': 'Task dependency conflict',
  'BIZ_003': 'Project member limit exceeded',

  // System errors
  'SYS_001': 'Database connection failed',
  'SYS_002': 'External API unavailable',
  'SYS_003': 'File upload failed'
}
```

### Rate Limiting
```typescript
// Rate limits per endpoint
const RATE_LIMITS = {
  'auth': { requests: 5, window: '1m' },
  'chat': { requests: 20, window: '1m' },
  'file_upload': { requests: 10, window: '1m', size: '100MB' },
  'api_general': { requests: 100, window: '1m' }
}
```

## Development Guidelines

### Code Style
- Use TypeScript for all new code
- Follow ESLint configuration
- Use Prettier for formatting
- Write meaningful commit messages

### Component Guidelines
- Keep components small and focused
- Use proper TypeScript types
- Implement error boundaries
- Add loading states

### API Integration
- Use the centralized API client
- Handle errors gracefully
- Implement proper loading states
- Cache responses appropriately

## Quick Start Commands

```bash
# Install dependencies
pnpm install

# Start development server
pnpm dev

# Run type checking
pnpm type-check

# Run linting
pnpm lint

# Build for production
pnpm build

# Run tests
pnpm test
```

## Useful Resources

### Documentation
- [Next.js Documentation](https://nextjs.org/docs)
- [Tailwind CSS](https://tailwindcss.com/docs)
- [Radix UI](https://www.radix-ui.com/docs)
- [React Query](https://tanstack.com/query/latest)

### Tools
- [Figma](https://figma.com) - Design mockups
- [Postman](https://postman.com) - API testing
- [Chrome DevTools](https://developer.chrome.com/docs/devtools) - Debugging

---

**Note**: This context is focused on frontend development. For backend-specific information, refer to the backend documentation and API specifications.
