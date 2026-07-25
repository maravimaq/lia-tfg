from __future__ import annotations

import pytest

from tests.helpers import auth_headers, login_user, register_and_login


@pytest.mark.integration
def test_regular_user_cannot_access_admin(client):
    _, token = register_and_login(client)
    response = client.get("/admin/only-admin", headers=auth_headers(token))
    assert response.status_code == 403


@pytest.mark.integration
def test_admin_dashboard_and_user_management(client, create_admin):
    create_admin()
    token = login_user(
        client,
        email="admin@example.com",
        password="Admin1234!",
    )
    headers = auth_headers(token)

    only_admin = client.get("/admin/only-admin", headers=headers)
    assert only_admin.status_code == 200

    created = client.post(
        "/admin/users",
        headers=headers,
        json={
            "nombre_usuario": "creado_admin",
            "nombre_completo": "Creado por Admin",
            "email": "creado@example.com",
            "contrasena": "Creado1234!",
            "rol_nombre": "usuario",
            "estado": "activo",
        },
    )
    assert created.status_code == 200, created.text
    user_id = created.json()["id_usuario"]

    page = client.get("/admin/users", headers=headers)
    assert page.status_code == 200
    assert page.json()["total"] == 2

    deactivate = client.patch(f"/admin/users/{user_id}/deactivate", headers=headers)
    assert deactivate.status_code == 200
    assert deactivate.json()["estado"] == "inactivo"

    dashboard = client.get("/admin/dashboard", headers=headers)
    assert dashboard.status_code == 200
    assert dashboard.json()["total_usuarios"] == 2
