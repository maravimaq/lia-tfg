from __future__ import annotations

import json
import re
from decimal import Decimal
from typing import Any

import httpx
from fastapi import HTTPException, status
from pydantic import ValidationError

from app.core.config import settings
from app.schemas.chat import ListChatAIResponse, ListChatSuggestion

class ListChatbotAIService:
    """Genera respuestas para el chat interno de una lista.

    La IA no modifica base de datos. Solo recibe contexto preparado por el backend y devuelve
    una respuesta estructurada. El backend ya ha validado usuario, permisos y lista.
    """

    SYSTEM_PROMPT = """
Eres LIA, el asistente inteligente de UNA lista de la compra concreta.

OBJETIVO
Ayudar al usuario a tomar mejores decisiones sobre la lista actual: comparar costes, recomendar cantidades,
detectar excesos, sugerir ahorro y explicar alternativas.

RESPONDE COMO PRODUCTO FINAL, NO COMO PROTOTIPO
- Nada de respuestas vagas tipo "podría ser útil revisar la lista" si hay datos concretos.
- Usa nombres de productos, cantidades, precios, supermercados y totales presentes en el contexto.
- Si haces una recomendación, explica brevemente el motivo.
- Sé breve, pero con contenido real: 2-5 frases suelen bastar.

REGLAS DE SEGURIDAD Y COHERENCIA
- Responde siempre en español.
- No inventes productos, precios, marcas ni supermercados.
- No digas que has añadido, eliminado o modificado productos. Este chat interno solo analiza y recomienda.
- Si el usuario pide añadir productos, responde que esa función se gestionará desde el bot externo o desde la interfaz de la app.
- Si faltan datos, dilo claramente y ofrece una estimación prudente.
- Las alternativas del catálogo pueden no ser equivalentes exactas; avisa cuando sugieras sustituciones.
- Si el usuario pregunta algo ajeno a la lista de la compra, usa intent "fuera_de_alcance".

CÓMO USAR EL CONTEXTO
- Prioriza el bloque "analisis_precalculado".
- Para "¿Dónde es más barata mi lista?", usa primero "comparativa_por_producto": compara productos concretos de la lista con alternativas muy parecidas y más baratas en otros supermercados. No limites la respuesta a una cesta completa.
- Para ahorro o sustituciones, usa "candidatos_ahorro" y menciona el ahorro estimado si aparece.
- Para cantidades, usa primero "historico_usuario" si está disponible: compara cantidad actual, media mensual, compras ya realizadas este mes, porcentaje del mes transcurrido y cantidad esperada restante.
- Si no hay historial suficiente, usa los productos de la lista si son relevantes; si no, da una regla práctica por persona.
- Para excesos, usa cantidades altas, productos repetidos, categorías con mucho peso o desviaciones frente al historial.

FORMATO DE SALIDA
Devuelve SIEMPRE un JSON válido y nada más. Debe cumplir exactamente este esquema:
{
  "intent": "analizar_lista | comparar_lista_supermercados | recomendar_cantidad | sugerir_ahorro | sugerir_sustituciones | detectar_excesos | pregunta_general_lista | fuera_de_alcance",
  "reply": "respuesta concreta en español",
  "suggestions": [
    {
      "type": "info | warning | saving | quantity | substitution",
      "title": "título corto",
      "description": "explicación concreta y breve"
    }
  ],
  "confidence": 0.0
}
"""

    WEAK_REPLY_PATTERNS = [
        "podría ser útil revisar",
        "asegurarse de que no haya",
        "excesos o insuficiencias",
        "la lista incluye productos",
        "sería recomendable revisar",
        "depende de tus necesidades",
    ]

    @staticmethod
    def generate_response(
        *,
        user_message: str,
        list_context: dict,
    ) -> ListChatAIResponse:
        provider = (settings.ai_provider or "cloudflare").lower().strip()

        # Para preguntas calculables sobre la lista, priorizamos el backend.
        # Evita que la IA invente precios, supermercados, cantidades o ahorros
        # cuando ya disponemos de datos objetivos calculados por LIA.
        if ListChatbotAIService._should_answer_deterministically(
            user_message,
            list_context,
        ):
            return ListChatbotAIService._generate_mock_response(
                user_message,
                list_context,
            )

        if provider == "mock":
            return ListChatbotAIService._generate_mock_response(
                user_message,
                list_context,
            )

        if provider == "cloudflare":
            return ListChatbotAIService._generate_with_cloudflare(
                user_message,
                list_context,
            )

        if provider == "ollama":
            return ListChatbotAIService._generate_with_ollama(
                user_message,
                list_context,
            )

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Proveedor de IA no soportado: {settings.ai_provider}",
        )

    @staticmethod
    def _generate_with_cloudflare(
        user_message: str,
        list_context: dict,
    ) -> ListChatAIResponse:
        if not settings.cloudflare_account_id:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Falta configurar CLOUDFLARE_ACCOUNT_ID en el backend.",
            )

        if not settings.cloudflare_ai_token:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Falta configurar CLOUDFLARE_AI_TOKEN en el backend.",
            )

        model = settings.cloudflare_ai_model

        url = (
            "https://api.cloudflare.com/client/v4/accounts/"
            f"{settings.cloudflare_account_id}/ai/run/{model}"
        )

        payload = {
            "messages": [
                {
                    "role": "system",
                    "content": ListChatbotAIService.SYSTEM_PROMPT,
                },
                {
                    "role": "user",
                    "content": ListChatbotAIService._build_user_prompt(
                        user_message,
                        list_context,
                    ),
                },
            ],
            "response_format": {
                "type": "json_schema",
                "json_schema": ListChatAIResponse.model_json_schema(),
            },
            "temperature": 0.1,
            "max_tokens": 500,
        }

        try:
            with httpx.Client(
                timeout=settings.cloudflare_ai_timeout_seconds
            ) as client:
                response = client.post(
                    url,
                    headers={
                        "Authorization": (
                            f"Bearer {settings.cloudflare_ai_token}"
                        ),
                        "Content-Type": "application/json",
                    },
                    json=payload,
                )
                response.raise_for_status()
                data = response.json()

        except httpx.ConnectError as exc:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="No se pudo conectar con Cloudflare Workers AI.",
            ) from exc

        except httpx.HTTPStatusError as exc:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=(
                    "Cloudflare Workers AI devolvió un error: "
                    f"{exc.response.text}"
                ),
            ) from exc

        except httpx.HTTPError as exc:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"Error al consultar Cloudflare Workers AI: {exc}",
            ) from exc

        result = data.get("result")

        if not isinstance(result, dict):
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Cloudflare Workers AI no devolvió un resultado válido.",
            )

        parsed_json = result.get("response")

        # Algunos modelos pueden devolver el JSON como texto dentro de choices.
        if not isinstance(parsed_json, dict):
            choices = result.get("choices") or []

            if choices:
                raw_content = (
                    choices[0]
                    .get("message", {})
                    .get("content")
                )

                if raw_content:
                    parsed_json = ListChatbotAIService._parse_ai_json(
                        raw_content
                    )

        if not isinstance(parsed_json, dict):
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=(
                    "Cloudflare Workers AI no devolvió "
                    "una respuesta estructurada."
                ),
            )

        try:
            ai_response = ListChatAIResponse.model_validate(parsed_json)

        except ValidationError as exc:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=(
                    "Cloudflare Workers AI no devolvió "
                    f"una respuesta válida: {exc}"
                ),
            ) from exc

        return ListChatbotAIService._postprocess_response(
            ai_response=ai_response,
            user_message=user_message,
            list_context=list_context,
        )

    @staticmethod
    def _generate_with_ollama(
        user_message: str,
        list_context: dict,
    ) -> ListChatAIResponse:
        payload = {
            "model": settings.ollama_model,
            "stream": False,
            "format": ListChatAIResponse.model_json_schema(),
            "options": {
                "temperature": 0.1,
                "top_p": 0.85,
                "num_ctx": 8192,
            },
            "messages": [
                {
                    "role": "system",
                    "content": ListChatbotAIService.SYSTEM_PROMPT,
                },
                {
                    "role": "user",
                    "content": ListChatbotAIService._build_user_prompt(user_message, list_context),
                },
            ],
        }

        url = settings.ollama_base_url.rstrip("/") + "/api/chat"

        try:
            with httpx.Client(timeout=settings.ollama_timeout_seconds) as client:
                response = client.post(url, json=payload)
                response.raise_for_status()
                data = response.json()
        except httpx.ConnectError as exc:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=(
                    "No se pudo conectar con Ollama. Comprueba que Ollama está abierto "
                    "y que responde en http://localhost:11434."
                ),
            ) from exc
        except httpx.HTTPStatusError as exc:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"Ollama devolvió un error: {exc.response.text}",
            ) from exc
        except httpx.HTTPError as exc:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"Error al consultar Ollama: {exc}",
            ) from exc

        raw_content = data.get("message", {}).get("content")
        if not raw_content:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Ollama no devolvió contenido en la respuesta.",
            )

        parsed_json = ListChatbotAIService._parse_ai_json(raw_content)

        try:
            ai_response = ListChatAIResponse.model_validate(parsed_json)
        except ValidationError as exc:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"La IA local no devolvió una respuesta válida: {exc}",
            ) from exc

        return ListChatbotAIService._postprocess_response(
            ai_response=ai_response,
            user_message=user_message,
            list_context=list_context,
        )

    @staticmethod
    def _build_user_prompt(user_message: str, list_context: dict) -> str:
        return (
            "Contexto de la lista en JSON. Usa estos datos como única fuente de verdad:\n"
            f"{json.dumps(list_context, ensure_ascii=False, default=str)}\n\n"
            "Mensaje del usuario:\n"
            f"{user_message}\n\n"
            "Recuerda: responde con datos concretos de la lista y devuelve solo JSON válido."
        )

    @staticmethod
    def _postprocess_response(
        *,
        ai_response: ListChatAIResponse,
        user_message: str,
        list_context: dict,
    ) -> ListChatAIResponse:
        # Con modelos locales pequeños puede ocurrir que devuelvan JSON válido,
        # pero con contenido poco útil. En ese caso gana el análisis determinista
        # del backend, que usa cálculos reales de la lista.
        if ListChatbotAIService._is_low_value_response(ai_response, user_message, list_context):
            return ListChatbotAIService._generate_mock_response(user_message, list_context)

        if ListChatbotAIService._is_weak_response(ai_response):
            fallback = ListChatbotAIService._generate_mock_response(user_message, list_context)
            if fallback.confidence >= ai_response.confidence or ai_response.confidence < 0.9:
                return fallback

        if not ai_response.suggestions:
            deterministic_suggestion = ListChatbotAIService._build_default_suggestion(user_message, list_context)
            if deterministic_suggestion:
                ai_response.suggestions.append(deterministic_suggestion)

        return ai_response

    @staticmethod
    def _is_low_value_response(
        response: ListChatAIResponse,
        user_message: str,
        list_context: dict,
    ) -> bool:
        reply = response.reply.lower().strip()
        suggestion_text = " ".join(
            f"{suggestion.title} {suggestion.description}".lower()
            for suggestion in response.suggestions
        )

        low_value_patterns = [
            "los productos son:",
            "el total estimado es el valor total",
            "valor total que se espera pagar",
            "la lista tiene un total estimado",
            "la lista incluye",
            "comparar los totales",
            "no hay productos en esta categoria",
            "no hay productos en esta categoría",
            "supermercados mas baratos",
            "supermercados más baratos",
            "consume mas peso",
            "consume más peso",
            "$",
        ]

        if any(pattern in reply or pattern in suggestion_text for pattern in low_value_patterns):
            return True

        # Si el usuario pide analizar y la respuesta solo enumera datos sin extraer ninguna conclusión,
        # preferimos la respuesta calculada por backend.
        message = user_message.lower()
        analysis_words = ["analiza", "analizar", "revisa", "opinión", "opinion", "qué ves", "que ves"]
        actionable_words = [
            "revis",
            "ahorr",
            "cambi",
            "sustitu",
            "caro",
            "barato",
            "exceso",
            "cantidad",
            "concentr",
        ]
        if any(word in message for word in analysis_words):
            has_actionable_reply = any(word in reply for word in actionable_words)
            has_actionable_suggestion = any(
                suggestion.type in {"warning", "saving", "quantity", "substitution"}
                for suggestion in response.suggestions
            )
            if not has_actionable_reply and not has_actionable_suggestion:
                return True

        return False

    @staticmethod
    def _is_weak_response(response: ListChatAIResponse) -> bool:
        normalized = response.reply.lower().strip()
        if len(normalized) < 80 and not response.suggestions:
            return True
        return any(pattern in normalized for pattern in ListChatbotAIService.WEAK_REPLY_PATTERNS)

    @staticmethod
    def _generate_mock_response(
        user_message: str,
        list_context: dict,
    ) -> ListChatAIResponse:
        """Fallback determinista para respuestas útiles aunque el modelo local sea vago."""
        message = user_message.lower()
        lista = list_context.get("lista", {})
        productos = list_context.get("productos", [])
        analysis = list_context.get("analisis_precalculado", {})
        total = ListChatbotAIService._to_float(lista.get("total_estimado", 0))
        nombre_lista = lista.get("nombre_lista", "esta lista")

        if any(word in message for word in ["barata", "barato", "supermercado", "donde", "dónde"]):
            return ListChatbotAIService._build_supermarket_comparison_response(analysis)

        if any(word in message for word in ["ahorro", "ahorrar", "sustituir", "cambiar", "alternativa", "barata"]):
            return ListChatbotAIService._build_saving_response(analysis)

        if ListChatbotAIService._is_quantity_or_amount_question(message):
            historical_response = ListChatbotAIService._build_historical_quantity_response(
                message=message,
                historico_usuario=list_context.get("historico_usuario") or {},
            )
            if historical_response:
                return historical_response

        if ListChatbotAIService._is_quantity_review_request(message):
            return ListChatbotAIService._build_quantity_review_response(analysis, productos)

        if ListChatbotAIService._is_quantity_recommendation_request(message):
            return ListChatbotAIService._build_quantity_response(message, productos)

        if any(word in message for word in ["exceso", "sobra", "demasiado", "mucho", "revisar"]):
            return ListChatbotAIService._build_excess_response(analysis)

        return ListChatbotAIService._build_analysis_response(
            nombre_lista=nombre_lista,
            total=total,
            productos=productos,
            analysis=analysis,
        )

    @staticmethod
    def _should_answer_deterministically(user_message: str, list_context: dict) -> bool:
        """Decide cuándo debe mandar el backend en vez del modelo local.

        Las preguntas con números, precios, comparaciones o cantidades deben ser trazables y
        consistentes. Ollama se conserva para preguntas más abiertas, pero no para cálculos.
        """
        message = user_message.lower()
        deterministic_keywords = [
            "analiza",
            "analizar",
            "revisa",
            "opinión",
            "opinion",
            "qué ves",
            "que ves",
            "barata",
            "barato",
            "supermercado",
            "donde",
            "dónde",
            "cantidad",
            "cuanto",
            "cuánto",
            "cuanta",
            "cuánta",
            "cuantos",
            "cuántos",
            "cuantas",
            "cuántas",
            "ahorro",
            "ahorrar",
            "sustituir",
            "cambiar",
            "alternativa",
            "exceso",
            "sobra",
            "demasiado",
            "mucho",
            "modificar",
            "coger",
            "coja",
            "comprar",
            "compre",
            "kg",
            "kilo",
            "kilos",
        ]
        return any(keyword in message for keyword in deterministic_keywords)

    @staticmethod
    def _is_quantity_review_request(message: str) -> bool:
        return (
            any(word in message for word in ["modificar", "revisar", "revisa", "recomiendas", "recomendar"])
            and any(word in message for word in ["cantidad", "kg", "kilo", "kilos", "unidad", "unidades"])
        )

    @staticmethod
    def _is_quantity_recommendation_request(message: str) -> bool:
        return any(word in message for word in ["cantidad", "cuanto", "cuánto", "cuánta", "cuanta", "cuantos", "cuántos", "cuantas", "cuántas"])

    @staticmethod
    def _is_quantity_or_amount_question(message: str) -> bool:
        return any(
            word in message
            for word in [
                "cantidad",
                "cuanto",
                "cuánto",
                "cuanta",
                "cuánta",
                "comprar",
                "compro",
                "compre",
                "coger",
                "coja",
                "llevar",
                "lleve",
                "kg",
                "kilo",
                "kilos",
                "unidad",
                "unidades",
                "está bien",
                "esta bien",
            ]
        )

    @staticmethod
    def _build_analysis_response(
        *,
        nombre_lista: str,
        total: float,
        productos: list[dict],
        analysis: dict,
    ) -> ListChatAIResponse:
        top_products = analysis.get("productos_mayor_peso_coste", [])
        breakdown = analysis.get("desglose_supermercados_actual", [])
        candidates = analysis.get("candidatos_ahorro", [])

        fragments = [
            f"La lista '{nombre_lista}' tiene {ListChatbotAIService._plural(len(productos), 'producto', 'productos')} y un total estimado de {ListChatbotAIService._format_money(total)}."
        ]

        if top_products:
            top = top_products[0]
            fragments.append(
                f"El producto que más pesa en el coste es {top.get('nombre')}, "
                f"con {ListChatbotAIService._format_money(top.get('precio_estimado', 0))} "
                f"({ListChatbotAIService._format_percent(top.get('peso_en_total_porcentaje', 0))} del total)."
            )

        if breakdown:
            supermarket_text = ", ".join(
                f"{item.get('supermercado')}: {ListChatbotAIService._format_money(item.get('total', 0))}"
                for item in breakdown
            )
            fragments.append(f"Por supermercado, ahora mismo queda así: {supermarket_text}.")

        sweet_count = ListChatbotAIService._count_sweet_products(productos)
        if sweet_count >= 2:
            fragments.append(
                f"Veo {ListChatbotAIService._plural(sweet_count, 'producto', 'productos')} de bollería/dulces, así que si esta lista no es solo para desayuno o merienda, "
                "la compra está bastante concentrada en ese tipo de producto."
            )

        if candidates:
            best = candidates[0]
            fragments.append(
                f"También hay una posible revisión de ahorro: {best.get('producto_original')} podría compararse con "
                f"{best.get('alternativa')} ({ListChatbotAIService._format_money(best.get('ahorro_estimado', 0))} de ahorro estimado), "
                "aunque habría que comprobar que sean equivalentes."
            )

        return ListChatAIResponse(
            intent="analizar_lista",
            reply=" ".join(fragments),
            suggestions=ListChatbotAIService._default_analysis_suggestions(analysis, productos),
            confidence=0.9,
        )

    @staticmethod
    def _build_supermarket_comparison_response(analysis: dict) -> ListChatAIResponse:
        product_comparisons = analysis.get("comparativa_por_producto", []) or []

        if product_comparisons:
            saving_comparisons = [
                comparison
                for comparison in product_comparisons
                if comparison.get("tiene_ahorro")
            ]
            neutral_comparisons = [
                comparison
                for comparison in product_comparisons
                if not comparison.get("tiene_ahorro")
            ]

            selected_comparisons = (saving_comparisons or neutral_comparisons)[:3]

            if saving_comparisons:
                fragments = [
                    "He revisado tu lista producto a producto y estas son las alternativas parecidas más baratas que he encontrado."
                ]
            else:
                fragments = [
                    "He revisado tu lista producto a producto. He encontrado productos parecidos en otros supermercados, pero no salen claramente más baratos con los precios actuales."
                ]

            for comparison in selected_comparisons:
                original = comparison.get("producto_original", {})
                alternative = comparison.get("mejor_alternativa_otro_supermercado", {})
                fragments.append(
                    ListChatbotAIService._format_product_level_comparison(
                        original=original,
                        alternative=alternative,
                    )
                )

            fragments.append(
                "La comparación es orientativa: son productos parecidos del catálogo, no necesariamente idénticos en formato, marca o peso."
            )

            suggestions = []
            for comparison in selected_comparisons:
                original = comparison.get("producto_original", {})
                alternative = comparison.get("mejor_alternativa_otro_supermercado", {})
                ahorro = float(alternative.get("ahorro_estimado") or 0)
                title = (
                    f"Ahorro en {original.get('nombre')}"
                    if ahorro > 0
                    else f"Alternativa encontrada para {original.get('nombre')}"
                )
                description = (
                    f"En {alternative.get('supermercado')} aparece {alternative.get('nombre')} por "
                    f"{ListChatbotAIService._format_money(alternative.get('precio_unitario', 0))}. "
                )
                if ahorro > 0:
                    description += f"Ahorro estimado: {ListChatbotAIService._format_money(ahorro)}."
                else:
                    description += "No mejora claramente el precio, pero sirve como referencia comparable."

                suggestions.append(
                    ListChatSuggestion(
                        type="saving" if ahorro > 0 else "info",
                        title=title,
                        description=description,
                    )
                )

            return ListChatAIResponse(
                intent="comparar_lista_supermercados",
                reply=" ".join(fragments),
                suggestions=suggestions,
                confidence=0.9 if saving_comparisons else 0.78,
            )

        return ListChatAIResponse(
            intent="comparar_lista_supermercados",
            reply=(
                "He intentado comparar tus productos con alternativas de otros supermercados, "
                "pero el catálogo no contiene productos suficientemente parecidos para hacer una recomendación fiable. "
                "Cuando haya más productos equivalentes entre supermercados, podré decirte cosas como: "
                "'este producto lo tienes aquí a 4,00 €, pero hay uno muy parecido allí a 3,00 €'."
            ),
            suggestions=[
                ListChatSuggestion(
                    type="warning",
                    title="Sin equivalencias claras",
                    description="No hay suficientes productos parecidos entre supermercados para recomendar cambios concretos.",
                )
            ],
            confidence=0.68,
        )

    @staticmethod
    def _format_product_level_comparison(original: dict, alternative: dict) -> str:
        original_quantity = int(original.get("cantidad") or 0)
        original_name = original.get("nombre") or "producto de la lista"
        original_supermarket = original.get("supermercado") or "su supermercado actual"
        alternative_name = alternative.get("nombre") or "una alternativa parecida"
        alternative_supermarket = alternative.get("supermercado") or "otro supermercado"
        ahorro = float(alternative.get("ahorro_estimado") or 0)

        base = (
            f"Tienes {original_name} en {original_supermarket} a "
            f"{ListChatbotAIService._format_money(original.get('precio_unitario', 0))} por unidad "
            f"({ListChatbotAIService._plural(original_quantity, 'unidad', 'unidades')}, "
            f"subtotal {ListChatbotAIService._format_money(original.get('subtotal', 0))}). "
            f"Una opción parecida es {alternative_name} en {alternative_supermarket} a "
            f"{ListChatbotAIService._format_money(alternative.get('precio_unitario', 0))} por unidad; "
            f"para la misma cantidad saldría por {ListChatbotAIService._format_money(alternative.get('subtotal_estimado', 0))}."
        )

        if ahorro > 0:
            return base + f" Ahorro estimado: {ListChatbotAIService._format_money(ahorro)}."

        diferencia = abs(ahorro)
        if diferencia == 0:
            return base + " El precio quedaría prácticamente igual."

        return base + f" No sería más barato: saldría aproximadamente {ListChatbotAIService._format_money(diferencia)} más caro."

    @staticmethod
    def _format_equivalent_basket_ranking(baskets: list[dict]) -> str:
        return "; ".join(
            f"{basket.get('supermercado')}: {ListChatbotAIService._format_money(basket.get('total_estimado', 0))}"
            for basket in baskets
        )

    @staticmethod
    def _format_partial_basket_ranking(baskets: list[dict]) -> str:
        return "; ".join(
            f"{basket.get('supermercado')}: {ListChatbotAIService._format_money(basket.get('total_estimado', 0))} "
            f"({basket.get('productos_encontrados')}/{basket.get('productos_totales')} productos)"
            for basket in baskets
        )

    @staticmethod
    def _format_current_supermarket_breakdown(analysis: dict) -> str:
        breakdown = analysis.get("desglose_supermercados_actual", []) or []
        if not breakdown:
            return "sin desglose disponible"
        return ", ".join(
            f"{item.get('supermercado')}: {ListChatbotAIService._format_money(item.get('total', 0))}"
            for item in breakdown
        )

    @staticmethod
    def _build_saving_response(analysis: dict) -> ListChatAIResponse:
        product_comparisons = [
            comparison
            for comparison in (analysis.get("comparativa_por_producto", []) or [])
            if comparison.get("tiene_ahorro")
        ]
        if product_comparisons:
            best = product_comparisons[0]
            original = best.get("producto_original", {})
            alternative = best.get("mejor_alternativa_otro_supermercado", {})
            reply = (
                "La oportunidad de ahorro más clara que veo está en comparar un producto concreto con otro supermercado. "
                + ListChatbotAIService._format_product_level_comparison(
                    original=original,
                    alternative=alternative,
                )
                + " Comprueba que el producto te encaje antes de sustituirlo."
            )
            return ListChatAIResponse(
                intent="sugerir_ahorro",
                reply=reply,
                suggestions=[
                    ListChatSuggestion(
                        type="saving",
                        title="Ahorro por sustitución",
                        description=(
                            f"{alternative.get('nombre')} en {alternative.get('supermercado')} podría ahorrarte "
                            f"{ListChatbotAIService._format_money(alternative.get('ahorro_estimado', 0))} frente a {original.get('nombre')}."
                        ),
                    )
                ],
                confidence=0.9,
            )

        candidates = analysis.get("candidatos_ahorro", [])
        if not candidates:
            return ListChatAIResponse(
                intent="sugerir_ahorro",
                reply="No he encontrado alternativas claramente más baratas en el catálogo para los productos actuales de esta lista.",
                suggestions=[],
                confidence=0.72,
            )

        best = candidates[0]
        reply = (
            f"La mejor oportunidad de ahorro que veo es revisar '{best.get('producto_original')}'. "
            f"Como alternativa aparece '{best.get('alternativa')}' en {best.get('supermercado_alternativa')} "
            f"por {ListChatbotAIService._format_money(best.get('precio_alternativa', 0))}, con un ahorro estimado de "
            f"{ListChatbotAIService._format_money(best.get('ahorro_estimado', 0))} para la misma cantidad. Comprueba que sea equivalente antes de cambiarlo."
        )

        return ListChatAIResponse(
            intent="sugerir_ahorro",
            reply=reply,
            suggestions=[
                ListChatSuggestion(
                    type="saving",
                    title="Posible ahorro",
                    description=(
                        f"{best.get('producto_original')} podría sustituirse por {best.get('alternativa')} "
                        f"si te encaja como producto equivalente."
                    ),
                )
            ],
            confidence=0.86,
        )

    @staticmethod
    def _build_historical_quantity_response(
        *,
        message: str,
        historico_usuario: dict,
    ) -> ListChatAIResponse | None:
        insights = historico_usuario.get("productos_relevantes", []) or []
        if not insights:
            return None

        selected = ListChatbotAIService._select_relevant_historical_insight(message, insights)
        if not selected:
            return None

        product_name = selected.get("producto_actual") or "este producto"
        current_quantity = ListChatbotAIService._to_float(selected.get("cantidad_actual"))
        avg_monthly = selected.get("cantidad_media_mensual")
        avg_per_purchase = selected.get("cantidad_media_por_compra")
        current_month_total = ListChatbotAIService._to_float(selected.get("cantidad_total_mes_actual"))
        expected_remaining = selected.get("cantidad_esperada_restante_mes")
        month_progress = ListChatbotAIService._to_float(selected.get("porcentaje_mes_transcurrido"))
        recommendation = selected.get("recomendacion_orientativa")
        historical_purchases = int(selected.get("compras_historicas") or 0)
        unit = selected.get("unidad_medida") or "unidades registradas"

        if historical_purchases == 0 or avg_monthly is None:
            return None

        fragments = [
            f"Para {product_name}, tu historial indica una media de {ListChatbotAIService._format_quantity(avg_monthly)} {unit} al mes",
        ]

        if avg_per_purchase is not None:
            fragments.append(
                f"y {ListChatbotAIService._format_quantity(avg_per_purchase)} {unit} por compra"
            )

        fragments.append(
            f"Ahora mismo llevas {ListChatbotAIService._format_quantity(current_month_total)} {unit} compradas este mes y el mes va aproximadamente por el {ListChatbotAIService._format_percent(month_progress)}."
        )

        if expected_remaining is not None:
            fragments.append(
                f"Para lo que queda de mes, la referencia sale en torno a {ListChatbotAIService._format_quantity(expected_remaining)} {unit}."
            )

        fragments.append(
            f"En tu lista actual tienes {ListChatbotAIService._format_quantity(current_quantity)} {unit}. {recommendation}"
        )

        return ListChatAIResponse(
            intent="recomendar_cantidad",
            reply=" ".join(fragments),
            suggestions=[
                ListChatSuggestion(
                    type="quantity",
                    title="Cantidad según historial",
                    description=(
                        f"Comparo {product_name} con tus compras anteriores. "
                        "Si el producto representa kg o packs depende de cómo esté registrado en el catálogo."
                    ),
                )
            ],
            confidence=0.9,
        )

    @staticmethod
    def _select_relevant_historical_insight(message: str, insights: list[dict]) -> dict | None:
        message_tokens = set(re.findall(r"[a-záéíóúñ]{3,}", message.lower()))
        normalized_message = message.lower()

        best_score = 0
        best_insight = None

        for insight in insights:
            name = str(insight.get("producto_actual") or "").lower()
            family = str(insight.get("familia_detectada") or "").lower()
            category = str(insight.get("categoria") or "").lower()
            tokens = set(re.findall(r"[a-záéíóúñ]{3,}", name))

            score = 0
            if family and family in normalized_message:
                score += 6
            if category and category in normalized_message:
                score += 2
            score += len(message_tokens.intersection(tokens)) * 3

            if score > best_score:
                best_score = score
                best_insight = insight

        if best_insight and best_score > 0:
            return best_insight

        return insights[0] if len(insights) == 1 else None

    @staticmethod
    def _build_quantity_review_response(analysis: dict, productos: list[dict]) -> ListChatAIResponse:
        high_quantity = analysis.get("productos_con_cantidad_alta", [])
        top_products = analysis.get("productos_mayor_peso_coste", [])
        suggestions: list[ListChatSuggestion] = []

        if high_quantity:
            product = high_quantity[0]
            reply = (
                f"Revisaría primero la cantidad de {product.get('nombre')}: tienes "
                f"{ListChatbotAIService._plural(product.get('cantidad'), 'unidad', 'unidades')}, con un subtotal de "
                f"{ListChatbotAIService._format_money(product.get('precio_estimado', 0))}. "
                "No significa que esté mal, pero es el candidato más claro para comprobar si la cantidad encaja con el uso real."
            )
            suggestions.append(
                ListChatSuggestion(
                    type="quantity",
                    title="Cantidad a revisar",
                    description=(
                        f"{product.get('nombre')} aparece con {ListChatbotAIService._plural(product.get('cantidad'), 'unidad', 'unidades')}. "
                        "Valida si es para una compra puntual o para varios días."
                    ),
                )
            )
            return ListChatAIResponse(
                intent="recomendar_cantidad",
                reply=reply,
                suggestions=suggestions,
                confidence=0.88,
            )

        sweet_count = ListChatbotAIService._count_sweet_products(productos)
        if sweet_count >= 2:
            reply = (
                "No veo una cantidad claramente excesiva solo por número de unidades, pero sí veo la lista bastante "
                f"concentrada en bollería/dulces: {ListChatbotAIService._plural(sweet_count, 'producto', 'productos')} de ese tipo. "
                "Si la lista es para desayuno o merienda, tiene sentido; si es una compra general, la equilibraría."
            )
            suggestions.append(
                ListChatSuggestion(
                    type="warning",
                    title="Revisar equilibrio de la lista",
                    description=(
                        f"Hay {ListChatbotAIService._plural(sweet_count, 'producto', 'productos')} de bollería, galletas o chocolate. "
                        "La cantidad no parece excesiva, pero la variedad está muy concentrada."
                    ),
                )
            )
            return ListChatAIResponse(
                intent="recomendar_cantidad",
                reply=reply,
                suggestions=suggestions,
                confidence=0.84,
            )

        if top_products:
            top = top_products[0]
            reply = (
                "No veo cantidades claramente problemáticas. Si quieres revisar algo, empezaría por "
                f"{top.get('nombre')}, porque es el producto que más pesa en el coste: "
                f"{ListChatbotAIService._format_money(top.get('precio_estimado', 0))}."
            )
            suggestions.append(
                ListChatSuggestion(
                    type="info",
                    title="Sin exceso claro",
                    description="No hay cantidades altas evidentes; revisa primero los productos con mayor impacto en el total.",
                )
            )
            return ListChatAIResponse(
                intent="recomendar_cantidad",
                reply=reply,
                suggestions=suggestions,
                confidence=0.8,
            )

        return ListChatAIResponse(
            intent="recomendar_cantidad",
            reply="No veo productos suficientes en la lista para recomendar cambios de cantidad.",
            suggestions=[],
            confidence=0.68,
        )

    @staticmethod
    def _build_quantity_response(message: str, productos: list[dict]) -> ListChatAIResponse:
        people = ListChatbotAIService._extract_people_count(message)
        product_hint = ListChatbotAIService._detect_food_from_message(message)

        if product_hint and people:
            amount_text = ListChatbotAIService._quantity_rule(product_hint, people)
            return ListChatAIResponse(
                intent="recomendar_cantidad",
                reply=amount_text,
                suggestions=[
                    ListChatSuggestion(
                        type="quantity",
                        title="Cantidad orientativa",
                        description="Ajusta la cantidad según si es plato principal, acompañamiento o si queréis repetir.",
                    )
                ],
                confidence=0.86,
            )

        if productos:
            relevant = ListChatbotAIService._find_relevant_product_in_list(message, productos)
            if relevant:
                return ListChatAIResponse(
                    intent="recomendar_cantidad",
                    reply=(
                        f"En tu lista tienes {ListChatbotAIService._plural(relevant.get('cantidad'), 'unidad', 'unidades')} de {relevant.get('nombre')}. "
                        "Para ajustar mejor la cantidad, dime para cuántas personas o comidas es."
                    ),
                    suggestions=[
                        ListChatSuggestion(
                            type="quantity",
                            title="Falta número de personas",
                            description="Indica para cuántas personas es la compra para poder afinar la recomendación.",
                        )
                    ],
                    confidence=0.78,
                )

        return ListChatAIResponse(
            intent="recomendar_cantidad",
            reply=(
                "Como referencia rápida: pasta o arroz seco, 80-100 g por persona; carne o pescado, "
                "150-200 g por persona; verduras de guarnición, 200-300 g por persona. "
                "Si me dices el producto y las personas, lo ajusto mejor."
            ),
            suggestions=[
                ListChatSuggestion(
                    type="quantity",
                    title="Regla básica",
                    description="Usa 80-100 g de pasta/arroz seco por persona como punto de partida.",
                )
            ],
            confidence=0.72,
        )

    @staticmethod
    def _build_excess_response(analysis: dict) -> ListChatAIResponse:
        high_quantity = analysis.get("productos_con_cantidad_alta", [])
        if high_quantity:
            product = high_quantity[0]
            return ListChatAIResponse(
                intent="detectar_excesos",
                reply=(
                    f"Revisaría la cantidad de {product.get('nombre')}: tienes {ListChatbotAIService._plural(product.get('cantidad'), 'unidad', 'unidades')}. "
                    "Si es para pocos días o para una sola comida, podría ser demasiado; si es compra semanal, puede tener sentido."
                ),
                suggestions=[
                    ListChatSuggestion(
                        type="warning",
                        title="Cantidad alta",
                        description=f"{product.get('nombre')} aparece con {ListChatbotAIService._plural(product.get('cantidad'), 'unidad', 'unidades')}.",
                    )
                ],
                confidence=0.8,
            )

        return ListChatAIResponse(
            intent="detectar_excesos",
            reply="No veo cantidades claramente excesivas en la lista con los datos actuales.",
            suggestions=[],
            confidence=0.7,
        )

    @staticmethod
    def _default_analysis_suggestions(
        analysis: dict,
        productos: list[dict] | None = None,
    ) -> list[ListChatSuggestion]:
        suggestions: list[ListChatSuggestion] = []

        candidates = analysis.get("candidatos_ahorro", [])
        if candidates:
            best = candidates[0]
            suggestions.append(
                ListChatSuggestion(
                    type="saving",
                    title="Revisar posible ahorro",
                    description=(
                        f"Hay una alternativa para {best.get('producto_original')} con ahorro estimado de "
                        f"{ListChatbotAIService._format_money(best.get('ahorro_estimado', 0))}. Comprueba equivalencia antes de sustituir."
                    ),
                )
            )

        high_quantity = analysis.get("productos_con_cantidad_alta", [])
        if high_quantity:
            product = high_quantity[0]
            suggestions.append(
                ListChatSuggestion(
                    type="warning",
                    title="Cantidad alta",
                    description=f"{product.get('nombre')} tiene {ListChatbotAIService._plural(product.get('cantidad'), 'unidad', 'unidades')}.",
                )
            )

        top_products = analysis.get("productos_mayor_peso_coste", [])
        if top_products:
            top = top_products[0]
            suggestions.append(
                ListChatSuggestion(
                    type="info",
                    title="Producto con más peso",
                    description=(
                        f"{top.get('nombre')} representa aproximadamente "
                        f"{ListChatbotAIService._format_percent(top.get('peso_en_total_porcentaje', 0))} del total de la lista."
                    ),
                )
            )

        if productos:
            sweet_count = ListChatbotAIService._count_sweet_products(productos)
            if sweet_count >= 2:
                suggestions.append(
                    ListChatSuggestion(
                        type="warning",
                        title="Lista concentrada en dulces",
                        description=(
                            f"Hay {ListChatbotAIService._plural(sweet_count, 'producto', 'productos')} de bollería, galletas o chocolate. "
                            "Si es una compra general, podrías equilibrarla con otros básicos."
                        ),
                    )
                )

        return suggestions[:3]

    @staticmethod
    def _build_default_suggestion(user_message: str, list_context: dict) -> ListChatSuggestion | None:
        analysis = list_context.get("analisis_precalculado", {})
        suggestions = ListChatbotAIService._default_analysis_suggestions(analysis, list_context.get("productos", []))
        return suggestions[0] if suggestions else None

    @staticmethod
    def _count_sweet_products(productos: list[dict]) -> int:
        keywords = [
            "croissant",
            "napolitana",
            "galleta",
            "cacao",
            "chocolate",
            "bolleria",
            "bollería",
            "dulce",
            "crema",
            "avellana",
        ]
        count = 0
        for product in productos:
            name = str(product.get("nombre", "")).lower()
            category = str(product.get("categoria", "")).lower()
            if any(keyword in name or keyword in category for keyword in keywords):
                count += 1
        return count

    @staticmethod
    def _parse_ai_json(raw_content: str) -> dict[str, Any]:
        try:
            return json.loads(raw_content)
        except json.JSONDecodeError:
            return ListChatbotAIService._extract_json_object(raw_content)

    @staticmethod
    def _extract_json_object(raw_content: str) -> dict[str, Any]:
        cleaned = raw_content.strip()
        cleaned = re.sub(r"^```json\s*", "", cleaned)
        cleaned = re.sub(r"^```\s*", "", cleaned)
        cleaned = re.sub(r"\s*```$", "", cleaned)

        start = cleaned.find("{")
        end = cleaned.rfind("}")
        if start == -1 or end == -1 or end <= start:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="La IA local no devolvió un JSON válido.",
            )

        try:
            return json.loads(cleaned[start : end + 1])
        except json.JSONDecodeError as exc:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="La IA local devolvió texto, pero no se pudo convertir a JSON.",
            ) from exc

    @staticmethod
    def _extract_people_count(message: str) -> int | None:
        match = re.search(r"(?:para|somos)\s+(\d+)\s*(?:personas|persona)?", message)
        if match:
            return int(match.group(1))
        match = re.search(r"\b(\d+)\s*(?:personas|persona)\b", message)
        return int(match.group(1)) if match else None

    @staticmethod
    def _detect_food_from_message(message: str) -> str | None:
        food_keywords = [
            "pasta",
            "macarrones",
            "espaguetis",
            "arroz",
            "pollo",
            "carne",
            "pescado",
            "patata",
            "verdura",
            "leche",
        ]
        for keyword in food_keywords:
            if keyword in message:
                return keyword
        return None

    @staticmethod
    def _quantity_rule(food: str, people: int) -> str:
        if food in {"pasta", "macarrones", "espaguetis"}:
            low, high, unit = 80 * people, 100 * people, "g de pasta seca"
        elif food == "arroz":
            low, high, unit = 70 * people, 90 * people, "g de arroz seco"
        elif food == "pollo":
            low, high, unit = 150 * people, 200 * people, "g de pollo"
        elif food in {"carne", "pescado"}:
            low, high, unit = 150 * people, 200 * people, f"g de {food}"
        elif food == "patata":
            low, high, unit = 200 * people, 300 * people, "g de patata"
        elif food == "verdura":
            low, high, unit = 200 * people, 300 * people, "g de verdura"
        elif food == "leche":
            low, high, unit = 200 * people, 250 * people, "ml de leche"
        else:
            low, high, unit = people, people, "ración por persona"

        return (
            f"Para {ListChatbotAIService._plural(people, 'persona', 'personas')}, compraría aproximadamente entre {low} y {high} {unit}. "
            "Tira hacia el extremo alto si es plato principal o si queréis repetir."
        )

    @staticmethod
    def _find_relevant_product_in_list(message: str, productos: list[dict]) -> dict | None:
        message_tokens = set(re.findall(r"[a-záéíóúñ]{4,}", message.lower()))
        if not message_tokens:
            return None

        for product in productos:
            name = str(product.get("nombre", "")).lower()
            if any(token in name for token in message_tokens):
                return product
        return None

    @staticmethod
    def _format_quantity(value: Any) -> str:
        number = ListChatbotAIService._to_float(value)
        if abs(number - round(number)) < 0.01:
            return str(int(round(number)))
        return f"{number:.2f}".replace(".", ",")

    @staticmethod
    def _format_money(value: Any) -> str:
        amount = ListChatbotAIService._to_float(value)
        return f"{amount:.2f}".replace(".", ",") + " €"

    @staticmethod
    def _format_percent(value: Any) -> str:
        percent = ListChatbotAIService._to_float(value)
        return f"{percent:.1f}".replace(".", ",") + " %"

    @staticmethod
    def _plural(value: Any, singular: str, plural: str) -> str:
        try:
            number = int(value or 0)
        except (TypeError, ValueError):
            number = 0
        word = singular if number == 1 else plural
        return f"{number} {word}"

    @staticmethod
    def _to_float(value: Any) -> float:
        try:
            return float(Decimal(str(value or 0)))
        except Exception:
            return 0.0
