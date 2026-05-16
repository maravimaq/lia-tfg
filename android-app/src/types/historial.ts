import { ListaCompra } from "./lista";

export type HistorialLista = {
  id_historial: number;
  fecha: string;
  estado: string;
  num_productos: number;
  total_gastado: string;
  lista_id: number;
  usuario_id: number;
};

export type HistorialProductoLista = {
  id_historial_producto: number;
  historial_id: number;
  producto_id: number | null;
  nombre_producto: string;
  marca: string | null;
  categoria: string | null;
  supermercado: string;
  unidad_medida: string | null;
  precio_unitario: string;
  cantidad: number;
  precio_estimado: string;
};

export type HistorialListaDetalle = HistorialLista & {
  productos: HistorialProductoLista[];
};

export type RepetirListaResponse = ListaCompra;
