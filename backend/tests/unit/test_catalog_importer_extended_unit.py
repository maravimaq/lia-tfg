from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import MagicMock

from app.scraping.base import ScrapedProduct
from app.scraping.catalog_importer import (
    CatalogImporter,
    CatalogImportResult,
    RejectedProduct,
)


def scraped(name="Leche entera", price="1.20", **kwargs):
    return ScrapedProduct(
        nombre=name,
        precio=Decimal(str(price)),
        supermercado=kwargs.pop("supermercado", "DIA"),
        **kwargs,
    )


def test_result_properties_and_dict():
    result = CatalogImportResult(
        supermercado="DIA",
        detected_count=4,
        created_count=2,
        updated_count=1,
        rejected_products=[RejectedProduct("Ruido", "DIA", "inválido")],
    )
    assert result.imported_count == 3
    data = result.to_dict()
    assert data["imported_count"] == 3
    assert data["rejected_products"][0]["reason"] == "inválido"


def test_validate_and_deduplicate():
    importer = CatalogImporter(MagicMock())
    result = CatalogImportResult(supermercado="DIA")
    products = [
        scraped(),
        scraped(name="LECHE ENTERA", price="1.30"),
        scraped(name="Oferta", price="2"),
    ]
    valid = importer._validate_and_deduplicate(products, result)
    assert len(valid) == 1
    assert result.valid_count == 1
    assert result.duplicated_count == 1
    assert result.rejected_count == 1
    assert result.rejected_products[0].nombre == "Oferta"


def test_load_existing_products_by_key():
    existing = SimpleNamespace(
        supermercado="DIA",
        nombre="Leche entera",
    )
    db = MagicMock()
    db.query.return_value.filter.return_value.all.return_value = [existing]
    importer = CatalogImporter(db)
    mapping = importer._load_existing_products_by_key([scraped()])
    assert mapping["dia::leche entera"] is existing

    assert importer._load_existing_products_by_key(
        [scraped(supermercado="")]
    ) == {}


def test_create_product():
    db = MagicMock()
    importer = CatalogImporter(db)
    product = importer._create_product(
        scraped(
            marca="DIA",
            categoria="Lácteos",
            unidad_medida="L",
            imagen_url="https://example.com/leche.jpg",
        )
    )
    assert product.nombre == "Leche entera"
    assert product.precio_unitario == Decimal("1.20")
    assert product.imagen_url == "https://example.com/leche.jpg"
    db.add.assert_called_once_with(product)


def test_update_product_changed_and_unchanged():
    importer = CatalogImporter(MagicMock())
    existing = SimpleNamespace(
        precio_unitario=Decimal("1.00"),
        marca=None,
        categoria="Sin categoría",
        unidad_medida=None,
        fecha_actualizacion=None,
        supermercado="DIA",
        nombre="Leche entera",
        imagen_url=None,
    )
    changed = importer._update_product_if_needed(
        existing,
        scraped(
            price="1.20",
            marca="DIA",
            categoria="Lácteos",
            unidad_medida="L",
            imagen_url="https://example.com/leche.jpg",
        ),
    )
    assert changed
    assert existing.precio_unitario == Decimal("1.20")
    assert existing.marca == "DIA"
    assert existing.imagen_url == "https://example.com/leche.jpg"
    assert existing.fecha_actualizacion is not None

    assert not importer._update_product_if_needed(
        existing,
        scraped(
            price="1.20",
            marca="DIA",
            categoria="Lácteos",
            unidad_medida="L",
            imagen_url="https://example.com/leche.jpg",
        ),
    )


def test_should_replace_text_and_decimal():
    assert not CatalogImporter._should_replace_text("actual", None)
    assert CatalogImporter._should_replace_text(None, "nuevo")
    assert not CatalogImporter._should_replace_text("igual", "igual")
    assert CatalogImporter._should_replace_text("uno", "dos")
    assert CatalogImporter._to_decimal("1.236") == Decimal("1.24")


def test_import_products_create_update_unchanged_and_commit():
    existing_changed = SimpleNamespace(
        supermercado="DIA",
        nombre="Leche entera",
        precio_unitario=Decimal("1.00"),
        marca=None,
        categoria=None,
        unidad_medida=None,
        fecha_actualizacion=None,
        imagen_url=None,
    )
    existing_same = SimpleNamespace(
        supermercado="DIA",
        nombre="Arroz redondo",
        precio_unitario=Decimal("1.50"),
        marca="DIA",
        categoria="Arroz",
        unidad_medida="kg",
        fecha_actualizacion=None,
        imagen_url=None,
    )
    db = MagicMock()
    db.query.return_value.filter.return_value.all.return_value = [
        existing_changed,
        existing_same,
    ]
    importer = CatalogImporter(db)

    result = importer.import_products(
        [
            scraped(price="1.20", marca="DIA"),
            scraped(
                name="Arroz redondo",
                price="1.50",
                marca="DIA",
                categoria="Arroz",
                unidad_medida="kg",
            ),
            scraped(name="Pan integral", price="0.95"),
        ],
        supermercado="DIA",
        commit=True,
    )

    assert result.updated_count == 1
    assert result.unchanged_count == 1
    assert result.created_count == 1
    assert result.imported_count == 2
    db.add.assert_called_once()
    db.commit.assert_called_once()


def test_import_products_sin_validos_commit_opcional():
    db = MagicMock()
    importer = CatalogImporter(db)
    result = importer.import_products(
        [scraped(name="Oferta", price="1")], commit=True
    )
    assert result.valid_count == 0
    db.commit.assert_called_once()

    db.reset_mock()
    importer.import_products([scraped(name="Oferta", price="1")], commit=False)
    db.commit.assert_not_called()
