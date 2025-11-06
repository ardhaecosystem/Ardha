# Ardha Frontend Code Patterns (Next.js/React)

> **Purpose**: Establish consistent frontend patterns following Server-First architecture principles.
>
> **Why This Matters**: Next.js 15 App Router with React 19 Server Components represents modern React development. These patterns ensure optimal performance and developer experience.
>
> **Open-Source Note**: These patterns showcase cutting-edge Next.js development. Perfect reference for modern React projects!

---

## 🎯 Frontend Technology Stack

**Core Framework:**
- **Next.js**: 15.0.2 (App Router, Server Components)
- **React**: 19.0.0 (with Server Components)
- **TypeScript**: 5.3.3 (strict mode enabled)
- **Package Manager**: pnpm 10.20.0

**Styling & UI:**
- **Tailwind CSS**: 3.4.1 (with custom design tokens)
- **Radix UI**: Accessible component primitives
- **shadcn/ui**: Pre-built accessible components
- **Framer Motion**: 10.18.0 (animations)
- **Lucide React**: 0.303.0 (icons)

**State & Data:**
- **Zustand**: 4.4.7 (client state, minimal usage)
- **TanStack Query**: 5.17.9 (server state caching)
- **SWR**: 2.2.4 (data fetching alternative)
- **React Hook Form**: 7.49.3 (form state)
- **Zod**: 3.22.4 (validation schemas)

**Code & Terminal:**
- **CodeMirror**: 6.0.1 (code editor)
- **xterm.js**: 5.3.0 (terminal emulator)

---

## 📁 Frontend Directory Structure

```
frontend/src/
├── app/                      # Next.js App Router pages
│   ├── (auth)/              # Route group (doesn't affect URL)
│   │   ├── login/
│   │   │   └── page.tsx     # /login route
│   │   ├── register/
│   │   │   └── page.tsx     # /register route
│   │   └── layout.tsx       # Auth layout
│   │
│   ├── dashboard/
│   │   ├── page.tsx         # /dashboard route
│   │   └── _components/     # Route-specific components
│   │       └── StatsCard.tsx
│   │
│   ├── projects/
│   │   ├── page.tsx         # /projects route
│   │   ├── [id]/            # Dynamic route
│   │   │   ├── page.tsx     # /projects/:id route
│   │   │   └── _components/
│   │   │       └── TaskBoard.tsx
│   │   └── _components/
│   │       └── ProjectCard.tsx
│   │
│   ├── api/                 # API route handlers
│   │   └── health/
│   │       └── route.ts     # /api/health endpoint
│   │
│   ├── layout.tsx           # Root layout
│   ├── page.tsx             # Home page (/)
│   └── globals.css          # Global styles
│
├── components/              # Shared components
│   ├── ui/                  # shadcn/ui base components
│   │   ├── button.tsx
│   │   ├── input.tsx
│   │   ├── dialog.tsx
│   │   └── ...
│   │
│   ├── layouts/             # Layout components
│   │   ├── Header.tsx
│   │   ├── Sidebar.tsx
│   │   └── Footer.tsx
│   │
│   └── forms/               # Form components
│       └── LoginForm.tsx
│
├── lib/                     # Utilities and configurations
│   ├── api/                 # API client
│   │   ├── client.ts        # Axios/fetch wrapper
│   │   └── endpoints.ts     # API endpoint definitions
│   │
│   ├── hooks/               # Custom React hooks
│   │   ├── useProjects.ts
│   │   └── useTasks.ts
│   │
│   └── utils/               # Utility functions
│       ├── cn.ts            # className utility
│       └── formatDate.ts
│
├── styles/                  # Additional styles
│   └── theme.css            # Theme variables
│
└── types/                   # TypeScript type definitions
    ├── api.ts               # API response types
    ├── project.ts
    └── task.ts
```

---

## 🏗️ Architecture Principles

### **1. Server Components by Default**

