import { useQuery } from "@tanstack/react-query";
import {
  getExecutions,
  getExecutionTrace,
  getExecutionTokens,
  getTokenTrend,
  getCostBreakdown,
  getInefficiencyScore,
  getExecutionTimeline,
  getExecutionAnomalies,
  getAiExplanation,
} from "../api/executions";

export function useExecutions(
  workflowId: string,
  filters?: { status?: string; platform?: string; date_from?: string; date_to?: string; min_cost?: number; limit?: number }
) {
  return useQuery({
    queryKey: ["executions", workflowId, filters],
    queryFn:  () => getExecutions(workflowId, filters),
    enabled:  !!workflowId,
  });
}

export function useExecutionTrace(executionId: string) {
  return useQuery({
    queryKey: ["execution-trace", executionId],
    queryFn:  () => getExecutionTrace(executionId),
    enabled:  !!executionId,
  });
}

export function useExecutionTokens(executionId: string) {
  return useQuery({
    queryKey: ["execution-tokens", executionId],
    queryFn:  () => getExecutionTokens(executionId),
    enabled:  !!executionId,
  });
}

export function useTokenTrend(workflowId: string, days = 30) {
  return useQuery({
    queryKey: ["token-trend", workflowId, days],
    queryFn:  () => getTokenTrend(workflowId, days),
    enabled:  !!workflowId,
  });
}

export function useCostBreakdown(workflowId: string) {
  return useQuery({
    queryKey: ["cost-breakdown", workflowId],
    queryFn:  () => getCostBreakdown(workflowId),
    enabled:  !!workflowId,
  });
}

export function useInefficiencyScore(workflowId: string) {
  return useQuery({
    queryKey: ["inefficiency-score", workflowId],
    queryFn:  () => getInefficiencyScore(workflowId),
    enabled:  !!workflowId,
  });
}

// ── Phase 4 & 9: timeline, anomalies, AI explanation ──────────────────────────

export function useExecutionTimeline(executionId: string) {
  return useQuery({
    queryKey: ["execution-timeline", executionId],
    queryFn:  () => getExecutionTimeline(executionId),
    enabled:  !!executionId,
  });
}

export function useExecutionAnomalies(executionId: string) {
  return useQuery({
    queryKey: ["execution-anomalies", executionId],
    queryFn:  () => getExecutionAnomalies(executionId),
    enabled:  !!executionId,
  });
}

export function useAiExplanation(executionId: string) {
  return useQuery({
    queryKey: ["ai-explanation", executionId],
    queryFn:  () => getAiExplanation(executionId),
    enabled:  !!executionId,
    // Re-fetch every 15s while pending so the page auto-updates
    refetchInterval: (query) => {
      const status = query.state.data?.status;
      return status === "pending" ? 15_000 : false;
    },
  });
}
