from types import SimpleNamespace
from unittest.mock import patch

import pytest
from fastapi import HTTPException

from app.schemas.lista_compartida import CompartirListaRequest, TipoCompartido
from app.services.lista_compartida_service import ListaCompartidaService


def _lista(owner_id=1):
    return SimpleNamespace(id_lista=10, usuario_id=owner_id)


def test_compartir_lista_crea_comparticion(db, user):
    target = SimpleNamespace(id_usuario=2)
    data = CompartirListaRequest(
        email_usuario="marta@example.com",
        tipo_compartido=TipoCompartido.EDICION,
    )
    created = object()

    with (
        patch("app.services.lista_compartida_service.ListaCompraRepository.get_by_id", return_value=_lista(user.id_usuario)),
        patch("app.services.lista_compartida_service.HistorialListasRepository.get_by_lista_id", return_value=None),
        patch("app.services.lista_compartida_service.UserRepository.get_by_email", return_value=target),
        patch("app.services.lista_compartida_service.ListaCompartidaRepository.get_by_lista_and_usuario", return_value=None),
        patch("app.services.lista_compartida_service.ListaCompartida") as model,
        patch("app.services.lista_compartida_service.ListaCompartidaRepository.create", return_value=created),
    ):
        model.return_value = object()
        result = ListaCompartidaService.compartir_lista(db, 10, data, user)

    assert result is created
    model.assert_called_once_with(
        lista_id=10,
        usuario_id=2,
        tipo_compartido="edicion",
    )


@pytest.mark.parametrize(
    ("lista", "history", "target", "already_shared", "status"),
    [
        (None, None, None, None, 404),
        (_lista(99), None, None, None, 403),
        (_lista(1), object(), None, None, 400),
        (_lista(1), None, None, None, 404),
        (_lista(1), None, SimpleNamespace(id_usuario=1), None, 400),
        (_lista(1), None, SimpleNamespace(id_usuario=2), object(), 400),
    ],
)
def test_compartir_lista_rechaza_casos_invalidos(
    db, user, lista, history, target, already_shared, status
):
    data = CompartirListaRequest(email_usuario="marta@example.com")
    with (
        patch("app.services.lista_compartida_service.ListaCompraRepository.get_by_id", return_value=lista),
        patch("app.services.lista_compartida_service.HistorialListasRepository.get_by_lista_id", return_value=history),
        patch("app.services.lista_compartida_service.UserRepository.get_by_email", return_value=target),
        patch("app.services.lista_compartida_service.ListaCompartidaRepository.get_by_lista_and_usuario", return_value=already_shared),
    ):
        with pytest.raises(HTTPException) as exc:
            ListaCompartidaService.compartir_lista(db, 10, data, user)
    assert exc.value.status_code == status


def test_salir_de_lista_compartida_elimina_comparticion(db, user):
    share = object()
    with (
        patch("app.services.lista_compartida_service.ListaCompartidaRepository.get_by_lista_and_usuario", return_value=share),
        patch("app.services.lista_compartida_service.ListaCompartidaRepository.delete") as delete_mock,
    ):
        ListaCompartidaService.salir_de_lista_compartida(db, 10, user)
    delete_mock.assert_called_once_with(db, share)