**Next.js 15 defaults to Server Components:**
- ✅ Render on server (zero client JavaScript)
- ✅ Direct database access (if needed)
- ✅ Better SEO and performance
- ✅ Smaller bundle sizes

**Use Client Components only when needed:**
- ❌ onClick, onChange handlers
- ❌ useState, useEffect hooks
- ❌ Browser APIs (localStorage, window)
- ❌ Third-party libraries requiring client

---

### **2. Server-First Data Fetching**

**Fetch data on server when possible:**
```tsx
// ✅ CORRECT: Server Component with data fetching
// app/dashboard/page.tsx
import { getProjects } from '@/lib/api/projects'
import { ProjectCard } from './_components/ProjectCard'

export default async function DashboardPage() {
  const projects = await getProjects() // Server-side fetch
  
  return (
    <div className="grid gap-4">
      <h1 className="text-2xl font-bold">Dashboard</h1>
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
        {projects.map(project => (
          <ProjectCard key={project.id} project={project} />
        ))}
      </div>
    </div>
  )
}

// ❌ INCORRECT: Client Component for static rendering
'use client'
import { useEffect, useState } from 'react'

export default function DashboardPage() {
  const [projects, setProjects] = useState([])
  
  useEffect(() => {
    fetch('/api/projects').then(/* ... */)
  }, [])
  
  // This defeats Server Component benefits!
}
```

---

## 🔍 File Selection Logic for Frontend Tasks

### **When Working on a Frontend Feature:**

**1. Identify the Component Type:**
- Is it a **page** (route)?
- Is it a **shared component**?
- Is it a **hook** (data fetching, state)?
- Is it **API integration**?

**2. Load Only Relevant Files:**

**For New Page:**
```
✅ Load similar existing page (pattern reference)
✅ Load related shared components
✅ Load layout files (if modifying layout)
✅ Load API client (if data fetching)

Example: Creating "task detail" page
- app/tasks/[id]/page.tsx (similar dynamic route)
- app/projects/[id]/page.tsx (reference pattern)
- components/ui/dialog.tsx (if using modal)
- lib/api/tasks.ts (API client)
```

**For New Component:**
```
✅ Load similar existing component (pattern reference)
✅ Load design system (openspec/project.md)
✅ Load used UI primitives

Example: Creating "CreateTaskButton" component
- components/ui/button.tsx (base button)
- app/projects/[id]/_components/CreateProjectButton.tsx (similar)
- lib/hooks/useTasks.ts (if data mutation)
```

**For API Integration:**
```
✅ Load API client file
✅ Load related types
✅ Load hook using that API

Example: Adding "delete project" API
- lib/api/client.ts (base client)
- lib/api/projects.ts (projects API)
- types/project.ts (Project type)
```

---

## 📐 Component Patterns

### **Server Component Pattern**

**Default for all pages and non-interactive components:**
```tsx
// app/projects/page.tsx
import { getProjects } from '@/lib/api/projects'
import { ProjectCard } from '@/components/ProjectCard'

// Server Component (no 'use client' directive)
export default async function ProjectsPage() {
  // Direct async/await in component
  const projects = await getProjects()
  
  return (
    <div className="container py-8">
      <h1 className="text-3xl font-bold mb-6">Projects</h1>
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
        {projects.map(project => (
          <ProjectCard key={project.id} project={project} />
        ))}
      </div>
    </div>
  )
}
```

**Key Rules:**
- ✅ Async/await directly in component
- ✅ No useState or useEffect
- ✅ Can access backend directly (if needed)
- ❌ Cannot use browser APIs
- ❌ Cannot use event handlers

---

### **Client Component Pattern**

