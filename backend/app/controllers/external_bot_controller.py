from __future__ import annotations

from fastapi import APIRouter, Depends, Header, HTTPException, status
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.dependencies import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.repositories.external_bot_message_repository import ExternalBotMessageRepository
from app.repositories.external_bot_session_repository import ExternalBotSessionRepository
from app.schemas.external_bot import (
    ExternalBotBindingStatusResponse,
    ExternalBotLinkCodeCreate,
    ExternalBotLinkCodeResponse,
    ExternalBotMessageResponse,
    TelegramBotInfoResponse,
    TelegramWebhookActionResponse,
    TelegramWebhookProcessResponse,
    TelegramWebhookUpdate,
)
from app.services.external_bot_binding_service import ExternalBotBindingService
from app.services.external_bot_service import ExternalBotService
from app.services.telegram_bot_client import TelegramBotClient


router = APIRouter(prefix="/external-bot", tags=["external-bot"])


@router.get("/health")
def external_bot_health():
    return {"status": "ok", "module": "external-bot"}


@router.get("/telegram/me", response_model=TelegramBotInfoResponse)
def get_telegram_bot_info(current_user: User = Depends(get_current_user)):
    if not settings.telegram_bot_token:
        return TelegramBotInfoResponse(configured=False)

    me = TelegramBotClient().get_me()
    return TelegramBotInfoResponse(
        configured=True,
        id=me.get("id"),
        username=me.get("username"),
        first_name=me.get("first_name"),
        can_join_groups=me.get("can_join_groups"),
        can_read_all_group_messages=me.get("can_read_all_group_messages"),
        supports_inline_queries=me.get("supports_inline_queries"),
    )


@router.post("/link-code", response_model=ExternalBotLinkCodeResponse)
def create_external_bot_link_code(
    data: ExternalBotLinkCodeCreate = ExternalBotLinkCodeCreate(),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return ExternalBotBindingService.create_link_code(
        db,
        current_user,
        data.plataforma,
    )


@router.get("/binding-status", response_model=ExternalBotBindingStatusResponse)
def get_external_bot_binding_status(
    plataforma: str = "telegram",
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return ExternalBotBindingService.get_binding_status(
        db,
        current_user,
        plataforma,
    )


@router.get("/messages", response_model=list[ExternalBotMessageResponse])
def get_external_bot_messages(
    plataforma: str = "telegram",
    limit: int = 50,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    session = ExternalBotSessionRepository.get_active_by_user(
        db,
        current_user.id_usuario,
        plataforma,
    )

    if session is None:
        return []

    return ExternalBotMessageRepository.get_by_session_id(
        db,
        session.id_sesion_bot,
        limit=min(max(limit, 1), 100),
    )


@router.post("/telegram/set-webhook", response_model=TelegramWebhookActionResponse)
def set_telegram_webhook(current_user: User = Depends(get_current_user)):
    if not settings.telegram_webhook_base_url:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Falta TELEGRAM_WEBHOOK_BASE_URL en .env. Para local usa polling: python -m app.bots.telegram_polling",
        )

    webhook_url = settings.telegram_webhook_base_url.rstrip("/") + "/external-bot/webhook/telegram"
    result = TelegramBotClient().set_webhook(
        webhook_url,
        secret_token=settings.telegram_webhook_secret,
    )

    return TelegramWebhookActionResponse(
        ok=True,
        message="Webhook de Telegram configurado correctamente.",
        webhook_url=webhook_url,
        telegram_result=result,
    )


@router.delete("/telegram/webhook", response_model=TelegramWebhookActionResponse)
def delete_telegram_webhook(
    drop_pending_updates: bool = False,
    current_user: User = Depends(get_current_user),
):
    result = TelegramBotClient().delete_webhook(drop_pending_updates=drop_pending_updates)
    return TelegramWebhookActionResponse(
        ok=True,
        message="Webhook de Telegram eliminado correctamente.",
        telegram_result=result,
    )


@router.get("/telegram/webhook-info")
def get_telegram_webhook_info(current_user: User = Depends(get_current_user)):
    return TelegramBotClient().get_webhook_info()


@router.post("/webhook/telegram", response_model=TelegramWebhookProcessResponse)
def telegram_webhook(
    update: TelegramWebhookUpdate,
    db: Session = Depends(get_db),
    x_telegram_bot_api_secret_token: str | None = Header(default=None),
):
    if settings.telegram_webhook_secret:
        if x_telegram_bot_api_secret_token != settings.telegram_webhook_secret:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Secret token de Telegram inválido",
            )

    message = update.message or {}
    from_data = message.get("from") or {}
    chat_data = message.get("chat") or {}
    text = message.get("text")

    chat_id = chat_data.get("id")
    external_user_id = from_data.get("id") or chat_id

    if not external_user_id or not text or not chat_id:
        return TelegramWebhookProcessResponse(ok=True, ignored=True)

    response = ExternalBotService.process_message(
        db,
        "telegram",
        str(external_user_id),
        text,
    )

    TelegramBotClient().send_message(chat_id, response.reply)

    return TelegramWebhookProcessResponse(
        ok=True,
        ignored=False,
        reply=response.reply,
        action=response.action,
        state=response.state,
    )
