from __future__ import annotations

import re
import unicodedata
from collections import defaultdict
from decimal import Decimal, InvalidOperation
from typing import Any

from sqlalchemy.orm import Session

from app.models.producto import Producto
from app.models.producto_lista import ProductoLista
from app.models.user import User
from app.repositories.producto_repository import ProductoRepository
from app.schemas.chat import ListChatMessageRequest, ListChatMessageResponse
from app.services.chatbot_ai_service import ListChatbotAIService
from app.services.lista_compra_service import ListaCompraService


class ListChatbotService:
    MAX_ALTERNATIVES_PER_PRODUCT = 6
    MAX_SAVING_CANDIDATES = 8

    STOPWORDS = {
        "de",
        "del",
        "la",
        "las",
        "el",
        "los",
        "y",
        "con",
        "sin",
        "para",
        "por",
        "en",
        "un",
        "una",
        "unos",
        "unas",
        "dia",
        "mercadona",
        "carrefour",
        "aldi",
        "alcampo",
    }

    @staticmethod
    def process_message(
        db: Session,
        lista_id: int,
        request: ListChatMessageRequest,
        current_user: User,
    ) -> ListChatMessageResponse:
        lista = ListaCompraService.get_lista_detalle(db, lista_id, current_user)
        list_context = ListChatbotService._build_list_context(db, lista)

        ai_response = ListChatbotAIService.generate_response(
            user_message=request.message.strip(),
            list_context=list_context,
        )

        return ListChatMessageResponse(
            reply=ai_response.reply,
            intent=ai_response.intent,
            suggestions=ai_response.suggestions,
            context_summary={
                "lista_id": lista.id_lista,
                "nombre_lista": lista.nombre_lista,
                "total_estimado": str(lista.total_estimado),
                "num_productos": len(getattr(lista, "productos", [])),
                "confidence": ai_response.confidence,
                "provider": list_context.get("metadata", {}).get("provider_hint", "local"),
            },
        )

    @staticmethod
    def _build_list_context(db: Session, lista) -> dict[str, Any]:
        productos_lista: list[ProductoLista] = getattr(lista, "productos", [])

        productos_contexto: list[dict[str, Any]] = []
        supermercados_totales: dict[str, Decimal] = defaultdict(lambda: Decimal("0"))
        categorias_totales: dict[str, dict[str, Any]] = {}
        alternativas_contexto: list[dict[str, Any]] = []
        candidatos_ahorro: list[dict[str, Any]] = []

        total_lista = ListChatbotService._to_decimal(lista.total_estimado)

        for producto_lista in productos_lista:
            producto = getattr(producto_lista, "producto", None)
            if producto is None:
                continue

            cantidad = int(producto_lista.cantidad or 0)
            precio_unitario = ListChatbotService._to_decimal(producto.precio_unitario)
            subtotal = ListChatbotService._to_decimal(producto_lista.precio_estimado)
            supermercado = producto.supermercado or "Sin supermercado"
            categoria = producto.categoria or "Sin categoría"

            productos_contexto.append(
                {
                    "id_producto_lista": producto_lista.id_producto_lista,
                    "producto_id": producto.id_producto,
                    "nombre": producto.nombre,
                    "marca": producto.marca,
                    "categoria": producto.categoria,
                    "supermercado": producto.supermercado,
                    "cantidad": cantidad,
                    "precio_unitario": float(precio_unitario),
                    "precio_estimado": float(subtotal),
                    "unidad_medida": producto.unidad_medida,
                    "peso_en_total_porcentaje": ListChatbotService._percentage(subtotal, total_lista),
                }
            )

            supermercados_totales[supermercado] += subtotal

            if categoria not in categorias_totales:
                categorias_totales[categoria] = {
                    "categoria": categoria,
                    "num_productos": 0,
                    "subtotal": Decimal("0"),
                }
            categorias_totales[categoria]["num_productos"] += 1
            categorias_totales[categoria]["subtotal"] += subtotal

            alternativas = ListChatbotService._get_alternatives_for_product(db, producto)
            cheaper_alternatives = [
                alternative
                for alternative in alternativas
                if ListChatbotService._to_decimal(alternative.precio_unitario) < precio_unitario
            ]

            if alternativas:
                alternativas_contexto.append(
                    {
                        "producto_original": {
                            "producto_id": producto.id_producto,
                            "nombre": producto.nombre,
                            "marca": producto.marca,
                            "categoria": producto.categoria,
                            "supermercado": producto.supermercado,
                            "precio_unitario": float(precio_unitario),
                            "cantidad": cantidad,
                            "subtotal": float(subtotal),
                        },
                        "alternativas_baratas": [
                            ListChatbotService._alternative_to_context(
                                alternative=alternative,
                                original_price=precio_unitario,
                                quantity=cantidad,
                            )
                            for alternative in cheaper_alternatives[: ListChatbotService.MAX_ALTERNATIVES_PER_PRODUCT]
                        ],
                        "otras_alternativas": [
                            ListChatbotService._alternative_to_context(
                                alternative=alternative,
                                original_price=precio_unitario,
                                quantity=cantidad,
                            )
                            for alternative in alternativas[: ListChatbotService.MAX_ALTERNATIVES_PER_PRODUCT]
                        ],
                    }
                )

            if cheaper_alternatives:
                best = cheaper_alternatives[0]
                best_price = ListChatbotService._to_decimal(best.precio_unitario)
                ahorro_unitario = precio_unitario - best_price
                ahorro_estimado = ahorro_unitario * Decimal(cantidad)
                candidatos_ahorro.append(
                    {
                        "producto_original": producto.nombre,
                        "supermercado_original": producto.supermercado,
                        "precio_original": float(precio_unitario),
                        "cantidad": cantidad,
                        "alternativa": best.nombre,
                        "supermercado_alternativa": best.supermercado,
                        "precio_alternativa": float(best_price),
                        "ahorro_unitario": float(ahorro_unitario),
                        "ahorro_estimado": float(ahorro_estimado),
                        "advertencia": "Verificar equivalencia antes de sustituir.",
                    }
                )

        productos_mayor_peso = sorted(
            productos_contexto,
            key=lambda item: item["precio_estimado"],
            reverse=True,
        )[:5]

        productos_cantidad_alta = [
            product
            for product in productos_contexto
            if product["cantidad"] >= 3
        ]

        desglose_supermercados = [
            {
                "supermercado": supermercado,
                "total": float(total),
                "porcentaje_total_lista": ListChatbotService._percentage(total, total_lista),
            }
            for supermercado, total in sorted(
                supermercados_totales.items(), key=lambda item: item[1]
            )
        ]

        supermercado_mas_barato_actual = (
            desglose_supermercados[0]
            if desglose_supermercados
            else None
        )

        categorias_resumen = [
            {
                "categoria": data["categoria"],
                "num_productos": data["num_productos"],
                "subtotal": float(data["subtotal"]),
                "porcentaje_total_lista": ListChatbotService._percentage(data["subtotal"], total_lista),
            }
            for data in sorted(
                categorias_totales.values(),
                key=lambda item: item["subtotal"],
                reverse=True,
            )
        ]

        candidatos_ahorro = sorted(
            candidatos_ahorro,
            key=lambda item: item["ahorro_estimado"],
            reverse=True,
        )[: ListChatbotService.MAX_SAVING_CANDIDATES]

        return {
            "lista": {
                "id_lista": lista.id_lista,
                "nombre_lista": lista.nombre_lista,
                "total_estimado": float(total_lista),
            },
            "productos": productos_contexto,
            "analisis_precalculado": {
                "num_productos": len(productos_contexto),
                "desglose_supermercados_actual": desglose_supermercados,
                "supermercado_mas_barato_actual": supermercado_mas_barato_actual,
                "productos_mayor_peso_coste": productos_mayor_peso,
                "productos_con_cantidad_alta": productos_cantidad_alta,
                "categorias_resumen": categorias_resumen,
                "candidatos_ahorro": candidatos_ahorro,
            },
            "totales_actuales_por_supermercado": {
                supermercado: float(total)
                for supermercado, total in supermercados_totales.items()
            },
            "alternativas_en_catalogo": alternativas_contexto,
            "metadata": {
                "provider_hint": "ollama_or_mock",
                "nota_importante": (
                    "Los totales por supermercado son los de los productos actualmente elegidos. "
                    "No equivalen a comparar toda la misma cesta en todos los supermercados. "
                    "Las alternativas son coincidencias del catálogo y pueden no ser equivalentes exactos."
                ),
                "instrucciones_para_ia": (
                    "Usa primero analisis_precalculado. Cita productos, cantidades y precios concretos. "
                    "No des consejos genéricos si hay datos concretos disponibles."
                ),
            },
        }

    @staticmethod
    def _get_alternatives_for_product(
        db: Session,
        product: Producto,
    ) -> list[Producto]:
        candidates_by_id: dict[int, Producto] = {}

        for term in ListChatbotService._build_search_terms(product):
            for alternative in ProductoRepository.search_by_text(
                db=db,
                text=term,
                limit=12,
                orden_precio="asc",
            ):
                if alternative.id_producto == product.id_producto:
                    continue
                if not ListChatbotService._is_reasonable_alternative(product, alternative):
                    continue
                candidates_by_id[alternative.id_producto] = alternative

        return sorted(
            candidates_by_id.values(),
            key=lambda candidate: ListChatbotService._to_decimal(candidate.precio_unitario),
        )[: ListChatbotService.MAX_ALTERNATIVES_PER_PRODUCT]

    @staticmethod
    def _build_search_terms(product: Producto) -> list[str]:
        normalized_name = ListChatbotService._normalize(product.nombre)
        tokens = [
            token
            for token in normalized_name.split()
            if len(token) >= 4 and token not in ListChatbotService.STOPWORDS
        ]

        terms: list[str] = []
        if product.categoria:
            terms.append(product.categoria)

        if tokens:
            terms.append(tokens[0])
        if len(tokens) >= 2:
            terms.append(" ".join(tokens[:2]))
        if len(tokens) >= 3:
            terms.append(" ".join(tokens[:3]))

        # Mantener el nombre completo al final; a veces funciona bien con productos muy concretos.
        if product.nombre:
            terms.append(product.nombre)

        seen: set[str] = set()
        unique_terms: list[str] = []
        for term in terms:
            clean = term.strip()
            if clean and clean.lower() not in seen:
                seen.add(clean.lower())
                unique_terms.append(clean)

        return unique_terms[:4]

    @staticmethod
    def _is_reasonable_alternative(original: Producto, alternative: Producto) -> bool:
        original_category = ListChatbotService._normalize(original.categoria)
        alternative_category = ListChatbotService._normalize(alternative.categoria)

        if original_category and alternative_category and original_category == alternative_category:
            return True

        original_tokens = set(ListChatbotService._keywords(original.nombre))
        alternative_tokens = set(ListChatbotService._keywords(alternative.nombre))

        if not original_tokens or not alternative_tokens:
            return False

        return len(original_tokens.intersection(alternative_tokens)) >= 1

    @staticmethod
    def _alternative_to_context(
        alternative: Producto,
        original_price: Decimal,
        quantity: int,
    ) -> dict[str, Any]:
        alternative_price = ListChatbotService._to_decimal(alternative.precio_unitario)
        ahorro_unitario = original_price - alternative_price
        return {
            "producto_id": alternative.id_producto,
            "nombre": alternative.nombre,
            "marca": alternative.marca,
            "categoria": alternative.categoria,
            "supermercado": alternative.supermercado,
            "precio_unitario": float(alternative_price),
            "subtotal_estimado_misma_cantidad": float(alternative_price * Decimal(quantity)),
            "ahorro_unitario_vs_original": float(ahorro_unitario),
            "ahorro_estimado_misma_cantidad": float(ahorro_unitario * Decimal(quantity)),
            "unidad_medida": alternative.unidad_medida,
        }

    @staticmethod
    def _keywords(text: str | None) -> list[str]:
        normalized = ListChatbotService._normalize(text)
        return [
            token
            for token in normalized.split()
            if len(token) >= 4 and token not in ListChatbotService.STOPWORDS
        ]

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
    def _to_decimal(value: Any) -> Decimal:
        try:
            return Decimal(str(value or 0))
        except (InvalidOperation, ValueError, TypeError):
            return Decimal("0")

    @staticmethod
    def _percentage(part: Decimal, total: Decimal) -> float:
        if total <= 0:
            return 0.0
        return round(float((part / total) * Decimal("100")), 2)
