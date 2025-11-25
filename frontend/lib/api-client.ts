/**
 * Ardha API Client
 *
 * Production-ready TypeScript client for Ardha backend API
 *
 * Features:
 * - Type-safe API calls
 * - Automatic token refresh
 * - Error handling
 * - Request/response interceptors
 *
 * Usage:
 * ```typescript
 * import { ArdhaClient } from './api-client';
 *
 * const client = new ArdhaClient('http://localhost:8000');
 * await client.auth.login('email@example.com', 'password');
 * const projects = await client.projects.list();
 * ```
 */

// Using native fetch API instead of axios for better compatibility and no additional dependencies

// ============================================================================
// Type Definitions
// ============================================================================

export interface User {
  id: string;
  email: string;
  username: string;
  full_name: string;
  avatar_url?: string;
  github_id?: string;
  google_id?: string;
  is_active: boolean;
  is_superuser: boolean;
  created_at: string;
  updated_at: string;
}

export interface AuthResponse {
  access_token: string;
  refresh_token: string;
  token_type: "bearer";
  user: User;
}

export interface Project {
  id: string;
  name: string;
  description?: string;
  slug: string;
  owner_id: string;
  is_archived: boolean;
  created_at: string;
  updated_at: string;
}

export interface Task {
  id: string;
  identifier: string;
  title: string;
  description?: string;
  project_id: string;
  status: "todo" | "in_progress" | "review" | "done" | "cancelled";
  priority: "low" | "medium" | "high" | "urgent";
  assigned_to_id?: string;
  created_by_id: string;
  due_date?: string;
  completed_at?: string;
  created_at: string;
  updated_at: string;
}

export interface Chat {
  id: string;
  title: string;
  user_id: string;
  project_id?: string;
  mode: "research" | "architect" | "implement" | "debug" | "chat";
  model?: string;
  is_archived: boolean;
  created_at: string;
  updated_at: string;
}

export interface Message {
  id: string;
  chat_id: string;
  role: "user" | "assistant" | "system";
  content: string;
  tokens?: number;
  model_used?: string;
  created_at: string;
}

export interface Notification {
  id: string;
  user_id: string;
  type: string;
  title: string;
  message: string;
  data?: Record<string, any>;
  link_type?: string;
  link_id?: string;
  is_read: boolean;
  read_at?: string;
  created_at: string;
  expires_at?: string;
}

export interface NotificationPreferences {
  id: string;
  user_id: string;
  email_enabled: boolean;
  push_enabled: boolean;
  task_assigned: boolean;
  task_completed: boolean;
  task_overdue: boolean;
  mentions: boolean;
  project_invites: boolean;
  database_updates: boolean;
  system_notifications: boolean;
  email_frequency: "instant" | "daily" | "weekly" | "never";
  quiet_hours_start?: string;
  quiet_hours_end?: string;
}

export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  skip: number;
  limit: number;
}

export interface APIError {
  detail: string;
  code?: string;
}

// ============================================================================
// Main Client
// ============================================================================

export class ArdhaClient {
  public baseURL: string;
  private accessToken?: string;
  private refreshToken?: string;

  public auth: AuthAPI;
  public projects: ProjectsAPI;
  public tasks: TasksAPI;
  public chats: ChatsAPI;
  public notifications: NotificationsAPI;

  constructor(baseURL: string = "http://localhost:8000") {
    this.baseURL = baseURL;

    // Initialize sub-APIs
    this.auth = new AuthAPI(this);
    this.projects = new ProjectsAPI(this);
    this.tasks = new TasksAPI(this);
    this.chats = new ChatsAPI(this);
    this.notifications = new NotificationsAPI(this);
  }

  async makeRequest<T>(url: string, options: RequestInit = {}): Promise<T> {
    const headers: Record<string, string> = {
      "Content-Type": "application/json",
      ...((options.headers as Record<string, string>) || {}),
    };

    if (this.accessToken) {
      headers.Authorization = `Bearer ${this.accessToken}`;
    }

    const response = await fetch(`${this.baseURL}${url}`, {
      ...options,
      headers,
    });

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      const error = new Error(
        errorData.detail || `HTTP ${response.status}: ${response.statusText}`,
      );
      (error as any).status = response.status;
      (error as any).data = errorData;
      throw error;
    }

