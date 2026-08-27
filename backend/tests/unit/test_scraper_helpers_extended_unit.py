from decimal import Decimal
from types import SimpleNamespace

import json
import pytest
from bs4 import BeautifulSoup

from app.scraping.alcampo_scraper import AlcampoScraper
from app.scraping.aldi_scraper import AldiScraper
from app.scraping.carrefour_scraper import CarrefourScraper
from app.scraping.dia_scraper import DiaScraper
from app.scraping.mercadona_scraper import MercadonaScraper
from app.scraping.base import ScrapedProduct


@pytest.fixture
def scrapers():
    return {
        "alcampo": AlcampoScraper(user_agent="test"),
        "aldi": AldiScraper(user_agent="test"),
        "carrefour": CarrefourScraper(user_agent="test"),
        "dia": DiaScraper(user_agent="test"),
        "mercadona": MercadonaScraper(user_agent="test"),
    }


def test_carrefour_helpers(scrapers):
    s = scrapers["carrefour"]
    assert s._humanize_slug_name("leche-entera-1l") == "Leche entera 1l"
    assert s._format_brand("coca cola") == "Coca Cola"
    assert s._format_brand(None) is None
    assert s._guess_unit_from_name("Leche 1 l") == "L"
    assert s._first_non_empty(None, "", "valor") == "valor"
    assert s._absolute_url("/producto") == "https://www.carrefour.es/producto"


def test_carrefour_impressions_y_deduplicado(scrapers):
    s = scrapers["carrefour"]
    html = 'window["impressions"] = [{"name":"Leche","price":"1,20"}];'
    impressions = s._extract_impressions(html)
    assert impressions[0]["name"] == "Leche"

    p1 = ScrapedProduct("Leche", Decimal("1.20"), "Carrefour", external_id="1")
    p2 = ScrapedProduct("LECHE", Decimal("1.30"), "Carrefour", external_id="1")
    assert len(s._deduplicate_products([p1, p2])) == 1

def test_carrefour_pagination_urls(scrapers):
    s = scrapers["carrefour"]

    base_url = "https://www.carrefour.es/supermercado/bebidas/cat20003/c"

    assert s._build_page_url(base_url, page=1) == base_url
    assert s._build_page_url(base_url, page=2) == f"{base_url}?offset=24"
    assert s._build_page_url(base_url, page=3) == f"{base_url}?offset=48"
    assert s._build_page_url(base_url, page=5) == f"{base_url}?offset=96"


def test_carrefour_categoria_prioriza_url_controlada(scrapers):
    s = scrapers["carrefour"]

    html = """
    <html>
        <body>
            <h1>
                Comida y accesorios para mascotas online al mejor precio
            </h1>
        </body>
    </html>
    """

    url = (
        "https://www.carrefour.es/supermercado/"
        "mascotas/cat20007/c?offset=24"
    )

    assert (
        s._extract_category_from_html_or_url(
            html,
            url,
        )
        == "Mascotas"
    )


def test_carrefour_detecta_bloqueo_html(scrapers):
    s = scrapers["carrefour"]

    assert s._is_blocked_html(
        "<html><h1>Sorry, you have been blocked</h1></html>"
    )

    assert not s._is_blocked_html(
        "<html><h1>La Despensa</h1></html>"
    )

def test_dia_helpers(scrapers):
    s = scrapers["dia"]
    assert "page=2" in s._build_products_url("/leche/c/L1", page=2)
    assert s._category_name_from_path("/charcuteria-y-quesos/c/L1") == "Charcuteria Y Quesos"
    assert s._first_non_empty(None, "", "x") == "x"
    assert s._absolute_url("/producto") == "https://www.dia.es/producto"


def test_dia_extract_fields(scrapers):
    s = scrapers["dia"]
    item = {
        "brand": "DIA",
        "measure_unit": "kg",
        "display_name": "Arroz 1 kg",
        "product_id": "123",
    }
    assert s._extract_brand(item) == "DIA"
    assert s._extract_unit(item) == "kg"
    assert s._extract_external_id(item) == "123"


def test_mercadona_helpers(scrapers):
    s = scrapers["mercadona"]
    assert s._parse_int_id("12") == 12
    assert s._parse_int_id("x") is None
    assert s._unique_ids([2, 1, 2]) == [2, 1]
    assert s._first_non_empty(None, "", "x") == "x"
    assert s._looks_like_product({"id": 1, "display_name": "Leche"})
    assert not s._looks_like_product({"foo": "bar"})


def test_mercadona_extract_ids_recursivo(scrapers):
    s = scrapers["mercadona"]
    data = {"categories": [{"id": 1, "categories": [{"id": 2}]}]}
    ids = s._extract_category_ids(data)
    assert ids == [2]


