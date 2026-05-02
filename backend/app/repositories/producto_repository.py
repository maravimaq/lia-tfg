from sqlalchemy.orm import Session

from app.models.producto import Producto


class ProductoRepository:

    @staticmethod
    def create(db: Session, producto: Producto) -> Producto:
        db.add(producto)
        db.commit()
        db.refresh(producto)
        return producto

    @staticmethod
    def get_by_id(db: Session, producto_id: int) -> Producto | None:
        return db.query(Producto).filter(
            Producto.id_producto == producto_id
        ).first()

    @staticmethod
    def get_all(db: Session) -> list[Producto]:
        return db.query(Producto).all()

    @staticmethod
    def update(db: Session, producto: Producto) -> Producto:
        db.commit()
        db.refresh(producto)
        return producto

    @staticmethod
    def delete(db: Session, producto: Producto) -> None:
        db.delete(producto)
        db.commit()