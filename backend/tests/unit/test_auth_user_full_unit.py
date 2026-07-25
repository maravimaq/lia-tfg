from datetime import datetime
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from fastapi import HTTPException

from app.schemas.account_request import AccountActionRequestCreate
from app.schemas.auth import ExternalUserPayload
from app.schemas.bot_config import BotConfigUpdate
from app.schemas.follow import FollowRequestAction
from app.schemas.user import UserUpdate
from app.services.auth_service import AuthService
from app.services.user_service import UserService
import app.services.auth_service as auth_module
import app.services.user_service as user_module


def test_register_missing_default_role(monkeypatch, db):
    monkeypatch.setattr(auth_module.UserRepository, 'get_by_email', MagicMock(return_value=None))
    monkeypatch.setattr(auth_module.UserRepository, 'get_by_username', MagicMock(return_value=None))
    monkeypatch.setattr(auth_module.RoleRepository, 'get_by_name', MagicMock(return_value=None))
    data = SimpleNamespace(email='a@b.com', nombre_usuario='a', contrasena='x', nombre_completo='A', telefono=None)
    with pytest.raises(HTTPException) as exc:
        AuthService.register(db, data)
    assert exc.value.status_code == 500


def test_create_external_user_existing(monkeypatch, db):
    existing = SimpleNamespace(id_usuario=1)
    monkeypatch.setattr(auth_module.UserRepository, 'get_by_email', MagicMock(return_value=existing))
    payload = ExternalUserPayload(email='a@b.com', nombre_usuario='a', nombre_completo='A')
    assert AuthService._create_external_user_if_needed(db, payload, 'apple') is existing


def test_create_external_user_unique_username(monkeypatch, db):
    role = SimpleNamespace(id_rol=2)
    created = SimpleNamespace(id_usuario=9)
    monkeypatch.setattr(auth_module.UserRepository, 'get_by_email', MagicMock(return_value=None))
    monkeypatch.setattr(auth_module.RoleRepository, 'get_by_name', MagicMock(return_value=role))
    monkeypatch.setattr(auth_module.UserRepository, 'get_by_username', MagicMock(side_effect=[object(), object(), None]))
    monkeypatch.setattr(auth_module, 'hash_password', MagicMock(return_value='HASH'))
    model = MagicMock(return_value=SimpleNamespace())
    monkeypatch.setattr(auth_module, 'User', model)
    monkeypatch.setattr(auth_module.UserRepository, 'create', MagicMock(return_value=created))
    payload = ExternalUserPayload(email='a@b.com', nombre_usuario='alpha', nombre_completo=None)

    assert AuthService._create_external_user_if_needed(db, payload, 'apple') is created
    assert model.call_args.kwargs['nombre_usuario'] == 'alpha2'
    assert model.call_args.kwargs['nombre_completo'] == 'alpha2'


def test_create_external_user_missing_role(monkeypatch, db):
    monkeypatch.setattr(auth_module.UserRepository, 'get_by_email', MagicMock(return_value=None))
    monkeypatch.setattr(auth_module.RoleRepository, 'get_by_name', MagicMock(return_value=None))
    with pytest.raises(HTTPException) as exc:
        AuthService._create_external_user_if_needed(db, ExternalUserPayload(email='a@b.com'), 'apple')
    assert exc.value.status_code == 500


def google_globals(monkeypatch, token_info=None, error=None):
    verifier = MagicMock(side_effect=error, return_value=token_info)
    monkeypatch.setattr(auth_module, 'id_token', SimpleNamespace(verify_oauth2_token=verifier), raising=False)
    monkeypatch.setattr(auth_module, 'google_requests', SimpleNamespace(Request=MagicMock), raising=False)
    monkeypatch.setattr(auth_module, 'settings', SimpleNamespace(google_web_client_id='client'), raising=False)
    return verifier


def test_google_login_invalid_token(monkeypatch, db):
    google_globals(monkeypatch, error=RuntimeError('bad'))
    with pytest.raises(HTTPException) as exc:
        AuthService.login_with_google(db, 'bad')
    assert exc.value.status_code == 401


@pytest.mark.parametrize('token_info', [
    {},
    {'email': 'a@b.com', 'email_verified': False},
])
def test_google_login_invalid_email(monkeypatch, db, token_info):
    google_globals(monkeypatch, token_info=token_info)
    with pytest.raises(HTTPException) as exc:
        AuthService.login_with_google(db, 'token')
    assert exc.value.status_code == 401


