from sqlalchemy.orm import Session
from sqlalchemy.orm.attributes import flag_modified

from app.models.external_bot_session import ExternalBotSession


class ExternalBotSessionRepository:
    @staticmethod
    def get_by_channel_and_chat_id(
        db: Session,
        channel: str,
        external_chat_id: str,
    ) -> ExternalBotSession | None:
        return (
            db.query(ExternalBotSession)
            .filter(ExternalBotSession.channel == channel)
            .filter(ExternalBotSession.external_chat_id == external_chat_id)
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
        if session.pending_action_json is not None:
            flag_modified(session, "pending_action_json")
        db.add(session)
        db.commit()
        db.refresh(session)
        return session

    @staticmethod
    def delete(db: Session, session: ExternalBotSession) -> None:
        db.delete(session)
        db.commit()
