import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { api } from "@/lib/api";
import type { Model, Page, PredictionResponse } from "@/types/api";

export function useModels(projectId: string | undefined, page = 1, size = 20) {
  return useQuery({
    queryKey: ["models", projectId, page, size],
    enabled: Boolean(projectId),
    queryFn: async () => {
      const { data } = await api.get<Page<Model>>(`/projects/${projectId}/models`, {
        params: { page, size },
      });
      return data;
    },
  });
}

export function useModel(id: string | undefined) {
  return useQuery({
    queryKey: ["model", id],
    enabled: Boolean(id),
    queryFn: async () => {
      const { data } = await api.get<Model>(`/models/${id}`);
      return data;
    },
  });
}

export function useRegisterModel() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (payload: { run_id: string; name: string; deploy?: boolean }) => {
      const { data } = await api.post<Model>("/models", payload);
      return data;
    },
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["models"] }),
  });
}

export function useDeployModel() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (id: string) => {
      const { data } = await api.post<Model>(`/models/${id}/deploy`);
      return data;
    },
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["models"] }),
  });
}

export function usePredict(modelId: string) {
  return useMutation({
    mutationFn: async (records: Record<string, unknown>[]) => {
      const { data } = await api.post<PredictionResponse>(`/models/${modelId}/predict`, {
        records,
      });
      return data;
    },
  });
}
