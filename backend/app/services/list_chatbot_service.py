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
from app.core.config import settings
from app.schemas.chat import ListChatMessageRequest, ListChatMessageResponse
from app.services.chatbot_ai_service import ListChatbotAIService
from app.services.lista_compra_service import ListaCompraService


class ListChatbotService:
    MAX_ALTERNATIVES_PER_PRODUCT = 6
    MAX_SAVING_CANDIDATES = 8
    MAX_EQUIVALENT_PRODUCTS_FOR_COMPARISON = 300
    MAX_PRODUCT_LEVEL_COMPARISONS = 6

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
        "hacendado",
        "caocream",
        "molino",
        "dia",
        "rellena",
        "relleno",
        "crema",
    }

    CHOCOLATE_WORDS = {"chocolate", "cacao", "cacaos", "choco", "chips"}

    PRODUCT_FAMILIES = {
        "galleta": {"galleta", "galletas"},
        "oblea": {"oblea", "obleas"},
        "helado": {"helado", "helados"},
        "croissant": {"croissant", "cruasán", "cruasan", "croissants"},
        "napolitana": {"napolitana", "napolitanas"},
        "leche": {"leche"},
        "yogur": {"yogur", "yogurt", "yogures"},
        "arroz": {"arroz"},
        "pasta": {"pasta", "macarrones", "espaguetis", "spaghetti"},
        "pollo": {"pollo", "pechuga", "pechugas"},
        "tomate": {"tomate", "tomates"},
        "aceite": {"aceite"},
        "pan": {"pan", "molde", "barra", "baguette"},
    }

    INCOMPATIBLE_FAMILIES = {
        frozenset({"galleta", "oblea"}),
        frozenset({"galleta", "helado"}),
        frozenset({"croissant", "napolitana"}),
        frozenset({"pan", "galleta"}),
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
                "provider": list_context.get("metadata", {}).get("provider_hint", settings.ai_provider),
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
        equivalencias_por_producto: list[dict[str, Any]] = []
        comparativas_por_producto: list[dict[str, Any]] = []

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

            equivalent_products = ListChatbotService._get_equivalent_products_for_product(db, producto)
            equivalent_product_context = ListChatbotService._build_equivalent_product_context(
                producto_lista=producto_lista,
                producto=producto,
                equivalent_products=equivalent_products,
            )
            equivalencias_por_producto.append(equivalent_product_context)

            product_level_comparison = ListChatbotService._build_product_level_comparison(
                producto_lista=producto_lista,
                producto=producto,
                equivalent_products=equivalent_products,
            )
            if product_level_comparison:
                comparativas_por_producto.append(product_level_comparison)

            alternativas = [
                candidate
                for candidate in equivalent_products
                if candidate.id_producto != producto.id_producto
            ][: ListChatbotService.MAX_ALTERNATIVES_PER_PRODUCT]
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

        comparativa_cesta_equivalente = ListChatbotService._build_equivalent_basket_comparison(
            equivalencias_por_producto
        )
        comparativas_por_producto = sorted(
            comparativas_por_producto,
            key=lambda item: item.get("mejor_alternativa_otro_supermercado", {}).get("ahorro_estimado", 0),
            reverse=True,
        )[: ListChatbotService.MAX_PRODUCT_LEVEL_COMPARISONS]

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
                "comparativa_por_producto": comparativas_por_producto,
                "comparativa_cesta_equivalente": comparativa_cesta_equivalente,
            },
            "totales_actuales_por_supermercado": {
                supermercado: float(total)
                for supermercado, total in supermercados_totales.items()
            },
            "alternativas_en_catalogo": alternativas_contexto,
            "metadata": {
                "provider_hint": (settings.ai_provider or "ollama").lower(),
                "nota_importante": (
                    "desglose_supermercados_actual agrupa los productos ya elegidos. "
                    "comparativa_por_producto muestra alternativas parecidas más baratas en otros supermercados. "
                    "comparativa_cesta_equivalente intenta reconstruir una cesta similar por supermercado. "
                    "Las equivalencias del catálogo son aproximadas y pueden no ser exactas."
                ),
                "instrucciones_para_ia": (
                    "Usa primero analisis_precalculado. Para comparar supermercados, prioriza "
                    "comparativa_por_producto: el usuario quiere saber si hay productos concretos muy parecidos "
                    "más baratos en otros supermercados. Cita productos, cantidades y precios concretos."
                ),
            },
        }

    @staticmethod
    def _get_alternatives_for_product(
        db: Session,
        product: Producto,
    ) -> list[Producto]:
        return [
            candidate
            for candidate in ListChatbotService._get_equivalent_products_for_product(db, product)
            if candidate.id_producto != product.id_producto
        ][: ListChatbotService.MAX_ALTERNATIVES_PER_PRODUCT]

    @staticmethod
    def _get_equivalent_products_for_product(
        db: Session,
        product: Producto,
    ) -> list[Producto]:
        """Busca alternativas comparables producto a producto.

        La versión anterior dependía demasiado de búsquedas SQL por texto exacto y por eso
        podía no encontrar sustitutos útiles. Aquí recorremos el catálogo y puntuamos cada
        producto por familia, categoría y palabras relevantes. El objetivo no es reconstruir
        una cesta completa, sino encontrar frases útiles del tipo:
        "tienes X a 4,00 €, he visto Y parecido a 3,00 €".
        """
        scored_candidates: list[tuple[int, Decimal, Producto]] = []

        for candidate in ProductoRepository.get_all(db):
            if candidate.id_producto == product.id_producto:
                scored_candidates.append((10_000, ListChatbotService._to_decimal(candidate.precio_unitario), candidate))
                continue

            score = ListChatbotService._score_product_alternative(product, candidate)
            if score <= 0:
                continue

            scored_candidates.append((score, ListChatbotService._to_decimal(candidate.precio_unitario), candidate))

        scored_candidates.sort(
            key=lambda item: (
                item[2].id_producto != product.id_producto,
                -item[0],
                item[1],
                str(item[2].nombre or "").lower(),
            )
        )

        return [candidate for _, _, candidate in scored_candidates[: ListChatbotService.MAX_EQUIVALENT_PRODUCTS_FOR_COMPARISON]]

    @staticmethod
    def _build_equivalent_product_context(
        producto_lista: ProductoLista,
        producto: Producto,
        equivalent_products: list[Producto],
    ) -> dict[str, Any]:
        cantidad = int(producto_lista.cantidad or 0)
        opciones_por_supermercado: dict[str, dict[str, Any]] = {}

        for candidate in equivalent_products:
            supermercado = candidate.supermercado or "Sin supermercado"
            candidate_price = ListChatbotService._to_decimal(candidate.precio_unitario)
            current_option = opciones_por_supermercado.get(supermercado)

            if current_option is not None:
                current_price = ListChatbotService._to_decimal(current_option.get("precio_unitario"))
                if current_price <= candidate_price:
                    continue

            opciones_por_supermercado[supermercado] = {
                "producto_id": candidate.id_producto,
                "nombre": candidate.nombre,
                "marca": candidate.marca,
                "categoria": candidate.categoria,
                "supermercado": supermercado,
                "precio_unitario": float(candidate_price),
                "subtotal_estimado": float(candidate_price * Decimal(cantidad)),
                "unidad_medida": candidate.unidad_medida,
                "es_producto_original": candidate.id_producto == producto.id_producto,
            }

        return {
            "producto_original": {
                "producto_id": producto.id_producto,
                "nombre": producto.nombre,
                "marca": producto.marca,
                "categoria": producto.categoria,
                "supermercado": producto.supermercado,
                "precio_unitario": float(ListChatbotService._to_decimal(producto.precio_unitario)),
                "cantidad": cantidad,
                "subtotal": float(ListChatbotService._to_decimal(producto_lista.precio_estimado)),
                "unidad_medida": producto.unidad_medida,
            },
            "cantidad": cantidad,
            "opciones_por_supermercado": opciones_por_supermercado,
        }

    @staticmethod
    def _build_product_level_comparison(
        producto_lista: ProductoLista,
        producto: Producto,
        equivalent_products: list[Producto],
    ) -> dict[str, Any] | None:
        """Compara un producto de la lista con alternativas parecidas de otros supermercados.

        Esta comparación es la que usa el chatbot cuando el usuario pregunta dónde es más barata
        su lista en sentido práctico: producto actual frente a sustitutos similares, no una cesta
        completa reconstruida al 100%.
        """
        cantidad = int(producto_lista.cantidad or 0)
        if cantidad <= 0:
            return None

        precio_original = ListChatbotService._to_decimal(producto.precio_unitario)
        subtotal_original = ListChatbotService._to_decimal(producto_lista.precio_estimado)
        supermercado_original = producto.supermercado or "Sin supermercado"

        opciones: list[dict[str, Any]] = []
        seen_product_ids: set[int] = set()

        for candidate in equivalent_products:
            if candidate.id_producto in seen_product_ids:
                continue
            seen_product_ids.add(candidate.id_producto)

            candidate_price = ListChatbotService._to_decimal(candidate.precio_unitario)
            candidate_supermarket = candidate.supermercado or "Sin supermercado"
            subtotal_estimado = candidate_price * Decimal(cantidad)
            ahorro_estimado = subtotal_original - subtotal_estimado

            opciones.append(
                {
                    "producto_id": candidate.id_producto,
                    "nombre": candidate.nombre,
                    "marca": candidate.marca,
                    "categoria": candidate.categoria,
                    "supermercado": candidate_supermarket,
                    "precio_unitario": float(candidate_price),
                    "cantidad": cantidad,
                    "subtotal_estimado": float(subtotal_estimado),
                    "ahorro_estimado": float(ahorro_estimado),
                    "unidad_medida": candidate.unidad_medida,
                    "es_producto_original": candidate.id_producto == producto.id_producto,
                    "es_otro_supermercado": candidate_supermarket != supermercado_original,
                }
            )

        opciones = sorted(
            opciones,
            key=lambda item: (
                not item["es_otro_supermercado"],
                ListChatbotService._to_decimal(item["precio_unitario"]),
            ),
        )

        alternativas_otro_supermercado = [
            option
            for option in opciones
            if option["es_otro_supermercado"]
        ]
        alternativas_mas_baratas = sorted(
            [option for option in alternativas_otro_supermercado if option["ahorro_estimado"] > 0],
            key=lambda item: item["ahorro_estimado"],
            reverse=True,
        )
        alternativas_otro_supermercado = sorted(
            alternativas_otro_supermercado,
            key=lambda item: (
                item["ahorro_estimado"] <= 0,
                -item["ahorro_estimado"],
                ListChatbotService._to_decimal(item["precio_unitario"]),
            ),
        )

        if not alternativas_otro_supermercado:
            return None

        best_other = alternativas_mas_baratas[0] if alternativas_mas_baratas else alternativas_otro_supermercado[0]

        return {
            "producto_original": {
                "producto_id": producto.id_producto,
                "nombre": producto.nombre,
                "marca": producto.marca,
                "categoria": producto.categoria,
                "supermercado": supermercado_original,
                "precio_unitario": float(precio_original),
                "cantidad": cantidad,
                "subtotal": float(subtotal_original),
                "unidad_medida": producto.unidad_medida,
            },
            "opciones_comparables": opciones[:6],
            "alternativas_mas_baratas_otro_supermercado": alternativas_mas_baratas[:4],
            "alternativas_otro_supermercado": alternativas_otro_supermercado[:4],
            "mejor_alternativa_otro_supermercado": best_other,
            "tiene_ahorro": best_other.get("ahorro_estimado", 0) > 0,
        }

    @staticmethod
    def _build_equivalent_basket_comparison(
        equivalencias_por_producto: list[dict[str, Any]],
    ) -> dict[str, Any]:
        total_productos = len(equivalencias_por_producto)
        if total_productos == 0:
            return {
                "total_productos_lista": 0,
                "ranking": [],
                "cestas_completas": [],
                "cestas_parciales": [],
                "mejor_cesta_completa": None,
                "nota": "La lista no tiene productos suficientes para comparar una cesta equivalente.",
            }

        supermercados = sorted(
            {
                supermercado
                for item in equivalencias_por_producto
                for supermercado in item.get("opciones_por_supermercado", {}).keys()
            }
        )

        ranking: list[dict[str, Any]] = []

        for supermercado in supermercados:
            total = Decimal("0")
            productos_encontrados: list[dict[str, Any]] = []
            productos_no_encontrados: list[str] = []

            for item in equivalencias_por_producto:
                original = item.get("producto_original", {})
                cantidad = int(item.get("cantidad") or 0)
                option = item.get("opciones_por_supermercado", {}).get(supermercado)

                if option is None:
                    productos_no_encontrados.append(str(original.get("nombre", "Producto sin nombre")))
                    continue

                subtotal = ListChatbotService._to_decimal(option.get("subtotal_estimado"))
                total += subtotal
                productos_encontrados.append(
                    {
                        "producto_original": original.get("nombre"),
                        "producto_equivalente": option.get("nombre"),
                        "producto_id": option.get("producto_id"),
                        "cantidad": cantidad,
                        "precio_unitario": option.get("precio_unitario"),
                        "subtotal_estimado": option.get("subtotal_estimado"),
                        "unidad_medida": option.get("unidad_medida"),
                        "es_producto_original": option.get("es_producto_original", False),
                    }
                )

            encontrados = len(productos_encontrados)
            if encontrados == 0:
                continue

            ranking.append(
                {
                    "supermercado": supermercado,
                    "total_estimado": float(total),
                    "productos_encontrados": encontrados,
                    "productos_totales": total_productos,
                    "cobertura_porcentaje": round((encontrados / total_productos) * 100, 2),
                    "cesta_completa": encontrados == total_productos,
                    "productos": productos_encontrados,
                    "productos_no_encontrados": productos_no_encontrados,
                }
            )

        cestas_completas = sorted(
            [item for item in ranking if item["cesta_completa"]],
            key=lambda item: item["total_estimado"],
        )
        cestas_parciales = sorted(
            [item for item in ranking if not item["cesta_completa"]],
            key=lambda item: (-item["productos_encontrados"], item["total_estimado"]),
        )

        ranking_ordenado = cestas_completas + cestas_parciales

        return {
            "total_productos_lista": total_productos,
            "ranking": ranking_ordenado,
            "cestas_completas": cestas_completas,
            "cestas_parciales": cestas_parciales,
            "mejor_cesta_completa": cestas_completas[0] if cestas_completas else None,
            "nota": (
                "Comparación aproximada: para cada producto se busca el equivalente más barato encontrado "
                "en cada supermercado. Solo las cestas completas son comparables de forma razonable."
            ),
        }

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
        return ListChatbotService._score_product_alternative(original, alternative) > 0

    @staticmethod
    def _score_product_alternative(original: Producto, alternative: Producto) -> int:
        original_tokens = set(ListChatbotService._keywords(original.nombre))
        alternative_tokens = set(ListChatbotService._keywords(alternative.nombre))

        if not original_tokens or not alternative_tokens:
            return 0

        original_family = ListChatbotService._detect_product_family(original.nombre)
        alternative_family = ListChatbotService._detect_product_family(alternative.nombre)

        if original_family and alternative_family:
            if frozenset({original_family, alternative_family}) in ListChatbotService.INCOMPATIBLE_FAMILIES:
                return 0
            if original_family != alternative_family:
                return 0

        if original_family and not alternative_family:
            return 0

        shared_tokens = original_tokens.intersection(alternative_tokens)
        original_category = ListChatbotService._normalize(original.categoria)
        alternative_category = ListChatbotService._normalize(alternative.categoria)
        same_category = bool(original_category and alternative_category and original_category == alternative_category)

        original_supermarket = ListChatbotService._normalize(original.supermercado)
        alternative_supermarket = ListChatbotService._normalize(alternative.supermercado)
        other_supermarket = original_supermarket != alternative_supermarket

        score = 0

        if original_family and alternative_family and original_family == alternative_family:
            score += 60
        elif same_category:
            score += 30
        else:
            return 0

        score += min(len(shared_tokens), 5) * 12

        # Para productos de chocolate/cacao, no exigimos que compartan exactamente "cacao" y
        # "chocolate", pero sí premiamos que ambos sean de esa familia de sabor.
        original_has_chocolate = bool(original_tokens.intersection(ListChatbotService.CHOCOLATE_WORDS))
        alternative_has_chocolate = bool(alternative_tokens.intersection(ListChatbotService.CHOCOLATE_WORDS))
        if original_has_chocolate and alternative_has_chocolate:
            score += 20
        elif original_has_chocolate != alternative_has_chocolate:
            score -= 20

        if same_category:
            score += 15

        if other_supermarket:
            score += 8

        # Umbrales por familia. En galletas/bollería necesitamos ser más flexibles porque
        # los nombres comerciales cambian mucho entre supermercados.
        if original_family in {"galleta", "croissant", "napolitana"}:
            return score if score >= 60 else 0

        if original_family:
            return score if score >= 70 else 0

        return score if score >= 75 else 0

    @staticmethod
    def _detect_product_family(text: str | None) -> str | None:
        normalized = ListChatbotService._normalize(text)
        tokens = set(normalized.split())

        for family, aliases in ListChatbotService.PRODUCT_FAMILIES.items():
            if tokens.intersection(aliases):
                return family

        return None

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
