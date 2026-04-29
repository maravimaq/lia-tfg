import { api } from "./api";
import {
  AdminDashboardResponse,
  AdminScrapingActionResponse,
  AdminScrapingOverviewResponse,
  AdminUserCreatePayload,
  AdminUserListItem,
  AdminUsersPageResponse,
  AdminUserUpdatePayload,
} from "@/src/types/admin";

export const adminService = {
  async getDashboard() {
    const { data } = await api.get<AdminDashboardResponse>("/admin/dashboard");
    return data;
  },

  async listUsers(page = 1, size = 10, search?: string) {
    const { data } = await api.get<AdminUsersPageResponse>("/admin/users", {
      params: {
        page,
        size,
        ...(search ? { search } : {}),
      },
    });
    return data;
  },

  async getUserById(userId: number) {
    const { data } = await api.get<AdminUserListItem>(`/admin/users/${userId}`);
    return data;
  },

  async createUser(payload: AdminUserCreatePayload) {
    const { data } = await api.post<AdminUserListItem>("/admin/users", payload);
    return data;
  },

  async updateUser(userId: number, payload: AdminUserUpdatePayload) {
    const { data } = await api.put<AdminUserListItem>(`/admin/users/${userId}`, payload);
    return data;
  },

  async activateUser(userId: number) {
    const { data } = await api.patch<AdminUserListItem>(`/admin/users/${userId}/activate`);
    return data;
  },

  async deactivateUser(userId: number) {
    const { data } = await api.patch<AdminUserListItem>(`/admin/users/${userId}/deactivate`);
    return data;
  },

  async deleteUser(userId: number) {
    const { data } = await api.delete<{ message: string }>(`/admin/users/${userId}`);
    return data;
  },

  async getScrapingOverview() {
    const { data } = await api.get<AdminScrapingOverviewResponse>("/admin/scraping/overview");
    return data;
  },

  async forceScraping() {
    const { data } = await api.post<AdminScrapingActionResponse>("/admin/scraping/force");
    return data;
  },

  async cancelScraping() {
    const { data } = await api.post<AdminScrapingActionResponse>("/admin/scraping/cancel");
    return data;
  },
};
