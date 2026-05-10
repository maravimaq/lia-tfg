from sqlalchemy import Column, ForeignKey, Integer, Numeric
from sqlalchemy.orm import relationship

from app.db.session import Base


class ProductoLista(Base):
    __tablename__ = "productos_lista"

    id_producto_lista = Column(Integer, primary_key=True, index=True)

    cantidad = Column(Integer, nullable=False, default=1)
    precio_estimado = Column(Numeric(10, 2), nullable=False, default=0)

    lista_id = Column(Integer, ForeignKey("listas_compra.id_lista"), nullable=False)
    lista = relationship("ListaCompra")

    producto_id = Column(Integer, ForeignKey("productos.id_producto"), nullable=False)
    producto = relationship("Producto")