import { useQuery } from "@tanstack/react-query";
import { useAuthStore } from "@/lib/auth-store";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export interface GitRepository {
  id: number;
  name: string;
  description: string;
  url: string;
  default_branch: string;
  project_id: number;
}

export interface GitCommit {
  hash: string;
  message: string;
  author: string;
  date: string;
  files_changed: number;
}

export interface GitBranch {
  name: string;
  last_commit: string;
  last_commit_date: string;
}

// Get repository for project
export function useRepository(projectId: number | null) {
  const { accessToken } = useAuthStore();

  return useQuery({
    queryKey: ["repository", projectId],
    queryFn: async () => {
      if (!projectId) return null;

      const response = await fetch(
        `${API_BASE_URL}/api/v1/projects/${projectId}/git/repository`,
        {
          headers: {
            Authorization: `Bearer ${accessToken}`,
          },
        },
      );

      if (!response.ok) {
        throw new Error("Failed to fetch repository");
      }

      return response.json() as Promise<GitRepository>;
    },
    enabled: !!accessToken && !!projectId,
  });
}

// Get commit history
export function useCommits(projectId: number | null, branch?: string) {
  const { accessToken } = useAuthStore();

  return useQuery({
    queryKey: ["commits", projectId, branch],
    queryFn: async () => {
      if (!projectId) return [];

      const url = new URL(
        `${API_BASE_URL}/api/v1/projects/${projectId}/git/commits`,
      );
      if (branch) url.searchParams.append("branch", branch);

      const response = await fetch(url.toString(), {
        headers: {
          Authorization: `Bearer ${accessToken}`,
        },
      });

      if (!response.ok) {
        throw new Error("Failed to fetch commits");
      }

      const data = await response.json();
      return data.items as GitCommit[];
    },
    enabled: !!accessToken && !!projectId,
  });
}

// Get branches
export function useBranches(projectId: number | null) {
  const { accessToken } = useAuthStore();

  return useQuery({
    queryKey: ["branches", projectId],
    queryFn: async () => {
      if (!projectId) return [];

      const response = await fetch(
        `${API_BASE_URL}/api/v1/projects/${projectId}/git/branches`,
        {
          headers: {
            Authorization: `Bearer ${accessToken}`,
          },
        },
      );

      if (!response.ok) {
        throw new Error("Failed to fetch branches");
      }

      const data = await response.json();
      return data.items as GitBranch[];
    },
    enabled: !!accessToken && !!projectId,
  });
}
