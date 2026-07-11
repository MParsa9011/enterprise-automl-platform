import { Plus, Trash2 } from "lucide-react";
import { useState } from "react";
import { useForm } from "react-hook-form";

import { PageHeader } from "@/components/ui/PageHeader";
import { Card } from "@/components/ui/Card";
import { Modal } from "@/components/ui/Modal";
import { Spinner } from "@/components/ui/Spinner";
import { EmptyState, ErrorState, LoadingState } from "@/components/ui/StateViews";
import { useCreateProject, useDeleteProject, useProjects } from "@/hooks/useProjects";
import { apiErrorMessage } from "@/lib/api";
import { formatDate } from "@/lib/utils";

interface ProjectForm {
  name: string;
  description?: string;
}

/** Projects list with create and delete. */
export function Projects() {
  const [modalOpen, setModalOpen] = useState(false);
  const { data, isLoading, isError, error, refetch } = useProjects();
  const createProject = useCreateProject();
  const deleteProject = useDeleteProject();
  const { register, handleSubmit, reset, formState } = useForm<ProjectForm>();

  const onSubmit = handleSubmit(async (values) => {
    await createProject.mutateAsync(values);
    reset();
    setModalOpen(false);
  });

  return (
    <div>
      <PageHeader
        title="Projects"
        description="Workspaces that organise your datasets, experiments and models."
        action={
          <button className="btn-primary" onClick={() => setModalOpen(true)}>
            <Plus className="h-4 w-4" /> New project
          </button>
        }
      />

      {isLoading && <LoadingState />}
      {isError && <ErrorState message={apiErrorMessage(error)} onRetry={refetch} />}

      {data && data.items.length === 0 && (
        <EmptyState
          title="No projects yet"
          description="Create your first project to get started."
          action={
            <button className="btn-primary" onClick={() => setModalOpen(true)}>
              <Plus className="h-4 w-4" /> New project
            </button>
          }
        />
      )}

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {data?.items.map((project) => (
          <Card key={project.id} className="flex flex-col p-5">
            <div className="flex items-start justify-between">
              <h3 className="font-semibold text-slate-900 dark:text-slate-100">{project.name}</h3>
              <button
                className="text-slate-400 hover:text-red-500"
                aria-label="Delete project"
                onClick={() => {
                  if (confirm(`Delete project "${project.name}"?`)) {
                    deleteProject.mutate(project.id);
                  }
                }}
              >
                <Trash2 className="h-4 w-4" />
              </button>
            </div>
            <p className="mt-1 line-clamp-2 flex-1 text-sm text-slate-500">
              {project.description || "No description"}
            </p>
            <p className="mt-3 text-xs text-slate-400">Created {formatDate(project.created_at)}</p>
          </Card>
        ))}
      </div>

      <Modal open={modalOpen} onClose={() => setModalOpen(false)} title="Create project">
        <form onSubmit={onSubmit} className="space-y-4">
          <div>
            <label className="label">Name</label>
            <input className="input" {...register("name", { required: true })} autoFocus />
          </div>
          <div>
            <label className="label">Description</label>
            <textarea className="input" rows={3} {...register("description")} />
          </div>
          {createProject.isError && (
            <p className="text-sm text-red-500">{apiErrorMessage(createProject.error)}</p>
          )}
          <div className="flex justify-end gap-2">
            <button type="button" className="btn-secondary" onClick={() => setModalOpen(false)}>
              Cancel
            </button>
            <button type="submit" className="btn-primary" disabled={formState.isSubmitting}>
              {formState.isSubmitting ? <Spinner className="h-4 w-4 text-white" /> : "Create"}
            </button>
          </div>
        </form>
      </Modal>
    </div>
  );
}
