from sqlalchemy import Column, ForeignKey, Integer, Numeric, String
from sqlalchemy.orm import relationship

from app.db.session import Base


class ProductoLista(Base):
    __tablename__ = "productos_lista"

    id_producto_lista = Column(Integer, primary_key=True, index=True)
    nombre_producto = Column(String, nullable=False)
    cantidad = Column(Integer, nullable=False, default=1)
    unidad_medida = Column(String, nullable=True)
    supermercado = Column(String, nullable=True)
    precio_estimado = Column(Numeric(10, 2), nullable=False, default=0)

    lista_id = Column(Integer, ForeignKey("listas_compra.id_lista"), nullable=False)
    lista = relationship("ListaCompra")