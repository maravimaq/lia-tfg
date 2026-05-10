from pydantic import BaseModel


class ProductoSearchFilters(BaseModel):
    nombre: str | None = None
    categoria: str | None = None
    supermercado: str | None = None
    marca: str | None = None
    orden_precio: str | None = None