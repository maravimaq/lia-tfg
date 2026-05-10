from datetime import datetime

from pydantic import BaseModel, ConfigDict


class CompartirListaRequest(BaseModel):
    email_usuario: str


class ListaCompartidaResponse(BaseModel):
    id_lista_compartida: int
    lista_id: int
    usuario_id: int
    fecha_compartida: datetime

    model_config = ConfigDict(from_attributes=True)