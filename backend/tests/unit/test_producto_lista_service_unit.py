from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import patch

import pytest
from fastapi import HTTPException

from app.schemas.producto_lista import ProductoListaCreate, ProductoListaUpdate
from app.services.producto_lista_service import ProductoListaService


def _lista(owner_id=1, list_id=10):
    return SimpleNamespace(id_lista=list_id, usuario_id=owner_id, total_estimado=Decimal("0"))


def test_usuario_con_comparticion_edicion_puede_modificar(db, user):
    lista = _lista(owner_id=99)
    with patch(
        "app.services.producto_lista_service.ListaCompartidaRepository.get_by_lista_and_usuario",
        return_value=SimpleNamespace(tipo_compartido="edicion"),
    ):
        assert ProductoListaService._usuario_puede_modificar(db, lista, user) is True


def test_usuario_con_visualizacion_no_puede_modificar(db, user):
    lista = _lista(owner_id=99)
    with patch(
        "app.services.producto_lista_service.ListaCompartidaRepository.get_by_lista_and_usuario",
        return_value=SimpleNamespace(tipo_compartido="visualizacion"),
    ):
        assert ProductoListaService._usuario_puede_modificar(db, lista, user) is False


def test_create_producto_calcula_precio_estimado(db, user):
    lista = _lista(owner_id=user.id_usuario)
    catalog = SimpleNamespace(precio_unitario=Decimal("1.25"))
    data = ProductoListaCreate(lista_id=10, producto_id=7, cantidad=3)
    created = object()

    with (
        patch("app.services.producto_lista_service.ListaCompraRepository.get_by_id", return_value=lista),
        patch("app.services.producto_lista_service.HistorialListasRepository.get_by_lista_id", return_value=None),
        patch("app.services.producto_lista_service.ProductoRepository.get_by_id", return_value=catalog),
        patch("app.services.producto_lista_service.ProductoLista") as model,
        patch("app.services.producto_lista_service.ProductoListaRepository.create", return_value=created),
        patch("app.services.producto_lista_service.ProductoListaService._recalcular_total_lista") as recalc,
    ):
        model.return_value = object()
        result = ProductoListaService.create_producto(db, data, user)

    assert result is created
    model.assert_called_once_with(
        lista_id=10,
        producto_id=7,
        cantidad=3,
        precio_estimado=Decimal("3.75"),
    )
    recalc.assert_called_once_with(db, 10)


def test_create_producto_rechaza_lista_inexistente(db, user):
    with patch("app.services.producto_lista_service.ListaCompraRepository.get_by_id", return_value=None):
        with pytest.raises(HTTPException) as exc:
            ProductoListaService.create_producto(
                db,
                ProductoListaCreate(lista_id=10, producto_id=7, cantidad=1),
                user,
            )
    assert exc.value.status_code == 404


def test_create_producto_rechaza_catalogo_inexistente(db, user):
    lista = _lista(owner_id=user.id_usuario)
    with (
        patch("app.services.producto_lista_service.ListaCompraRepository.get_by_id", return_value=lista),
        patch("app.services.producto_lista_service.HistorialListasRepository.get_by_lista_id", return_value=None),
        patch("app.services.producto_lista_service.ProductoRepository.get_by_id", return_value=None),
    ):
        with pytest.raises(HTTPException) as exc:
            ProductoListaService.create_producto(
                db,
                ProductoListaCreate(lista_id=10, producto_id=7, cantidad=1),
                user,
            )
    assert exc.value.status_code == 404


def test_recalcular_total_suma_precios(db):
    lista = _lista()
    products = [
        SimpleNamespace(precio_estimado=Decimal("2.50")),
        SimpleNamespace(precio_estimado=Decimal("3.20")),
    ]
    with (
        patch("app.services.producto_lista_service.ListaCompraRepository.get_by_id", return_value=lista),
        patch("app.services.producto_lista_service.ProductoListaRepository.get_by_lista_id", return_value=products),
        patch("app.services.producto_lista_service.ListaCompraRepository.save") as save_mock,
    ):
        ProductoListaService._recalcular_total_lista(db, 10)

    assert lista.total_estimado == Decimal("5.70")
    save_mock.assert_called_once_with(db, lista)


def test_update_producto_recalcula_cantidad_y_precio(db, user):
    item = SimpleNamespace(
        id_producto_lista=2,
        lista_id=10,
        producto_id=7,
        cantidad=1,
        precio_estimado=Decimal("1.25"),
    )
    catalog = SimpleNamespace(precio_unitario=Decimal("1.25"))

    with (
        patch("app.services.producto_lista_service.ProductoListaService.get_producto_by_id", return_value=item),
        patch("app.services.producto_lista_service.ProductoListaService._validar_permiso_modificacion_producto"),
        patch("app.services.producto_lista_service.ProductoRepository.get_by_id", return_value=catalog),
        patch("app.services.producto_lista_service.ProductoListaRepository.save", return_value=item),
        patch("app.services.producto_lista_service.ProductoListaService._recalcular_total_lista") as recalc,
    ):
        result = ProductoListaService.update_producto(
            db, 2, ProductoListaUpdate(cantidad=4), user
        )

    assert result.cantidad == 4
    assert result.precio_estimado == Decimal("5.00")
    recalc.assert_called_once_with(db, 10)


def test_delete_producto_delega_y_recalcula(db, user):
    item = SimpleNamespace(lista_id=10)
    with (
        patch("app.services.producto_lista_service.ProductoListaService.get_producto_by_id", return_value=item),
        patch("app.services.producto_lista_service.ProductoListaService._validar_permiso_modificacion_producto"),
        patch("app.services.producto_lista_service.ProductoListaRepository.delete") as delete_mock,
        patch("app.services.producto_lista_service.ProductoListaService._recalcular_total_lista") as recalc,
    ):
        ProductoListaService.delete_producto(db, 2, user)

    delete_mock.assert_called_once_with(db, item)
    recalc.assert_called_once_with(db, 10)
