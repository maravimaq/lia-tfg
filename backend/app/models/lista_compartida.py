from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, Integer, UniqueConstraint
from sqlalchemy.orm import relationship

from app.db.session import Base


class ListaCompartida(Base):
    __tablename__ = "listas_compartidas"

    id_lista_compartida = Column(Integer, primary_key=True, index=True)

    lista_id = Column(Integer, ForeignKey("listas_compra.id_lista"), nullable=False)
    usuario_id = Column(Integer, ForeignKey("users.id_usuario"), nullable=False)

    fecha_compartida = Column(DateTime, nullable=False, default=datetime.utcnow)

    lista = relationship("ListaCompra")
    usuario = relationship("User")

    __table_args__ = (
        UniqueConstraint("lista_id", "usuario_id", name="uq_lista_usuario_compartida"),
    )