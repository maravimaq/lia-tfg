from pydantic import BaseModel, ConfigDict


class ProductoListaBase(BaseModel):
    nombre_producto: str
    cantidad: int = 1
    unidad_medida: str | None = None
    supermercado: str | None = None
    precio_estimado: float = 0


class ProductoListaCreate(ProductoListaBase):
    lista_id: int


class ProductoListaUpdate(BaseModel):
    nombre_producto: str | None = None
    cantidad: int | None = None
    unidad_medida: str | None = None
    supermercado: str | None = None
    precio_estimado: float | None = None


class ProductoListaResponse(ProductoListaBase):
    id_producto_lista: int
    lista_id: int

    model_config = ConfigDict(from_attributes=True)