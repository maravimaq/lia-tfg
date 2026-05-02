from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class UserBase(BaseModel):
    nombre_usuario: str
    nombre_completo: str
    email: EmailStr
    telefono: Optional[str] = None
    avatar_url: Optional[str] = None


class UserCreate(UserBase):
    contrasena: str = Field(
        ...,
        min_length=8,
        max_length=512,
        description="La contraseña debe tener entre 8 y 512 caracteres"
    )

class UserUpdate(BaseModel):
    nombre_usuario: Optional[str] = None
    nombre_completo: Optional[str] = None
    email: Optional[EmailStr] = None
    telefono: Optional[str] = None
    avatar_url: Optional[str] = None


class ChangePasswordRequest(BaseModel):
    contrasena_actual: str = Field(..., min_length=1, max_length=512)
    nueva_contrasena: str = Field(..., min_length=8, max_length=512)


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    token: str
    nueva_contrasena: str


class UserResponse(UserBase):
    id_usuario: int
    estado: str
    fecha_registro: datetime
    rol_id: int
    proveedor_auth: str

    model_config = ConfigDict(from_attributes=True)