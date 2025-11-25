# Frontend Integration Guide

This guide helps frontend developers integrate with the Ardha backend API.

**Quick Links:**
- [Backend URLs](#backend-urls)
- [Authentication](#authentication)
- [API Client Setup](#api-client-setup)
- [WebSocket Connection](#websocket-connection)
- [API Examples](#api-examples)
- [Error Handling](#error-handling)
- [Environment Variables](#environment-variables)

---

## Backend URLs

### Development
- **API Base:** `http://localhost:8000`
- **API Docs:** `http://localhost:8000/docs`
- **WebSocket Base:** `ws://localhost:8000`

### Production
- **API Base:** `https://api.ardha.dev`
- **WebSocket Base:** `wss://api.ardha.dev`

---

## Authentication

Ardha supports three authentication methods:
1. Email/Password with JWT tokens
2. GitHub OAuth
3. Google OAuth

### JWT Token Structure

**Access Token:**
- Type: Bearer token
- Expiry: 15 minutes
- Format: JWT (HS256)
- Payload: `{ "sub": "<user_id>", "exp": <timestamp> }`

**Refresh Token:**
- Expiry: 7 days
- Used to obtain new access tokens
- Endpoint: `POST /api/v1/auth/refresh`

---

## Method 1: Email/Password Authentication

### Registration
```typescript
interface RegisterRequest {
  email: string;
  username: string;
  password: string;
  full_name: string;
}

interface AuthResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
  user: User;
}

// Example
const response = await fetch('http://localhost:8000/api/v1/auth/register', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    email: 'user@example.com',
    username: 'username',
    password: 'SecurePass123!',
    full_name: 'John Doe'
  })
});

const data: AuthResponse = await response.json();

// Store tokens
localStorage.setItem('access_token', data.access_token);
localStorage.setItem('refresh_token', data.refresh_token);
```

### Login
```typescript
interface LoginRequest {
  email: string;
  password: string;
}

// Example
const response = await fetch('http://localhost:8000/api/v1/auth/login', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    email: 'user@example.com',
    password: 'SecurePass123!'
  })
});

const data: AuthResponse = await response.json();

// Store tokens
localStorage.setItem('access_token', data.access_token);
localStorage.setItem('refresh_token', data.refresh_token);
```

### Using Access Token
```typescript
// On every API request
const token = localStorage.getItem('access_token');

const response = await fetch('http://localhost:8000/api/v1/projects', {
  headers: {
    'Authorization': `Bearer ${token}`,
    'Content-Type': 'application/json'
  }
});
```

### Token Refresh
```typescript
// When access token expires (401 response)
async function refreshAccessToken() {
  const refreshToken = localStorage.getItem('refresh_token');

  const response = await fetch('http://localhost:8000/api/v1/auth/refresh', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ refresh_token: refreshToken })
  });

  if (response.ok) {
    const { access_token } = await response.json();
    localStorage.setItem('access_token', access_token);
    return access_token;
  } else {
    // Refresh failed, redirect to login
    localStorage.clear();
    window.location.href = '/login';
  }
}
```

---

## Method 2: OAuth Authentication (GitHub/Google)

### Step 1: Redirect to OAuth Provider
```typescript
// For GitHub
function loginWithGitHub() {
  window.location.href = 'http://localhost:8000/api/v1/auth/oauth/github';
}

// For Google
function loginWithGoogle() {
  window.location.href = 'http://localhost:8000/api/v1/auth/oauth/google';
}
```

### Step 2: Handle OAuth Callback

**Backend redirects to:** `http://localhost:3000/auth/callback?token=xxx&refresh_token=yyy`
```typescript
// In your /auth/callback page
'use client';

import { useEffect } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';

export default function OAuthCallback() {
  const router = useRouter();
  const searchParams = useSearchParams();

  useEffect(() => {
    const token = searchParams.get('token');
    const refreshToken = searchParams.get('refresh_token');

    if (token && refreshToken) {
      // Store tokens
      localStorage.setItem('access_token', token);
      localStorage.setItem('refresh_token', refreshToken);

      // Redirect to dashboard
      router.push('/dashboard');
    } else {
      // OAuth failed
      router.push('/login?error=oauth_failed');
    }
  }, [router, searchParams]);

  return <div>Completing login...</div>;
}
```

---

## API Client Setup

### Recommended: Axios with Interceptors
```typescript
// lib/api-client.ts
import axios, { AxiosError } from 'axios';

const apiClient = axios.create({
  baseURL: process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000',
  headers: {
    'Content-Type': 'application/json',
  },
});

// Request interceptor - Add token to all requests
apiClient.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('access_token');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => Promise.reject(error)
);

// Response interceptor - Handle token refresh
apiClient.interceptors.response.use(
  (response) => response,
  async (error: AxiosError) => {
    const originalRequest = error.config;

    // If 401 and haven't retried yet
    if (error.response?.status === 401 && originalRequest && !originalRequest._retry) {
      originalRequest._retry = true;

      try {
        // Try to refresh token
        const refreshToken = localStorage.getItem('refresh_token');
        const response = await axios.post(
          `${process.env.NEXT_PUBLIC_API_URL}/api/v1/auth/refresh`,
          { refresh_token: refreshToken }
        );

        const { access_token } = response.data;
        localStorage.setItem('access_token', access_token);

        // Retry original request with new token
        originalRequest.headers.Authorization = `Bearer ${access_token}`;
        return axios(originalRequest);
      } catch (refreshError) {
        // Refresh failed, clear tokens and redirect
        localStorage.clear();
        window.location.href = '/login';
        return Promise.reject(refreshError);
      }
    }

    return Promise.reject(error);
  }
);

export default apiClient;
```

### Usage Example
```typescript
import apiClient from '@/lib/api-client';

// GET request
const projects = await apiClient.get('/api/v1/projects');

// POST request
const newProject = await apiClient.post('/api/v1/projects', {
  name: 'My Project',
  description: 'Project description'
});

// PATCH request
await apiClient.patch(`/api/v1/projects/${id}`, {
  name: 'Updated Name'
});

// DELETE request
await apiClient.delete(`/api/v1/projects/${id}`);
```

---

## WebSocket Connection

### Chat Streaming WebSocket
```typescript
// Connect to chat for streaming
function connectToChatWebSocket(chatId: string, onMessage: (data: any) => void) {
  const token = localStorage.getItem('access_token');
  const ws = new WebSocket(
    `ws://localhost:8000/api/v1/chats/${chatId}/ws?token=${token}`
  );

  ws.onopen = () => {
    console.log('Connected to chat WebSocket');
  };

  ws.onmessage = (event) => {
    const data = JSON.parse(event.data);

    switch (data.type) {
      case 'content_delta':
        // Append content to message
        onMessage({ type: 'delta', content: data.data.content });
        break;

      case 'message_complete':
        // Message finished streaming
        onMessage({ type: 'complete', message: data.data.message });
        break;

      case 'error':
        // Error occurred
        onMessage({ type: 'error', message: data.data.message });
        break;
    }
  };

  ws.onerror = (error) => {
    console.error('WebSocket error:', error);
  };

  ws.onclose = () => {
    console.log('WebSocket closed');
  };

  return ws;
}

// Usage in React component
'use client';

import { useState, useEffect, useRef } from 'react';

export default function ChatComponent({ chatId }: { chatId: string }) {
  const [messages, setMessages] = useState<string[]>([]);
  const [currentMessage, setCurrentMessage] = useState('');
  const wsRef = useRef<WebSocket | null>(null);

  useEffect(() => {
    wsRef.current = connectToChatWebSocket(chatId, (data) => {
      if (data.type === 'delta') {
        setCurrentMessage(prev => prev + data.content);
      } else if (data.type === 'complete') {
        setMessages(prev => [...prev, currentMessage]);
        setCurrentMessage('');
      }
    });

    return () => {
      wsRef.current?.close();
    };
  }, [chatId]);

  return (
    <div>
      {messages.map((msg, i) => <div key={i}>{msg}</div>)}
      {currentMessage && <div>{currentMessage}</div>}
    </div>
  );
}
```

### Notifications WebSocket
```typescript
// Connect to notifications
function connectToNotifications(onNotification: (notification: any) => void) {
  const token = localStorage.getItem('access_token');
  const ws = new WebSocket(
    `ws://localhost:8000/api/v1/ws/notifications?token=${token}`
  );

  ws.onopen = () => {
    console.log('Connected to notifications');
  };

  ws.onmessage = (event) => {
    const data = JSON.parse(event.data);

    if (data.type === 'notification') {
      onNotification(data.data);
    } else if (data.type === 'system') {
      console.log('System message:', data.data.message);
    }
  };

  // Ping/pong for keepalive
  const pingInterval = setInterval(() => {
    if (ws.readyState === WebSocket.OPEN) {
      ws.send(JSON.stringify({ type: 'ping' }));
    }
  }, 30000);

  ws.onclose = () => {
    clearInterval(pingInterval);
    console.log('Notifications disconnected');
  };

  return ws;
}
```

---

## API Examples

### Projects API
```typescript
// List all projects
const projects = await apiClient.get('/api/v1/projects');

// Get single project
const project = await apiClient.get(`/api/v1/projects/${projectId}`);

// Create project
const newProject = await apiClient.post('/api/v1/projects', {
  name: 'My Project',
  description: 'Project description'
});

// Update project
await apiClient.patch(`/api/v1/projects/${projectId}`, {
  name: 'Updated Name',
  description: 'Updated description'
});

// Archive project (soft delete)
await apiClient.patch(`/api/v1/projects/${projectId}`, {
  is_archived: true
});

// Delete project
await apiClient.delete(`/api/v1/projects/${projectId}`);
```

### Tasks API
```typescript
// List tasks (with filtering)
const tasks = await apiClient.get('/api/v1/tasks', {
  params: {
    project_id: projectId,
    status: 'todo',  // optional filter
    skip: 0,
    limit: 50
  }
});

// Create task
const task = await apiClient.post('/api/v1/tasks', {
  title: 'Implement feature X',
  description: 'Detailed description',
  project_id: projectId,
  status: 'todo',
  priority: 'high',
  assigned_to_id: userId,  // optional
  due_date: '2025-12-31T23:59:59Z'  // optional
});

// Update task
await apiClient.patch(`/api/v1/tasks/${taskId}`, {
  status: 'in_progress',
  assigned_to_id: userId
});

// Add task dependency
await apiClient.post(`/api/v1/tasks/${taskId}/dependencies`, {
  depends_on_task_id: otherTaskId
});
```

### AI Chat API
```typescript
// Create chat
const chat = await apiClient.post('/api/v1/chats', {
  title: 'New Chat',
  mode: 'chat',  // 'research' | 'architect' | 'implement' | 'debug' | 'chat'
  project_id: projectId  // optional
});

// Send message (non-streaming)
const message = await apiClient.post(`/api/v1/chats/${chatId}/messages`, {
  content: 'Hello, AI!',
  model: 'gpt-4-turbo'  // optional, auto-selected if not provided
});

// For streaming responses, use WebSocket (see above)
```

### Notifications API
```typescript
// List notifications
const notifications = await apiClient.get('/api/v1/notifications', {
  params: {
    unread_only: true,  // optional
    skip: 0,
    limit: 50
  }
});

// Mark notification as read
await apiClient.patch(`/api/v1/notifications/${notificationId}/read`);

// Mark all as read
await apiClient.post('/api/v1/notifications/mark-all-read');

// Delete notification
await apiClient.delete(`/api/v1/notifications/${notificationId}`);

// Get notification preferences
const prefs = await apiClient.get('/api/v1/notifications/preferences');

// Update preferences
await apiClient.patch('/api/v1/notifications/preferences', {
  email_enabled: true,
  task_assigned: true,
  mentions: true,
  quiet_hours_start: '22:00:00',
  quiet_hours_end: '08:00:00'
});
```

### Git Integration API
```typescript
// Initialize repository
await apiClient.post(`/git/repositories/${projectId}/initialize`);

// Clone repository
await apiClient.post(`/git/repositories/${projectId}/clone`, {
  url: 'https://github.com/user/repo.git',
  branch: 'main'
});

// Create commit
const commit = await apiClient.post('/git/commits', {
  project_id: projectId,
  message: 'feat: implement new feature',
  files: ['src/app.ts', 'src/utils.ts']
});

// List commits
const commits = await apiClient.get(`/git/projects/${projectId}/commits`);

// Push commits
await apiClient.post(`/git/projects/${projectId}/push`);

// Pull commits
await apiClient.post(`/git/projects/${projectId}/pull`);
```

### OpenSpec API
```typescript
// List OpenSpec proposals
const proposals = await apiClient.get('/api/v1/openspec/proposals');

// Create proposal
const proposal = await apiClient.post('/api/v1/openspec/proposals', {
  title: 'New Feature Proposal',
  description: 'Detailed description of the proposed change',
  change_type: 'feature',
  priority: 'high'
});

// Get proposal details
const proposalDetails = await apiClient.get(`/api/v1/openspec/proposals/${proposalId}`);

// Update proposal
await apiClient.patch(`/api/v1/openspec/proposals/${proposalId}`, {
  title: 'Updated Title',
  description: 'Updated description'
});

// Generate spec from proposal
const spec = await apiClient.post(`/api/v1/openspec/proposals/${proposalId}/generate-spec`);
```

---

## Error Handling

### Standard Error Response Format
```typescript
interface APIError {
  detail: string;
  code?: string;
}
```

### HTTP Status Codes

- **200 OK** - Successful GET/PATCH
- **201 Created** - Successful POST
- **204 No Content** - Successful DELETE
- **400 Bad Request** - Validation error
- **401 Unauthorized** - Not authenticated (no token or invalid token)
- **403 Forbidden** - Not authorized (insufficient permissions)
- **404 Not Found** - Resource doesn't exist
- **429 Too Many Requests** - Rate limit exceeded
- **500 Internal Server Error** - Server error

### Error Handling Example
```typescript
try {
  const task = await apiClient.post('/api/v1/tasks', taskData);
} catch (error) {
  if (axios.isAxiosError(error) && error.response) {
    const status = error.response.status;
    const detail = error.response.data.detail;

    switch (status) {
      case 400:
        toast.error(`Invalid input: ${detail}`);
        break;
      case 401:
        // Handled by interceptor, but can add custom logic
        router.push('/login');
        break;
      case 403:
        toast.error('You do not have permission for this action');
        break;
      case 404:
        toast.error('Resource not found');
        break;
      case 429:
        toast.error('Too many requests. Please wait and try again.');
        break;
      case 500:
        toast.error('Server error. Please try again later.');
        break;
      default:
        toast.error('An error occurred');
    }
  }
}
```

---

## Environment Variables

### Next.js Configuration

**File:** `frontend/.env.local`
```bash
# API Configuration
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_WS_URL=ws://localhost:8000

# OAuth Client IDs (from backend .env)
NEXT_PUBLIC_GITHUB_CLIENT_ID=your_github_client_id
NEXT_PUBLIC_GOOGLE_CLIENT_ID=your_google_client_id

# Feature Flags
NEXT_PUBLIC_ENABLE_NOTIFICATIONS=true
NEXT_PUBLIC_ENABLE_WEBSOCKET=true
NEXT_PUBLIC_ENABLE_AI_CHAT=true
NEXT_PUBLIC_ENABLE_GIT=true
NEXT_PUBLIC_ENABLE_DATABASES=true

# Optional: Analytics
NEXT_PUBLIC_GA_ID=G-XXXXXXXXXX
```

### Production Configuration

**File:** `frontend/.env.production`
```bash
NEXT_PUBLIC_API_URL=https://api.ardha.dev
NEXT_PUBLIC_WS_URL=wss://api.ardha.dev
# ... rest of production values
```

---

## Rate Limiting

**Backend rate limits per endpoint:**
- Authentication: 10 requests/minute
- General API: 100 requests/minute
- AI Chat: 20 requests/minute

**Rate limit headers in responses:**
- `X-RateLimit-Limit`: Total requests allowed
- `X-RateLimit-Remaining`: Requests remaining
- `X-RateLimit-Reset`: Unix timestamp when limit resets

**Handling rate limits:**
```typescript
apiClient.interceptors.response.use(
  (response) => {
    // Check rate limit headers
    const remaining = response.headers['x-ratelimit-remaining'];
    if (remaining && parseInt(remaining) < 10) {
      console.warn('Approaching rate limit');
    }
    return response;
  },
  (error) => {
    if (error.response?.status === 429) {
      const resetTime = error.response.headers['x-ratelimit-reset'];
      toast.error(`Rate limit exceeded. Try again at ${new Date(resetTime * 1000).toLocaleTimeString()}`);
    }
    return Promise.reject(error);
  }
);
```

---

## Pagination

**All list endpoints support pagination:**
```typescript
// Request with pagination
const response = await apiClient.get('/api/v1/tasks', {
  params: {
    skip: 0,     // Offset (default 0)
    limit: 50,   // Page size (default 50, max 100)
  }
});

// Response format
interface PaginatedResponse<T> {
  items: T[];
  total: number;
  skip: number;
  limit: number;
}
```

---

## TypeScript Types

**Generate types from OpenAPI spec:**
```bash
# Install openapi-typescript
npm install -D openapi-typescript

# Generate types
npx openapi-typescript http://localhost:8000/openapi.json --output types/api.ts
```

**Import and use:**
```typescript
import type { paths } from '@/types/api';

// Get response type for specific endpoint
type ProjectListResponse = paths['/api/v1/projects']['get']['responses']['200']['content']['application/json'];
```

---

## Testing the API

### Using API Documentation

1. Visit: http://localhost:8000/docs
2. Click "Authorize" button
3. Enter Bearer token: `<your_access_token>`
4. Try any endpoint interactively

### Using Postman

1. Import collection: `docs/api/Ardha_API_Collection.json`
2. Set environment variable `access_token`
3. Run requests

---

## Troubleshooting

### CORS Errors

**Symptoms:** Network errors in browser console

**Solutions:**
1. Verify backend CORS includes `http://localhost:3000`
2. Check `NEXT_PUBLIC_API_URL` environment variable
3. Ensure credentials mode if needed

### 401 Errors on All Requests

**Symptoms:** Every request returns 401

**Solutions:**
1. Check token exists: `localStorage.getItem('access_token')`
2. Verify token format: Should be JWT string
3. Check Authorization header: Should be `Bearer <token>`
4. Try logging in again

### WebSocket Connection Fails

**Symptoms:** WebSocket closes immediately

**Solutions:**
1. Verify token in query parameter
2. Check WebSocket URL (ws:// not wss:// for local)
3. Ensure backend WebSocket endpoint is running

---

## Next Steps

1. **Setup Environment**: Copy `.env.example` to `.env.local`
2. **Install Dependencies**: `npm install axios`
3. **Create API Client**: Use examples above
4. **Test Authentication**: Login and verify token storage
5. **Start Building**: Begin implementing features

---

For complete API documentation, see:
- [API Reference](./API_REFERENCE.md)
- [OpenAPI Spec](./api/openapi.json)
- [Architecture](./ARCHITECTURE.md)
