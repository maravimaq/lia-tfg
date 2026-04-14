export type UserResponse = {
  id_usuario: number;
  nombre_usuario: string;
  nombre_completo: string;
  email: string;
  telefono?: string | null;
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
};

export type ChangePasswordPayload = {
  contrasena_actual: string;
  nueva_contrasena: string;
};