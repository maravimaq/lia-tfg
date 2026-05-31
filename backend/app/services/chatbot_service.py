import re
import unicodedata
from decimal import Decimal

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.producto import Producto
from app.models.user import User
from app.repositories.lista_compra_repository import ListaCompraRepository
from app.repositories.producto_repository import ProductoRepository
from app.schemas.chat import (
    ChatListOption,
    ChatMessageRequest,
    ChatMessageResponse,
    ChatPendingAction,
    ChatProductOption,
)


class ChatbotService:
    MAX_OPTIONS = 8

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

    @staticmethod
    def process_message(
        db: Session,
        request: ChatMessageRequest,
        current_user: User,
    ) -> ChatMessageResponse:
        message = request.message.strip()
        if not message:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="El mensaje no puede estar vacío",
            )

        normalized = ChatbotService._normalize_query(message)

        if normalized in {"cancelar", "cancela", "olvida", "anular"}:
            return ChatMessageResponse(
                reply="Perfecto, cancelo la acción pendiente.",
                intent="cancelar",
            )

        if ChatbotService._is_list_intent(normalized):
            return ChatbotService._list_user_lists(db, current_user)

        if ChatbotService._is_quantity_recommendation_intent(normalized):
            return ChatbotService._recommend_quantity(normalized)

        intent = "comparar_opciones" if ChatbotService._is_compare_intent(normalized) else "buscar_producto"
        query = ChatbotService._extract_product_query(normalized, intent)

        if not query:
            return ChatMessageResponse(
                reply=(
                    "No he entendido el mensaje. Prueba con 'tengo que comprar leche', "
                    "'qué pollo sale mejor' o 'cuánta pasta compro para 4 personas'."
                ),
                intent="desconocido",
            )

        return ChatbotService._search_products_response(
            db=db,
            query=query,
            intent=intent,
            lista_id=request.lista_id,
            order_by_price=intent == "comparar_opciones",
        )

    @staticmethod
    def _search_products_response(
        db: Session,
        query: str,
        intent: str,
        lista_id: int | None,
        order_by_price: bool,
    ) -> ChatMessageResponse:
        options = ChatbotService._search_products(db, query, order_by_price)

        if not options:
            return ChatMessageResponse(
                reply=f"No he encontrado productos para '{query}'. Prueba con un nombre más simple.",
                intent=intent,
                pending_action=ChatPendingAction(
                    type="search_product",
                    query=query,
                    lista_id=lista_id,
                ),
            )

        reply = (
            f"Estas son las opciones más baratas que he encontrado para '{query}'."
            if intent == "comparar_opciones"
            else f"He encontrado estas opciones para '{query}'. Elige una por número."
        )

        return ChatMessageResponse(
            reply=reply,
            intent=intent,
            options=options,
            pending_action=ChatPendingAction(
                type="select_product",
                query=query,
                lista_id=lista_id,
                options=options,
            ),
        )

    @staticmethod
    def _list_user_lists(db: Session, current_user: User) -> ChatMessageResponse:
        listas = ListaCompraRepository.get_all_by_user_id(db, current_user.id_usuario)
        options = [
            ChatListOption(
                id_lista=lista.id_lista,
                nombre_lista=lista.nombre_lista,
                total_estimado=lista.total_estimado,
            )
            for lista in listas
        ]

        if not options:
            return ChatMessageResponse(
                reply="No tienes listas activas ahora mismo.",
                intent="listar_listas",
            )

        return ChatMessageResponse(
            reply="Estas son tus listas activas.",
            intent="listar_listas",
            listas=options,
        )

    @staticmethod
    def _recommend_quantity(normalized_message: str) -> ChatMessageResponse:
        people = ChatbotService._extract_people_count(normalized_message) or 1
        product_query = ChatbotService._extract_quantity_product_query(normalized_message)

        rules = [
            ({"pasta", "macarrones", "espaguetis"}, 90, "g en seco"),
            ({"arroz"}, 80, "g en seco"),
            ({"pollo", "pechuga"}, 180, "g"),
            ({"carne", "ternera", "cerdo"}, 180, "g"),
            ({"pescado", "merluza", "salmon"}, 180, "g"),
            ({"patata", "patatas"}, 250, "g"),
            ({"tomate", "tomates"}, 150, "g"),
            ({"leche"}, 250, "ml"),
        ]

        for keywords, amount_per_person, unit in rules:
            if any(keyword in product_query for keyword in keywords):
                total = amount_per_person * people
                return ChatMessageResponse(
                    reply=(
                        f"Para {people} persona(s), compraría aproximadamente {total} {unit} "
                        f"de {product_query}. Ajusta un poco según hambre y si es plato principal."
                    ),
                    intent="recomendar_cantidad",
                    metadata={
                        "personas": people,
                        "producto_detectado": product_query,
                    },
                )

        return ChatMessageResponse(
            reply=(
                f"Para {people} persona(s), compraría una ración por persona y redondearía un poco al alza. "
                "Si me dices el producto concreto, puedo afinar más."
            ),
            intent="recomendar_cantidad",
            metadata={
                "personas": people,
                "producto_detectado": product_query,
            },
        )

    @staticmethod
    def _search_products(
        db: Session,
        query: str,
        order_by_price: bool,
    ) -> list[ChatProductOption]:
        normalized_query = ChatbotService._normalize_query(query)
        singular_query = ChatbotService._singularize(normalized_query)
        query_tokens = [token for token in singular_query.split() if len(token) > 2]

        matches: list[tuple[int, Decimal, Producto]] = []
        for product in ProductoRepository.get_all(db):
            searchable = ChatbotService._normalize_query(
                " ".join(
                    value
                    for value in [
                        product.nombre,
                        product.marca,
                        product.categoria,
                        product.supermercado,
                    ]
                    if value
                )
            )
            score = ChatbotService._score_match(
                searchable,
                normalized_query,
                singular_query,
                query_tokens,
            )
            if score is not None:
                matches.append((score, product.precio_unitario, product))

        if order_by_price:
            matches.sort(key=lambda item: (item[1], item[0], item[2].nombre.lower()))
        else:
            matches.sort(key=lambda item: (item[0], item[1], item[2].nombre.lower()))

        return [
            ChatbotService._to_product_option(product)
            for _, _, product in matches[: ChatbotService.MAX_OPTIONS]
        ]

    @staticmethod
    def _score_match(
        searchable: str,
        query: str,
        singular_query: str,
        query_tokens: list[str],
    ) -> int | None:
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
        return None

    @staticmethod
    def _to_product_option(product: Producto) -> ChatProductOption:
        return ChatProductOption(
            producto_id=product.id_producto,
            nombre=product.nombre,
            marca=product.marca,
            categoria=product.categoria,
            supermercado=product.supermercado,
            precio_unitario=product.precio_unitario,
            unidad_medida=product.unidad_medida,
        )

    @staticmethod
    def _extract_product_query(normalized_message: str, intent: str) -> str:
        text = normalized_message

        if intent == "comparar_opciones":
            for expression in [
                "que",
                "cual",
                "cuales",
                "sale mejor",
                "mas barato",
                "mejor precio",
                "comparar",
                "compara",
                "opcion",
                "opciones",
            ]:
                text = text.replace(expression, " ")
            return ChatbotService._clean_query(text)

        pattern = (
            r"^(tengo que comprar|tengo que coger|necesito comprar|necesito|"
            r"quiero comprar|comprar|compra|añade|anade|agrega|mete)\s+(.+)$"
        )
        match = re.search(pattern, text)
        candidate = match.group(2) if match else text
        return ChatbotService._clean_query(candidate)

    @staticmethod
    def _extract_quantity_product_query(normalized_message: str) -> str:
        text = re.sub(r"\b\d+\b", " ", normalized_message)
        for expression in [
            "cuanto",
            "cuanta",
            "cuantos",
            "cuantas",
            "compro",
            "comprar",
            "para",
            "personas",
            "persona",
        ]:
            text = text.replace(expression, " ")
        return ChatbotService._clean_query(text)

    @staticmethod
    def _clean_query(text: str) -> str:
        text = re.split(r"\s+(a la lista|en la lista|a mi lista|en mi lista)\s+", text)[0]
        text = re.sub(r"^\d+\s+", "", text).strip()
        for word in ChatbotService.NUMBER_WORDS:
            text = re.sub(rf"^{word}\s+", "", text).strip()
        return re.sub(r"\s+", " ", text).strip()

    @staticmethod
    def _extract_people_count(normalized_message: str) -> int | None:
        match = re.search(r"para\s+(\d+)\s+(persona|personas)", normalized_message)
        if match:
            return int(match.group(1))
        match = re.search(r"\b(\d+)\b", normalized_message)
        return int(match.group(1)) if match else None

    @staticmethod
    def _is_list_intent(normalized: str) -> bool:
        return any(
            expression in normalized
            for expression in [
                "mis listas",
                "ver listas",
                "listar listas",
                "que listas",
                "cuales son mis listas",
            ]
        )

    @staticmethod
    def _is_quantity_recommendation_intent(normalized: str) -> bool:
        return any(
            expression in normalized
            for expression in [
                "cuanto compro",
                "cuanta compro",
                "cuantos compro",
                "cuantas compro",
                "cantidad comprar",
            ]
        )

    @staticmethod
    def _is_compare_intent(normalized: str) -> bool:
        return any(
            expression in normalized
            for expression in [
                "sale mejor",
                "mas barato",
                "mejor precio",
                "comparar",
                "compara",
            ]
        )

    @staticmethod
    def _normalize_query(text: str | None) -> str:
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