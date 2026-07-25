import json
from datetime import datetime
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from fastapi import HTTPException

from app.services.admin_service import AdminService
import app.services.admin_service as admin_module


def test_build_request_headers_html_y_json(monkeypatch):
    monkeypatch.setattr(admin_module.settings, "scraping_user_agent", "LIA-UA")
    html = AdminService._build_request_headers("https://example.com/path")
    api = AdminService._build_request_headers("https://example.com/api", json_preferred=True)
    assert html["Origin"] == "https://example.com"
    assert "text/html" in html["Accept"]
    assert api["Accept"].startswith("application/json")


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("1,25 €", 1.25),
        ("1.234,56", 1234.56),
        ("1,234.56", 1234.56),
        ("0", None),
        ("gratis", None),
        (None, None),
    ],
)
def test_parse_price(raw, expected):
    assert AdminService._parse_price(raw) == expected


def test_validate_estado():
    assert AdminService._validate_estado(" ACTIVO ") == "activo"
    with pytest.raises(HTTPException):
        AdminService._validate_estado("pendiente")


def test_get_role(monkeypatch):
    role = SimpleNamespace(nombre="usuario")
    monkeypatch.setattr(admin_module.RoleRepository, "get_by_name", MagicMock(return_value=role))
    assert AdminService._get_role_or_404(MagicMock(), " USUARIO ") is role

    monkeypatch.setattr(admin_module.RoleRepository, "get_by_name", MagicMock(return_value=None))
    with pytest.raises(HTTPException):
        AdminService._get_role_or_404(MagicMock(), "fantasma")


def test_map_user():
    user = SimpleNamespace(
        id_usuario=1,
        nombre_usuario="juan",
        nombre_completo="Juan",
        email="juan@example.com",
        telefono=None,
        estado="activo",
        rol_id=2,
        rol=SimpleNamespace(nombre="usuario"),
        fecha_registro=datetime(2026, 1, 1),
    )
    mapped = AdminService._map_user(user)
    assert mapped.rol_nombre == "usuario"
    assert mapped.email == "juan@example.com"


def test_default_sources():
    sources = AdminService._build_default_sources()
    names = {item["supermercado"] for item in sources}
    assert {"DIA", "Mercadona", "Carrefour", "ALDI", "Alcampo"} <= names


def test_configured_sources_valido(monkeypatch):
    raw = json.dumps([
        {"supermercado": "Prueba", "url": "https://example.com", "crawl_internal_links": False}
    ])
    monkeypatch.setattr(admin_module.settings, "scraping_sources_json", raw)
    sources = AdminService._get_configured_sources()
    assert sources[0]["urls"] == ["https://example.com"]
    assert sources[0]["crawl_internal_links"] is False


@pytest.mark.parametrize("raw", ["{}", "no json", '[{"foo":"bar"}]'])
def test_configured_sources_invalido_usa_default(monkeypatch, raw):
    monkeypatch.setattr(admin_module.settings, "scraping_sources_json", raw)
    assert len(AdminService._get_configured_sources()) >= 5


def test_ensure_state_sources_loaded(monkeypatch):
    previous = AdminService._scraping_state
    AdminService._scraping_state = {
        "ultima_ejecucion_fecha": "-",
        "ultima_ejecucion_estado": "idle",
        "progreso_general": 0,
        "en_curso": False,
        "tiempo_restante_segundos": 0,
        "detalle_error": None,
        "cancel_requested": False,
        "fuentes": [],
    }
    monkeypatch.setattr(
        AdminService,
        "_get_configured_sources",
        MagicMock(return_value=[{"supermercado": "DIA", "urls": ["x"]}]),
    )
    try:
        AdminService._ensure_state_sources_loaded()
        assert AdminService._scraping_state["fuentes"][0]["supermercado"] == "DIA"
    finally:
        AdminService._scraping_state = previous


def test_extract_prices_selector_json_y_texto():
    html = """
    <div class='price'>1,25 €</div>
    <script>{"price": "2.50"}</script>
    """
    prices = AdminService._extract_prices(html, ".price", AdminService.DEFAULT_PRICE_REGEX)
    assert 1.25 in prices
    assert 2.5 in prices


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("  Café CON leche ", "café con leche"),
        (None, ""),
    ],
)
def test_normalize_product_text(text, expected):
    assert AdminService._normalize_product_text(text) == expected


def test_similarity():
    assert AdminService._similarity("Leche entera", "leche entera") == 1.0
    assert AdminService._similarity("", "leche") == 0.0


@pytest.mark.parametrize(
    ("name", "valid"),
    [
        ("Leche entera Hacendado", True),
        ("", False),
        ("precio", False),
        ("12,99 €", False),
    ],
)
def test_valid_scraped_name(name, valid):
    assert AdminService._is_valid_scraped_product_name(name) is valid


@pytest.mark.parametrize(
    ("price", "valid"),
    [(1.2, True), (2.5, True), ("2,50", False), (0, False), (-1, False), ("bad", False)],
)
def test_valid_scraped_price(price, valid):
    assert AdminService._is_valid_scraped_price(price) is valid
