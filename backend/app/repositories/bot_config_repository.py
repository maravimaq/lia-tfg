from sqlalchemy.orm import Session

from app.models.configuracion_bot_externo import ConfiguracionBotExterno


class BotConfigRepository:
    @staticmethod
    def get_by_user_id(db: Session, user_id: int) -> ConfiguracionBotExterno | None:
        return db.query(ConfiguracionBotExterno).filter(
            ConfiguracionBotExterno.usuario_id == user_id
        ).first()

    @staticmethod
    def create(db: Session, config: ConfiguracionBotExterno) -> ConfiguracionBotExterno:
        db.add(config)
        db.commit()
        db.refresh(config)
        return config

    @staticmethod
    def save(db: Session, config: ConfiguracionBotExterno) -> ConfiguracionBotExterno:
        db.add(config)
        db.commit()
        db.refresh(config)
        return config