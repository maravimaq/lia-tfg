from __future__ import annotations

import json
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


class AlcampoScraper(BaseScraper):
    """
    Scraper para Alcampo España.

    Estrategia:
    - Usar páginas públicas de categorías.
    - Extraer productos desde texto estructurado de listado:
      nombre + formato + "Precio X €".
    - Usar Playwright como fallback si httpx devuelve HTML incompleto/bloqueado.
    - No parsear texto genérico sin precio.
    """

    supermercado = "Alcampo"
    base_url = "https://www.compraonline.alcampo.es"

    START_URLS = [
        "https://www.compraonline.alcampo.es/categories",
        "https://www.compraonline.alcampo.es/categories/alimentaci%C3%B3n/OCC10",
        "https://www.compraonline.alcampo.es/categories/frescos/OC2112?sortBy=favorite",
        "https://www.compraonline.alcampo.es/categories/leche-huevos-l%C3%A1cteos-yogures-y-bebidas-vegetales/OC16?sortBy=favorite",
        "https://www.compraonline.alcampo.es/categories/congelados/OC200220183?sortBy=favorite",
        "https://www.compraonline.alcampo.es/categories/bebidas/OCC11?sortBy=favorite",
    ]

    PRICE_LINE_RE = re.compile(
        r"\bPrecio\s+(\d{1,4}(?:[,.]\d{1,2})?)\s*€",
        re.IGNORECASE,
    )
    
    PRICE_VALUE_RE = re.compile(
        r"(?<!\d)(\d{1,4}(?:[,.]\d{1,2})?)\s*(?:€|EUR)\b",
        re.IGNORECASE,
    )

    FORMAT_LINE_RE = re.compile(
        r"^\s*(?P<format>\d+(?:[,.]\d+)?\s*(?:g|kg|ml|l)\s*(?:aprox)?|"
        r"\d+\s*uds?.*?|"
        r"\d+\s*por\s+envase.*?)"
        r"(?:\s*\(|$)",
        re.IGNORECASE,
    )

    UNIT_PRICE_RE = re.compile(
        r"\((?P<unit_price>\d{1,4}(?:[,.]\d{1,2})?\s*€\s*(?:por\s+kilogramo|por\s+litro|unidad))\)",
        re.IGNORECASE,
    )

    INVALID_NAME_PARTS = {
        "nombre de oferta",
        "puntuación",
        "precio",
        "añadir",
        "clasificar",
        "filtrar",
        "marcas",
        "filtros",
        "categorías",
        "lista de productos",
        "iniciar sesión",
        "registrarse",
        "pagar",
        "carrito",
        "elige ubicación",
        "volver",
        "en oferta",
        "producto en folleto",
        "club alcampo",
        "ofertones",
        "2ª unidad",
        "2 x 1",
        "dto",
        "descuento",
    }

    BAD_EXACT_NAMES = {
        "producto alcampo producto alcampo",
        "refrigerado refrigerado",
        "sin gluten sin gluten",
        "sin lactosa sin lactosa",
        "vegano vegano",
        "peso variable peso variable",
    }

    def __init__(
        self,
        *,
        timeout_seconds: int = 20,
        user_agent: str,
        max_urls: int = 6,
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
        playwright_urls = 0
        blocked_urls = 0

        try:
            for url in self.START_URLS[: self.max_urls]:
                html, used_playwright, was_blocked = await self._get_html(url)

                if was_blocked:
                    blocked_urls += 1

                if used_playwright:
                    playwright_urls += 1

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

            return ScraperRunResult(
                supermercado=self.supermercado,
                status="success" if products else "empty",
                products=products,
                detected_count=len(products) + rejected_count,
                accepted_count=len(products),
                rejected_count=rejected_count,
                message=(
                    f"Alcampo procesado: {processed_urls} URLs, "
                    f"{playwright_urls} con Playwright, "
                    f"{len(products)} productos aceptados."
                ),
                metadata={
                    "mode": "alcampo_initial_state",
                    "processed_urls": processed_urls,
                    "blocked_urls": blocked_urls,
                    "playwright_urls": playwright_urls,
                    "max_urls": self.max_urls,
                    "max_products_per_url": self.max_products_per_url,
                },
            )

        except Exception as exc:
            logger.exception("Error inesperado scrapeando Alcampo")
            return ScraperRunResult.failed(
                supermercado=self.supermercado,
                error=f"Error inesperado en Alcampo: {exc}",
            )

    async def _get_html(self, url: str) -> tuple[Optional[str], bool, bool]:
        try:
            html = await self.get_text(
                url,
                headers=self._alcampo_headers(),
            )

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
            logger.warning(
                "Alcampo URL omitida por HTTP %s: %s",
                exc.response.status_code,
                url,
            )

            if not self.use_playwright_fallback:
                return None, False, False

            html = await self._get_text_with_playwright(url)
            return html, bool(html), False

    def _should_retry_with_playwright(self, html: str) -> bool:
        if not html:
            return True

        lowered = html.lower()

        has_alcampo = "alcampo" in lowered
        has_initial_state_products = (
            "window.__initial_state__" in lowered
            and '"productentities"' in lowered
            and '"productid"' in lowered
            and '"price"' in lowered
        )

        return not has_alcampo or not has_initial_state_products

    async def _get_text_with_playwright(self, url: str) -> Optional[str]:
        if async_playwright is None:
            logger.warning(
                "Playwright no está instalado. No se puede usar fallback para Alcampo."
            )
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
                    logger.warning(
                        "Timeout cargando Alcampo, se continúa con HTML parcial: %s",
                        url,
                    )
                else:
                    logger.warning(
                        "Error cargando Alcampo con Playwright: url=%s error=%s",
                        url,
                        exc,
                    )
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

    def _parse_html(
        self,
        html: str,
        *,
        source_url: str,
    ) -> tuple[list[ScrapedProduct], int]:
        soup = BeautifulSoup(html, "html.parser")
        category = self._extract_category(soup, source_url)

        products, rejected_count = self._parse_initial_state_products(
            html,
            category=category,
            source_url=source_url,
        )

        if products:
            return products, rejected_count

        # Fallback antiguo por texto visible, por si alguna página no trae initial state.
        lines = self._extract_clean_lines(soup)

        for index, line in enumerate(lines):
            if len(products) >= self.max_products_per_url:
                break

            price = self._extract_price_from_lines(lines, index)

            if price is None:
                continue

            try:
                name = self._find_product_name_before(lines, index)

                if not name:
                    raise ValueError("No se encontró nombre antes del precio")

                format_text = self._find_format_before(lines, index)
                unit_price = self._find_unit_price_before(lines, index)
                product_url = self._find_product_url_by_name(soup, name)

                brand, clean_name = self._extract_brand_and_clean_name(name)

                product = ScrapedProduct(
                    nombre=clean_name,
                    precio=parse_price(price),
                    supermercado=self.supermercado,
                    marca=brand,
                    categoria=category,
                    unidad_medida=self._guess_unit_from_format(format_text or clean_name),
                    formato=format_text,
                    external_id=self._extract_external_id(product_url),
                    url_producto=product_url or source_url,
                    imagen_url=self._find_image_url_near_name(soup, name),
                    metadata={
                        "source": "alcampo_text_fallback",
                        "source_url": source_url,
                        "unit_price": unit_price,
                    },
                )

            except Exception as exc:
                rejected_count += 1
                logger.debug("Producto Alcampo rechazado por parseo: %s", exc)
                continue

            is_valid, reason = validate_scraped_product(product)

            if not is_valid:
                rejected_count += 1
                logger.debug(
                    "Producto Alcampo inválido: nombre=%r precio=%r motivo=%s",
                    product.nombre,
                    product.precio,
                    reason,
                )
                continue

            products.append(product)

        return products, rejected_count
    
    def _parse_initial_state_products(
        self,
        html: str,
        *,
        category: Optional[str],
        source_url: str,
    ) -> tuple[list[ScrapedProduct], int]:
        data = self._extract_initial_state(html)

        if not data:
            return [], 0

        raw_products = self._find_product_nodes(data)

        products: list[ScrapedProduct] = []
        rejected_count = 0

        for raw_product in raw_products:
            if len(products) >= self.max_products_per_url:
                break

            try:
                product = self._build_product_from_initial_state(
                    raw_product,
                    category=category,
                    source_url=source_url,
                )
            except Exception as exc:
                rejected_count += 1
                logger.debug("Producto Alcampo initial state rechazado: %s", exc)
                continue

            is_valid, reason = validate_scraped_product(product)

            if not is_valid:
                rejected_count += 1
                logger.debug(
                    "Producto Alcampo initial state inválido: nombre=%r precio=%r motivo=%s",
                    product.nombre,
                    product.precio,
                    reason,
                )
                continue

            products.append(product)

        return products, rejected_count

    def _extract_initial_state(self, html: str) -> Optional[dict[str, Any]]:
        match = re.search(
            r"window\.__INITIAL_STATE__\s*=\s*(\{.*?\})\s*</script>",
            html,
            re.DOTALL,
        )

        if not match:
            return None

        raw_json = match.group(1).strip()

        try:
            return json.loads(raw_json)
        except json.JSONDecodeError as exc:
            logger.warning("No se pudo parsear window.__INITIAL_STATE__ de Alcampo: %s", exc)
            return None

    def _find_product_nodes(self, data: Any) -> list[dict[str, Any]]:
        products: list[dict[str, Any]] = []
        seen_ids: set[str] = set()

        def visit(node: Any) -> None:
            if isinstance(node, list):
                for item in node:
                    visit(item)
                return

            if not isinstance(node, dict):
                return

            product_id = node.get("productId")
            name = node.get("name")
            price = node.get("price")

            if product_id and name and isinstance(price, dict):
                product_id_text = str(product_id)

                if product_id_text not in seen_ids:
                    seen_ids.add(product_id_text)
                    products.append(node)

            for value in node.values():
                if isinstance(value, list | dict):
                    visit(value)

        visit(data)

        return products

    def _build_product_from_initial_state(
        self,
        raw: dict[str, Any],
        *,
        category: Optional[str],
        source_url: str,
    ) -> ScrapedProduct:
        name = clean_text(raw.get("name"))

        if not name:
            raise ValueError("Producto Alcampo sin nombre")

        price_info = raw.get("price")

        if not isinstance(price_info, dict):
            raise ValueError(f"Producto Alcampo sin price_info: {name}")

        current_price = price_info.get("current")

        if not isinstance(current_price, dict):
            raise ValueError(f"Producto Alcampo sin precio actual: {name}")

        amount = current_price.get("amount")

        if amount is None:
            raise ValueError(f"Producto Alcampo sin amount: {name}")

        brand = clean_text(raw.get("brand"))

        size = raw.get("size")
        format_text = None

        if isinstance(size, dict):
            format_text = clean_text(size.get("value"))

        category_path = raw.get("categoryPath")
        product_category = category

        if isinstance(category_path, list) and category_path:
            product_category = clean_text(category_path[-1]).title()

        image_url = self._extract_image_url_from_initial_state(raw)

        clean_brand, clean_name = self._extract_brand_and_clean_name(name)

        if not clean_brand and brand:
            clean_brand = self._normalize_brand(brand)

        return ScrapedProduct(
            nombre=clean_name,
            precio=parse_price(amount),
            supermercado=self.supermercado,
            marca=clean_brand,
            categoria=product_category,
            unidad_medida=self._guess_unit_from_format(format_text or clean_name),
            formato=format_text,
            external_id=str(raw.get("productId")) if raw.get("productId") else None,
            url_producto=source_url,
            imagen_url=image_url,
            metadata={
                "source": "alcampo_initial_state",
                "source_url": source_url,
                "retailer_product_id": raw.get("retailerProductId"),
                "unit_price": self._extract_unit_price_from_initial_state(price_info),
            },
        )

    def _extract_image_url_from_initial_state(
        self,
        raw: dict[str, Any],
    ) -> Optional[str]:
        image = raw.get("image")

        if isinstance(image, dict):
            src = image.get("src")

            if src:
                return self._absolute_url(src)

        images = raw.get("images")

        if isinstance(images, list) and images:
            first = images[0]

            if isinstance(first, dict):
                src = first.get("src") or first.get("url")

                if src:
                    return self._absolute_url(src)

        return None

    def _extract_unit_price_from_initial_state(
        self,
        price_info: dict[str, Any],
    ) -> Optional[str]:
        unit = price_info.get("unit")

        if not isinstance(unit, dict):
            return None

        current = unit.get("current")

        if not isinstance(current, dict):
            return None

        amount = current.get("amount")

        if amount is None:
            return None

        label = clean_text(unit.get("label"))

        if "kg" in label.lower():
            return f"{amount} €/kg"

        if "litro" in label.lower() or "l" in label.lower():
            return f"{amount} €/l"

        return f"{amount} €"

    def _normalize_brand(self, value: str) -> Optional[str]:
        text = clean_text(value)

        if not text:
            return None

        if text.upper() == "PRODUCTO ALCAMPO":
            return "Alcampo"

        return text.title()
    
    def _looks_like_unit_price_line(self, value: str) -> bool:
        text = clean_text(value).lower()

        return (
            "por kilogramo" in text
            or "por litro" in text
            or "por unidad" in text
            or "€/kg" in text
            or "€/l" in text
        )
    
    def _extract_price_from_lines(
        self,
        lines: list[str],
        index: int,
    ) -> Optional[str]:
        line = clean_text(lines[index])
        lowered = line.lower()

        # Caso 1: "Precio 3,99 €"
        if "precio" in lowered:
            match = self.PRICE_VALUE_RE.search(line)

            if match:
                return match.group(1)

            # Caso 2:
            # línea actual: "Precio"
            # línea siguiente: "3,99 €"
            if index + 1 < len(lines):
                next_line = clean_text(lines[index + 1])
                next_lowered = next_line.lower()

                if self._looks_like_unit_price_line(next_line):
                    return None

                match = self.PRICE_VALUE_RE.search(next_line)

                if match:
                    return match.group(1)

        # Caso 3:
        # línea actual: "3,99 €"
        # línea anterior: "Precio"
        if index > 0 and "precio" in clean_text(lines[index - 1]).lower():
            if self._looks_like_unit_price_line(line):
                return None

            match = self.PRICE_VALUE_RE.search(line)

            if match:
                return match.group(1)

        return None

    def _extract_clean_lines(self, soup: BeautifulSoup) -> list[str]:
        raw_text = soup.get_text("\n", strip=True)

        lines: list[str] = []

        for raw_line in raw_text.splitlines():
            line = clean_text(raw_line)

            if not line:
                continue

            lines.append(line)

        return lines

    def _find_product_name_before(
        self,
        lines: list[str],
        price_index: int,
    ) -> Optional[str]:
        start = max(price_index - 14, 0)
        candidates = lines[start:price_index]

        for candidate in reversed(candidates):
            cleaned = self._clean_product_name(candidate)

            if self._looks_like_product_name(cleaned):
                return cleaned

        return None

    def _find_format_before(
        self,
        lines: list[str],
        price_index: int,
    ) -> Optional[str]:
        start = max(price_index - 8, 0)

        for candidate in reversed(lines[start:price_index]):
            line = clean_text(candidate)

            match = self.FORMAT_LINE_RE.search(line)

            if match:
                return clean_text(match.group("format"))

        return None

    def _find_unit_price_before(
        self,
        lines: list[str],
        price_index: int,
    ) -> Optional[str]:
        start = max(price_index - 8, 0)

        for candidate in reversed(lines[start:price_index]):
            line = clean_text(candidate)
            match = self.UNIT_PRICE_RE.search(line)

            if match:
                return clean_text(match.group("unit_price"))

        return None

    def _looks_like_product_name(self, value: str) -> bool:
        text = clean_text(value)
        lowered = text.lower()

        if len(text) < 4:
            return False

        if lowered in self.BAD_EXACT_NAMES:
            return False

        if any(part in lowered for part in self.INVALID_NAME_PARTS):
            return False

        if self.PRICE_LINE_RE.search(text):
            return False

        if self.FORMAT_LINE_RE.search(text):
            return False

        if re.fullmatch(r"\(\d+\)", text):
            return False

        if "€" in text:
            return False

        return True

    def _clean_product_name(self, value: str) -> str:
        text = clean_text(value)

        text = text.replace("Producto Alcampo Producto Alcampo", "Producto Alcampo")
        text = text.replace("PRODUCTO ALCAMPO", "Producto Alcampo")
        text = re.sub(r"\s+", " ", text)

        return clean_text(text)[:180]

    def _extract_brand_and_clean_name(self, name: str) -> tuple[Optional[str], str]:
        text = self._clean_product_name(name)

        if text.lower().startswith("producto alcampo "):
            clean_name = clean_text(text[len("producto alcampo "):])
            return "Alcampo", clean_name

        if text.lower().startswith("auchan "):
            clean_name = clean_text(text[len("auchan "):])
            return "Auchan", clean_name

        first_words = text.split(" ")[:2]
        possible_brand = " ".join(first_words)

        known_brands = {
            "alcampo",
            "auchan",
            "koipesol",
            "bezoya",
            "font vella",
            "lanjarón",
            "solan de cabras",
            "pringles",
            "campo/frío",
            "campofrío",
            "el pozo",
            "monster",
            "zespri",
        }

        lowered_brand = possible_brand.lower()

        for brand in known_brands:
            if lowered_brand.startswith(brand):
                clean_name = clean_text(text[len(possible_brand):]) or text
                return possible_brand.title(), clean_name

        return None, text

    def _extract_category(
        self,
        soup: BeautifulSoup,
        source_url: str,
    ) -> Optional[str]:
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
                "www.compraonline.alcampo.es",
                "categories",
            }
        ]

        for part in parts:
            if part.startswith("OC"):
                continue

            return part.replace("-", " ").title()

        return None

    def _find_product_url_by_name(
        self,
        soup: BeautifulSoup,
        name: str,
    ) -> Optional[str]:
        normalized_target = self._normalize_for_match(name)

        best_href: Optional[str] = None

        for link in soup.find_all("a", href=True):
            if not isinstance(link, Tag):
                continue

            text = clean_text(link.get_text(" ", strip=True))

            if not text:
                continue

            normalized_text = self._normalize_for_match(text)

            if normalized_text == normalized_target or normalized_target in normalized_text:
                href = clean_text(link.get("href"))

                if href:
                    best_href = self._absolute_url(href)
                    break

        return best_href

    def _find_image_url_near_name(
        self,
        soup: BeautifulSoup,
        name: str,
    ) -> Optional[str]:
        normalized_target = self._normalize_for_match(name)

        for image in soup.find_all("img"):
            if not isinstance(image, Tag):
                continue

            alt = clean_text(image.get("alt"))

            if not alt:
                continue

            normalized_alt = self._normalize_for_match(alt)

            if normalized_target in normalized_alt or normalized_alt in normalized_target:
                src = (
                    image.get("src")
                    or image.get("data-src")
                    or image.get("data-original")
                )

                return self._absolute_url(src)

        return None

    def _extract_external_id(self, product_url: Optional[str]) -> Optional[str]:
        if not product_url:
            return None

        # Intentamos capturar IDs si vienen en la URL.
        match = re.search(r"/(?:p|product|products)/([^/?#]+)", product_url)

        if match:
            return match.group(1)

        return None

    def _guess_unit_from_format(self, value: str) -> Optional[str]:
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

    def _alcampo_headers(self) -> dict[str, str]:
        return {
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Referer": "https://www.compraonline.alcampo.es/categories",
            "Origin": "https://www.compraonline.alcampo.es",
        }

    def _absolute_url(self, value: Optional[Any]) -> Optional[str]:
        text = clean_text(value)

        if not text:
            return None

        if text.startswith("http://") or text.startswith("https://"):
            return text

        return urljoin(self.base_url or "https://www.compraonline.alcampo.es", text)

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
    def _normalize_for_match(value: str) -> str:
        text = clean_text(value).lower()
        text = re.sub(r"\s+", " ", text)
        return text.strip()