from typing import Optional

from pydantic import BaseModel, ConfigDict


class BotConfigUpdate(BaseModel):
    plataforma: str = "telegram"
    token: Optional[str] = None
    estado: str = "inactivo"


class BotConfigResponse(BaseModel):
    id_configuracion: int
    plataforma: str
    token: Optional[str] = None
    estado: str
    usuario_id: int

    model_config = ConfigDict(from_attributes=True)