from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class ExternalBotIncomingMessage(BaseModel):
    plataforma: str = Field(default="telegram", examples=["telegram"])
    external_user_id: str = Field(examples=["123456789"])
    texto: str = Field(examples=["añadir leche"])


class ExternalBotOption(BaseModel):
    numero: int
    label: str
    value: str | int | None = None


class ExternalBotResponse(BaseModel):
    reply: str
    action: str = "message"
    state: str | None = None
    options: list[ExternalBotOption] = []
    added_to_list_id: int | None = None
    created_list_id: int | None = None


class ExternalBotLinkCodeCreate(BaseModel):
    plataforma: str = "telegram"


class ExternalBotLinkCodeResponse(BaseModel):
    codigo: str
    plataforma: str
    fecha_expiracion: datetime
    instrucciones: str


class ExternalBotBindingStatusResponse(BaseModel):
    plataforma: str
    vinculado: bool
    external_user_id: str | None = None
    estado_conversacion: str | None = None
    fecha_vinculacion: datetime | None = None


class TelegramWebhookUpdate(BaseModel):
    """
    Estructura flexible para aceptar updates reales/simulados de Telegram.
    Para el TFG basta con extraer message.from.id y message.text.
    """

    update_id: int | None = None
    message: dict[str, Any] | None = None


class ExternalBotMessageResponse(BaseModel):
    id_mensaje_bot: int
    direccion: str
    texto: str
    payload: dict[str, Any] | None = None
    fecha_creacion: datetime

    model_config = ConfigDict(from_attributes=True)



class TelegramBotInfoResponse(BaseModel):
    configured: bool
    id: int | None = None
    username: str | None = None
    first_name: str | None = None
    can_join_groups: bool | None = None
    can_read_all_group_messages: bool | None = None
    supports_inline_queries: bool | None = None


class TelegramWebhookActionResponse(BaseModel):
    ok: bool
    message: str
    webhook_url: str | None = None
    telegram_result: Any | None = None


class TelegramWebhookProcessResponse(BaseModel):
    ok: bool
    ignored: bool = False
    reply: str | None = None
    action: str | None = None
    state: str | None = None
