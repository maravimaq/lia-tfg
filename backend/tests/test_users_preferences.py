from __future__ import annotations

import time

import pytest

from tests.helpers import auth_headers, login_user, register_and_login, register_user


@pytest.mark.integration
def test_update_profile_and_preferences(client):
    _, token = register_and_login(client)
    headers = auth_headers(token)

    update = client.put(
        "/users/me",
        headers=headers,
        json={"nombre_completo": "Nombre Actualizado", "telefono": "699999999"},
    )
    assert update.status_code == 200
    assert update.json()["nombre_completo"] == "Nombre Actualizado"

    defaults = client.get("/users/me/preferences", headers=headers)
    assert defaults.status_code == 200
    assert defaults.json()["idioma"] == "es"
    assert defaults.json()["notificaciones"] is True

    updated = client.put(
        "/users/me/preferences",
        headers=headers,
        json={
            "modo_oscuro": True,
            "unidad_precio": "usd",
            "supermercado_favorito": "día",
        },
    )
    assert updated.status_code == 200
    assert updated.json()["modo_oscuro"] is True
    assert updated.json()["unidad_precio"] == "USD"
    assert updated.json()["supermercado_favorito"] == "DIA"


@pytest.mark.integration
def test_invalid_preferences_are_rejected(client):
    _, token = register_and_login(client)
    response = client.put(
        "/users/me/preferences",
        headers=auth_headers(token),
        json={"idioma": "fr"},
    )
    assert response.status_code == 422


@pytest.mark.integration
def test_change_password_revokes_sessions(client):
    _, token = register_and_login(client)
    response = client.put(
        "/users/me/password",
        headers=auth_headers(token),
        json={
            "contrasena_actual": "Usuario1234!",
            "nueva_contrasena": "NuevaClave1234!",
        },
    )
    assert response.status_code == 200

    assert client.get("/users/me", headers=auth_headers(token)).status_code == 401
    time.sleep(1.05)
    assert login_user(client, password="NuevaClave1234!")


@pytest.mark.integration
def test_follow_request_flow(client):
    first, first_token = register_and_login(client)
    second = register_user(
        client,
        email="segundo@example.com",
        username="segundo_test",
        full_name="Segundo Usuario",
    )
    second_token = login_user(client, email="segundo@example.com")

    discover = client.get("/users/discover", headers=auth_headers(first_token))
    assert discover.status_code == 200
    assert any(item["id_usuario"] == second["id_usuario"] for item in discover.json())

    request = client.post(
        f"/users/follow-requests/{second['id_usuario']}",
        headers=auth_headers(first_token),
    )
    assert request.status_code == 200
    request_id = request.json()["id_solicitud_seguimiento"]

    incoming = client.get(
        "/users/me/follow-requests/incoming",
        headers=auth_headers(second_token),
    )
    assert incoming.status_code == 200
    assert incoming.json()[0]["solicitante"]["id_usuario"] == first["id_usuario"]

    accepted = client.put(
        f"/users/me/follow-requests/{request_id}/respond",
        headers=auth_headers(second_token),
        json={"accion": "aceptar"},
    )
    assert accepted.status_code == 200
    assert "aceptada" in accepted.json()["message"].lower()
