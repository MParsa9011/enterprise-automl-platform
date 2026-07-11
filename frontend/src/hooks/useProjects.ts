import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { api } from "@/lib/api";
import type { Page, Project } from "@/types/api";

export function useProjects(page = 1, size = 20, search = "") {
  return useQuery({
    queryKey: ["projects", page, size, search],
    queryFn: async () => {
      const { data } = await api.get<Page<Project>>("/projects", {
        params: { page, size, search: search || undefined },
      });
      return data;
    },
  });
}

export function useProject(id: string | undefined) {
  return useQuery({
    queryKey: ["project", id],
    enabled: Boolean(id),
    queryFn: async () => {
      const { data } = await api.get<Project>(`/projects/${id}`);
      return data;
    },
  });
}

export function useCreateProject() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (payload: { name: string; description?: string }) => {
      const { data } = await api.post<Project>("/projects", payload);
      return data;
    },
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["projects"] }),
  });
}

export function useDeleteProject() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (id: string) => {
      await api.delete(`/projects/${id}`);
    },
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["projects"] }),
  });
}
