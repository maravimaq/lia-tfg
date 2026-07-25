from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest
from fastapi import HTTPException

from app.schemas.user import UserCreate
from app.services.auth_service import AuthService


def _user_data():
    return UserCreate(
        nombre_usuario="juan",
        nombre_completo="Juan del Junco",
        email="juan@example.com",
        telefono=None,
        contrasena="clave-segura",
    )


def test_register_crea_usuario_local_con_rol(db):
    role = SimpleNamespace(id_rol=2)
    created = SimpleNamespace(id_usuario=1)

    with (
        patch("app.services.auth_service.UserRepository.get_by_email", return_value=None),
        patch("app.services.auth_service.UserRepository.get_by_username", return_value=None),
        patch("app.services.auth_service.RoleRepository.get_by_name", return_value=role),
        patch("app.services.auth_service.hash_password", return_value="HASH") as hash_mock,
        patch("app.services.auth_service.User") as user_model,
        patch("app.services.auth_service.UserRepository.create", return_value=created) as create_mock,
    ):
        user_model.return_value = SimpleNamespace()
        result = AuthService.register(db, _user_data())

    assert result is created
    hash_mock.assert_called_once_with("clave-segura")
    user_model.assert_called_once_with(
        nombre_usuario="juan",
        nombre_completo="Juan del Junco",
        email="juan@example.com",
        contrasena="HASH",
        telefono=None,
        estado="activo",
        rol_id=2,
        proveedor_auth="local",
    )
    create_mock.assert_called_once_with(db, user_model.return_value)


def test_register_rechaza_email_duplicado(db):
    with patch("app.services.auth_service.UserRepository.get_by_email", return_value=object()):
        with pytest.raises(HTTPException) as exc:
            AuthService.register(db, _user_data())
    assert exc.value.status_code == 400
    assert exc.value.detail == "El email ya está registrado"


def test_register_rechaza_username_duplicado(db):
    with (
        patch("app.services.auth_service.UserRepository.get_by_email", return_value=None),
        patch("app.services.auth_service.UserRepository.get_by_username", return_value=object()),
    ):
        with pytest.raises(HTTPException) as exc:
            AuthService.register(db, _user_data())
    assert exc.value.status_code == 400
    assert exc.value.detail == "El nombre de usuario ya está en uso"


def test_login_crea_token_y_sesion(db, user):
    with (
        patch("app.services.auth_service.UserRepository.get_by_email", return_value=user),
        patch("app.services.auth_service.verify_password", return_value=True),
        patch("app.services.auth_service.create_access_token", return_value="TOKEN") as token_mock,
        patch("app.services.auth_service.SesionAutenticacion") as session_model,
        patch("app.services.auth_service.SessionRepository.create") as session_create,
    ):
        session_model.return_value = SimpleNamespace()
        token = AuthService.login(db, user.email, "clave")

    assert token == "TOKEN"
    token_mock.assert_called_once_with(data={"sub": user.email})
    session_model.assert_called_once_with(
        proveedor="local",
        token="TOKEN",
        usuario_id=user.id_usuario,
    )
    session_create.assert_called_once_with(db, session_model.return_value)


@pytest.mark.parametrize(
    ("found_user", "password_ok", "expected_status"),
    [
        (None, True, 401),
        (SimpleNamespace(proveedor_auth="local", contrasena="HASH", estado="activo"), False, 401),
        (SimpleNamespace(proveedor_auth="local", contrasena="HASH", estado="inactivo"), True, 403),
        (SimpleNamespace(proveedor_auth="google", contrasena="HASH", estado="activo"), True, 400),
    ],
)
def test_login_rechaza_casos_invalidos(db, found_user, password_ok, expected_status):
    with (
        patch("app.services.auth_service.UserRepository.get_by_email", return_value=found_user),
        patch("app.services.auth_service.verify_password", return_value=password_ok),
    ):
        with pytest.raises(HTTPException) as exc:
            AuthService.login(db, "juan@example.com", "clave")
    assert exc.value.status_code == expected_status


def test_logout_cierra_sesion_activa(db):
    session = object()
    with (
        patch("app.services.auth_service.SessionRepository.get_active_by_token", return_value=session),
        patch("app.services.auth_service.SessionRepository.close_session") as close_mock,
    ):
        result = AuthService.logout(db, "TOKEN")

    assert result == {"message": "Sesión cerrada correctamente"}
    close_mock.assert_called_once_with(db, session)


def test_logout_es_idempotente_si_no_hay_sesion(db):
    with patch("app.services.auth_service.SessionRepository.get_active_by_token", return_value=None):
        assert AuthService.logout(db, "TOKEN") == {
            "message": "La sesión ya estaba cerrada o revocada"
        }


def test_temporary_password_tiene_longitud_y_alfanumerica():
    password = AuthService._generate_temporary_password(20)
    assert len(password) == 20
    assert password.isalnum()


def test_forgot_password_no_revela_si_email_no_existe(db):
    with patch("app.services.auth_service.UserRepository.get_by_email", return_value=None):
        result = AuthService.forgot_password(db, "nadie@example.com")
    assert "Si el correo existe" in result["message"]


def test_forgot_password_cambia_hash_revoca_sesiones_y_envia_email(db, user):
    with (
        patch("app.services.auth_service.UserRepository.get_by_email", return_value=user),
        patch("app.services.auth_service.AuthService._generate_temporary_password", return_value="TEMP12345678"),
        patch("app.services.auth_service.hash_password", return_value="NUEVO_HASH"),
        patch("app.services.auth_service.UserRepository.save") as save_mock,
        patch("app.services.auth_service.SessionRepository.revoke_all_user_sessions") as revoke_mock,
        patch("app.services.auth_service.EmailService.send_temporary_password_email") as email_mock,
    ):
        result = AuthService.forgot_password(db, user.email)

    assert user.contrasena == "NUEVO_HASH"
    save_mock.assert_called_once_with(db, user)
    revoke_mock.assert_called_once_with(db, user.id_usuario)
    email_mock.assert_called_once_with(user.email, "TEMP12345678")
    assert "contraseña temporal" in result["message"]
