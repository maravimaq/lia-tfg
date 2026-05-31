from datetime import datetime, timedelta
import secrets
import string

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.configuracion_bot_externo import ConfiguracionBotExterno
from app.models.external_bot_link_code import ExternalBotLinkCode
from app.models.external_bot_session import ExternalBotSession
from app.models.user import User
from app.repositories.bot_config_repository import BotConfigRepository
from app.repositories.external_bot_link_code_repository import ExternalBotLinkCodeRepository
from app.repositories.external_bot_session_repository import ExternalBotSessionRepository
from app.schemas.external_bot import (
    ExternalBotGenerateLinkCodeRequest,
    ExternalBotLinkChatRequest,
    ExternalBotLinkChatResponse,
    ExternalBotLinkCodeResponse,
    ExternalBotLinkStatusResponse,
    ExternalBotUnlinkResponse,
)


class ExternalBotBindingService:
    CODE_LENGTH = 6
    CODE_EXPIRATION_MINUTES = 15
    CODE_ALPHABET = string.ascii_uppercase + string.digits

    @staticmethod
    def generate_link_code(
        db: Session,
        request: ExternalBotGenerateLinkCodeRequest,
        current_user: User,
    ) -> ExternalBotLinkCodeResponse:
        channel = request.channel.upper()
        now = datetime.utcnow()
        expires_at = now + timedelta(minutes=ExternalBotBindingService.CODE_EXPIRATION_MINUTES)

        ExternalBotLinkCodeRepository.expire_pending_by_user_and_channel(
            db=db,
            user_id=current_user.id_usuario,
            channel=channel,
            now=now,
        )

        code = ExternalBotBindingService._generate_unique_code(db, channel)

        link_code = ExternalBotLinkCodeRepository.create(
            db,
            ExternalBotLinkCode(
                user_id=current_user.id_usuario,
                channel=channel,
                code=code,
                estado="pendiente",
                expires_at=expires_at,
            ),
        )

        ExternalBotBindingService._update_user_bot_config(
            db=db,
            current_user=current_user,
            channel=channel,
            estado="pendiente_vinculacion",
        )

        return ExternalBotLinkCodeResponse(
            code=link_code.code,
            channel=link_code.channel,
            expires_at=link_code.expires_at,
            instructions=(
                "Abre el bot de Telegram de LIA y envía este comando: "
                f"/start {link_code.code}. "
                f"El código caduca en {ExternalBotBindingService.CODE_EXPIRATION_MINUTES} minutos."
            ),
        )

    @staticmethod
    def link_external_chat(
        db: Session,
        request: ExternalBotLinkChatRequest,
    ) -> ExternalBotLinkChatResponse:
        channel = request.channel.upper()
        code = request.code.strip().upper()
        external_chat_id = request.external_chat_id.strip()
        now = datetime.utcnow()

        link_code = ExternalBotLinkCodeRepository.get_active_by_code(
            db=db,
            channel=channel,
            code=code,
            now=now,
        )

        if not link_code:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Código de vinculación inválido o caducado.",
            )

        existing_session = ExternalBotSessionRepository.get_by_channel_and_chat_id(
            db=db,
            channel=channel,
            external_chat_id=external_chat_id,
        )

        if existing_session and existing_session.user_id != link_code.user_id:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Este chat externo ya está vinculado a otro usuario.",
            )

        if existing_session is None:
            ExternalBotSessionRepository.create(
                db,
                ExternalBotSession(
                    user_id=link_code.user_id,
                    channel=channel,
                    external_chat_id=external_chat_id,
                    state="idle",
                    pending_action_json={},
                ),
            )
        else:
            existing_session.state = existing_session.state or "idle"
            existing_session.pending_action_json = existing_session.pending_action_json or {}
            ExternalBotSessionRepository.save(db, existing_session)

        link_code.estado = "usado"
        link_code.used_at = now
        link_code.external_chat_id = external_chat_id
        ExternalBotLinkCodeRepository.save(db, link_code)

        user = link_code.usuario
        if user:
            ExternalBotBindingService._update_user_bot_config(
                db=db,
                current_user=user,
                channel=channel,
                estado="activo",
            )

        return ExternalBotLinkChatResponse(
            reply=(
                "Vinculación completada correctamente. Ya puedes escribirme mensajes como: "
                "tengo que comprar leche."
            ),
            linked=True,
            channel=channel,
            external_chat_id=external_chat_id,
            user_id=link_code.user_id,
        )

    @staticmethod
    def get_link_status(
        db: Session,
        channel: str,
        current_user: User,
    ) -> ExternalBotLinkStatusResponse:
        normalized_channel = channel.upper()
        sessions = ExternalBotSessionRepository.get_by_user_and_channel(
            db=db,
            user_id=current_user.id_usuario,
            channel=normalized_channel,
        )
        latest_code = ExternalBotLinkCodeRepository.get_latest_by_user_and_channel(
            db=db,
            user_id=current_user.id_usuario,
            channel=normalized_channel,
        )

        linked_session = sessions[0] if sessions else None

        return ExternalBotLinkStatusResponse(
            channel=normalized_channel,
            linked=linked_session is not None,
            external_chat_id=linked_session.external_chat_id if linked_session else None,
            state=linked_session.state if linked_session else None,
            last_link_code=latest_code.code if latest_code else None,
            last_link_code_status=latest_code.estado if latest_code else None,
            last_link_code_expires_at=latest_code.expires_at if latest_code else None,
        )

    @staticmethod
    def unlink(
        db: Session,
        channel: str,
        current_user: User,
    ) -> ExternalBotUnlinkResponse:
        normalized_channel = channel.upper()
        sessions = ExternalBotSessionRepository.get_by_user_and_channel(
            db=db,
            user_id=current_user.id_usuario,
            channel=normalized_channel,
        )

        deleted_count = 0
        for session in sessions:
            ExternalBotSessionRepository.delete(db, session)
            deleted_count += 1

        ExternalBotBindingService._update_user_bot_config(
            db=db,
            current_user=current_user,
            channel=normalized_channel,
            estado="inactivo",
        )

        return ExternalBotUnlinkResponse(
            detail="Vinculación eliminada correctamente.",
            deleted_sessions=deleted_count,
        )

    @staticmethod
    def _generate_unique_code(db: Session, channel: str) -> str:
        for _ in range(20):
            code = "".join(
                secrets.choice(ExternalBotBindingService.CODE_ALPHABET)
                for _ in range(ExternalBotBindingService.CODE_LENGTH)
            )
            existing = ExternalBotLinkCodeRepository.get_by_code(db, channel, code)
            if existing is None:
                return code

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="No se ha podido generar un código de vinculación único.",
        )

    @staticmethod
    def _update_user_bot_config(
        db: Session,
        current_user: User,
        channel: str,
        estado: str,
    ) -> ConfiguracionBotExterno:
        config = BotConfigRepository.get_by_user_id(db, current_user.id_usuario)
        if config is None:
            config = ConfiguracionBotExterno(usuario_id=current_user.id_usuario)

        config.plataforma = channel.lower()
        config.estado = estado

        if config.id_configuracion is None:
            return BotConfigRepository.create(db, config)

        return BotConfigRepository.save(db, config)