    return response.json();
  }

  async makeRequestWithRefresh<T>(
    url: string,
    options: RequestInit = {},
  ): Promise<T> {
    try {
      return await this.makeRequest<T>(url, options);
    } catch (error: any) {
      const headers = (options.headers as Record<string, string>) || {};
      if (error.status === 401 && this.refreshToken && !headers["X-Retry"]) {
        // Try to refresh the token
        try {
          const refreshResponse = await fetch(
            `${this.baseURL}/api/v1/auth/refresh`,
            {
              method: "POST",
              headers: { "Content-Type": "application/json" },
              body: JSON.stringify({ refresh_token: this.refreshToken }),
            },
          );

          if (refreshResponse.ok) {
            const refreshData = await refreshResponse.json();
            this.accessToken = refreshData.access_token;

            // Retry the original request with the new token
            const retryOptions = {
              ...options,
              headers: {
                ...headers,
                "X-Retry": "true",
              },
            };

            return await this.makeRequest<T>(url, retryOptions);
          }
        } catch (refreshError) {
          // Refresh failed, clear tokens
          this.accessToken = undefined;
          this.refreshToken = undefined;
        }
      }

      throw error;
    }
  }

  setTokens(accessToken: string, refreshToken: string): void {
    this.accessToken = accessToken;
    this.refreshToken = refreshToken;
  }

  getTokens(): { accessToken?: string; refreshToken?: string } {
    return {
      accessToken: this.accessToken,
      refreshToken: this.refreshToken,
    };
  }

  clearTokens(): void {
    this.accessToken = undefined;
    this.refreshToken = undefined;
  }
}

// ============================================================================
// Auth API
// ============================================================================

class AuthAPI {
  constructor(private client: ArdhaClient) {}

  async register(
    email: string,
    username: string,
    password: string,
    fullName: string,
  ): Promise<AuthResponse> {
    const response = await this.client.makeRequestWithRefresh<AuthResponse>(
      "/api/v1/auth/register",
      {
        method: "POST",
        body: JSON.stringify({
          email,
          username,
          password,
          full_name: fullName,
        }),
      },
    );

    this.client.setTokens(response.access_token, response.refresh_token);
    return response;
  }

  async login(email: string, password: string): Promise<AuthResponse> {
    const response = await this.client.makeRequestWithRefresh<AuthResponse>(
      "/api/v1/auth/login",
      {
        method: "POST",
        body: JSON.stringify({
          email,
          password,
        }),
      },
    );

    this.client.setTokens(response.access_token, response.refresh_token);
    return response;
  }

  async logout(): Promise<void> {
    await this.client.makeRequestWithRefresh("/api/v1/auth/logout", {
      method: "POST",
    });
    this.client.clearTokens();
  }

  async me(): Promise<User> {
    return await this.client.makeRequestWithRefresh<User>("/api/v1/auth/me");
  }

  async updateProfile(updates: {
    username?: string;
    full_name?: string;
    avatar_url?: string;
  }): Promise<User> {
    return await this.client.makeRequestWithRefresh<User>("/api/v1/auth/me", {
      method: "PATCH",
      body: JSON.stringify(updates),
    });
  }

  async refresh(refreshToken: string): Promise<{ access_token: string }> {
    const response = await this.client.makeRequest<{ access_token: string }>(
      "/api/v1/auth/refresh",
      {
        method: "POST",
        body: JSON.stringify({
          refresh_token: refreshToken,
        }),
      },
    );

    this.client.setTokens(response.access_token, refreshToken);
    return response;
  }
}

// ============================================================================
// Projects API
// ============================================================================

class ProjectsAPI {
  constructor(private client: ArdhaClient) {}

