import api from "./client";

export interface Workflow {
  id: string;
  name: string;
  description: string | null;
  n8n_workflow_id?: string | null;
  platform?: string | null;
  created_at: string;
  updated_at?: string | null;
}

export interface CreateWorkflowPayload { name: string; description?: string; n8n_workflow_id: string; }
export interface UpdateWorkflowPayload { name?: string; description?: string; }

export const getWorkflows  = (): Promise<Workflow[]>  => api.get("/api/workflows/").then((r) => r.data);
export const getWorkflow   = (id: string): Promise<Workflow> => api.get(`/api/workflows/${id}`).then((r) => r.data);
export const createWorkflow = (data: CreateWorkflowPayload): Promise<Workflow> => api.post("/api/workflows/", data).then((r) => r.data);
export const updateWorkflow = (id: string, data: UpdateWorkflowPayload): Promise<Workflow> => api.patch(`/api/workflows/${id}`, data).then((r) => r.data);
export const deleteWorkflow = (id: string): Promise<void> => api.delete(`/api/workflows/${id}`).then(() => undefined);
