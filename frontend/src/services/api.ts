import type { Project, ProjectCreate, ProjectUpdate, ProjectStats } from "../types/project";

const API_BASE = import.meta.env.VITE_API_URL || "";

async function fetchApi<T>(path: string, options?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    headers: {
      "Content-Type": "application/json",
      ...options?.headers,
    },
    ...options,
  });
  if (!response.ok) {
    throw new Error(`API error: ${response.status} ${response.statusText}`);
  }
  return response.json();
}

async function fetchBlob(path: string, options?: RequestInit): Promise<Blob> {
  const response = await fetch(`${API_BASE}${path}`, {
    headers: {
      "Content-Type": "application/json",
      ...options?.headers,
    },
    ...options,
  });
  if (!response.ok) {
    throw new Error(`API error: ${response.status} ${response.statusText}`);
  }
  return response.blob();
}

export const api = {
  questionnaire: {
    getCategories: () => fetchApi<{ categories: Category[] }>("/api/questionnaire/categories"),
    getQuestions: () => fetchApi<{ questions: Question[] }>("/api/questionnaire/questions"),
    getNextQuestion: (answers: Record<string, string | string[]>) =>
      fetchApi<{ complete: boolean; question: Question | null; progress?: Progress }>(
        "/api/questionnaire/next",
        { method: "POST", body: JSON.stringify({ answers }) }
      ),
    resolveUnsure: (answers: Record<string, string | string[]>) =>
      fetchApi<{ resolved_answers: Record<string, string | string[]>; recommendations: { question_id: string; recommended_value: string; reason: string }[] }>(
        "/api/questionnaire/resolve-unsure",
        { method: "POST", body: JSON.stringify({ answers }) }
      ),
    getProgress: (answers: Record<string, string | string[]>) =>
      fetchApi<Progress>("/api/questionnaire/progress", {
        method: "POST",
        body: JSON.stringify({ answers }),
      }),
    saveState: (projectId: string, answers: Record<string, string | string[]>) =>
      fetchApi<{ saved: boolean }>("/api/questionnaire/state/save", {
        method: "POST",
        body: JSON.stringify({ project_id: projectId, answers }),
      }),
    loadState: (projectId: string) =>
      fetchApi<{ answers: Record<string, string | string[]> }>(
        `/api/questionnaire/state/load/${projectId}`,
      ),
  },
  architecture: {
    getArchetypes: () => fetchApi<{ archetypes: Archetype[] }>("/api/architecture/archetypes"),
    getByProject: (projectId: string) =>
      fetchApi<{ architecture: Architecture | null; project_id: string }>(
        `/api/architecture/project/${projectId}`
      ),
    generate: (
      answers: Record<string, string | string[]>,
      useAi = false,
      options?: { project_id?: string; use_archetype?: boolean },
    ) =>
      fetchApi<{ architecture: Architecture }>("/api/architecture/generate", {
        method: "POST",
        body: JSON.stringify({ answers, use_ai: useAi, ...options }),
      }),
    refine: (architecture: Record<string, unknown>, message: string) =>
      fetchApi<{ response: string; updated_architecture: Record<string, unknown> | null }>(
        "/api/architecture/refine",
        { method: "POST", body: JSON.stringify({ architecture, message }) }
      ),
    estimateCosts: (architecture: Record<string, unknown>) =>
      fetchApi<CostEstimation>(
        "/api/architecture/estimate-costs",
        { method: "POST", body: JSON.stringify({ architecture }) }
      ),
  },
  compliance: {
    getFrameworks: () => fetchApi<{ frameworks: Framework[] }>("/api/compliance/frameworks"),
  },
  scoring: {
    evaluate: (
      architecture: Record<string, unknown>,
      frameworks: string[],
      options?: { use_ai?: boolean; project_id?: string },
    ) =>
      fetchApi<{ results: Record<string, unknown>; overall_score: number }>(
        "/api/scoring/evaluate",
        {
          method: "POST",
          body: JSON.stringify({ architecture, frameworks, ...options }),
        },
      ),
    getByProject: (projectId: string) =>
      fetchApi<{ results: Array<{ scoring_data: Record<string, unknown>; overall_score: number }>; project_id: string }>(
        `/api/scoring/project/${projectId}`
      ),
  },
  bicep: {
    templates: () =>
      fetchApi<{ templates: BicepTemplate[] }>("/api/bicep/templates"),
    getTemplate: (templateName: string) =>
      fetchApi<{ name: string; content: string }>(
        `/api/bicep/templates/${templateName}`,
      ),
    generate: (
      architecture: Record<string, unknown>,
      options?: { use_ai?: boolean; project_id?: string },
    ) =>
      fetchApi<{ files: BicepFile[] }>("/api/bicep/generate", {
        method: "POST",
        body: JSON.stringify({ architecture, ...options }),
      }),
    download: (architecture: Record<string, unknown>) =>
      fetchBlob("/api/bicep/download", {
        method: "POST",
        body: JSON.stringify({ architecture }),
      }),
    getByProject: (projectId: string) =>
      fetchApi<{ files: Array<{ name: string; file_path: string; content: string; size_bytes: number }>; project_id: string }>(
        `/api/bicep/project/${projectId}`
      ),
  },
  deployment: {
    validate: (subscriptionId: string, region: string = "eastus2") =>
      fetchApi<DeploymentValidation>("/api/deployment/validate", {
        method: "POST",
        body: JSON.stringify({ subscription_id: subscriptionId, region }),
      }),
    create: (projectId: string, architecture: Record<string, unknown>, subscriptionIds: string[]) =>
      fetchApi<DeploymentRecord>("/api/deployment/create", {
        method: "POST",
        body: JSON.stringify({
          project_id: projectId,
          architecture,
          subscription_ids: subscriptionIds,
        }),
      }),
    start: (deploymentId: string) =>
      fetchApi<DeploymentRecord>(`/api/deployment/${deploymentId}/start`, {
        method: "POST",
      }),
    status: (deploymentId: string) =>
      fetchApi<DeploymentRecord>(`/api/deployment/${deploymentId}`),
    rollback: (deploymentId: string) =>
      fetchApi<DeploymentRecord>(`/api/deployment/${deploymentId}/rollback`, {
        method: "POST",
      }),
    audit: (deploymentId: string) =>
      fetchApi<{ deployment_id: string; entries: AuditEntry[] }>(
        `/api/deployment/${deploymentId}/audit`,
      ),
    list: (projectId?: string) =>
      fetchApi<{ deployments: DeploymentRecord[] }>(
        `/api/deployment/${projectId ? `?project_id=${encodeURIComponent(projectId)}` : ""}`,
      ),
  },
  users: {
    me: () => fetchApi<UserProfile>("/api/users/me"),
    projects: () =>
      fetchApi<{ projects: Array<{ id: string; name: string; description: string | null; status: string; created_at: string | null }> }>(
        "/api/users/me/projects",
      ),
  },
  projects: {
    list: () => fetchApi<{ projects: Project[] }>("/api/projects/"),
    get: (id: string) => fetchApi<Project>(`/api/projects/${id}`),
    create: (data: ProjectCreate) =>
      fetchApi<Project>("/api/projects/", {
        method: "POST",
        body: JSON.stringify(data),
      }),
    update: (id: string, data: ProjectUpdate) =>
      fetchApi<Project>(`/api/projects/${id}`, {
        method: "PUT",
        body: JSON.stringify(data),
      }),
    delete: (id: string) =>
      fetchApi<{ deleted: boolean }>(`/api/projects/${id}`, { method: "DELETE" }),
    getStats: () => fetchApi<ProjectStats>("/api/projects/stats"),
  },
};

