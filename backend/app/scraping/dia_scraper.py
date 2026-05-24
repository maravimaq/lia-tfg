from __future__ import annotations

import asyncio
import logging
from decimal import Decimal
from typing import Any, Optional
from urllib.parse import urljoin

import httpx

from app.scraping.base import (
    BaseScraper,
    ScrapedProduct,
    ScraperBlockedError,
    ScraperRunResult,
    clean_text,
    parse_price,
)
from app.scraping.validators import validate_scraped_product

logger = logging.getLogger(__name__)


class DiaScraper(BaseScraper):
    """
    Scraper de catálogo para DIA.

    Estrategia:
    - Obtener categorías desde un endpoint interno de analytics.
    - Recorrer rutas de categorías.
    - Consumir el endpoint interno de listado reducido de productos.
    - Aceptar solo productos con nombre + precio + estructura fiable.

    Nota:
    DIA puede requerir cookie en algunos entornos. Por ahora el scraper funciona
    sin depender obligatoriamente de cookie, pero admite `cookie` en el constructor.
    """

    supermercado = "DIA"
    base_url = "https://www.dia.es"

    CATEGORY_BOOTSTRAP_URL = (
        "https://www.dia.es/api/v1/plp-insight/initial_analytics/"
        "charcuteria-y-quesos/jamon-cocido-lacon-fiambres-y-mortadela/c/L2001"
    )

    PRODUCTS_BY_CATEGORY_BASE_URL = "https://www.dia.es/api/v1/plp-back/reduced"

    def __init__(
        self,
        *,
        timeout_seconds: int = 20,
        user_agent: str,
        cookie: Optional[str] = None,
        max_categories: int = 20,
        max_pages_per_category: int = 3,
        delay_seconds: float = 0.15,
    ) -> None:
        super().__init__(
            timeout_seconds=timeout_seconds,
            user_agent=user_agent,
        )
        self.cookie = cookie
        self.max_categories = max_categories
        self.max_pages_per_category = max_pages_per_category
        self.delay_seconds = delay_seconds

    async def scrape(self) -> ScraperRunResult:
        try:
            category_paths = await self.get_category_paths()

            if not category_paths:
                return ScraperRunResult(
                    supermercado=self.supermercado,
                    status="empty",
                    message="No se han encontrado categorías de DIA.",
                    metadata={
                        "max_categories": self.max_categories,
                        "max_pages_per_category": self.max_pages_per_category,
                    },
                )

            products: list[ScrapedProduct] = []
            rejected_count = 0
            processed_categories = 0

            for category_path in category_paths[: self.max_categories]:
                processed_categories += 1

                category_products, category_rejected = await self.get_products_by_category(
                    category_path
                )

                products.extend(category_products)
                rejected_count += category_rejected

                if self.delay_seconds > 0:
                    await asyncio.sleep(self.delay_seconds)

            return ScraperRunResult(
                supermercado=self.supermercado,
                status="success" if products else "empty",
                products=products,
                detected_count=len(products) + rejected_count,
                accepted_count=len(products),
                rejected_count=rejected_count,
                message=(
                    f"DIA procesado: {processed_categories} categorías, "
                    f"{len(products)} productos aceptados."
                ),
                metadata={
                    "processed_categories": processed_categories,
                    "available_categories": len(category_paths),
                    "max_categories": self.max_categories,
                    "max_pages_per_category": self.max_pages_per_category,
                },
            )

        except ScraperBlockedError as exc:
            logger.warning("DIA bloqueado: %s", exc)
            return ScraperRunResult.blocked(
                supermercado=self.supermercado,
                message=str(exc),
            )

        except httpx.HTTPStatusError as exc:
            logger.exception("Error HTTP scrapeando DIA")
            return ScraperRunResult.failed(
                supermercado=self.supermercado,
                error=f"Error HTTP en DIA: {exc.response.status_code}",
                metadata={
                    "url": str(exc.request.url),
                    "response": exc.response.text[:500],
                },
            )

        except Exception as exc:
            logger.exception("Error inesperado scrapeando DIA")
            return ScraperRunResult.failed(
                supermercado=self.supermercado,
                error=f"Error inesperado en DIA: {exc}",
            )

    async def get_category_paths(self) -> list[str]:
        data = await self.get_json(
            self.CATEGORY_BOOTSTRAP_URL,
            params={"navigation": "L2001"},
            headers=self._dia_headers(),
        )

        menu_analytics = data.get("menu_analytics")

        if not isinstance(menu_analytics, dict):
            logger.warning("DIA no ha devuelto menu_analytics válido.")
            return []

        category_paths = self._extract_category_paths(menu_analytics)

        unique_paths: list[str] = []
        seen: set[str] = set()

        for path in category_paths:
            normalized_path = clean_text(path)

            if not normalized_path:
                continue

            if normalized_path in seen:
                continue

            seen.add(normalized_path)
            unique_paths.append(normalized_path)

        logger.info("DIA: %s rutas de categoría encontradas.", len(unique_paths))
        return unique_paths

    async def get_products_by_category(
        self,
        category_path: str,
    ) -> tuple[list[ScrapedProduct], int]:
        products: list[ScrapedProduct] = []
        rejected_count = 0

        for page in range(1, self.max_pages_per_category + 1):
            url = self._build_products_url(category_path, page=page)

            try:
                data = await self.get_json(
                    url,
                    headers=self._dia_headers(),
                )
            except httpx.HTTPStatusError as exc:
                if exc.response.status_code == 404:
                    logger.debug(
                        "DIA categoría sin página: category=%s page=%s",
                        category_path,
                        page,
                    )
                    break

                raise

            items = data.get("plp_items")

            if not isinstance(items, list) or not items:
                break

            page_products, page_rejected = self._parse_items(
                items,
                category_path=category_path,
            )

            products.extend(page_products)
            rejected_count += page_rejected

            # Si la API no devuelve info de paginación clara, este corte evita
            # insistir cuando una página ya viene vacía o repetida.
            if len(items) == 0:
                break

            if self.delay_seconds > 0:
                await asyncio.sleep(self.delay_seconds)

        return products, rejected_count

    def _parse_items(
        self,
        items: list[dict[str, Any]],
        *,
        category_path: str,
    ) -> tuple[list[ScrapedProduct], int]:
        products: list[ScrapedProduct] = []
        rejected_count = 0

        for item in items:
            try:
                product = self._parse_item(item, category_path=category_path)
            except Exception as exc:
                rejected_count += 1
                logger.debug("Producto DIA rechazado por error de parseo: %s", exc)
                continue

            is_valid, reason = validate_scraped_product(product)

            if not is_valid:
                rejected_count += 1
                logger.debug(
                    "Producto DIA rechazado: nombre=%r precio=%r motivo=%s",
                    product.nombre,
                    product.precio,
                    reason,
                )
                continue

            products.append(product)

        return products, rejected_count

    def _parse_item(
        self,
        item: dict[str, Any],
        *,
        category_path: str,
    ) -> ScrapedProduct:
        name = self._first_non_empty(
            item.get("display_name"),
            item.get("name"),
            item.get("title"),
        )

        price = self._first_non_empty(
            item.get("prices", {}).get("price") if isinstance(item.get("prices"), dict) else None,
            item.get("prices_price"),
            item.get("price"),
            item.get("unit_price"),
        )

        if not name:
            raise ValueError("Producto DIA sin nombre")

        if price is None:
            raise ValueError(f"Producto DIA sin precio: {name}")

        price_decimal = parse_price(price)

        relative_url = self._first_non_empty(
            item.get("url"),
            item.get("product_url"),
            item.get("share_url"),
        )

        image_url = self._first_non_empty(
            item.get("image"),
            item.get("image_url"),
            item.get("thumbnail"),
        )

        return ScrapedProduct(
            nombre=clean_text(name),
            precio=price_decimal,
            supermercado=self.supermercado,
            marca=self._extract_brand(item),
            categoria=self._category_name_from_path(category_path),
            unidad_medida=self._extract_unit(item),
            formato=self._extract_format(item),
            external_id=self._extract_external_id(item),
            url_producto=self._absolute_url(relative_url),
            imagen_url=self._absolute_url(image_url),
            metadata={
                "source": "dia_api",
                "category_path": category_path,
                "raw_price_per_unit": self._first_non_empty(
                    item.get("prices", {}).get("price_per_unit")
                    if isinstance(item.get("prices"), dict)
                    else None,
                    item.get("prices_price_per_unit"),
                ),
            },
        )

    def _build_products_url(self, category_path: str, *, page: int) -> str:
        path = clean_text(category_path)

        if not path.startswith("/"):
            path = "/" + path

        url = self.PRODUCTS_BY_CATEGORY_BASE_URL + path

        separator = "&" if "?" in url else "?"
        return f"{url}{separator}page={page}"

    def _dia_headers(self) -> dict[str, str]:
        headers = {
            "Accept": "application/json,text/plain,*/*",
            "Referer": "https://www.dia.es/",
            "Origin": "https://www.dia.es",
        }

        if self.cookie:
            headers["Cookie"] = self.cookie

        return headers

    def _extract_category_paths(self, node: dict[str, Any]) -> list[str]:
        paths: list[str] = []

        def visit(current_node: Any) -> None:
            if not isinstance(current_node, dict):
                return

            node_path = current_node.get("path")
            node_parameter = current_node.get("parameter")

            if isinstance(node_path, str) and node_path:
                paths.append(node_path)

            if isinstance(node_parameter, str) and node_parameter:
                paths.append(node_parameter)

            children = current_node.get("children")

            if isinstance(children, dict):
                for child in children.values():
                    visit(child)

        for value in node.values():
            visit(value)

        return paths

    def _extract_brand(self, item: dict[str, Any]) -> Optional[str]:
        return self._first_non_empty(
            item.get("brand"),
            item.get("manufacturer"),
            item.get("marca"),
        )

    def _extract_unit(self, item: dict[str, Any]) -> Optional[str]:
        prices = item.get("prices") if isinstance(item.get("prices"), dict) else {}

        return self._first_non_empty(
            prices.get("measure_unit"),
            item.get("prices_measure_unit"),
            item.get("measure_unit"),
            item.get("unit"),
        )

    def _extract_format(self, item: dict[str, Any]) -> Optional[str]:
        prices = item.get("prices") if isinstance(item.get("prices"), dict) else {}

        price_per_unit = self._first_non_empty(
            prices.get("price_per_unit"),
            item.get("prices_price_per_unit"),
            item.get("price_per_unit"),
        )

        unit = self._extract_unit(item)

        if price_per_unit and unit:
            return f"{price_per_unit} €/{unit}"

        if unit:
            return unit

        return self._first_non_empty(
            item.get("format"),
            item.get("packaging"),
            item.get("size"),
        )

    def _extract_external_id(self, item: dict[str, Any]) -> Optional[str]:
        value = self._first_non_empty(
            item.get("object_id"),
            item.get("id"),
            item.get("product_id"),
            item.get("sku"),
        )

        return str(value) if value is not None else None

    def _absolute_url(self, value: Optional[Any]) -> Optional[str]:
        text = clean_text(value)

        if not text:
            return None

        if text.startswith("http://") or text.startswith("https://"):
            return text

        return urljoin(self.base_url or "https://www.dia.es", text)

    @staticmethod
    def _first_non_empty(*values: Any) -> Optional[Any]:
        for value in values:
            if value is None:
                continue

            if isinstance(value, str) and not clean_text(value):
                continue

            return value

        return None

    @staticmethod
    def _category_name_from_path(category_path: str) -> Optional[str]:
        path = clean_text(category_path)

        if not path:
            return None

        parts = [
            part
            for part in path.split("/")
            if part and part not in {"c"} and not part.startswith("L")
        ]

        if not parts:
            return None

        raw_name = parts[-1]
        return raw_name.replace("-", " ").strip().title()