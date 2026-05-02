from decimal import Decimal
from pydantic import BaseModel, ConfigDict

from app.schemas.producto import ProductoResponse


class ProductoListaCreate(BaseModel):
    lista_id: int
    producto_id: int
    cantidad: int = 1


class ProductoListaUpdate(BaseModel):
    cantidad: int | None = None


class ProductoListaResponse(BaseModel):
    id_producto_lista: int
    lista_id: int
    producto_id: int
    cantidad: int
    precio_estimado: Decimal
    producto: ProductoResponse

    model_config = ConfigDict(from_attributes=True)