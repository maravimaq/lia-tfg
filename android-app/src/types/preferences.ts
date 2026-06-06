export type IdiomaPreferido = "es" | "en";
export type UnidadPesoPreferida = "kg" | "g" | "lb";
export type UnidadPrecioPreferida = "EUR" | "USD";

export type SupermercadoFavorito =
  | "Mercadona"
  | "DIA"
  | "Carrefour"
  | "ALDI"
  | "Alcampo";

export type PreferenciasResponse = {
  id_preferencia: number;
  usuario_id: number;
  idioma: IdiomaPreferido;
  modo_oscuro: boolean;
  notificaciones: boolean;
  unidad_peso: UnidadPesoPreferida;
  unidad_precio: UnidadPrecioPreferida;
  supermercado_favorito: SupermercadoFavorito | null;
};

export type PreferenciasUpdatePayload = {
  idioma: IdiomaPreferido;
  modo_oscuro: boolean;
  notificaciones: boolean;
  unidad_peso: UnidadPesoPreferida;
  unidad_precio: UnidadPrecioPreferida;
  supermercado_favorito?: SupermercadoFavorito | null;
};

export type PreferenciasFormValues = {
  idioma: IdiomaPreferido;
  modo_oscuro: boolean;
  notificaciones: boolean;
  unidad_peso: UnidadPesoPreferida;
  unidad_precio: UnidadPrecioPreferida;
  supermercado_favorito: SupermercadoFavorito | "";
};