def test_google_login_existing_user(monkeypatch, db):
    google_globals(monkeypatch, token_info={'email': 'a@b.com', 'email_verified': True, 'name': 'A'})
    user = SimpleNamespace(id_usuario=1, email='a@b.com', estado='activo')
    monkeypatch.setattr(auth_module.UserRepository, 'get_by_email', MagicMock(return_value=user))
    monkeypatch.setattr(auth_module, 'create_access_token', MagicMock(return_value='TOKEN'))
    assert AuthService.login_with_google(db, 'token') == 'TOKEN'


def test_google_login_creates_user_and_resolves_username(monkeypatch, db):
    google_globals(monkeypatch, token_info={'email': 'a@b.com', 'email_verified': True})
    role = SimpleNamespace(id_rol=2)
    created = SimpleNamespace(id_usuario=2, email='a@b.com', estado='activo')
    monkeypatch.setattr(auth_module.UserRepository, 'get_by_email', MagicMock(return_value=None))
    monkeypatch.setattr(auth_module.RoleRepository, 'get_by_name', MagicMock(return_value=role))
    monkeypatch.setattr(auth_module.UserRepository, 'get_by_username', MagicMock(side_effect=[object(), None]))
    monkeypatch.setattr(auth_module, 'hash_password', MagicMock(return_value='HASH'))
    model = MagicMock(return_value=SimpleNamespace())
    monkeypatch.setattr(auth_module, 'User', model)
    monkeypatch.setattr(auth_module.UserRepository, 'create', MagicMock(return_value=created))
    monkeypatch.setattr(auth_module, 'create_access_token', MagicMock(return_value='TOKEN'))

    assert AuthService.login_with_google(db, 'token') == 'TOKEN'
    assert model.call_args.kwargs['nombre_usuario'] == 'a1'
    assert model.call_args.kwargs['nombre_completo'] == 'Usuario Google'


def test_google_login_missing_role_and_inactive(monkeypatch, db):
    google_globals(monkeypatch, token_info={'email': 'a@b.com', 'email_verified': True})
    monkeypatch.setattr(auth_module.UserRepository, 'get_by_email', MagicMock(return_value=None))
    monkeypatch.setattr(auth_module.RoleRepository, 'get_by_name', MagicMock(return_value=None))
    with pytest.raises(HTTPException) as exc:
        AuthService.login_with_google(db, 'token')
    assert exc.value.status_code == 500

    monkeypatch.setattr(auth_module.UserRepository, 'get_by_email', MagicMock(return_value=SimpleNamespace(estado='inactivo')))
    with pytest.raises(HTTPException) as exc:
        AuthService.login_with_google(db, 'token')
    assert exc.value.status_code == 403


def test_apple_login_success_and_inactive(monkeypatch, db):
    payload = ExternalUserPayload(email='apple@b.com', nombre_usuario='apple', nombre_completo='Apple')
    monkeypatch.setattr(auth_module, 'verify_apple_id_token', MagicMock(return_value=payload))
    active = SimpleNamespace(id_usuario=3, email='apple@b.com', estado='activo')
    monkeypatch.setattr(AuthService, '_create_external_user_if_needed', MagicMock(return_value=active))
    monkeypatch.setattr(auth_module, 'create_access_token', MagicMock(return_value='APPLE'))
    session_model = MagicMock(return_value=SimpleNamespace())
    monkeypatch.setattr(auth_module, 'SesionAutenticacion', session_model)
    create_session = MagicMock()
    monkeypatch.setattr(auth_module.SessionRepository, 'create', create_session)

    assert AuthService.login_with_apple(db, 'id') == 'APPLE'
    create_session.assert_called_once()

    monkeypatch.setattr(AuthService, '_create_external_user_if_needed', MagicMock(return_value=SimpleNamespace(estado='inactivo')))
    with pytest.raises(HTTPException) as exc:
        AuthService.login_with_apple(db, 'id')
    assert exc.value.status_code == 403


def test_forgot_external_and_email_failure(monkeypatch, db):
    external = SimpleNamespace(proveedor_auth='google')
    monkeypatch.setattr(auth_module.UserRepository, 'get_by_email', MagicMock(return_value=external))
    with pytest.raises(HTTPException) as exc:
        AuthService.forgot_password(db, 'a@b.com')
    assert exc.value.status_code == 400

    local = SimpleNamespace(id_usuario=1, proveedor_auth='local', email='a@b.com', contrasena='old')
    monkeypatch.setattr(auth_module.UserRepository, 'get_by_email', MagicMock(return_value=local))
    monkeypatch.setattr(AuthService, '_generate_temporary_password', MagicMock(return_value='TEMP'))
    monkeypatch.setattr(auth_module, 'hash_password', MagicMock(return_value='HASH'))
    monkeypatch.setattr(auth_module.UserRepository, 'save', MagicMock())
    monkeypatch.setattr(auth_module.SessionRepository, 'revoke_all_user_sessions', MagicMock())
    monkeypatch.setattr(auth_module.EmailService, 'send_temporary_password_email', MagicMock(side_effect=OSError('smtp')))
    with pytest.raises(HTTPException) as exc:
        AuthService.forgot_password(db, 'a@b.com')
    assert exc.value.status_code == 503


