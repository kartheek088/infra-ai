import api from "./client";

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
  node_type?: string;
  event_type?: string;
  provider?: string;
  error_message?: string;
  latency_ms?: number;
  node_metadata?: Record<string, unknown>;
}

export interface Execution {
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

export interface ExecutionEvent {
  event_type: string;
  timestamp: string | null;
  node_name: string | null;
  source: string;
  message: string;
  metadata?: Record<string, unknown>;
}

export interface RunTrace {
  execution_id: string;
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
    node_type?: string;
    event_type?: string;
    provider?: string;
    error_message?: string;
    latency_ms?: number;
    node_metadata?: Record<string, unknown>;
  }[];
  events: ExecutionEvent[];
}

// Backend returns: { days, data: [{date,total_tokens,...}], summary: {...} }
export interface TokenTrendData {
  days: number;
  data: {
    date: string;
    total_tokens: number;
    prompt_tokens: number;
    completion_tokens: number;
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

// Backend returns a single cost summary object
export interface CostBreakdownData {
  avg_cost_per_run: number;
  per_day: number;
  per_week: number;
  per_month: number;
  projected_monthly: number;
  runs_per_day_estimate: number;
  total_runs_analyzed: number;
}

// Backend returns: { inefficiency_score, grade, flags, interpretation }
export interface InefficiencyScoreData {
  inefficiency_score: number;
  grade: string;
  flags: string[];
  interpretation: string;
}

export async function getExecutions(
  workflowId: string,
  params?: { status?: string; platform?: string; date_from?: string; date_to?: string; min_cost?: number; limit?: number }
): Promise<Execution[]> {
  const sp = new URLSearchParams();
  if (params?.status)   sp.set("status",   params.status);
  if (params?.platform) sp.set("platform", params.platform);
  if (params?.date_from) sp.set("date_from", params.date_from);
  if (params?.date_to)   sp.set("date_to",   params.date_to);
  if (params?.min_cost)  sp.set("min_cost",  String(params.min_cost));
  if (params?.limit)     sp.set("limit",     String(params.limit));
  const qs = sp.toString();
  return api.get<Execution[]>(`/api/executions/${workflowId}${qs ? `?${qs}` : ""}`).then(res => res.data);
}

export async function getExecutionTrace(executionId: string): Promise<RunTrace> {
  return api.get<RunTrace>(`/api/executions/${executionId}/trace`).then(res => res.data);
}

export async function getExecutionTokens(executionId: string): Promise<{ by_node: TokenNode[] }> {
  return api.get<{ by_node: TokenNode[] }>(`/api/executions/${executionId}/tokens`).then(res => res.data);
}

export async function getTokenTrend(workflowId: string, days = 30): Promise<TokenTrendData> {
  return api.get<TokenTrendData>(`/api/analytics/token-trend/${workflowId}?days=${days}`).then(res => res.data);
}

export async function getCostBreakdown(workflowId: string): Promise<CostBreakdownData> {
  return api.get<CostBreakdownData>(`/api/analytics/cost-breakdown/${workflowId}`).then(res => res.data);
}

export async function getInefficiencyScore(workflowId: string): Promise<InefficiencyScoreData> {
  return api.get<InefficiencyScoreData>(`/api/analytics/inefficiency-score/${workflowId}`).then(res => res.data);
}
