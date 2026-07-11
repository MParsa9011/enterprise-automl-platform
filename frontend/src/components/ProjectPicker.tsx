import { useEffect } from "react";

import { EmptyState } from "@/components/ui/StateViews";
import { useProjects } from "@/hooks/useProjects";

/**
 * Project selector used by resource pages. Auto-selects the first project when
 * none is chosen and renders a helpful empty state when there are none.
 */
export function ProjectPicker({
  projectId,
  onChange,
}: {
  projectId: string | null;
  onChange: (id: string) => void;
}) {
  const { data } = useProjects(1, 100);
  const projects = data?.items ?? [];

  useEffect(() => {
    if (!projectId && projects.length > 0) {
      onChange(projects[0].id);
    }
  }, [projectId, projects, onChange]);

  if (data && projects.length === 0) {
    return (
      <EmptyState
        title="No projects yet"
        description="Create a project first to start uploading datasets and running experiments."
      />
    );
  }

  return (
    <div className="flex items-center gap-2">
      <label className="text-sm font-medium text-slate-600 dark:text-slate-400">Project</label>
      <select
        className="input max-w-xs"
        value={projectId ?? ""}
        onChange={(event) => onChange(event.target.value)}
      >
        {projects.map((project) => (
          <option key={project.id} value={project.id}>
            {project.name}
          </option>
        ))}
      </select>
    </div>
  );
}
