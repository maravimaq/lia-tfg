from pydantic import BaseModel, EmailStr
from typing import Optional


class LoginRequest(BaseModel):
    email: EmailStr
    contrasena: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class ExternalAuthRequest(BaseModel):
    id_token: str
    proveedor: str  # google / apple


class ExternalUserPayload(BaseModel):
    email: EmailStr
    nombre_completo: Optional[str] = None
    nombre_usuario: Optional[str] = None