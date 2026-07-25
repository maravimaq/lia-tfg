from decimal import Decimal
from unittest.mock import MagicMock

import httpx
import pytest
from fastapi import HTTPException

from app.schemas.chat import ListChatAIResponse, ListChatSuggestion
from app.services.chatbot_ai_service import ListChatbotAIService
import app.services.chatbot_ai_service as ai_module


def response(reply="Una respuesta suficientemente extensa y útil para la lista.", suggestions=None, confidence=0.8):
    return ListChatAIResponse(
        intent="analizar_lista",
        reply=reply,
        suggestions=suggestions or [],
        confidence=confidence,
    )


def base_context():
    return {
        "lista": {"nombre_lista": "Compra", "total_estimado": 10},
        "productos": [
            {"nombre": "Chocolate", "categoria": "Dulces", "cantidad": 2},
            {"nombre": "Galletas", "categoria": "Dulces", "cantidad": 3},
        ],
        "analisis_precalculado": {
            "productos_mayor_peso_coste": [
                {"nombre": "Chocolate", "precio_estimado": 5, "peso_en_total_porcentaje": 50}
            ],
            "desglose_supermercados_actual": [{"supermercado": "DIA", "total": 10}],
            "productos_con_cantidad_alta": [{"nombre": "Galletas", "cantidad": 8}],
            "candidatos_ahorro": [
                {
                    "producto_original": "Chocolate",
                    "alternativa": "Chocolate barato",
                    "ahorro_estimado": 1.5,
                }
            ],
        },
    }


@pytest.mark.parametrize(
    "message",
    ["analiza la lista", "dónde es más barata", "cuánta leche", "revisa cantidades", "2 kg de pollo"],
)
def test_should_answer_deterministically(message):
    assert ListChatbotAIService._should_answer_deterministically(message, {})


def test_should_not_answer_deterministically():
    assert not ListChatbotAIService._should_answer_deterministically("hola, qué tal", {})


@pytest.mark.parametrize(
    ("message", "expected"),
    [
        ("revisa la cantidad en kg", True),
        ("revisa el precio", False),
        ("cuánta pasta", False),
    ],
)
def test_quantity_review(message, expected):
    assert ListChatbotAIService._is_quantity_review_request(message) is expected


def test_quantity_detectors():
    assert ListChatbotAIService._is_quantity_recommendation_request("cuánta pasta")
    assert ListChatbotAIService._is_quantity_or_amount_question("comprar 2 kg")
    assert not ListChatbotAIService._is_quantity_or_amount_question("hola")


def test_generate_response_mock(monkeypatch):
    monkeypatch.setattr(ai_module.settings, "ai_provider", "mock")
    result = ListChatbotAIService.generate_response(
        user_message="hola",
        list_context=base_context(),
    )
    assert result.reply


def test_generate_response_provider_invalido(monkeypatch):
    monkeypatch.setattr(ai_module.settings, "ai_provider", "desconocido")
    with pytest.raises(HTTPException) as exc:
        ListChatbotAIService.generate_response(user_message="hola", list_context={})
    assert exc.value.status_code == 500


def test_build_user_prompt_contiene_contexto():
    prompt = ListChatbotAIService._build_user_prompt("analiza", {"lista": {"total": 2}})
    assert "analiza" in prompt
    assert '"total": 2' in prompt


@pytest.mark.parametrize(
    "reply",
    [
        "Los productos son: leche",
        "La lista incluye varios productos",
        "El total estimado es el valor total",
    ],
)
def test_low_value_patterns(reply):
    assert ListChatbotAIService._is_low_value_response(response(reply=reply), "hola", {})


def test_low_value_analisis_sin_conclusion():
    assert ListChatbotAIService._is_low_value_response(
        response(reply="La lista contiene leche y pan y tiene diez euros."),
        "analiza mi lista",
        {},
    )


def test_weak_response():
    assert ListChatbotAIService._is_weak_response(
        response(reply="Muy breve", suggestions=[])
    )
    assert not ListChatbotAIService._is_weak_response(
        response(
            reply="Respuesta larga con información concreta y suficiente para que el usuario tome una decisión útil.",
            suggestions=[ListChatSuggestion(type="info", title="Dato", description="Descripción")],
        )
    )


def test_postprocess_anade_sugerencia():
    ai = response(suggestions=[], confidence=0.95)
    result = ListChatbotAIService._postprocess_response(
        ai_response=ai,
        user_message="hola",
        list_context=base_context(),
    )
    assert result.suggestions


