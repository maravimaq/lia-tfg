from datetime import datetime
from enum import Enum

from pydantic import BaseModel, ConfigDict

from app.schemas.lista_compra import ListaCompraResponse


class TipoCompartido(str, Enum):
    EDICION = "edicion"
    VISUALIZACION = "visualizacion"


class CompartirListaRequest(BaseModel):
    email_usuario: str
    tipo_compartido: TipoCompartido = TipoCompartido.EDICION


class ListaCompartidaResponse(BaseModel):
    id_lista_compartida: int
    lista_id: int
    usuario_id: int
    tipo_compartido: TipoCompartido
    fecha_compartida: datetime

    model_config = ConfigDict(from_attributes=True)


class ListaCompartidaConListaResponse(ListaCompartidaResponse):
    lista: ListaCompraResponse