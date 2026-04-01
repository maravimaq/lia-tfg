from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict


class SessionResponse(BaseModel):
    id_sesion: int
    proveedor: str
    fecha_inicio: datetime
    fecha_fin: Optional[datetime] = None
    estado: str

    model_config = ConfigDict(from_attributes=True)