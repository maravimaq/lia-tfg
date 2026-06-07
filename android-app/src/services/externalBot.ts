import { api } from "./api";
import {
  ExternalBotBindingStatusResponse,
  ExternalBotLinkCodeResponse,
  ExternalBotMessageResponse,
  TelegramBotInfoResponse,
} from "@/src/types/externalBot";

export const externalBotService = {
  async getTelegramBotInfo() {
    const { data } = await api.get<TelegramBotInfoResponse>("/external-bot/telegram/me");
    return data;
  },

  async createLinkCode(plataforma = "telegram") {
    const { data } = await api.post<ExternalBotLinkCodeResponse>("/external-bot/link-code", {
      plataforma,
    });
    return data;
  },

  async getBindingStatus(plataforma = "telegram") {
    const { data } = await api.get<ExternalBotBindingStatusResponse>(
      "/external-bot/binding-status",
      { params: { plataforma } }
    );
    return data;
  },

  async getMessages(plataforma = "telegram", limit = 20) {
    const { data } = await api.get<ExternalBotMessageResponse[]>("/external-bot/messages", {
      params: { plataforma, limit },
    });
    return data;
  },
};
