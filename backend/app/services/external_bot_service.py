import re
import unicodedata
from decimal import Decimal
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.external_bot_message import ExternalBotMessage
from app.models.external_bot_session import ExternalBotSession
from app.models.producto import Producto
from app.models.user import User
from app.repositories.external_bot_message_repository import ExternalBotMessageRepository
from app.repositories.external_bot_session_repository import ExternalBotSessionRepository
from app.repositories.lista_compra_repository import ListaCompraRepository
from app.repositories.producto_repository import ProductoRepository
from app.repositories.user_repository import UserRepository
from app.schemas.external_bot import (
    ExternalBotHistoryResponse,
    ExternalBotListOption,
    ExternalBotMessageRequest,
    ExternalBotMessageResponse,
    ExternalBotProductOption,
)
from app.schemas.producto_lista import ProductoListaCreate
from app.services.producto_lista_service import ProductoListaService


class ExternalBotService:
    STATE_IDLE = "idle"
    STATE_WAITING_PRODUCT_SELECTION = "waiting_product_selection"
    STATE_WAITING_QUANTITY = "waiting_quantity"
    STATE_WAITING_LIST_SELECTION = "waiting_list_selection"

    MAX_PRODUCT_OPTIONS = 8
    MAX_HISTORY_MESSAGES = 80

    NUMBER_WORDS = {
        "un": 1,
        "una": 1,
        "uno": 1,
        "dos": 2,
        "tres": 3,
        "cuatro": 4,
        "cinco": 5,
        "seis": 6,
        "siete": 7,
        "ocho": 8,
        "nueve": 9,
        "diez": 10,
    }

    STOPWORDS = {
        "de",
        "del",
        "la",
        "el",
        "los",
        "las",
        "un",
        "una",
        "unos",
        "unas",
        "para",
        "por",
        "con",
        "sin",
        "en",
        "a",
        "mi",
        "mis",
    }

    @staticmethod
    def process_message(
        db: Session,
        request: ExternalBotMessageRequest,
        current_user: User,
    ) -> ExternalBotMessageResponse:
        """
        Endpoint de simulación protegido por JWT.
        Si no existe sesión para external_chat_id, la crea asociada al usuario autenticado.
        """
        clean_message = request.message.strip()
        if not clean_message:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="El mensaje no puede estar vacío",
            )

        channel = request.channel.upper()
        session = ExternalBotService._get_or_create_session(
            db=db,
            current_user=current_user,
            channel=channel,
            external_chat_id=request.external_chat_id.strip(),
        )

        return ExternalBotService._process_message_with_session(
            db=db,
            request=request,
            current_user=current_user,
            session=session,
        )

    @staticmethod
    def process_linked_message(
        db: Session,
        request: ExternalBotMessageRequest,
    ) -> ExternalBotMessageResponse:
        """
        Endpoint de simulación sin JWT para probar el comportamiento del futuro webhook.
        Solo funciona si el external_chat_id ya está vinculado a un usuario de LIA.
        """
        clean_message = request.message.strip()
        if not clean_message:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="El mensaje no puede estar vacío",
            )

        channel = request.channel.upper()
        session = ExternalBotSessionRepository.get_by_channel_and_chat_id(
            db=db,
            channel=channel,
            external_chat_id=request.external_chat_id.strip(),
        )

        if not session:
            return ExternalBotMessageResponse(
                reply=(
                    "Este chat todavía no está vinculado a ninguna cuenta de LIA. "
                    "Abre la app, genera un código de vinculación y envíalo con /start CÓDIGO."
                ),
                state="not_linked",
                channel=channel,
                external_chat_id=request.external_chat_id.strip(),
                metadata={"linked": False},
            )

        current_user = UserRepository.get_by_id(db, session.user_id)
        if not current_user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Usuario vinculado no encontrado.",
            )

        return ExternalBotService._process_message_with_session(
            db=db,
            request=request,
            current_user=current_user,
            session=session,
        )

    @staticmethod
    def _process_message_with_session(
        db: Session,
        request: ExternalBotMessageRequest,
        current_user: User,
        session: ExternalBotSession,
    ) -> ExternalBotMessageResponse:
        clean_message = request.message.strip()

        ExternalBotService._save_message(
            db=db,
            session=session,
            role="user",
            content=clean_message,
        )

        normalized = ExternalBotService._normalize(clean_message)

        if ExternalBotService._is_cancel_intent(normalized):
            response = ExternalBotService._cancel_flow(db, session)
        elif ExternalBotService._is_help_intent(normalized):
            response = ExternalBotService._help_response(session)
        elif ExternalBotService._is_list_intent(normalized) and session.state == ExternalBotService.STATE_IDLE:
            response = ExternalBotService._show_lists(db, session, current_user)
        elif session.state == ExternalBotService.STATE_WAITING_PRODUCT_SELECTION:
            response = ExternalBotService._handle_product_selection(
                db,
                session,
                normalized,
                current_user,
            )
        elif session.state == ExternalBotService.STATE_WAITING_QUANTITY:
            response = ExternalBotService._handle_quantity(
                db,
                session,
                normalized,
                current_user,
            )
        elif session.state == ExternalBotService.STATE_WAITING_LIST_SELECTION:
            response = ExternalBotService._handle_list_selection(
                db,
                session,
                normalized,
                current_user,
            )
        else:
            response = ExternalBotService._start_product_search(
                db,
                session,
                normalized,
            )

        ExternalBotService._save_message(
            db=db,
            session=session,
            role="assistant",
            content=response.reply,
            metadata={
                "state": response.state,
                "product_options": [option.model_dump(mode="json") for option in response.product_options],
                "list_options": [option.model_dump(mode="json") for option in response.list_options],
            },
        )

        return response

    @staticmethod
    def get_history(
        db: Session,
        channel: str,
        external_chat_id: str,
        current_user: User,
    ) -> ExternalBotHistoryResponse:
        session = ExternalBotService._get_session_or_404(
            db=db,
            current_user=current_user,
            channel=channel.upper(),
            external_chat_id=external_chat_id,
        )
        messages = ExternalBotMessageRepository.get_by_session_id(
            db,
            session.id_external_bot_session,
            limit=ExternalBotService.MAX_HISTORY_MESSAGES,
        )
        return ExternalBotHistoryResponse(
            external_chat_id=session.external_chat_id,
            channel=session.channel,
            state=session.state,
            messages=messages,
        )

    @staticmethod
    def reset_session(
        db: Session,
        channel: str,
        external_chat_id: str,
        current_user: User,
    ) -> None:
        session = ExternalBotService._get_session_or_404(
            db=db,
            current_user=current_user,
            channel=channel.upper(),
            external_chat_id=external_chat_id,
        )
        ExternalBotSessionRepository.delete(db, session)

    @staticmethod
    def _get_or_create_session(
        db: Session,
        current_user: User,
        channel: str,
        external_chat_id: str,
    ) -> ExternalBotSession:
        session = ExternalBotSessionRepository.get_by_channel_and_chat_id(
            db,
            channel,
            external_chat_id,
        )

        if session:
            if session.user_id != current_user.id_usuario:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Este chat externo ya está vinculado a otro usuario.",
                )
            return session

        return ExternalBotSessionRepository.create(
            db,
            ExternalBotSession(
                user_id=current_user.id_usuario,
                channel=channel,
                external_chat_id=external_chat_id,
                state=ExternalBotService.STATE_IDLE,
                pending_action_json={},
            ),
        )

    @staticmethod
    def _get_session_or_404(
        db: Session,
        current_user: User,
        channel: str,
        external_chat_id: str,
    ) -> ExternalBotSession:
        session = ExternalBotSessionRepository.get_by_channel_and_chat_id(
            db,
            channel,
            external_chat_id,
        )
        if not session:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Sesión externa no encontrada",
            )
        if session.user_id != current_user.id_usuario:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="No tienes permiso para acceder a esta sesión externa",
            )
        return session

    @staticmethod
    def _save_message(
        db: Session,
        session: ExternalBotSession,
        role: str,
        content: str,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        ExternalBotMessageRepository.create(
            db,
            ExternalBotMessage(
                session_id=session.id_external_bot_session,
                role=role,
                content=content,
                metadata_json=metadata or {},
            ),
        )

    @staticmethod
    def _cancel_flow(db: Session, session: ExternalBotSession) -> ExternalBotMessageResponse:
        session.state = ExternalBotService.STATE_IDLE
        session.pending_action_json = {}
        ExternalBotSessionRepository.save(db, session)
        return ExternalBotService._response(
            session=session,
            reply="Perfecto, he cancelado la acción pendiente. Puedes escribirme algo como: tengo que comprar leche.",
        )

    @staticmethod
    def _help_response(session: ExternalBotSession) -> ExternalBotMessageResponse:
        return ExternalBotService._response(
            session=session,
            reply=(
                "Puedo ayudarte a añadir productos a tus listas.\n\n"
                "Ejemplos:\n"
                "- Tengo que comprar leche\n"
                "- Añade 2 arroces\n"
                "- Mete tomate frito\n\n"
                "También puedes escribir 'cancelar' para reiniciar la conversación."
            ),
        )

    @staticmethod
    def _show_lists(
        db: Session,
        session: ExternalBotSession,
        current_user: User,
    ) -> ExternalBotMessageResponse:
        list_options = ExternalBotService._get_user_list_options(db, current_user)
        if not list_options:
            return ExternalBotService._response(
                session=session,
                reply="No tienes listas activas ahora mismo.",
            )

        reply = "Estas son tus listas activas:\n" + ExternalBotService._format_list_options(list_options)
        return ExternalBotService._response(
            session=session,
            reply=reply,
            list_options=list_options,
        )

    @staticmethod
    def _start_product_search(
        db: Session,
        session: ExternalBotSession,
        normalized_message: str,
    ) -> ExternalBotMessageResponse:
        quantity = ExternalBotService._extract_quantity(normalized_message)
        product_query = ExternalBotService._extract_product_query(normalized_message)

        if not product_query:
            return ExternalBotService._response(
                session=session,
                reply=(
                    "No he entendido qué producto quieres buscar. "
                    "Prueba con: tengo que comprar leche."
                ),
            )

        product_options = ExternalBotService._search_product_options(
            db,
            product_query,
        )

        if not product_options:
            return ExternalBotService._response(
                session=session,
                reply=f"No he encontrado productos para '{product_query}'. Prueba con un término más simple.",
                metadata={"query": product_query},
            )

        session.state = ExternalBotService.STATE_WAITING_PRODUCT_SELECTION
        session.pending_action_json = {
            "product_query": product_query,
            "quantity": quantity,
            "product_options": [option.model_dump(mode="json") for option in product_options],
        }
        ExternalBotSessionRepository.save(db, session)

        reply = (
            f"He encontrado estas opciones para '{product_query}'.\n"
            f"Responde con el número del producto que quieres añadir:\n\n"
            f"{ExternalBotService._format_product_options(product_options)}"
        )

        return ExternalBotService._response(
            session=session,
            reply=reply,
            product_options=product_options,
            metadata={"query": product_query, "quantity_detected": quantity},
        )

    @staticmethod
    def _handle_product_selection(
        db: Session,
        session: ExternalBotSession,
        normalized_message: str,
        current_user: User,
    ) -> ExternalBotMessageResponse:
        pending = dict(session.pending_action_json or {})
        options = pending.get("product_options", [])
        selected = ExternalBotService._select_option_by_number(normalized_message, options)

        if not selected:
            return ExternalBotService._response(
                session=session,
                reply=(
                    "No he podido identificar la opción. Responde solo con el número del producto:\n\n"
                    f"{ExternalBotService._format_product_options_from_dict(options)}"
                ),
            )

        pending["selected_product"] = selected
        quantity = pending.get("quantity")

        if quantity and int(quantity) > 0:
            session.state = ExternalBotService.STATE_WAITING_LIST_SELECTION
            pending["quantity"] = int(quantity)
            session.pending_action_json = pending
            ExternalBotSessionRepository.save(db, session)
            return ExternalBotService._ask_for_list(db, session, current_user)

        session.state = ExternalBotService.STATE_WAITING_QUANTITY
        session.pending_action_json = pending
        ExternalBotSessionRepository.save(db, session)

        return ExternalBotService._response(
            session=session,
            reply=(
                f"Has elegido: {selected['nombre']} ({selected['supermercado']}, "
                f"{ExternalBotService._format_money(Decimal(str(selected['precio_unitario'])))}).\n"
                "¿Qué cantidad quieres añadir?"
            ),
        )

    @staticmethod
    def _handle_quantity(
        db: Session,
        session: ExternalBotSession,
        normalized_message: str,
        current_user: User,
    ) -> ExternalBotMessageResponse:
        quantity = ExternalBotService._extract_quantity(normalized_message)
        if not quantity or quantity <= 0:
            return ExternalBotService._response(
                session=session,
                reply="No he entendido la cantidad. Responde con un número, por ejemplo: 2.",
            )

        pending = dict(session.pending_action_json or {})
        pending["quantity"] = quantity
        session.pending_action_json = pending
        session.state = ExternalBotService.STATE_WAITING_LIST_SELECTION
        ExternalBotSessionRepository.save(db, session)

        return ExternalBotService._ask_for_list(db, session, current_user)

    @staticmethod
    def _ask_for_list(
        db: Session,
        session: ExternalBotSession,
        current_user: User | None = None,
    ) -> ExternalBotMessageResponse:
        if current_user is None:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="No se ha podido obtener el usuario para listar listas",
            )

        list_options = ExternalBotService._get_user_list_options(db, current_user)
        if not list_options:
            session.state = ExternalBotService.STATE_IDLE
            session.pending_action_json = {}
            ExternalBotSessionRepository.save(db, session)
            return ExternalBotService._response(
                session=session,
                reply="No tienes listas activas donde pueda añadir el producto.",
            )

        pending = dict(session.pending_action_json or {})
        pending["list_options"] = [option.model_dump(mode="json") for option in list_options]
        session.pending_action_json = pending
        ExternalBotSessionRepository.save(db, session)

        return ExternalBotService._response(
            session=session,
            reply=(
                "¿A qué lista quieres añadirlo? Responde con el número de la lista:\n\n"
                f"{ExternalBotService._format_list_options(list_options)}"
            ),
            list_options=list_options,
        )

    @staticmethod
    def _handle_list_selection(
        db: Session,
        session: ExternalBotSession,
        normalized_message: str,
        current_user: User,
    ) -> ExternalBotMessageResponse:
        pending = dict(session.pending_action_json or {})
        list_options = pending.get("list_options", [])
        selected_list = ExternalBotService._select_list(normalized_message, list_options)

        if not selected_list:
            return ExternalBotService._response(
                session=session,
                reply=(
                    "No he podido identificar la lista. Responde con el número o el nombre de la lista:\n\n"
                    f"{ExternalBotService._format_list_options_from_dict(list_options)}"
                ),
            )

        selected_product = pending.get("selected_product")
        quantity = int(pending.get("quantity") or 1)

        if not selected_product:
            session.state = ExternalBotService.STATE_IDLE
            session.pending_action_json = {}
            ExternalBotSessionRepository.save(db, session)
            return ExternalBotService._response(
                session=session,
                reply="Se ha perdido la selección del producto. Empezamos de nuevo: dime qué quieres comprar.",
            )

        producto_lista = ProductoListaService.create_producto(
            db=db,
            producto_data=ProductoListaCreate(
                lista_id=int(selected_list["lista_id"]),
                producto_id=int(selected_product["producto_id"]),
                cantidad=quantity,
            ),
            current_user=current_user,
        )

        subtotal = ExternalBotService._format_money(producto_lista.precio_estimado)
        product_price = ExternalBotService._format_money(
            Decimal(str(selected_product["precio_unitario"])),
        )

        session.state = ExternalBotService.STATE_IDLE
        session.pending_action_json = {}
        ExternalBotSessionRepository.save(db, session)

        return ExternalBotService._response(
            session=session,
            reply=(
                f"Añadido: {quantity} x {selected_product['nombre']} "
                f"a la lista '{selected_list['nombre_lista']}'.\n"
                f"Precio unitario: {product_price}. Subtotal estimado: {subtotal}."
            ),
            metadata={
                "lista_id": selected_list["lista_id"],
                "producto_id": selected_product["producto_id"],
                "cantidad": quantity,
                "producto_lista_id": producto_lista.id_producto_lista,
            },
        )

    @staticmethod
    def _get_user_list_options(db: Session, current_user: User) -> list[ExternalBotListOption]:
        listas = ListaCompraRepository.get_all_by_user_id(db, current_user.id_usuario)
        return [
            ExternalBotListOption(
                index=index,
                lista_id=lista.id_lista,
                nombre_lista=lista.nombre_lista,
                total_estimado=lista.total_estimado,
            )
            for index, lista in enumerate(listas, start=1)
        ]

    @staticmethod
    def _search_product_options(db: Session, query: str) -> list[ExternalBotProductOption]:
        products = ProductoRepository.get_all(db)
        normalized_query = ExternalBotService._normalize(query)
        singular_query = ExternalBotService._singularize(normalized_query)
        query_tokens = [
            token
            for token in singular_query.split()
            if len(token) > 2 and token not in ExternalBotService.STOPWORDS
        ]

        scored: list[tuple[int, Decimal, Producto]] = []
        for product in products:
            searchable = ExternalBotService._normalize(
                " ".join(
                    value
                    for value in [product.nombre, product.marca, product.categoria, product.supermercado]
                    if value
                )
            )
            score = ExternalBotService._score_product(searchable, normalized_query, singular_query, query_tokens)
            if score is not None:
                scored.append((score, product.precio_unitario, product))

        scored.sort(key=lambda item: (item[0], item[1], item[2].nombre.lower()))

        return [
            ExternalBotProductOption(
                index=index,
                producto_id=product.id_producto,
                nombre=product.nombre,
                marca=product.marca,
                supermercado=product.supermercado,
                precio_unitario=product.precio_unitario,
                unidad_medida=product.unidad_medida,
            )
            for index, (_, _, product) in enumerate(scored[: ExternalBotService.MAX_PRODUCT_OPTIONS], start=1)
        ]

    @staticmethod
    def _score_product(
        searchable: str,
        query: str,
        singular_query: str,
        query_tokens: list[str],
    ) -> int | None:
        if not query:
            return None
        if searchable == query:
            return 0
        if searchable.startswith(query):
            return 1
        if query in searchable:
            return 2
        if singular_query and singular_query in searchable:
            return 3
        if query_tokens and all(token in searchable for token in query_tokens):
            return 4
        if query_tokens and any(token in searchable for token in query_tokens):
            return 6
        return None

    @staticmethod
    def _extract_product_query(normalized_message: str) -> str:
        text = normalized_message

        for expression in [
            "tengo que comprar",
            "tengo que coger",
            "necesito comprar",
            "quiero comprar",
            "comprar",
            "compra",
            "añade",
            "anade",
            "agrega",
            "mete",
            "pon",
            "necesito",
        ]:
            if text.startswith(expression + " "):
                text = text[len(expression):].strip()
                break

        text = re.sub(r"^\d+\s+", "", text).strip()
        for word in ExternalBotService.NUMBER_WORDS:
            text = re.sub(rf"^{word}\s+", "", text).strip()

        text = re.split(r"\s+(a la lista|en la lista|a mi lista|en mi lista)\s+", text)[0]
        return re.sub(r"\s+", " ", text).strip()

    @staticmethod
    def _extract_quantity(normalized_message: str) -> int | None:
        match = re.search(r"\b(\d+)\b", normalized_message)
        if match:
            return int(match.group(1))

        first_word = normalized_message.split()[0] if normalized_message.split() else ""
        return ExternalBotService.NUMBER_WORDS.get(first_word)

    @staticmethod
    def _select_option_by_number(normalized_message: str, options: list[dict[str, Any]]) -> dict[str, Any] | None:
        number = ExternalBotService._extract_quantity(normalized_message)
        if not number:
            return None
        return next((option for option in options if int(option.get("index", -1)) == number), None)

    @staticmethod
    def _select_list(normalized_message: str, list_options: list[dict[str, Any]]) -> dict[str, Any] | None:
        selected_by_number = ExternalBotService._select_option_by_number(normalized_message, list_options)
        if selected_by_number:
            return selected_by_number

        normalized_selection = ExternalBotService._normalize(normalized_message)
        return next(
            (
                option
                for option in list_options
                if normalized_selection in ExternalBotService._normalize(option.get("nombre_lista", ""))
                or ExternalBotService._normalize(option.get("nombre_lista", "")) in normalized_selection
            ),
            None,
        )

    @staticmethod
    def _is_cancel_intent(normalized: str) -> bool:
        return normalized in {"cancelar", "cancela", "cancel", "olvida", "parar", "salir"}

    @staticmethod
    def _is_help_intent(normalized: str) -> bool:
        return normalized in {"ayuda", "help", "/help", "?"}

    @staticmethod
    def _is_list_intent(normalized: str) -> bool:
        return normalized in {"listas", "mis listas", "ver listas", "listar listas"}

    @staticmethod
    def _normalize(text: str | None) -> str:
        if not text:
            return ""
        without_accents = "".join(
            char
            for char in unicodedata.normalize("NFD", text.lower())
            if unicodedata.category(char) != "Mn"
        )
        clean = re.sub(r"[^a-z0-9ñ\s]", " ", without_accents)
        return re.sub(r"\s+", " ", clean).strip()

    @staticmethod
    def _singularize(text: str) -> str:
        words = []
        for word in text.split():
            if word.endswith("es") and len(word) > 4:
                words.append(word[:-2])
            elif word.endswith("s") and len(word) > 3:
                words.append(word[:-1])
            else:
                words.append(word)
        return " ".join(words)

    @staticmethod
    def _format_money(value: Decimal | float | int | str) -> str:
        amount = Decimal(str(value)).quantize(Decimal("0.01"))
        return f"{amount:.2f}".replace(".", ",") + " €"

    @staticmethod
    def _format_product_options(options: list[ExternalBotProductOption]) -> str:
        return "\n".join(
            f"{option.index}. {option.nombre}"
            f"{f' - {option.marca}' if option.marca else ''}"
            f" - {option.supermercado} - {ExternalBotService._format_money(option.precio_unitario)}"
            for option in options
        )

    @staticmethod
    def _format_product_options_from_dict(options: list[dict[str, Any]]) -> str:
        return "\n".join(
            f"{option.get('index')}. {option.get('nombre')}"
            f"{f' - {option.get('marca')}' if option.get('marca') else ''}"
            f" - {option.get('supermercado')} - {ExternalBotService._format_money(option.get('precio_unitario', 0))}"
            for option in options
        )

    @staticmethod
    def _format_list_options(options: list[ExternalBotListOption]) -> str:
        return "\n".join(
            f"{option.index}. {option.nombre_lista} - total actual {ExternalBotService._format_money(option.total_estimado)}"
            for option in options
        )

    @staticmethod
    def _format_list_options_from_dict(options: list[dict[str, Any]]) -> str:
        return "\n".join(
            f"{option.get('index')}. {option.get('nombre_lista')} - total actual {ExternalBotService._format_money(option.get('total_estimado', 0))}"
            for option in options
        )

    @staticmethod
    def _response(
        session: ExternalBotSession,
        reply: str,
        product_options: list[ExternalBotProductOption] | None = None,
        list_options: list[ExternalBotListOption] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> ExternalBotMessageResponse:
        return ExternalBotMessageResponse(
            reply=reply,
            state=session.state,
            channel=session.channel,
            external_chat_id=session.external_chat_id,
            product_options=product_options or [],
            list_options=list_options or [],
            metadata=metadata or {},
        )
