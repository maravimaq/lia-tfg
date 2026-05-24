from sqlalchemy import Column, ForeignKey, Integer, Numeric, String
from sqlalchemy.orm import relationship

from app.db.session import Base


class HistorialProductoLista(Base):
    __tablename__ = "historial_productos_lista"

    id_historial_producto = Column(Integer, primary_key=True, index=True)

    historial_id = Column(
        Integer,
        ForeignKey("historial_listas.id_historial"),
        nullable=False
    )
    historial = relationship("HistorialListas")

    producto_id = Column(Integer, ForeignKey("productos.id_producto"), nullable=True)

    nombre_producto = Column(String, nullable=False)
    marca = Column(String, nullable=True)
    categoria = Column(String, nullable=True)
    supermercado = Column(String, nullable=False)
    unidad_medida = Column(String, nullable=True)

    precio_unitario = Column(Numeric(10, 2), nullable=False, default=0)
    cantidad = Column(Integer, nullable=False, default=1)
    precio_estimado = Column(Numeric(10, 2), nullable=False, default=0)