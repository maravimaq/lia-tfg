from decimal import Decimal
from types import SimpleNamespace

import pytest

from app.services.list_chatbot_service import ListChatbotService


def product(**kwargs):
    defaults = dict(
        id_producto=1,
        nombre="Leche entera",
        marca="Marca",
        categoria="Lácteos",
        supermercado="DIA",
        precio_unitario=Decimal("1.20"),
        unidad_medida="l",
    )
    defaults.update(kwargs)
    return SimpleNamespace(**defaults)


def test_build_search_terms_unicos_y_limitados():
    p = product(nombre="Leche entera fresca sin lactosa", categoria="Lácteos")
    terms = ListChatbotService._build_search_terms(p)
    assert terms[0] == "Lácteos"
    assert len(terms) <= 4
    assert len({x.lower() for x in terms}) == len(terms)


@pytest.mark.parametrize(
    ("text", "family"),
    [
        ("Galletas de chocolate", "galleta"),
        ("Pechugas de pollo", "pollo"),
        ("Aceite de oliva", "aceite"),
        ("Desconocido total", None),
    ],
)
def test_detect_family(text, family):
    assert ListChatbotService._detect_product_family(text) == family


def test_score_rechaza_familias_incompatibles():
    original = product(nombre="Galletas cacao", categoria="Dulces")
    alt = product(nombre="Helado cacao", categoria="Dulces", supermercado="Mercadona")
    assert ListChatbotService._score_product_alternative(original, alt) == 0


def test_score_acepta_misma_familia_otro_supermercado():
    original = product(nombre="Leche entera", categoria="Lácteos", supermercado="DIA")
    alt = product(
        nombre="Leche entera fresca",
        categoria="Lácteos",
        supermercado="Mercadona",
    )
    assert ListChatbotService._score_product_alternative(original, alt) > 0
    assert ListChatbotService._is_reasonable_alternative(original, alt)


def test_score_sin_tokens_es_cero():
    assert ListChatbotService._score_product_alternative(
        product(nombre="de la"),
        product(nombre="y con"),
    ) == 0


def test_alternative_to_context_calcula_ahorro():
    alt = product(precio_unitario=Decimal("1.00"))
    context = ListChatbotService._alternative_to_context(
        alt,
        original_price=Decimal("1.50"),
        quantity=3,
    )
    assert context["subtotal_estimado_misma_cantidad"] == 3.0
    assert context["ahorro_estimado_misma_cantidad"] == 1.5


def test_keywords_stopwords_y_normalizacion():
    assert ListChatbotService._normalize("  Café, CON leche ") == "cafe con leche"
    assert ListChatbotService._keywords("Leche de Mercadona entera") == ["leche", "entera"]


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (None, Decimal("0")),
        ("bad", Decimal("0")),
        ("1.25", Decimal("1.25")),
    ],
)
def test_to_decimal(value, expected):
    assert ListChatbotService._to_decimal(value) == expected


def test_percentage():
    assert ListChatbotService._percentage(Decimal("2"), Decimal("8")) == 25.0
    assert ListChatbotService._percentage(Decimal("2"), Decimal("0")) == 0.0