**Only when interactivity is required:**
```tsx
// components/CreateProjectButton.tsx
'use client'  // Required directive

import { useState } from 'react'
import { Button } from '@/components/ui/button'
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog'
import { createProject } from '@/lib/api/projects'

export function CreateProjectButton() {
  const [isOpen, setIsOpen] = useState(false)
  const [isLoading, setIsLoading] = useState(false)
  
  const handleCreate = async () => {
    setIsLoading(true)
    try {
      await createProject({ name: 'New Project' })
      setIsOpen(false)
      // Optionally revalidate or refresh
    } catch (error) {
      console.error('Failed to create project:', error)
    } finally {
      setIsLoading(false)
    }
  }
  
  return (
    <>
      <Button onClick={() => setIsOpen(true)}>
        Create Project
      </Button>
      
      <Dialog open={isOpen} onOpenChange={setIsOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Create New Project</DialogTitle>
          </DialogHeader>
          {/* Form content */}
          <Button onClick={handleCreate} disabled={isLoading}>
            {isLoading ? 'Creating...' : 'Create'}
          </Button>
        </DialogContent>
      </Dialog>
    </>
  )
}
```

**When to Use Client Components:**
- ✅ onClick, onChange, onSubmit handlers
- ✅ useState, useEffect, useRef hooks
- ✅ Browser APIs (localStorage, window, navigator)
- ✅ Third-party libraries requiring client (xterm, CodeMirror)
- ✅ Real-time updates (WebSocket connections)

---

### **Hybrid Pattern (Server + Client)**

**Compose Server and Client Components:**
```tsx
// app/projects/[id]/page.tsx (Server Component)
import { getProject } from '@/lib/api/projects'
import { TaskBoard } from './_components/TaskBoard'  // Client Component

export default async function ProjectDetailPage({
  params,
}: {
  params: { id: string }
}) {
  // Fetch on server
  const project = await getProject(params.id)
  
  return (
    <div className="container py-8">
      <h1 className="text-3xl font-bold mb-6">{project.name}</h1>
      
      {/* Pass data to Client Component */}
      <TaskBoard projectId={project.id} initialTasks={project.tasks} />
    </div>
  )
}


// app/projects/[id]/_components/TaskBoard.tsx (Client Component)
'use client'

import { useState } from 'react'
import type { Task } from '@/types/task'

interface TaskBoardProps {
  projectId: string
  initialTasks: Task[]
}

export function TaskBoard({ projectId, initialTasks }: TaskBoardProps) {
  const [tasks, setTasks] = useState(initialTasks)
  
  // Client-side interactions
  const handleDragEnd = (result: any) => {
    // Update task status
  }
  
  return (
    <div className="grid grid-cols-4 gap-4">
      {/* Kanban columns */}
    </div>
  )
}
```

**Key Pattern:**
- ✅ Server Component fetches data
- ✅ Passes data as props to Client Component
- ✅ Client Component handles interactivity
- ✅ Best of both worlds (fast initial load + interactive UI)

---

## 🎨 Styling with Tailwind CSS

### **Design System (Ardha Theme)**

**Use Tailwind utility classes following design tokens:**
```tsx
// ✅ CORRECT: Using design system
<Button className="bg-primary text-primary-foreground hover:bg-primary/90">
  Click Me
</Button>

// ❌ INCORRECT: Hardcoded colors
<Button style={{ backgroundColor: '#8B5CF6' }}>
  Click Me
</Button>
```

**Design Tokens:**
```css
/* styles/globals.css */
:root {
  /* Primary (Purple brand color) */
  --primary: 262.1 83.3% 57.8%;
  --primary-foreground: 210 20% 98%;
  
  /* Neutrals (LCH color space - perfect grays) */
  --neutral-0: 0 0% 100%;    /* Pure white */
  --neutral-50: 210 20% 98%;
  --neutral-100: 214 32% 91%;
  --neutral-900: 222 47% 11%;
  
  /* Semantic colors */
  --success: 142 76% 36%;
  --error: 0 84% 60%;
  --warning: 38 92% 50%;
}

.dark {
  /* Dark mode variants */
  --primary: 262.1 83.3% 57.8%;  /* Same purple */
  --neutral-0: 222 47% 11%;       /* Dark background */
  --neutral-900: 210 20% 98%;     /* Light text */
}
```

