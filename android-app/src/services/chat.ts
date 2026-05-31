import { api } from "./api";
import {
  ListChatMessageRequest,
  ListChatMessageResponse,
  ListChatStoredMessage,
} from "@/src/types/chat";

const LIST_CHAT_TIMEOUT_MS = 180000;

export const chatService = {
  async getListMessages(listaId: number) {
    const { data } = await api.get<ListChatStoredMessage[]>(
      `/chat/lista/${listaId}/messages`
    );

    return data;
  },

  async sendListMessage(listaId: number, payload: ListChatMessageRequest) {
    const { data } = await api.post<ListChatMessageResponse>(
      `/chat/lista/${listaId}/message`,
      payload,
      {
        timeout: LIST_CHAT_TIMEOUT_MS,
      }
    );

    return data;
  },

  async clearListMessages(listaId: number) {
    const { data } = await api.delete<{ message: string; deleted: number }>(
      `/chat/lista/${listaId}/messages`
    );

    return data;
  },
};
