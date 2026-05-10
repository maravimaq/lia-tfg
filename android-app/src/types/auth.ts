export type LoginPayload = {
  email: string;
  contrasena: string;
};

export type RegisterPayload = {
  nombre_usuario: string;
  nombre_completo: string;
  email: string;
  telefono?: string;
  contrasena: string;
};

export type ForgotPasswordPayload = {
  email: string;
};

export type ResetPasswordPayload = {
  token: string;
  nueva_contrasena: string;
};

export type ForgotPasswordResponse = {
  message: string;
};

export type TokenResponse = {
  access_token: string;
  token_type: string;
};