from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.lista_compra import ListaCompra


class ListaCompraRepository:

    @staticmethod
    def create(db: Session, lista: ListaCompra) -> ListaCompra:
        db.add(lista)
        db.commit()
        db.refresh(lista)
        return lista

    @staticmethod
    def get_by_id(db: Session, lista_id: int) -> ListaCompra | None:
        return db.query(ListaCompra).filter(ListaCompra.id_lista == lista_id).first()

    @staticmethod
    def get_all_by_user_id(db: Session, user_id: int) -> list[ListaCompra]:
        return (
            db.query(ListaCompra)
            .filter(ListaCompra.usuario_id == user_id)
            .order_by(ListaCompra.fecha_creacion.desc())
            .all()
        )

    @staticmethod
    def count_all(db: Session) -> int:
        return db.query(func.count(ListaCompra.id_lista)).scalar() or 0

    @staticmethod
    def get_latest_created(db: Session) -> ListaCompra | None:
        return db.query(ListaCompra).order_by(ListaCompra.fecha_creacion.desc()).first()