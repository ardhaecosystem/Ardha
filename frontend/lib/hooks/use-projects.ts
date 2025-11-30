import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useAuthStore } from "@/lib/auth-store";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export interface Project {
  id: string;
  name: string;
  description: string | null;
  slug: string;
  is_private: boolean;
  owner_id: string;
  created_at: string;
  updated_at: string;
}

export function useProjects() {
  const { accessToken } = useAuthStore();

  return useQuery({
    queryKey: ["projects"],
    queryFn: async () => {
      const response = await fetch(`${API_BASE_URL}/api/v1/projects`, {
        headers: {
          Authorization: `Bearer ${accessToken}`,
        },
      });

      if (!response.ok) {
        throw new Error("Failed to fetch projects");
      }

      return response.json() as Promise<Project[]>;
    },
    enabled: !!accessToken,
  });
}

export function useProject(slug: string) {
  const { accessToken } = useAuthStore();

  return useQuery({
    queryKey: ["project", slug],
    queryFn: async () => {
      const response = await fetch(`${API_BASE_URL}/api/v1/projects/${slug}`, {
        headers: {
          Authorization: `Bearer ${accessToken}`,
        },
      });

      if (!response.ok) {
        throw new Error("Project not found");
      }

      return response.json() as Promise<Project>;
    },
    enabled: !!accessToken && !!slug,
  });
}

export function useCreateProject() {
  const queryClient = useQueryClient();
  const { accessToken } = useAuthStore();

  return useMutation({
    mutationFn: async (data: {
      name: string;
      description?: string;
      is_private?: boolean;
    }) => {
      const response = await fetch(`${API_BASE_URL}/api/v1/projects`, {
        method: "POST",
        headers: {
          Authorization: `Bearer ${accessToken}`,
          "Content-Type": "application/json",
        },
        body: JSON.stringify(data),
      });

      if (!response.ok) {
        throw new Error("Failed to create project");
      }

      return response.json() as Promise<Project>;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["projects"] });
    },
  });
}
