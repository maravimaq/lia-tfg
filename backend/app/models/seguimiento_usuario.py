from datetime import datetime

from sqlalchemy import Column, Integer, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship

from app.db.session import Base


class SeguimientoUsuario(Base):
    __tablename__ = "seguimientos_usuario"
    __table_args__ = (
        UniqueConstraint("seguidor_id", "seguido_id", name="uq_seguidor_seguido"),
    )

    id_seguimiento = Column(Integer, primary_key=True, index=True)
    seguidor_id = Column(Integer, ForeignKey("users.id_usuario"), nullable=False)
    seguido_id = Column(Integer, ForeignKey("users.id_usuario"), nullable=False)
    fecha_seguimiento = Column(DateTime, nullable=False, default=datetime.utcnow)

    seguidor = relationship("User", foreign_keys=[seguidor_id], back_populates="siguiendo")
    seguido = relationship("User", foreign_keys=[seguido_id], back_populates="seguidores")
