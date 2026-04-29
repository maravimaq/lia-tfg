export type UserResponse = {
  id_usuario: number;
  nombre_usuario: string;
  nombre_completo: string;
  email: string;
  telefono?: string | null;
  avatar_url?: string | null;
  estado: string;
  fecha_registro: string;
  rol_id: number;
  proveedor_auth: string;
};

export type UserUpdatePayload = {
  nombre_usuario?: string;
  nombre_completo?: string;
  email?: string;
  telefono?: string;
  avatar_url?: string;
};

export type ChangePasswordPayload = {
  contrasena_actual: string;
  nueva_contrasena: string;
};

export type BotConfigResponse = {
  id_configuracion: number;
  plataforma: string;
  token?: string | null;
  estado: string;
  usuario_id: number;
};

export type BotConfigUpdatePayload = {
  plataforma: string;
  token?: string | null;
  estado: string;
};

export type SessionResponse = {
  id_sesion: number;
  proveedor: string;
  fecha_inicio: string;
  fecha_fin?: string | null;
  estado: string;
};

export type AccountActionRequestPayload = {
  tipo: "desactivacion" | "eliminacion";
  motivo?: string | null;
};

export type AccountActionRequestResponse = {
  id_solicitud: number;
  tipo: string;
  motivo?: string | null;
  estado: string;
  fecha_solicitud: string;
};

export type DiscoverUserResponse = {
  id_usuario: number;
  nombre_usuario: string;
  nombre_completo: string;
  email: string;
  avatar_url?: string | null;
  follow_status: "none" | "pending" | "followed";
};

export type FollowRequestResponse = {
  id_solicitud_seguimiento: number;
  solicitante_id: number;
  destinatario_id: number;
  estado: string;
  fecha_solicitud: string;
};

export type IncomingFollowRequestItem = {
  id_solicitud_seguimiento: number;
  estado: string;
  fecha_solicitud: string;
  solicitante: DiscoverUserResponse;
};