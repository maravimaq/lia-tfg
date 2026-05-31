from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_user, get_db
from app.models.user import User
from app.schemas.external_bot import (
    ExternalBotHistoryResponse,
    ExternalBotMessageRequest,
    ExternalBotMessageResponse,
)
from app.services.external_bot_service import ExternalBotService


router = APIRouter(prefix="/external-bot", tags=["External Bot"])


@router.post("/message", response_model=ExternalBotMessageResponse)
def process_external_bot_message(
    request: ExternalBotMessageRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Endpoint de simulación del futuro bot externo.

    De momento requiere JWT para poder asociar el external_chat_id al usuario autenticado.
    Más adelante, Telegram enviará mensajes a un webhook y se reutilizará la misma lógica.
    """
    return ExternalBotService.process_message(db, request, current_user)


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
