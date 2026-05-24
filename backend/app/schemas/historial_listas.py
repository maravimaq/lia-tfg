from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict

from app.schemas.historial_producto_lista import HistorialProductoListaResponse


class HistorialListasBase(BaseModel):
    nombre_lista: str | None = None
    estado: str = "finalizada"
    num_productos: int
    total_gastado: Decimal


class HistorialListasCreate(BaseModel):
    lista_id: int


class HistorialListasResponse(HistorialListasBase):
    id_historial: int
    fecha: datetime
    lista_id: int
    usuario_id: int

    model_config = ConfigDict(from_attributes=True)


class HistorialListasDetalleResponse(HistorialListasResponse):
    productos: list[HistorialProductoListaResponse]