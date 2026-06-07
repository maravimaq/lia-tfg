from datetime import datetime, timedelta
import secrets
import string

from sqlalchemy.orm import Session

from app.models.configuracion_bot_externo import ConfiguracionBotExterno
from app.models.external_bot_link_code import ExternalBotLinkCode
from app.models.external_bot_session import ExternalBotSession
from app.models.user import User
from app.repositories.bot_config_repository import BotConfigRepository
from app.repositories.external_bot_link_code_repository import ExternalBotLinkCodeRepository
from app.repositories.external_bot_session_repository import ExternalBotSessionRepository
from app.schemas.external_bot import (
    ExternalBotBindingStatusResponse,
    ExternalBotLinkCodeResponse,
)


class ExternalBotBindingService:
    CODE_LENGTH = 8
    CODE_TTL_MINUTES = 15

    @staticmethod
    def _generate_code() -> str:
        alphabet = string.ascii_uppercase + string.digits
        return "".join(secrets.choice(alphabet) for _ in range(ExternalBotBindingService.CODE_LENGTH))

    @staticmethod
    def _ensure_bot_config_active(db: Session, user_id: int, plataforma: str) -> None:
        config = BotConfigRepository.get_by_user_id(db, user_id)
        if config is None:
            config = ConfiguracionBotExterno(
                usuario_id=user_id,
                plataforma=plataforma,
                estado="activo",
            )
            BotConfigRepository.create(db, config)
            return

        config.plataforma = plataforma
        config.estado = "activo"
        BotConfigRepository.save(db, config)

    @staticmethod
    def create_link_code(
        db: Session,
        current_user: User,
        plataforma: str = "telegram",
    ) -> ExternalBotLinkCodeResponse:
        plataforma = plataforma.lower().strip()

        existing = ExternalBotLinkCodeRepository.get_latest_active_by_user(
            db,
            current_user.id_usuario,
            plataforma,
        )

        if existing:
            code = existing
        else:
            for _ in range(10):
                candidate = ExternalBotBindingService._generate_code()
                if ExternalBotLinkCodeRepository.get_valid_by_code(db, candidate) is None:
                    code = ExternalBotLinkCode(
                        codigo=candidate,
                        plataforma=plataforma,
                        usuario_id=current_user.id_usuario,
                        fecha_expiracion=datetime.utcnow()
                        + timedelta(minutes=ExternalBotBindingService.CODE_TTL_MINUTES),
                    )
                    code = ExternalBotLinkCodeRepository.create(db, code)
                    break
            else:
                raise RuntimeError("No se pudo generar un código de vinculación único")

        return ExternalBotLinkCodeResponse(
            codigo=code.codigo,
            plataforma=code.plataforma,
            fecha_expiracion=code.fecha_expiracion,
            instrucciones=(
                f"Escribe /start {code.codigo} en el bot de {code.plataforma} "
                "para vincular tu cuenta de LIA con Telegram."
            ),
        )

    @staticmethod
    def bind_external_user(
        db: Session,
        plataforma: str,
        external_user_id: str,
        codigo: str,
    ) -> ExternalBotSession | None:
        plataforma = plataforma.lower().strip()
        external_user_id = str(external_user_id).strip()
        codigo = codigo.upper().strip()

        link_code = ExternalBotLinkCodeRepository.get_valid_by_code(
            db,
            codigo,
            plataforma,
        )

        if link_code is None:
            return None

        existing_session = ExternalBotSessionRepository.get_by_external_user(
            db,
            plataforma,
            external_user_id,
        )

        if existing_session:
            existing_session.usuario_id = link_code.usuario_id
            existing_session.activo = True
            existing_session.estado_conversacion = "idle"
            existing_session.datos_temporales = {}
            session = ExternalBotSessionRepository.save(db, existing_session)
        else:
            session = ExternalBotSession(
                plataforma=plataforma,
                external_user_id=external_user_id,
                usuario_id=link_code.usuario_id,
                estado_conversacion="idle",
                datos_temporales={},
            )
            session = ExternalBotSessionRepository.create(db, session)

        ExternalBotLinkCodeRepository.mark_as_used(db, link_code)
        ExternalBotBindingService._ensure_bot_config_active(db, link_code.usuario_id, plataforma)
        return session

    @staticmethod
    def get_binding_status(
        db: Session,
        current_user: User,
        plataforma: str = "telegram",
    ) -> ExternalBotBindingStatusResponse:
        plataforma = plataforma.lower().strip()
        session = ExternalBotSessionRepository.get_active_by_user(
            db,
            current_user.id_usuario,
            plataforma,
        )

        if session is None:
            return ExternalBotBindingStatusResponse(
                plataforma=plataforma,
                vinculado=False,
            )

        return ExternalBotBindingStatusResponse(
            plataforma=session.plataforma,
            vinculado=True,
            external_user_id=session.external_user_id,
            estado_conversacion=session.estado_conversacion,
            fecha_vinculacion=session.fecha_creacion,
        )
