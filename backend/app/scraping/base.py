from __future__ import annotations

import logging
import re
import unicodedata
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation
from typing import Any, Optional

import httpx

logger = logging.getLogger(__name__)

DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124.0.0.0 Safari/537.36"
)

_PRICE_CLEAN_RE = re.compile(r"[^\d,.\-]")


@dataclass(slots=True)
class ScrapedProduct:
    """
    Producto extraído desde una fuente externa.

    Esta clase NO representa directamente una entidad SQLAlchemy.
    Es una estructura intermedia común para todos los scrapers.
    """

    nombre: str
    precio: Decimal
    supermercado: str

    marca: Optional[str] = None
    categoria: Optional[str] = None
    unidad_medida: Optional[str] = None
    formato: Optional[str] = None

    external_id: Optional[str] = None
    url_producto: Optional[str] = None
    imagen_url: Optional[str] = None

    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        self.nombre = clean_text(self.nombre)
        self.supermercado = clean_text(self.supermercado)

        self.marca = clean_optional_text(self.marca)
        self.categoria = clean_optional_text(self.categoria)
        self.unidad_medida = clean_optional_text(self.unidad_medida)
        self.formato = clean_optional_text(self.formato)
        self.external_id = clean_optional_text(self.external_id)
        self.url_producto = clean_optional_text(self.url_producto)
        self.imagen_url = clean_optional_text(self.imagen_url)

        self.precio = ensure_decimal_price(self.precio)

    @property
    def normalized_name(self) -> str:
        return normalize_for_matching(self.nombre)

    @property
    def normalized_supermarket(self) -> str:
        return normalize_for_matching(self.supermercado)

    def to_debug_dict(self) -> dict[str, Any]:
        return {
            "nombre": self.nombre,
            "precio": str(self.precio),
            "supermercado": self.supermercado,
            "marca": self.marca,
            "categoria": self.categoria,
            "unidad_medida": self.unidad_medida,
            "formato": self.formato,
            "external_id": self.external_id,
            "url_producto": self.url_producto,
            "imagen_url": self.imagen_url,
            "metadata": self.metadata,
        }


@dataclass(slots=True)
class ScraperRunResult:
    """
    Resultado de ejecución de un scraper concreto.

    status esperado:
    - "success": scraping correcto con productos válidos.
    - "empty": scraping correcto pero sin productos.
    - "partial": scraping parcialmente correcto.
    - "blocked": fuente bloqueada, por ejemplo HTTP 403.
    - "error": error no recuperable.
    """

    supermercado: str
    status: str
    products: list[ScrapedProduct] = field(default_factory=list)

    detected_count: int = 0
    accepted_count: int = 0
    rejected_count: int = 0

    message: Optional[str] = None
    error: Optional[str] = None
    metadata: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def success(
        cls,
        supermercado: str,
        products: list[ScrapedProduct],
        message: Optional[str] = None,
        metadata: Optional[dict[str, Any]] = None,
    ) -> "ScraperRunResult":
        return cls(
            supermercado=supermercado,
            status="success" if products else "empty",
            products=products,
            detected_count=len(products),
            accepted_count=len(products),
            rejected_count=0,
            message=message,
            metadata=metadata or {},
        )

    @classmethod
    def blocked(
        cls,
        supermercado: str,
        message: str,
        metadata: Optional[dict[str, Any]] = None,
    ) -> "ScraperRunResult":
        return cls(
            supermercado=supermercado,
            status="blocked",
            message=message,
            metadata=metadata or {},
        )

    @classmethod
    def failed(
        cls,
        supermercado: str,
        error: str,
        metadata: Optional[dict[str, Any]] = None,
    ) -> "ScraperRunResult":
        return cls(
            supermercado=supermercado,
            status="error",
            error=error,
            metadata=metadata or {},
        )


