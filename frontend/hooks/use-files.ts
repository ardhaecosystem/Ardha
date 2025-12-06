import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useAuthStore } from "@/lib/auth-store";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export interface File {
  id: number;
  name: string;
  size: number;
  type: string;
  path: string;
  project_id: number;
  uploaded_by: number;
  created_at: string;
  updated_at: string;
  url?: string;
}

export interface Folder {
  id: number;
  name: string;
  path: string;
  project_id: number;
  created_at: string;
}

// Get all files for a project
export function useFiles(projectId: number | null) {
  const { accessToken } = useAuthStore();

  return useQuery({
    queryKey: ["files", projectId],
    queryFn: async () => {
      if (!projectId) return [];

      const response = await fetch(
        `${API_BASE_URL}/api/v1/projects/${projectId}/files`,
        {
          headers: {
            Authorization: `Bearer ${accessToken}`,
          },
        },
      );

      if (!response.ok) {
        throw new Error("Failed to fetch files");
      }

      const data = await response.json();
      return data.items as File[];
    },
    enabled: !!accessToken && !!projectId,
  });
}

// Upload file
export function useUploadFile() {
  const { accessToken } = useAuthStore();
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async ({
      projectId,
      file,
    }: {
      projectId: number;
      file: globalThis.File;
    }) => {
      const formData = new FormData();
      formData.append("file", file);

      const response = await fetch(
        `${API_BASE_URL}/api/v1/projects/${projectId}/files`,
        {
          method: "POST",
          headers: {
            Authorization: `Bearer ${accessToken}`,
          },
          body: formData,
        },
      );

      if (!response.ok) {
        throw new Error("Failed to upload file");
      }

      return response.json();
    },
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({
        queryKey: ["files", variables.projectId],
      });
    },
  });
}

// Delete file
export function useDeleteFile() {
  const { accessToken } = useAuthStore();
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async ({
      projectId,
      fileId,
    }: {
      projectId: number;
      fileId: number;
    }) => {
      const response = await fetch(
        `${API_BASE_URL}/api/v1/projects/${projectId}/files/${fileId}`,
        {
          method: "DELETE",
          headers: {
            Authorization: `Bearer ${accessToken}`,
          },
        },
      );

      if (!response.ok) {
        throw new Error("Failed to delete file");
      }
    },
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({
        queryKey: ["files", variables.projectId],
      });
    },
  });
}
