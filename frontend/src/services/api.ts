const API_BASE = import.meta.env.VITE_API_URL || "http://localhost:8000";

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

export const api = {
  questionnaire: {
    getCategories: () => fetchApi<{ categories: Category[] }>("/api/questionnaire/categories"),
    getQuestions: () => fetchApi<{ questions: Question[] }>("/api/questionnaire/questions"),
    getNextQuestion: (answers: Record<string, string | string[]>) =>
      fetchApi<{ complete: boolean; question: Question | null; progress?: Progress }>(
        "/api/questionnaire/next",
        { method: "POST", body: JSON.stringify({ answers }) }
      ),
    getProgress: (answers: Record<string, string | string[]>) =>
      fetchApi<Progress>("/api/questionnaire/progress", {
        method: "POST",
        body: JSON.stringify({ answers }),
      }),
  },
  architecture: {
    getArchetypes: () => fetchApi<{ archetypes: Archetype[] }>("/api/architecture/archetypes"),
    generate: (answers: Record<string, string | string[]>, useAi = false) =>
      fetchApi<{ architecture: Architecture }>("/api/architecture/generate", {
        method: "POST",
        body: JSON.stringify({ answers, use_ai: useAi }),
      }),
  },
  validateSubscription: (subscriptionId: string, location: string) =>
    fetchApi<{ valid: boolean }>("/api/deployment/validate-subscription", {
      method: "POST",
      body: JSON.stringify({ subscription_id: subscriptionId, location }),
    }),
  compliance: {
    getFrameworks: () => fetchApi<{ frameworks: Framework[] }>("/api/compliance/frameworks"),
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
  options?: { value: string; label: string }[];
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

export interface Framework {
  name: string;
  short_name: string;
  description: string;
  version: string;
  control_count: number;
}
