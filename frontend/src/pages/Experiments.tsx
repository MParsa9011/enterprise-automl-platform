import { FlaskConical, Play } from "lucide-react";
import { useState } from "react";
import { useForm } from "react-hook-form";

import { ProjectPicker } from "@/components/ProjectPicker";
import { PageHeader } from "@/components/ui/PageHeader";
import { Card, CardBody, CardHeader } from "@/components/ui/Card";
import { Modal } from "@/components/ui/Modal";
import { Spinner } from "@/components/ui/Spinner";
import { StatusBadge } from "@/components/ui/Badge";
import { EmptyState, ErrorState, LoadingState } from "@/components/ui/StateViews";
import { useDatasets } from "@/hooks/useDatasets";
import {
  useCreateExperiment,
  useExperiment,
  useExperiments,
  type ExperimentCreate,
} from "@/hooks/useExperiments";
import { useRegisterModel } from "@/hooks/useModels";
import { useProjectSelection } from "@/hooks/useProjectSelection";
import { apiErrorMessage } from "@/lib/api";
import { formatMetric } from "@/lib/utils";
import type { Experiment } from "@/types/api";

/** Experiments list, creation and run inspection. */
export function Experiments() {
  const { projectId, setProjectId } = useProjectSelection();
  const [createOpen, setCreateOpen] = useState(false);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const { data, isLoading, isError, error, refetch } = useExperiments(projectId ?? undefined);

  return (
    <div>
      <PageHeader
        title="Experiments"
        description="Train and tune many algorithms, then pick the winner."
        action={
          projectId && (
            <button className="btn-primary" onClick={() => setCreateOpen(true)}>
              <Play className="h-4 w-4" /> New experiment
            </button>
          )
        }
      />

      <div className="mb-4">
        <ProjectPicker projectId={projectId} onChange={setProjectId} />
      </div>

      {projectId && isLoading && <LoadingState />}
      {isError && <ErrorState message={apiErrorMessage(error)} onRetry={refetch} />}
      {data && data.items.length === 0 && (
        <EmptyState title="No experiments" description="Launch one to start training." />
      )}

      <div className="space-y-3">
        {data?.items.map((experiment) => (
          <Card key={experiment.id} className="p-4">
            <div className="flex items-center justify-between gap-4">
              <div className="flex items-center gap-3">
                <FlaskConical className="h-6 w-6 text-purple-500" />
                <div>
                  <h3 className="font-semibold text-slate-900 dark:text-slate-100">
                    {experiment.name}
                  </h3>
                  <p className="text-xs text-slate-500">
                    {experiment.task_type} · {experiment.algorithms.length} algorithms ·{" "}
                    {experiment.primary_metric}
                  </p>
                </div>
              </div>
              <div className="flex items-center gap-3">
                <StatusBadge status={experiment.status} />
                <button
                  className="text-sm font-medium text-brand-600 hover:underline"
                  onClick={() => setSelectedId(experiment.id)}
                >
                  View runs
                </button>
              </div>
            </div>
          </Card>
        ))}
      </div>

      {projectId && (
        <CreateExperimentModal
          open={createOpen}
          onClose={() => setCreateOpen(false)}
          projectId={projectId}
        />
      )}
      <ExperimentDetail experimentId={selectedId} onClose={() => setSelectedId(null)} />
    </div>
  );
}

