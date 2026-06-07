from typing import ClassVar

from pydantic import BaseModel, ConfigDict, Field, field_validator


class PreferenciasBase(BaseModel):
    idioma: str = Field(default="es", description="Idioma de la aplicación")
    modo_oscuro: bool = Field(default=False, description="Activa o desactiva el modo oscuro")
    notificaciones: bool = Field(default=True, description="Activa o desactiva las notificaciones")
    unidad_peso: str = Field(default="kg", description="Unidad de peso preferida")
    unidad_precio: str = Field(default="EUR", description="Moneda preferida")
    supermercado_favorito: str | None = Field(
        default=None,
        description="Supermercado favorito del usuario",
    )

    _IDIOMAS_VALIDOS: ClassVar[set[str]] = {"es", "en"}
    _UNIDADES_PESO_VALIDAS: ClassVar[set[str]] = {"kg", "g", "lb"}
    _UNIDADES_PRECIO_VALIDAS: ClassVar[set[str]] = {"EUR", "USD"}
    _SUPERMERCADOS_VALIDOS: ClassVar[dict[str, str]] = {
        "mercadona": "Mercadona",
        "dia": "DIA",
        "día": "DIA",
        "carrefour": "Carrefour",
        "aldi": "ALDI",
        "alcampo": "Alcampo",
    }

    @field_validator("idioma")
    @classmethod
    def validar_idioma(cls, value: str) -> str:
        value = value.strip().lower()
        if value not in cls._IDIOMAS_VALIDOS:
            raise ValueError("El idioma debe ser 'es' o 'en'")
        return value

    @field_validator("unidad_peso")
    @classmethod
    def validar_unidad_peso(cls, value: str) -> str:
        value = value.strip().lower()
        if value not in cls._UNIDADES_PESO_VALIDAS:
            raise ValueError("La unidad de peso debe ser 'kg', 'g' o 'lb'")
        return value

    @field_validator("unidad_precio")
    @classmethod
    def validar_unidad_precio(cls, value: str) -> str:
        value = value.strip().upper()
        if value not in cls._UNIDADES_PRECIO_VALIDAS:
            raise ValueError("La unidad de precio debe ser 'EUR' o 'USD'")
        return value

    @field_validator("supermercado_favorito")
    @classmethod
    def validar_supermercado_favorito(cls, value: str | None) -> str | None:
        if value is None:
            return None

        normalized = value.strip()
        if not normalized:
            return None

        key = normalized.lower()
        if key not in cls._SUPERMERCADOS_VALIDOS:
            raise ValueError(
                "El supermercado favorito debe ser Mercadona, DIA, Carrefour, ALDI o Alcampo"
            )

        return cls._SUPERMERCADOS_VALIDOS[key]


class PreferenciasUpdate(BaseModel):
    idioma: str | None = None
    modo_oscuro: bool | None = None
    notificaciones: bool | None = None
    unidad_peso: str | None = None
    unidad_precio: str | None = None
    supermercado_favorito: str | None = None

    _IDIOMAS_VALIDOS: ClassVar[set[str]] = PreferenciasBase._IDIOMAS_VALIDOS
    _UNIDADES_PESO_VALIDAS: ClassVar[set[str]] = PreferenciasBase._UNIDADES_PESO_VALIDAS
    _UNIDADES_PRECIO_VALIDAS: ClassVar[set[str]] = PreferenciasBase._UNIDADES_PRECIO_VALIDAS
    _SUPERMERCADOS_VALIDOS: ClassVar[dict[str, str]] = PreferenciasBase._SUPERMERCADOS_VALIDOS

    @field_validator("idioma")
    @classmethod
    def validar_idioma(cls, value: str | None) -> str | None:
        if value is None:
            return None

        value = value.strip().lower()
        if value not in cls._IDIOMAS_VALIDOS:
            raise ValueError("El idioma debe ser 'es' o 'en'")
        return value

    @field_validator("unidad_peso")
    @classmethod
    def validar_unidad_peso(cls, value: str | None) -> str | None:
        if value is None:
            return None

        value = value.strip().lower()
        if value not in cls._UNIDADES_PESO_VALIDAS:
            raise ValueError("La unidad de peso debe ser 'kg', 'g' o 'lb'")
        return value

    @field_validator("unidad_precio")
    @classmethod
    def validar_unidad_precio(cls, value: str | None) -> str | None:
        if value is None:
            return None

        value = value.strip().upper()
        if value not in cls._UNIDADES_PRECIO_VALIDAS:
            raise ValueError("La unidad de precio debe ser 'EUR' o 'USD'")
        return value

    @field_validator("supermercado_favorito")
    @classmethod
    def validar_supermercado_favorito(cls, value: str | None) -> str | None:
        if value is None:
            return None

        normalized = value.strip()
        if not normalized:
            return None

        key = normalized.lower()
        if key not in cls._SUPERMERCADOS_VALIDOS:
            raise ValueError(
                "El supermercado favorito debe ser Mercadona, DIA, Carrefour, ALDI o Alcampo"
            )

        return cls._SUPERMERCADOS_VALIDOS[key]


class PreferenciasResponse(PreferenciasBase):
    id_preferencia: int
    usuario_id: int

    model_config = ConfigDict(from_attributes=True)
