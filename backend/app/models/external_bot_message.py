from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship

from app.db.session import Base


class ExternalBotMessage(Base):
    __tablename__ = "external_bot_messages"

    id_mensaje_bot = Column(Integer, primary_key=True, index=True)
    direccion = Column(String(16), nullable=False)  # incoming | outgoing
    texto = Column(Text, nullable=False)
    payload = Column(JSONB, nullable=True)
    fecha_creacion = Column(DateTime, nullable=False, default=datetime.utcnow)

    sesion_id = Column(Integer, ForeignKey("external_bot_sessions.id_sesion_bot"), nullable=False)
    sesion = relationship("ExternalBotSession", back_populates="mensajes")
