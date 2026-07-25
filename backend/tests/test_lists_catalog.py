from __future__ import annotations

from decimal import Decimal

import pytest

from tests.helpers import (
    add_product_to_list,
    auth_headers,
    create_list,
    create_product,
    register_and_login,
)


@pytest.mark.integration
def test_catalog_search_compare_and_crud(client):
    milk_a = create_product(client, name="Leche entera 1L", price="1.25", supermarket="Mercadona")
    milk_b = create_product(client, name="Leche entera 1L", price="1.10", supermarket="DIA", brand="DIA")
    create_product(client, name="Café con leche", price="0.85", supermarket="Carrefour")

    search = client.get("/productos/search", params={"nombre": "Leche entera", "orden_precio": "asc"})
    assert search.status_code == 200
    assert len(search.json()) >= 2

    compare = client.get("/productos/comparar", params={"nombre": "Leche entera"})
    assert compare.status_code == 200
    prices = [Decimal(item["precio_unitario"]) for item in compare.json()]
    assert prices == sorted(prices)

    update = client.put(
        f"/productos/{milk_a['id_producto']}",
        json={"precio_unitario": "1.30"},
    )
    assert update.status_code == 200
    assert Decimal(update.json()["precio_unitario"]) == Decimal("1.30")

    delete = client.delete(f"/productos/{milk_b['id_producto']}")
    assert delete.status_code == 200


@pytest.mark.integration
def test_list_and_product_line_crud_recalculates_total(client):
    _, token = register_and_login(client)
    shopping_list = create_list(client, token)
    product = create_product(client, price="1.25")

    line = add_product_to_list(
        client,
        token,
        list_id=shopping_list["id_lista"],
        product_id=product["id_producto"],
        quantity=2,
    )
    assert Decimal(line["precio_estimado"]) == Decimal("2.50")

    detail = client.get(
        f"/listas/{shopping_list['id_lista']}",
        headers=auth_headers(token),
    )
    assert detail.status_code == 200
    assert Decimal(detail.json()["total_estimado"]) == Decimal("2.50")
    assert len(detail.json()["productos"]) == 1

    update_line = client.put(
        f"/productos-lista/{line['id_producto_lista']}",
        headers=auth_headers(token),
        json={"cantidad": 3},
    )
    assert update_line.status_code == 200
    assert Decimal(update_line.json()["precio_estimado"]) == Decimal("3.75")

    updated_list = client.put(
        f"/listas/{shopping_list['id_lista']}",
        headers=auth_headers(token),
        json={"nombre_lista": "Compra actualizada"},
    )
    assert updated_list.status_code == 200
    assert updated_list.json()["nombre_lista"] == "Compra actualizada"

    deleted_line = client.delete(
        f"/productos-lista/{line['id_producto_lista']}",
        headers=auth_headers(token),
    )
    assert deleted_line.status_code == 200

    detail_after = client.get(
        f"/listas/{shopping_list['id_lista']}",
        headers=auth_headers(token),
    )
    assert Decimal(detail_after.json()["total_estimado"]) == Decimal("0.00")


@pytest.mark.integration
def test_user_cannot_access_another_users_private_list(client):
    _, owner_token = register_and_login(client)
    shopping_list = create_list(client, owner_token)

    _, other_token = register_and_login(
        client,
        email="otro@example.com",
        username="otro_test",
        full_name="Otro Usuario",
    )
    response = client.get(
        f"/listas/{shopping_list['id_lista']}",
        headers=auth_headers(other_token),
    )
    assert response.status_code == 403
