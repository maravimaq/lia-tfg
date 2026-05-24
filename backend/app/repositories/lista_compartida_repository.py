from sqlalchemy import exists
from sqlalchemy.orm import Session

from app.models.historial_listas import HistorialListas
from app.models.lista_compartida import ListaCompartida


class ListaCompartidaRepository:

    @staticmethod
    def create(
        db: Session,
        lista_compartida: ListaCompartida
    ) -> ListaCompartida:

        db.add(lista_compartida)
        db.commit()
        db.refresh(lista_compartida)

        return lista_compartida

    @staticmethod
    def get_by_lista_and_usuario(
        db: Session,
        lista_id: int,
        usuario_id: int
    ) -> ListaCompartida | None:

        return (
            db.query(ListaCompartida)
            .filter(
                ListaCompartida.lista_id == lista_id,
                ListaCompartida.usuario_id == usuario_id
            )
            .first()
        )

    @staticmethod
    def get_all_by_usuario(
        db: Session,
        usuario_id: int
    ) -> list[ListaCompartida]:
        lista_finalizada_exists = exists().where(
            HistorialListas.lista_id == ListaCompartida.lista_id
        )

        return (
            db.query(ListaCompartida)
            .filter(ListaCompartida.usuario_id == usuario_id)
            .filter(~lista_finalizada_exists)
            .all()
        )

    @staticmethod
    def delete(
        db: Session,
        lista_compartida: ListaCompartida
    ) -> None:

        db.delete(lista_compartida)
        db.commit()