from sqlalchemy.orm import Session

from app.models.external_bot_session import ExternalBotSession


class ExternalBotSessionRepository:
    @staticmethod
    def get_by_external_user(
        db: Session,
        plataforma: str,
        external_user_id: str,
    ) -> ExternalBotSession | None:
        return (
            db.query(ExternalBotSession)
            .filter(
                ExternalBotSession.plataforma == plataforma,
                ExternalBotSession.external_user_id == str(external_user_id),
            )
            .first()
        )

    @staticmethod
    def get_active_by_user(
        db: Session,
        user_id: int,
        plataforma: str = "telegram",
    ) -> ExternalBotSession | None:
        return (
            db.query(ExternalBotSession)
            .filter(
                ExternalBotSession.usuario_id == user_id,
                ExternalBotSession.plataforma == plataforma,
                ExternalBotSession.activo.is_(True),
            )
            .order_by(ExternalBotSession.fecha_actualizacion.desc())
            .first()
        )

    @staticmethod
    def create(db: Session, session: ExternalBotSession) -> ExternalBotSession:
        db.add(session)
        db.commit()
        db.refresh(session)
        return session

    @staticmethod
    def save(db: Session, session: ExternalBotSession) -> ExternalBotSession:
        db.commit()
        db.refresh(session)
        return session
