from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict


# -----------------------
# BASE
# -----------------------
class ProductoBase(BaseModel):
    nombre: str
    marca: str | None = None
    categoria: str | None = None
    supermercado: str
    precio_unitario: Decimal
    unidad_medida: str | None = None
    formato: str | None = None
    imagen_url: str | None = None


# -----------------------
# CREATE
# -----------------------
class ProductoCreate(ProductoBase):
    pass


# -----------------------
# UPDATE
# -----------------------
class ProductoUpdate(BaseModel):
    nombre: str | None = None
    marca: str | None = None
    categoria: str | None = None
    supermercado: str | None = None
    precio_unitario: Decimal | None = None
    unidad_medida: str | None = None
    formato: str | None = None
    imagen_url: str | None = None


# -----------------------
# RESPONSE
# -----------------------
class ProductoResponse(ProductoBase):
    id_producto: int
    fecha_actualizacion: datetime

    model_config = ConfigDict(from_attributes=True)