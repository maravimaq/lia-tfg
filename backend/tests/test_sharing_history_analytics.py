from __future__ import annotations

from datetime import datetime
from decimal import Decimal

import pytest

from app.models.historial_listas import HistorialListas
from app.models.lista_compartida import ListaCompartida
from tests.helpers import (
    add_product_to_list,
    auth_headers,
    create_list,
    create_product,
    login_user,
    register_and_login,
    register_user,
)


@pytest.mark.integration
def test_share_list_with_edit_and_leave(client):
    _, owner_token = register_and_login(client)
    guest = register_user(
        client,
        email="invitado@example.com",
        username="invitado_test",
        full_name="Invitado Test",
    )
    guest_token = login_user(client, email="invitado@example.com")

    shopping_list = create_list(client, owner_token, "Lista compartida")
    product = create_product(client)

    share = client.post(
        f"/listas/{shopping_list['id_lista']}/compartir",
        headers=auth_headers(owner_token),
        json={"email_usuario": guest["email"], "tipo_compartido": "edicion"},
    )
    assert share.status_code == 200

    shared = client.get("/listas/compartidas", headers=auth_headers(guest_token))
    assert shared.status_code == 200
    assert shared.json()[0]["lista"]["id_lista"] == shopping_list["id_lista"]

    line = add_product_to_list(
        client,
        guest_token,
        list_id=shopping_list["id_lista"],
        product_id=product["id_producto"],
        quantity=1,
    )
    assert line["lista_id"] == shopping_list["id_lista"]

    leave = client.delete(
        f"/listas/compartidas/{shopping_list['id_lista']}",
        headers=auth_headers(guest_token),
    )
    assert leave.status_code == 200

@pytest.mark.integration
def test_owner_can_delete_shared_list(client):
    _, owner_token = register_and_login(client)

    guest = register_user(
        client,
        email="delete_guest@example.com",
        username="delete_guest",
        full_name="Delete Guest",
    )

    shopping_list = create_list(
        client,
        owner_token,
        "Lista compartida para borrar",
    )

    share = client.post(
        f"/listas/{shopping_list['id_lista']}/compartir",
        headers=auth_headers(owner_token),
        json={
            "email_usuario": guest["email"],
            "tipo_compartido": "edicion",
        },
    )

    assert share.status_code == 200

    delete = client.delete(
        f"/listas/{shopping_list['id_lista']}",
        headers=auth_headers(owner_token),
    )

    assert delete.status_code == 200

    from tests.conftest import TestingSessionLocal

    with TestingSessionLocal() as db:
        remaining_shares = (
            db.query(ListaCompartida)
            .filter(
                ListaCompartida.lista_id
                == shopping_list["id_lista"]
            )
            .count()
        )

        assert remaining_shares == 0


@pytest.mark.integration
def test_read_only_shared_user_cannot_modify(client):
    _, owner_token = register_and_login(client)
    guest = register_user(
        client,
        email="lector@example.com",
        username="lector_test",
        full_name="Lector Test",
    )
    guest_token = login_user(client, email="lector@example.com")
    shopping_list = create_list(client, owner_token)
    product = create_product(client)

    client.post(
        f"/listas/{shopping_list['id_lista']}/compartir",
        headers=auth_headers(owner_token),
        json={"email_usuario": guest["email"], "tipo_compartido": "visualizacion"},
    )

    response = client.post(
        "/productos-lista",
        headers=auth_headers(guest_token),
        json={
            "lista_id": shopping_list["id_lista"],
            "producto_id": product["id_producto"],
            "cantidad": 1,
        },
    )
    assert response.status_code == 403


@pytest.mark.integration
def test_finalize_history_repeat_and_analytics(client, db):
    user, token = register_and_login(client)
    shopping_list = create_list(client, token, "Compra mensual")
    milk = create_product(client, name="Leche entera", price="1.50", category="Lácteos")
    rice = create_product(client, name="Arroz redondo", price="2.00", category="Despensa")

    add_product_to_list(
        client,
        token,
        list_id=shopping_list["id_lista"],
        product_id=milk["id_producto"],
        quantity=2,
    )
    add_product_to_list(
        client,
        token,
        list_id=shopping_list["id_lista"],
        product_id=rice["id_producto"],
        quantity=1,
    )

    finalize = client.post(
        f"/historial/listas/{shopping_list['id_lista']}/finalizar",
        headers=auth_headers(token),
    )
    assert finalize.status_code == 200, finalize.text
    history_id = finalize.json()["id_historial"]
    assert finalize.json()["num_productos"] == 3
    assert Decimal(finalize.json()["total_gastado"]) == Decimal("5.00")

    # Fijamos la fecha para que las consultas mensuales sean deterministas.
    history = db.query(HistorialListas).filter(HistorialListas.id_historial == history_id).one()
    history.fecha = datetime(2026, 6, 12, 18, 30)
    db.commit()

    detail = client.get(
        f"/historial/{history_id}/detalle",
        headers=auth_headers(token),
    )
    assert detail.status_code == 200
    assert len(detail.json()["productos"]) == 2

    repeated = client.post(
        f"/historial/{history_id}/repetir",
        headers=auth_headers(token),
    )
    assert repeated.status_code == 200
    assert repeated.json()["nombre_lista"] == "Copia de Compra mensual"

    monthly = client.get(
        "/analytics/monthly-expenses",
        params={"year": 2026, "month": 6},
        headers=auth_headers(token),
    )
    assert monthly.status_code == 200
    assert monthly.json()["resumen"]["total_mensual"] == 5.0
    assert monthly.json()["resumen"]["numero_compras"] == 1

    categories = client.get(
        "/analytics/categories",
        params={"year": 2026, "month": 6},
        headers=auth_headers(token),
    )
    assert categories.status_code == 200
    assert {item["categoria"] for item in categories.json()["categorias"]} == {
        "Lácteos",
        "Despensa",
    }

    habits = client.get("/analytics/habits", headers=auth_headers(token))
    assert habits.status_code == 200
    assert habits.json()["promedio_productos_por_compra"] == 3.0

    finalized_list = client.get(
        f"/listas/{shopping_list['id_lista']}",
        headers=auth_headers(token),
    )
    assert finalized_list.status_code == 400
