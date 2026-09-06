import { useMutation } from "@tanstack/react-query";
import { useNavigate } from "react-router-dom";
import { loginUser, registerUser } from "../api/auth";
import { useAuthStore } from "../store/authStore";

export const useLogin = () => {
  const navigate = useNavigate();
  const { login } = useAuthStore();
  return useMutation({
    mutationFn: loginUser,
    onSuccess: (data) => { login(data.access_token, data.user_id); navigate("/dashboard"); },
  });
};

export const useRegister = () => {
  const navigate = useNavigate();
  const { login } = useAuthStore();
  return useMutation({
    mutationFn: registerUser,
    onSuccess: (data) => { login(data.access_token, data.user_id); navigate("/dashboard"); },
  });
};

export const useLogout = () => {
  const navigate = useNavigate();
  const { logout } = useAuthStore();
  return () => { logout(); navigate("/login"); };
};
