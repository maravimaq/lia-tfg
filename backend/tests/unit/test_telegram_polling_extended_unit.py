from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from fastapi import HTTPException

import app.bots.telegram_polling as polling


@pytest.mark.parametrize(
    ("update", "expected"),
    [
        (
            {"message": {"text": "hola", "chat": {"id": 7}, "from": {"id": 9}}},
            ("9", "hola", 7),
        ),
        (
            {"edited_message": {"text": "edit", "chat": {"id": 8}}},
            ("8", "edit", 8),
        ),
        ({}, (None, None, None)),
        ({"message": {"chat": {"id": 1}}}, (None, None, None)),
    ],
)
def test_extract_message(update, expected):
    assert polling._extract_message(update) == expected


def test_handle_update_ignora_update_invalido(monkeypatch):
    client = MagicMock()
    session_factory = MagicMock()
    monkeypatch.setattr(polling, "SessionLocal", session_factory)
    polling.handle_update(client, {})
    session_factory.assert_not_called()


def test_handle_update_procesa_y_cierra_db(monkeypatch):
    db = MagicMock()
    monkeypatch.setattr(polling, "SessionLocal", MagicMock(return_value=db))
    monkeypatch.setattr(
        polling.ExternalBotService,
        "process_message",
        MagicMock(return_value=SimpleNamespace(reply="respuesta")),
    )
    client = MagicMock()

    polling.handle_update(
        client,
        {"message": {"text": "hola", "chat": {"id": 7}, "from": {"id": 9}}},
    )

    client.send_message.assert_called_once_with(7, "respuesta")
    db.close.assert_called_once()


def test_handle_update_envia_error_si_servicio_falla(monkeypatch):
    db = MagicMock()
    monkeypatch.setattr(polling, "SessionLocal", MagicMock(return_value=db))
    monkeypatch.setattr(
        polling.ExternalBotService,
        "process_message",
        MagicMock(side_effect=RuntimeError("boom")),
    )
    client = MagicMock()

    polling.handle_update(
        client,
        {"message": {"text": "hola", "chat": {"id": 7}, "from": {"id": 9}}},
    )

    assert "Ha ocurrido un error" in client.send_message.call_args.args[1]
    db.close.assert_called_once()


def test_run_polling_procesa_update_y_sale_con_keyboard(monkeypatch):
    client = MagicMock()
    client.get_me.return_value = {"username": "bot"}
    client.get_updates.side_effect = [
        [{"update_id": 4, "message": {"text": "hola", "chat": {"id": 1}}}],
        KeyboardInterrupt(),
    ]
    monkeypatch.setattr(polling, "TelegramBotClient", MagicMock(return_value=client))
    handle = MagicMock()
    monkeypatch.setattr(polling, "handle_update", handle)

    polling.run_polling()

    client.delete_webhook.assert_called_once_with(drop_pending_updates=False)
    handle.assert_called_once()
    assert client.get_updates.call_args_list[1].kwargs["offset"] == 5


def test_run_polling_reintenta_http_exception(monkeypatch):
    client = MagicMock()
    client.get_me.return_value = {}
    client.get_updates.side_effect = [
        HTTPException(status_code=502, detail="temporal"),
        KeyboardInterrupt(),
    ]
    monkeypatch.setattr(polling, "TelegramBotClient", MagicMock(return_value=client))
    sleep = MagicMock()
    monkeypatch.setattr(polling.time, "sleep", sleep)

    polling.run_polling()
    sleep.assert_called_once_with(2)