export interface Category {
  id: string;
  name: string;
  caf_area: string;
  question_count: number;
}

export interface Question {
  id: string;
  category: string;
  caf_area: string;
  text: string;
  type: "text" | "single_choice" | "multi_choice";
  options?: { value: string; label: string; recommended?: boolean }[];
  required: boolean;
  order: number;
}

export interface Progress {
  total: number;
  answered: number;
  remaining: number;
  percent_complete: number;
}

export interface Archetype {
  size: string;
  name: string;
  description: string;
  subscription_count: number;
  estimated_monthly_cost_usd: number;
}

export interface Architecture {
  organization_size: string;
  management_groups: Record<string, unknown>;
  subscriptions: { name: string; purpose: string; management_group: string }[];
  network_topology: Record<string, unknown>;
  [key: string]: unknown;
}

export interface CostEstimation {
  estimated_monthly_total_usd: number;
  confidence: string;
  breakdown: { category: string; service: string; estimated_monthly_usd: number; notes: string }[];
  cost_optimization_tips: string[];
  assumptions: string[];
}

export interface Framework {
  name: string;
  short_name: string;
  description: string;
  version: string;
  control_count: number;
}

export interface BicepTemplate {
  name: string;
  description: string;
  file_path: string;
}

export interface BicepFile {
  name: string;
  file_path: string;
  content: string;
  size_bytes: number;
}

export interface DeploymentValidation {
  subscription_id: string;
  credentials_valid: boolean;
  permissions_sufficient: boolean;
  quotas_sufficient: boolean;
  ready_to_deploy: boolean;
  details: Record<string, unknown>;
}

export interface DeploymentRecord {
  id: string;
  project_id: string;
  status: string;
  steps: Array<{ name: string; status: string; started_at?: string; completed_at?: string }>;
  created_at: string;
  updated_at: string;
  [key: string]: unknown;
}

export interface AuditEntry {
  timestamp: string;
  action: string;
  details: string;
  user?: string;
}

export interface UserProfile {
  id: string;
  name: string;
  email: string;
  roles: string[];
  [key: string]: unknown;
}
