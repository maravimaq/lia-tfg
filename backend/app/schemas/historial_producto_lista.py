from decimal import Decimal
from pydantic import BaseModel, ConfigDict


class HistorialProductoListaResponse(BaseModel):
    id_historial_producto: int
    historial_id: int

    producto_id: int | None = None
    nombre_producto: str
    marca: str | None = None
    categoria: str | None = None
    supermercado: str
    unidad_medida: str | None = None
    imagen_url: str | None = None

    precio_unitario: Decimal
    cantidad: int
    precio_estimado: Decimal

    model_config = ConfigDict(from_attributes=True)