from unittest.mock import MagicMock

import httpx
import pytest
from fastapi import HTTPException

from app.services.telegram_bot_client import TelegramBotClient
import app.services.telegram_bot_client as telegram_module


def fake_client(monkeypatch, *, payload=None, error=None):
    response = MagicMock()
    response.raise_for_status.side_effect = error
    response.json.return_value = payload or {"ok": True, "result": {"id": 1}}

    client = MagicMock()
    client.post.return_value = response

    manager = MagicMock()
    manager.__enter__.return_value = client
    manager.__exit__.return_value = False

    factory = MagicMock(return_value=manager)
    monkeypatch.setattr(telegram_module.httpx, "Client", factory)
    return client, response, factory


def test_init_sin_token_falla(monkeypatch):
    monkeypatch.setattr(telegram_module.settings, "telegram_bot_token", None)
    with pytest.raises(HTTPException) as exc:
        TelegramBotClient()
    assert exc.value.status_code == 500


def test_init_construye_url(monkeypatch):
    monkeypatch.setattr(telegram_module.settings, "telegram_request_timeout_seconds", 15)
    client = TelegramBotClient("TOKEN")
    assert client.base_url.endswith("botTOKEN")
    assert client.timeout == 15


def test_request_correcta(monkeypatch):
    fake_client(monkeypatch, payload={"ok": True, "result": {"username": "lia"}})
    result = TelegramBotClient("TOKEN")._request("getMe")
    assert result["result"]["username"] == "lia"


def test_request_error_http(monkeypatch):
    request = httpx.Request("POST", "https://telegram.test")
    error = httpx.ConnectError("sin red", request=request)
    fake_client(monkeypatch, error=error)

    with pytest.raises(HTTPException) as exc:
        TelegramBotClient("TOKEN")._request("getMe")
    assert exc.value.status_code == 502


def test_request_ok_false(monkeypatch):
    fake_client(monkeypatch, payload={"ok": False, "description": "bad"})
    with pytest.raises(HTTPException, match="Telegram devolvió"):
        TelegramBotClient("TOKEN")._request("getMe")


def test_get_me(monkeypatch):
    client = TelegramBotClient("TOKEN")
    client._request = MagicMock(return_value={"result": {"username": "asisLIA_bot"}})
    assert client.get_me()["username"] == "asisLIA_bot"


def test_send_message_un_solo_fragment():
    client = TelegramBotClient("TOKEN")
    client._request = MagicMock(return_value={"result": {"message_id": 1}})
    result = client.send_message(99, "hola")
    assert result == [{"message_id": 1}]
    assert client._request.call_args.args[0] == "sendMessage"


def test_send_message_divide_texto_largo():
    client = TelegramBotClient("TOKEN")
    client.MAX_MESSAGE_LENGTH = 10
    client._request = MagicMock(return_value={"result": {"ok": True}})
    client.send_message(1, "uno dos tres\ncuatro cinco")
    assert client._request.call_count >= 2


def test_split_prefiere_salto_de_linea():
    client = TelegramBotClient("TOKEN")
    client.MAX_MESSAGE_LENGTH = 10
    chunks = client._split_message("12345\n67890\nabc")
    assert len(chunks) >= 2
    assert all(len(chunk) <= 10 for chunk in chunks)


def test_get_updates_con_offset():
    client = TelegramBotClient("TOKEN")
    client._request = MagicMock(return_value={"result": [{"update_id": 3}]})
    result = client.get_updates(offset=10, timeout=5)
    assert result[0]["update_id"] == 3
    payload = client._request.call_args.args[1]
    assert payload["offset"] == 10


def test_get_updates_timeout_se_convierte_en_lista_vacia():
    client = TelegramBotClient("TOKEN")
    client._request = MagicMock(
        side_effect=HTTPException(status_code=502, detail="Read timed out")
    )
    assert client.get_updates(timeout=5) == []


def test_get_updates_error_no_timeout_se_propaga():
    client = TelegramBotClient("TOKEN")
    client._request = MagicMock(
        side_effect=HTTPException(status_code=502, detail="otro error")
    )
    with pytest.raises(HTTPException):
        client.get_updates()


def test_webhook_methods():
    client = TelegramBotClient("TOKEN")
    client._request = MagicMock(return_value={"result": {"ok": True}})

    assert client.set_webhook("https://lia.test/hook", "secret") == {"ok": True}
    assert client.delete_webhook(True) == {"ok": True}
    assert client.get_webhook_info() == {"ok": True}