def test_aldi_helpers(scrapers):
    s = scrapers["aldi"]
    assert s._is_article_link("/ofertas/leche.article.html")
    assert not s._is_article_link("/contacto")
    assert s._price_context("abc 1,20 € def", 4, 10)
    assert s._is_unit_price_context("1 kg = 2,00 €")
    assert s._has_discount_signal("precio anterior 3 €")
    assert s._external_id_from_url("https://aldi.es/foo/leche-12345-1-2.article.html") == "12345"
    assert s._absolute_url("/ofertas") == "https://www.aldi.es/ofertas"
    assert s._unique_urls(["a", "a", "b"]) == ["a", "b"]


def test_aldi_validity_y_format(scrapers):
    s = scrapers["aldi"]
    dates = s._extract_validity("Precios válidos del 01-07-2026 al 07-07-2026")
    assert dates == ("01-07-2026", "07-07-2026")
    assert s._guess_unit_from_name("Leche 1 l") == "L"

def test_aldi_extract_next_data_offers(scrapers):
    s = scrapers["aldi"]

    api_data = [
        [
            "OFFER_GET",
            {
                "req": {
                    "locale": "es",
                    "week": "current",
                    "region": "pen",
                },
                "res": {
                    "algoliaDataMap": {
                        "10001": {
                            "objectID": "10001",
                            "name": "Leche entera",
                            "isAvailable": True,
                            "currentPrice": {
                                "priceValue": 1.29,
                            },
                        },
                        "10002": {
                            "objectID": "10002",
                            "name": "Producto no disponible",
                            "isAvailable": False,
                            "currentPrice": {
                                "priceValue": 2.50,
                            },
                        },
                    }
                },
            },
        ],
        [
            "PAGE_MGNL_GET",
            {
                "req": {
                    "locale": "es",
                },
                "res": {},
            },
        ],
    ]

    next_data = {
        "props": {
            "pageProps": {
                "apiData": json.dumps(api_data),
            }
        }
    }

    html = (
        '<html><body>'
        '<script id="__NEXT_DATA__" type="application/json">'
        f'{json.dumps(next_data)}'
        '</script>'
        '</body></html>'
    )

    items = s._extract_offer_items(html)

    assert len(items) == 1
    assert items[0]["objectID"] == "10001"
    assert items[0]["name"] == "Leche entera"
    assert items[0]["currentPrice"]["priceValue"] == 1.29


def test_aldi_build_offer_product_y_deduplicado(scrapers):
    s = scrapers["aldi"]

    base_item = {
        "name": "Leche entera",
        "brandName": "MILSA®",
        "salesUnit": "1 l unidad",
        "isAvailable": True,
        "currentPrice": {
            "priceValue": 1.29,
        },
        "hierarchicalCategories": {
            "lvl0": ["Lácteos"],
        },
        "assets": [
            {
                "type": "primary",
                "url": "https://example.com/leche.jpg",
            }
        ],
        "promotionPrices": [
            {
                "validFromLocalDate": "2026-08-24",
                "validUntilLocalDate": "2026-08-30",
            }
        ],
        "productSlug": "leche-entera-10001",
        "objectID": "10001",
    }

    product_1 = s._build_product_from_offer_item(
        base_item,
        source_url="https://www.aldi.es/ofertas.html",
    )

    second_item = {
        **base_item,
        "objectID": "10002",
        "productSlug": "leche-entera-10002",
    }

    product_2 = s._build_product_from_offer_item(
        second_item,
        source_url="https://www.aldi.es/ofertas.html",
    )

    assert product_1.nombre == "Leche entera"
    assert product_1.precio == Decimal("1.29")
    assert product_1.marca == "MILSA"
    assert product_1.categoria == "Lácteos"
    assert product_1.formato == "1 l unidad"
    assert product_1.unidad_medida == "L"
    assert product_1.external_id == "10001"
    assert product_1.imagen_url == "https://example.com/leche.jpg"
    assert product_1.metadata["valid_from"] == "2026-08-24"
    assert product_1.metadata["valid_to"] == "2026-08-30"

    # Mismo nombre, pero IDs distintos: son productos distintos.
    assert len(
        s._deduplicate_products(
            [product_1, product_2]
        )
    ) == 2


def test_alcampo_helpers(scrapers):
    s = scrapers["alcampo"]
    assert s._normalize_brand("  Alcampo ") == "Alcampo"
    assert s._normalize_brand("") is None
    assert s._looks_like_unit_price_line("1,20 € por kilogramo")
    assert s._guess_unit_from_format("Botella 1 l") == "L"
    assert s._extract_external_id("https://example.com/product/ABC123") is not None
    assert s._absolute_url("/categories") == "https://www.compraonline.alcampo.es/categories"
    assert s._normalize_for_match("Café con leche") == "café con leche"


def test_alcampo_brand_clean_and_name(scrapers):
    s = scrapers["alcampo"]
    brand, name = s._extract_brand_and_clean_name("Alcampo Leche entera")
    assert name
    assert s._looks_like_product_name("Leche entera 1 litro")
    assert not s._looks_like_product_name("Precio")
