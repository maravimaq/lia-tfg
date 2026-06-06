from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.chat import (
    ListChatMessageRequest,
    ListChatMessageResponse,
    ListChatStoredMessage,
)
from app.services.list_chat_history_service import ListChatHistoryService
from app.services.list_chatbot_service import ListChatbotService


router = APIRouter(prefix="/chat", tags=["chat"])


@router.get(
    "/lista/{lista_id}/messages",
    response_model=list[ListChatStoredMessage],
)
def get_list_chat_messages(
    lista_id: int,
    limit: int = Query(default=100, ge=1, le=300),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return ListChatHistoryService.get_history(
        db=db,
        lista_id=lista_id,
        current_user=current_user,
        limit=limit,
    )


@router.post(
    "/lista/{lista_id}/message",
    response_model=ListChatMessageResponse,
)
def send_list_chat_message(
    lista_id: int,
    request: ListChatMessageRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    response = ListChatbotService.process_message(
        db=db,
        lista_id=lista_id,
        request=request,
        current_user=current_user,
    )

    ListChatHistoryService.save_interaction(
        db=db,
        lista_id=lista_id,
        current_user=current_user,
        user_content=request.message.strip(),
        assistant_response=response,
    )

    return response


@router.delete(
    "/lista/{lista_id}/messages",
)
def clear_list_chat_messages(
    lista_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return ListChatHistoryService.clear_history(
        db=db,
        lista_id=lista_id,
        current_user=current_user,
    )
