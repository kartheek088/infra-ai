import { useQuery } from "@tanstack/react-query";
import { getDashboard, getPlatforms } from "../api/dashboard";

export const useDashboard = (workflowId: string) =>
  useQuery({
    queryKey: ["dashboard", workflowId],
    queryFn:  () => getDashboard(workflowId),
    enabled:  !!workflowId,
    refetchInterval: 30_000,
  });

export const usePlatforms = () =>
  useQuery({ queryKey: ["platforms"], queryFn: getPlatforms, refetchInterval: 60_000 });
