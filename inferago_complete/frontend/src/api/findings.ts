import api from "./client";

export interface SecurityFinding {
  id: string;
  workflow_id: string;
  run_id: string;
  detector_id: string;
  severity: "critical" | "high" | "medium" | "low" | "info";
  title: string;
  description: string;
  risk_score: number;
  evidence: Record<string, any>;
  governance_action: string | null;
  policy_id: string | null;
  policy_name: string | null;
  created_at: string;
}

export interface AuditLog {
  id: string;
  user_id: string;
  entity_type: string;
  entity_id: string;
  action: string;
  performed_by: string;
  snapshot: Record<string, any>;
  note: string | null;
  created_at: string;
}

export const getFindings = (params?: { workflow_id?: string; severity?: string; limit?: number }): Promise<SecurityFinding[]> =>
  api.get("/api/security-findings", { params }).then((r) => r.data);

export const getFinding = (id: string): Promise<SecurityFinding> =>
  api.get(`/api/security-findings/${id}`).then((r) => r.data);

export const getAuditLogs = (params?: { entity_type?: string; limit?: number }): Promise<AuditLog[]> =>
  api.get("/api/audit-logs", { params }).then((r) => r.data);
