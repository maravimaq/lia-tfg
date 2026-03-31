from sqlalchemy.orm import Session

from app.models.producto_lista import ProductoLista


class ProductoListaRepository:

    @staticmethod
    def create(db: Session, producto: ProductoLista) -> ProductoLista:
        db.add(producto)
        db.commit()
        db.refresh(producto)
        return producto

    @staticmethod
    def get_by_id(db: Session, producto_id: int) -> ProductoLista | None:
        return db.query(ProductoLista).filter(
            ProductoLista.id_producto_lista == producto_id
        ).first()

    @staticmethod
    def get_by_lista_id(db: Session, lista_id: int) -> list[ProductoLista]:
        return db.query(ProductoLista).filter(
            ProductoLista.lista_id == lista_id
        ).all()