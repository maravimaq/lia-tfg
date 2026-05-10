from sqlalchemy.orm import Session, joinedload

from app.models.solicitud_baja_usuario import SolicitudBajaUsuario


class AccountRequestRepository:
    @staticmethod
    def create(
        db: Session,
        solicitud: SolicitudBajaUsuario,
    ) -> SolicitudBajaUsuario:
        db.add(solicitud)
        db.commit()
        db.refresh(solicitud)
        return solicitud

    @staticmethod
    def get_pending_by_user_id(
        db: Session,
        user_id: int,
    ) -> SolicitudBajaUsuario | None:
        return db.query(SolicitudBajaUsuario).filter(
            SolicitudBajaUsuario.usuario_id == user_id,
            SolicitudBajaUsuario.estado == "pendiente",
        ).first()

    @staticmethod
    def get_pending_deletion_requests(db: Session) -> list[SolicitudBajaUsuario]:
        return (
            db.query(SolicitudBajaUsuario)
            .options(joinedload(SolicitudBajaUsuario.usuario))
            .filter(
                SolicitudBajaUsuario.tipo == "eliminacion",
                SolicitudBajaUsuario.estado == "pendiente",
            )
            .order_by(SolicitudBajaUsuario.fecha_solicitud.asc())
            .all()
        )