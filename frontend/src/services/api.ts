import type { Project, ProjectCreate, ProjectUpdate, ProjectStats } from "../types/project";

const API_BASE = import.meta.env.VITE_API_BASE_URL || import.meta.env.VITE_API_URL || "";

// ── Structured Error Handling ───────────────────────────────────────────

/** Matches the backend's ErrorDetail schema. */
export interface ApiErrorDetail {
  code: string;
  message: string;
  type: string;
  details?: Record<string, unknown>[];
  request_id?: string;
}

/** Matches the backend's ErrorResponse schema. */
export interface ApiErrorResponse {
  error: ApiErrorDetail;
}

/**
 * Custom error class thrown by API helpers.
 *
 * Attempts to parse the backend's structured error format first.  Falls
 * back to the legacy `{ detail: ... }` shape and finally to raw status
 * text so callers always get a usable `.message`.
 */
export class ApiError extends Error {
  status: number;
  statusText: string;
  code: string;
  errorType: string;
  details?: Record<string, unknown>[];
  requestId?: string;

  constructor(
    status: number,
    statusText: string,
    body?: ApiErrorResponse | { detail?: string } | string,
  ) {
    // Derive a human-readable message from whatever the server returned.
    let message = `API error: ${status} ${statusText}`;
    let code = "UNKNOWN";
    let errorType = "unknown";
    let details: Record<string, unknown>[] | undefined;
    let requestId: string | undefined;

    if (body && typeof body === "object" && "error" in body) {
      // New structured format
      const structured = body as ApiErrorResponse;
      message = structured.error.message;
      code = structured.error.code;
      errorType = structured.error.type;
      details = structured.error.details;
      requestId = structured.error.request_id;
    } else if (body && typeof body === "object" && "detail" in body) {
      // Legacy FastAPI format
      const legacy = body as { detail?: string };
      message = legacy.detail ?? message;
    } else if (typeof body === "string" && body.length > 0) {
      message = body;
    }

    super(message);
    this.name = "ApiError";
    this.status = status;
    this.statusText = statusText;
    this.code = code;
    this.errorType = errorType;
    this.details = details;
    this.requestId = requestId;
  }
}

/** Try to parse the response body into a structured or legacy error object. */
async function parseErrorBody(
  response: Response,
): Promise<ApiErrorResponse | { detail?: string } | string> {
  try {
    return (await response.json()) as ApiErrorResponse | { detail?: string };
  } catch {
    try {
      return await response.text();
    } catch {
      return "";
    }
  }
}

