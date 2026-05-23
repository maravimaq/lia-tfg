import { api } from "./api";
import {
  Producto,
  ProductoCreate,
  ProductoSearchParams,
  ProductoUpdate,
} from "@/src/types/producto";

export const productosService = {
  async getAll() {
    const { data } = await api.get<Producto[]>("/productos");
    return data;
  },

  async getById(productoId: number) {
    const { data } = await api.get<Producto>(`/productos/${productoId}`);
    return data;
  },

  async create(payload: ProductoCreate) {
    const { data } = await api.post<Producto>("/productos", payload);
    return data;
  },

  async update(productoId: number, payload: ProductoUpdate) {
    const { data } = await api.put<Producto>(`/productos/${productoId}`, payload);
    return data;
  },

  async delete(productoId: number) {
    const { data } = await api.delete(`/productos/${productoId}`);
    return data;
  },

  async search(params: ProductoSearchParams) {
    const { data } = await api.get<Producto[]>("/productos/search", {
      params,
    });
    return data;
  },

  async comparar(nombre: string) {
    const { data } = await api.get<Producto[]>("/productos/comparar", {
      params: { nombre },
    });
    return data;
  },
};