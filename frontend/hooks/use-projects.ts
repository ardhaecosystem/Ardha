import { useQuery } from "@tanstack/react-query";
import { useAuthStore } from "@/lib/auth-store";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

interface Project {
  id: number;
  name: string;
  description: string;
  slug: string;
  is_private: boolean;
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

      const data = await response.json();
      return data.items as Project[];
    },
    enabled: !!accessToken,
  });
}

export function useProjectStats() {
  const { accessToken } = useAuthStore();

  return useQuery({
    queryKey: ["project-stats"],
    queryFn: async () => {
      const response = await fetch(`${API_BASE_URL}/api/v1/projects`, {
        headers: {
          Authorization: `Bearer ${accessToken}`,
        },
      });

      if (!response.ok) {
        return { total: 0, active: 0 };
      }

      const data = await response.json();
      return {
        total: data.total || 0,
        active: data.items?.filter((p: Project) => !p.is_private).length || 0,
      };
    },
    enabled: !!accessToken,
  });
}
