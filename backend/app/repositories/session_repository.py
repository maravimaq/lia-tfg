from datetime import datetime

from sqlalchemy.orm import Session

from app.models.sesion_autenticacion import SesionAutenticacion


class SessionRepository:
    @staticmethod
    def create(db: Session, sesion: SesionAutenticacion) -> SesionAutenticacion:
        db.add(sesion)
        db.commit()
        db.refresh(sesion)
        return sesion

    @staticmethod
    def get_active_by_token(db: Session, token: str) -> SesionAutenticacion | None:
        return db.query(SesionAutenticacion).filter(
            SesionAutenticacion.token == token,
            SesionAutenticacion.estado == "activa",
        ).first()

    @staticmethod
    def get_active_by_user_id(db: Session, user_id: int) -> list[SesionAutenticacion]:
        return db.query(SesionAutenticacion).filter(
            SesionAutenticacion.usuario_id == user_id,
            SesionAutenticacion.estado == "activa",
        ).all()

    @staticmethod
    def close_session(db: Session, sesion: SesionAutenticacion) -> SesionAutenticacion:
        sesion.estado = "cerrada"
        sesion.fecha_fin = datetime.utcnow()
        db.add(sesion)
        db.commit()
        db.refresh(sesion)
        return sesion

    @staticmethod
    def revoke_all_user_sessions(db: Session, user_id: int) -> None:
        sesiones = db.query(SesionAutenticacion).filter(
            SesionAutenticacion.usuario_id == user_id,
            SesionAutenticacion.estado == "activa",
        ).all()

        for sesion in sesiones:
            sesion.estado = "revocada"
            sesion.fecha_fin = datetime.utcnow()
            db.add(sesion)

        db.commit()