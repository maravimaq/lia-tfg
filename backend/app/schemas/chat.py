from datetime import datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


ListChatIntent = Literal[
    "analizar_lista",
    "comparar_lista_supermercados",
    "recomendar_cantidad",
    "sugerir_ahorro",
    "sugerir_sustituciones",
    "detectar_excesos",
    "pregunta_general_lista",
    "fuera_de_alcance",
]


class ListChatMessageRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=1000)


class ListChatSuggestion(BaseModel):
    type: Literal[
        "info",
        "warning",
        "saving",
        "quantity",
        "substitution",
    ]
    title: str
    description: str


class ListChatMessageResponse(BaseModel):
    reply: str
    intent: ListChatIntent
    suggestions: list[ListChatSuggestion] = Field(default_factory=list)
    context_summary: dict = Field(default_factory=dict)


class ListChatAIResponse(BaseModel):
    intent: ListChatIntent
    reply: str
    suggestions: list[ListChatSuggestion]
    confidence: float = Field(..., ge=0, le=1)


class ChatProductoCatalogoResumen(BaseModel):
    id_producto: int
    nombre: str
    marca: str | None = None
    categoria: str | None = None
    supermercado: str
    precio_unitario: Decimal
    unidad_medida: str | None = None

    model_config = ConfigDict(from_attributes=True)


class ChatProductoListaResumen(BaseModel):
    id_producto_lista: int
    producto_id: int
    nombre: str
    marca: str | None = None
    categoria: str | None = None
    supermercado: str
    cantidad: int
    precio_unitario: Decimal
    precio_estimado: Decimal
    unidad_medida: str | None = None


class ChatListaResumen(BaseModel):
    id_lista: int
    nombre_lista: str
    total_estimado: Decimal
    productos: list[ChatProductoListaResumen]

class ListChatStoredMessage(BaseModel):
    id_chat_message: int
    lista_id: int
    usuario_id: int
    role: Literal["user", "assistant"]
    content: str
    intent: ListChatIntent | None = None
    suggestions: list[ListChatSuggestion] = Field(default_factory=list)
    context_summary: dict = Field(default_factory=dict)
    fecha_creacion: datetime

    model_config = ConfigDict(from_attributes=True)
