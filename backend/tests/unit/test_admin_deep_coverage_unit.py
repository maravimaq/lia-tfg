import json
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from app.services.admin_service import AdminService
import app.services.admin_service as admin_module


def test_fetch_url_reintenta_y_devuelve_respuesta(monkeypatch):
    bad = MagicMock()
    bad.raise_for_status.side_effect = RuntimeError("primer intento")
    good = MagicMock()
    good.raise_for_status.return_value = None
    get = MagicMock(side_effect=[bad, good])
    monkeypatch.setattr(admin_module.httpx, "get", get)

    result = AdminService._fetch_url("https://example.com/api/productos")

    assert result is good
    assert get.call_count == 2


def test_fetch_url_propaga_ultimo_error(monkeypatch):
    monkeypatch.setattr(
        admin_module.httpx,
        "get",
        MagicMock(side_effect=[RuntimeError("uno"), RuntimeError("dos")]),
    )
    with pytest.raises(RuntimeError, match="dos"):
        AdminService._fetch_url("https://example.com")


def test_extract_prices_from_pdf(monkeypatch):
    pages = [
        SimpleNamespace(extract_text=lambda: "Leche 1,25 € y pan 0,90 €"),
        SimpleNamespace(extract_text=lambda: None),
    ]
    monkeypatch.setattr(
        admin_module,
        "PdfReader",
        MagicMock(return_value=SimpleNamespace(pages=pages)),
    )
    assert AdminService._extract_prices_from_pdf(
        b"pdf", AdminService.DEFAULT_PRICE_REGEX
    ) == [1.25, 0.9]


def test_discover_internal_urls_filtra_host_regex_y_duplicados(monkeypatch):
    html = """
    <a href='/cat/leche'>Leche</a>
    <a href='/cat/leche?x=1'>Duplicado</a>
    <a href='/otro'>Otro</a>
    <a href='https://externo.test/cat/arroz'>Externo</a>
    <a href='mailto:a@example.com'>Correo</a>
    <a href='/cat/pan'>Pan</a>
    """
    monkeypatch.setattr(
        AdminService,
        "_fetch_url",
        MagicMock(return_value=SimpleNamespace(text=html)),
    )
    urls = AdminService._discover_internal_urls(
        "https://example.com/inicio", r"/cat/", max_urls=3
    )
    assert urls == [
        "https://example.com/inicio",
        "https://example.com/cat/leche",
        "https://example.com/cat/pan",
    ]


def test_discover_internal_urls_fallback(monkeypatch):
    monkeypatch.setattr(
        AdminService, "_fetch_url", MagicMock(side_effect=RuntimeError("red"))
    )
    assert AdminService._discover_internal_urls("https://example.com", None) == [
        "https://example.com"
    ]


def test_discover_mercadona_category_urls(monkeypatch):
    data = [
        {
            "id": 2,
            "categories": [
                {"id": 7, "categories": []},
                {"id": "8", "categories": []},
            ],
        }
    ]
    monkeypatch.setattr(
        AdminService,
        "_fetch_url",
        MagicMock(return_value=SimpleNamespace(json=lambda: data)),
    )
    urls = AdminService._discover_mercadona_category_urls(
        "https://tienda.mercadona.es"
    )
    assert "https://tienda.mercadona.es/api/categories/2" in urls
    assert "https://tienda.mercadona.es/api/categories/7" in urls
    assert all("/8" not in url for url in urls)


def test_discover_mercadona_fallbacks(monkeypatch):
    monkeypatch.setattr(
        AdminService, "_fetch_url", MagicMock(side_effect=RuntimeError("red"))
    )
    assert AdminService._discover_mercadona_category_urls("base") == ["base"]

    monkeypatch.setattr(
        AdminService,
        "_fetch_url",
        MagicMock(return_value=SimpleNamespace(json=lambda: {"id": 1})),
    )
    assert AdminService._discover_mercadona_category_urls("base") == ["base"]


def test_expand_source_urls_todas_las_ramas(monkeypatch):
    assert AdminService._expand_source_urls({"urls": []}) == []
    assert AdminService._expand_source_urls(
        {"urls": ["a"], "crawl_internal_links": False}
    ) == ["a"]

    monkeypatch.setattr(
        AdminService,
        "_discover_mercadona_category_urls",
        MagicMock(return_value=["m1", "comun"]),
    )
    monkeypatch.setattr(
        AdminService,
        "_discover_internal_urls",
        MagicMock(return_value=["i1", "comun"]),
    )
    result = AdminService._expand_source_urls(
        {
            "urls": ["https://tienda.mercadona.es", "https://example.com"],
            "crawl_internal_links": True,
            "link_include_regex": "/cat/",
        }
    )
    assert result == ["m1", "comun", "i1"]