function CreateExperimentModal({
  open,
  onClose,
  projectId,
}: {
  open: boolean;
  onClose: () => void;
  projectId: string;
}) {
  const { data: datasets } = useDatasets(projectId, 1, 100);
  const create = useCreateExperiment(projectId);
  const { register, handleSubmit, reset, formState } = useForm<ExperimentCreate>({
    defaultValues: { task_type: "classification", optimize: false, cv_folds: 3 },
  });

  const onSubmit = handleSubmit(async (values) => {
    await create.mutateAsync({ ...values, cv_folds: Number(values.cv_folds) });
    reset();
    onClose();
  });

  return (
    <Modal open={open} onClose={onClose} title="New experiment">
      <form onSubmit={onSubmit} className="space-y-4">
        <div>
          <label className="label">Name</label>
          <input className="input" {...register("name", { required: true })} autoFocus />
        </div>
        <div>
          <label className="label">Dataset</label>
          <select className="input" {...register("dataset_id", { required: true })}>
            {datasets?.items.map((dataset) => (
              <option key={dataset.id} value={dataset.id}>
                {dataset.name}
              </option>
            ))}
          </select>
        </div>
        <div className="grid grid-cols-2 gap-3">
          <div>
            <label className="label">Task</label>
            <select className="input" {...register("task_type")}>
              <option value="classification">Classification</option>
              <option value="regression">Regression</option>
            </select>
          </div>
          <div>
            <label className="label">Target column</label>
            <input className="input" {...register("target_column", { required: true })} />
          </div>
        </div>
        <div className="grid grid-cols-2 gap-3">
          <div>
            <label className="label">CV folds</label>
            <input type="number" min={2} max={10} className="input" {...register("cv_folds")} />
          </div>
          <label className="flex items-end gap-2 pb-2 text-sm text-slate-600 dark:text-slate-300">
            <input type="checkbox" {...register("optimize")} className="h-4 w-4" />
            Optuna tuning
          </label>
        </div>
        {create.isError && <p className="text-sm text-red-500">{apiErrorMessage(create.error)}</p>}
        <div className="flex justify-end gap-2">
          <button type="button" className="btn-secondary" onClick={onClose}>
            Cancel
          </button>
          <button type="submit" className="btn-primary" disabled={formState.isSubmitting}>
            {formState.isSubmitting ? (
              <>
                <Spinner className="h-4 w-4 text-white" /> Training…
              </>
            ) : (
              "Launch"
            )}
          </button>
        </div>
      </form>
    </Modal>
  );
}

function ExperimentDetail({
  experimentId,
  onClose,
}: {
  experimentId: string | null;
  onClose: () => void;
}) {
  const { data, isLoading } = useExperiment(experimentId ?? undefined);
  const registerModel = useRegisterModel();

  if (!experimentId) return null;

  return (
    <Modal open={Boolean(experimentId)} onClose={onClose} title={data?.name ?? "Experiment"}>
      {isLoading || !data ? (
        <LoadingState />
      ) : (
        <RunsTable experiment={data} onRegister={(runId) => registerModel.mutate({ run_id: runId, name: data.name, deploy: false })} />
      )}
    </Modal>
  );
}

function RunsTable({
  experiment,
  onRegister,
}: {
  experiment: Experiment;
  onRegister: (runId: string) => void;
}) {
  const runs = [...(experiment.runs ?? [])].sort(
    (a, b) => (b.primary_score ?? -Infinity) - (a.primary_score ?? -Infinity),
  );

  return (
    <Card>
      <CardHeader title={`Runs · ${experiment.primary_metric}`} />
      <CardBody className="max-h-96 overflow-y-auto p-0">
        <table className="w-full text-sm">
          <thead className="sticky top-0 bg-slate-50 text-left text-xs uppercase text-slate-500 dark:bg-slate-800">
            <tr>
              <th className="px-4 py-2">Algorithm</th>
              <th className="px-4 py-2">Status</th>
              <th className="px-4 py-2">Score</th>
              <th className="px-4 py-2" />
            </tr>
          </thead>
          <tbody>
            {runs.map((run) => (
              <tr key={run.id} className="border-t border-slate-100 dark:border-slate-800">
                <td className="px-4 py-2 font-medium">
                  {run.algorithm}
                  {run.id === experiment.best_run_id && (
                    <span className="ml-2 text-xs text-green-600">best</span>
                  )}
                </td>
                <td className="px-4 py-2">
                  <StatusBadge status={run.status} />
                </td>
                <td className="px-4 py-2">{formatMetric(run.primary_score)}</td>
                <td className="px-4 py-2 text-right">
                  {run.status === "completed" && (
                    <button
                      className="text-xs font-medium text-brand-600 hover:underline"
                      onClick={() => onRegister(run.id)}
                    >
                      Register
                    </button>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </CardBody>
    </Card>
  );
}
