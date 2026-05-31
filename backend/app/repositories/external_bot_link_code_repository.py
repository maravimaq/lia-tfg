from datetime import datetime

from sqlalchemy.orm import Session

from app.models.external_bot_link_code import ExternalBotLinkCode


class ExternalBotLinkCodeRepository:
    @staticmethod
    def get_by_code(
        db: Session,
        channel: str,
        code: str,
    ) -> ExternalBotLinkCode | None:
        return (
            db.query(ExternalBotLinkCode)
            .filter(ExternalBotLinkCode.channel == channel)
            .filter(ExternalBotLinkCode.code == code)
            .first()
        )

    @staticmethod
    def get_active_by_code(
        db: Session,
        channel: str,
        code: str,
        now: datetime,
    ) -> ExternalBotLinkCode | None:
        return (
            db.query(ExternalBotLinkCode)
            .filter(ExternalBotLinkCode.channel == channel)
            .filter(ExternalBotLinkCode.code == code)
            .filter(ExternalBotLinkCode.estado == "pendiente")
            .filter(ExternalBotLinkCode.expires_at > now)
            .first()
        )

    @staticmethod
    def get_latest_by_user_and_channel(
        db: Session,
        user_id: int,
        channel: str,
    ) -> ExternalBotLinkCode | None:
        return (
            db.query(ExternalBotLinkCode)
            .filter(ExternalBotLinkCode.user_id == user_id)
            .filter(ExternalBotLinkCode.channel == channel)
            .order_by(ExternalBotLinkCode.fecha_creacion.desc())
            .first()
        )

    @staticmethod
    def expire_pending_by_user_and_channel(
        db: Session,
        user_id: int,
        channel: str,
        now: datetime,
    ) -> None:
        pending_codes = (
            db.query(ExternalBotLinkCode)
            .filter(ExternalBotLinkCode.user_id == user_id)
            .filter(ExternalBotLinkCode.channel == channel)
            .filter(ExternalBotLinkCode.estado == "pendiente")
            .all()
        )

        for link_code in pending_codes:
            link_code.estado = "expirado"
            link_code.expires_at = min(link_code.expires_at, now)
            db.add(link_code)

        db.commit()

    @staticmethod
    def create(db: Session, link_code: ExternalBotLinkCode) -> ExternalBotLinkCode:
        db.add(link_code)
        db.commit()
        db.refresh(link_code)
        return link_code

    @staticmethod
    def save(db: Session, link_code: ExternalBotLinkCode) -> ExternalBotLinkCode:
        db.add(link_code)
        db.commit()
        db.refresh(link_code)
        return link_code
