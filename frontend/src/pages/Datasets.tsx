import { Database, Upload } from "lucide-react";
import { useState } from "react";
import { useForm } from "react-hook-form";

import { ProjectPicker } from "@/components/ProjectPicker";
import { PageHeader } from "@/components/ui/PageHeader";
import { Card, CardBody, CardHeader } from "@/components/ui/Card";
import { Modal } from "@/components/ui/Modal";
import { Spinner } from "@/components/ui/Spinner";
import { EmptyState, ErrorState, LoadingState } from "@/components/ui/StateViews";
import { useDatasets, useUploadDataset } from "@/hooks/useDatasets";
import { useProjectSelection } from "@/hooks/useProjectSelection";
import { apiErrorMessage } from "@/lib/api";
import { formatBytes } from "@/lib/utils";
import type { Dataset } from "@/types/api";

interface UploadForm {
  name: string;
  description?: string;
  file: FileList;
}

/** Dataset management: upload, list and inspect statistics. */
export function Datasets() {
  const { projectId, setProjectId } = useProjectSelection();
  const [uploadOpen, setUploadOpen] = useState(false);
  const [selected, setSelected] = useState<Dataset | null>(null);
  const { data, isLoading, isError, error, refetch } = useDatasets(projectId ?? undefined);

  return (
    <div>
      <PageHeader
        title="Datasets"
        description="Upload CSV or Excel files; profiling runs automatically."
        action={
          projectId && (
            <button className="btn-primary" onClick={() => setUploadOpen(true)}>
              <Upload className="h-4 w-4" /> Upload
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
        <EmptyState title="No datasets" description="Upload a file to get started." />
      )}

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {data?.items.map((dataset) => (
          <Card key={dataset.id} className="p-5">
            <div className="flex items-center gap-3">
              <Database className="h-8 w-8 text-brand-500" />
              <div>
                <h3 className="font-semibold text-slate-900 dark:text-slate-100">
                  {dataset.name}
                </h3>
                <p className="text-xs text-slate-500">v{dataset.latest_version}</p>
              </div>
            </div>
            <button
              className="mt-4 text-sm font-medium text-brand-600 hover:underline"
              onClick={() => setSelected(dataset)}
            >
              View statistics →
            </button>
          </Card>
        ))}
      </div>

      <UploadModal
        open={uploadOpen}
        onClose={() => setUploadOpen(false)}
        projectId={projectId ?? ""}
      />
      <StatisticsModal dataset={selected} onClose={() => setSelected(null)} />
    </div>
  );
}

function UploadModal({
  open,
  onClose,
  projectId,
}: {
  open: boolean;
  onClose: () => void;
  projectId: string;
}) {
  const upload = useUploadDataset(projectId);
  const { register, handleSubmit, reset, formState } = useForm<UploadForm>();

  const onSubmit = handleSubmit(async (values) => {
    await upload.mutateAsync({
      name: values.name,
      description: values.description,
      file: values.file[0],
    });
    reset();
    onClose();
  });

  return (
    <Modal open={open} onClose={onClose} title="Upload dataset">
      <form onSubmit={onSubmit} className="space-y-4">
        <div>
          <label className="label">Name</label>
          <input className="input" {...register("name", { required: true })} autoFocus />
        </div>
        <div>
          <label className="label">File (.csv / .xlsx)</label>
          <input
            type="file"
            accept=".csv,.xlsx,.xls,.parquet"
            className="input"
            {...register("file", { required: true })}
          />
        </div>
        {upload.isError && <p className="text-sm text-red-500">{apiErrorMessage(upload.error)}</p>}
        <div className="flex justify-end gap-2">
          <button type="button" className="btn-secondary" onClick={onClose}>
            Cancel
          </button>
          <button type="submit" className="btn-primary" disabled={formState.isSubmitting}>
            {formState.isSubmitting ? <Spinner className="h-4 w-4 text-white" /> : "Upload"}
          </button>
        </div>
      </form>
    </Modal>
  );
}

function StatisticsModal({ dataset, onClose }: { dataset: Dataset | null; onClose: () => void }) {
  const version = dataset?.versions?.[0];
  if (!dataset) return null;

  return (
    <Modal open={Boolean(dataset)} onClose={onClose} title={`${dataset.name} — statistics`}>
      {!version ? (
        <p className="text-sm text-slate-500">No version data available.</p>
      ) : (
        <div className="space-y-4">
          <div className="grid grid-cols-3 gap-3 text-center">
            <Stat label="Rows" value={version.n_rows} />
            <Stat label="Columns" value={version.n_columns} />
            <Stat label="Size" value={formatBytes(version.size_bytes)} />
          </div>
          <Card>
            <CardHeader title="Columns" />
            <CardBody className="max-h-64 overflow-y-auto p-0">
              <table className="w-full text-sm">
                <thead className="sticky top-0 bg-slate-50 text-left text-xs uppercase text-slate-500 dark:bg-slate-800">
                  <tr>
                    <th className="px-4 py-2">Name</th>
                    <th className="px-4 py-2">Type</th>
                    <th className="px-4 py-2">Missing</th>
                    <th className="px-4 py-2">Unique</th>
                  </tr>
                </thead>
                <tbody>
                  {version.columns_schema.map((column) => (
                    <tr key={column.name} className="border-t border-slate-100 dark:border-slate-800">
                      <td className="px-4 py-2 font-medium">{column.name}</td>
                      <td className="px-4 py-2 text-slate-500">{column.inferred_type}</td>
                      <td className="px-4 py-2 text-slate-500">{column.missing_pct}%</td>
                      <td className="px-4 py-2 text-slate-500">{column.n_unique}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </CardBody>
          </Card>
        </div>
      )}
    </Modal>
  );
}

function Stat({ label, value }: { label: string; value: string | number }) {
  return (
    <div className="rounded-lg bg-slate-50 py-3 dark:bg-slate-800">
      <p className="text-lg font-bold text-slate-900 dark:text-slate-100">{value}</p>
      <p className="text-xs text-slate-500">{label}</p>
    </div>
  );
}
