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

    rol_id = Column(Integer, ForeignKey("roles.id_rol"), nullable=False)
    rol = relationship("Role", back_populates="usuarios")