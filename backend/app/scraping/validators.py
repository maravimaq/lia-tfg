from __future__ import annotations

import re
from decimal import Decimal
from typing import Any

from app.scraping.base import ScrapedProduct, clean_text, normalize_for_matching


MIN_PRODUCT_NAME_LENGTH = 3
MAX_PRODUCT_NAME_LENGTH = 160
MIN_VALID_PRICE = Decimal("0.01")
MAX_VALID_PRICE = Decimal("999.99")


INVALID_EXACT_NAMES = {
    "envios",
    "envio",
    "mejor valorado",
    "mas vendido",
    "más vendido",
    "oferta",
    "ofertas",
    "descuento",
    "descuentos",
    "promocion",
    "promoción",
    "promociones",
    "comprar",
    "anadir",
    "añadir",
    "ver mas",
    "ver más",
    "ver todo",
    "ver todos",
    "inicio",
    "ayuda",
    "contacto",
    "faq",
    "preguntas frecuentes",
    "politica de privacidad",
    "política de privacidad",
    "politica de cookies",
    "política de cookies",
    "condiciones legales",
    "aviso legal",
}


INVALID_CONTAINS = {
    "dto",
    "% dto",
    "% descuento",
    "descuento",
    "envio gratis",
    "envío gratis",
    "gastos de envio",
    "gastos de envío",
    "recogida en tienda",
    "entrega a domicilio",
    "codigo postal",
    "código postal",
    "iniciar sesion",
    "iniciar sesión",
    "registrate",
    "regístrate",
    "mi cuenta",
    "carrito",
    "cesta",
    "tramitar pedido",
    "seguir comprando",
    "atencion al cliente",
    "atención al cliente",
    "politica de privacidad",
    "política de privacidad",
    "politica de cookies",
    "política de cookies",
    "aviso legal",
    "condiciones de compra",
    "condiciones legales",
    "newsletter",
    "suscribete",
    "suscríbete",
    "preguntas frecuentes",
    "sobre nosotros",
    "mapa web",
}


INVALID_PREFIXES = {
    "funcion ",
    "función ",
    "potencia",
    "medidas",
    "dimensiones",
    "alto ",
    "ancho ",
    "fondo ",
    "peso ",
    "capacidad ",
    "color ",
    "material ",
    "garantia ",
    "garantía ",
}


MEASURE_ONLY_RE = re.compile(
    r"^\s*\d+(?:[,.]\d+)?\s*(x\s*\d+(?:[,.]\d+)?\s*){1,3}"
    r"(cm|mm|m|kg|g|l|ml)?\s*$",
    re.IGNORECASE,
)


PRICE_LIKE_RE = re.compile(
    r"^\s*\d+(?:[,.]\d{1,2})?\s*€?\s*(/|por)?\s*(kg|g|l|ml|ud|unidad)?\s*$",
    re.IGNORECASE,
)

ONLY_NUMBERS_SYMBOLS_RE = re.compile(r"^[\d\s.,€%/+*\-x]+$", re.IGNORECASE)


def validate_scraped_product(product: ScrapedProduct) -> tuple[bool, str | None]:
    """
    Valida un producto scrapeado antes de importarlo a la tabla productos.

    Devuelve:
    - (True, None) si el producto parece válido.
    - (False, motivo) si debe rechazarse.
    """

    valid_name, name_reason = validate_product_name(product.nombre)
    if not valid_name:
        return False, name_reason

    valid_price, price_reason = validate_product_price(product.precio)
    if not valid_price:
        return False, price_reason

    if not clean_text(product.supermercado):
        return False, "supermercado vacío"

    return True, None


def validate_product_name(name: Any) -> tuple[bool, str | None]:
    raw_name = clean_text(name)
    normalized = normalize_for_matching(raw_name)

    if not raw_name:
        return False, "nombre vacío"

    if len(raw_name) < MIN_PRODUCT_NAME_LENGTH:
        return False, "nombre demasiado corto"

    if len(raw_name) > MAX_PRODUCT_NAME_LENGTH:
        return False, "nombre demasiado largo"

    if normalized in {normalize_for_matching(item) for item in INVALID_EXACT_NAMES}:
        return False, "nombre incluido en blacklist exacta"

    for invalid in INVALID_CONTAINS:
        if normalize_for_matching(invalid) in normalized:
            return False, f"nombre contiene texto no válido: {invalid}"

    for prefix in INVALID_PREFIXES:
        if normalized.startswith(normalize_for_matching(prefix)):
            return False, f"nombre empieza por texto técnico/no válido: {prefix}"

    if PRICE_LIKE_RE.match(raw_name):
        return False, "nombre parece ser solo un precio"

    if ONLY_NUMBERS_SYMBOLS_RE.match(raw_name):
        return False, "nombre solo contiene números o símbolos"

    if MEASURE_ONLY_RE.match(raw_name):
        return False, "nombre parece ser solo una medida"

    if looks_like_menu_or_action(raw_name):
        return False, "nombre parece ser navegación o acción de interfaz"

    return True, None


def validate_product_price(price: Any) -> tuple[bool, str | None]:
    try:
        decimal_price = Decimal(str(price))
    except Exception:
        return False, "precio no numérico"

    if decimal_price < MIN_VALID_PRICE:
        return False, "precio demasiado bajo"

    if decimal_price > MAX_VALID_PRICE:
        return False, "precio demasiado alto"

    return True, None


def looks_like_menu_or_action(text: Any) -> bool:
    normalized = normalize_for_matching(text)

    action_patterns = (
        r"^anadir .+ carrito$",
        r"^añadir .+ carrito$",
        r"^comprar .+ ahora$",
        r"^ver .+ productos$",
        r"^mostrar .+ resultados$",
        r"^ordenar por",
        r"^filtrar por",
        r"^aplicar filtros",
        r"^borrar filtros",
    )

    return any(re.search(pattern, normalized) for pattern in action_patterns)


def is_duplicate_candidate(product_a: ScrapedProduct, product_b: ScrapedProduct) -> bool:
    """
    Comparación simple para evitar duplicados dentro de una misma tanda scrapeada.

    No intenta ser inteligente de más: si mismo supermercado y mismo nombre normalizado,
    se considera duplicado.
    """

    return (
        product_a.normalized_supermarket == product_b.normalized_supermarket
        and product_a.normalized_name == product_b.normalized_name
    )


def build_product_key(product: ScrapedProduct) -> str:
    return f"{product.normalized_supermarket}::{product.normalized_name}"