async function fetchApi<T>(path: string, options?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    headers: {
      "Content-Type": "application/json",
      ...options?.headers,
    },
    ...options,
  });
  if (!response.ok) {
    const body = await parseErrorBody(response);
    throw new ApiError(response.status, response.statusText, body);
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
    const body = await parseErrorBody(response);
    throw new ApiError(response.status, response.statusText, body);
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
    refine: (
      architecture: Record<string, unknown>,
      message: string,
      options?: { architecture_id?: string; version?: number },
    ) =>
      fetchApi<{ response: string; updated_architecture: Record<string, unknown> | null }>(
        "/api/architecture/refine",
        {
          method: "POST",
          body: JSON.stringify({
            architecture,
            message,
            architecture_id: options?.architecture_id,
            version: options?.version,
          }),
          headers: options?.version
            ? { "If-Match": String(options.version) }
            : undefined,
        }
      ),
    estimateCosts: (architecture: Record<string, unknown>) =>
      fetchApi<CostEstimation>(
        "/api/architecture/estimate-costs",
        { method: "POST", body: JSON.stringify({ architecture }) }
      ),
    generateAdrs: (
      architecture: Record<string, unknown>,
      answers: Record<string, string | string[]>,
      useAi = false,
      projectId?: string,
    ) =>
      fetchApi<ADRGenerateResponse>("/api/architecture/adrs/generate", {
        method: "POST",
        body: JSON.stringify({
          architecture,
          answers,
          use_ai: useAi,
          project_id: projectId,
        }),
      }),
    exportAdrs: (adrs: ADRRecord[], format: "individual" | "combined" = "combined") =>
      fetchApi<{ content: string }>("/api/architecture/adrs/export", {
        method: "POST",
        body: JSON.stringify({ adrs, format }),
      }),
    compare: (answers: Record<string, string>, options?: object) =>
      fetchApi<ComparisonResult>("/api/architecture/compare", {
        method: "POST",
        body: JSON.stringify({ answers, options }),
      }),
    compareTradeoffs: (answers: Record<string, string>, options?: object) =>
      fetchApi<{ tradeoff_analysis: string }>("/api/architecture/compare/tradeoffs", {
        method: "POST",
        body: JSON.stringify({ answers, options }),
      }),
    update: (
      projectId: string,
      architectureId: string,
      architectureData: Record<string, unknown>,
      version: number,
    ) =>
      fetchApi<{ architecture: Record<string, unknown>; project_id: string; version: number }>(
        `/api/architecture/project/${projectId}`,
        {
          method: "PUT",
          body: JSON.stringify({
            architecture_data: architectureData,
            architecture_id: architectureId,
            version,
          }),
          headers: { "If-Match": String(version) },
        },
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
  arm: {
    generate: (
      architecture: Record<string, unknown>,
      options?: { use_ai?: boolean; project_id?: string },
    ) =>
      fetchApi<{ files: Array<{ name: string; content: string; size_bytes: number }>; total_files: number; ai_generated: boolean }>(
        "/api/arm/generate",
        {
          method: "POST",
          body: JSON.stringify({ architecture, ...options }),
        },
      ),
    download: (architecture: Record<string, unknown>) =>
      fetchBlob("/api/arm/download", {
        method: "POST",
        body: JSON.stringify({ architecture }),
      }),
    validate: (template: string) =>
      fetchApi<{ valid: boolean; errors: string[]; warnings: string[] }>(
        "/api/arm/validate",
        {
          method: "POST",
          body: JSON.stringify({ template }),
        },
      ),
  },
  pulumi: {
    templates: () =>
      fetchApi<{ templates: PulumiTemplate[] }>("/api/pulumi/templates"),
    generate: (
      architecture: Record<string, unknown>,
      options?: { language?: "typescript" | "python"; use_ai?: boolean; project_id?: string },
    ) =>
      fetchApi<{ files: PulumiFile[]; total_files: number; language: string; ai_generated: boolean }>(
        "/api/pulumi/generate",
        {
          method: "POST",
          body: JSON.stringify({ architecture, ...options }),
        },
      ),
    download: (
      architecture: Record<string, unknown>,
      options?: { language?: "typescript" | "python"; use_ai?: boolean },
    ) =>
      fetchBlob("/api/pulumi/download", {
        method: "POST",
        body: JSON.stringify({ architecture, ...options }),
      }),
  },
  terraform: {
    templates: () =>
      fetchApi<{ templates: Array<{ name: string; description: string; category: string }> }>(
        "/api/terraform/templates",
      ),
    generate: (
      architecture: Record<string, unknown>,
      options?: { use_ai?: boolean; project_id?: string },
    ) =>
      fetchApi<{ files: Array<{ name: string; content: string; size_bytes: number }>; total_files: number; ai_generated: boolean }>(
        "/api/terraform/generate",
        {
          method: "POST",
          body: JSON.stringify({ architecture, ...options }),
        },
      ),
    download: (architecture: Record<string, unknown>) =>
      fetchBlob("/api/terraform/download", {
        method: "POST",
        body: JSON.stringify({ architecture }),
      }),
  },
  pipelines: {
    templates: () =>
      fetchApi<{ templates: PipelineTemplate[] }>("/api/pipelines/templates"),
    generate: (
      architecture: Record<string, unknown>,
      iacFormat: string,
      options?: {
        pipeline_format?: string;
        environments?: string[];
        include_approval_gates?: boolean;
        project_name?: string;
        service_connection?: string;
        variable_group?: string;
      },
    ) =>
      fetchApi<PipelineGenerateResponse>("/api/pipelines/generate", {
        method: "POST",
        body: JSON.stringify({
          architecture,
          iac_format: iacFormat,
          ...options,
        }),
      }),
    download: (
      architecture: Record<string, unknown>,
      iacFormat: string,
      options?: {
        pipeline_format?: string;
        environments?: string[];
        include_approval_gates?: boolean;
        project_name?: string;
        service_connection?: string;
        variable_group?: string;
      },
    ) =>
      fetchBlob("/api/pipelines/download", {
        method: "POST",
        body: JSON.stringify({
          architecture,
          iac_format: iacFormat,
          ...options,
        }),
      }),
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
        const body = await parseErrorBody(res);
        throw new ApiError(res.status, res.statusText, body);
      }
      return res.json() as Promise<WorkloadImportResult>;
    },
    generateMapping: (projectId: string, architectureId: string = "", useAi: boolean = true) =>
      fetchApi<WorkloadMappingResponse>("/api/workloads/map", {
        method: "POST",
        body: JSON.stringify({ project_id: projectId, architecture_id: architectureId, use_ai: useAi }),
      }),
    overrideMapping: (workloadId: string, subscriptionId: string, reasoning: string = "Manual override") =>
      fetchApi<WorkloadRecord>(`/api/workloads/${workloadId}/mapping`, {
        method: "PATCH",
        body: JSON.stringify({ target_subscription_id: subscriptionId, reasoning }),
      }),
    getDependencyGraph: (projectId: string) =>
      fetchApi<DependencyGraph>(
        `/api/workloads/dependency-graph?project_id=${encodeURIComponent(projectId)}`,
      ),
    getMigrationOrder: (projectId: string) =>
      fetchApi<MigrationOrderResponse>(
        `/api/workloads/migration-order?project_id=${encodeURIComponent(projectId)}`,
      ),
    /** Add a dependency between two workloads.
     *
     * @param dependencyType - Accepted by the API for future extensibility.
     *   Currently only "depends_on" is supported; the backend records the
     *   dependency as a plain ID reference and does not yet persist the type.
     */
    addDependency: (workloadId: string, targetId: string, dependencyType = "depends_on") =>
      fetchApi<WorkloadRecord>(`/api/workloads/${workloadId}/dependencies`, {
        method: "POST",
        body: JSON.stringify({ target_workload_id: targetId, dependency_type: dependencyType }),
      }),
    removeDependency: (workloadId: string, targetId: string) =>
      fetchApi<WorkloadRecord>(`/api/workloads/${workloadId}/dependencies/${targetId}`, {
        method: "DELETE",
      }),
  },

  migration: {
    generateWaves: (body: WaveGenerateRequest) =>
      fetchApi<WavePlanResponse>("/api/migration/waves/generate", {
        method: "POST",
        body: JSON.stringify(body),
      }),
    getWaves: (projectId: string) =>
      fetchApi<WavePlanResponse>(
        `/api/migration/waves?project_id=${encodeURIComponent(projectId)}`,
      ),
    getWave: (waveId: string) =>
      fetchApi<WaveResponse>(`/api/migration/waves/${waveId}`),
    updateWave: (waveId: string, body: WaveUpdateRequest) =>
      fetchApi<WaveResponse>(`/api/migration/waves/${waveId}`, {
        method: "PATCH",
        body: JSON.stringify(body),
      }),
    moveWorkload: (body: MoveWorkloadRequest) =>
      fetchApi<WavePlanResponse>("/api/migration/waves/move", {
        method: "POST",
        body: JSON.stringify(body),
      }),
    validatePlan: (projectId: string) =>
      fetchApi<WavePlanResponse>("/api/migration/waves/validate", {
        method: "POST",
        body: JSON.stringify({ project_id: projectId }),
      }),
    exportPlan: (projectId: string, format: 'csv' | 'markdown') =>
      fetchBlob("/api/migration/waves/export", {
        method: "POST",
        body: JSON.stringify({ project_id: projectId, format }),
      }),
    deleteWave: (waveId: string) =>
      fetchApi<void>(`/api/migration/waves/${waveId}`, { method: "DELETE" }),
  },

  plugins: {
    list: () => fetchApi<PluginListResponse>("/api/plugins/"),
    get: (name: string) =>
      fetchApi<PluginResponse>(`/api/plugins/${encodeURIComponent(name)}`),
  },

  policies: {
    generate: (description: string, context?: object) =>
      fetchApi<PolicyDefinition>("/api/policies/generate", {
        method: "POST",
        body: JSON.stringify({ description, context }),
      }).then((res) => (res as unknown as { policy: PolicyDefinition }).policy),
    validate: (policy: object) =>
      fetchApi<PolicyValidationResult>("/api/policies/validate", {
        method: "POST",
        body: JSON.stringify({ policy }),
      }),
    getLibrary: () =>
      fetchApi<{ policies: PolicyTemplate[] }>("/api/policies/library").then(
        (res) => res.policies,
      ),
    apply: (policy: object, architectureId?: string) =>
      fetchApi<void>("/api/policies/apply", {
        method: "POST",
        body: JSON.stringify({ policy, architecture_id: architectureId }),
      }),
  },

  governance: {
    drift: {
      remediate: (data: RemediationRequest) =>
        fetchApi<RemediationResponseType>("/api/governance/drift/remediate", {
          method: "POST",
          body: JSON.stringify(data),
        }),
      remediateBatch: (data: BatchRemediationRequest) =>
        fetchApi<BatchRemediationResponseType>("/api/governance/drift/remediate/batch", {
          method: "POST",
          body: JSON.stringify(data),
        }),
      getRemediation: (id: string) =>
        fetchApi<RemediationResponseType>(`/api/governance/drift/remediation/${id}`),
      getRemediationHistory: () =>
        fetchApi<RemediationAuditLogType>("/api/governance/drift/remediation/history"),
    },
    scorecard: {
      getScorecard: (projectId: string) =>
        fetchApi<GovernanceScoreResponse>(`/api/governance/scorecard/${projectId}`),
      getScoreTrend: (projectId: string, days?: number) =>
        fetchApi<ScoreTrendResponse>(`/api/governance/scorecard/${projectId}/trend${days ? `?days=${days}` : ""}`),
      refreshScore: (projectId: string) =>
        fetchApi<GovernanceScoreResponse>(`/api/governance/scorecard/${projectId}/refresh`, { method: "POST" }),
      getSummary: (projectId: string) =>
        fetchApi<ExecutiveSummaryResponse>(`/api/governance/scorecard/${projectId}/summary`),
    },
  },

  security: {
    analyze: (architecture: Record<string, unknown>, useAi?: boolean) =>
      fetchApi<SecurityAnalysisResponse>("/api/security/analyze", {
        method: "POST",
        body: JSON.stringify({ architecture, use_ai: useAi ?? false }),
      }),
    getChecks: () => fetchApi<SecurityCheckItem[]>("/api/security/checks"),
    fix: (findingId: string, architecture: Record<string, unknown>) =>
      fetchApi<SecurityRemediationStep>("/api/security/fix", {
        method: "POST",
        body: JSON.stringify({ finding_id: findingId, architecture }),
      }),
  },

  chat: {
    createConversation: (projectId?: string) =>
      fetchApi<ConversationResponse>("/api/chat/new", {
        method: "POST",
        body: JSON.stringify({ project_id: projectId ?? "default" }),
      }),
    getConversations: (projectId?: string) =>
      fetchApi<{ conversations: ConversationResponse[] }>(
        `/api/chat/conversations?project_id=${encodeURIComponent(projectId ?? "default")}`,
      ).then((r) => r.conversations),
    getConversation: (conversationId: string) =>
      fetchApi<ConversationWithMessages>(`/api/chat/${conversationId}`),
    sendMessage: (conversationId: string, content: string) =>
      fetchApi<SendMessageApiResponse>(`/api/chat/${conversationId}/message`, {
        method: "POST",
        body: JSON.stringify({ content }),
      }),
    archiveConversation: (conversationId: string) =>
      fetchApi<void>(`/api/chat/${conversationId}/archive`, { method: "POST" }),
    deleteConversation: (conversationId: string) =>
      fetchApi<void>(`/api/chat/${conversationId}`, { method: "DELETE" }),
  },

  iacValidation: {
    validate: (code: string, format: string, fileName?: string) =>
      fetchApi<{
        is_valid: boolean;
        format: string;
        errors: { line: number | null; column: number | null; message: string; severity: string }[];
        warnings: { line: number | null; message: string }[];
        file_name: string | null;
      }>("/api/iac/validate", {
        method: "POST",
        body: JSON.stringify({ code, format, file_name: fileName }),
      }),
    validateBundle: (files: { code: string; file_name: string }[], format: string) =>
      fetchApi<{
        is_valid: boolean;
        format: string;
        file_results: {
          is_valid: boolean;
          format: string;
          errors: { line: number | null; column: number | null; message: string; severity: string }[];
          warnings: { line: number | null; message: string }[];
          file_name: string | null;
        }[];
        bundle_errors: { line: number | null; column: number | null; message: string; severity: string }[];
        bundle_warnings: { line: number | null; message: string }[];
      }>("/api/iac/validate-bundle", {
        method: "POST",
        body: JSON.stringify({ files, format }),
      }),
  },

  versions: {
    terraform: () =>
      fetchApi<{
        terraform_version: string;
        providers: { name: string; source: string; version_constraint: string; release_date: string; notes: string }[];
      }>("/api/versions/terraform"),
    pulumi: (language: "typescript" | "python") =>
      fetchApi<{
        language: string;
        packages: { name: string; source: string; version_constraint: string; release_date: string; notes: string }[];
      }>(`/api/versions/pulumi/${language}`),
    arm: () =>
      fetchApi<{
        schema_version: string;
        content_version: string;
        api_versions: { resource_type: string; api_version: string; release_date: string; notes: string }[];
      }>("/api/versions/arm"),
    bicep: () =>
      fetchApi<{
        api_versions: { resource_type: string; api_version: string; release_date: string; notes: string }[];
      }>("/api/versions/bicep"),
    report: (thresholdDays?: number) =>
      fetchApi<{
        staleness_threshold_days: number;
        terraform: { name: string; version: string; release_date: string; age_days: number; is_stale: boolean }[];
        pulumi_typescript: { name: string; version: string; release_date: string; age_days: number; is_stale: boolean }[];
        pulumi_python: { name: string; version: string; release_date: string; age_days: number; is_stale: boolean }[];
        arm: { name: string; version: string; release_date: string; age_days: number; is_stale: boolean }[];
        bicep: { name: string; version: string; release_date: string; age_days: number; is_stale: boolean }[];
        total_entries: number;
        stale_count: number;
      }>(
        thresholdDays
          ? `/api/versions/report?threshold_days=${thresholdDays}`
          : "/api/versions/report",
      ),
  },
  architectureVersions: {
    list: (archId: string) =>
      fetchApi<VersionListResponse>(`/api/architectures/${archId}/versions`),
    get: (archId: string, version: number) =>
      fetchApi<ArchitectureVersionItem>(
        `/api/architectures/${archId}/versions/${version}`,
      ),
    restore: (archId: string, version: number, summary?: string) =>
      fetchApi<ArchitectureVersionItem>(
        `/api/architectures/${archId}/versions/${version}/restore`,
        {
          method: "POST",
          body: summary !== undefined ? JSON.stringify({ change_summary: summary }) : undefined,
        },
      ),
    diff: (archId: string, from: number, to: number) =>
      fetchApi<EnhancedVersionDiffResult>(
        `/api/architectures/${archId}/versions/diff?from=${from}&to=${to}`,
      ),
  },

  collaboration: {
    listMembers: (projectId: string) =>
      fetchApi<ProjectMemberListResponse>(
        `/api/projects/${projectId}/members`,
      ),
    addMember: (projectId: string, data: ProjectMemberCreateRequest) =>
      fetchApi<ProjectMemberResponse>(
        `/api/projects/${projectId}/members`,
        { method: "POST", body: JSON.stringify(data) },
      ),
    removeMember: (projectId: string, userId: string) =>
      fetchApi<{ removed: boolean; user_id: string }>(
        `/api/projects/${projectId}/members/${userId}`,
        { method: "DELETE" },
      ),
    listComments: (projectId: string, componentRef?: string) =>
      fetchApi<CommentListResponse>(
        `/api/projects/${projectId}/comments${
          componentRef
            ? `?component_ref=${encodeURIComponent(componentRef)}`
            : ""
        }`,
      ),
    addComment: (projectId: string, data: CommentCreateRequest) =>
      fetchApi<CommentResponseItem>(
        `/api/projects/${projectId}/comments`,
        { method: "POST", body: JSON.stringify(data) },
      ),
    getActivity: (projectId: string) =>
      fetchApi<ActivityFeedResponse>(
        `/api/projects/${projectId}/activity`,
      ),
  },

  reviews: {
    submit: (architectureId: string) =>
      fetchApi<ReviewSubmitResponse>(
        `/api/architectures/${architectureId}/reviews/submit`,
        { method: "POST" },
      ),
    perform: (architectureId: string, data: ReviewActionRequest) =>
      fetchApi<ReviewResponseItem>(
        `/api/architectures/${architectureId}/reviews`,
        { method: "POST", body: JSON.stringify(data) },
      ),
    getHistory: (architectureId: string) =>
      fetchApi<ReviewHistoryResponse>(
        `/api/architectures/${architectureId}/reviews`,
      ),
    getStatus: (architectureId: string) =>
      fetchApi<ReviewStatusResponse>(
        `/api/architectures/${architectureId}/reviews/status`,
      ),
    withdraw: (architectureId: string) =>
      fetchApi<ReviewSubmitResponse>(
        `/api/architectures/${architectureId}/reviews/withdraw`,
        { method: "POST" },
      ),
    configureRequirements: (
      projectId: string,
      data: { required_approvals: number },
    ) =>
      fetchApi<ReviewConfigurationResponse>(
        `/api/projects/${projectId}/review-config`,
        { method: "PUT", body: JSON.stringify(data) },
      ),
  },
  msp: {
    getOverview: () =>
      fetchApi<MSPOverviewResponse>("/api/msp/overview"),
    getTenantHealth: (tenantId: string) =>
      fetchApi<MSPTenantHealthResponse>(
        `/api/msp/tenants/${tenantId}/health`,
      ),
    getComplianceSummary: () =>
      fetchApi<MSPComplianceSummaryResponse>(
        "/api/msp/compliance-summary",
      ),
  },
  templates: {
    list: (params?: Record<string, string>) => {
      const qs = params
        ? "?" + new URLSearchParams(params).toString()
        : "";
      return fetchApi<TemplateListResponse>(`/api/templates${qs}`);
    },
    get: (id: string) =>
      fetchApi<TemplateItem>(`/api/templates/${id}`),
    create: (data: {
      name: string;
      description?: string;
      industry: string;
      tags?: string[];
      architecture_json: string;
      visibility?: string;
    }) =>
      fetchApi<TemplateItem>("/api/templates", {
        method: "POST",
        body: JSON.stringify(data),
      }),
    use: (id: string, projectId: string) =>
      fetchApi<TemplateItem>(`/api/templates/${id}/use`, {
        method: "POST",
        body: JSON.stringify({ project_id: projectId }),
      }),
    rate: (id: string, rating: "up" | "down") =>
      fetchApi<TemplateItem>(`/api/templates/${id}/rate`, {
        method: "POST",
        body: JSON.stringify({ rating }),
      }),
  },
  cloud: {
    getEnvironments: () =>
      fetchApi<CloudEnvironmentItem[]>("/api/cloud/environments"),
    getEnvironment: (name: string) =>
      fetchApi<CloudEnvironmentItem>(`/api/cloud/environments/${name}`),
    getEndpoints: (name: string) =>
      fetchApi<CloudEndpointsItem>(`/api/cloud/environments/${name}/endpoints`),
    validateEnvironment: (data: {
      environment: string;
      required_services: string[];
    }) =>
      fetchApi<CloudValidationResult>("/api/cloud/environments/validate", {
        method: "POST",
        body: JSON.stringify(data),
      }),
  },
  sovereign: {
    getFrameworks: () =>
      fetchApi<SovereignFrameworkListResponse>("/api/sovereign/frameworks"),
    getFramework: (name: string) =>
      fetchApi<SovereignFrameworkDetail>(`/api/sovereign/frameworks/${name}`),
    getControls: (name: string) =>
      fetchApi<{ framework: string; controls: SovereignControl[] }>(
        `/api/sovereign/frameworks/${name}/controls`
      ),
    evaluateCompliance: (name: string, architecture: Record<string, unknown>) =>
      fetchApi<SovereignComplianceResult>(
        `/api/sovereign/frameworks/${name}/evaluate`,
        { method: "POST", body: JSON.stringify({ architecture }) }
      ),
    getServices: () =>
      fetchApi<ServiceAvailabilityItem[]>("/api/sovereign/services"),
    getAvailabilityMatrix: () =>
      fetchApi<ServiceAvailabilityMatrix>("/api/sovereign/services/matrix"),
    checkCompatibility: (data: {
      architecture: Record<string, unknown>;
      target_environment: string;
    }) =>
      fetchApi<ArchitectureCompatibilityResult>(
        "/api/sovereign/services/check-compatibility",
        { method: "POST", body: JSON.stringify(data) }
      ),
  },

  government: {
    getRegions: () =>
      fetchApi<GovernmentRegionListResponse>("/api/government/regions"),
    getRegion: (name: string) =>
      fetchApi<GovernmentRegionResponse>(`/api/government/regions/${name}`),
    getDodRegions: () =>
      fetchApi<GovernmentRegionListResponse>("/api/government/regions/dod"),
    customizeBicep: (data: {
      bicep_content: string;
      region: string;
      compliance_level?: string;
    }) =>
      fetchApi<GovernmentBicepResponse>("/api/government/bicep/customize", {
        method: "POST",
        body: JSON.stringify(data),
      }),
    getQuestions: () =>
      fetchApi<GovernmentQuestionResponse[]>("/api/government/questions"),
    applyConstraints: (data: {
      architecture: Record<string, unknown>;
      gov_answers: Record<string, string>;
    }) =>
      fetchApi<GovernmentConstraintsResponse>("/api/government/constraints", {
        method: "POST",
        body: JSON.stringify(data),
      }),
  },

  china: {
    getRegions: () =>
      fetchApi<ChinaRegionListResponse>("/api/china/regions"),
    getRegion: (name: string) =>
      fetchApi<ChinaRegionResponse>(`/api/china/regions/${name}`),
    customizeBicep: (data: {
      bicep_content: string;
      region: string;
      compliance_level?: string;
    }) =>
      fetchApi<ChinaBicepResponse>("/api/china/bicep/customize", {
        method: "POST",
        body: JSON.stringify(data),
      }),
    getQuestions: () =>
      fetchApi<ChinaQuestionResponse[]>("/api/china/questions"),
    applyConstraints: (data: {
      architecture: Record<string, unknown>;
      china_answers: Record<string, string>;
    }) =>
      fetchApi<ChinaConstraintsResponse>("/api/china/constraints", {
        method: "POST",
        body: JSON.stringify(data),
      }),
    getDataResidency: () =>
      fetchApi<DataResidencyResponse>("/api/china/data-residency"),
    getIcpRequirements: () =>
      fetchApi<ICPRequirementsResponse>("/api/china/icp-requirements"),
  },

  confidential: {
    getOptions: () =>
      fetchApi<ConfidentialOptionsListResponse>("/api/confidential/options"),
    getVmSkus: () =>
      fetchApi<ConfidentialVmSkuListResponse>("/api/confidential/vm-skus"),
    getRegions: () =>
      fetchApi<ConfidentialRegionListResponse>("/api/confidential/regions"),
    recommend: (data: { workload_type: string; requirements: Record<string, unknown> }) =>
      fetchApi<ConfidentialRecommendResponse>("/api/confidential/recommend", {
        method: "POST",
        body: JSON.stringify(data),
      }),
    generateArchitecture: (data: {
      base_architecture: Record<string, unknown>;
      cc_options: Record<string, unknown>;
    }) =>
      fetchApi<ConfidentialArchitectureResponse>("/api/confidential/architecture", {
        method: "POST",
        body: JSON.stringify(data),
      }),
    generateBicep: (data: { template_type: string; config: Record<string, unknown> }) =>
      fetchApi<ConfidentialBicepResponse>("/api/confidential/bicep", {
        method: "POST",
        body: JSON.stringify(data),
      }),
    getAttestationConfig: (ccType: string) =>
      fetchApi<AttestationConfigResponse>(`/api/confidential/attestation/${encodeURIComponent(ccType)}`),
  },

  workloadExtensions: {
    list: () =>
      fetchApi<{ extensions: WorkloadExtensionItem[] }>("/api/workloads/extensions/"),
    get: (workloadType: string) =>
      fetchApi<WorkloadExtensionDetail>(`/api/workloads/extensions/${workloadType}`),
    getQuestions: (workloadType: string) =>
      fetchApi<{ workload_type: string; questions: WorkloadQuestion[] }>(
        `/api/workloads/extensions/${workloadType}/questions`
      ),
    getBestPractices: (workloadType: string) =>
      fetchApi<{ workload_type: string; best_practices: BestPractice[] }>(
        `/api/workloads/extensions/${workloadType}/best-practices`
      ),
    validate: (workloadType: string, architecture: Record<string, unknown>) =>
      fetchApi<WorkloadValidationResult>(
        `/api/workloads/extensions/${workloadType}/validate`,
        { method: "POST", body: JSON.stringify({ architecture }) }
      ),
    estimateSizing: (workloadType: string, requirements: Record<string, unknown>) =>
      fetchApi<{ workload_type: string; sizing: Record<string, unknown> }>(
        `/api/workloads/extensions/${workloadType}/sizing`,
        { method: "POST", body: JSON.stringify({ requirements }) }
      ),
  },

  skus: {
    getCompute: (filters?: { family?: string; min_vcpus?: number; min_ram?: number; gpu?: boolean; price_tier?: string }) => {
      const params = new URLSearchParams();
      if (filters?.family) params.set("family", filters.family);
      if (filters?.min_vcpus != null) params.set("min_vcpus", String(filters.min_vcpus));
      if (filters?.min_ram != null) params.set("min_ram", String(filters.min_ram));
      if (filters?.gpu != null) params.set("gpu", String(filters.gpu));
      if (filters?.price_tier) params.set("price_tier", filters.price_tier);
      const qs = params.toString();
      return fetchApi<SkuListResult>(`/api/skus/compute${qs ? `?${qs}` : ""}`);
    },
    getStorage: (filters?: { tier?: string; media?: string }) => {
      const params = new URLSearchParams();
      if (filters?.tier) params.set("tier", filters.tier);
      if (filters?.media) params.set("media", filters.media);
      const qs = params.toString();
      return fetchApi<SkuListResult>(`/api/skus/storage${qs ? `?${qs}` : ""}`);
    },
    getDatabase: (filters?: { service?: string; tier?: string }) => {
      const params = new URLSearchParams();
      if (filters?.service) params.set("service", filters.service);
      if (filters?.tier) params.set("tier", filters.tier);
      const qs = params.toString();
      return fetchApi<SkuListResult>(`/api/skus/database${qs ? `?${qs}` : ""}`);
    },
    getNetworking: (filters?: { service?: string; tier?: string }) => {
      const params = new URLSearchParams();
      if (filters?.service) params.set("service", filters.service);
      if (filters?.tier) params.set("tier", filters.tier);
      const qs = params.toString();
      return fetchApi<SkuListResult>(`/api/skus/networking${qs ? `?${qs}` : ""}`);
    },
    recommend: (workloadType: string, requirements: Record<string, unknown>) =>
      fetchApi<SkuRecommendResult>("/api/skus/recommend", {
        method: "POST",
        body: JSON.stringify({ workload_type: workloadType, requirements }),
      }),
    compare: (skuIds: string[]) =>
      fetchApi<{ skus: Record<string, unknown>[] }>("/api/skus/compare", {
        method: "POST",
        body: JSON.stringify({ sku_ids: skuIds }),
      }),
    validateAvailability: (sku: string, region: string, cloudEnv?: string) =>
      fetchApi<SkuAvailabilityResult>("/api/skus/validate", {
        method: "POST",
        body: JSON.stringify({ sku, region, cloud_env: cloudEnv ?? "commercial" }),
      }),
  },

  validation: {
    validateArchitecture: (data: {
      architecture: Record<string, unknown>;
      workload_type?: string;
      cloud_env?: string;
    }) =>
      fetchApi<ArchValidationResult>("/api/validation/architecture", {
        method: "POST",
        body: JSON.stringify(data),
      }),
    validateSkus: (data: { architecture: Record<string, unknown>; region?: string }) =>
      fetchApi<ArchValidationResult>("/api/validation/skus", {
        method: "POST",
        body: JSON.stringify(data),
      }),
    validateCompliance: (data: {
      architecture: Record<string, unknown>;
      framework: string;
    }) =>
      fetchApi<ArchValidationResult>("/api/validation/compliance", {
        method: "POST",
        body: JSON.stringify(data),
      }),
    validateNetworking: (data: { architecture: Record<string, unknown> }) =>
      fetchApi<ArchValidationResult>("/api/validation/networking", {
        method: "POST",
        body: JSON.stringify(data),
      }),
    getRules: () =>
      fetchApi<{ rules: ValidationRule[] }>("/api/validation/rules"),
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

export interface PulumiTemplate {
  name: string;
  description: string;
  languages: string[];
}

export interface PulumiFile {
  name: string;
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
  target_subscription_id: string | null;
  mapping_reasoning: string | null;
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

export interface WorkloadMappingRecord {
  workload_id: string;
  workload_name: string;
  recommended_subscription_id: string;
  recommended_subscription_name: string;
  reasoning: string;
  confidence_score: number;
  warnings: string[];
}

export interface WorkloadMappingResponse {
  mappings: WorkloadMappingRecord[];
  warnings: string[];
}

export interface WorkloadSummary {
  id: string;
  name: string;
  criticality: string;
  migration_strategy: string;
  project_id: string;
}

export interface DependencyEdge {
  source: string;
  target: string;
  dependency_type: string;
}

export interface DependencyGraph {
  nodes: WorkloadSummary[];
  edges: DependencyEdge[];
  circular_dependencies: string[][];
  migration_groups: string[][];
}

export interface MigrationOrderResponse {
  order: string[];
  migration_groups: string[][];
  circular_dependencies: string[][];
  has_circular: boolean;
  workload_names: Record<string, string>;
}

// --- Migration Wave Planning ---

export interface WaveGenerateRequest {
  project_id: string;
  strategy?: string;
  max_wave_size?: number | null;
  plan_name?: string;
}

export interface WaveWorkloadItem {
  id: string;
  workload_id: string;
  name: string;
  type: string;
  criticality: string;
  migration_strategy: string;
  position: number;
  dependencies: string[];
}

export interface WaveResponse {
  id: string;
  name: string;
  order: number;
  status: string;
  notes: string | null;
  workloads: WaveWorkloadItem[];
  created_at: string;
  updated_at: string;
}

export interface ValidationWarning {
  type: string;
  message: string;
  wave_id: string | null;
  workload_id: string | null;
}

export interface WavePlanResponse {
  id: string;
  project_id: string;
  name: string;
  strategy: string;
  is_active: boolean;
  waves: WaveResponse[];
  warnings: ValidationWarning[];
  created_at: string;
  updated_at: string;
}

export interface WaveUpdateRequest {
  name?: string;
  status?: string;
  notes?: string;
  workload_ids?: string[];
}

export interface MoveWorkloadRequest {
  workload_id: string;
  target_wave_id: string;
  position?: number;
}

export interface ADRRecord {
  id: string;
  title: string;
  status: string;
  context: string;
  decision: string;
  consequences: string;
  category: string;
  created_at: string;
}

export interface ADRGenerateResponse {
  adrs: ADRRecord[];
  project_id: string | null;
}

export interface PluginResponse {
  name: string;
  version: string;
  plugin_type: string;
  description: string;
  enabled: boolean;
}

export interface PluginListResponse {
  plugins: PluginResponse[];
  total: number;
}

// ── Drift remediation types ───────────────────────────────────────────────

export interface RemediationRequest {
  finding_id: string;
  action: "accept" | "revert" | "suppress";
  justification?: string;
  expiration_days?: number;
}

export interface BatchRemediationRequest {
  finding_ids: string[];
  action: "accept" | "revert" | "suppress";
  justification?: string;
  expiration_days?: number;
}

export interface RemediationResponseType {
  id: string;
  finding_id: string;
  action: string;
  status: string;
  result_details: Record<string, unknown>;
  created_at: string;
}

export interface BatchRemediationResponseType {
  results: RemediationResponseType[];
  total: number;
  succeeded: number;
  failed: number;
}

export interface RemediationAuditEntry {
  id: string;
  actor: string;
  action: string;
  finding_id: string;
  justification: string | null;
  timestamp: string;
}

export interface RemediationAuditLogType {
  entries: RemediationAuditEntry[];
  total: number;
}

export interface DriftFinding {
  id: string;
  resource_type: string;
  resource_id: string;
  drift_type: string;
  expected_value: Record<string, unknown> | null;
  actual_value: Record<string, unknown> | null;
  severity: "critical" | "high" | "medium" | "low";
  detected_at: string;
  resolved_at: string | null;
  resolution_type: string | null;
}

// ── Governance scorecard types ────────────────────────────────────────────

export interface CategoryScore {
  name: string;
  score: number;
  status: "healthy" | "warning" | "critical";
  finding_count: number;
}

export interface GovernanceScoreResponse {
  overall_score: number;
  categories: CategoryScore[];
  executive_summary: string;
  last_updated: string | null;
}

export interface ScoreTrendPoint {
  timestamp: string;
  overall_score: number;
  category_scores: Record<string, number>;
}

export interface ScoreTrendResponse {
  project_id: string;
  data_points: ScoreTrendPoint[];
}

export interface ExecutiveSummaryResponse {
  executive_summary: string;
}

// ── Policy types ──────────────────────────────────────────────────────────

export interface PolicyDefinition {
  name: string;
  display_name: string;
  description: string;
  mode: string;
  policy_rule: Record<string, unknown>;
  parameters: Record<string, unknown>;
  metadata: Record<string, unknown>;
}

export interface PolicyValidationResult {
  valid: boolean;
  errors: string[];
  warnings: string[];
}

export interface PolicyTemplate {
  id: string;
  name: string;
  description: string;
  category: string;
  policy_json: Record<string, unknown>;
}

// ── Architecture Comparison types ─────────────────────────────────────────

export interface ArchitectureVariant {
  name: string;
  description: string;
  architecture: Record<string, unknown>;
  resource_count: number;
  estimated_monthly_cost_min: number;
  estimated_monthly_cost_max: number;
  complexity: "simple" | "moderate" | "complex";
  compliance_scores: Record<string, number>;
}

export interface ComparisonResult {
  variants: ArchitectureVariant[];
  tradeoff_analysis: string;
  recommended_index: number;
}

// ── Security posture types ───────────────────────────────────────────────

export interface SecurityFindingResponse {
  id: string;
  severity: "critical" | "high" | "medium" | "low";
  category: string;
  resource: string;
  finding: string;
  remediation: string;
  auto_fixable: boolean;
}

export interface SecurityAnalysisResponse {
  score: number;
  findings: SecurityFindingResponse[];
  summary: string;
  analyzed_at: string;
}

export interface SecurityCheckItem {
  id: string;
  name: string;
  description: string;
  category: string;
  severity: "critical" | "high" | "medium" | "low";
}

export interface SecurityRemediationStep {
  finding_id: string;
  description: string;
  architecture_changes: Record<string, unknown>;
}

// ── Chat / Conversation types ───────────────────────────────────────────

export interface ConversationMessageItem {
  id: string;
  role: "system" | "user" | "assistant";
  content: string;
  token_count: number | null;
  created_at: string;
}

export interface ConversationResponse {
  id: string;
  title: string | null;
  status: string;
  model_name: string;
  total_tokens: number;
  project_id: string;
  created_at: string;
  updated_at: string;
  message_count: number;
}

export interface ConversationWithMessages extends ConversationResponse {
  messages: ConversationMessageItem[];
}

export interface SendMessageApiResponse {
  assistant_message: ConversationMessageItem;
  conversation: ConversationResponse;
}

// ── Pipeline types ──────────────────────────────────────────────────────

export interface PipelineTemplate {
  name: string;
  description: string;
  iac_format: string;
  pipeline_format: string;
}

export interface PipelineFileItem {
  name: string;
  content: string;
  size_bytes: number;
  environment: string;
}

export interface PipelineGenerateResponse {
  files: PipelineFileItem[];
  total_files: number;
  iac_format: string;
  pipeline_format: string;
  environments: string[];
}

// ── Architecture Version types ──────────────────────────────────────────

export interface ArchitectureVersionItem {
  id: string;
  version_number: number;
  architecture_json: string;
  change_summary: string | null;
  created_by: string | null;
  created_at: string;
}

export interface VersionListResponse {
  versions: ArchitectureVersionItem[];
  total: number;
}

export interface ComponentChange {
  name: string;
  detail: string;
}

export interface VersionDiffResult {
  from_version: number;
  to_version: number;
  added_components: ComponentChange[];
  removed_components: ComponentChange[];
  modified_components: ComponentChange[];
  summary: string;
}

// ── Enhanced Diff types ─────────────────────────────────────────────────

export interface PropertyDiff {
  property_name: string;
  old_value: unknown;
  new_value: unknown;
  change_type: "added" | "removed" | "modified";
}

export interface EnhancedComponentChange {
  name: string;
  detail: string;
  category: string;
  property_diffs: PropertyDiff[];
}

export interface CategoryGroup {
  category: string;
  display_name: string;
  added: EnhancedComponentChange[];
  removed: EnhancedComponentChange[];
  modified: EnhancedComponentChange[];
}

export interface EnhancedVersionDiffResult {
  from_version: number;
  to_version: number;
  added_components: EnhancedComponentChange[];
  removed_components: EnhancedComponentChange[];
  modified_components: EnhancedComponentChange[];
  summary: string;
  change_counts: Record<string, number>;
  category_groups: CategoryGroup[];
}

// ── Conflict types ──────────────────────────────────────────────────────

export interface ConflictResponse {
  current_version: number;
  submitted_version: number;
  current_data: Record<string, unknown>;
  message: string;
}

// ── Collaboration types ─────────────────────────────────────────────────

export interface ProjectMemberCreateRequest {
  email: string;
  role?: "owner" | "editor" | "viewer";
}

export interface ProjectMemberResponse {
  id: string;
  user_id: string;
  email: string;
  display_name: string;
  role: string;
  invited_at: string;
  accepted_at: string | null;
}

export interface ProjectMemberListResponse {
  members: ProjectMemberResponse[];
  total: number;
}

export interface CommentCreateRequest {
  content: string;
  component_ref?: string;
}

export interface CommentResponseItem {
  id: string;
  content: string;
  component_ref: string | null;
  user_id: string;
  display_name: string;
  created_at: string;
}

export interface CommentListResponse {
  comments: CommentResponseItem[];
  total: number;
}

export interface ActivityEntryItem {
  type: string;
  user_id: string;
  description: string;
  timestamp: string;
}

export interface ActivityFeedResponse {
  activities: ActivityEntryItem[];
}

// ── Architecture Review types ───────────────────────────────────────────

export interface ReviewActionRequest {
  action: "approved" | "changes_requested" | "rejected";
  comments?: string;
}

export interface ReviewResponseItem {
  id: string;
  architecture_id: string;
  reviewer_id: string;
  action: string;
  comments: string | null;
  created_at: string;
}

export interface ReviewHistoryResponse {
  reviews: ReviewResponseItem[];
  current_status: string;
  required_approvals: number;
  approvals_received: number;
}

export interface ReviewStatusResponse {
  status: string;
  is_locked: boolean;
  can_deploy: boolean;
  approvals_needed: number;
  approvals_received: number;
}

export interface ReviewSubmitResponse {
  architecture_id: string;
  status: string;
  is_locked: boolean;
}

export interface ReviewConfigurationResponse {
  id: string;
  project_id: string;
  required_approvals: number;
  created_at: string;
  updated_at: string;
}

// ── MSP Dashboard types ─────────────────────────────────────────────

export interface MSPTenantOverview {
  tenant_id: string;
  name: string;
  status: string;
  last_activity: string | null;
  compliance_score: number;
  project_count: number;
  deployment_count: number;
  active_deployments: number;
}

export interface MSPOverviewResponse {
  tenants: MSPTenantOverview[];
  total_tenants: number;
  total_projects: number;
  avg_compliance_score: number;
}

export interface MSPDeploymentSummary {
  id: string;
  project_name: string;
  status: string;
  started_at: string | null;
  completed_at: string | null;
}

export interface MSPTenantHealthResponse {
  tenant_id: string;
  name: string;
  compliance_score: number;
  compliance_status: string;
  recent_deployments: MSPDeploymentSummary[];
  active_alerts: number;
  resource_count: number;
}

export interface MSPTenantComplianceScore {
  tenant_id: string;
  name: string;
  score: number;
  status: string;
}

export interface MSPComplianceSummaryResponse {
  total_tenants: number;
  passing: number;
  warning: number;
  failing: number;
  scores_by_tenant: MSPTenantComplianceScore[];
}

// ── Template Marketplace Types ──────────────────────────────────────────

export interface TemplateItem {
  id: string;
  name: string;
  description: string | null;
  industry: string;
  tags: string[];
  architecture_json: string | null;
  author_tenant_id: string | null;
  visibility: string;
  download_count: number;
  rating_up: number;
  rating_down: number;
  created_at: string;
  updated_at: string;
}

export interface TemplateListResponse {
  templates: TemplateItem[];
  total: number;
  page: number;
  page_size: number;
}

// ── Cloud Environment Types ─────────────────────────────────────────────

export interface CloudEnvironmentItem {
  name: string;
  display_name: string;
  description: string;
  available_regions: string[];
}

export interface CloudEndpointsItem {
  resource_manager: string;
  authentication: string;
  portal: string;
  graph: string;
  storage_suffix: string;
  sql_suffix: string;
  keyvault_suffix: string;
  ai_foundry: string | null;
}

export interface CloudValidationResult {
  supported: boolean;
  missing_services: string[];
  warnings: string[];
}

// ── Sovereign Compliance Types ──────────────────────────────────────────

export interface SovereignControl {
  id: string;
  name: string;
  description: string;
  control_count: number;
}

export interface SovereignFrameworkSummary {
  short_name: string;
  name: string;
  description: string;
  version: string;
  cloud_environments: string[];
  control_family_count: number;
}

export interface SovereignFrameworkListResponse {
  frameworks: SovereignFrameworkSummary[];
  total: number;
}

export interface SovereignFrameworkDetail {
  short_name: string;
  name: string;
  description: string;
  version: string;
  cloud_environments: string[];
  control_families: SovereignControl[];
  total_controls: number;
}

export interface FamilyScoreResult {
  family_id: string;
  family_name: string;
  score: number | null;
  status: string;
  controls_evaluated: number;
  controls_met: number;
}

export interface SovereignComplianceResult {
  framework: string;
  framework_name: string;
  overall_score: number;
  status: string;
  total_controls_evaluated: number;
  total_controls_met: number;
  family_scores: FamilyScoreResult[];
  recommendations: string[];
  message?: string;
}

export interface ServiceAvailabilityItem {
  service_name: string;
  category: string;
  commercial: boolean;
  government: boolean;
  china: boolean;
  notes: string;
}

export interface ServiceAvailabilityMatrix {
  environments: string[];
  services: ServiceAvailabilityItem[];
  by_category: Record<string, ServiceAvailabilityItem[]>;
  total_services: number;
}

export interface ArchitectureCompatibilityResult {
  compatible: boolean;
  target_environment: string;
  services_checked: number;
  missing_services: string[];
  warnings: string[];
  alternatives: Record<string, string>;
}

// ── China Types ─────────────────────────────────────────────────────────────

// ── Government Cloud Types ───────────────────────────────────────────────────

export interface GovernmentRegionResponse {
  name: string;
  display_name: string;
  paired_region: string;
  geography: string;
  available_zones: string[];
  restricted: boolean;
}

export interface GovernmentRegionListResponse {
  regions: GovernmentRegionResponse[];
  total: number;
}

export interface GovernmentBicepResponse {
  customized_content: string;
  changes_applied: string[];
}

export interface GovernmentQuestionResponse {
  id: string;
  text: string;
  type: string;
  options: { value: string; label: string; group?: string }[];
  required: boolean;
  category: string;
  help_text: string;
}

export interface GovernmentConstraintsResponse {
  architecture: Record<string, unknown>;
  warnings: string[];
}

// ── China Cloud Types ───────────────────────────────────────────────────────

export interface ChinaRegionResponse {
  name: string;
  display_name: string;
  paired_region: string;
  geography: string;
  available_zones: string[];
}

export interface ChinaRegionListResponse {
  regions: ChinaRegionResponse[];
  total: number;
}

export interface ChinaBicepResponse {
  customized_content: string;
  region: string;
  compliance_level: string;
  endpoints_replaced: number;
}

export interface ChinaQuestionResponse {
  id: string;
  text: string;
  description: string;
  type: string;
  options: { value: string; label: string }[];
  required: boolean;
  category: string;
}

export interface ChinaConstraintsResponse {
  architecture: Record<string, unknown>;
  region: string;
  compliance_level: string;
  cloud_environment: string;
}

export interface DataResidencyResponse {
  jurisdiction: string;
  data_boundary: string;
  cross_border_transfer: boolean;
  regulations: string[];
  requirements: string[];
  operator: string;
  operator_relationship: string;
}

export interface ICPRequirementsResponse {
  requires_icp: boolean;
  affected_resources: string[];
  resource_types_checked: number;
  guidance: string;
  icp_types: { type: string; description: string; applies_to: string }[];
}

// ── Confidential Computing Types ────────────────────────────────────────

export interface ConfidentialOption {
  id: string;
  name: string;
  category: string;
  tee_types: string[];
  description: string;
  use_cases: string[];
  vm_series: string[];
  attestation_supported: boolean;
}

export interface ConfidentialOptionsListResponse {
  options: ConfidentialOption[];
  total: number;
}

export interface ConfidentialVmSku {
  name: string;
  series: string;
  vcpus: number;
  memory_gb: number;
  tee_type: string;
  vendor: string;
  max_data_disks: number;
  enclave_memory_mb: number | null;
  description: string;
}

export interface ConfidentialVmSkuListResponse {
  skus: ConfidentialVmSku[];
  total: number;
}

export interface ConfidentialRegion {
  name: string;
  display_name: string;
  tee_types: string[];
  services: string[];
}

export interface ConfidentialRegionListResponse {
  regions: ConfidentialRegion[];
  total: number;
}

export interface ConfidentialRecommendResponse {
  workload_type: string;
  recommended_option: Record<string, unknown>;
  recommended_skus: Record<string, unknown>[];
  region_options: Record<string, unknown>[];
  attestation: Record<string, unknown> | null;
  rationale: string;
}

export interface ConfidentialArchitectureResponse {
  architecture: Record<string, unknown>;
  cc_enabled: boolean;
}

export interface ConfidentialBicepResponse {
  template_type: string;
  bicep_template: string;
  description: string;
}

export interface AttestationConfigResponse {
  cc_type: string;
  attestation_provider: string;
  protocol: string;
  evidence_type: string;
  key_release_policy: string;
  steps: string[];
}

// ── Workload Extensions Types ─────────────────────────────────────────

export interface WorkloadExtensionItem {
  workload_type: string;
  display_name: string;
  description: string;
}

export interface WorkloadQuestion {
  id: string;
  category: string;
  text: string;
  type: string;
  options?: { value: string; label: string }[];
  required: boolean;
  order: number;
}

export interface BestPractice {
  id: string;
  title: string;
  description: string;
  category: string;
  severity: string;
}

export interface WorkloadExtensionDetail {
  workload_type: string;
  display_name: string;
  description: string;
  questions: WorkloadQuestion[];
  best_practices: BestPractice[];
}

export interface WorkloadValidationResult {
  workload_type: string;
  valid: boolean;
  errors: string[];
  warnings: string[];
  suggestions: string[];
}

// ── SKU Types ─────────────────────────────────────────────────────────

export interface SkuListResult {
  skus: Record<string, unknown>[];
  count: number;
}

export interface SkuRecommendResult {
  recommended_sku: Record<string, unknown>;
  reason: string;
  alternatives: Record<string, unknown>[];
}

export interface SkuAvailabilityResult {
  available: boolean;
  sku: string;
  region: string;
  cloud_env: string;
  reason?: string;
}

// ── Architecture Validation Types ─────────────────────────────────────

export interface ArchValidationResult {
  valid: boolean;
  errors: string[];
  warnings: string[];
  suggestions?: string[];
  framework?: string;
}

export interface ValidationRule {
  id: string;
  category: string;
  description: string;
  severity: string;
}