**Spacing System (4px base):**
```tsx
// ✅ CORRECT: Using spacing scale
<div className="p-4 mb-6 gap-8">  {/* 16px, 24px, 32px */}
  
// ❌ INCORRECT: Arbitrary values
<div className="p-[13px] mb-[25px]">
```

---

## 📡 Data Fetching Patterns

### **Pattern 1: Server Component Fetch (Preferred)**

```tsx
// app/dashboard/page.tsx
import { api } from '@/lib/api/client'

async function getStats() {
  const res = await api.get('/api/v1/stats')
  return res.data
}

export default async function DashboardPage() {
  const stats = await getStats()
  
  return <StatsDisplay stats={stats} />
}
```

---

### **Pattern 2: Client Component with SWR**

```tsx
// app/dashboard/_components/LiveStats.tsx
'use client'

import useSWR from 'swr'
import { fetcher } from '@/lib/api/client'

export function LiveStats() {
  const { data, error, isLoading } = useSWR('/api/v1/stats', fetcher, {
    refreshInterval: 5000,  // Refresh every 5s
  })
  
  if (isLoading) return <Skeleton />
  if (error) return <ErrorMessage />
  
  return <StatsDisplay stats={data} />
}
```

---

### **Pattern 3: TanStack Query (Complex State)**

```tsx
// hooks/useProjects.ts
'use client'

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { api } from '@/lib/api/client'

export function useProjects() {
  return useQuery({
    queryKey: ['projects'],
    queryFn: async () => {
      const res = await api.get('/api/v1/projects')
      return res.data
    },
  })
}

export function useCreateProject() {
  const queryClient = useQueryClient()
  
  return useMutation({
    mutationFn: async (data: ProjectCreate) => {
      const res = await api.post('/api/v1/projects', data)
      return res.data
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['projects'] })
    },
  })
}
```

---

## 🧩 Component Standards

### **Component Structure**

```tsx
// ✅ CORRECT: Well-structured component
'use client'

import { useState } from 'react'
import { Button } from '@/components/ui/button'
import type { Project } from '@/types/project'

interface ProjectCardProps {
  project: Project
  onUpdate?: (project: Project) => void
}

export function ProjectCard({ project, onUpdate }: ProjectCardProps) {
  const [isEditing, setIsEditing] = useState(false)
  
  // Event handlers
  const handleEdit = () => {
    setIsEditing(true)
  }
  
  const handleSave = async () => {
    // Save logic
    setIsEditing(false)
    onUpdate?.(project)
  }
  
  // Render
  return (
    <div className="rounded-lg border p-4">
      <h3 className="text-lg font-semibold">{project.name}</h3>
      <p className="text-neutral-600">{project.description}</p>
      
      <div className="mt-4 flex gap-2">
        {isEditing ? (
          <>
            <Button onClick={handleSave}>Save</Button>
            <Button variant="outline" onClick={() => setIsEditing(false)}>
              Cancel
            </Button>
          </>
        ) : (
          <Button variant="outline" onClick={handleEdit}>
            Edit
          </Button>
        )}
      </div>
    </div>
  )
}
```

**Key Rules:**
- ✅ Named exports (not default exports for components)
- ✅ TypeScript interface for props
- ✅ Descriptive prop names
- ✅ Optional props with `?`
- ✅ Group by: imports → types → component → export

---

## 🔗 Routing & Navigation

### **Link Component (Client-Side Navigation)**

```tsx
import Link from 'next/link'

<Link href="/projects" className="text-primary hover:underline">
  View Projects
</Link>
```

### **Programmatic Navigation**

```tsx
'use client'

import { useRouter } from 'next/navigation'

export function LoginForm() {
  const router = useRouter()
  
  const handleLogin = async () => {
    await login(credentials)
    router.push('/dashboard')  // Navigate after login
  }
}
```

