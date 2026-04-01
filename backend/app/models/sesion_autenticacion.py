from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import relationship

from app.db.session import Base


class SesionAutenticacion(Base):
    __tablename__ = "sesiones_autenticacion"

    id_sesion = Column(Integer, primary_key=True, index=True)
    proveedor = Column(String, nullable=False, default="local")  # local / google / apple
    token = Column(String, nullable=False, unique=True)
    fecha_inicio = Column(DateTime, nullable=False, default=datetime.utcnow)
    fecha_fin = Column(DateTime, nullable=True)
    estado = Column(String, nullable=False, default="activa")  # activa / cerrada / revocada

    usuario_id = Column(Integer, ForeignKey("users.id_usuario"), nullable=False)
    usuario = relationship("User", back_populates="sesiones")