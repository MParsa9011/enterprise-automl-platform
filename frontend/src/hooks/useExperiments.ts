import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { api } from "@/lib/api";
import type { Experiment, Page, Run, TaskType } from "@/types/api";

export interface ExperimentCreate {
  name: string;
  description?: string;
  dataset_id: string;
  dataset_version?: number;
  task_type: TaskType;
  target_column?: string;
  algorithms?: string[];
  optimize?: boolean;
  n_trials?: number;
  cv_folds?: number;
}

export function useExperiments(projectId: string | undefined, page = 1, size = 20) {
  return useQuery({
    queryKey: ["experiments", projectId, page, size],
    enabled: Boolean(projectId),
    queryFn: async () => {
      const { data } = await api.get<Page<Experiment>>(`/projects/${projectId}/experiments`, {
        params: { page, size },
      });
      return data;
    },
  });
}

export function useExperiment(id: string | undefined) {
  return useQuery({
    queryKey: ["experiment", id],
    enabled: Boolean(id),
    queryFn: async () => {
      const { data } = await api.get<Experiment>(`/experiments/${id}`);
      return data;
    },
  });
}

export function useRun(experimentId: string | undefined, runId: string | undefined) {
  return useQuery({
    queryKey: ["run", experimentId, runId],
    enabled: Boolean(experimentId && runId),
    queryFn: async () => {
      const { data } = await api.get<Run>(`/experiments/${experimentId}/runs/${runId}`);
      return data;
    },
  });
}

export function useCreateExperiment(projectId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (payload: ExperimentCreate) => {
      const { data } = await api.post<Experiment>(
        `/projects/${projectId}/experiments`,
        payload,
      );
      return data;
    },
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["experiments", projectId] }),
  });
}
