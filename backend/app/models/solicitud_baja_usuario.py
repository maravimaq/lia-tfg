from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from app.db.session import Base


class SolicitudBajaUsuario(Base):
    __tablename__ = "solicitudes_baja_usuario"

    id_solicitud = Column(Integer, primary_key=True, index=True)
    tipo = Column(String, nullable=False)  # desactivacion / eliminacion
    motivo = Column(Text, nullable=True)
    estado = Column(String, nullable=False, default="pendiente")  # pendiente / aprobada / rechazada
    fecha_solicitud = Column(DateTime, nullable=False, default=datetime.utcnow)
    fecha_resolucion = Column(DateTime, nullable=True)

    usuario_id = Column(Integer, ForeignKey("users.id_usuario"), nullable=False)
    usuario = relationship("User", back_populates="solicitudes_baja")