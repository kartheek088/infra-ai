import api from "./client";

export const generateKey = (name: string) => api.post("/api/keys/generate", { name }).then((r) => r.data);
export const listKeys    = () => api.get("/api/keys/").then((r) => r.data);
export const revokeKey   = (id: string) => api.delete(`/api/keys/${id}`).then(() => undefined);
