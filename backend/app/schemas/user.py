from datetime import datetime
from pydantic import BaseModel, EmailStr, ConfigDict


class UserBase(BaseModel):
    nombre_usuario: str
    nombre_completo: str
    email: EmailStr
    telefono: str | None = None


class UserCreate(UserBase):
    contrasena: str


class UserResponse(UserBase):
    id_usuario: int
    estado: str
    fecha_registro: datetime
    rol_id: int

    model_config = ConfigDict(from_attributes=True)