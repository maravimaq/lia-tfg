from sqlalchemy.orm import Session

from app.models.list_chat_message import ListChatMessage


class ListChatMessageRepository:

    @staticmethod
    def create(
        db: Session,
        *,
        lista_id: int,
        usuario_id: int,
        role: str,
        content: str,
        intent: str | None = None,
        suggestions_json: list | None = None,
        context_summary_json: dict | None = None,
    ) -> ListChatMessage:
        message = ListChatMessage(
            lista_id=lista_id,
            usuario_id=usuario_id,
            role=role,
            content=content,
            intent=intent,
            suggestions_json=suggestions_json or [],
            context_summary_json=context_summary_json or {},
        )

        db.add(message)
        db.commit()
        db.refresh(message)
        return message

    @staticmethod
    def get_by_lista_and_user(
        db: Session,
        *,
        lista_id: int,
        usuario_id: int,
        limit: int = 100,
    ) -> list[ListChatMessage]:
        return (
            db.query(ListChatMessage)
            .filter(ListChatMessage.lista_id == lista_id)
            .filter(ListChatMessage.usuario_id == usuario_id)
            .order_by(ListChatMessage.fecha_creacion.asc(), ListChatMessage.id_chat_message.asc())
            .limit(limit)
            .all()
        )

    @staticmethod
    def delete_by_lista_and_user(
        db: Session,
        *,
        lista_id: int,
        usuario_id: int,
    ) -> int:
        deleted = (
            db.query(ListChatMessage)
            .filter(ListChatMessage.lista_id == lista_id)
            .filter(ListChatMessage.usuario_id == usuario_id)
            .delete(synchronize_session=False)
        )
        db.commit()
        return deleted

    @staticmethod
    def delete_by_lista(
        db: Session,
        *,
        lista_id: int,
    ) -> int:
        deleted = (
            db.query(ListChatMessage)
            .filter(ListChatMessage.lista_id == lista_id)
            .delete(synchronize_session=False)
        )
        db.commit()
        return deleted