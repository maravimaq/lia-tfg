import { api } from "./api";
import {
  ForgotPasswordPayload,
  ForgotPasswordResponse,
  LoginPayload,
  RegisterPayload,
  TokenResponse,
} from "@/src/types/auth";
import { UserResponse } from "@/src/types/user";

export const authService = {
  async login(payload: LoginPayload) {
    const { data } = await api.post<TokenResponse>("/auth/login", payload);
    return data;
  },

  async register(payload: RegisterPayload) {
    const { data } = await api.post<UserResponse>("/auth/register", payload);
    return data;
  },

  async forgotPassword(payload: ForgotPasswordPayload) {
    const { data } = await api.post<ForgotPasswordResponse>("/auth/forgot-password", payload);
    return data;
  },

  async logout(token?: string | null) {
    const { data } = await api.post(
      "/auth/logout",
      undefined,
      token ? { headers: { Authorization: `Bearer ${token}` } } : undefined
    );
    return data;
  },
};