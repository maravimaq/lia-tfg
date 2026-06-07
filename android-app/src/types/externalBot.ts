export type ExternalBotLinkCodeResponse = {
  codigo: string;
  plataforma: string;
  fecha_expiracion: string;
  instrucciones: string;
};

export type ExternalBotBindingStatusResponse = {
  plataforma: string;
  vinculado: boolean;
  external_user_id?: string | null;
  estado_conversacion?: string | null;
  fecha_vinculacion?: string | null;
};

export type ExternalBotMessageResponse = {
  id_mensaje_bot: number;
  direccion: "incoming" | "outgoing" | string;
  texto: string;
  payload?: Record<string, unknown> | null;
  fecha_creacion: string;
};

export type TelegramBotInfoResponse = {
  configured: boolean;
  id?: number | null;
  username?: string | null;
  first_name?: string | null;
  can_join_groups?: boolean | null;
  can_read_all_group_messages?: boolean | null;
  supports_inline_queries?: boolean | null;
};
