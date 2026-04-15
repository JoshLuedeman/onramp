import type { Project, ProjectCreate, ProjectUpdate, ProjectStats } from "../types/project";

const API_BASE = import.meta.env.VITE_API_BASE_URL || import.meta.env.VITE_API_URL || "";

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
  discovery: {
    startScan: (projectId: string, subscriptionId: string, scanConfig?: Record<string, unknown>) =>
      fetchApi<DiscoveryScanResponse>("/api/discovery/scan", {
        method: "POST",
        body: JSON.stringify({
          project_id: projectId,
          subscription_id: subscriptionId,
          scan_config: scanConfig,
        }),
      }),
    getScan: (scanId: string) =>
      fetchApi<DiscoveryScanResponse>(`/api/discovery/scan/${scanId}`),
    getScanResources: (scanId: string, category?: string) =>
      fetchApi<DiscoveredResourceList>(
        `/api/discovery/scan/${scanId}/resources${category ? `?category=${encodeURIComponent(category)}` : ""}`,
      ),
    analyzeScanGaps: (scanId: string) =>
      fetchApi<GapAnalysisResponse>(`/api/discovery/scan/${scanId}/analyze`, {
        method: "POST",
      }),
    getBrownfieldContext: (scanId: string) =>
      fetchApi<BrownfieldContextResponse>(
        `/api/discovery/scan/${scanId}/brownfield-context`,
      ),
  },

  workloads: {
    list: (projectId: string) =>
      fetchApi<WorkloadListResponse>(
        `/api/workloads?project_id=${encodeURIComponent(projectId)}`,
      ),
    create: (body: WorkloadCreateRequest) =>
      fetchApi<WorkloadRecord>("/api/workloads", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      }),
    update: (id: string, body: Partial<WorkloadCreateRequest>) =>
      fetchApi<WorkloadRecord>(`/api/workloads/${id}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      }),
    delete: (id: string) =>
      fetchApi<void>(`/api/workloads/${id}`, { method: "DELETE" }),
    importFile: async (file: File, projectId: string): Promise<WorkloadImportResult> => {
      const form = new FormData();
      form.append("file", file);
      const res = await fetch(`${API_BASE}/api/workloads/import?project_id=${encodeURIComponent(projectId)}`, { method: "POST", body: form });
      if (!res.ok) {
        let detail: string;
        try {
          const json = await res.json() as { detail?: string };
          detail = json.detail || JSON.stringify(json);
        } catch {
          detail = await res.text();
        }
        throw new Error(detail || "Import failed");
      }
      return res.json() as Promise<WorkloadImportResult>;
    },
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
  discovered_answer?: DiscoveredAnswer;
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
  steps: Array<{ id: string; name: string; status: string; started_at?: string; completed_at?: string }>;
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

export interface DiscoveryScanResponse {
  id: string;
  project_id: string;
  subscription_id: string;
  status: "pending" | "scanning" | "completed" | "failed";
  scan_config?: Record<string, unknown>;
  results?: Record<string, unknown>;
  error_message?: string;
  resource_count: number;
  created_at: string;
  updated_at: string;
}

export interface DiscoveredResource {
  id: string;
  scan_id: string;
  category: "resource" | "policy" | "rbac" | "network";
  resource_type: string;
  resource_id: string;
  resource_group?: string;
  name: string;
  properties?: Record<string, unknown>;
  created_at: string;
}

export interface DiscoveredResourceList {
  resources: DiscoveredResource[];
  total: number;
  scan_id: string;
}

export interface GapFinding {
  id: string;
  category: string;
  severity: "critical" | "high" | "medium" | "low";
  title: string;
  description: string;
  remediation: string;
  caf_reference?: string;
  can_auto_remediate: boolean;
}

export interface GapAnalysisResponse {
  scan_id: string;
  total_findings: number;
  critical_count: number;
  high_count: number;
  medium_count: number;
  low_count: number;
  findings: GapFinding[];
  areas_checked: string[];
  areas_skipped: string[];
}

export interface DiscoveredAnswer {
  value: string | string[];
  confidence: "high" | "medium" | "low";
  evidence: string;
  source: string;
}

export interface BrownfieldContextResponse {
  scan_id: string;
  discovered_answers: Record<string, DiscoveredAnswer>;
  gap_summary: Record<string, number>;
}

export interface WorkloadRecord {
  id: string;
  project_id: string;
  name: string;
  type: string;
  source_platform: string;
  cpu_cores: number | null;
  memory_gb: number | null;
  storage_gb: number | null;
  os_type: string | null;
  os_version: string | null;
  criticality: string;
  compliance_requirements: string[];
  dependencies: string[];
  migration_strategy: string;
  notes: string | null;
  created_at: string;
  updated_at: string;
}

export interface WorkloadCreateRequest {
  project_id: string;
  name: string;
  type: string;
  source_platform: string;
  cpu_cores?: number | null;
  memory_gb?: number | null;
  storage_gb?: number | null;
  os_type?: string | null;
  os_version?: string | null;
  criticality?: string;
  compliance_requirements?: string[];
  dependencies?: string[];
  migration_strategy?: string;
  notes?: string | null;
}

export interface WorkloadListResponse {
  workloads: WorkloadRecord[];
  total: number;
}

export interface WorkloadImportResult {
  imported_count: number;
  failed_count: number;
  errors: string[];
  workloads: WorkloadRecord[];
}
