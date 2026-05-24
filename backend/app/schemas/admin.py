from datetime import datetime
from typing import Optional

from pydantic import BaseModel, EmailStr, ConfigDict


class AdminUserListItem(BaseModel):
    id_usuario: int
    nombre_usuario: str
    nombre_completo: str
    email: EmailStr
    telefono: Optional[str] = None
    estado: str
    rol_id: int
    rol_nombre: str
    fecha_registro: datetime

    model_config = ConfigDict(from_attributes=True)


class AdminUsersPageResponse(BaseModel):
    items: list[AdminUserListItem]
    total: int
    page: int
    size: int
    total_pages: int


class AdminUserCreate(BaseModel):
    nombre_usuario: str
    nombre_completo: str
    email: EmailStr
    contrasena: str
    telefono: Optional[str] = None
    rol_nombre: str = "usuario"   # "usuario" o "administrador"
    estado: str = "activo"        # "activo" o "inactivo"


class AdminUserUpdate(BaseModel):
    nombre_usuario: Optional[str] = None
    nombre_completo: Optional[str] = None
    email: Optional[EmailStr] = None
    telefono: Optional[str] = None
    rol_nombre: Optional[str] = None
    estado: Optional[str] = None


class AdminDashboardLatestUser(BaseModel):
    id_usuario: int
    nombre_usuario: str
    email: EmailStr
    fecha_registro: datetime

    model_config = ConfigDict(from_attributes=True)


class AdminDashboardLatestList(BaseModel):
    id_lista: int
    nombre_lista: str
    fecha_creacion: datetime
    usuario_id: int

    model_config = ConfigDict(from_attributes=True)


class AdminPendingDeletionRequest(BaseModel):
    id_solicitud: int
    usuario_id: int
    nombre_usuario: str
    nombre_completo: str
    email: EmailStr
    fecha_solicitud: datetime
    motivo: Optional[str] = None


class AdminDashboardResponse(BaseModel):
    total_usuarios: int
    total_usuarios_activos: int
    total_usuarios_inactivos: int
    total_listas: int
    ultimo_usuario_registrado: Optional[AdminDashboardLatestUser] = None
    ultima_lista_creada: Optional[AdminDashboardLatestList] = None
    actividad_reciente: list[str] = []
    solicitudes_eliminacion_pendientes: list[AdminPendingDeletionRequest] = []


class AdminScrapingStoreStatus(BaseModel):
    supermercado: str
    estado: str
    fecha: str
    precios_detectados: int = 0
    productos_actualizados: int = 0
    warning: Optional[str] = None
    detalle_error: Optional[str] = None


class AdminScrapingOverviewResponse(BaseModel):
    ultima_ejecucion_fecha: str
    ultima_ejecucion_estado: str
    progreso_general: int
    en_curso: bool
    tiempo_restante_segundos: int
    detalle_error: Optional[str] = None
    fuentes: list[AdminScrapingStoreStatus]


class AdminScrapingActionResponse(BaseModel):
    message: str
    status: str