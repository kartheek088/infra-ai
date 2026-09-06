import { create } from "zustand";

interface AuthState {
  token: string | null;
  userId: string | null;
  isAuthenticated: boolean;
  login: (token: string, userId: string) => void;
  logout: () => void;
}

export const useAuthStore = create<AuthState>((set) => ({
  token:           localStorage.getItem("token"),
  userId:          localStorage.getItem("userId"),
  isAuthenticated: !!localStorage.getItem("token"),
  login: (token, userId) => {
    localStorage.setItem("token", token);
    localStorage.setItem("userId", userId);
    set({ token, userId, isAuthenticated: true });
  },
  logout: () => {
    localStorage.removeItem("token");
    localStorage.removeItem("userId");
    set({ token: null, userId: null, isAuthenticated: false });
  },
}));
