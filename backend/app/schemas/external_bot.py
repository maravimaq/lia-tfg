from datetime import datetime
from decimal import Decimal
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


ExternalBotChannel = Literal["TELEGRAM", "WHATSAPP", "TEST"]
ExternalBotRole = Literal["user", "assistant", "system"]


class ExternalBotMessageRequest(BaseModel):
    external_chat_id: str = Field(
        ...,
        min_length=1,
        description="Identificador externo del chat. En pruebas puedes usar 'telegram-test-juan'.",
    )
    message: str = Field(..., min_length=1)
    channel: ExternalBotChannel = "TELEGRAM"


class ExternalBotProductOption(BaseModel):
    index: int
    producto_id: int
    nombre: str
    marca: str | None = None
    supermercado: str
    precio_unitario: Decimal
    unidad_medida: str | None = None


class ExternalBotListOption(BaseModel):
    index: int
    lista_id: int
    nombre_lista: str
    total_estimado: Decimal


class ExternalBotMessageResponse(BaseModel):
    reply: str
    state: str
    channel: str
    external_chat_id: str
    product_options: list[ExternalBotProductOption] = Field(default_factory=list)
    list_options: list[ExternalBotListOption] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class ExternalBotStoredMessage(BaseModel):
    id_external_bot_message: int
    role: ExternalBotRole
    content: str
    metadata_json: dict[str, Any]
    fecha_creacion: datetime

    model_config = ConfigDict(from_attributes=True)


class ExternalBotHistoryResponse(BaseModel):
    external_chat_id: str
    channel: str
    state: str
    messages: list[ExternalBotStoredMessage]
