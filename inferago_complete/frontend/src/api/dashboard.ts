import api from "./client";

export const getDashboard  = (workflowId: string) => api.get(`/api/dashboard/${workflowId}`).then((r) => r.data);
export const getHealth     = (workflowId: string) => api.get(`/api/analytics/${workflowId}/health`).then((r) => r.data);
export const getSuggestions = (workflowId: string) => api.get(`/api/suggestions/${workflowId}`).then((r) => r.data);
export const getPlatforms  = () => api.get("/api/analytics/platforms/summary").then((r) => r.data);
export const getRagSummary = (workflowId: string) => api.get(`/api/rag/${workflowId}/summary`).then((r) => r.data);
export const getRagEfficiency = (workflowId: string) => api.get(`/api/rag/${workflowId}/efficiency`).then((r) => r.data);
export const getAlerts     = (workflowId: string) => api.get(`/api/alerts/${workflowId}`).then((r) => r.data);
export const createAlert   = (data: any) => api.post("/api/alerts/", data).then((r) => r.data);
export const deleteAlert   = (id: string) => api.delete(`/api/alerts/${id}`).then(() => undefined);
