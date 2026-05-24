from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, Integer, Numeric, String
from sqlalchemy.orm import relationship

from app.db.session import Base


class HistorialListas(Base):
    __tablename__ = "historial_listas"

    id_historial = Column(Integer, primary_key=True, index=True)
    nombre_lista = Column(String(255), nullable=True)
    fecha = Column(DateTime, nullable=False, default=datetime.utcnow)
    estado = Column(String, nullable=False, default="finalizada")
    num_productos = Column(Integer, nullable=False, default=0)
    total_gastado = Column(Numeric(10, 2), nullable=False, default=0)

    lista_id = Column(Integer, ForeignKey("listas_compra.id_lista"), nullable=False)
    lista = relationship("ListaCompra")

    usuario_id = Column(Integer, ForeignKey("users.id_usuario"), nullable=False)
    usuario = relationship("User")