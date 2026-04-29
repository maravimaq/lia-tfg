from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict


class DiscoverUserResponse(BaseModel):
    id_usuario: int
    nombre_usuario: str
    nombre_completo: str
    email: str
    avatar_url: Optional[str] = None
    follow_status: str  # none | pending | followed


class FollowRequestResponse(BaseModel):
    id_solicitud_seguimiento: int
    solicitante_id: int
    destinatario_id: int
    estado: str
    fecha_solicitud: datetime

    model_config = ConfigDict(from_attributes=True)


class FollowRequestIncomingItem(BaseModel):
    id_solicitud_seguimiento: int
    estado: str
    fecha_solicitud: datetime
    solicitante: DiscoverUserResponse


class FollowRequestAction(BaseModel):
    accion: str  # aceptar | rechazar
