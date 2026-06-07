from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import relationship

from app.db.session import Base


class ExternalBotLinkCode(Base):
    __tablename__ = "external_bot_link_codes"

    id_codigo = Column(Integer, primary_key=True, index=True)
    codigo = Column(String(16), nullable=False, unique=True, index=True)
    plataforma = Column(String(32), nullable=False, default="telegram")
    usado = Column(Boolean, nullable=False, default=False)
    fecha_creacion = Column(DateTime, nullable=False, default=datetime.utcnow)
    fecha_expiracion = Column(DateTime, nullable=False)

    usuario_id = Column(Integer, ForeignKey("users.id_usuario"), nullable=False)
    usuario = relationship("User", back_populates="external_bot_link_codes")
