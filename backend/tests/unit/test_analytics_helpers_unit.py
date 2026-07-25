from datetime import datetime
from decimal import Decimal
from types import SimpleNamespace

import pytest

from app.services.analytics_service import AnalyticsService


def test_month_bounds_mes_normal():
    assert AnalyticsService._month_bounds(2026, 7) == (
        datetime(2026, 7, 1),
        datetime(2026, 8, 1),
    )


def test_month_bounds_diciembre_cambia_de_ano():
    assert AnalyticsService._month_bounds(2026, 12) == (
        datetime(2026, 12, 1),
        datetime(2027, 1, 1),
    )


def test_previous_month_bounds_enero():
    assert AnalyticsService._previous_month_bounds(2026, 1) == (
        datetime(2025, 12, 1),
        datetime(2026, 1, 1),
    )


@pytest.mark.parametrize(
    ("value", "expected"),
    [(None, Decimal("0")), ("abc", Decimal("0")), ("1.25", Decimal("1.25"))],
)
def test_to_decimal(value, expected):
    assert AnalyticsService._to_decimal(value) == expected


def test_main_supermarket_elige_mayor_gasto():
    products = [
        SimpleNamespace(supermercado="DIA", precio_estimado=Decimal("2")),
        SimpleNamespace(supermercado="Mercadona", precio_estimado=Decimal("5")),
        SimpleNamespace(supermercado="DIA", precio_estimado=Decimal("1")),
    ]
    assert AnalyticsService._main_supermarket(products) == "Mercadona"


def test_average_days_between_purchases():
    histories = [
        SimpleNamespace(fecha=datetime(2026, 1, 11)),
        SimpleNamespace(fecha=datetime(2026, 1, 1)),
        SimpleNamespace(fecha=datetime(2026, 1, 6)),
    ]
    assert AnalyticsService._average_days_between_purchases(histories) == 5.0


@pytest.mark.parametrize(
    ("days", "fragment"),
    [
        (None, "no hay compras suficientes"),
        (1, "diaria"),
        (5, "cada 5 días"),
        (14, "quincenal"),
        (30, "mensual"),
    ],
)
def test_format_purchase_frequency(days, fragment):
    assert fragment in AnalyticsService._format_purchase_frequency(days)


def test_hour_range_agrupa_en_bloques_de_dos_horas():
    assert AnalyticsService._hour_range(17) == "16:00 – 18:00"
    assert AnalyticsService._hour_range(0) == "00:00 – 02:00"


def test_normalize_list_name_elimina_prefijo_copia():
    assert AnalyticsService._normalize_list_name("  Copia de   Compra semanal ") == "Compra semanal"


def test_normalize_y_keywords():
    assert AnalyticsService._normalize("Café, LECHE y pan") == "cafe leche y pan"
    assert AnalyticsService._keywords("Leche entera de Mercadona") == {"leche", "entera"}


@pytest.mark.parametrize(
    ("text", "family"),
    [
        ("Pechugas de pollo", "pollo"),
        ("Macarrones integrales", "pasta"),
        ("Leche semidesnatada", "leche"),
        ("Producto desconocido", None),
    ],
)
def test_detect_product_family(text, family):
    assert AnalyticsService._detect_product_family(text) == family


def test_filter_relevant_history_products_prioriza_familia():
    milk = SimpleNamespace(nombre_producto="Leche entera", categoria="Lácteos")
    coffee = SimpleNamespace(nombre_producto="Café molido", categoria="Desayuno")
    result = AnalyticsService._filter_relevant_history_products(
        product_name="Leche semidesnatada",
        category="Lácteos",
        family="leche",
        history_products=[milk, coffee],
    )
    assert result == [milk]
