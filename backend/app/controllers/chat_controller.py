from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.chat import ListChatMessageRequest, ListChatMessageResponse
from app.services.list_chatbot_service import ListChatbotService


router = APIRouter(prefix="/chat", tags=["chat"])


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
    return ListChatbotService.process_message(
        db=db,
        lista_id=lista_id,
        request=request,
        current_user=current_user,
    )
