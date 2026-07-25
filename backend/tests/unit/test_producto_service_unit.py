from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import patch

import pytest
from fastapi import HTTPException

from app.schemas.producto import ProductoCreate, ProductoUpdate
from app.services.producto_service import ProductoService


def _create_data():
    return ProductoCreate(
        nombre="Leche entera",
        marca="Hacendado",
        categoria="Lácteos",
        supermercado="Mercadona",
        precio_unitario=Decimal("1.20"),
        unidad_medida="1 L",
    )


def test_create_producto_construye_modelo_y_delega(db):
    created = object()
    with (
        patch("app.services.producto_service.Producto") as model,
        patch("app.services.producto_service.ProductoRepository.create", return_value=created) as create_mock,
    ):
        model.return_value = object()
        result = ProductoService.create_producto(db, _create_data())

    assert result is created
    model.assert_called_once_with(
        nombre="Leche entera",
        marca="Hacendado",
        categoria="Lácteos",
        supermercado="Mercadona",
        precio_unitario=Decimal("1.20"),
        unidad_medida="1 L",
    )
    create_mock.assert_called_once_with(db, model.return_value)


def test_get_producto_by_id_rechaza_inexistente(db):
    with patch("app.services.producto_service.ProductoRepository.get_by_id", return_value=None):
        with pytest.raises(HTTPException) as exc:
            ProductoService.get_producto_by_id(db, 1)
    assert exc.value.status_code == 404


def test_update_producto_solo_cambia_campos_enviados(db):
    product = SimpleNamespace(nombre="Leche", precio_unitario=Decimal("1.20"), marca="X")
    with (
        patch("app.services.producto_service.ProductoRepository.get_by_id", return_value=product),
        patch("app.services.producto_service.ProductoRepository.update", return_value=product),
    ):
        result = ProductoService.update_producto(
            db, 1, ProductoUpdate(precio_unitario=Decimal("1.35"))
        )
    assert result.precio_unitario == Decimal("1.35")
    assert result.nombre == "Leche"
    assert result.marca == "X"


def test_search_productos_rechaza_orden_invalido(db):
    with pytest.raises(HTTPException) as exc:
        ProductoService.search_productos(db, orden_precio="barato")
    assert exc.value.status_code == 400


def test_search_productos_delega_filtros(db):
    expected = [object()]
    with patch("app.services.producto_service.ProductoRepository.search", return_value=expected) as search:
        result = ProductoService.search_productos(
            db,
            nombre="leche",
            categoria="Lácteos",
            supermercado="DIA",
            marca="Puleva",
            orden_precio="asc",
        )
    assert result is expected
    search.assert_called_once_with(
        db,
        nombre="leche",
        categoria="Lácteos",
        supermercado="DIA",
        marca="Puleva",
        orden_precio="asc",
    )


def test_comparar_productos_requiere_nombre(db):
    with pytest.raises(HTTPException) as exc:
        ProductoService.comparar_productos(db, "   ")
    assert exc.value.status_code == 400