def test_reset_password_is_gone(db):
    with pytest.raises(HTTPException) as exc:
        AuthService.reset_password(db, 'token', 'new')
    assert exc.value.status_code == 410


def test_user_profile_and_bot_config_paths(monkeypatch, db, user):
    assert UserService.get_profile(user) is user
    monkeypatch.setattr(user_module.UserRepository, 'get_by_username', MagicMock(return_value=None))
    monkeypatch.setattr(user_module.UserRepository, 'save', MagicMock(return_value=user))
    updated = UserService.update_profile(db, user, UserUpdate(nombre_usuario='nuevo', telefono='123', avatar_url='url'))
    assert updated.nombre_usuario == 'nuevo' and updated.telefono == '123' and updated.avatar_url == 'url'

    monkeypatch.setattr(user_module.UserRepository, 'get_by_username', MagicMock(return_value=object()))
    with pytest.raises(HTTPException):
        UserService.update_profile(db, user, UserUpdate(nombre_usuario='ocupado'))

    created = SimpleNamespace(id_configuracion=1)
    monkeypatch.setattr(user_module.BotConfigRepository, 'get_by_user_id', MagicMock(return_value=None))
    monkeypatch.setattr(user_module.BotConfigRepository, 'create', MagicMock(return_value=created))
    assert UserService.get_bot_config(db, user) is created


def test_update_bot_config_create_and_save(monkeypatch, db, user):
    monkeypatch.setattr(user_module.BotConfigRepository, 'get_by_user_id', MagicMock(return_value=None))
    created = SimpleNamespace(id_configuracion=4)
    monkeypatch.setattr(user_module.BotConfigRepository, 'create', MagicMock(return_value=created))
    data = BotConfigUpdate(plataforma='telegram', token='T', estado='activo')
    assert UserService.update_bot_config(db, user, data) is created

    existing = SimpleNamespace(id_configuracion=1, plataforma='x', token=None, estado='inactivo')
    saved = SimpleNamespace(id_configuracion=1)
    monkeypatch.setattr(user_module.BotConfigRepository, 'get_by_user_id', MagicMock(return_value=existing))
    monkeypatch.setattr(user_module.BotConfigRepository, 'save', MagicMock(return_value=saved))
    assert UserService.update_bot_config(db, user, data) is saved
    assert existing.token == 'T'


def test_get_active_sessions_and_account_actions(monkeypatch, db, user):
    sessions = [object()]
    monkeypatch.setattr(user_module.SessionRepository, 'get_active_by_user_id', MagicMock(return_value=sessions))
    assert UserService.get_active_sessions(db, user) == sessions

    with pytest.raises(HTTPException):
        UserService.request_account_action(db, user, AccountActionRequestCreate(tipo='bad'))

    existing = SimpleNamespace(tipo='desactivacion', motivo=None)
    monkeypatch.setattr(user_module.AccountRequestRepository, 'get_pending_by_user_id', MagicMock(return_value=existing))
    result = UserService.request_account_action(db, user, AccountActionRequestCreate(tipo='desactivacion', motivo='pausa'))
    assert result is existing and existing.motivo == 'pausa'
    db.add.assert_called_with(existing)

    monkeypatch.setattr(user_module.AccountRequestRepository, 'get_pending_by_user_id', MagicMock(return_value=None))
    created = SimpleNamespace(id_solicitud=8)
    monkeypatch.setattr(user_module.AccountRequestRepository, 'create', MagicMock(return_value=created))
    monkeypatch.setattr(user_module.UserRepository, 'save', MagicMock())
    monkeypatch.setattr(user_module.SessionRepository, 'revoke_all_user_sessions', MagicMock())
    assert UserService.request_account_action(db, user, AccountActionRequestCreate(tipo='eliminacion')) is created
    assert user.estado == 'inactivo'


