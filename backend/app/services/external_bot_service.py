from __future__ import annotations

import re
import unicodedata
from decimal import Decimal

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models.external_bot_message import ExternalBotMessage
from app.models.external_bot_session import ExternalBotSession
from app.models.user import User
from app.repositories.external_bot_message_repository import ExternalBotMessageRepository
from app.repositories.external_bot_session_repository import ExternalBotSessionRepository
from app.repositories.lista_compra_repository import ListaCompraRepository
from app.repositories.producto_repository import ProductoRepository
from app.schemas.external_bot import ExternalBotOption, ExternalBotResponse
from app.schemas.lista_compra import ListaCompraCreate
from app.schemas.producto_lista import ProductoListaCreate
from app.services.external_bot_binding_service import ExternalBotBindingService
from app.services.lista_compra_service import ListaCompraService
from app.services.producto_lista_service import ProductoListaService


class ExternalBotService:
    @staticmethod
    def _normalize(text: str) -> str:
        text = text.strip().lower()
        text = "".join(
            char for char in unicodedata.normalize("NFD", text)
            if unicodedata.category(char) != "Mn"
        )
        return re.sub(r"\s+", " ", text)

    @staticmethod
    def _format_price(value: Decimal | float | int | None) -> str:
        if value is None:
            return "0,00 €"
        return f"{float(value):.2f}".replace(".", ",") + " €"

    @staticmethod
    def _product_label(producto) -> str:
        marca = f" - {producto.marca}" if producto.marca else ""
        unidad = f"/{producto.unidad_medida}" if producto.unidad_medida else ""
        return (
            f"{producto.nombre}{marca} - {producto.supermercado} - "
            f"{ExternalBotService._format_price(producto.precio_unitario)}{unidad}"
        )

    @staticmethod
    def _get_user_from_session(session: ExternalBotSession) -> User:
        return session.usuario

    @staticmethod
    def _save_message(
        db: Session,
        session: ExternalBotSession,
        direction: str,
        text: str,
        payload: dict | None = None,
    ) -> None:
        ExternalBotMessageRepository.create(
            db,
            ExternalBotMessage(
                sesion_id=session.id_sesion_bot,
                direccion=direction,
                texto=text,
                payload=payload,
            ),
        )

    @staticmethod
    def _set_state(
        db: Session,
        session: ExternalBotSession,
        state: str,
        data: dict | None = None,
    ) -> ExternalBotSession:
        session.estado_conversacion = state
        # Importante: datos_temporales es JSON. SQLAlchemy no siempre detecta
        # cambios hechos sobre el mismo dict en memoria, así que asignamos una
        # copia nueva para que se persistan correctamente entre mensajes.
        session.datos_temporales = dict(data or {})
        return ExternalBotSessionRepository.save(db, session)

    @staticmethod
    def _reply(
        db: Session,
        session: ExternalBotSession,
        reply: str,
        action: str = "message",
        options: list[ExternalBotOption] | None = None,
        added_to_list_id: int | None = None,
        created_list_id: int | None = None,
    ) -> ExternalBotResponse:
        ExternalBotService._save_message(db, session, "outgoing", reply)
        return ExternalBotResponse(
            reply=reply,
            action=action,
            state=session.estado_conversacion,
            options=options or [],
            added_to_list_id=added_to_list_id,
            created_list_id=created_list_id,
        )

    @staticmethod
    def _extract_link_code(text: str) -> str | None:
        match = re.search(r"(?:/start|vincular|codigo|c[oó]digo)\s+([a-zA-Z0-9]{6,16})", text)
        if match:
            return match.group(1).upper()

        clean = text.strip().upper()
        if re.fullmatch(r"[A-Z0-9]{6,16}", clean):
            return clean

        return None

    @staticmethod
    def _extract_create_list_name(text: str) -> str | None:
        patterns = [
            r"^(?:crear|crea|nueva|hacer|haz)\s+(?:una\s+)?lista(?:\s+(?:llamada|con nombre))?\s+(.+)$",
            r"^lista\s+nueva\s+(.+)$",
        ]
        for pattern in patterns:
            match = re.search(pattern, text, flags=re.IGNORECASE)
            if match:
                name = match.group(1).strip(" .")
                return name[:80] if name else None
        return None

    @staticmethod
    def _extract_product_query_for_add(text: str) -> str | None:
        patterns = [
            r"^(?:añadir|anadir|agregar|meter|apuntar|comprar|compra)\s+(.+)$",
            r"^(?:tengo que comprar|necesito|me hace falta|me falta)\s+(.+)$",
        ]
        for pattern in patterns:
            match = re.search(pattern, text, flags=re.IGNORECASE)
            if match:
                query = match.group(1).strip(" .")
                query = re.sub(r"\s+(?:a|en)\s+(?:la\s+)?lista\s+.+$", "", query, flags=re.IGNORECASE)
                return query if query else None
        return None

    @staticmethod
    def _extract_product_query_for_compare(text: str) -> str | None:
        patterns = [
            r"^(?:comparar|compara)\s+(?:precio\s+de\s+)?(.+)$",
            r"^(?:donde|dónde)\s+(?:esta|está|es)\s+(?:mas|más)\s+barat[oa]\s+(.+)$",
            r"^precio\s+de\s+(.+)$",
        ]
        for pattern in patterns:
            match = re.search(pattern, text, flags=re.IGNORECASE)
            if match:
                query = match.group(1).strip(" .")
                return query if query else None
        return None

    @staticmethod
    def _parse_positive_int(text: str) -> int | None:
        match = re.search(r"\d+", text)
        if not match:
            return None
        value = int(match.group(0))
        return value if value > 0 else None

    @staticmethod
    def _list_pending_lists(db: Session, user: User):
        return ListaCompraRepository.get_all_by_user_id(db, user.id_usuario)

    @staticmethod
    def _handle_waiting_product_selection(
        db: Session,
        session: ExternalBotSession,
        text: str,
    ) -> ExternalBotResponse:
        data = session.datos_temporales or {}
        products = data.get("products") or []
        selected = ExternalBotService._parse_positive_int(text)

        if selected is None or selected < 1 or selected > len(products):
            return ExternalBotService._reply(
                db,
                session,
                "No he entendido el número del producto. Responde con una de las opciones anteriores o escribe cancelar.",
                action="invalid_selection",
            )

        product_data = products[selected - 1]
        session = ExternalBotService._set_state(
            db,
            session,
            "waiting_quantity",
            {"product_id": product_data["id_producto"], "product_label": product_data["label"]},
        )

        return ExternalBotService._reply(
            db,
            session,
            f"Has elegido: {product_data['label']}\n¿Cuántas unidades quieres añadir?",
            action="ask_quantity",
        )

    @staticmethod
    def _handle_waiting_quantity(
        db: Session,
        session: ExternalBotSession,
        text: str,
    ) -> ExternalBotResponse:
        quantity = ExternalBotService._parse_positive_int(text)
        if quantity is None:
            return ExternalBotService._reply(
                db,
                session,
                "Indícame una cantidad válida, por ejemplo: 1, 2 o 3.",
                action="invalid_quantity",
            )

        user = ExternalBotService._get_user_from_session(session)
        lists = ExternalBotService._list_pending_lists(db, user)
        # Copiamos el JSON temporal para no mutar el mismo objeto en memoria.
        data = dict(session.datos_temporales or {})
        data["quantity"] = quantity

        if not lists:
            session = ExternalBotService._set_state(db, session, "idle", {})
            return ExternalBotService._reply(
                db,
                session,
                "No tienes listas pendientes. Crea una lista primero desde la app o escribe: crear lista Compra semanal.",
                action="no_lists",
            )

        if len(lists) == 1:
            return ExternalBotService._add_pending_product_to_list(
                db,
                session,
                lists[0].id_lista,
                quantity,
            )

        options = [
            ExternalBotOption(numero=index, label=lista.nombre_lista, value=lista.id_lista)
            for index, lista in enumerate(lists, start=1)
        ]

        data["lists"] = [
            {"id_lista": lista.id_lista, "nombre_lista": lista.nombre_lista}
            for lista in lists
        ]

        session = ExternalBotService._set_state(db, session, "waiting_list_selection", data)
        reply = "¿A qué lista quieres añadirlo?\n\n" + "\n".join(
            f"{option.numero}. {option.label}" for option in options
        )
        return ExternalBotService._reply(
            db,
            session,
            reply,
            action="ask_list_selection",
            options=options,
        )

    @staticmethod
    def _handle_waiting_list_selection(
        db: Session,
        session: ExternalBotSession,
        text: str,
    ) -> ExternalBotResponse:
        data = session.datos_temporales or {}
        lists = data.get("lists") or []
        selected = ExternalBotService._parse_positive_int(text)

        if selected is None or selected < 1 or selected > len(lists):
            normalized_text = ExternalBotService._normalize(text)
            matching_index = next(
                (
                    index
                    for index, item in enumerate(lists)
                    if ExternalBotService._normalize(str(item.get("nombre_lista", ""))) == normalized_text
                ),
                None,
            )
            if matching_index is None:
                return ExternalBotService._reply(
                    db,
                    session,
                    "No he entendido el número de la lista. Responde con una de las opciones anteriores o escribe cancelar.",
                    action="invalid_selection",
                )
            selected = matching_index + 1

        selected_list = lists[selected - 1]
        return ExternalBotService._add_pending_product_to_list(
            db,
            session,
            selected_list["id_lista"],
            int(data.get("quantity", 1)),
        )

    @staticmethod
    def _add_pending_product_to_list(
        db: Session,
        session: ExternalBotSession,
        lista_id: int,
        quantity: int,
    ) -> ExternalBotResponse:
        data = session.datos_temporales or {}
        product_id = data.get("product_id")
        product_label = data.get("product_label", "producto")
        user = ExternalBotService._get_user_from_session(session)

        if not product_id:
            session = ExternalBotService._set_state(db, session, "idle", {})
            return ExternalBotService._reply(
                db,
                session,
                "He perdido el producto que querías añadir. Vuelve a escribir el producto.",
                action="missing_pending_product",
            )

        try:
            ProductoListaService.create_producto(
                db,
                ProductoListaCreate(
                    lista_id=lista_id,
                    producto_id=int(product_id),
                    cantidad=quantity,
                ),
                user,
            )
        except HTTPException as exc:
            session = ExternalBotService._set_state(db, session, "idle", {})
            return ExternalBotService._reply(
                db,
                session,
                str(exc.detail),
                action="error",
            )

        list_obj = ListaCompraRepository.get_by_id(db, lista_id)
        list_name = list_obj.nombre_lista if list_obj else f"lista {lista_id}"
        session = ExternalBotService._set_state(db, session, "idle", {})

        return ExternalBotService._reply(
            db,
            session,
            f"Añadido: {quantity} unidad/es de {product_label} a la lista {list_name}.",
            action="product_added",
            added_to_list_id=lista_id,
        )

    @staticmethod
    def _handle_create_list(
        db: Session,
        session: ExternalBotSession,
        name: str,
    ) -> ExternalBotResponse:
        user = ExternalBotService._get_user_from_session(session)
        lista = ListaCompraService.create_lista(
            db,
            ListaCompraCreate(nombre_lista=name, compartida=False),
            user,
        )
        return ExternalBotService._reply(
            db,
            session,
            f"Lista creada: {lista.nombre_lista}.",
            action="list_created",
            created_list_id=lista.id_lista,
        )

    @staticmethod
    def _handle_list_lists(db: Session, session: ExternalBotSession) -> ExternalBotResponse:
        user = ExternalBotService._get_user_from_session(session)
        lists = ExternalBotService._list_pending_lists(db, user)

        if not lists:
            return ExternalBotService._reply(
                db,
                session,
                "No tienes listas pendientes.",
                action="lists_empty",
            )

        reply = "Tus listas pendientes:\n\n" + "\n".join(
            f"{index}. {lista.nombre_lista} - {ExternalBotService._format_price(lista.total_estimado)}"
            for index, lista in enumerate(lists, start=1)
        )
        return ExternalBotService._reply(db, session, reply, action="lists_shown")

    @staticmethod
    def _handle_add_product(
        db: Session,
        session: ExternalBotSession,
        query: str,
    ) -> ExternalBotResponse:
        products = ProductoRepository.search_by_text(db, query, limit=20, orden_precio="asc")

        if not products:
            return ExternalBotService._reply(
                db,
                session,
                f"No he encontrado productos para '{query}'. Prueba con otro término, por ejemplo: leche, pan o arroz.",
                action="products_not_found",
            )

        options_data = [
            {"id_producto": product.id_producto, "label": ExternalBotService._product_label(product)}
            for product in products
        ]

        options = [
            ExternalBotOption(numero=index, label=item["label"], value=item["id_producto"])
            for index, item in enumerate(options_data, start=1)
        ]

        session = ExternalBotService._set_state(
            db,
            session,
            "waiting_product_selection",
            {"query": query, "products": options_data},
        )

        reply = (
            f"He encontrado estas opciones para '{query}'.\n"
            "Responde con el número del producto que quieres añadir:\n\n"
            + "\n".join(f"{option.numero}. {option.label}" for option in options)
        )
        return ExternalBotService._reply(
            db,
            session,
            reply,
            action="ask_product_selection",
            options=options,
        )

    @staticmethod
    def _handle_compare_product(
        db: Session,
        session: ExternalBotSession,
        query: str,
    ) -> ExternalBotResponse:
        products = ProductoRepository.search_by_text(db, query, limit=8, orden_precio="asc")

        if not products:
            return ExternalBotService._reply(
                db,
                session,
                f"No he encontrado productos para comparar '{query}'.",
                action="compare_not_found",
            )

        cheapest = products[0]
        reply = (
            f"La opción más barata que he encontrado para '{query}' es:\n"
            f"{ExternalBotService._product_label(cheapest)}\n\n"
            "Otras opciones:\n"
            + "\n".join(
                f"{index}. {ExternalBotService._product_label(product)}"
                for index, product in enumerate(products, start=1)
            )
        )
        return ExternalBotService._reply(db, session, reply, action="comparison_shown")

    @staticmethod
    def _help(db: Session, session: ExternalBotSession) -> ExternalBotResponse:
        reply = (
            "Puedes escribirme cosas como:\n"
            "• crear lista Compra semanal\n"
            "• añadir leche\n"
            "• tengo que comprar pan\n"
            "• comparar arroz\n"
            "• mis listas\n"
            "• cancelar"
        )
        return ExternalBotService._reply(db, session, reply, action="help")

    @staticmethod
    def process_message(
        db: Session,
        plataforma: str,
        external_user_id: str,
        text: str,
    ) -> ExternalBotResponse:
        plataforma = plataforma.lower().strip()
        external_user_id = str(external_user_id).strip()
        text = text.strip()
        normalized = ExternalBotService._normalize(text)

        code = ExternalBotService._extract_link_code(text)
        if code:
            bound_session = ExternalBotBindingService.bind_external_user(
                db,
                plataforma,
                external_user_id,
                code,
            )
            if bound_session:
                ExternalBotService._save_message(db, bound_session, "incoming", text)
                return ExternalBotService._reply(
                    db,
                    bound_session,
                    "Cuenta vinculada correctamente con LIA. Ya puedes crear listas, añadir productos o comparar precios desde aquí.",
                    action="linked",
                )

        session = ExternalBotSessionRepository.get_by_external_user(
            db,
            plataforma,
            external_user_id,
        )

        if session is None or not session.activo:
            return ExternalBotResponse(
                reply=(
                    "Tu cuenta externa todavía no está vinculada con LIA. "
                    "Genera un código desde Perfil > Configuración Bot Externo y escríbeme /start CÓDIGO."
                ),
                action="not_linked",
                state=None,
            )

        ExternalBotService._save_message(db, session, "incoming", text)

        if normalized in {"cancelar", "cancela", "salir", "reset"}:
            session = ExternalBotService._set_state(db, session, "idle", {})
            return ExternalBotService._reply(db, session, "Operación cancelada.", action="cancelled")

        if session.estado_conversacion == "waiting_product_selection":
            return ExternalBotService._handle_waiting_product_selection(db, session, text)

        if session.estado_conversacion == "waiting_quantity":
            return ExternalBotService._handle_waiting_quantity(db, session, text)

        if session.estado_conversacion == "waiting_list_selection":
            return ExternalBotService._handle_waiting_list_selection(db, session, text)

        if normalized in {"ayuda", "help", "/help", "hola", "buenas", "/start"}:
            return ExternalBotService._help(db, session)

        if normalized in {"mis listas", "listas", "ver listas", "lista"}:
            return ExternalBotService._handle_list_lists(db, session)

        list_name = ExternalBotService._extract_create_list_name(text)
        if list_name:
            return ExternalBotService._handle_create_list(db, session, list_name)

        compare_query = ExternalBotService._extract_product_query_for_compare(text)
        if compare_query:
            return ExternalBotService._handle_compare_product(db, session, compare_query)

        add_query = ExternalBotService._extract_product_query_for_add(text)
        if add_query:
            return ExternalBotService._handle_add_product(db, session, add_query)

        return ExternalBotService._reply(
            db,
            session,
            "No he entendido la petición. Prueba con: añadir leche, comparar arroz, crear lista Compra semanal o mis listas.",
            action="unknown_intent",
        )
