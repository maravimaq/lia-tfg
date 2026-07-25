from decimal import Decimal

import pytest

from app.scraping.base import ScrapedProduct
from app.scraping.validators import (
    has_product_hint,
    validate_product_name,
    validate_product_price,
    validate_scraped_product,
)


@pytest.mark.parametrize(
    "name",
    [
        "Leche entera Hacendado 1 L",
        "Arroz redondo 1 kg",
        "Detergente líquido",
        "Pan de molde integral",
    ],
)
def test_validate_product_name_acepta_productos(name):
    assert validate_product_name(name) == (True, None)


@pytest.mark.parametrize(
    ("name", "reason_part"),
    [
        ("", "vacío"),
        ("ab", "corto"),
        ("Oferta", "blacklist"),
        ("Iniciar sesión", "texto no válido"),
        ("12,99 €", "precio"),
        ("1234 + 5", "números"),
        ("20 x 30 cm", "medida"),
        ("Dimensiones 20 x 30 cm", "empieza"),
    ],
)
def test_validate_product_name_rechaza_ruido(name, reason_part):
    valid, reason = validate_product_name(name)
    assert valid is False
    assert reason_part in reason


@pytest.mark.parametrize("price", [Decimal("0.01"), 1, "25.50", 999.99])
def test_validate_product_price_acepta_rango(price):
    assert validate_product_price(price) == (True, None)


@pytest.mark.parametrize(
    ("price", "reason"),
    [
        ("abc", "precio no numérico"),
        (0, "precio demasiado bajo"),
        (-1, "precio demasiado bajo"),
        (1000, "precio demasiado alto"),
    ],
)
def test_validate_product_price_rechaza_fuera_de_rango(price, reason):
    assert validate_product_price(price) == (False, reason)


def test_has_product_hint_detecta_palabras_de_producto():
    assert has_product_hint("caja de leche 20 x 30 cm") is True
    assert has_product_hint("estructura 20 x 30 cm") is False


def test_validate_scraped_product_valida_todo_el_objeto():
    valid = ScrapedProduct("Leche entera", Decimal("1.20"), "Mercadona")
    invalid = ScrapedProduct("Oferta", Decimal("1.20"), "Mercadona")

    assert validate_scraped_product(valid) == (True, None)
    is_valid, reason = validate_scraped_product(invalid)
    assert is_valid is False
    assert reason is not None