def test_discover_users_ordering(monkeypatch, db, user):
    followed_user = SimpleNamespace(id_usuario=2, nombre_usuario='z', nombre_completo='Zeta', email='z@x', avatar_url=None)
    pending_user = SimpleNamespace(id_usuario=3, nombre_usuario='a', nombre_completo='Ana', email='a@x', avatar_url=None)
    none_user = SimpleNamespace(id_usuario=4, nombre_usuario='b', nombre_completo='Beto', email='b@x', avatar_url=None)
    monkeypatch.setattr(user_module.UserRepository, 'discover_users', MagicMock(return_value=[none_user, pending_user, followed_user]))
    follow = SimpleNamespace(fecha_seguimiento=datetime(2026, 1, 1))
    monkeypatch.setattr(user_module.FollowRepository, 'get_follow', MagicMock(side_effect=[None, None, follow]))
    monkeypatch.setattr(user_module.FollowRepository, 'get_request_between', MagicMock(side_effect=[None, SimpleNamespace(estado='pendiente'), None]))
    result = UserService.discover_users(db, user)
    assert [x['follow_status'] for x in result] == ['followed', 'pending', 'none']
    assert '_followed_at' not in result[0]


def test_follow_request_error_paths(monkeypatch, db, user):
    monkeypatch.setattr(user_module.UserRepository, 'get_by_id', MagicMock(return_value=None))
    with pytest.raises(HTTPException) as exc:
        UserService.request_follow(db, user, 2)
    assert exc.value.status_code == 404

    monkeypatch.setattr(user_module.UserRepository, 'get_by_id', MagicMock(return_value=object()))
    monkeypatch.setattr(user_module.FollowRepository, 'get_follow', MagicMock(return_value=object()))
    with pytest.raises(HTTPException):
        UserService.request_follow(db, user, 2)

    monkeypatch.setattr(user_module.FollowRepository, 'get_follow', MagicMock(return_value=None))
    monkeypatch.setattr(user_module.FollowRepository, 'get_request_between', MagicMock(return_value=SimpleNamespace(estado='pendiente')))
    with pytest.raises(HTTPException):
        UserService.request_follow(db, user, 2)


def test_incoming_and_respond_follow_paths(monkeypatch, db, user):
    sender = SimpleNamespace(id_usuario=2, nombre_usuario='ana', nombre_completo='Ana', email='a@x', avatar_url='u')
    req = SimpleNamespace(id_solicitud_seguimiento=5, estado='pendiente', fecha_solicitud=datetime(2026, 1, 1), solicitante=sender)
    monkeypatch.setattr(user_module.FollowRepository, 'get_incoming_pending_requests', MagicMock(return_value=[req]))
    result = UserService.get_incoming_follow_requests(db, user)
    assert result[0]['solicitante']['nombre_completo'] == 'Ana'

    monkeypatch.setattr(user_module.FollowRepository, 'get_request_by_id', MagicMock(return_value=None))
    with pytest.raises(HTTPException) as exc:
        UserService.respond_follow_request(db, user, 1, FollowRequestAction(accion='aceptar'))
    assert exc.value.status_code == 404

    req2 = SimpleNamespace(destinatario_id=user.id_usuario, solicitante_id=2, estado='pendiente')
    monkeypatch.setattr(user_module.FollowRepository, 'get_request_by_id', MagicMock(return_value=req2))
    with pytest.raises(HTTPException):
        UserService.respond_follow_request(db, user, 1, FollowRequestAction(accion='otra'))

    delete = MagicMock()
    monkeypatch.setattr(user_module.FollowRepository, 'delete_request', delete)
    assert UserService.respond_follow_request(db, user, 1, FollowRequestAction(accion='rechazar'))['message'] == 'Solicitud rechazada'

    monkeypatch.setattr(user_module.FollowRepository, 'save_request', MagicMock())
    monkeypatch.setattr(user_module.FollowRepository, 'get_follow', MagicMock(return_value=None))
    create = MagicMock()
    monkeypatch.setattr(user_module.FollowRepository, 'create_follow', create)
    assert UserService.respond_follow_request(db, user, 1, FollowRequestAction(accion='aceptar'))['message'] == 'Solicitud aceptada'
    create.assert_called_once()

    monkeypatch.setattr(user_module.FollowRepository, 'get_follow', MagicMock(return_value=object()))
    UserService.respond_follow_request(db, user, 1, FollowRequestAction(accion='aceptar'))


def test_public_profile_success_and_not_found(monkeypatch, db):
    monkeypatch.setattr(user_module.UserRepository, 'get_by_id', MagicMock(return_value=None))
    with pytest.raises(HTTPException):
        UserService.get_public_profile(db, 1)

    u = SimpleNamespace(id_usuario=1, nombre_usuario='j', nombre_completo='Juan', email='j@x', avatar_url=None, estado='activo', fecha_registro=datetime(2026,1,1), rol_id=2, proveedor_auth='local', telefono=None)
    monkeypatch.setattr(user_module.UserRepository, 'get_by_id', MagicMock(return_value=u))
    assert UserService.get_public_profile(db, 1)['proveedor_auth'] == 'local'
