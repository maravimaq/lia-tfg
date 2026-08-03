from __future__ import annotations

import time

import pytest

from app.core.config import settings
from app.services.email_service import EmailService
from tests.helpers import auth_headers, login_user, register_and_login, register_user, user_payload


@pytest.mark.integration
def test_health_endpoints(client):
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "environment": settings.environment,
    }


@pytest.mark.integration
def test_register_login_me_logout(client):
    user, token = register_and_login(client)
    assert user["email"] == "usuario@example.com"
    assert user["proveedor_auth"] == "local"

    me = client.get("/users/me", headers=auth_headers(token))
    assert me.status_code == 200
    assert me.json()["id_usuario"] == user["id_usuario"]

    logout = client.post("/auth/logout", headers=auth_headers(token))
    assert logout.status_code == 200

    after_logout = client.get("/users/me", headers=auth_headers(token))
    assert after_logout.status_code == 401


@pytest.mark.integration
def test_register_rejects_duplicate_email_and_username(client):
    register_user(client)

    duplicate_email = user_payload(username="otro_usuario")
    response = client.post("/auth/register", json=duplicate_email)
    assert response.status_code == 400
    assert "email" in response.json()["detail"].lower()

    duplicate_username = user_payload(
        email="otro@example.com",
        username="usuario_test",
    )
    response = client.post("/auth/register", json=duplicate_username)
    assert response.status_code == 400
    assert "usuario" in response.json()["detail"].lower()


@pytest.mark.integration
def test_login_rejects_wrong_password(client):
    register_user(client)
    response = client.post(
        "/auth/login",
        json={"email": "usuario@example.com", "contrasena": "incorrecta"},
    )
    assert response.status_code == 401


@pytest.mark.integration
def test_forgot_password_sends_temporary_password_and_revokes_session(client, monkeypatch):
    _, old_token = register_and_login(client)
    captured: dict[str, str] = {}

    def fake_send(email: str, temporary_password: str):
        captured["email"] = email
        captured["password"] = temporary_password
        return None

    monkeypatch.setattr(EmailService, "send_temporary_password_email", staticmethod(fake_send))

    response = client.post(
        "/auth/forgot-password",
        json={"email": "usuario@example.com"},
    )
    assert response.status_code == 200
    assert captured["email"] == "usuario@example.com"
    assert len(captured["password"]) == 12

    old_session = client.get("/users/me", headers=auth_headers(old_token))
    assert old_session.status_code == 401

    time.sleep(1.05)
    new_token = login_user(
        client,
        email="usuario@example.com",
        password=captured["password"],
    )
    assert new_token


@pytest.mark.integration
def test_forgot_password_unknown_email_does_not_disclose_account(client, monkeypatch):
    called = False

    def fake_send(_email: str, _password: str):
        nonlocal called
        called = True

    monkeypatch.setattr(EmailService, "send_temporary_password_email", staticmethod(fake_send))
    response = client.post(
        "/auth/forgot-password",
        json={"email": "no-existe@example.com"},
    )
    assert response.status_code == 200
    assert called is False


@pytest.mark.integration
def test_legacy_reset_password_endpoint_is_gone(client):
    response = client.post(
        "/auth/reset-password",
        json={"token": "obsolete", "nueva_contrasena": "Nueva1234!"},
    )
    assert response.status_code == 410
