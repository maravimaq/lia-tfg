from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship

from app.db.session import Base


class ExternalBotSession(Base):
    __tablename__ = "external_bot_sessions"
    __table_args__ = (
        UniqueConstraint("plataforma", "external_user_id", name="uq_external_bot_session_platform_user"),
    )

    id_sesion_bot = Column(Integer, primary_key=True, index=True)
    plataforma = Column(String(32), nullable=False, default="telegram")
    external_user_id = Column(String(128), nullable=False, index=True)
    activo = Column(Boolean, nullable=False, default=True)

    estado_conversacion = Column(String(64), nullable=False, default="idle")
    datos_temporales = Column(JSONB, nullable=False, default=dict)

    fecha_creacion = Column(DateTime, nullable=False, default=datetime.utcnow)
    fecha_actualizacion = Column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
    )

    usuario_id = Column(Integer, ForeignKey("users.id_usuario"), nullable=False)
    usuario = relationship("User", back_populates="external_bot_sessions")

    mensajes = relationship(
        "ExternalBotMessage",
        back_populates="sesion",
        cascade="all, delete-orphan",
    )
