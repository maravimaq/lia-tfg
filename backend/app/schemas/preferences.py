from typing import Optional

from pydantic import BaseModel, ConfigDict


class PreferenciasBase(BaseModel):
    idioma: str = "es"
    modo_oscuro: bool = False
    notificaciones: bool = True
    unidad_peso: str = "kg"
    unidad_precio: str = "EUR"
    supermercado_favorito: Optional[str] = None


class PreferenciasUpdate(PreferenciasBase):
    pass


class PreferenciasResponse(PreferenciasBase):
    id_preferencia: int
    usuario_id: int

    model_config = ConfigDict(from_attributes=True)