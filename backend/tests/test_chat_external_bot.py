from __future__ import annotations

import pytest

from app.schemas.chat import ListChatMessageResponse, ListChatSuggestion
from app.services.list_chatbot_service import ListChatbotService
from app.services.telegram_bot_client import TelegramBotClient
from tests.helpers import (
    auth_headers,
    create_list,
    create_product,
    register_and_login,
)


@pytest.mark.integration
def test_list_chat_persists_and_clears_history(client, monkeypatch):
    _, token = register_and_login(client)
    shopping_list = create_list(client, token)

    def fake_process_message(**_kwargs):
        return ListChatMessageResponse(
            reply="La lista parece equilibrada.",
            intent="analizar_lista",
            suggestions=[
                ListChatSuggestion(
                    type="info",
                    title="Revisión",
                    description="No se detectan problemas importantes.",
                )
            ],
            context_summary={"productos": 0},
        )

    monkeypatch.setattr(ListChatbotService, "process_message", staticmethod(fake_process_message))

    send = client.post(
        f"/chat/lista/{shopping_list['id_lista']}/message",
        headers=auth_headers(token),
        json={"message": "Analiza esta lista"},
    )
    assert send.status_code == 200
    assert send.json()["intent"] == "analizar_lista"

    history = client.get(
        f"/chat/lista/{shopping_list['id_lista']}/messages",
        headers=auth_headers(token),
    )
    assert history.status_code == 200
    assert [item["role"] for item in history.json()] == ["user", "assistant"]

    clear = client.delete(
        f"/chat/lista/{shopping_list['id_lista']}/messages",
        headers=auth_headers(token),
    )
    assert clear.status_code == 200
    assert clear.json()["deleted"] == 2


@pytest.mark.integration
def test_delete_list_removes_chat_history(client, monkeypatch):
    _, token = register_and_login(client)
    shopping_list = create_list(client, token)

    def fake_process_message(**_kwargs):
        return ListChatMessageResponse(
            reply="Respuesta de prueba.",
            intent="analizar_lista",
            suggestions=[],
            context_summary={"productos": 0},
        )

    monkeypatch.setattr(
        ListChatbotService,
        "process_message",
        staticmethod(fake_process_message),
    )

    send = client.post(
        f"/chat/lista/{shopping_list['id_lista']}/message",
        headers=auth_headers(token),
        json={"message": "Analiza esta lista"},
    )

    assert send.status_code == 200

    from app.models.list_chat_message import ListChatMessage
    from tests.conftest import TestingSessionLocal

    with TestingSessionLocal() as db:
        messages_before = (
            db.query(ListChatMessage)
            .filter(
                ListChatMessage.lista_id
                == shopping_list["id_lista"]
            )
            .count()
        )

        assert messages_before == 2

    delete = client.delete(
        f"/listas/{shopping_list['id_lista']}",
        headers=auth_headers(token),
    )

    assert delete.status_code == 200
    assert delete.json()["message"] == "Lista eliminada correctamente"

    with TestingSessionLocal() as db:
        messages_after = (
            db.query(ListChatMessage)
            .filter(
                ListChatMessage.lista_id
                == shopping_list["id_lista"]
            )
            .count()
        )

        assert messages_after == 0

    missing_list = client.get(
        f"/listas/{shopping_list['id_lista']}",
        headers=auth_headers(token),
    )

    assert missing_list.status_code == 404


@pytest.mark.integration
def test_external_bot_link_and_add_product_flow(client):
    _, token = register_and_login(client)
    shopping_list = create_list(client, token, "Compra Telegram")
    create_list(client, token, "Otra lista")
    create_product(client, name="Leche semidesnatada", price="1.20")

    link_code = client.post(
        "/external-bot/link-code",
        headers=auth_headers(token),
        json={"plataforma": "telegram"},
    )
    assert link_code.status_code == 200, link_code.text
    code = link_code.json()["codigo"]

    from app.services.external_bot_service import ExternalBotService
    from tests.conftest import TestingSessionLocal

    with TestingSessionLocal() as db:
        linked = ExternalBotService.process_message(
            db,
            "telegram",
            "telegram-user-123",
            f"/start {code}",
        )
        assert "vinculada" in linked.reply.lower()

        search = ExternalBotService.process_message(
            db,
            "telegram",
            "telegram-user-123",
            "añadir leche",
        )
        assert search.state == "waiting_product_selection"
        assert search.options

        quantity = ExternalBotService.process_message(
            db,
            "telegram",
            "telegram-user-123",
            "1",
        )
        assert quantity.state == "waiting_quantity"

        list_selection = ExternalBotService.process_message(
            db,
            "telegram",
            "telegram-user-123",
            "2",
        )
        assert list_selection.state == "waiting_list_selection"

        selected_number = next(
            option.numero
            for option in list_selection.options
            if int(option.value) == shopping_list["id_lista"]
        )
        added = ExternalBotService.process_message(
            db,
            "telegram",
            "telegram-user-123",
            str(selected_number),
        )
        assert added.added_to_list_id == shopping_list["id_lista"]

    detail = client.get(
        f"/listas/{shopping_list['id_lista']}",
        headers=auth_headers(token),
    )
    assert len(detail.json()["productos"]) == 1
    assert detail.json()["productos"][0]["cantidad"] == 2

@pytest.mark.integration
def test_external_bot_compare_does_not_mix_different_units(client):
    _, token = register_and_login(client)

    create_product(
        client,
        name="Arroz cocido integral",
        price="1.05",
        unit="VASITOS",
    )
    create_product(
        client,
        name="Arroz redondo",
        price="1.20",
        unit="KG",
    )

    link_code = client.post(
        "/external-bot/link-code",
        headers=auth_headers(token),
        json={"plataforma": "telegram"},
    )
    assert link_code.status_code == 200, link_code.text
    code = link_code.json()["codigo"]

    from app.services.external_bot_service import ExternalBotService
    from tests.conftest import TestingSessionLocal

    with TestingSessionLocal() as db:
        linked = ExternalBotService.process_message(
            db,
            "telegram",
            "telegram-compare-user",
            f"/start {code}",
        )
        assert "vinculada" in linked.reply.lower()

        comparison = ExternalBotService.process_message(
            db,
            "telegram",
            "telegram-compare-user",
            "comparar arroz",
        )

        reply = comparison.reply.lower()

        assert comparison.action == "comparison_shown"
        assert "unidades distintas" in reply
        assert "vasitos" in reply
        assert "kg" in reply
        assert "opción más barata por cada unidad" in reply

@pytest.mark.integration
def test_telegram_webhook_rejects_bad_secret(client):
    response = client.post(
        "/external-bot/webhook/telegram",
        headers={"X-Telegram-Bot-Api-Secret-Token": "incorrecto"},
        json={
            "update_id": 1,
            "message": {
                "from": {"id": 123},
                "chat": {"id": 123},
                "text": "hola",
            },
        },
    )
    assert response.status_code == 401
