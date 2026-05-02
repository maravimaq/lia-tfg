from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.models.seguimiento_usuario import SeguimientoUsuario
from app.models.solicitud_seguimiento import SolicitudSeguimiento


class FollowRepository:
    @staticmethod
    def get_follow(db: Session, seguidor_id: int, seguido_id: int) -> SeguimientoUsuario | None:
        return (
            db.query(SeguimientoUsuario)
            .filter(
                SeguimientoUsuario.seguidor_id == seguidor_id,
                SeguimientoUsuario.seguido_id == seguido_id,
            )
            .first()
        )

    @staticmethod
    def create_follow(db: Session, follow: SeguimientoUsuario) -> SeguimientoUsuario:
        db.add(follow)
        db.commit()
        db.refresh(follow)
        return follow

    @staticmethod
    def get_request_between(
        db: Session,
        user_a_id: int,
        user_b_id: int,
    ) -> SolicitudSeguimiento | None:
        return (
            db.query(SolicitudSeguimiento)
            .filter(
                or_(
                    (SolicitudSeguimiento.solicitante_id == user_a_id)
                    & (SolicitudSeguimiento.destinatario_id == user_b_id),
                    (SolicitudSeguimiento.solicitante_id == user_b_id)
                    & (SolicitudSeguimiento.destinatario_id == user_a_id),
                )
            )
            .first()
        )

    @staticmethod
    def get_request_by_id(db: Session, request_id: int) -> SolicitudSeguimiento | None:
        return (
            db.query(SolicitudSeguimiento)
            .filter(SolicitudSeguimiento.id_solicitud_seguimiento == request_id)
            .first()
        )

    @staticmethod
    def create_request(db: Session, request: SolicitudSeguimiento) -> SolicitudSeguimiento:
        db.add(request)
        db.commit()
        db.refresh(request)
        return request

    @staticmethod
    def save_request(db: Session, request: SolicitudSeguimiento) -> SolicitudSeguimiento:
        db.add(request)
        db.commit()
        db.refresh(request)
        return request

    @staticmethod
    def delete_request(db: Session, request: SolicitudSeguimiento) -> None:
        db.delete(request)
        db.commit()

    @staticmethod
    def get_incoming_pending_requests(db: Session, user_id: int) -> list[SolicitudSeguimiento]:
        return (
            db.query(SolicitudSeguimiento)
            .filter(
                SolicitudSeguimiento.destinatario_id == user_id,
                SolicitudSeguimiento.estado == "pendiente",
            )
            .order_by(SolicitudSeguimiento.fecha_solicitud.desc())
            .all()
        )
