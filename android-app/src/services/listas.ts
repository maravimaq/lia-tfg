import { api } from "./api";
import {
  ListaCompra,
  ListaCompraCreate,
  ListaCompraDetalle,
  ListaCompraUpdate,
  ListaCompartida,
  ProductoLista,
  ProductoListaCreate,
  ProductoListaUpdate,
} from "@/src/types/lista";

export const listasService = {
  async getMisListas() {
    const { data } = await api.get<ListaCompra[]>("/listas");
    return data;
  },

  async getDetalle(listaId: number) {
    const { data } = await api.get<ListaCompraDetalle>(`/listas/${listaId}`);
    return data;
  },

  async create(payload: ListaCompraCreate) {
    const { data } = await api.post<ListaCompra>("/listas", payload);
    return data;
  },

  async update(listaId: number, payload: ListaCompraUpdate) {
    const { data } = await api.put<ListaCompra>(`/listas/${listaId}`, payload);
    return data;
  },

  async delete(listaId: number) {
    const { data } = await api.delete<{ message: string }>(`/listas/${listaId}`);
    return data;
  },

  async getProductosByLista(listaId: number) {
    const { data } = await api.get<ProductoLista[]>(
      `/productos-lista/lista/${listaId}`
    );
    return data;
  },

  async addProducto(payload: ProductoListaCreate) {
    const { data } = await api.post<ProductoLista>("/productos-lista", payload);
    return data;
  },

  async updateProducto(productoListaId: number, payload: ProductoListaUpdate) {
    const { data } = await api.put<ProductoLista>(
      `/productos-lista/${productoListaId}`,
      payload
    );
    return data;
  },

  async deleteProducto(productoListaId: number) {
    const { data } = await api.delete<{ message: string }>(
      `/productos-lista/${productoListaId}`
    );
    return data;
  },

  async compartir(listaId: number, emailUsuario: string) {
    const { data } = await api.post<ListaCompartida>(`/listas/${listaId}/compartir`, {
      email_usuario: emailUsuario,
    });
    return data;
  },

  async getCompartidas() {
    const { data } = await api.get<ListaCompartida[]>("/listas/compartidas");
    return data;
  },

  async eliminarComparticion(listaId: number, usuarioId: number) {
    const { data } = await api.delete<{ message: string }>(
      `/listas/${listaId}/compartir/${usuarioId}`
    );
    return data;
  },
};
