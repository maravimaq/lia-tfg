from __future__ import annotations

from typing import Any

import httpx
from fastapi import HTTPException, status

from app.core.config import settings


class TelegramBotClient:
    """Cliente mínimo para usar un bot real de Telegram desde LIA."""

    MAX_MESSAGE_LENGTH = 3900

    def __init__(self, token: str | None = None):
        self.token = token or settings.telegram_bot_token
        if not self.token:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Falta TELEGRAM_BOT_TOKEN en el archivo .env del backend.",
            )
        self.base_url = f"https://api.telegram.org/bot{self.token}"
        self.timeout = settings.telegram_request_timeout_seconds

    def _request(
        self,
        method: str,
        payload: dict[str, Any] | None = None,
        request_timeout: int | float | None = None,
    ) -> dict[str, Any]:
        url = f"{self.base_url}/{method}"
        timeout_seconds = request_timeout or self.timeout

        try:
            with httpx.Client(timeout=httpx.Timeout(timeout_seconds)) as client:
                response = client.post(url, json=payload or {})
                response.raise_for_status()
                data = response.json()
        except httpx.HTTPError as exc:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"No se pudo contactar con Telegram: {str(exc)}",
            ) from exc

        if not data.get("ok"):
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"Telegram devolvió un error: {data}",
            )

        return data

    def get_me(self) -> dict[str, Any]:
        return self._request("getMe").get("result", {})

    def send_message(self, chat_id: int | str, text: str) -> list[dict[str, Any]]:
        messages: list[dict[str, Any]] = []
        chunks = self._split_message(text)

        for chunk in chunks:
            data = self._request(
                "sendMessage",
                {
                    "chat_id": chat_id,
                    "text": chunk,
                    "disable_web_page_preview": True,
                },
            )
            messages.append(data.get("result", {}))

        return messages

    def get_updates(self, offset: int | None = None, timeout: int = 5) -> list[dict[str, Any]]:
        payload: dict[str, Any] = {
            "timeout": timeout,
            "allowed_updates": ["message"],
        }
        if offset is not None:
            payload["offset"] = offset

        # getUpdates usa long polling. En local/Windows algunos timeouts de lectura
        # pueden ocurrir aunque el bot esté bien conectado, especialmente cuando no
        # llegan mensajes. En polling los tratamos como ciclo vacío, no como error fatal.
        try:
            return self._request(
                "getUpdates",
                payload,
                request_timeout=max(timeout + 20, 30),
            ).get("result", [])
        except HTTPException as exc:
            detail = str(exc.detail).lower()
            if "timed out" in detail or "timeout" in detail:
                return []
            raise

    def set_webhook(self, webhook_url: str, secret_token: str | None = None) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "url": webhook_url,
            "allowed_updates": ["message"],
        }
        if secret_token:
            payload["secret_token"] = secret_token

        return self._request("setWebhook", payload).get("result", {})

    def delete_webhook(self, drop_pending_updates: bool = False) -> dict[str, Any]:
        return self._request(
            "deleteWebhook",
            {"drop_pending_updates": drop_pending_updates},
        ).get("result", {})

    def get_webhook_info(self) -> dict[str, Any]:
        return self._request("getWebhookInfo").get("result", {})

    def _split_message(self, text: str) -> list[str]:
        if len(text) <= self.MAX_MESSAGE_LENGTH:
            return [text]

        chunks: list[str] = []
        current = text
        while len(current) > self.MAX_MESSAGE_LENGTH:
            cut = current.rfind("\n", 0, self.MAX_MESSAGE_LENGTH)
            if cut == -1:
                cut = self.MAX_MESSAGE_LENGTH
            chunks.append(current[:cut].strip())
            current = current[cut:].strip()

        if current:
            chunks.append(current)

        return chunks
