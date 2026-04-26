from datetime import datetime
from pydantic import BaseModel, ConfigDict


class ListaCompraBase(BaseModel):
    nombre_lista: str
    compartida: bool = False


class ListaCompraCreate(ListaCompraBase):
    pass

class ListaCompraUpdate(BaseModel):
    nombre_lista: str | None = None
    compartida: bool | None = None

class ListaCompraResponse(ListaCompraBase):
    id_lista: int
    fecha_creacion: datetime
    fecha_modificacion: datetime
    total_estimado: float
    usuario_id: int

    model_config = ConfigDict(from_attributes=True)