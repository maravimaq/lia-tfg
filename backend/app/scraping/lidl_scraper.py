from __future__ import annotations

import json
import logging
import re
from decimal import Decimal
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

logger = logging.getLogger(__name__)


class LidlScraper(BaseScraper):
    """
    Scraper experimental para Lidl España.

    Objetivo:
    - Intentar extraer productos desde datos estructurados del HTML.
    - Aceptar solo productos con nombre + precio claro.
    - No hacer scraping laxo de textos visibles para evitar basura.

    Importante:
    Este scraper NO debe considerarse estable hasta probarlo con datos reales.
    """

    supermercado = "Lidl"
    base_url = "https://www.lidl.es"

    START_URLS = [
        "https://www.lidl.es/",
        "https://www.lidl.es/c/alimentacion/c100",
        "https://www.lidl.es/c/frutas-y-verduras/c101",
        "https://www.lidl.es/c/carne-y-pescado/c102",
        "https://www.lidl.es/c/lacteos-huevos-y-refrigerados/c103",
        "https://www.lidl.es/c/despensa/c104",
        "https://www.lidl.es/c/bebidas/c105",
    ]

    def __init__(
        self,
        *,
        timeout_seconds: int = 20,
        user_agent: str,
        max_urls: int = 8,
    ) -> None:
        super().__init__(
            timeout_seconds=timeout_seconds,
            user_agent=user_agent,
        )
        self.max_urls = max_urls

    async def scrape(self) -> ScraperRunResult:
        try:
            products: list[ScrapedProduct] = []
            rejected_count = 0
            processed_urls = 0

            for url in self.START_URLS[: self.max_urls]:
                try:
                    html = await self.get_text(
                        url,
                        headers=self._lidl_headers(),
                    )
                except httpx.HTTPStatusError as exc:
                    logger.warning(
                        "Lidl URL omitida por HTTP %s: %s",
                        exc.response.status_code,
                        url,
                    )
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
                    f"Lidl experimental procesado: {processed_urls} URLs, "
                    f"{len(products)} productos aceptados."
                ),
                metadata={
                    "mode": "experimental_html_structured_data",
                    "processed_urls": processed_urls,
                    "max_urls": self.max_urls,
                },
            )

        except ScraperBlockedError as exc:
            logger.warning("Lidl bloqueado: %s", exc)
            return ScraperRunResult.blocked(
                supermercado=self.supermercado,
                message=str(exc),
            )

        except httpx.HTTPStatusError as exc:
            logger.exception("Error HTTP scrapeando Lidl")
            return ScraperRunResult.failed(
                supermercado=self.supermercado,
                error=f"Error HTTP en Lidl: {exc.response.status_code}",
                metadata={
                    "url": str(exc.request.url),
                    "response": exc.response.text[:500],
                },
            )

        except Exception as exc:
            logger.exception("Error inesperado scrapeando Lidl")
            return ScraperRunResult.failed(
                supermercado=self.supermercado,
                error=f"Error inesperado en Lidl: {exc}",
            )

    def _parse_html(
        self,
        html: str,
        *,
        source_url: str,
    ) -> tuple[list[ScrapedProduct], int]:
        products: list[ScrapedProduct] = []
        rejected_count = 0

        soup = BeautifulSoup(html, "html.parser")

        json_ld_products, json_ld_rejected = self._parse_json_ld_products(
            soup,
            source_url=source_url,
        )

        products.extend(json_ld_products)
        rejected_count += json_ld_rejected

        next_data_products, next_data_rejected = self._parse_next_data_products(
            soup,
            source_url=source_url,
        )

        products.extend(next_data_products)
        rejected_count += next_data_rejected

        return products, rejected_count

    def _parse_json_ld_products(
        self,
        soup: BeautifulSoup,
        *,
        source_url: str,
    ) -> tuple[list[ScrapedProduct], int]:
        products: list[ScrapedProduct] = []
        rejected_count = 0

        scripts = soup.find_all("script", attrs={"type": "application/ld+json"})

        for script in scripts:
            raw_content = script.string or script.get_text()

            if not raw_content:
                continue

            try:
                data = json.loads(raw_content)
            except json.JSONDecodeError:
                continue

            raw_products = self._extract_product_nodes(data)

            for raw_product in raw_products:
                try:
                    product = self._build_product_from_structured_data(
                        raw_product,
                        source_url=source_url,
                        source_type="json_ld",
                    )
                except Exception as exc:
                    rejected_count += 1
                    logger.debug("Producto Lidl JSON-LD rechazado: %s", exc)
                    continue

                is_valid, reason = validate_scraped_product(product)

                if not is_valid:
                    rejected_count += 1
                    logger.debug(
                        "Producto Lidl JSON-LD inválido: nombre=%r motivo=%s",
                        product.nombre,
                        reason,
                    )
                    continue

                products.append(product)

        return products, rejected_count

    def _parse_next_data_products(
        self,
        soup: BeautifulSoup,
        *,
        source_url: str,
    ) -> tuple[list[ScrapedProduct], int]:
        products: list[ScrapedProduct] = []
        rejected_count = 0

        next_data_script = soup.find("script", id="__NEXT_DATA__")

        if next_data_script is None:
            return products, rejected_count

        raw_content = next_data_script.string or next_data_script.get_text()

        if not raw_content:
            return products, rejected_count

        try:
            data = json.loads(raw_content)
        except json.JSONDecodeError:
            return products, rejected_count

        raw_products = self._extract_product_nodes(data)

        for raw_product in raw_products:
            try:
                product = self._build_product_from_structured_data(
                    raw_product,
                    source_url=source_url,
                    source_type="next_data",
                )
            except Exception as exc:
                rejected_count += 1
                logger.debug("Producto Lidl NEXT_DATA rechazado: %s", exc)
                continue

            is_valid, reason = validate_scraped_product(product)

            if not is_valid:
                rejected_count += 1
                logger.debug(
                    "Producto Lidl NEXT_DATA inválido: nombre=%r motivo=%s",
                    product.nombre,
                    reason,
                )
                continue

            products.append(product)

        return products, rejected_count

    def _extract_product_nodes(self, data: Any) -> list[dict[str, Any]]:
        products: list[dict[str, Any]] = []

        def visit(node: Any) -> None:
            if isinstance(node, list):
                for item in node:
                    visit(item)
                return

            if not isinstance(node, dict):
                return

            if self._looks_like_product_node(node):
                products.append(node)

            for value in node.values():
                if isinstance(value, list | dict):
                    visit(value)

        visit(data)
        return products

    def _looks_like_product_node(self, node: dict[str, Any]) -> bool:
        name = self._first_non_empty(
            node.get("name"),
            node.get("title"),
            node.get("displayName"),
            node.get("display_name"),
            node.get("productName"),
        )

        price = self._extract_price_value(node)

        return bool(name and price is not None)

    def _build_product_from_structured_data(
        self,
        node: dict[str, Any],
        *,
        source_url: str,
        source_type: str,
    ) -> ScrapedProduct:
        name = self._first_non_empty(
            node.get("name"),
            node.get("title"),
            node.get("displayName"),
            node.get("display_name"),
            node.get("productName"),
        )

        if not name:
            raise ValueError("Producto Lidl sin nombre")

        price = self._extract_price_value(node)

        if price is None:
            raise ValueError(f"Producto Lidl sin precio: {name}")

        brand = self._extract_brand(node)

        category = self._first_non_empty(
            node.get("category"),
            node.get("categoryName"),
            node.get("breadcrumb"),
        )

        if isinstance(category, list):
            category = " > ".join(str(item) for item in category if item)

        relative_url = self._first_non_empty(
            node.get("url"),
            node.get("canonicalUrl"),
            node.get("productUrl"),
            node.get("href"),
        )

        image_url = self._extract_image_url(node)

        return ScrapedProduct(
            nombre=clean_text(name),
            precio=parse_price(price),
            supermercado=self.supermercado,
            marca=brand,
            categoria=clean_text(category).title() if category else None,
            unidad_medida=self._extract_unit(node),
            formato=self._extract_format(node),
            external_id=self._extract_external_id(node),
            url_producto=self._absolute_url(relative_url) or source_url,
            imagen_url=self._absolute_url(image_url),
            metadata={
                "source": source_type,
                "source_url": source_url,
            },
        )

    def _extract_price_value(self, node: dict[str, Any]) -> Optional[Any]:
        direct_price = self._first_non_empty(
            node.get("price"),
            node.get("salesPrice"),
            node.get("currentPrice"),
            node.get("finalPrice"),
            node.get("priceValue"),
        )

        if direct_price is not None:
            return self._normalize_possible_price(direct_price)

        offers = node.get("offers")

        if isinstance(offers, dict):
            offer_price = self._first_non_empty(
                offers.get("price"),
                offers.get("lowPrice"),
                offers.get("highPrice"),
            )

            if offer_price is not None:
                return self._normalize_possible_price(offer_price)

        if isinstance(offers, list):
            for offer in offers:
                if not isinstance(offer, dict):
                    continue

                offer_price = self._first_non_empty(
                    offer.get("price"),
                    offer.get("lowPrice"),
                    offer.get("highPrice"),
                )

                if offer_price is not None:
                    return self._normalize_possible_price(offer_price)

        price_info = self._first_non_empty(
            node.get("priceInfo"),
            node.get("pricing"),
            node.get("priceData"),
        )

        if isinstance(price_info, dict):
            nested_price = self._first_non_empty(
                price_info.get("price"),
                price_info.get("salesPrice"),
                price_info.get("currentPrice"),
                price_info.get("amount"),
                price_info.get("value"),
            )

            if nested_price is not None:
                return self._normalize_possible_price(nested_price)

        return None

    def _normalize_possible_price(self, value: Any) -> Optional[Any]:
        if isinstance(value, int | float | Decimal | str):
            return value

        if isinstance(value, dict):
            return self._first_non_empty(
                value.get("value"),
                value.get("amount"),
                value.get("price"),
                value.get("centAmount"),
            )

        return None

    def _extract_brand(self, node: dict[str, Any]) -> Optional[str]:
        brand = self._first_non_empty(
            node.get("brand"),
            node.get("manufacturer"),
            node.get("marca"),
        )

        if isinstance(brand, dict):
            brand = self._first_non_empty(
                brand.get("name"),
                brand.get("displayName"),
            )

        return clean_text(brand) if brand else None

    def _extract_unit(self, node: dict[str, Any]) -> Optional[str]:
        unit = self._first_non_empty(
            node.get("unit"),
            node.get("unitName"),
            node.get("baseUnit"),
            node.get("measurementUnit"),
        )

        return clean_text(unit).upper() if unit else None

    def _extract_format(self, node: dict[str, Any]) -> Optional[str]:
        return self._first_non_empty(
            node.get("unitPricingMeasure"),
            node.get("packageSize"),
            node.get("size"),
            node.get("quantity"),
            node.get("content"),
        )

    def _extract_external_id(self, node: dict[str, Any]) -> Optional[str]:
        value = self._first_non_empty(
            node.get("sku"),
            node.get("id"),
            node.get("productId"),
            node.get("gtin"),
        )

        return str(value) if value is not None else None

    def _extract_image_url(self, node: dict[str, Any]) -> Optional[str]:
        image = self._first_non_empty(
            node.get("image"),
            node.get("imageUrl"),
            node.get("thumbnail"),
        )

        if isinstance(image, list) and image:
            image = image[0]

        if isinstance(image, dict):
            image = self._first_non_empty(
                image.get("url"),
                image.get("src"),
            )

        return clean_text(image) if image else None

    def _absolute_url(self, value: Optional[Any]) -> Optional[str]:
        text = clean_text(value)

        if not text:
            return None

        if text.startswith("http://") or text.startswith("https://"):
            return text

        return urljoin(self.base_url or "https://www.lidl.es", text)

    def _lidl_headers(self) -> dict[str, str]:
        return {
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Referer": "https://www.lidl.es/",
            "Origin": "https://www.lidl.es",
        }

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