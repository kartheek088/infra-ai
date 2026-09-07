import api from "./client";

export interface PolicyCondition {
  field: string;
  operator: string;
  value: any;
}

export interface Policy {
  id: string;
  name: string;
  description: string;
  enabled: boolean;
  action: string;
  priority: number;
  applies_to_all_workflows: boolean;
  workflow_ids: string[] | null;
  conditions: { all?: PolicyCondition[]; any?: PolicyCondition[] };
  notify_on_trigger: boolean;
  created_at: string;
  updated_at: string | null;
}

export interface CreatePolicyPayload {
  name: string;
  description?: string;
  enabled?: boolean;
  action: string;
  priority?: number;
  applies_to_all_workflows?: boolean;
  workflow_ids?: string[];
  conditions: { all?: PolicyCondition[]; any?: PolicyCondition[] };
  notify_on_trigger?: boolean;
}

export const getPolicies = (): Promise<Policy[]> => api.get("/api/policies/").then((r) => r.data);
export const getPolicy = (id: string): Promise<Policy> => api.get(`/api/policies/${id}`).then((r) => r.data);
export const createPolicy = (data: CreatePolicyPayload): Promise<Policy> => api.post("/api/policies/", data).then((r) => r.data);
export const updatePolicy = (id: string, data: Partial<CreatePolicyPayload>): Promise<Policy> => api.patch(`/api/policies/${id}`, data).then((r) => r.data);
export const deletePolicy = (id: string): Promise<void> => api.delete(`/api/policies/${id}`).then(() => undefined);
