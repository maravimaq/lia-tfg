from __future__ import annotations

import logging
import time
from typing import Any

from fastapi import HTTPException

from app.db.session import SessionLocal
import app.db.base  # noqa: F401  # registra todos los modelos SQLAlchemy antes de procesar mensajes
from app.services.external_bot_service import ExternalBotService
from app.services.telegram_bot_client import TelegramBotClient

logging.basicConfig(level=logging.INFO, format="[%(asctime)s] %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)


def _extract_message(update: dict[str, Any]) -> tuple[str | None, str | None, int | None]:
    message = update.get("message") or update.get("edited_message") or {}
    text = message.get("text")
    chat = message.get("chat") or {}
    from_data = message.get("from") or {}

    chat_id = chat.get("id")
    external_user_id = from_data.get("id") or chat_id

    if text is None or chat_id is None or external_user_id is None:
        return None, None, None

    return str(external_user_id), text, int(chat_id)


def handle_update(client: TelegramBotClient, update: dict[str, Any]) -> None:
    external_user_id, text, chat_id = _extract_message(update)
    if external_user_id is None or text is None or chat_id is None:
        return

    db = SessionLocal()
    try:
        response = ExternalBotService.process_message(
            db,
            plataforma="telegram",
            external_user_id=external_user_id,
            text=text,
        )
        client.send_message(chat_id, response.reply)
    except Exception:
        logger.exception("Error procesando update de Telegram")
        try:
            client.send_message(
                chat_id,
                "Ha ocurrido un error procesando tu mensaje. Inténtalo de nuevo en unos segundos.",
            )
        except Exception:
            logger.exception("No se pudo enviar mensaje de error a Telegram")
    finally:
        db.close()


def run_polling() -> None:
    client = TelegramBotClient()

    me = client.get_me()
    logger.info("Bot conectado: @%s", me.get("username", "sin_username"))

    # getUpdates no funciona si hay webhook activo.
    client.delete_webhook(drop_pending_updates=False)

    offset: int | None = None
    while True:
        try:
            updates = client.get_updates(offset=offset, timeout=5)
            for update in updates:
                update_id = update.get("update_id")
                if update_id is not None:
                    offset = int(update_id) + 1
                handle_update(client, update)
        except KeyboardInterrupt:
            logger.info("Polling detenido por el usuario")
            break
        except HTTPException as exc:
            logger.warning("Error temporal contactando con Telegram: %s", exc.detail)
            time.sleep(2)
        except Exception:
            logger.exception("Error en polling de Telegram")
            time.sleep(2)


if __name__ == "__main__":
    run_polling()
