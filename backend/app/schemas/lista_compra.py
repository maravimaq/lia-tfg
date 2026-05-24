from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict

from app.schemas.producto_lista import ProductoListaResponse


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
    total_estimado: Decimal
    usuario_id: int
    tipo_compartido: str | None = None

    model_config = ConfigDict(from_attributes=True)


class ListaCompraDetalleResponse(ListaCompraResponse):
    productos: list[ProductoListaResponse]