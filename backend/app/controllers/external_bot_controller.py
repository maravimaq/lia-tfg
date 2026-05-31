from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_user, get_db
from app.models.user import User
from app.schemas.external_bot import (
    ExternalBotGenerateLinkCodeRequest,
    ExternalBotHistoryResponse,
    ExternalBotLinkChatRequest,
    ExternalBotLinkChatResponse,
    ExternalBotLinkCodeResponse,
    ExternalBotLinkStatusResponse,
    ExternalBotMessageRequest,
    ExternalBotMessageResponse,
    ExternalBotUnlinkResponse,
)
from app.services.external_bot_binding_service import ExternalBotBindingService
from app.services.external_bot_service import ExternalBotService


router = APIRouter(prefix="/external-bot", tags=["External Bot"])


@router.post("/message", response_model=ExternalBotMessageResponse)
def process_external_bot_message(
    request: ExternalBotMessageRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Endpoint de simulación protegido por JWT.

    Sirve para probar el flujo completo desde Swagger asociando external_chat_id
    al usuario autenticado. Más adelante Telegram usará el endpoint sin JWT.
    """
    return ExternalBotService.process_message(db, request, current_user)


@router.post("/linked-message", response_model=ExternalBotMessageResponse)
def process_linked_external_bot_message(
    request: ExternalBotMessageRequest,
    db: Session = Depends(get_db),
):
    """
    Endpoint de simulación del futuro webhook de Telegram.

    No recibe JWT. Busca el usuario a partir de channel + external_chat_id.
    Solo funcionará si el chat ya se ha vinculado con un código generado desde la app.
    """
    return ExternalBotService.process_linked_message(db, request)


@router.get("/messages", response_model=ExternalBotHistoryResponse)
def get_external_bot_history(
    external_chat_id: str = Query(...),
    channel: str = Query("TELEGRAM"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return ExternalBotService.get_history(
        db=db,
        channel=channel,
        external_chat_id=external_chat_id,
        current_user=current_user,
    )


@router.delete("/session")
def reset_external_bot_session(
    external_chat_id: str = Query(...),
    channel: str = Query("TELEGRAM"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    ExternalBotService.reset_session(
        db=db,
        channel=channel,
        external_chat_id=external_chat_id,
        current_user=current_user,
    )
    return {"detail": "Sesión externa eliminada correctamente"}


@router.post("/link-code", response_model=ExternalBotLinkCodeResponse)
def generate_external_bot_link_code(
    request: ExternalBotGenerateLinkCodeRequest = ExternalBotGenerateLinkCodeRequest(),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Genera un código temporal para vincular una cuenta externa, como Telegram,
    con el usuario autenticado de LIA.
    """
    return ExternalBotBindingService.generate_link_code(
        db=db,
        request=request,
        current_user=current_user,
    )


@router.get("/link-status", response_model=ExternalBotLinkStatusResponse)
def get_external_bot_link_status(
    channel: str = Query("TELEGRAM"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return ExternalBotBindingService.get_link_status(
        db=db,
        channel=channel,
        current_user=current_user,
    )


@router.post("/link-chat", response_model=ExternalBotLinkChatResponse)
def link_external_chat(
    request: ExternalBotLinkChatRequest,
    db: Session = Depends(get_db),
):
    """
    Simula el comando /start CÓDIGO de Telegram.

    En Telegram real, el external_chat_id será el chat.id recibido en el webhook.
    """
    return ExternalBotBindingService.link_external_chat(db=db, request=request)


@router.delete("/link", response_model=ExternalBotUnlinkResponse)
def unlink_external_bot(
    channel: str = Query("TELEGRAM"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return ExternalBotBindingService.unlink(
        db=db,
        channel=channel,
        current_user=current_user,
    )
