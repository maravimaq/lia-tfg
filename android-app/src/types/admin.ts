export type AdminUserListItem = {
  id_usuario: number;
  nombre_usuario: string;
  nombre_completo: string;
  email: string;
  telefono?: string | null;
  estado: "activo" | "inactivo" | string;
  rol_id: number;
  rol_nombre: "usuario" | "administrador" | string;
  fecha_registro: string;
};

export type AdminUsersPageResponse = {
  items: AdminUserListItem[];
  total: number;
  page: number;
  size: number;
  total_pages: number;
};

export type AdminDashboardLatestUser = {
  id_usuario: number;
  nombre_usuario: string;
  email: string;
  fecha_registro: string;
};

export type AdminDashboardLatestList = {
  id_lista: number;
  nombre_lista: string;
  fecha_creacion: string;
  usuario_id: number;
};

export type AdminDashboardResponse = {
  total_usuarios: number;
  total_usuarios_activos: number;
  total_usuarios_inactivos: number;
  total_listas: number;
  ultimo_usuario_registrado?: AdminDashboardLatestUser | null;
  ultima_lista_creada?: AdminDashboardLatestList | null;
  actividad_reciente: string[];
};

export type AdminUserCreatePayload = {
  nombre_usuario: string;
  nombre_completo: string;
  email: string;
  contrasena: string;
  telefono?: string;
  rol_nombre?: "usuario" | "administrador";
  estado?: "activo" | "inactivo";
};

export type AdminUserUpdatePayload = {
  nombre_usuario?: string;
  nombre_completo?: string;
  email?: string;
  telefono?: string;
  rol_nombre?: "usuario" | "administrador";
  estado?: "activo" | "inactivo";
};

export type AdminScrapingStoreStatus = {
  supermercado: string;
  estado: "ok" | "error" | "en_proceso" | "en_cola" | "cancelado" | string;
  fecha: string;
  precios_detectados: number;
  productos_actualizados: number;
  warning?: string | null;
  detalle_error?: string | null;
};

export type AdminScrapingOverviewResponse = {
  ultima_ejecucion_fecha: string;
  ultima_ejecucion_estado: "ok" | "error" | "en_proceso" | "cancelado" | string;
  progreso_general: number;
  en_curso: boolean;
  tiempo_restante_segundos: number;
  detalle_error?: string | null;
  fuentes: AdminScrapingStoreStatus[];
};

export type AdminScrapingActionResponse = {
  message: string;
  status: string;
};