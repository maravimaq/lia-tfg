import { api } from "./api";
import {
  ChangePasswordPayload,
  UserResponse,
  UserUpdatePayload,
} from "@/src/types/user";

export const userService = {
  async getMe() {
    const { data } = await api.get<UserResponse>("/users/me");
    return data;
  },

  async updateMe(payload: UserUpdatePayload) {
    const { data } = await api.put<UserResponse>("/users/me", payload);
    return data;
  },

  async changePassword(payload: ChangePasswordPayload) {
    const { data } = await api.put("/users/me/password", payload);
    return data;
  },
};