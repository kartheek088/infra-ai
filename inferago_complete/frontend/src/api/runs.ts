import api from "./client";

export interface Run {
  id: string;
  workflow_id: string;
  n8n_execution_id: string | null;
  status: string;
  triggered_by: string | null;
  platform: string;
  duration_ms: number | null;
  started_at: string | null;
  finished_at: string | null;
  created_at: string;
}

export interface TokenNode {
  id: string;
  run_id: string;
  node_name: string;
  model: string | null;
  prompt_tokens: number;
  completion_tokens: number;
  total_tokens: number;
  cost_usd: number;
  recorded_at: string;
}

export interface RunTrace {
  run_id: string;
  status: string;
  platform: string;
  triggered_by: string | null;
  duration_ms: number | null;
  started_at: string | null;
  finished_at: string | null;
  total_tokens: number;
  total_cost_usd: number;
  error_hint: string | null;
  node_trace: {
    step: number;
    node_name: string;
    model: string;
    prompt_tokens: number;
    completion_tokens: number;
    total_tokens: number;
    cost_usd: number;
    cost_pct: number;
    recorded_at: string | null;
  }[];
}

export interface TokenTrend {
  days: number;
  data: {
    date: string;
    runs: number;
    prompt_tokens: number;
    completion_tokens: number;
    total_tokens: number;
    cost_usd: number;
  }[];
  summary: {
    total_tokens: number;
    total_cost_usd: number;
    avg_tokens_per_day: number;
    peak_tokens_day: number;
    avg_cost_per_day: number;
    peak_cost_day: number;
  };
}

export interface CostBreakdown {
  avg_cost_per_run: number;
  per_day: number;
  per_week: number;
  per_month: number;
  projected_monthly: number;
  runs_per_day_estimate: number;
  total_runs_analyzed: number;
}

export const getRuns = (
  workflowId: string,
  params?: {
    status?: string;
    platform?: string;
    date_from?: string;
    date_to?: string;
    min_cost?: number;
    limit?: number;
  }
): Promise<Run[]> =>
  api.get(`/api/runs/${workflowId}`, { params }).then((r) => r.data);

export const getRunTrace = (runId: string): Promise<RunTrace> =>
  api.get(`/api/runs/${runId}/trace`).then((r) => r.data);

export const getRunTokens = (runId: string) =>
  api.get(`/api/runs/${runId}/tokens`).then((r) => r.data);

export const getTokenTrend = (workflowId: string, days: number = 30): Promise<TokenTrend> =>
  api.get(`/api/analytics/${workflowId}/token-trend`, { params: { days } }).then((r) => r.data);

export const getCostBreakdown = (workflowId: string): Promise<CostBreakdown> =>
  api.get(`/api/analytics/${workflowId}/cost-breakdown`).then((r) => r.data);

export const getInefficiencyScore = (workflowId: string) =>
  api.get(`/api/analytics/${workflowId}/inefficiency-score`).then((r) => r.data);
