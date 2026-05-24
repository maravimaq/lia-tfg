from __future__ import annotations

import json
import logging
import re
from typing import Any, Optional
from urllib.parse import urljoin

import httpx
from bs4 import BeautifulSoup

from app.scraping.base import (
    BaseScraper,
    ScrapedProduct,
    ScraperBlockedError,
    ScraperRunResult,
    clean_text,
    parse_price,
)
from app.scraping.validators import validate_scraped_product

try:
    from playwright.async_api import TimeoutError as PlaywrightTimeoutError
    from playwright.async_api import async_playwright
except ImportError:  # pragma: no cover
    PlaywrightTimeoutError = None
    async_playwright = None


logger = logging.getLogger(__name__)


class CarrefourScraper(BaseScraper):
    """
    Scraper para Carrefour España.

    Estrategia:
    - Intentar primero HTTP normal con httpx.
    - Si Carrefour bloquea HTTP normal, usar Playwright como navegador real.
    - Extraer productos desde window["impressions"], que contiene datos estructurados.
    - No parsear texto visible de forma laxa.
    """

    supermercado = "Carrefour"
    base_url = "https://www.carrefour.es"

    START_URLS = [
        "https://www.carrefour.es/supermercado/la-despensa/cat20001/c",
        "https://www.carrefour.es/supermercado/frescos/cat20002/c",
        "https://www.carrefour.es/supermercado/bebidas/cat20005/c",
        "https://www.carrefour.es/supermercado/congelados/cat20004/c",
        "https://www.carrefour.es/supermercado/bebe/cat20010/c",
        "https://www.carrefour.es/supermercado/perfumeria-e-higiene/cat20006/c",
        "https://www.carrefour.es/supermercado/limpieza-y-hogar/cat20007/c",
    ]

    IMPRESSIONS_RE = re.compile(
        r'window\["impressions"\]\s*=\s*(\[.*?\]);',
        re.DOTALL,
    )

    def __init__(
        self,
        *,
        timeout_seconds: int = 20,
        user_agent: str,
        max_urls: int = 7,
        max_products_per_url: int = 80,
        use_playwright_fallback: bool = True,
    ) -> None:
        super().__init__(
            timeout_seconds=timeout_seconds,
            user_agent=user_agent,
        )
        self.max_urls = max_urls
        self.max_products_per_url = max_products_per_url
        self.use_playwright_fallback = use_playwright_fallback

    async def scrape(self) -> ScraperRunResult:
        products: list[ScrapedProduct] = []
        rejected_count = 0
        processed_urls = 0
        blocked_urls = 0
        playwright_urls = 0

        try:
            for url in self.START_URLS[: self.max_urls]:
                html: Optional[str] = None

                try:
                    html = await self.get_text(
                        url,
                        headers=self._carrefour_headers(),
                    )
                except ScraperBlockedError:
                    blocked_urls += 1

                    if self.use_playwright_fallback:
                        html = await self._get_text_with_playwright(url)
                        if html:
                            playwright_urls += 1
                    else:
                        continue

                except httpx.HTTPStatusError as exc:
                    logger.warning(
                        "Carrefour URL omitida por HTTP %s: %s",
                        exc.response.status_code,
                        url,
                    )
                    continue

                if not html:
                    continue

                processed_urls += 1

                url_products, url_rejected = self._parse_html(
                    html,
                    source_url=url,
                )

                products.extend(url_products)
                rejected_count += url_rejected

            products = self._deduplicate_products(products)

            if not products and blocked_urls > 0 and processed_urls == 0:
                return ScraperRunResult.blocked(
                    supermercado=self.supermercado,
                    message="Carrefour ha bloqueado las peticiones HTTP y Playwright no obtuvo productos.",
                    metadata={
                        "blocked_urls": blocked_urls,
                        "processed_urls": processed_urls,
                        "playwright_urls": playwright_urls,
                    },
                )

            return ScraperRunResult(
                supermercado=self.supermercado,
                status="success" if products else "empty",
                products=products,
                detected_count=len(products) + rejected_count,
                accepted_count=len(products),
                rejected_count=rejected_count,
                message=(
                    f"Carrefour procesado: {processed_urls} URLs, "
                    f"{playwright_urls} con Playwright, "
                    f"{len(products)} productos aceptados."
                ),
                metadata={
                    "mode": "window_impressions_with_playwright_fallback",
                    "processed_urls": processed_urls,
                    "blocked_urls": blocked_urls,
                    "playwright_urls": playwright_urls,
                    "max_urls": self.max_urls,
                    "max_products_per_url": self.max_products_per_url,
                },
            )

        except ScraperBlockedError as exc:
            logger.warning("Carrefour bloqueado: %s", exc)
            return ScraperRunResult.blocked(
                supermercado=self.supermercado,
                message=str(exc),
            )

        except httpx.HTTPStatusError as exc:
            logger.exception("Error HTTP scrapeando Carrefour")
            return ScraperRunResult.failed(
                supermercado=self.supermercado,
                error=f"Error HTTP en Carrefour: {exc.response.status_code}",
                metadata={
                    "url": str(exc.request.url),
                    "response": exc.response.text[:500],
                },
            )

        except Exception as exc:
            logger.exception("Error inesperado scrapeando Carrefour")
            return ScraperRunResult.failed(
                supermercado=self.supermercado,
                error=f"Error inesperado en Carrefour: {exc}",
            )

    async def _get_text_with_playwright(self, url: str) -> Optional[str]:
        if async_playwright is None:
            logger.warning(
                "Playwright no está instalado. No se puede usar fallback para Carrefour."
            )
            return None

        logger.info("Carrefour: usando Playwright para %s", url)

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)

            context = await browser.new_context(
                user_agent=self.user_agent,
                locale="es-ES",
                viewport={"width": 1366, "height": 900},
            )

            async def block_heavy_resources(route):
                resource_type = route.request.resource_type

                if resource_type in {"image", "font", "media"}:
                    await route.abort()
                else:
                    await route.continue_()

            await context.route("**/*", block_heavy_resources)

            page = await context.new_page()

            try:
                await page.goto(
                    url,
                    wait_until="domcontentloaded",
                    timeout=max(self.timeout_seconds * 1000, 60000),
                )
            except Exception as exc:
                if PlaywrightTimeoutError is not None and isinstance(exc, PlaywrightTimeoutError):
                    logger.warning(
                        "Timeout cargando Carrefour con Playwright, se continúa con HTML parcial: %s",
                        url,
                    )
                else:
                    logger.warning(
                        "Error cargando Carrefour con Playwright: url=%s error=%s",
                        url,
                        exc,
                    )
                    await context.close()
                    await browser.close()
                    return None

            await self._accept_cookies_if_present(page)

            await page.wait_for_timeout(2500)

            for _ in range(4):
                await page.mouse.wheel(0, 900)
                await page.wait_for_timeout(700)

            html = await page.content()

            await context.close()
            await browser.close()

            return html

    async def _accept_cookies_if_present(self, page) -> None:
        cookie_texts = [
            "Aceptar todo",
            "Aceptar",
            "Aceptar cookies",
            "Guardar configuración",
            "Guardar configuracion",
        ]

        for text in cookie_texts:
            try:
                locator = page.get_by_text(text, exact=False).first

                if await locator.count() > 0:
                    await locator.click(timeout=2500)
                    return
            except Exception:
                continue

    def _parse_html(
        self,
        html: str,
        *,
        source_url: str,
    ) -> tuple[list[ScrapedProduct], int]:
        products: list[ScrapedProduct] = []
        rejected_count = 0

        category = self._extract_category_from_html_or_url(html, source_url)
        raw_items = self._extract_impressions(html)

        for item in raw_items[: self.max_products_per_url]:
            try:
                product = self._build_product_from_impression(
                    item,
                    category=category,
                    source_url=source_url,
                )
            except Exception as exc:
                rejected_count += 1
                logger.debug("Producto Carrefour rechazado por parseo: %s", exc)
                continue

            is_valid, reason = validate_scraped_product(product)

            if not is_valid:
                rejected_count += 1
                logger.debug(
                    "Producto Carrefour inválido: nombre=%r precio=%r motivo=%s",
                    product.nombre,
                    product.precio,
                    reason,
                )
                continue

            products.append(product)

        return products, rejected_count

    def _extract_impressions(self, html: str) -> list[dict[str, Any]]:
        match = self.IMPRESSIONS_RE.search(html)

        if not match:
            return []

        raw_json = match.group(1)

        try:
            data = json.loads(raw_json)
        except json.JSONDecodeError as exc:
            logger.warning("No se pudo parsear window['impressions']: %s", exc)
            return []

        if not isinstance(data, list):
            return []

        return [item for item in data if isinstance(item, dict)]

    def _build_product_from_impression(
        self,
        item: dict[str, Any],
        *,
        category: Optional[str],
        source_url: str,
    ) -> ScrapedProduct:
        raw_name = self._first_non_empty(
            item.get("item_name"),
            item.get("name"),
            item.get("product_name"),
        )

        price = self._first_non_empty(
            item.get("price"),
            item.get("item_price"),
        )

        if not raw_name:
            raise ValueError("Producto Carrefour sin nombre")

        if price is None:
            raise ValueError(f"Producto Carrefour sin precio: {raw_name}")

        name = self._humanize_slug_name(str(raw_name))

        brand = self._first_non_empty(
            item.get("item_brand"),
            item.get("brand"),
        )

        external_id = self._first_non_empty(
            item.get("item_id"),
            item.get("item_internal_id"),
            item.get("item_sms"),
            item.get("item_ean"),
        )

        return ScrapedProduct(
            nombre=name,
            precio=parse_price(price),
            supermercado=self.supermercado,
            marca=self._format_brand(brand),
            categoria=category,
            unidad_medida=self._guess_unit_from_name(name),
            formato=self._guess_format_from_name(name),
            external_id=str(external_id) if external_id is not None else None,
            url_producto=self._build_product_url(external_id, source_url),
            imagen_url=None,
            metadata={
                "source": "carrefour_window_impressions",
                "source_url": source_url,
                "item_ean": item.get("item_ean"),
                "item_category": item.get("item_category"),
                "item_internal_id": item.get("item_internal_id"),
                "item_shipping": item.get("item_shipping"),
            },
        )

    def _extract_category_from_html_or_url(
        self,
        html: str,
        source_url: str,
    ) -> Optional[str]:
        soup = BeautifulSoup(html, "html.parser")

        heading = soup.find("h1")
        if heading:
            text = clean_text(heading.get_text(" ", strip=True))
            if text:
                return text.title()

        title = soup.find("title")
        if title:
            text = clean_text(title.get_text(" ", strip=True))
            if text:
                return text.split("-")[0].strip().title()

        parts = [
            part
            for part in source_url.split("/")
            if part
            and part not in {
                "https:",
                "www.carrefour.es",
                "supermercado",
                "c",
            }
        ]

        for part in reversed(parts):
            if part.startswith("cat"):
                continue

            return part.replace("-", " ").title()

        return None

    def _humanize_slug_name(self, value: str) -> str:
        text = clean_text(value)
        text = text.replace("-", " ").lower()

        replacements = {
            r"\batun\b": "atún",
            r"\bazucar\b": "azúcar",
            r"\bcafe\b": "café",
            r"\bsin azucares\b": "sin azúcares",
            r"\banadidos\b": "añadidos",
            r"\bcategoria\b": "categoría",
        }

        for pattern, replacement in replacements.items():
            text = re.sub(pattern, replacement, text)

        return text.strip().capitalize()

    def _format_brand(self, value: Optional[Any]) -> Optional[str]:
        text = clean_text(value)

        if not text:
            return None

        return text.replace("-", " ").title()

    def _build_product_url(
        self,
        external_id: Optional[Any],
        source_url: str,
    ) -> Optional[str]:
        if external_id:
            return f"{self.base_url}/supermercado/producto/{external_id}"

        return source_url

    def _guess_unit_from_name(self, name: str) -> Optional[str]:
        text = name.lower()

        if re.search(r"\b\d+(?:[,.]\d+)?\s*(kg|kilo|kilos)\b", text):
            return "KG"

        if re.search(r"\b\d+(?:[,.]\d+)?\s*g\b", text):
            return "G"

        if re.search(r"\b\d+(?:[,.]\d+)?\s*l\b", text):
            return "L"

        if re.search(r"\b\d+(?:[,.]\d+)?\s*ml\b", text):
            return "ML"

        if re.search(r"\b\d+\s*(ud|uds|unidades)\b", text):
            return "UD."

        return None

    def _guess_format_from_name(self, name: str) -> Optional[str]:
        patterns = [
            r"\bpack de \d+\s+[a-záéíóúüñ.]+(?:\s+de\s+\d+(?:[,.]\d+)?\s*(?:g|kg|ml|l))?",
            r"\b\d+\s*x\s*\d+(?:[,.]\d+)?\s*(?:g|kg|ml|l)\b",
            r"\b\d+(?:[,.]\d+)?\s*(?:g|kg|ml|l)\b",
            r"\b\d+\s*(?:ud|uds|unidades)\b",
        ]

        lowered = name.lower()

        for pattern in patterns:
            match = re.search(pattern, lowered, re.IGNORECASE)

            if match:
                return match.group(0).strip()

        return None

    def _carrefour_headers(self) -> dict[str, str]:
        return {
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Referer": "https://www.carrefour.es/supermercado",
            "Origin": "https://www.carrefour.es",
        }

    def _absolute_url(self, value: Optional[Any]) -> Optional[str]:
        text = clean_text(value)

        if not text:
            return None

        if text.startswith("http://") or text.startswith("https://"):
            return text

        return urljoin(self.base_url or "https://www.carrefour.es", text)

    def _deduplicate_products(
        self,
        products: list[ScrapedProduct],
    ) -> list[ScrapedProduct]:
        deduplicated: list[ScrapedProduct] = []
        seen: set[str] = set()

        for product in products:
            key = f"{product.normalized_supermarket}::{product.normalized_name}"

            if key in seen:
                continue

            seen.add(key)
            deduplicated.append(product)

        return deduplicated

    @staticmethod
    def _first_non_empty(*values: Any) -> Optional[Any]:
        for value in values:
            if value is None:
                continue

            if isinstance(value, str) and not clean_text(value):
                continue

            return value

        return None