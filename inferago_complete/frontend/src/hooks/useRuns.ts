import { useQuery } from "@tanstack/react-query";
import {
  getRuns,
  getRunTrace,
  getTokenTrend,
  getCostBreakdown,
  getInefficiencyScore,
} from "../api/runs";

export const useRuns = (
  workflowId: string,
  filters?: {
    status?: string;
    platform?: string;
    date_from?: string;
    date_to?: string;
    min_cost?: number;
    limit?: number;
  }
) =>
  useQuery({
    queryKey: ["runs", workflowId, filters],
    queryFn:  () => getRuns(workflowId, filters),
    enabled:  !!workflowId,
    refetchInterval: 30_000,
  });

export const useRunTrace = (runId: string) =>
  useQuery({
    queryKey: ["run-trace", runId],
    queryFn:  () => getRunTrace(runId),
    enabled:  !!runId,
  });

export const useTokenTrend = (workflowId: string, days: number = 30) =>
  useQuery({
    queryKey: ["token-trend", workflowId, days],
    queryFn:  () => getTokenTrend(workflowId, days),
    enabled:  !!workflowId,
    refetchInterval: 60_000,
  });

export const useCostBreakdown = (workflowId: string) =>
  useQuery({
    queryKey: ["cost-breakdown", workflowId],
    queryFn:  () => getCostBreakdown(workflowId),
    enabled:  !!workflowId,
    refetchInterval: 60_000,
  });

export const useInefficiencyScore = (workflowId: string) =>
  useQuery({
    queryKey: ["inefficiency", workflowId],
    queryFn:  () => getInefficiencyScore(workflowId),
    enabled:  !!workflowId,
  });