### **Dynamic Routes**

```tsx
// app/projects/[id]/page.tsx
interface PageProps {
  params: { id: string }
  searchParams: { tab?: string }
}

export default async function ProjectPage({ params, searchParams }: PageProps) {
  const project = await getProject(params.id)
  const activeTab = searchParams.tab || 'overview'
  
  return <ProjectDetail project={project} activeTab={activeTab} />
}
```

---

## 🎨 Design System Components

### **Using shadcn/ui Components**

```tsx
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'

<div className="space-y-4">
  <div>
    <Label htmlFor="email">Email</Label>
    <Input
      id="email"
      type="email"
      placeholder="Enter your email"
    />
  </div>
  
  <Button type="submit" className="w-full">
    Sign In
  </Button>
</div>
```

### **Custom Component with Variants**

```tsx
// components/ui/badge.tsx
import { cva, type VariantProps } from 'class-variance-authority'
import { cn } from '@/lib/utils/cn'

const badgeVariants = cva(
  'inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-semibold',
  {
    variants: {
      variant: {
        default: 'bg-primary text-primary-foreground',
        success: 'bg-success text-white',
        error: 'bg-error text-white',
        warning: 'bg-warning text-white',
      },
    },
    defaultVariants: {
      variant: 'default',
    },
  }
)

interface BadgeProps
  extends React.HTMLAttributes<HTMLDivElement>,
    VariantProps<typeof badgeVariants> {}

export function Badge({ className, variant, ...props }: BadgeProps) {
  return (
    <div className={cn(badgeVariants({ variant }), className)} {...props} />
  )
}

// Usage:
<Badge variant="success">Active</Badge>
<Badge variant="error">Failed</Badge>
```

---

## 🧪 Testing Standards

### **Component Tests (Vitest + Testing Library)**

```tsx
// __tests__/ProjectCard.test.tsx
import { render, screen, fireEvent } from '@testing-library/react'
import { ProjectCard } from '@/components/ProjectCard'

describe('ProjectCard', () => {
  const mockProject = {
    id: '1',
    name: 'Test Project',
    description: 'Test description',
  }
  
  it('renders project name and description', () => {
    render(<ProjectCard project={mockProject} />)
    
    expect(screen.getByText('Test Project')).toBeInTheDocument()
    expect(screen.getByText('Test description')).toBeInTheDocument()
  })
  
  it('calls onUpdate when saved', async () => {
    const onUpdate = vi.fn()
    render(<ProjectCard project={mockProject} onUpdate={onUpdate} />)
    
    fireEvent.click(screen.getByText('Edit'))
    fireEvent.click(screen.getByText('Save'))
    
    expect(onUpdate).toHaveBeenCalledWith(mockProject)
  })
})
```

---

## ⚡ Performance Optimization

### **Code Splitting**

```tsx
// Dynamic import for large components
import dynamic from 'next/dynamic'

const CodeEditor = dynamic(() => import('@/components/CodeEditor'), {
  loading: () => <EditorSkeleton />,
  ssr: false,  // Disable SSR for browser-only components
})
```

### **Image Optimization**

```tsx
import Image from 'next/image'

<Image
  src="/project-thumbnail.jpg"
  alt="Project thumbnail"
  width={400}
  height={300}
  className="rounded-lg"
  priority={false}  // Lazy load by default
/>
```

---

## 🌟 Open-Source Best Practices

These patterns demonstrate:

✨ **Modern React** - Server Components + Client Components  
✨ **Type Safety** - Full TypeScript with strict mode  
✨ **Accessibility** - Radix UI primitives, semantic HTML  
✨ **Performance** - Code splitting, image optimization  
✨ **Design System** - Consistent Tailwind patterns  

**Learn more**: https://github.com/ardhaecosystem/Ardha

---

**Version**: 1.0  
**Last Updated**: November 5, 2025  
**Maintained By**: Ardha Development Team  
**License**: MIT (Open Source)
