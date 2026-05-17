import { Producto } from "./producto";

export type TipoCompartido = "edicion" | "visualizacion";

export type ListaCompra = {
  id_lista: number;
  nombre_lista: string;
  compartida: boolean;
  fecha_creacion: string;
  fecha_modificacion: string;
  total_estimado: string;
  usuario_id: number;

  /**
   * null/undefined -> lista propia
   * "edicion" -> lista compartida con permisos de edición
   * "visualizacion" -> lista compartida solo lectura
   */
  tipo_compartido?: TipoCompartido | null;
};

export type ListaCompraCreate = {
  nombre_lista: string;
  compartida?: boolean;
};

export type ListaCompraUpdate = {
  nombre_lista?: string;
  compartida?: boolean;
};

export type ProductoLista = {
  id_producto_lista: number;
  lista_id: number;
  producto_id: number;
  cantidad: number;
  precio_estimado: string;
  producto: Producto;
};

export type ProductoListaCreate = {
  lista_id: number;
  producto_id: number;
  cantidad: number;
};

export type ProductoListaUpdate = {
  cantidad?: number;
};

export type ListaCompraDetalle = ListaCompra & {
  productos: ProductoLista[];
};

export interface ListaCompartida {
  id_lista_compartida: number;
  lista_id: number;
  usuario_id: number;
  tipo_compartido: TipoCompartido;
  fecha_compartida?: string;
  fecha_comparticion?: string;
  lista?: ListaCompra;
}