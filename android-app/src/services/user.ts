import { api } from "./api";
import {
  AccountActionRequestPayload,
  AccountActionRequestResponse,
  BotConfigResponse,
  BotConfigUpdatePayload,
  ChangePasswordPayload,
  DiscoverUserResponse,
  FollowRequestResponse,
  IncomingFollowRequestItem,
  SessionResponse,
  UserResponse,
  UserUpdatePayload,
} from "@/src/types/user";

export const userService = {
  async getMe() {
    const { data } = await api.get<UserResponse>("/users/me");
    return data;
  },

  async getPublicProfile(userId: number) {
    const { data } = await api.get<UserResponse>(`/users/${userId}/public`);
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

  async getMyBotConfig() {
    const { data } = await api.get<BotConfigResponse>("/users/me/bot-config");
    return data;
  },

  async updateMyBotConfig(payload: BotConfigUpdatePayload) {
    const { data } = await api.put<BotConfigResponse>("/users/me/bot-config", payload);
    return data;
  },

  async getMySessions() {
    const { data } = await api.get<SessionResponse[]>("/users/me/sessions");
    return data;
  },

  async closeCurrentSession() {
    const { data } = await api.delete<{ message: string }>("/users/me/sessions/current");
    return data;
  },

  async requestAccountAction(payload: AccountActionRequestPayload) {
    const { data } = await api.post<AccountActionRequestResponse>(
      "/users/me/account-action-request",
      payload
    );
    return data;
  },

  async discoverUsers(search = "") {
    const { data } = await api.get<DiscoverUserResponse[]>("/users/discover", {
      params: search.trim() ? { search } : undefined,
    });
    return data;
  },

  async sendFollowRequest(targetUserId: number) {
    const { data } = await api.post<FollowRequestResponse>(`/users/follow-requests/${targetUserId}`);
    return data;
  },

  async getIncomingFollowRequests() {
    const { data } = await api.get<IncomingFollowRequestItem[]>("/users/me/follow-requests/incoming");
    return data;
  },

  async respondFollowRequest(requestId: number, action: "aceptar" | "rechazar") {
    const { data } = await api.put<{ message: string }>(`/users/me/follow-requests/${requestId}/respond`, {
      accion: action,
    });
    return data;
  },
};