def test_build_analysis_response():
    result = ListChatbotAIService._build_analysis_response(
        nombre_lista="Compra",
        total=10,
        productos=base_context()["productos"],
        analysis=base_context()["analisis_precalculado"],
    )
    assert "Compra" in result.reply
    assert "DIA" in result.reply
    assert result.suggestions


def test_supermarket_comparison_sin_equivalencias():
    result = ListChatbotAIService._build_supermarket_comparison_response({})
    assert result.intent == "comparar_lista_supermercados"
    assert result.suggestions[0].type == "warning"


def test_supermarket_comparison_con_ahorro():
    analysis = {
        "comparativa_por_producto": [
            {
                "tiene_ahorro": True,
                "producto_original": {
                    "nombre": "Leche", "cantidad": 2, "supermercado": "DIA",
                    "precio_unitario": 1.5, "subtotal": 3,
                },
                "mejor_alternativa_otro_supermercado": {
                    "nombre": "Leche fresca", "supermercado": "Mercadona",
                    "precio_unitario": 1, "ahorro_estimado": 1,
                },
            }
        ]
    }
    result = ListChatbotAIService._build_supermarket_comparison_response(analysis)
    assert "Leche" in result.reply
    assert result.suggestions[0].type == "saving"


def test_excess_response_con_y_sin_exceso():
    with_excess = ListChatbotAIService._build_excess_response(
        {"productos_con_cantidad_alta": [{"nombre": "Leche", "cantidad": 9}]}
    )
    without = ListChatbotAIService._build_excess_response({})
    assert "Leche" in with_excess.reply
    assert without.suggestions == []


def test_default_suggestions_maximo_tres():
    suggestions = ListChatbotAIService._default_analysis_suggestions(
        base_context()["analisis_precalculado"],
        base_context()["productos"],
    )
    assert 1 <= len(suggestions) <= 3


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ('{"intent":"analizar_lista"}', "analizar_lista"),
        ('```json\n{"intent":"analizar_lista"}\n```', "analizar_lista"),
        ('texto {"intent":"analizar_lista"} final', "analizar_lista"),
    ],
)
def test_parse_ai_json(raw, expected):
    assert ListChatbotAIService._parse_ai_json(raw)["intent"] == expected


@pytest.mark.parametrize("raw", ["sin json", "{mal}"])
def test_parse_ai_json_invalido(raw):
    with pytest.raises(HTTPException):
        ListChatbotAIService._parse_ai_json(raw)


@pytest.mark.parametrize(
    ("message", "expected"),
    [
        ("somos 4 personas", 4),
        ("para 2", 2),
        ("comida normal", None),
    ],
)
def test_extract_people_count(message, expected):
    assert ListChatbotAIService._extract_people_count(message) == expected


@pytest.mark.parametrize(
    ("message", "expected"),
    [
        ("quiero macarrones", "macarrones"),
        ("comprar pollo", "pollo"),
        ("comprar jabón", None),
    ],
)
def test_detect_food(message, expected):
    assert ListChatbotAIService._detect_food_from_message(message) == expected


@pytest.mark.parametrize("food", ["pasta", "arroz", "pollo", "carne", "pescado", "patata", "verdura", "leche", "otro"])
def test_quantity_rule(food):
    text = ListChatbotAIService._quantity_rule(food, 3)
    assert "3 personas" in text


def test_find_relevant_product():
    products = [{"nombre": "Leche entera"}, {"nombre": "Arroz redondo"}]
    assert ListChatbotAIService._find_relevant_product_in_list("cuánta leche compro", products)["nombre"] == "Leche entera"
    assert ListChatbotAIService._find_relevant_product_in_list("qué tal", products) is None


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (2, "2"),
        (2.5, "2,50"),
        ("bad", "0"),
    ],
)
def test_format_quantity(value, expected):
    assert ListChatbotAIService._format_quantity(value) == expected


def test_formatters():
    assert ListChatbotAIService._format_money(1.2) == "1,20 €"
    assert ListChatbotAIService._format_percent(12.34) == "12,3 %"
    assert ListChatbotAIService._plural(1, "producto", "productos") == "1 producto"
    assert ListChatbotAIService._plural(2, "producto", "productos") == "2 productos"
    assert ListChatbotAIService._to_float("bad") == 0.0
    assert ListChatbotAIService._count_sweet_products(base_context()["productos"]) == 2
