from sqlalchemy.orm import Session

from app.models.user import User
from app.repositories.list_chat_message_repository import ListChatMessageRepository
from app.schemas.chat import ListChatMessageResponse, ListChatStoredMessage
from app.services.lista_compra_service import ListaCompraService


class ListChatHistoryService:

    @staticmethod
    def get_history(
        db: Session,
        *,
        lista_id: int,
        current_user: User,
        limit: int = 100,
    ) -> list[ListChatStoredMessage]:
        # Valida que la lista existe, no está finalizada y el usuario tiene acceso.
        ListaCompraService.get_lista_by_id(db, lista_id, current_user)

        messages = ListChatMessageRepository.get_by_lista_and_user(
            db,
            lista_id=lista_id,
            usuario_id=current_user.id_usuario,
            limit=limit,
        )

        return [ListChatHistoryService._to_schema(message) for message in messages]

    @staticmethod
    def save_interaction(
        db: Session,
        *,
        lista_id: int,
        current_user: User,
        user_content: str,
        assistant_response: ListChatMessageResponse,
    ) -> None:
        ListChatMessageRepository.create(
            db,
            lista_id=lista_id,
            usuario_id=current_user.id_usuario,
            role="user",
            content=user_content,
        )

        ListChatMessageRepository.create(
            db,
            lista_id=lista_id,
            usuario_id=current_user.id_usuario,
            role="assistant",
            content=assistant_response.reply,
            intent=assistant_response.intent,
            suggestions_json=[
                suggestion.model_dump(mode="json")
                for suggestion in assistant_response.suggestions
            ],
            context_summary_json=assistant_response.context_summary,
        )

    @staticmethod
    def clear_history(
        db: Session,
        *,
        lista_id: int,
        current_user: User,
    ) -> dict[str, int | str]:
        # Valida permisos antes de borrar.
        ListaCompraService.get_lista_by_id(db, lista_id, current_user)

        deleted = ListChatMessageRepository.delete_by_lista_and_user(
            db,
            lista_id=lista_id,
            usuario_id=current_user.id_usuario,
        )

        return {
            "message": "Historial del chat eliminado correctamente",
            "deleted": deleted,
        }

    @staticmethod
    def _to_schema(message) -> ListChatStoredMessage:
        return ListChatStoredMessage(
            id_chat_message=message.id_chat_message,
            lista_id=message.lista_id,
            usuario_id=message.usuario_id,
            role=message.role,
            content=message.content,
            intent=message.intent,
            suggestions=message.suggestions_json or [],
            context_summary=message.context_summary_json or {},
            fecha_creacion=message.fecha_creacion,
        )
