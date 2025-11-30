import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useAuthStore } from "@/lib/auth-store";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export interface Task {
  id: number;
  title: string;
  description: string | null;
  status: "todo" | "in_progress" | "in_review" | "done" | "blocked";
  priority: "low" | "medium" | "high" | "urgent";
  due_date: string | null;
  created_at: string;
  updated_at: string;
  project_id: number;
  assigned_to: number | null;
  created_by: number;
}

interface TasksResponse {
  items: Task[];
  total: number;
  page: number;
  size: number;
  pages: number;
}

// Get tasks for a specific project
export function useProjectTasks(projectId: number | null) {
  const { accessToken } = useAuthStore();

  return useQuery({
    queryKey: ["tasks", projectId],
    queryFn: async () => {
      if (!projectId) return { items: [], total: 0 };

      const response = await fetch(
        `${API_BASE_URL}/api/v1/projects/${projectId}/tasks?limit=100`,
        {
          headers: {
            Authorization: `Bearer ${accessToken}`,
          },
        },
      );

      if (!response.ok) {
        throw new Error("Failed to fetch tasks");
      }

      return response.json() as Promise<TasksResponse>;
    },
    enabled: !!accessToken && !!projectId,
  });
}

// Get all tasks across all projects
export function useAllTasks() {
  const { accessToken } = useAuthStore();

  return useQuery({
    queryKey: ["tasks", "all"],
    queryFn: async () => {
      // First get all projects
      const projectsResponse = await fetch(`${API_BASE_URL}/api/v1/projects`, {
        headers: {
          Authorization: `Bearer ${accessToken}`,
        },
      });

      if (!projectsResponse.ok) {
        return [];
      }

      const projectsData = await projectsResponse.json();
      const projects = projectsData.items || [];

      // Then fetch tasks from all projects
      const allTasksPromises = projects.map(async (project: any) => {
        const tasksResponse = await fetch(
          `${API_BASE_URL}/api/v1/projects/${project.id}/tasks?limit=100`,
          {
            headers: {
              Authorization: `Bearer ${accessToken}`,
            },
          },
        );

        if (tasksResponse.ok) {
          const data = await tasksResponse.json();
          return data.items || [];
        }
        return [];
      });

      const tasksArrays = await Promise.all(allTasksPromises);
      return tasksArrays.flat() as Task[];
    },
    enabled: !!accessToken,
  });
}

// Update task status (for drag-and-drop)
export function useUpdateTaskStatus() {
  const { accessToken } = useAuthStore();
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async ({
      projectId,
      taskId,
      status,
    }: {
      projectId: number;
      taskId: number;
      status: Task["status"];
    }) => {
      const response = await fetch(
        `${API_BASE_URL}/api/v1/projects/${projectId}/tasks/${taskId}`,
        {
          method: "PATCH",
          headers: {
            Authorization: `Bearer ${accessToken}`,
            "Content-Type": "application/json",
          },
          body: JSON.stringify({ status }),
        },
      );

      if (!response.ok) {
        throw new Error("Failed to update task");
      }

      return response.json();
    },
    onSuccess: () => {
      // Invalidate tasks queries to refetch
      queryClient.invalidateQueries({ queryKey: ["tasks"] });
    },
  });
}

// Create new task
export function useCreateTask() {
  const { accessToken } = useAuthStore();
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async ({
      projectId,
      data,
    }: {
      projectId: number;
      data: Partial<Task>;
    }) => {
      const response = await fetch(
        `${API_BASE_URL}/api/v1/projects/${projectId}/tasks`,
        {
          method: "POST",
          headers: {
            Authorization: `Bearer ${accessToken}`,
            "Content-Type": "application/json",
          },
          body: JSON.stringify(data),
        },
      );

      if (!response.ok) {
        throw new Error("Failed to create task");
      }

      return response.json();
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["tasks"] });
    },
  });
}

// Legacy hooks for dashboard compatibility
export function useRecentTasks(limit: number = 10) {
  const { accessToken } = useAuthStore();

  return useQuery({
    queryKey: ["recent-tasks", limit],
    queryFn: async () => {
      // Get all projects first
      const projectsResponse = await fetch(`${API_BASE_URL}/api/v1/projects`, {
        headers: {
          Authorization: `Bearer ${accessToken}`,
        },
      });

      if (!projectsResponse.ok) {
        return [];
      }

      const projectsData = await projectsResponse.json();
      const projects = projectsData.items || [];

      if (projects.length === 0) {
        return [];
      }

      // Get tasks from first project (or aggregate from all)
      const firstProject = projects[0];
      const tasksResponse = await fetch(
        `${API_BASE_URL}/api/v1/projects/${firstProject.id}/tasks?limit=${limit}`,
        {
          headers: {
            Authorization: `Bearer ${accessToken}`,
          },
        },
      );

      if (!tasksResponse.ok) {
        return [];
      }

      const tasksData = await tasksResponse.json();
      return (tasksData.items || []) as Task[];
    },
    enabled: !!accessToken,
  });
}

export function useTaskStats() {
  const { accessToken } = useAuthStore();

  return useQuery({
    queryKey: ["task-stats"],
    queryFn: async () => {
      // Get all projects
      const projectsResponse = await fetch(`${API_BASE_URL}/api/v1/projects`, {
        headers: {
          Authorization: `Bearer ${accessToken}`,
        },
      });

      if (!projectsResponse.ok) {
        return { total: 0, thisWeek: 0, completed: 0 };
      }

      const projectsData = await projectsResponse.json();
      const projects = projectsData.items || [];

      let totalTasks = 0;
      let completedTasks = 0;

      // Aggregate task counts from all projects
      for (const project of projects) {
        const tasksResponse = await fetch(
          `${API_BASE_URL}/api/v1/projects/${project.id}/tasks`,
          {
            headers: {
              Authorization: `Bearer ${accessToken}`,
            },
          },
        );

        if (tasksResponse.ok) {
          const tasksData = await tasksResponse.json();
          const tasks = tasksData.items || [];
          totalTasks += tasks.length;
          completedTasks += tasks.filter(
            (t: Task) => t.status === "done",
          ).length;
        }
      }

      return {
        total: totalTasks,
        thisWeek: totalTasks, // Simplified - could filter by date
        completed: completedTasks,
      };
    },
    enabled: !!accessToken,
  });
}
