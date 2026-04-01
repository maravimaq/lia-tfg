from sqlalchemy import Column, ForeignKey, Integer, String
from sqlalchemy.orm import relationship

from app.db.session import Base


class ConfiguracionBotExterno(Base):
    __tablename__ = "configuracion_bot_externo"

    id_configuracion = Column(Integer, primary_key=True, index=True)
    plataforma = Column(String, nullable=False, default="telegram")
    token = Column(String, nullable=True)
    estado = Column(String, nullable=False, default="inactivo")

    usuario_id = Column(Integer, ForeignKey("users.id_usuario"), unique=True, nullable=False)
    usuario = relationship("User", back_populates="configuracion_bot")