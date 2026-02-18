export type ProjectStatus =
  | "draft"
  | "questionnaire_complete"
  | "architecture_generated"
  | "compliance_scored"
  | "bicep_ready"
  | "deploying"
  | "deployed"
  | "failed";

export interface Project {
  id: string;
  name: string;
  description: string | null;
  status: ProjectStatus;
  created_at: string;
  updated_at: string;
}

export interface ProjectCreate {
  name: string;
  description?: string;
}

export interface ProjectUpdate {
  name?: string;
  description?: string;
  status?: ProjectStatus;
}

export interface ProjectStats {
  total: number;
  by_status: Record<string, number>;
  avg_compliance_score: number | null;
  deployment_success_rate: number | null;
  recent_projects: Project[];
}
