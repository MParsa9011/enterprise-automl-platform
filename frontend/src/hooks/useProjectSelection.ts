import { useEffect, useState } from "react";

const STORAGE_KEY = "automl.selected_project";

/**
 * Tracks the currently-selected project id, persisted to localStorage so the
 * choice survives navigation and reloads.
 */
export function useProjectSelection() {
  const [projectId, setProjectId] = useState<string | null>(() =>
    localStorage.getItem(STORAGE_KEY),
  );

  useEffect(() => {
    if (projectId) localStorage.setItem(STORAGE_KEY, projectId);
  }, [projectId]);

  return { projectId, setProjectId };
}
