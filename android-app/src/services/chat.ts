import { api } from "./api";
import {
  ListChatMessageRequest,
  ListChatMessageResponse,
} from "@/src/types/chat";

const LIST_CHAT_TIMEOUT_MS = 180000;

export const chatService = {
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
};
