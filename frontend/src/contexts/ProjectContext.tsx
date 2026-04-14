import {
  createContext,
  useContext,
  useState,
  useEffect,
  useCallback,
  type ReactNode,
} from "react";
import { useParams } from "react-router-dom";
import { api } from "../services/api";
import type { Project, ProjectStatus } from "../types/project";

interface ProjectContextValue {
  project: Project | null;
  loading: boolean;
  error: string | null;
  refresh: () => Promise<void>;
  updateStatus: (status: ProjectStatus) => Promise<void>;
}

const ProjectContext = createContext<ProjectContextValue | null>(null);

export function ProjectProvider({ children }: { children: ReactNode }) {
  const { projectId } = useParams<{ projectId: string }>();
  const [project, setProject] = useState<Project | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    if (!projectId) return;
    setLoading(true);
    try {
      const data = await api.projects.get(projectId);
      setProject(data);
      setError(null);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load project");
    } finally {
      setLoading(false);
    }
  }, [projectId]);

  const updateStatus = useCallback(
    async (status: ProjectStatus) => {
      if (!projectId) return;
      try {
        const updated = await api.projects.update(projectId, { status });
        setProject(updated);
      } catch (e) {
        console.error("Failed to update project status:", e);
      }
    },
    [projectId],
  );

  useEffect(() => {
    refresh();
  }, [refresh]);

  return (
    <ProjectContext.Provider value={{ project, loading, error, refresh, updateStatus }}>
      {children}
    </ProjectContext.Provider>
  );
}

// eslint-disable-next-line react-refresh/only-export-components
export function useProject() {
  const ctx = useContext(ProjectContext);
  if (!ctx) throw new Error("useProject must be used within ProjectProvider");
  return ctx;
}
