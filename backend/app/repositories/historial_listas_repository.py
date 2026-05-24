from sqlalchemy.orm import Session

from app.models.historial_listas import HistorialListas


class HistorialListasRepository:

    @staticmethod
    def create(db: Session, historial: HistorialListas) -> HistorialListas:
        db.add(historial)
        db.commit()
        db.refresh(historial)
        return historial

    @staticmethod
    def get_by_id(db: Session, historial_id: int) -> HistorialListas | None:
        return db.query(HistorialListas).filter(
            HistorialListas.id_historial == historial_id
        ).first()

    @staticmethod
    def get_by_lista_id(db: Session, lista_id: int) -> HistorialListas | None:
        return db.query(HistorialListas).filter(
            HistorialListas.lista_id == lista_id
        ).first()

    @staticmethod
    def get_all_by_user_id(
        db: Session,
        user_id: int
    ) -> list[HistorialListas]:
        return db.query(HistorialListas).filter(
            HistorialListas.usuario_id == user_id
        ).order_by(HistorialListas.fecha.desc()).all()