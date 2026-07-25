from types import SimpleNamespace
from unittest.mock import patch

import pytest
from fastapi import HTTPException

from app.schemas.preferences import PreferenciasUpdate
from app.schemas.user import ChangePasswordRequest, UserUpdate
from app.services.user_service import UserService


def test_update_profile_guarda_y_revoca_si_cambia_email(db, user):
    data = UserUpdate(email="nuevo@example.com", nombre_completo="Juan Nuevo")
    with (
        patch("app.services.user_service.UserRepository.get_by_email", return_value=None),
        patch("app.services.user_service.UserRepository.save", return_value=user) as save_mock,
        patch("app.services.user_service.SessionRepository.revoke_all_user_sessions") as revoke_mock,
    ):
        result = UserService.update_profile(db, user, data)

    assert result.email == "nuevo@example.com"
    assert result.nombre_completo == "Juan Nuevo"
    save_mock.assert_called_once_with(db, user)
    revoke_mock.assert_called_once_with(db, user.id_usuario)


def test_update_profile_rechaza_email_duplicado(db, user):
    with patch("app.services.user_service.UserRepository.get_by_email", return_value=object()):
        with pytest.raises(HTTPException) as exc:
            UserService.update_profile(db, user, UserUpdate(email="otro@example.com"))
    assert exc.value.status_code == 400


def test_change_password_verifica_hashea_guarda_y_revoca(db, user):
    data = ChangePasswordRequest(
        contrasena_actual="actual",
        nueva_contrasena="nueva-segura",
    )
    with (
        patch("app.services.user_service.verify_password", return_value=True),
        patch("app.services.user_service.hash_password", return_value="NUEVO_HASH"),
        patch("app.services.user_service.UserRepository.save") as save_mock,
        patch("app.services.user_service.SessionRepository.revoke_all_user_sessions") as revoke_mock,
    ):
        result = UserService.change_password(db, user, data)

    assert user.contrasena == "NUEVO_HASH"
    save_mock.assert_called_once_with(db, user)
    revoke_mock.assert_called_once_with(db, user.id_usuario)
    assert "actualizada" in result["message"]


def test_change_password_rechaza_clave_actual_incorrecta(db, user):
    data = ChangePasswordRequest(
        contrasena_actual="mal",
        nueva_contrasena="nueva-segura",
    )
    with patch("app.services.user_service.verify_password", return_value=False):
        with pytest.raises(HTTPException) as exc:
            UserService.change_password(db, user, data)
    assert exc.value.status_code == 400


def test_update_preferences_solo_cambia_campos_presentes(db, user):
    prefs = SimpleNamespace(
        idioma="es",
        modo_oscuro=False,
        notificaciones=True,
        unidad_peso="kg",
        unidad_precio="EUR",
        supermercado_favorito=None,
    )
    data = PreferenciasUpdate(modo_oscuro=True, supermercado_favorito="DIA")

    with (
        patch("app.services.user_service.PreferencesRepository.get_or_create_by_user_id", return_value=prefs),
        patch("app.services.user_service.PreferencesRepository.save", return_value=prefs) as save_mock,
    ):
        result = UserService.update_preferences(db, user, data)

    assert result.modo_oscuro is True
    assert result.supermercado_favorito == "DIA"
    assert result.idioma == "es"
    save_mock.assert_called_once_with(db, prefs)


def test_request_follow_rechaza_seguirse_a_si_mismo(db, user):
    with pytest.raises(HTTPException) as exc:
        UserService.request_follow(db, user, user.id_usuario)
    assert exc.value.status_code == 400


def test_request_follow_crea_solicitud(db, user):
    target = SimpleNamespace(id_usuario=2)
    created = object()
    with (
        patch("app.services.user_service.UserRepository.get_by_id", return_value=target),
        patch("app.services.user_service.FollowRepository.get_follow", return_value=None),
        patch("app.services.user_service.FollowRepository.get_request_between", return_value=None),
        patch("app.services.user_service.SolicitudSeguimiento") as model,
        patch("app.services.user_service.FollowRepository.create_request", return_value=created),
    ):
        model.return_value = object()
        result = UserService.request_follow(db, user, 2)

    assert result is created
    model.assert_called_once_with(
        solicitante_id=user.id_usuario,
        destinatario_id=2,
        estado="pendiente",
    )


def test_respond_follow_request_rechaza_usuario_ajeno(db, user):
    request = SimpleNamespace(destinatario_id=99)
    action = SimpleNamespace(accion="aceptar")
    with patch("app.services.user_service.FollowRepository.get_request_by_id", return_value=request):
        with pytest.raises(HTTPException) as exc:
            UserService.respond_follow_request(db, user, 3, action)
    assert exc.value.status_code == 403
