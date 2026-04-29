from datetime import datetime

from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship

from app.db.session import Base


class SolicitudSeguimiento(Base):
    __tablename__ = "solicitudes_seguimiento"
    __table_args__ = (
        UniqueConstraint("solicitante_id", "destinatario_id", name="uq_solicitud_seguimiento"),
    )

    id_solicitud_seguimiento = Column(Integer, primary_key=True, index=True)
    solicitante_id = Column(Integer, ForeignKey("users.id_usuario"), nullable=False)
    destinatario_id = Column(Integer, ForeignKey("users.id_usuario"), nullable=False)
    estado = Column(String, nullable=False, default="pendiente")
    fecha_solicitud = Column(DateTime, nullable=False, default=datetime.utcnow)

    solicitante = relationship("User", foreign_keys=[solicitante_id], back_populates="solicitudes_enviadas")
    destinatario = relationship("User", foreign_keys=[destinatario_id], back_populates="solicitudes_recibidas")
