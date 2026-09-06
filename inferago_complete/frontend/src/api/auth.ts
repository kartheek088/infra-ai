import api from "./client";

export interface TokenResponse { access_token: string; token_type: string; user_id: string; }
export interface RegisterPayload { email: string; password: string; full_name: string; }
export interface LoginPayload { email: string; password: string; }

export const registerUser = (data: RegisterPayload): Promise<TokenResponse> =>
  api.post("/api/auth/register", data).then((r) => r.data);

export const loginUser = (data: LoginPayload): Promise<TokenResponse> =>
  api.post("/api/auth/login", data).then((r) => r.data);

export const getMe = () => api.get("/api/auth/me").then((r) => r.data);
