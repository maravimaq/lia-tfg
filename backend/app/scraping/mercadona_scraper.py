from __future__ import annotations

import asyncio
import logging
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


class MercadonaScraper(BaseScraper):
    """
    Scraper de catálogo para Mercadona.

    Estrategia:
    - Usar API interna de tienda.mercadona.es.
    - Probar endpoint actual /api/categories/.
    - Si falla o no devuelve productos, probar /api/v1_1/categories/.
    - Saltar categorías concretas que devuelvan 404.
    - Extraer solo productos estructurados desde arrays `products`.

    No usa HTML genérico.
    """

    supermercado = "Mercadona"
    base_url = "https://tienda.mercadona.es"

    CATEGORY_ENDPOINTS = [
        {
            "name": "api",
            "categories_url": "https://tienda.mercadona.es/api/categories/",
            "category_detail_url": "https://tienda.mercadona.es/api/categories/{category_id}/",
        },
        {
            "name": "api_v1_1",
            "categories_url": "https://tienda.mercadona.es/api/v1_1/categories/",
            "category_detail_url": "https://tienda.mercadona.es/api/v1_1/categories/{category_id}/",
        },
    ]

    def __init__(
        self,
        *,
        timeout_seconds: int = 20,
        user_agent: str,
        max_categories: int = 40,
        delay_seconds: float = 0.15,
    ) -> None:
        super().__init__(
            timeout_seconds=timeout_seconds,
            user_agent=user_agent,
        )
        self.max_categories = max_categories
        self.delay_seconds = delay_seconds
        self._active_endpoint_name: Optional[str] = None
        self._active_detail_url_template: Optional[str] = None

    async def scrape(self) -> ScraperRunResult:
        try:
            category_ids = await self.get_category_ids()

            if not category_ids:
                return ScraperRunResult(
                    supermercado=self.supermercado,
                    status="empty",
                    message="No se han encontrado categorías válidas de Mercadona.",
                    metadata={
                        "max_categories": self.max_categories,
                    },
                )

            products: list[ScrapedProduct] = []
            rejected_count = 0
            skipped_categories = 0
            processed_categories = 0

            for category_id in category_ids[: self.max_categories]:
                category_products, category_rejected, was_skipped = (
                    await self.get_products_by_category(category_id)
                )

                if was_skipped:
                    skipped_categories += 1
                    continue

                processed_categories += 1
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
                    f"Mercadona procesado: {processed_categories} categorías, "
                    f"{skipped_categories} omitidas, "
                    f"{len(products)} productos aceptados."
                ),
                metadata={
                    "endpoint": self._active_endpoint_name,
                    "processed_categories": processed_categories,
                    "skipped_categories": skipped_categories,
                    "available_categories": len(category_ids),
                    "max_categories": self.max_categories,
                },
            )

        except ScraperBlockedError as exc:
            logger.warning("Mercadona bloqueado: %s", exc)
            return ScraperRunResult.blocked(
                supermercado=self.supermercado,
                message=str(exc),
            )

        except httpx.HTTPStatusError as exc:
            logger.exception("Error HTTP scrapeando Mercadona")
            return ScraperRunResult.failed(
                supermercado=self.supermercado,
                error=f"Error HTTP en Mercadona: {exc.response.status_code}",
                metadata={
                    "url": str(exc.request.url),
                    "response": exc.response.text[:500],
                },
            )

        except Exception as exc:
            logger.exception("Error inesperado scrapeando Mercadona")
            return ScraperRunResult.failed(
                supermercado=self.supermercado,
                error=f"Error inesperado en Mercadona: {exc}",
            )

    async def get_category_ids(self) -> list[int]:
        errors: list[str] = []

        for endpoint in self.CATEGORY_ENDPOINTS:
            endpoint_name = endpoint["name"]
            categories_url = endpoint["categories_url"]
            detail_url_template = endpoint["category_detail_url"]

            try:
                data = await self.get_json(
                    categories_url,
                    headers=self._mercadona_headers(),
                )
            except httpx.HTTPStatusError as exc:
                errors.append(f"{endpoint_name}: HTTP {exc.response.status_code}")
                continue

            category_ids = self._extract_category_ids(data)
            unique_ids = self._unique_ids(category_ids)

            if unique_ids:
                self._active_endpoint_name = endpoint_name
                self._active_detail_url_template = detail_url_template

                logger.info(
                    "Mercadona: %s ids de categoría encontrados usando %s.",
                    len(unique_ids),
                    endpoint_name,
                )

                return unique_ids

            errors.append(f"{endpoint_name}: sin ids de categoría")

        logger.warning(
            "Mercadona: no se pudieron obtener categorías válidas. Errores: %s",
            errors,
        )

        return []

    async def get_products_by_category(
        self,
        category_id: int,
    ) -> tuple[list[ScrapedProduct], int, bool]:
        """
        Devuelve:
        - productos aceptados
        - productos rechazados
        - was_skipped=True si la categoría se omite por 404 o respuesta vacía
        """

        if self._active_detail_url_template is None:
            return [], 0, True

        url = self._active_detail_url_template.format(category_id=category_id)

        try:
            data = await self.get_json(
                url,
                headers=self._mercadona_headers(),
            )
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code == 404:
                logger.debug(
                    "Mercadona: categoría omitida por 404. category_id=%s url=%s",
                    category_id,
                    url,
                )
                return [], 0, True

            raise

        raw_products = self._extract_products(data)

        if not raw_products:
            logger.debug(
                "Mercadona: categoría sin productos. category_id=%s url=%s",
                category_id,
                url,
            )
            return [], 0, True

        products: list[ScrapedProduct] = []
        rejected_count = 0

        for raw_product in raw_products:
            try:
                product = self._parse_product(raw_product, fallback_category=data)
            except Exception as exc:
                rejected_count += 1
                logger.debug(
                    "Producto Mercadona rechazado por error de parseo: %s",
                    exc,
                )
                continue

            is_valid, reason = validate_scraped_product(product)

            if not is_valid:
                rejected_count += 1
                logger.debug(
                    "Producto Mercadona rechazado: nombre=%r precio=%r motivo=%s",
                    product.nombre,
                    product.precio,
                    reason,
                )
                continue

            products.append(product)

        return products, rejected_count, False

    def _parse_product(
        self,
        product: dict[str, Any],
        *,
        fallback_category: Optional[dict[str, Any]] = None,
    ) -> ScrapedProduct:
        name = self._first_non_empty(
            product.get("display_name"),
            product.get("name"),
            product.get("title"),
        )

        if not name:
            raise ValueError("Producto Mercadona sin nombre")

        price_instructions = product.get("price_instructions")
        if not isinstance(price_instructions, dict):
            price_instructions = {}

        price = self._first_non_empty(
            price_instructions.get("unit_price"),
            price_instructions.get("price"),
            product.get("price"),
        )

        if price is None:
            raise ValueError(f"Producto Mercadona sin precio: {name}")

        unit_name = self._first_non_empty(
            price_instructions.get("unit_name"),
            price_instructions.get("size_format"),
            product.get("unit_name"),
        )

        unit_size = self._first_non_empty(
            price_instructions.get("unit_size"),
            product.get("unit_size"),
        )

        bulk_price = self._first_non_empty(
            price_instructions.get("bulk_price"),
            product.get("bulk_price"),
        )

        format_text = self._build_format(
            unit_size=unit_size,
            unit_name=unit_name,
            bulk_price=bulk_price,
        )

        relative_url = self._first_non_empty(
            product.get("share_url"),
            product.get("url"),
            product.get("slug"),
        )

        return ScrapedProduct(
            nombre=clean_text(name),
            precio=parse_price(price),
            supermercado=self.supermercado,
            marca=self._extract_brand(product),
            categoria=self._extract_category_name(product, fallback_category),
            unidad_medida=clean_text(unit_name).upper() if unit_name else None,
            formato=format_text,
            external_id=self._extract_external_id(product),
            url_producto=self._build_product_url(product, relative_url),
            imagen_url=self._absolute_url(
                self._first_non_empty(
                    product.get("thumbnail"),
                    product.get("image_url"),
                    product.get("image"),
                )
            ),
            metadata={
                "source": "mercadona_api",
                "endpoint": self._active_endpoint_name,
                "raw_bulk_price": bulk_price,
                "raw_unit_price": price,
                "raw_unit_name": unit_name,
                "raw_unit_size": unit_size,
            },
        )

    def _extract_category_ids(self, data: Any) -> list[int]:
        ids: list[int] = []

        def visit(node: Any) -> None:
            if isinstance(node, list):
                for item in node:
                    visit(item)
                return

            if not isinstance(node, dict):
                return

            if self._looks_like_product(node):
                return

            nested_category_nodes = self._get_nested_category_nodes(node)
            node_id = self._parse_int_id(node.get("id"))

            # Lo más fiable es pedir detalle de categorías hoja.
            # Algunas categorías padre pueden devolver 404.
            if node_id is not None and not nested_category_nodes:
                ids.append(node_id)

            for child in nested_category_nodes:
                visit(child)

            # Algunos endpoints meten las categorías directamente en results.
            results = node.get("results")
            if isinstance(results, list):
                for item in results:
                    visit(item)

        visit(data)
        return ids

    def _extract_products(self, data: Any) -> list[dict[str, Any]]:
        products: list[dict[str, Any]] = []

        def visit(node: Any) -> None:
            if isinstance(node, list):
                for item in node:
                    visit(item)
                return

            if not isinstance(node, dict):
                return

            node_products = node.get("products")

            if isinstance(node_products, list):
                for product in node_products:
                    if isinstance(product, dict):
                        products.append(product)

            for key in ("results", "categories", "children", "subcategories"):
                child = node.get(key)

                if isinstance(child, list):
                    for item in child:
                        visit(item)
                elif isinstance(child, dict):
                    visit(child)

        visit(data)
        return products

    def _mercadona_headers(self) -> dict[str, str]:
        return {
            "Accept": "application/json,text/plain,*/*",
            "Referer": "https://tienda.mercadona.es/categories",
            "Origin": "https://tienda.mercadona.es",
        }

    def _extract_brand(self, product: dict[str, Any]) -> Optional[str]:
        brand = self._first_non_empty(
            product.get("brand"),
            product.get("marca"),
            product.get("manufacturer"),
        )

        if brand:
            return clean_text(brand)

        return None

    def _extract_category_name(
        self,
        product: dict[str, Any],
        fallback_category: Optional[dict[str, Any]],
    ) -> Optional[str]:
        categories = product.get("categories")

        if isinstance(categories, list) and categories:
            last_category = categories[-1]

            if isinstance(last_category, dict):
                name = self._first_non_empty(
                    last_category.get("name"),
                    last_category.get("display_name"),
                )

                if name:
                    return clean_text(name).title()

        if isinstance(fallback_category, dict):
            name = self._first_non_empty(
                fallback_category.get("name"),
                fallback_category.get("display_name"),
            )

            if name:
                return clean_text(name).title()

        return None

    def _extract_external_id(self, product: dict[str, Any]) -> Optional[str]:
        value = self._first_non_empty(
            product.get("id"),
            product.get("product_id"),
            product.get("sku"),
        )

        return str(value) if value is not None else None

    def _build_product_url(
        self,
        product: dict[str, Any],
        relative_url: Optional[Any],
    ) -> Optional[str]:
        product_id = self._extract_external_id(product)

        if product_id:
            return f"{self.base_url}/product/{product_id}"

        return self._absolute_url(relative_url)

    def _absolute_url(self, value: Optional[Any]) -> Optional[str]:
        text = clean_text(value)

        if not text:
            return None

        if text.startswith("http://") or text.startswith("https://"):
            return text

        if text.startswith("/"):
            return urljoin(self.base_url or "https://tienda.mercadona.es", text)

        return text

    @staticmethod
    def _build_format(
        *,
        unit_size: Optional[Any],
        unit_name: Optional[Any],
        bulk_price: Optional[Any],
    ) -> Optional[str]:
        parts: list[str] = []

        unit_size_text = clean_text(unit_size)
        unit_name_text = clean_text(unit_name)

        if unit_size_text and unit_name_text:
            parts.append(f"{unit_size_text} {unit_name_text}")
        elif unit_name_text:
            parts.append(unit_name_text)

        bulk_price_text = clean_text(bulk_price)

        if bulk_price_text and unit_name_text:
            parts.append(f"{bulk_price_text} €/{unit_name_text}")

        return " · ".join(parts) if parts else None

    @staticmethod
    def _get_nested_category_nodes(node: dict[str, Any]) -> list[Any]:
        nested: list[Any] = []

        for key in ("categories", "children", "subcategories"):
            value = node.get(key)

            if isinstance(value, list):
                nested.extend(value)
            elif isinstance(value, dict):
                nested.append(value)

        return nested

    @staticmethod
    def _looks_like_product(node: dict[str, Any]) -> bool:
        return (
            "price_instructions" in node
            or "display_name" in node and "id" in node and "products" not in node
        )

    @staticmethod
    def _parse_int_id(value: Any) -> Optional[int]:
        if isinstance(value, int):
            return value

        if isinstance(value, str) and value.isdigit():
            return int(value)

        return None

    @staticmethod
    def _unique_ids(ids: list[int]) -> list[int]:
        unique_ids: list[int] = []
        seen: set[int] = set()

        for item in ids:
            if item in seen:
                continue

            seen.add(item)
            unique_ids.append(item)

        return unique_ids

    @staticmethod
    def _first_non_empty(*values: Any) -> Optional[Any]:
        for value in values:
            if value is None:
                continue

            if isinstance(value, str) and not clean_text(value):
                continue

            return value

        return None