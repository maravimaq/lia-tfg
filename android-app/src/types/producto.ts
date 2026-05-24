export type Producto = {
  id_producto: number;
  nombre: string;
  marca: string | null;
  categoria: string | null;
  supermercado: string;
  precio_unitario: string;
  unidad_medida: string | null;
  fecha_actualizacion: string;
};

export type ProductoCreate = {
  nombre: string;
  marca?: string | null;
  categoria?: string | null;
  supermercado: string;
  precio_unitario: number;
  unidad_medida?: string | null;
};

export type ProductoUpdate = Partial<ProductoCreate>;

export type ProductoSearchParams = {
  nombre?: string;
  categoria?: string;
  supermercado?: string;
  marca?: string;
  orden_precio?: "asc" | "desc";
};