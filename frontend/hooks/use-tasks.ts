import { useQuery } from "@tanstack/react-query";
import { useAuthStore } from "@/lib/auth-store";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

interface Task {
  id: number;
  title: string;
  description: string;
  status: string;
  priority: string;
  due_date: string | null;
  created_at: string;
  updated_at: string;
  project_id: number;
}

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
