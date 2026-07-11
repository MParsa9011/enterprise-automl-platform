import { Package, Rocket, Sparkles } from "lucide-react";
import { useState } from "react";

import { ProjectPicker } from "@/components/ProjectPicker";
import { PageHeader } from "@/components/ui/PageHeader";
import { Card, CardBody, CardHeader } from "@/components/ui/Card";
import { Modal } from "@/components/ui/Modal";
import { Spinner } from "@/components/ui/Spinner";
import { StatusBadge } from "@/components/ui/Badge";
import { EmptyState, ErrorState, LoadingState } from "@/components/ui/StateViews";
import { useDeployModel, useModels, usePredict } from "@/hooks/useModels";
import { useProjectSelection } from "@/hooks/useProjectSelection";
import { apiErrorMessage } from "@/lib/api";
import { formatMetric } from "@/lib/utils";
import type { Model } from "@/types/api";

/** Model registry: list, deploy and predict. */
export function Models() {
  const { projectId, setProjectId } = useProjectSelection();
  const [predictModel, setPredictModel] = useState<Model | null>(null);
  const { data, isLoading, isError, error, refetch } = useModels(projectId ?? undefined);
  const deploy = useDeployModel();

  return (
    <div>
      <PageHeader title="Model registry" description="Version, deploy and serve your models." />

      <div className="mb-4">
        <ProjectPicker projectId={projectId} onChange={setProjectId} />
      </div>

      {projectId && isLoading && <LoadingState />}
      {isError && <ErrorState message={apiErrorMessage(error)} onRetry={refetch} />}
      {data && data.items.length === 0 && (
        <EmptyState
          title="No models registered"
          description="Register a completed run from the Experiments page."
        />
      )}

      <div className="grid gap-4 lg:grid-cols-2">
        {data?.items.map((model) => (
          <Card key={model.id} className="p-5">
            <div className="flex items-start justify-between">
              <div className="flex items-center gap-3">
                <Package className="h-8 w-8 text-green-500" />
                <div>
                  <h3 className="font-semibold text-slate-900 dark:text-slate-100">
                    {model.name} <span className="text-slate-400">v{model.version}</span>
                  </h3>
                  <p className="text-xs text-slate-500">
                    {model.algorithm} · {model.primary_metric} {formatMetric(model.primary_score)}
                  </p>
                </div>
              </div>
              <StatusBadge status={model.stage} />
            </div>
            <div className="mt-4 flex gap-2">
              {model.stage !== "production" && (
                <button
                  className="btn-secondary flex-1"
                  onClick={() => deploy.mutate(model.id)}
                  disabled={deploy.isPending}
                >
                  <Rocket className="h-4 w-4" /> Deploy
                </button>
              )}
              <button className="btn-primary flex-1" onClick={() => setPredictModel(model)}>
                <Sparkles className="h-4 w-4" /> Predict
              </button>
            </div>
          </Card>
        ))}
      </div>

      <PredictModal model={predictModel} onClose={() => setPredictModel(null)} />
    </div>
  );
}

function PredictModal({ model, onClose }: { model: Model | null; onClose: () => void }) {
  const predict = usePredict(model?.id ?? "");
  const [values, setValues] = useState<Record<string, string>>({});

  if (!model) return null;

  const submit = () => {
    const record: Record<string, unknown> = {};
    for (const column of model.feature_schema) {
      const raw = values[column.name] ?? "";
      record[column.name] =
        column.dtype.includes("int") || column.dtype.includes("float") ? Number(raw) : raw;
    }
    predict.mutate([record]);
  };

  const result = predict.data?.predictions[0];

  return (
    <Modal open={Boolean(model)} onClose={onClose} title={`Predict — ${model.name}`}>
      <div className="space-y-4">
        <div className="grid grid-cols-2 gap-3">
          {model.feature_schema.map((column) => (
            <div key={column.name}>
              <label className="label">{column.name}</label>
              <input
                className="input"
                placeholder={column.dtype}
                value={values[column.name] ?? ""}
                onChange={(event) =>
                  setValues((prev) => ({ ...prev, [column.name]: event.target.value }))
                }
              />
            </div>
          ))}
        </div>
        {predict.isError && <p className="text-sm text-red-500">{apiErrorMessage(predict.error)}</p>}
        {result && (
          <Card>
            <CardHeader title="Prediction" />
            <CardBody>
              <p className="text-2xl font-bold text-brand-600">{String(result.prediction)}</p>
              {result.probabilities && (
                <div className="mt-3 space-y-1">
                  {Object.entries(result.probabilities).map(([label, probability]) => (
                    <div key={label} className="flex items-center gap-2 text-sm">
                      <span className="w-20 text-slate-500">{label}</span>
                      <div className="h-2 flex-1 rounded-full bg-slate-100 dark:bg-slate-800">
                        <div
                          className="h-2 rounded-full bg-brand-500"
                          style={{ width: `${probability * 100}%` }}
                        />
                      </div>
                      <span className="w-12 text-right text-slate-500">
                        {(probability * 100).toFixed(1)}%
                      </span>
                    </div>
                  ))}
                </div>
              )}
            </CardBody>
          </Card>
        )}
        <button className="btn-primary w-full" onClick={submit} disabled={predict.isPending}>
          {predict.isPending ? <Spinner className="h-4 w-4 text-white" /> : "Run prediction"}
        </button>
      </div>
    </Modal>
  );
}