def test_extract_json_candidates_varios_formatos():
    raw = '{"a": 1}'
    assert AdminService._extract_json_candidates_from_script(raw) == [raw]

    marked = 'window.__STATE__ = {"products": []};'
    assert AdminService._extract_json_candidates_from_script(marked) == [
        '{"products": []}'
    ]

    assert AdminService._extract_json_candidates_from_script("sin json") == []


def test_extract_product_prices_from_json_like_html():
    payload = [
        {
            "name": "Leche entera",
            "price": "1,20",
            "brand": {"name": "DIA"},
            "categories": [{"name": "Lácteos"}, "Frescos"],
            "unit": "L",
        },
        {
            "title": "Pan integral",
            "currentPrice": 0.95,
            "brand": "DIA",
            "category": "Panadería",
            "format": "500 g",
        },
        {
            "name": "Leche entera",
            "price": "1,30",
        },
    ]
    html = f"<script type='application/json'>{json.dumps(payload)}</script>"
    products = AdminService._extract_product_prices_from_json_like_html(html)

    by_name = {item["nombre"]: item for item in products}
    assert set(by_name) == {"Leche entera", "Pan integral"}
    assert by_name["Leche entera"]["precio"] == 1.3
    assert by_name["Pan integral"]["categoria"] == "Panadería"


def test_extract_product_prices_from_visible_html():
    html = """
    <article class='product-card'>
      <a href='/producto/leche'><img alt='Leche entera 1 L'></a>
      <span class='price'>1,25 €</span>
    </article>
    <article>
      <h3>Sin estructura válida</h3><span>2,00 €</span>
    </article>
    """
    products = AdminService._extract_product_prices_from_visible_html(
        html, AdminService.DEFAULT_PRICE_REGEX
    )
    assert products == [
        {
            "nombre": "Leche entera 1 L",
            "precio": 1.25,
            "marca": None,
            "categoria": None,
            "unidad_medida": "unidad",
        }
    ]


def _query_db(products):
    db = MagicMock()
    query = db.query.return_value
    query.filter.return_value.all.return_value = products
    return db


def test_find_existing_product_exacto_aproximado_y_sin_match():
    exact = SimpleNamespace(supermercado="DIA", nombre="Leche entera")
    other_store = SimpleNamespace(supermercado="Mercadona", nombre="Leche entera")
    db = _query_db([other_store, exact])
    assert AdminService._find_existing_product_for_upsert(
        db, "dia", "LECHE ENTERA"
    ) is exact

    similar = SimpleNamespace(supermercado="DIA", nombre="Leche entera fresca")
    db = _query_db([similar])
    assert AdminService._find_existing_product_for_upsert(
        db, "DIA", "Leche entera frescas", min_score=0.7
    ) is similar
    assert AdminService._find_existing_product_for_upsert(
        db, "DIA", "Arroz", min_score=0.99
    ) is None


def test_upsert_products_actualiza_crea_filtra_y_commit(monkeypatch):
    existing = SimpleNamespace(
        precio_unitario=1.0,
        fecha_actualizacion=None,
    )
    monkeypatch.setattr(
        AdminService,
        "_find_existing_product_for_upsert",
        MagicMock(side_effect=[existing, None]),
    )
    db = MagicMock()
    items = [
        {"nombre": "Leche entera", "precio": 1.25},
        {
            "nombre": "Pan integral",
            "precio": 0.95,
            "marca": "DIA",
            "categoria": "Panadería",
            "unidad_medida": "ud",
        },
        {"nombre": "precio", "precio": 3},
        {"nombre": "Producto sin precio", "precio": 0},
        {"nombre": "PAN INTEGRAL", "precio": 1.10},
    ]

    modified = AdminService._upsert_products_from_scraped_items(
        db, "DIA", items
    )

    assert modified == 2
    assert existing.precio_unitario == 1.25
    db.add.assert_called_once()
    created = db.add.call_args.args[0]
    assert created.nombre == "Pan integral"
    assert created.categoria == "Panadería"
    db.commit.assert_called_once()


def test_upsert_sin_elementos_validos_no_commit():
    db = MagicMock()
    assert AdminService._upsert_products_from_scraped_items(
        db, "DIA", [{"nombre": "precio", "precio": 0}]
    ) == 0
    db.commit.assert_not_called()
