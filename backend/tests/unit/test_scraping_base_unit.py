from decimal import Decimal

import pytest

from app.scraping.base import (
    ScrapedProduct,
    ScraperRunResult,
    clean_optional_text,
    clean_text,
    normalize_for_matching,
    parse_price,
)


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        (None, ""),
        ("  leche   entera  ", "leche entera"),
        ("pan\xa0de\xa0molde", "pan de molde"),
        (123, "123"),
    ],
)
def test_clean_text(raw, expected):
    assert clean_text(raw) == expected


def test_clean_optional_text_convierte_vacio_en_none():
    assert clean_optional_text("   ") is None
    assert clean_optional_text("  DIA ") == "DIA"


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("Café con Leche", "cafe con leche"),
        ("  Jamón   50%  ", "jamon 50"),
        ("DÍA", "dia"),
    ],
)
def test_normalize_for_matching(raw, expected):
    assert normalize_for_matching(raw) == expected


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("1,25 €", Decimal("1.25")),
        ("1.234,56 €", Decimal("1234.56")),
        ("1,234.56 EUR", Decimal("1234.56")),
        (2, Decimal("2.00")),
        (Decimal("3.456"), Decimal("3.46")),
    ],
)
def test_parse_price_formatos_validos(raw, expected):
    assert parse_price(raw) == expected


@pytest.mark.parametrize("raw", [None, "", "gratis", 0, -1])
def test_parse_price_rechaza_valores_invalidos(raw):
    with pytest.raises(ValueError):
        parse_price(raw)


def test_scraped_product_limpia_y_normaliza_datos():
    product = ScrapedProduct(
        nombre="  Leche   Entera ",
        precio=Decimal("1.259"),
        supermercado="  Mercadona ",
        marca=" Hacendado ",
    )

    assert product.nombre == "Leche Entera"
    assert product.precio == Decimal("1.26")
    assert product.supermercado == "Mercadona"
    assert product.marca == "Hacendado"
    assert product.normalized_name == "leche entera"


def test_scraper_run_result_success_y_empty():
    product = ScrapedProduct("Leche", Decimal("1"), "DIA")

    success = ScraperRunResult.success("DIA", [product])
    empty = ScraperRunResult.success("DIA", [])

    assert success.status == "success"
    assert success.detected_count == 1
    assert success.accepted_count == 1
    assert empty.status == "empty"
