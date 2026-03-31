from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, Numeric, String
from sqlalchemy.orm import relationship

from app.db.session import Base


class ListaCompra(Base):
    __tablename__ = "listas_compra"

    id_lista = Column(Integer, primary_key=True, index=True)
    nombre_lista = Column(String, nullable=False)
    compartida = Column(Boolean, nullable=False, default=False)
    fecha_creacion = Column(DateTime, nullable=False, default=datetime.utcnow)
    fecha_modificacion = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    total_estimado = Column(Numeric(10, 2), nullable=False, default=0)

    usuario_id = Column(Integer, ForeignKey("users.id_usuario"), nullable=False)
    usuario = relationship("User")