export type ListChatIntent =
  | "analizar_lista"
  | "comparar_lista_supermercados"
  | "recomendar_cantidad"
  | "sugerir_ahorro"
  | "sugerir_sustituciones"
  | "detectar_excesos"
  | "pregunta_general_lista"
  | "fuera_de_alcance";

export type ListChatSuggestionType =
  | "info"
  | "warning"
  | "saving"
  | "quantity"
  | "substitution";

export type ListChatSuggestion = {
  type: ListChatSuggestionType;
  title: string;
  description: string;
};

export type ListChatMessageRequest = {
  message: string;
};

export type ListChatContextSummary = {
  lista_id?: number;
  nombre_lista?: string;
  total_estimado?: string;
  num_productos?: number;
  confidence?: number;
  provider?: string;
  [key: string]: unknown;
};

export type ListChatMessageResponse = {
  reply: string;
  intent: ListChatIntent;
  suggestions: ListChatSuggestion[];
  context_summary: ListChatContextSummary;
};

export type ListChatStoredMessage = {
  id_chat_message: number;
  lista_id: number;
  usuario_id: number;
  role: "user" | "assistant";
  content: string;
  intent?: ListChatIntent | null;
  suggestions: ListChatSuggestion[];
  context_summary: ListChatContextSummary;
  fecha_creacion: string;
};
