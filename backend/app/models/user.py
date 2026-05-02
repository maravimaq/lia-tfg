from datetime import datetime

from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship

from app.db.session import Base


class User(Base):
    __tablename__ = "users"

    id_usuario = Column("id_usuario", Integer, primary_key=True, index=True)
    nombre_usuario = Column(String, nullable=False, unique=True, index=True)
    nombre_completo = Column(String, nullable=False)
    email = Column(String, nullable=False, unique=True, index=True)
    contrasena = Column(String, nullable=False)
    telefono = Column(String, nullable=True)
    estado = Column(String, nullable=False, default="activo")
    fecha_registro = Column(DateTime, nullable=False, default=datetime.utcnow)
    proveedor_auth = Column(String, nullable=False, default="local")
    avatar_url = Column(String, nullable=True)

    rol_id = Column(Integer, ForeignKey("roles.id_rol"), nullable=False)
    rol = relationship("Role", back_populates="usuarios")

    preferencias = relationship(
        "PreferenciasUsuario",
        back_populates="usuario",
        uselist=False,
        cascade="all, delete-orphan",
    )

    configuracion_bot = relationship(
        "ConfiguracionBotExterno",
        back_populates="usuario",
        uselist=False,
        cascade="all, delete-orphan",
    )

    sesiones = relationship(
        "SesionAutenticacion",
        back_populates="usuario",
        cascade="all, delete-orphan",
    )

    solicitudes_baja = relationship(
        "SolicitudBajaUsuario",
        back_populates="usuario",
        cascade="all, delete-orphan",
    )
    siguiendo = relationship(
        "SeguimientoUsuario",
        foreign_keys="SeguimientoUsuario.seguidor_id",
        back_populates="seguidor",
        cascade="all, delete-orphan",
    )

    seguidores = relationship(
        "SeguimientoUsuario",
        foreign_keys="SeguimientoUsuario.seguido_id",
        back_populates="seguido",
        cascade="all, delete-orphan",
    )
    solicitudes_enviadas = relationship(
        "SolicitudSeguimiento",
        foreign_keys="SolicitudSeguimiento.solicitante_id",
        back_populates="solicitante",
        cascade="all, delete-orphan",
    )

    solicitudes_recibidas = relationship(
        "SolicitudSeguimiento",
        foreign_keys="SolicitudSeguimiento.destinatario_id",
        back_populates="destinatario",
        cascade="all, delete-orphan",
    )