class BaseScraper(ABC):
    """
    Clase base para todos los scrapers de supermercados.

    Cada scraper concreto debe implementar `scrape`.
    """

    supermercado: str
    base_url: Optional[str] = None

    def __init__(
        self,
        *,
        timeout_seconds: int = 20,
        user_agent: str = DEFAULT_USER_AGENT,
        client: Optional[httpx.AsyncClient] = None,
    ) -> None:
        self.timeout_seconds = timeout_seconds
        self.user_agent = user_agent
        self._external_client = client
        self._client: Optional[httpx.AsyncClient] = client

    @abstractmethod
    async def scrape(self) -> ScraperRunResult:
        raise NotImplementedError

    async def __aenter__(self) -> "BaseScraper":
        await self._ensure_client()
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        await self.close()

    async def close(self) -> None:
        if self._client is not None and self._external_client is None:
            await self._client.aclose()

        self._client = self._external_client

    async def get_json(
        self,
        url: str,
        *,
        params: Optional[dict[str, Any]] = None,
        headers: Optional[dict[str, str]] = None,
    ) -> Any:
        response = await self._request(
            "GET",
            url,
            params=params,
            headers=headers,
        )

        return response.json()

    async def get_text(
        self,
        url: str,
        *,
        params: Optional[dict[str, Any]] = None,
        headers: Optional[dict[str, str]] = None,
    ) -> str:
        response = await self._request(
            "GET",
            url,
            params=params,
            headers=headers,
        )

        return response.text

    async def _request(
        self,
        method: str,
        url: str,
        *,
        params: Optional[dict[str, Any]] = None,
        headers: Optional[dict[str, str]] = None,
    ) -> httpx.Response:
        client = await self._ensure_client()

        request_headers = self.default_headers()
        if headers:
            request_headers.update(headers)

        logger.debug(
            "Scraping request: supermarket=%s method=%s url=%s params=%s",
            self.supermercado,
            method,
            url,
            params,
        )

        response = await client.request(
            method,
            url,
            params=params,
            headers=request_headers,
        )

        if response.status_code == 403:
            raise ScraperBlockedError(
                f"{self.supermercado} ha devuelto HTTP 403 en {url}"
            )

        response.raise_for_status()
        return response

    async def _ensure_client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(
                timeout=httpx.Timeout(self.timeout_seconds),
                follow_redirects=True,
            )

        return self._client

    def default_headers(self) -> dict[str, str]:
        return {
            "User-Agent": self.user_agent,
            "Accept": "application/json,text/html;q=0.9,*/*;q=0.8",
            "Accept-Language": "es-ES,es;q=0.9,en;q=0.8",
            "Connection": "keep-alive",
        }

    def build_product(
        self,
        *,
        nombre: Any,
        precio: Any,
        marca: Optional[Any] = None,
        categoria: Optional[Any] = None,
        unidad_medida: Optional[Any] = None,
        formato: Optional[Any] = None,
        external_id: Optional[Any] = None,
        url_producto: Optional[Any] = None,
        imagen_url: Optional[Any] = None,
        metadata: Optional[dict[str, Any]] = None,
    ) -> ScrapedProduct:
        return ScrapedProduct(
            nombre=str(nombre),
            precio=parse_price(precio),
            supermercado=self.supermercado,
            marca=str(marca) if marca is not None else None,
            categoria=str(categoria) if categoria is not None else None,
            unidad_medida=str(unidad_medida) if unidad_medida is not None else None,
            formato=str(formato) if formato is not None else None,
            external_id=str(external_id) if external_id is not None else None,
            url_producto=str(url_producto) if url_producto is not None else None,
            imagen_url=str(imagen_url) if imagen_url is not None else None,
            metadata=metadata or {},
        )


class ScraperError(Exception):
    pass


class ScraperBlockedError(ScraperError):
    pass


def clean_text(value: Any) -> str:
    if value is None:
        return ""

    text = str(value)
    text = text.replace("\xa0", " ")
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def clean_optional_text(value: Optional[Any]) -> Optional[str]:
    text = clean_text(value)
    return text or None


def normalize_for_matching(value: Any) -> str:
    text = clean_text(value).lower()

    text = unicodedata.normalize("NFKD", text)
    text = "".join(char for char in text if not unicodedata.combining(char))

    text = re.sub(r"[^a-z0-9]+", " ", text)
    text = re.sub(r"\s+", " ", text)

    return text.strip()


def parse_price(value: Any) -> Decimal:
    if isinstance(value, Decimal):
        return ensure_decimal_price(value)

    if isinstance(value, int | float):
        return ensure_decimal_price(Decimal(str(value)))

    text = clean_text(value)
    if not text:
        raise ValueError("No se puede parsear un precio vacío")

    cleaned = _PRICE_CLEAN_RE.sub("", text)

    if not cleaned:
        raise ValueError(f"No se puede parsear el precio: {value!r}")

    # Casos tipo "1.234,56"
    if "," in cleaned and "." in cleaned:
        if cleaned.rfind(",") > cleaned.rfind("."):
            cleaned = cleaned.replace(".", "").replace(",", ".")
        else:
            cleaned = cleaned.replace(",", "")

    # Casos tipo "1,25"
    elif "," in cleaned:
        cleaned = cleaned.replace(",", ".")

    try:
        return ensure_decimal_price(Decimal(cleaned))
    except InvalidOperation as exc:
        raise ValueError(f"No se puede parsear el precio: {value!r}") from exc


def ensure_decimal_price(value: Decimal) -> Decimal:
    if value <= 0:
        raise ValueError(f"El precio debe ser mayor que 0: {value}")

    return value.quantize(Decimal("0.01"))