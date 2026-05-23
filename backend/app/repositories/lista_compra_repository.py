from sqlalchemy import exists, func
from sqlalchemy.orm import Session

from app.models.historial_listas import HistorialListas
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
        lista_finalizada_exists = exists().where(
            HistorialListas.lista_id == ListaCompra.id_lista
        )

        return (
            db.query(ListaCompra)
            .filter(ListaCompra.usuario_id == user_id)
            .filter(~lista_finalizada_exists)
            .order_by(ListaCompra.fecha_creacion.desc())
            .all()
        )

    @staticmethod
    def save(db: Session, lista: ListaCompra) -> ListaCompra:
        db.commit()
        db.refresh(lista)
        return lista

    @staticmethod
    def delete(db: Session, lista: ListaCompra) -> None:
        db.delete(lista)
        db.commit()

    @staticmethod
    def count_all(db: Session) -> int:
        return db.query(func.count(ListaCompra.id_lista)).scalar() or 0

    @staticmethod
    def get_latest_created(db: Session) -> ListaCompra | None:
        return db.query(ListaCompra).order_by(ListaCompra.fecha_creacion.desc()).first()