  async list(params?: { skip?: number; limit?: number }): Promise<Project[]> {
    let url = "/api/v1/projects";
    if (params) {
      const searchParams = new URLSearchParams();
      Object.entries(params).forEach(([key, value]) => {
        if (value !== undefined) {
          searchParams.append(key, value.toString());
        }
      });
      url += `?${searchParams.toString()}`;
    }

    return await this.client.makeRequestWithRefresh<Project[]>(url);
  }

  async get(id: string): Promise<Project> {
    return await this.client.makeRequestWithRefresh<Project>(
      `/api/v1/projects/${id}`,
    );
  }

  async create(data: { name: string; description?: string }): Promise<Project> {
    return await this.client.makeRequestWithRefresh<Project>(
      "/api/v1/projects",
      {
        method: "POST",
        body: JSON.stringify(data),
      },
    );
  }

  async update(
    id: string,
    data: {
      name?: string;
      description?: string;
      is_archived?: boolean;
    },
  ): Promise<Project> {
    return await this.client.makeRequestWithRefresh<Project>(
      `/api/v1/projects/${id}`,
      {
        method: "PATCH",
        body: JSON.stringify(data),
      },
    );
  }

  async delete(id: string): Promise<void> {
    await this.client.makeRequestWithRefresh(`/api/v1/projects/${id}`, {
      method: "DELETE",
    });
  }
}

// ============================================================================
// Tasks API
// ============================================================================

class TasksAPI {
  constructor(private client: ArdhaClient) {}

  async list(params?: {
    project_id?: string;
    status?: string;
    priority?: string;
    assigned_to_id?: string;
    skip?: number;
    limit?: number;
  }): Promise<Task[]> {
    let url = "/api/v1/tasks";
    if (params) {
      const searchParams = new URLSearchParams();
      Object.entries(params).forEach(([key, value]) => {
        if (value !== undefined) {
          searchParams.append(key, value.toString());
        }
      });
      url += `?${searchParams.toString()}`;
    }

    return await this.client.makeRequestWithRefresh<Task[]>(url);
  }

  async get(id: string): Promise<Task> {
    return await this.client.makeRequestWithRefresh<Task>(
      `/api/v1/tasks/${id}`,
    );
  }

  async create(data: {
    title: string;
    project_id: string;
    description?: string;
    status?: string;
    priority?: string;
    assigned_to_id?: string;
    due_date?: string;
  }): Promise<Task> {
    return await this.client.makeRequestWithRefresh<Task>("/api/v1/tasks", {
      method: "POST",
      body: JSON.stringify(data),
    });
  }

  async update(
    id: string,
    data: {
      title?: string;
      description?: string;
      status?: string;
      priority?: string;
      assigned_to_id?: string;
      due_date?: string;
    },
  ): Promise<Task> {
    return await this.client.makeRequestWithRefresh<Task>(
      `/api/v1/tasks/${id}`,
      {
        method: "PATCH",
        body: JSON.stringify(data),
      },
    );
  }

  async delete(id: string): Promise<void> {
    await this.client.makeRequestWithRefresh(`/api/v1/tasks/${id}`, {
      method: "DELETE",
    });
  }

  async addDependency(taskId: string, dependsOnTaskId: string): Promise<void> {
    await this.client.makeRequestWithRefresh(
      `/api/v1/tasks/${taskId}/dependencies`,
      {
        method: "POST",
        body: JSON.stringify({
          depends_on_task_id: dependsOnTaskId,
        }),
      },
    );
  }

  async removeDependency(taskId: string, dependencyId: string): Promise<void> {
    await this.client.makeRequestWithRefresh(
      `/api/v1/tasks/${taskId}/dependencies/${dependencyId}`,
      {
        method: "DELETE",
      },
    );
  }
}

// ============================================================================
// Chats API
// ============================================================================

class ChatsAPI {
  constructor(private client: ArdhaClient) {}

  async list(params?: { skip?: number; limit?: number }): Promise<Chat[]> {
    let url = "/api/v1/chats";
    if (params) {
      const searchParams = new URLSearchParams();
      Object.entries(params).forEach(([key, value]) => {
        if (value !== undefined) {
          searchParams.append(key, value.toString());
        }
      });
      url += `?${searchParams.toString()}`;
    }

    return await this.client.makeRequestWithRefresh<Chat[]>(url);
  }

