from types import SimpleNamespace
from unittest.mock import patch

import pytest
from fastapi import HTTPException

from app.schemas.lista_compra import ListaCompraCreate, ListaCompraUpdate
from app.services.lista_compra_service import ListaCompraService


def _lista(owner_id=1, list_id=10):
    return SimpleNamespace(
        id_lista=list_id,
        usuario_id=owner_id,
        nombre_lista="Compra semanal",
        compartida=False,
        tipo_compartido=None,
    )


def test_usuario_propietario_tiene_acceso_sin_consultar_comparticion(db, user):
    lista = _lista(owner_id=user.id_usuario)
    with patch("app.services.lista_compra_service.ListaCompartidaRepository.get_by_lista_and_usuario") as repo:
        assert ListaCompraService._usuario_tiene_acceso(db, lista, user) is True
    repo.assert_not_called()


def test_usuario_compartido_tiene_acceso(db, user):
    lista = _lista(owner_id=99)
    with patch(
        "app.services.lista_compra_service.ListaCompartidaRepository.get_by_lista_and_usuario",
        return_value=SimpleNamespace(tipo_compartido="visualizacion"),
    ):
        assert ListaCompraService._usuario_tiene_acceso(db, lista, user) is True


def test_create_lista_delega_en_repositorio(db, user):
    data = ListaCompraCreate(nombre_lista="Nueva", compartida=True)
    created = object()

    with (
        patch("app.services.lista_compra_service.ListaCompra") as model,
        patch("app.services.lista_compra_service.ListaCompraRepository.create", return_value=created) as create_mock,
    ):
        model.return_value = object()
        result = ListaCompraService.create_lista(db, data, user)

    assert result is created
    model.assert_called_once_with(
        nombre_lista="Nueva",
        compartida=True,
        usuario_id=user.id_usuario,
    )
    create_mock.assert_called_once_with(db, model.return_value)


def test_get_lista_by_id_rechaza_inexistente(db, user):
    with patch("app.services.lista_compra_service.ListaCompraRepository.get_by_id", return_value=None):
        with pytest.raises(HTTPException) as exc:
            ListaCompraService.get_lista_by_id(db, 10, user)
    assert exc.value.status_code == 404


def test_get_lista_by_id_rechaza_sin_acceso(db, user):
    lista = _lista(owner_id=99)
    with (
        patch("app.services.lista_compra_service.ListaCompraRepository.get_by_id", return_value=lista),
        patch("app.services.lista_compra_service.ListaCompartidaRepository.get_by_lista_and_usuario", return_value=None),
    ):
        with pytest.raises(HTTPException) as exc:
            ListaCompraService.get_lista_by_id(db, 10, user)
    assert exc.value.status_code == 403


def test_get_lista_by_id_inyecta_tipo_compartido(db, user):
    lista = _lista(owner_id=99)
    share = SimpleNamespace(tipo_compartido="edicion")
    with (
        patch("app.services.lista_compra_service.ListaCompraRepository.get_by_id", return_value=lista),
        patch("app.services.lista_compra_service.ListaCompartidaRepository.get_by_lista_and_usuario", return_value=share),
        patch("app.services.lista_compra_service.HistorialListasRepository.get_by_lista_id", return_value=None),
    ):
        result = ListaCompraService.get_lista_by_id(db, 10, user)
    assert result.tipo_compartido == "edicion"


def test_update_lista_solo_modifica_campos_enviados(db, user):
    lista = _lista(owner_id=user.id_usuario)
    data = ListaCompraUpdate(nombre_lista="Renombrada")

    with (
        patch("app.services.lista_compra_service.ListaCompraRepository.get_by_id", return_value=lista),
        patch("app.services.lista_compra_service.HistorialListasRepository.get_by_lista_id", return_value=None),
        patch("app.services.lista_compra_service.ListaCompraRepository.save", return_value=lista) as save_mock,
    ):
        result = ListaCompraService.update_lista(db, 10, data, user)

    assert result.nombre_lista == "Renombrada"
    assert result.compartida is False
    save_mock.assert_called_once_with(db, lista)


def test_update_lista_rechaza_usuario_no_propietario(db, user):
    with patch("app.services.lista_compra_service.ListaCompraRepository.get_by_id", return_value=_lista(owner_id=99)):
        with pytest.raises(HTTPException) as exc:
            ListaCompraService.update_lista(db, 10, ListaCompraUpdate(nombre_lista="X"), user)
    assert exc.value.status_code == 403


def test_validar_lista_no_finalizada_rechaza_historial_existente(db):
    with patch("app.services.lista_compra_service.HistorialListasRepository.get_by_lista_id", return_value=object()):
        with pytest.raises(HTTPException) as exc:
            ListaCompraService._validar_lista_no_finalizada(db, 10)
    assert exc.value.status_code == 400


def test_delete_lista_elimina_productos_antes_de_lista(db, user):
    lista = _lista(owner_id=user.id_usuario)
    products = [object(), object()]

    with (
        patch("app.services.lista_compra_service.ListaCompraRepository.get_by_id", return_value=lista),
        patch("app.services.lista_compra_service.HistorialListasRepository.get_by_lista_id", return_value=None),
        patch("app.services.lista_compra_service.ProductoListaRepository.get_by_lista_id", return_value=products),
        patch("app.services.lista_compra_service.ProductoListaRepository.delete") as delete_product,
        patch("app.services.lista_compra_service.ListaCompraRepository.delete") as delete_list,
    ):
        ListaCompraService.delete_lista(db, 10, user)

    assert delete_product.call_count == 2
    delete_list.assert_called_once_with(db, lista)
