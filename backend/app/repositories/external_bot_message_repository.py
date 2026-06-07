from sqlalchemy.orm import Session

from app.models.external_bot_message import ExternalBotMessage


class ExternalBotMessageRepository:
    @staticmethod
    def create(db: Session, message: ExternalBotMessage) -> ExternalBotMessage:
        db.add(message)
        db.commit()
        db.refresh(message)
        return message

    @staticmethod
    def get_by_session_id(
        db: Session,
        session_id: int,
        limit: int = 50,
    ) -> list[ExternalBotMessage]:
        return (
            db.query(ExternalBotMessage)
            .filter(ExternalBotMessage.sesion_id == session_id)
            .order_by(ExternalBotMessage.fecha_creacion.desc())
            .limit(limit)
            .all()
        )
