export type MoneyValue = number | string;

export interface HistorialLista {
  id_historial: number;
  fecha: string;
  lista_id: number;
  usuario_id: number;
  estado: string;
  num_productos: number;
  total_gastado: MoneyValue;
}

export interface HistorialProductoLista {
  id_historial_producto: number;
  historial_id: number;

  producto_id?: number | null;
  nombre_producto: string;
  marca?: string | null;
  categoria?: string | null;
  supermercado: string;
  unidad_medida?: string | null;

  precio_unitario: MoneyValue;
  cantidad: number;
  precio_estimado: MoneyValue;
}

export interface HistorialListaDetalle extends HistorialLista {
  productos: HistorialProductoLista[];
}