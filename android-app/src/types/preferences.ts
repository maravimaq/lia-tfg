export type PreferenciasResponse = {
  id_preferencia: number;
  usuario_id: number;
  idioma: string;
  modo_oscuro: boolean;
  notificaciones: boolean;
  unidad_peso: string;
  unidad_precio: string;
  supermercado_favorito?: string | null;
};

export type PreferenciasUpdatePayload = {
  idioma: string;
  modo_oscuro: boolean;
  notificaciones: boolean;
  unidad_peso: string;
  unidad_precio: string;
  supermercado_favorito?: string | null;
};