  async get(id: string): Promise<Chat> {
    return await this.client.makeRequestWithRefresh<Chat>(
      `/api/v1/chats/${id}`,
    );
  }

  async create(data: {
    title: string;
    mode: string;
    project_id?: string;
  }): Promise<Chat> {
    return await this.client.makeRequestWithRefresh<Chat>("/api/v1/chats", {
      method: "POST",
      body: JSON.stringify(data),
    });
  }

  async update(
    id: string,
    data: {
      title?: string;
      is_archived?: boolean;
    },
  ): Promise<Chat> {
    return await this.client.makeRequestWithRefresh<Chat>(
      `/api/v1/chats/${id}`,
      {
        method: "PATCH",
        body: JSON.stringify(data),
      },
    );
  }

  async delete(id: string): Promise<void> {
    await this.client.makeRequestWithRefresh(`/api/v1/chats/${id}`, {
      method: "DELETE",
    });
  }

  async sendMessage(
    chatId: string,
    content: string,
    model?: string,
  ): Promise<Message> {
    return await this.client.makeRequestWithRefresh<Message>(
      `/api/v1/chats/${chatId}/messages`,
      {
        method: "POST",
        body: JSON.stringify({ content, model }),
      },
    );
  }

  async getMessages(chatId: string): Promise<Message[]> {
    return await this.client.makeRequestWithRefresh<Message[]>(
      `/api/v1/chats/${chatId}/messages`,
    );
  }

  /**
   * Connect to chat WebSocket for streaming responses
   */
  connectWebSocket(chatId: string, token: string, baseURL: string): WebSocket {
    const wsURL = baseURL.replace("http", "ws");
    const ws = new WebSocket(
      `${wsURL}/api/v1/chats/${chatId}/ws?token=${token}`,
    );
    return ws;
  }
}

// ============================================================================
// Notifications API
// ============================================================================

class NotificationsAPI {
  constructor(private client: ArdhaClient) {}

  async list(params?: {
    unread_only?: boolean;
    skip?: number;
    limit?: number;
  }): Promise<Notification[]> {
    let url = "/api/v1/notifications";
    if (params) {
      const searchParams = new URLSearchParams();
      Object.entries(params).forEach(([key, value]) => {
        if (value !== undefined) {
          searchParams.append(key, value.toString());
        }
      });
      url += `?${searchParams.toString()}`;
    }

    return await this.client.makeRequestWithRefresh<Notification[]>(url);
  }

  async markAsRead(id: string): Promise<void> {
    await this.client.makeRequestWithRefresh(
      `/api/v1/notifications/${id}/read`,
      {
        method: "PATCH",
      },
    );
  }

  async markAllAsRead(): Promise<void> {
    await this.client.makeRequestWithRefresh(
      "/api/v1/notifications/mark-all-read",
      {
        method: "POST",
      },
    );
  }

  async delete(id: string): Promise<void> {
    await this.client.makeRequestWithRefresh(`/api/v1/notifications/${id}`, {
      method: "DELETE",
    });
  }

  async getPreferences(): Promise<NotificationPreferences> {
    return await this.client.makeRequestWithRefresh<NotificationPreferences>(
      "/api/v1/notifications/preferences",
    );
  }

  async updatePreferences(
    updates: Partial<Omit<NotificationPreferences, "id" | "user_id">>,
  ): Promise<NotificationPreferences> {
    return await this.client.makeRequestWithRefresh<NotificationPreferences>(
      "/api/v1/notifications/preferences",
      {
        method: "PATCH",
        body: JSON.stringify(updates),
      },
    );
  }

  /**
   * Connect to notifications WebSocket
   */
  connectWebSocket(token: string, baseURL: string): WebSocket {
    const wsURL = baseURL.replace("http", "ws");
    const ws = new WebSocket(`${wsURL}/api/v1/ws/notifications?token=${token}`);
    return ws;
  }
}

// ============================================================================
// Export
// ============================================================================

export default ArdhaClient;
