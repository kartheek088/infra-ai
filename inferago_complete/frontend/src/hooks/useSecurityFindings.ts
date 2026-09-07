import { useQuery } from "@tanstack/react-query";
import { getFindings } from "../api/findings";
import type { SecurityFinding } from "../api/findings";

/**
 * Security findings scoped to a single execution.
 * Uses the run_id filter on GET /api/security-findings.
 */
export function useSecurityFindingsForRun(executionId: string | undefined) {
  return useQuery<SecurityFinding[]>({
    queryKey: ["security-findings-for-run", executionId],
    queryFn:  () => getFindings({ run_id: executionId, limit: 50 }),
    enabled:  !!executionId,
  });
}
