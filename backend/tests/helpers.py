from __future__ import annotations

from fastapi.testclient import TestClient


def user_payload(
    *,
    email: str = "usuario@example.com",
    username: str = "usuario_test",
    password: str = "Usuario1234!",
    full_name: str = "Usuario Test",
) -> dict:
    return {
        "nombre_usuario": username,
        "nombre_completo": full_name,
        "email": email,
        "telefono": "600000000",
        "avatar_url": None,
        "contrasena": password,
    }


def register_user(client: TestClient, **overrides) -> dict:
    payload = user_payload(**overrides)
    response = client.post("/auth/register", json=payload)
    assert response.status_code == 200, response.text
    return response.json()


def login_user(
    client: TestClient,
    *,
    email: str = "usuario@example.com",
    password: str = "Usuario1234!",
) -> str:
    response = client.post(
        "/auth/login",
        json={"email": email, "contrasena": password},
    )
    assert response.status_code == 200, response.text
    return response.json()["access_token"]


def register_and_login(client: TestClient, **overrides) -> tuple[dict, str]:
    user = register_user(client, **overrides)
    token = login_user(
        client,
        email=overrides.get("email", "usuario@example.com"),
        password=overrides.get("password", "Usuario1234!"),
    )
    return user, token


def auth_headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def create_product(
    client: TestClient,
    *,
    name: str = "Leche entera 1L",
    price: str = "1.25",
    supermarket: str = "Mercadona",
    brand: str = "Hacendado",
    category: str = "Lácteos",
    unit: str = "L",
    image_url: str | None = None,
) -> dict:
    response = client.post(
        "/productos",
        json={
            "nombre": name,
            "marca": brand,
            "categoria": category,
            "supermercado": supermarket,
            "precio_unitario": price,
            "unidad_medida": unit,
            "imagen_url": image_url,
        },
    )
    assert response.status_code == 200, response.text
    return response.json()


def create_list(client: TestClient, token: str, name: str = "Compra semanal") -> dict:
    response = client.post(
        "/listas",
        headers=auth_headers(token),
        json={"nombre_lista": name, "compartida": False},
    )
    assert response.status_code == 200, response.text
    return response.json()


def add_product_to_list(
    client: TestClient,
    token: str,
    *,
    list_id: int,
    product_id: int,
    quantity: int = 2,
) -> dict:
    response = client.post(
        "/productos-lista",
        headers=auth_headers(token),
        json={
            "lista_id": list_id,
            "producto_id": product_id,
            "cantidad": quantity,
        },
    )
    assert response.status_code == 200, response.text
    return response.json()
