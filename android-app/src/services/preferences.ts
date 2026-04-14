import { api } from "./api";
import {
  PreferenciasResponse,
  PreferenciasUpdatePayload,
} from "@/src/types/preferences";

export const preferencesService = {
  async getMyPreferences() {
    const { data } = await api.get<PreferenciasResponse>("/users/me/preferences");
    return data;
  },

  async updateMyPreferences(payload: PreferenciasUpdatePayload) {
    const { data } = await api.put<PreferenciasResponse>(
      "/users/me/preferences",
      payload
    );
    return data;
  },
};