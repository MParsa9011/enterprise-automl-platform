import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { api } from "@/lib/api";
import type { Dataset, DatasetVersion, Page } from "@/types/api";

export function useDatasets(projectId: string | undefined, page = 1, size = 20) {
  return useQuery({
    queryKey: ["datasets", projectId, page, size],
    enabled: Boolean(projectId),
    queryFn: async () => {
      const { data } = await api.get<Page<Dataset>>(`/projects/${projectId}/datasets`, {
        params: { page, size },
      });
      return data;
    },
  });
}

export function useDataset(id: string | undefined) {
  return useQuery({
    queryKey: ["dataset", id],
    enabled: Boolean(id),
    queryFn: async () => {
      const { data } = await api.get<Dataset>(`/datasets/${id}`);
      return data;
    },
  });
}

export function useDatasetVersion(datasetId: string | undefined, version: number | undefined) {
  return useQuery({
    queryKey: ["dataset-version", datasetId, version],
    enabled: Boolean(datasetId && version),
    queryFn: async () => {
      const { data } = await api.get<DatasetVersion>(
        `/datasets/${datasetId}/versions/${version}`,
      );
      return data;
    },
  });
}

export function useUploadDataset(projectId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (payload: { name: string; description?: string; file: File }) => {
      const form = new FormData();
      form.append("name", payload.name);
      if (payload.description) form.append("description", payload.description);
      form.append("file", payload.file);
      const { data } = await api.post<Dataset>(`/projects/${projectId}/datasets`, form, {
        headers: { "Content-Type": "multipart/form-data" },
      });
      return data;
    },
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["datasets", projectId] }),
  });
}
