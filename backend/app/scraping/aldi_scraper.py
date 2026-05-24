from __future__ import annotations

import asyncio
import logging
import re
from typing import Any, Optional
from urllib.parse import urljoin

import httpx
from bs4 import BeautifulSoup, Tag

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


class AldiScraper(BaseScraper):
    """
    Scraper para ALDI España.

    ALDI no expone un catálogo completo permanente como Mercadona/DIA.
    Su web pública expone sobre todo ofertas y folletos semanales.

    Estrategia:
    - Entrar en páginas generales de ofertas.
    - Extraer enlaces de fichas .article.html.
    - Visitar cada ficha.
    - Parsear nombre, precio, formato, unidad y fechas de validez cuando aparezcan.
    """

    supermercado = "ALDI"
    base_url = "https://www.aldi.es"

    START_URLS = [
        "https://www.aldi.es/ofertas.html",
        "https://www.aldi.es/ofertas-proxima-semana.html",
        "https://www.aldi.es/folleto.html",
    ]

    ARTICLE_LINK_RE = re.compile(
        r"""["'](?P<href>[^"']*?\.article\.html)["']""",
        re.IGNORECASE,
    )

    PRICE_RE = re.compile(
        r"(?<!\d)(\d{1,3}(?:[,.]\d{1,2})?)\s*€",
        re.IGNORECASE,
    )

    OLD_PRICE_HINT_RE = re.compile(
        r"(antes|precio anterior|tachado|rebajado|-%|- \d+%)",
        re.IGNORECASE,
    )

    UNIT_PRICE_HINT_RE = re.compile(
        r"(\bkg\s*=|\bl\s*=|\b100\s*g\s*=|\b100\s*ml\s*=|€/kg|€/l|euros?/kg|euros?/l)",
        re.IGNORECASE,
    )

    DATE_VALIDITY_RE = re.compile(
        r"Precios válidos del\s+([0-9]{2}-[0-9]{2}-[0-9]{4})\s+al\s+([0-9]{2}-[0-9]{2}-[0-9]{4})",
        re.IGNORECASE,
    )

    FORMAT_PATTERNS = [
        r"\b\d+(?:[,.]\d+)?\s*(?:kg|g|l|ml)\b",
        r"\b\d+\s*x\s*\d+(?:[,.]\d+)?\s*(?:kg|g|l|ml)\b",
        r"\bpack\s+de\s+\d+\b",
        r"\b\d+\s*(?:ud|uds|unidades)\b",
    ]

    def __init__(
        self,
        *,
        timeout_seconds: int = 20,
        user_agent: str,
        max_listing_urls: int = 3,
        max_article_links: int = 120,
        max_products: int = 120,
        delay_seconds: float = 0.15,
        use_playwright_fallback: bool = True,
    ) -> None:
        super().__init__(
            timeout_seconds=timeout_seconds,
            user_agent=user_agent,
        )
        self.max_listing_urls = max_listing_urls
        self.max_article_links = max_article_links
        self.max_products = max_products
        self.delay_seconds = delay_seconds
        self.use_playwright_fallback = use_playwright_fallback

    async def scrape(self) -> ScraperRunResult:
        products: list[ScrapedProduct] = []
        rejected_count = 0
        processed_listing_urls = 0
        processed_article_urls = 0
        playwright_urls = 0
        blocked_urls = 0

        try:
            article_urls: list[str] = []

            for listing_url in self.START_URLS[: self.max_listing_urls]:
                html, used_playwright, was_blocked = await self._get_html(listing_url)

                if was_blocked:
                    blocked_urls += 1

                if used_playwright:
                    playwright_urls += 1

                if not html:
                    continue

                processed_listing_urls += 1

                article_urls.extend(
                    self._extract_article_links(
                        html,
                        source_url=listing_url,
                    )
                )

            article_urls = self._unique_urls(article_urls)[: self.max_article_links]

            if not article_urls:
                return ScraperRunResult(
                    supermercado=self.supermercado,
                    status="empty",
                    products=[],
                    detected_count=0,
                    accepted_count=0,
                    rejected_count=0,
                    message="ALDI procesado, pero no se encontraron fichas .article.html.",
                    metadata={
                        "mode": "aldi_article_pages",
                        "processed_listing_urls": processed_listing_urls,
                        "processed_article_urls": processed_article_urls,
                        "playwright_urls": playwright_urls,
                        "blocked_urls": blocked_urls,
                        "article_links": 0,
                        "note": "ALDI expone principalmente ofertas/folletos, no catálogo permanente completo.",
                    },
                )

            for article_url in article_urls:
                if len(products) >= self.max_products:
                    break

                html, used_playwright, was_blocked = await self._get_html(article_url)

                if was_blocked:
                    blocked_urls += 1

                if used_playwright:
                    playwright_urls += 1

                if not html:
                    continue

                processed_article_urls += 1

                try:
                    product = self._parse_article_page(
                        html,
                        source_url=article_url,
                    )
                except Exception as exc:
                    rejected_count += 1
                    logger.debug("Ficha ALDI rechazada por parseo: %s", exc)
                    continue

                is_valid, reason = validate_scraped_product(product)

                if not is_valid:
                    rejected_count += 1
                    logger.debug(
                        "Producto ALDI inválido: nombre=%r precio=%r motivo=%s",
                        product.nombre,
                        product.precio,
                        reason,
                    )
                    continue

                products.append(product)

                if self.delay_seconds > 0:
                    await asyncio.sleep(self.delay_seconds)

            products = self._deduplicate_products(products)

            return ScraperRunResult(
                supermercado=self.supermercado,
                status="success" if products else "empty",
                products=products,
                detected_count=len(products) + rejected_count,
                accepted_count=len(products),
                rejected_count=rejected_count,
                message=(
                    f"ALDI procesado: {processed_listing_urls} páginas de ofertas, "
                    f"{processed_article_urls} fichas, "
                    f"{len(products)} productos aceptados."
                ),
                metadata={
                    "mode": "aldi_article_pages",
                    "processed_listing_urls": processed_listing_urls,
                    "processed_article_urls": processed_article_urls,
                    "article_links": len(article_urls),
                    "playwright_urls": playwright_urls,
                    "blocked_urls": blocked_urls,
                    "max_article_links": self.max_article_links,
                    "max_products": self.max_products,
                    "note": "ALDI: ofertas/folletos semanales, no catálogo permanente completo.",
                },
            )

        except Exception as exc:
            logger.exception("Error inesperado scrapeando ALDI")
            return ScraperRunResult.failed(
                supermercado=self.supermercado,
                error=f"Error inesperado en ALDI: {exc}",
            )

    async def _get_html(self, url: str) -> tuple[Optional[str], bool, bool]:
        try:
            html = await self.get_text(
                url,
                headers=self._aldi_headers(),
            )

            # Si la página viene demasiado vacía o sin señales útiles, probamos navegador.
            if self.use_playwright_fallback and self._should_retry_with_playwright(html):
                playwright_html = await self._get_text_with_playwright(url)

                if playwright_html:
                    return playwright_html, True, False

            return html, False, False

        except ScraperBlockedError:
            if not self.use_playwright_fallback:
                return None, False, True

            html = await self._get_text_with_playwright(url)
            return html, bool(html), True

        except httpx.HTTPStatusError as exc:
            logger.warning("ALDI URL omitida por HTTP %s: %s", exc.response.status_code, url)

            if not self.use_playwright_fallback:
                return None, False, False

            html = await self._get_text_with_playwright(url)
            return html, bool(html), False

    def _should_retry_with_playwright(self, html: str) -> bool:
        if not html:
            return True

        lowered = html.lower()

        has_article_links = ".article.html" in lowered
        has_price = "€" in html
        has_basic_content = "aldi" in lowered

        return not has_basic_content or (not has_article_links and not has_price)

    async def _get_text_with_playwright(self, url: str) -> Optional[str]:
        if async_playwright is None:
            logger.warning("Playwright no está instalado. No se puede usar fallback para ALDI.")
            return None

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
                    logger.warning("Timeout cargando ALDI, se continúa con HTML parcial: %s", url)
                else:
                    logger.warning("Error cargando ALDI con Playwright: %s", exc)
                    await context.close()
                    await browser.close()
                    return None

            await self._accept_cookies_if_present(page)
            await page.wait_for_timeout(2500)

            for _ in range(5):
                await page.mouse.wheel(0, 1000)
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

    def _extract_article_links(
        self,
        html: str,
        *,
        source_url: str,
    ) -> list[str]:
        soup = BeautifulSoup(html, "html.parser")
        links: list[str] = []

        for link in soup.find_all("a", href=True):
            href = clean_text(link.get("href"))

            if self._is_article_link(href):
                links.append(self._absolute_url(href))

        for match in self.ARTICLE_LINK_RE.finditer(html):
            href = clean_text(match.group("href"))

            if self._is_article_link(href):
                links.append(self._absolute_url(href))

        return [link for link in links if link]

    def _is_article_link(self, href: str) -> bool:
        href = clean_text(href)

        if not href:
            return False

        return ".article.html" in href and "/ofertas/" in href

    def _parse_article_page(
        self,
        html: str,
        *,
        source_url: str,
    ) -> ScrapedProduct:
        soup = BeautifulSoup(html, "html.parser")
        page_text = clean_text(soup.get_text(" ", strip=True))

        name = self._extract_name(soup)

        if not name:
            raise ValueError("Ficha ALDI sin nombre")

        price = self._extract_current_price(soup, page_text)

        if price is None:
            raise ValueError(f"Ficha ALDI sin precio: {name}")

        brand, clean_name = self._extract_brand_and_clean_name(name)

        validity = self._extract_validity(page_text)
        format_text = self._guess_format_from_text(page_text, clean_name)
        unit = self._guess_unit_from_name(format_text or clean_name)

        return ScrapedProduct(
            nombre=clean_name,
            precio=parse_price(price),
            supermercado=self.supermercado,
            marca=brand,
            categoria=self._category_from_url(source_url),
            unidad_medida=unit,
            formato=format_text,
            external_id=self._external_id_from_url(source_url),
            url_producto=source_url,
            imagen_url=self._extract_image_url(soup),
            metadata={
                "source": "aldi_article_page",
                "source_url": source_url,
                "valid_from": validity[0] if validity else None,
                "valid_to": validity[1] if validity else None,
                "note": "ALDI: oferta/folleto, no catálogo permanente completo.",
            },
        )

    def _extract_name(self, soup: BeautifulSoup) -> Optional[str]:
        for selector in ["h1", "h2"]:
            tag = soup.find(selector)

            if not tag:
                continue

            text = clean_text(tag.get_text(" ", strip=True))

            if text and len(text) > 2:
                return self._clean_product_name(text)

        title = soup.find("title")

        if title:
            text = clean_text(title.get_text(" ", strip=True))
            text = text.replace("| ALDI Supermercados", "")
            text = text.replace("ALDI Supermercados", "")
            return self._clean_product_name(text)

        return None

    def _extract_current_price(
        self,
        soup: BeautifulSoup,
        page_text: str,
    ) -> Optional[str]:
        """
        Extrae el PVP principal de la ficha ALDI.

        Estrategia:
        - Aislar el bloque de precio principal de la ficha.
        - Eliminar precios unitarios tipo "kg = 9,95 €" o "l = 1,20 €".
        - Si hay precio anterior + precio actual, quedarse con el último precio principal.
        """

        price_area = self._extract_main_price_area(soup, page_text)

        if not price_area:
            price_area = page_text[:1500]

        cleaned_price_area = self._remove_unit_price_segments(price_area)

        prices = [
            match.group(1)
            for match in self.PRICE_RE.finditer(cleaned_price_area)
        ]

        if prices:
            has_discount = (
                "%" in cleaned_price_area
                or self.OLD_PRICE_HINT_RE.search(cleaned_price_area) is not None
                or len(prices) >= 2
            )

            if has_discount and len(prices) >= 2:
                # En ALDI suele aparecer: precio anterior + precio actual.
                # Ejemplo: "2,65 € 1,99 €"
                return prices[-1]

            return prices[0]

        # Fallback por si la página tiene una estructura rara.
        candidates: list[tuple[str, str]] = []

        for match in self.PRICE_RE.finditer(page_text):
            price = match.group(1)
            context = self._price_context(page_text, match.start(), match.end())

            if self._is_unit_price_context(context):
                continue

            candidates.append((price, context))

        if not candidates:
            return None

        if len(candidates) >= 2:
            return candidates[-1][0]

        return candidates[0][0]

    @staticmethod
    def _price_context(text: str, start: int, end: int) -> str:
        return text[max(start - 45, 0): min(end + 45, len(text))]
    
    def _extract_main_price_area(
        self,
        soup: BeautifulSoup,
        page_text: str,
    ) -> str:
        name = self._extract_name(soup)

        if name and name in page_text:
            area = page_text.split(name, 1)[1]
        else:
            area = page_text

        stop_markers = [
            "Añadir a lista de la compra",
            "Precios válidos del",
            "Precios válidos según tienda",
            "Descargar App ALDI",
            "ALDI Newsletter",
        ]

        for marker in stop_markers:
            position = area.find(marker)

            if position != -1:
                area = area[:position]
                break

        return clean_text(area[:1500])

    def _remove_unit_price_segments(self, text: str) -> str:
        cleaned = text

        patterns = [
            r"\bkg\s*=\s*\d{1,3}(?:[,.]\d{1,2})?\s*€",
            r"\bl\s*=\s*\d{1,3}(?:[,.]\d{1,2})?\s*€",
            r"\b100\s*g\s*=\s*\d{1,3}(?:[,.]\d{1,2})?\s*€",
            r"\b100\s*ml\s*=\s*\d{1,3}(?:[,.]\d{1,2})?\s*€",
            r"\d{1,3}(?:[,.]\d{1,2})?\s*€\s*/\s*(?:kg|l|100\s*g|100\s*ml)",
        ]

        for pattern in patterns:
            cleaned = re.sub(
                pattern,
                " ",
                cleaned,
                flags=re.IGNORECASE,
            )

        return clean_text(cleaned)
    
    def _is_unit_price_context(self, context: str) -> bool:
        text = clean_text(context).lower()

        return self.UNIT_PRICE_HINT_RE.search(text) is not None

    def _has_discount_signal(self, context: str) -> bool:
        text = clean_text(context).lower()

        return "%" in text or self.OLD_PRICE_HINT_RE.search(text) is not None

    def _extract_validity(self, page_text: str) -> Optional[tuple[str, str]]:
        match = self.DATE_VALIDITY_RE.search(page_text)

        if not match:
            return None

        return match.group(1), match.group(2)

    def _extract_brand_and_clean_name(self, name: str) -> tuple[Optional[str], str]:
        text = self._clean_product_name(name)

        # Patrones tipo "CUCINA® Sazonador..." o "LILY & DAN® Conjunto..."
        brand_match = re.match(
            r"^(?P<brand>[A-ZÁÉÍÓÚÜÑ0-9& .'-]{2,30}®?)\s+(?P<rest>.+)$",
            text,
        )

        if brand_match and "®" in brand_match.group("brand"):
            brand = clean_text(brand_match.group("brand")).replace("®", "").title()
            rest = clean_text(brand_match.group("rest"))
            return brand, rest

        return None, text

    def _clean_product_name(self, value: str) -> str:
        text = clean_text(value)

        text = text.replace("ALDI Supermercados", "")
        text = text.replace("|", " ")
        text = re.sub(r"\s+", " ", text)
        text = re.sub(r"\bAñadir a lista de la compra\b.*$", "", text, flags=re.IGNORECASE)
        text = re.sub(r"\bRecordatorio\b.*$", "", text, flags=re.IGNORECASE)
        text = re.sub(r"\d{1,3}(?:[,.]\d{1,2})?\s*€", "", text)
        text = clean_text(text)

        return text[:160]

    def _guess_format_from_text(
        self,
        page_text: str,
        name: str,
    ) -> Optional[str]:
        search_area = f"{name} {page_text[:1200]}".lower()

        for pattern in self.FORMAT_PATTERNS:
            match = re.search(pattern, search_area, re.IGNORECASE)

            if match:
                return clean_text(match.group(0))

        return None

    def _guess_unit_from_name(self, value: str) -> Optional[str]:
        text = clean_text(value).lower()

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

        if "unidad" in text:
            return "UD."

        return None

    def _extract_image_url(self, soup: BeautifulSoup) -> Optional[str]:
        og_image = soup.find("meta", property="og:image")

        if isinstance(og_image, Tag):
            content = og_image.get("content")
            if content:
                return self._absolute_url(content)

        image = soup.find("img")

        if not isinstance(image, Tag):
            return None

        src = image.get("src") or image.get("data-src") or image.get("data-original")

        return self._absolute_url(src)

    def _external_id_from_url(self, source_url: str) -> Optional[str]:
        match = re.search(r"-(\d{4,})-\d+-\d+\.article\.html", source_url)

        if not match:
            return None

        return match.group(1)

    def _category_from_url(self, source_url: str) -> Optional[str]:
        if "proxima" in source_url:
            return "Ofertas Próxima Semana"

        if "/desde-" in source_url:
            return "Ofertas"

        if "folleto" in source_url:
            return "Folleto"

        return "Ofertas"

    def _aldi_headers(self) -> dict[str, str]:
        return {
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Referer": "https://www.aldi.es/",
            "Origin": "https://www.aldi.es",
        }

    def _absolute_url(self, value: Optional[Any]) -> Optional[str]:
        text = clean_text(value)

        if not text:
            return None

        if text.startswith("http://") or text.startswith("https://"):
            return text

        return urljoin(self.base_url or "https://www.aldi.es", text)

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
    def _unique_urls(urls: list[str]) -> list[str]:
        unique_urls: list[str] = []
        seen: set[str] = set()

        for url in urls:
            if not url:
                continue

            if url in seen:
                continue

            seen.add(url)
            unique_urls.append(url)

        return unique_urls