from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict


class AccountActionRequestCreate(BaseModel):
    tipo: str  # desactivacion / eliminacion
    motivo: Optional[str] = None


class AccountActionRequestResponse(BaseModel):
    id_solicitud: int
    tipo: str
    motivo: Optional[str] = None
    estado: str
    fecha_solicitud: datetime

    model_config = ConfigDict(from_attributes=True)