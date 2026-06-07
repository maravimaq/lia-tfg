from datetime import datetime

from sqlalchemy.orm import Session

from app.models.external_bot_link_code import ExternalBotLinkCode


class ExternalBotLinkCodeRepository:
    @staticmethod
    def create(db: Session, link_code: ExternalBotLinkCode) -> ExternalBotLinkCode:
        db.add(link_code)
        db.commit()
        db.refresh(link_code)
        return link_code

    @staticmethod
    def get_valid_by_code(
        db: Session,
        codigo: str,
        plataforma: str | None = None,
    ) -> ExternalBotLinkCode | None:
        query = db.query(ExternalBotLinkCode).filter(
            ExternalBotLinkCode.codigo == codigo.upper().strip(),
            ExternalBotLinkCode.usado.is_(False),
            ExternalBotLinkCode.fecha_expiracion > datetime.utcnow(),
        )

        if plataforma:
            query = query.filter(ExternalBotLinkCode.plataforma == plataforma)

        return query.first()

    @staticmethod
    def mark_as_used(db: Session, link_code: ExternalBotLinkCode) -> ExternalBotLinkCode:
        link_code.usado = True
        db.commit()
        db.refresh(link_code)
        return link_code

    @staticmethod
    def get_latest_active_by_user(
        db: Session,
        user_id: int,
        plataforma: str = "telegram",
    ) -> ExternalBotLinkCode | None:
        return (
            db.query(ExternalBotLinkCode)
            .filter(
                ExternalBotLinkCode.usuario_id == user_id,
                ExternalBotLinkCode.plataforma == plataforma,
                ExternalBotLinkCode.usado.is_(False),
                ExternalBotLinkCode.fecha_expiracion > datetime.utcnow(),
            )
            .order_by(ExternalBotLinkCode.fecha_creacion.desc())
            .first()
        )
