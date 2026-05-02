from datetime import datetime

from sqlalchemy import Column, DateTime, Integer, Numeric, String

from app.db.session import Base


class Producto(Base):
    __tablename__ = "productos"

    id_producto = Column(Integer, primary_key=True, index=True)

    nombre = Column(String, nullable=False)
    marca = Column(String, nullable=True)
    categoria = Column(String, nullable=True)

    supermercado = Column(String, nullable=False)

    precio_unitario = Column(Numeric(10, 2), nullable=False, default=0)
    unidad_medida = Column(String, nullable=True)

    fecha_actualizacion = Column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
        onupdate=datetime.utcnow
    )