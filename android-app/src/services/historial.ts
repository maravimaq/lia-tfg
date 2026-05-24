import { api } from "./api";

import { ListaCompra } from "@/src/types/lista";
import {
  HistorialLista,
  HistorialListaDetalle,
} from "@/src/types/historial";

export const historialService = {
  async finalizarLista(listaId: number) {
    const { data } = await api.post<HistorialLista>(
      `/historial/listas/${listaId}/finalizar`
    );

    return data;
  },

  async getMiHistorial() {
    const { data } = await api.get<HistorialLista[]>("/historial");
    return data;
  },

  async getById(historialId: number) {
    const { data } = await api.get<HistorialLista>(
      `/historial/${historialId}`
    );

    return data;
  },

  async getDetalle(historialId: number) {
    const { data } = await api.get<HistorialListaDetalle>(
      `/historial/${historialId}/detalle`
    );

    return data;
  },

  async repetirLista(historialId: number) {
    const { data } = await api.post<ListaCompra>(
      `/historial/${historialId}/repetir`
    );

    return data;
  },
};