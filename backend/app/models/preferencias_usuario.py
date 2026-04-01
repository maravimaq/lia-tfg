from sqlalchemy import Boolean, Column, ForeignKey, Integer, String
from sqlalchemy.orm import relationship

from app.db.session import Base


class PreferenciasUsuario(Base):
    __tablename__ = "preferencias_usuario"

    id_preferencia = Column(Integer, primary_key=True, index=True)
    idioma = Column(String, nullable=False, default="es")
    modo_oscuro = Column(Boolean, nullable=False, default=False)
    notificaciones = Column(Boolean, nullable=False, default=True)
    unidad_peso = Column(String, nullable=False, default="kg")
    unidad_precio = Column(String, nullable=False, default="EUR")
    supermercado_favorito = Column(String, nullable=True)

    usuario_id = Column(Integer, ForeignKey("users.id_usuario"), unique=True, nullable=False)
    usuario = relationship("User", back_populates="preferencias")