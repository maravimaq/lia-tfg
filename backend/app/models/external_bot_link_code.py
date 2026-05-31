from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import relationship

from app.db.session import Base


class ExternalBotLinkCode(Base):
    __tablename__ = "external_bot_link_codes"

    id_external_bot_link_code = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id_usuario"), nullable=False, index=True)
    channel = Column(String, nullable=False, default="TELEGRAM", index=True)
    code = Column(String, nullable=False, index=True)
    estado = Column(String, nullable=False, default="pendiente", index=True)
    external_chat_id = Column(String, nullable=True, index=True)
    fecha_creacion = Column(DateTime, nullable=False, default=datetime.utcnow)
    expires_at = Column(DateTime, nullable=False)
    used_at = Column(DateTime, nullable=True)

    usuario = relationship("User")
