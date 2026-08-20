from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from typing import Optional

from sqlalchemy.orm import Session

from app.models.producto import Producto
from app.scraping.base import ScrapedProduct, clean_text, normalize_for_matching
from app.scraping.validators import build_product_key, validate_scraped_product

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class RejectedProduct:
    nombre: str
    supermercado: str
    reason: str


@dataclass(slots=True)
class CatalogImportResult:
    supermercado: Optional[str] = None

    detected_count: int = 0
    valid_count: int = 0
    rejected_count: int = 0
    duplicated_count: int = 0

    created_count: int = 0
    updated_count: int = 0
    unchanged_count: int = 0

    rejected_products: list[RejectedProduct] = field(default_factory=list)

    @property
    def imported_count(self) -> int:
        return self.created_count + self.updated_count

    def to_dict(self) -> dict:
        return {
            "supermercado": self.supermercado,
            "detected_count": self.detected_count,
            "valid_count": self.valid_count,
            "rejected_count": self.rejected_count,
            "duplicated_count": self.duplicated_count,
            "created_count": self.created_count,
            "updated_count": self.updated_count,
            "unchanged_count": self.unchanged_count,
            "imported_count": self.imported_count,
            "rejected_products": [
                {
                    "nombre": item.nombre,
                    "supermercado": item.supermercado,
                    "reason": item.reason,
                }
                for item in self.rejected_products
            ],
        }


class CatalogImporter:
    """
    Importa productos scrapeados en la tabla `productos`.

    Estrategia actual sin migraciones:
    - Deduplicar la tanda scrapeada usando supermercado + nombre normalizado.
    - Buscar productos existentes del supermercado en BD.
    - Si existe mismo nombre normalizado, actualizar precio/datos.
    - Si no existe, crear producto nuevo.

    Más adelante se puede mejorar con columnas como:
    - external_id
    - url_producto
    - imagen_url
    """

    def __init__(self, db: Session) -> None:
        self.db = db

    def import_products(
        self,
        products: list[ScrapedProduct],
        *,
        supermercado: Optional[str] = None,
        commit: bool = True,
    ) -> CatalogImportResult:
        result = CatalogImportResult(supermercado=supermercado)
        result.detected_count = len(products)

        valid_products = self._validate_and_deduplicate(products, result)

        if not valid_products:
            if commit:
                self.db.commit()
            return result

        existing_by_key = self._load_existing_products_by_key(valid_products)

        for scraped_product in valid_products:
            key = build_product_key(scraped_product)
            existing_product = existing_by_key.get(key)

            if existing_product is None:
                created = self._create_product(scraped_product)
                existing_by_key[key] = created
                result.created_count += 1
                continue

            was_updated = self._update_product_if_needed(
                existing_product,
                scraped_product,
            )

            if was_updated:
                result.updated_count += 1
            else:
                result.unchanged_count += 1

        if commit:
            self.db.commit()

        logger.info(
            "Catálogo importado: supermercado=%s detectados=%s válidos=%s "
            "rechazados=%s duplicados=%s creados=%s actualizados=%s sin_cambios=%s",
            result.supermercado,
            result.detected_count,
            result.valid_count,
            result.rejected_count,
            result.duplicated_count,
            result.created_count,
            result.updated_count,
            result.unchanged_count,
        )

        return result

    def _validate_and_deduplicate(
        self,
        products: list[ScrapedProduct],
        result: CatalogImportResult,
    ) -> list[ScrapedProduct]:
        valid_products: list[ScrapedProduct] = []
        seen_keys: set[str] = set()

        for product in products:
            is_valid, reason = validate_scraped_product(product)

            if not is_valid:
                result.rejected_count += 1
                result.rejected_products.append(
                    RejectedProduct(
                        nombre=clean_text(product.nombre),
                        supermercado=clean_text(product.supermercado),
                        reason=reason or "producto rechazado",
                    )
                )
                continue

            key = build_product_key(product)

            if key in seen_keys:
                result.duplicated_count += 1
                continue

            seen_keys.add(key)
            valid_products.append(product)

        result.valid_count = len(valid_products)
        return valid_products

    def _load_existing_products_by_key(
        self,
        scraped_products: list[ScrapedProduct],
    ) -> dict[str, Producto]:
        supermarkets = {
            clean_text(product.supermercado)
            for product in scraped_products
            if clean_text(product.supermercado)
        }

        if not supermarkets:
            return {}

        existing_products = (
            self.db.query(Producto)
            .filter(Producto.supermercado.in_(supermarkets))
            .all()
        )

        existing_by_key: dict[str, Producto] = {}

        for product in existing_products:
            supermarket = clean_text(product.supermercado)
            name = clean_text(product.nombre)

            key = (
                f"{normalize_for_matching(supermarket)}::"
                f"{normalize_for_matching(name)}"
            )

            existing_by_key[key] = product

        return existing_by_key

    def _create_product(self, scraped_product: ScrapedProduct) -> Producto:
        product = Producto(
            nombre=scraped_product.nombre,
            marca=scraped_product.marca,
            categoria=scraped_product.categoria,
            supermercado=scraped_product.supermercado,
            precio_unitario=self._to_decimal(scraped_product.precio),
            unidad_medida=scraped_product.unidad_medida or scraped_product.formato,
            imagen_url=scraped_product.imagen_url,
            fecha_actualizacion=datetime.utcnow(),
        )

        self.db.add(product)

        logger.debug(
            "Producto creado desde scraping: supermercado=%s nombre=%s precio=%s",
            product.supermercado,
            product.nombre,
            product.precio_unitario,
        )

        return product

    def _update_product_if_needed(
        self,
        existing_product: Producto,
        scraped_product: ScrapedProduct,
    ) -> bool:
        changed = False

        new_price = self._to_decimal(scraped_product.precio)
        current_price = self._to_decimal(existing_product.precio_unitario)

        if current_price != new_price:
            existing_product.precio_unitario = new_price
            changed = True

        if self._should_replace_text(existing_product.marca, scraped_product.marca):
            existing_product.marca = scraped_product.marca
            changed = True

        if self._should_replace_text(existing_product.categoria, scraped_product.categoria):
            existing_product.categoria = scraped_product.categoria
            changed = True

        new_unit = scraped_product.unidad_medida or scraped_product.formato
        if self._should_replace_text(existing_product.unidad_medida, new_unit):
            existing_product.unidad_medida = new_unit
            changed = True

        if self._should_replace_text(
            existing_product.imagen_url,
            scraped_product.imagen_url,
        ):
            existing_product.imagen_url = scraped_product.imagen_url
            changed = True

        if changed:
            existing_product.fecha_actualizacion = datetime.utcnow()

            logger.debug(
                "Producto actualizado desde scraping: supermercado=%s nombre=%s precio=%s",
                existing_product.supermercado,
                existing_product.nombre,
                existing_product.precio_unitario,
            )

        return changed

    @staticmethod
    def _should_replace_text(current_value: Optional[str], new_value: Optional[str]) -> bool:
        current = clean_text(current_value)
        new = clean_text(new_value)

        if not new:
            return False

        if not current:
            return True

        return current != new

    @staticmethod
    def _to_decimal(value) -> Decimal:
        return Decimal(str(value)).quantize(Decimal("0.01"))