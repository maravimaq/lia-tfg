import asyncio
import json
import math
import re
import threading
from difflib import SequenceMatcher
from io import BytesIO
from datetime import datetime
import urllib.parse as url_parse

import httpx
from bs4 import BeautifulSoup
from fastapi import HTTPException, status
from pypdf import PdfReader
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import hash_password
from app.db.session import SessionLocal
from app.models.producto import Producto
from app.models.user import User
from app.scraping.scraping_runner import ScrapingRunner
from app.repositories.account_request_repository import AccountRequestRepository
from app.repositories.lista_compra_repository import ListaCompraRepository
from app.repositories.role_repository import RoleRepository
from app.repositories.user_repository import UserRepository
from app.schemas.admin import (
    AdminDashboardResponse,
    AdminScrapingActionResponse,
    AdminScrapingOverviewResponse,
    AdminScrapingStoreStatus,
    AdminUserCreate,
    AdminUserListItem,
    AdminUsersPageResponse,
    AdminUserUpdate,
)


class AdminService:
    DEFAULT_PRICE_REGEX = r"(\d{1,3}(?:[\.,]\d{3})*[\.,]\d{1,2})\s?€?"

    _scraping_lock = threading.Lock()
    _scraping_state = {
        "ultima_ejecucion_fecha": "-",
        "ultima_ejecucion_estado": "idle",
        "progreso_general": 0,
        "en_curso": False,
        "tiempo_restante_segundos": 0,
        "detalle_error": None,
        "cancel_requested": False,
        "fuentes": [],
    }

    @staticmethod
    def _build_request_headers(
        url: str,
        *,
        json_preferred: bool = False,
    ) -> dict[str, str]:
        parsed = url_parse.urlparse(url)
        origin = f"{parsed.scheme}://{parsed.netloc}"

        return {
            "User-Agent": settings.scraping_user_agent,
            "Accept": (
                "application/json,text/plain,*/*"
                if json_preferred
                else "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"
            ),
            "Accept-Language": "es-ES,es;q=0.9,en;q=0.8",
            "Cache-Control": "no-cache",
            "Pragma": "no-cache",
            "Referer": origin,
            "Origin": origin,
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
        }

    @staticmethod
    def _fetch_url(
        url: str,
        *,
        timeout_seconds: int | None = None,
    ) -> httpx.Response:
        timeout = timeout_seconds or settings.scraping_timeout_seconds

        attempts = [
            {"json_preferred": url.endswith("/api/categories/") or "/api/" in url},
            {"json_preferred": False},
        ]

        last_exc = None

        for attempt in attempts:
            try:
                response = httpx.get(
                    url,
                    timeout=timeout,
                    headers=AdminService._build_request_headers(
                        url,
                        json_preferred=attempt["json_preferred"],
                    ),
                    follow_redirects=True,
                )
                response.raise_for_status()
                return response
            except Exception as exc:
                last_exc = exc
                continue

        raise last_exc if last_exc else RuntimeError(f"No se pudo acceder a {url}")

    @staticmethod
    def _validate_estado(estado: str) -> str:
        estado_normalizado = estado.strip().lower()

        if estado_normalizado not in {"activo", "inactivo"}:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="El estado debe ser 'activo' o 'inactivo'",
            )

        return estado_normalizado

    @staticmethod
    def _get_role_or_404(db: Session, rol_nombre: str):
        role = RoleRepository.get_by_name(db, rol_nombre.strip().lower())

        if not role:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"El rol '{rol_nombre}' no existe",
            )

        return role

    @staticmethod
    def _map_user(user: User) -> AdminUserListItem:
        return AdminUserListItem(
            id_usuario=user.id_usuario,
            nombre_usuario=user.nombre_usuario,
            nombre_completo=user.nombre_completo,
            email=user.email,
            telefono=user.telefono,
            estado=user.estado,
            rol_id=user.rol_id,
            rol_nombre=user.rol.nombre if user.rol else "",
            fecha_registro=user.fecha_registro,
        )

    @staticmethod
    def _build_default_sources() -> list[dict]:
        """
        Fuentes activas por defecto para el nuevo sistema de scraping.

        DIA y Mercadona ya usan scrapers estructurados.
        Lidl y Carrefour se añadirán cuando tengan una extracción fiable.
        """

        return [
            {
                "supermercado": "DIA",
                "urls": ["https://www.dia.es"],
                "crawl_internal_links": False,
                "link_include_regex": None,
                "selector": None,
                "price_regex": AdminService.DEFAULT_PRICE_REGEX,
            },
            {
                "supermercado": "Mercadona",
                "urls": ["https://tienda.mercadona.es"],
                "crawl_internal_links": False,
                "link_include_regex": None,
                "selector": None,
                "price_regex": AdminService.DEFAULT_PRICE_REGEX,
            },
            {
                "supermercado": "Carrefour",
                "urls": ["https://www.carrefour.es/supermercado"],
                "crawl_internal_links": False,
                "link_include_regex": None,
                "selector": None,
                "price_regex": AdminService.DEFAULT_PRICE_REGEX,
            },
            {
                "supermercado": "ALDI",
                "urls": ["https://www.aldi.es/ofertas.html"],
                "crawl_internal_links": False,
                "link_include_regex": None,
                "selector": None,
                "price_regex": AdminService.DEFAULT_PRICE_REGEX,
            },
            {
                "supermercado": "Alcampo",
                "urls": ["https://www.compraonline.alcampo.es/categories"],
                "crawl_internal_links": False,
                "link_include_regex": None,
                "selector": None,
                "price_regex": AdminService.DEFAULT_PRICE_REGEX,
            },
        ]

    @staticmethod
    def _get_configured_sources() -> list[dict]:
        raw_json = settings.scraping_sources_json

        if not raw_json:
            return AdminService._build_default_sources()

        try:
            configured = json.loads(raw_json)

            if not isinstance(configured, list):
                raise ValueError("SCRAPING_SOURCES_JSON debe ser una lista")

            normalized = []

            for item in configured:
                if not isinstance(item, dict):
                    continue

                supermercado = item.get("supermercado")
                urls = item.get("urls")
                url = item.get("url")

                if not urls and url:
                    urls = [url]

                if not supermercado or not urls:
                    continue

                normalized.append(
                    {
                        "supermercado": supermercado,
                        "urls": urls,
                        "crawl_internal_links": item.get("crawl_internal_links", True),
                        "link_include_regex": item.get("link_include_regex"),
                        "selector": item.get("selector"),
                        "price_regex": item.get("price_regex")
                        or AdminService.DEFAULT_PRICE_REGEX,
                    }
                )

            return normalized or AdminService._build_default_sources()
        except Exception:
            return AdminService._build_default_sources()

    @staticmethod
    def _ensure_state_sources_loaded() -> None:
        with AdminService._scraping_lock:
            if AdminService._scraping_state["fuentes"]:
                return

            AdminService._scraping_state["fuentes"] = [
                {
                    "supermercado": source["supermercado"],
                    "estado": "pendiente",
                    "fecha": "-",
                    "urls": source.get("urls", []),
                    "crawl_internal_links": source.get("crawl_internal_links", True),
                    "link_include_regex": source.get("link_include_regex"),
                    "selector": source.get("selector"),
                    "price_regex": source.get("price_regex")
                    or AdminService.DEFAULT_PRICE_REGEX,
                    "precios_detectados": 0,
                    "productos_actualizados": 0,
                    "warning": None,
                    "detalle_error": None,
                }
                for source in AdminService._get_configured_sources()
            ]

    @staticmethod
    def _parse_price(raw: object) -> float | None:
        if raw is None:
            return None

        cleaned = str(raw).strip().replace("€", "").replace(" ", "")

        if "," in cleaned and "." in cleaned:
            if cleaned.rfind(",") > cleaned.rfind("."):
                cleaned = cleaned.replace(".", "").replace(",", ".")
            else:
                cleaned = cleaned.replace(",", "")
        else:
            cleaned = cleaned.replace(",", ".")

        try:
            value = float(cleaned)

            if value <= 0:
                return None

            return value
        except ValueError:
            return None

    @staticmethod
    def _extract_prices(html: str, selector: str | None, price_regex: str) -> list[float]:
        soup = BeautifulSoup(html, "html.parser")

        texts: list[str] = []

        if selector:
            texts.extend(node.get_text(" ", strip=True) for node in soup.select(selector))

        if not texts:
            texts = [soup.get_text(" ", strip=True)]

        texts.extend(script.get_text(" ", strip=True) for script in soup.find_all("script"))

        pattern = re.compile(price_regex)
        prices: list[float] = []

        for text in texts:
            for match in pattern.findall(text):
                raw = match if isinstance(match, str) else match[0]
                parsed = AdminService._parse_price(raw)

                if parsed is not None:
                    prices.append(parsed)

        json_price_pattern = re.compile(
            r'"(?:price|salePrice|unitPrice|amount|value)"\s*:\s*"?(\d+(?:[.,]\d{1,2})?)"?',
            re.IGNORECASE,
        )

        for text in texts:
            for raw in json_price_pattern.findall(text):
                parsed = AdminService._parse_price(raw)

                if parsed is not None:
                    prices.append(parsed)

        def collect_prices_from_obj(obj):
            if isinstance(obj, dict):
                for key, value in obj.items():
                    key_lower = str(key).lower()

                    if any(
                        token in key_lower
                        for token in ["price", "precio", "amount", "importe", "value"]
                    ):
                        if isinstance(value, (int, float, str)):
                            parsed = AdminService._parse_price(str(value))

                            if parsed is not None:
                                prices.append(parsed)

                    collect_prices_from_obj(value)

            elif isinstance(obj, list):
                for item in obj:
                    collect_prices_from_obj(item)

        for script in soup.find_all("script"):
            raw_script = script.get_text(" ", strip=True)

            if not raw_script or ("{" not in raw_script and "[" not in raw_script):
                continue

            candidates = AdminService._extract_json_candidates_from_script(raw_script)

            for candidate in candidates:
                try:
                    parsed_json = json.loads(candidate)
                    collect_prices_from_obj(parsed_json)
                except Exception:
                    continue

        return sorted(set(prices))

    @staticmethod
    def _extract_prices_from_pdf(content: bytes, price_regex: str) -> list[float]:
        reader = PdfReader(BytesIO(content))
        text_chunks: list[str] = []

        for page in reader.pages:
            page_text = page.extract_text() or ""
            text_chunks.append(page_text)

        pattern = re.compile(price_regex)
        prices: list[float] = []

        for text in text_chunks:
            for match in pattern.findall(text):
                raw = match if isinstance(match, str) else match[0]
                parsed = AdminService._parse_price(raw)

                if parsed is not None:
                    prices.append(parsed)

        return prices

    @staticmethod
    def _discover_internal_urls(
        base_url: str,
        include_pattern: str | None,
        max_urls: int = 40,
    ) -> list[str]:
        try:
            response = AdminService._fetch_url(base_url)
        except Exception:
            return [base_url]

        soup = BeautifulSoup(response.text, "html.parser")
        base_host = url_parse.urlparse(base_url).netloc
        include_regex = re.compile(include_pattern) if include_pattern else None
        discovered: list[str] = [base_url]
        seen: set[str] = {base_url}

        for anchor in soup.find_all("a", href=True):
            href = anchor["href"].strip()
            full_url = url_parse.urljoin(base_url, href)
            parsed = url_parse.urlparse(full_url)

            if parsed.scheme not in {"http", "https"}:
                continue

            if parsed.netloc != base_host:
                continue

            normalized = f"{parsed.scheme}://{parsed.netloc}{parsed.path}"

            if include_regex and not include_regex.search(normalized):
                continue

            if normalized in seen:
                continue

            seen.add(normalized)
            discovered.append(normalized)

            if len(discovered) >= max_urls:
                break

        return discovered

    @staticmethod
    def _discover_mercadona_category_urls(base_url: str) -> list[str]:
        try:
            response = AdminService._fetch_url(
                "https://tienda.mercadona.es/api/categories/"
            )
            data = response.json()
        except Exception:
            return [base_url]

        ids: set[int] = set()

        def walk(nodes):
            for node in nodes or []:
                node_id = node.get("id")

                if isinstance(node_id, int):
                    ids.add(node_id)

                walk(node.get("categories"))

        if isinstance(data, list):
            walk(data)

        if not ids:
            return [base_url]

        urls = [base_url, "https://tienda.mercadona.es/api/categories/"]
        urls.extend(
            [f"https://tienda.mercadona.es/api/categories/{cat_id}" for cat_id in sorted(ids)]
        )

        return urls[:120]

    @staticmethod
    def _expand_source_urls(source: dict) -> list[str]:
        base_urls = source.get("urls", [])

        if not base_urls:
            return []

        if not source.get("crawl_internal_links", True):
            return base_urls

        include_pattern = source.get("link_include_regex")
        expanded: list[str] = []
        seen: set[str] = set()

        for base_url in base_urls:
            mercadona_source = "tienda.mercadona.es" in base_url

            if mercadona_source:
                discovered = AdminService._discover_mercadona_category_urls(base_url)
            else:
                discovered = AdminService._discover_internal_urls(
                    base_url,
                    include_pattern,
                )

            for url in discovered:
                if url in seen:
                    continue

                seen.add(url)
                expanded.append(url)

        return expanded or base_urls

    @staticmethod
    def _normalize_product_text(value: str | None) -> str:
        if not value:
            return ""

        normalized = value.strip().lower()
        normalized = re.sub(r"[^\w\sáéíóúüñ]", " ", normalized)
        normalized = re.sub(r"\s+", " ", normalized)

        return normalized.strip()

    @staticmethod
    def _similarity(a: str, b: str) -> float:
        a_normalized = AdminService._normalize_product_text(a)
        b_normalized = AdminService._normalize_product_text(b)

        if not a_normalized or not b_normalized:
            return 0.0

        return SequenceMatcher(None, a_normalized, b_normalized).ratio()

    @staticmethod
    def _extract_json_candidates_from_script(raw_script: str) -> list[str]:
        candidates: list[str] = []
        trimmed = raw_script.strip()

        if trimmed.startswith("{") or trimmed.startswith("["):
            candidates.append(trimmed)

        for marker in ("window.__", "INITIAL_STATE", "__NEXT_DATA__", "dataLayer"):
            marker_pos = raw_script.find(marker)

            if marker_pos < 0:
                continue

            start_obj = raw_script.find("{", marker_pos)
            start_arr = raw_script.find("[", marker_pos)
            starts = [pos for pos in (start_obj, start_arr) if pos >= 0]

            if starts:
                possible_json = raw_script[min(starts):].strip()

                if possible_json.endswith(";"):
                    possible_json = possible_json[:-1]

                candidates.append(possible_json)

        cleaned_candidates = []

        for candidate in candidates:
            cleaned = candidate.strip()

            if cleaned.endswith(";"):
                cleaned = cleaned[:-1]

            cleaned_candidates.append(cleaned)

        return cleaned_candidates

    @staticmethod
    def _extract_product_prices_from_json_like_html(html: str) -> list[dict]:
        soup = BeautifulSoup(html, "html.parser")
        scraped_products: list[dict] = []

        def find_name(obj: dict) -> str | None:
            name_keys = [
                "name",
                "nombre",
                "title",
                "titulo",
                "productName",
                "displayName",
                "description",
                "descripcion",
            ]

            for key in name_keys:
                value = obj.get(key)

                if isinstance(value, str) and len(value.strip()) >= 3:
                    return value.strip()

            return None

        def find_price(obj: dict) -> float | None:
            price_keys = [
                "price",
                "precio",
                "salePrice",
                "unitPrice",
                "amount",
                "value",
                "currentPrice",
                "finalPrice",
            ]

            for key, value in obj.items():
                key_lower = str(key).lower()

                if any(price_key.lower() in key_lower for price_key in price_keys):
                    parsed = AdminService._parse_price(value)

                    if parsed is not None:
                        return parsed

            return None

        def find_brand(obj: dict) -> str | None:
            brand_keys = ["brand", "marca", "manufacturer"]

            for key in brand_keys:
                value = obj.get(key)

                if isinstance(value, str) and value.strip():
                    return value.strip()

                if isinstance(value, dict):
                    nested_name = value.get("name") or value.get("nombre")

                    if isinstance(nested_name, str) and nested_name.strip():
                        return nested_name.strip()

            return None

        def find_category(obj: dict) -> str | None:
            category_keys = ["category", "categoria", "categories", "breadcrumb"]

            for key in category_keys:
                value = obj.get(key)

                if isinstance(value, str) and value.strip():
                    return value.strip()

                if isinstance(value, list) and value:
                    parts = []

                    for item in value:
                        if isinstance(item, str):
                            parts.append(item)
                        elif isinstance(item, dict):
                            name = item.get("name") or item.get("nombre")
                            if isinstance(name, str):
                                parts.append(name)

                    if parts:
                        return " > ".join(parts[:3])

            return None

        def find_unit(obj: dict) -> str | None:
            unit_keys = [
                "unit",
                "unidad",
                "unitName",
                "unit_name",
                "measure",
                "measurement",
                "format",
                "formato",
            ]

            for key in unit_keys:
                value = obj.get(key)

                if isinstance(value, str) and value.strip():
                    return value.strip()

            return None

        def walk(obj):
            if isinstance(obj, dict):
                name = find_name(obj)
                price = find_price(obj)

                if name and price is not None:
                    scraped_products.append(
                        {
                            "nombre": name,
                            "precio": round(price, 2),
                            "marca": find_brand(obj),
                            "categoria": find_category(obj),
                            "unidad_medida": find_unit(obj),
                        }
                    )

                for value in obj.values():
                    walk(value)

            elif isinstance(obj, list):
                for item in obj:
                    walk(item)

        for script in soup.find_all("script"):
            raw_script = script.get_text(" ", strip=True)

            if not raw_script or ("{" not in raw_script and "[" not in raw_script):
                continue

            candidates = AdminService._extract_json_candidates_from_script(raw_script)

            for candidate in candidates:
                try:
                    parsed_json = json.loads(candidate)
                    walk(parsed_json)
                except Exception:
                    continue

        unique: dict[str, dict] = {}

        for item in scraped_products:
            key = AdminService._normalize_product_text(item["nombre"])

            if not key:
                continue

            unique[key] = item

        return list(unique.values())

    @staticmethod
    def _extract_product_prices_from_visible_html(
        html: str,
        price_regex: str,
    ) -> list[dict]:
        soup = BeautifulSoup(html, "html.parser")
        pattern = re.compile(price_regex)
        scraped_products: list[dict] = []

        product_like_selectors = [
            "[data-test*='product']",
            "[data-testid*='product']",
            "[data-qa*='product']",
            "[class*='product']",
            "[class*='Product']",
            "[class*='product-card']",
            "[class*='ProductCard']",
            "article",
        ]

        name_selectors = [
            "[data-test*='name']",
            "[data-testid*='name']",
            "[data-qa*='name']",
            "[class*='name']",
            "[class*='Name']",
            "[class*='title']",
            "[class*='Title']",
            "h1",
            "h2",
            "h3",
            "h4",
            "a",
        ]

        def clean_text(value: str | None) -> str:
            return re.sub(r"\s+", " ", value or "").strip()

        def contains_price(value: str) -> bool:
            return bool(pattern.search(value))

        def extract_price(value: str) -> float | None:
            match = pattern.search(value)

            if not match:
                return None

            raw = match.group(1) if match.groups() else match.group(0)
            return AdminService._parse_price(raw)

        def has_product_structure(node) -> bool:
            has_image_alt = any(
                clean_text(img.get("alt"))
                for img in node.find_all("img")
            )

            has_product_link = any(
                "/p/" in (anchor.get("href") or "")
                or "/producto" in (anchor.get("href") or "").lower()
                or "/product" in (anchor.get("href") or "").lower()
                for anchor in node.find_all("a", href=True)
            )

            class_text = " ".join(node.get("class") or []).lower()
            has_product_class = "product" in class_text or "producto" in class_text

            return has_image_alt or has_product_link or has_product_class

        def find_name_from_node(node) -> str | None:
            candidates: list[str] = []

            for img in node.find_all("img"):
                alt = clean_text(img.get("alt"))

                if alt:
                    candidates.append(alt)

            for selector in name_selectors:
                for child in node.select(selector):
                    text = clean_text(child.get_text(" ", strip=True))

                    if text:
                        candidates.append(text)

                    title = clean_text(child.get("title"))

                    if title:
                        candidates.append(title)

                    aria_label = clean_text(child.get("aria-label"))

                    if aria_label:
                        candidates.append(aria_label)

            for candidate in candidates:
                if contains_price(candidate):
                    continue

                if not AdminService._is_valid_scraped_product_name(candidate):
                    continue

                return candidate

            return None

        seen_nodes: set[int] = set()

        for selector in product_like_selectors:
            for node in soup.select(selector):
                node_id = id(node)

                if node_id in seen_nodes:
                    continue

                seen_nodes.add(node_id)

                text = clean_text(node.get_text(" ", strip=True))

                if not text or not contains_price(text):
                    continue

                if not has_product_structure(node):
                    continue

                price = extract_price(text)
                name = find_name_from_node(node)

                if name and price is not None:
                    scraped_products.append(
                        {
                            "nombre": name,
                            "precio": round(price, 2),
                            "marca": None,
                            "categoria": None,
                            "unidad_medida": "unidad",
                        }
                    )

        unique: dict[str, dict] = {}

        for item in scraped_products:
            key = AdminService._normalize_product_text(
                f"{item['nombre']} {item['precio']}"
            )

            if not key:
                continue

            unique[key] = item

        return list(unique.values())

    @staticmethod
    def _is_valid_scraped_product_name(name: str | None) -> bool:
        if not name:
            return False

        raw = name.strip()
        normalized = AdminService._normalize_product_text(raw)

        if len(normalized) < 4:
            return False

        if len(normalized) > 140:
            return False

        if raw.endswith("."):
            return False

        if "?" in raw or "¿" in raw:
            return False

        if "%" in raw:
            return False

        if "€" in raw:
            return False

        if normalized.replace(" ", "").isdigit():
            return False

        blacklist_phrases = {
            "precio",
            "oferta",
            "ofertas",
            "comprar",
            "añadir",
            "carrito",
            "supermercado",
            "inicio",
            "categorias",
            "categoría",
            "promociones",
            "promocion",
            "promoción",
            "descuento",
            "dto",
            "envio",
            "envío",
            "envios",
            "envíos",
            "entrega",
            "pedido",
            "pedidos",
            "login",
            "registrarse",
            "gastos",
            "gastos de envio",
            "gastos de envío",
            "funcion",
            "función",
            "potencia",
            "medidas",
            "alto",
            "ancho",
            "largo",
            "actividad fisica",
            "actividad física",
            "produccion",
            "producción",
            "sudamerica",
            "sudamérica",
            "asia",
            "mejor valorado",
            "iva incluido",
            "ver producto",
            "mas informacion",
            "más información",
            "atencion al cliente",
            "atención al cliente",
            "politica de privacidad",
            "política de privacidad",
            "condiciones",
            "cookies",
            "newsletter",
            "app dia",
            "club dia",
        }

        if normalized in blacklist_phrases:
            return False

        if any(phrase in normalized for phrase in blacklist_phrases):
            return False

        return True

    @staticmethod
    def _is_valid_scraped_price(price: object) -> bool:
        try:
            value = float(price)
        except (TypeError, ValueError):
            return False

        return 0.05 <= value <= 100

    @staticmethod
    def _find_existing_product_for_upsert(
        db: Session,
        store: str,
        scraped_name: str,
        min_score: float = 0.86,
    ) -> Producto | None:
        target_store = store.strip().lower()
        scraped_normalized = AdminService._normalize_product_text(scraped_name)

        products = (
            db.query(Producto)
            .filter(Producto.supermercado.isnot(None))
            .all()
        )

        best_product = None
        best_score = 0.0

        for product in products:
            product_store = (product.supermercado or "").strip().lower()

            if product_store != target_store:
                continue

            product_normalized = AdminService._normalize_product_text(product.nombre)

            if not product_normalized:
                continue

            if product_normalized == scraped_normalized:
                return product

            score = AdminService._similarity(product.nombre, scraped_name)

            if score > best_score:
                best_score = score
                best_product = product

        if best_score < min_score:
            return None

        return best_product

    @staticmethod
    def _upsert_products_from_scraped_items(
        db: Session,
        store: str,
        scraped_items: list[dict],
        max_items: int = 300,
    ) -> int:
        modified = 0
        seen_names: set[str] = set()

        for scraped_item in scraped_items[:max_items]:
            scraped_name = scraped_item.get("nombre")
            scraped_price = scraped_item.get("precio")

            if not AdminService._is_valid_scraped_product_name(scraped_name):
                continue

            if not AdminService._is_valid_scraped_price(scraped_price):
                continue

            normalized_name = AdminService._normalize_product_text(scraped_name)

            if normalized_name in seen_names:
                continue

            seen_names.add(normalized_name)

            existing_product = AdminService._find_existing_product_for_upsert(
                db=db,
                store=store,
                scraped_name=scraped_name,
            )

            if existing_product:
                existing_product.precio_unitario = round(float(scraped_price), 2)
                existing_product.fecha_actualizacion = datetime.utcnow()
                modified += 1
                continue

            new_product = Producto(
                nombre=scraped_name.strip(),
                marca=scraped_item.get("marca"),
                categoria=scraped_item.get("categoria") or "Sin categoría",
                supermercado=store,
                precio_unitario=round(float(scraped_price), 2),
                unidad_medida=scraped_item.get("unidad_medida") or "unidad",
                fecha_actualizacion=datetime.utcnow(),
            )

            db.add(new_product)
            modified += 1

        if modified > 0:
            db.commit()

        return modified

    @staticmethod
    def _run_scraping_job() -> None:
        db = SessionLocal()
        start = datetime.now()

        try:
            with AdminService._scraping_lock:
                sources = list(AdminService._scraping_state["fuentes"])

            total = len(sources)
            errors: list[str] = []

            for index, source in enumerate(sources, start=1):
                with AdminService._scraping_lock:
                    if AdminService._scraping_state["cancel_requested"]:
                        break

                supermercado = str(source.get("supermercado") or "").strip()
                supermercado_key = supermercado.upper()

                with AdminService._scraping_lock:
                    source["estado"] = "en_proceso"
                    source["fecha"] = datetime.now().strftime("%d %b %Y - %H:%M")
                    source["warning"] = None
                    source["detalle_error"] = None
                    source["precios_detectados"] = 0
                    source["productos_actualizados"] = 0

                try:
                    if supermercado_key not in {"DIA", "MERCADONA", "CARREFOUR", "ALDI", "ALCAMPO"}:
                        with AdminService._scraping_lock:
                            source["estado"] = "pendiente"
                            source["fecha"] = datetime.now().strftime("%d %b %Y - %H:%M")
                            source["precios_detectados"] = 0
                            source["productos_actualizados"] = 0
                            source["warning"] = (
                                "Fuente todavía no conectada al nuevo sistema de scraping. "
                                "Se omite para evitar importar productos basura desde HTML genérico."
                            )
                            source["detalle_error"] = None

                    else:
                        runner = ScrapingRunner(
                            db,
                            timeout_seconds=settings.scraping_timeout_seconds,
                            user_agent=settings.scraping_user_agent,
                            dia_cookie=settings.dia_cookie,
                            dia_max_categories=settings.dia_max_categories,
                            dia_max_pages_per_category=settings.dia_max_pages_per_category,
                            mercadona_max_categories=settings.mercadona_max_categories,
                            carrefour_max_urls=settings.carrefour_max_urls,
                            carrefour_max_products_per_url=settings.carrefour_max_products_per_url,
                            carrefour_max_pages_per_url=settings.carrefour_max_pages_per_url,
                            carrefour_use_playwright_fallback=settings.carrefour_use_playwright_fallback,
                            aldi_max_listing_urls=settings.aldi_max_listing_urls,
                            aldi_max_article_links=settings.aldi_max_article_links,
                            aldi_max_products=settings.aldi_max_products,
                            aldi_use_playwright_fallback=settings.aldi_use_playwright_fallback,
                            alcampo_max_urls=settings.alcampo_max_urls,
                            alcampo_max_products_per_url=settings.alcampo_max_products_per_url,
                            alcampo_use_playwright_fallback=settings.alcampo_use_playwright_fallback,
                        )

                        summary = asyncio.run(
                            runner.run(
                                supermarkets=[supermercado_key],
                                commit=True,
                            )
                        )

                        source_result = next(
                            (
                                item
                                for item in summary.sources
                                if item.supermercado.upper() == supermercado_key
                            ),
                            None,
                        )

                        if source_result is None:
                            raise ValueError(
                                f"No se ha obtenido resultado para {supermercado}"
                            )

                        if source_result.scraper_status in {"success", "partial"}:
                            estado = "ok"
                        elif source_result.scraper_status == "empty":
                            estado = "error"
                        else:
                            estado = "error"

                        warning_message = None

                        if source_result.scraper_status == "empty":
                            warning_message = (
                                "La fuente respondió, pero no se han obtenido productos válidos."
                            )
                        elif source_result.scraper_status == "blocked":
                            warning_message = (
                                "Acceso bloqueado por la tienda. Puede requerir cookie, "
                                "API alternativa o integración con navegador."
                            )
                        elif source_result.imported_count == 0 and source_result.unchanged_count > 0:
                            warning_message = (
                                "Productos detectados correctamente, pero no había cambios nuevos "
                                "respecto a los productos ya guardados."
                            )
                        elif source_result.imported_count == 0:
                            warning_message = (
                                "Se detectaron productos, pero ninguno terminó creando "
                                "o actualizando registros en el catálogo."
                            )

                        with AdminService._scraping_lock:
                            source["estado"] = estado
                            source["fecha"] = datetime.now().strftime("%d %b %Y - %H:%M")
                            source["precios_detectados"] = source_result.detected_count
                            source["productos_actualizados"] = source_result.imported_count
                            source["warning"] = warning_message
                            source["detalle_error"] = source_result.error

                        if estado == "error":
                            errors.append(
                                f"{supermercado}: "
                                f"{source_result.error or warning_message or 'error en scraping'}"
                            )

                except Exception as exc:
                    db.rollback()

                    with AdminService._scraping_lock:
                        source["estado"] = "error"
                        source["fecha"] = datetime.now().strftime("%d %b %Y - %H:%M")
                        source["precios_detectados"] = 0
                        source["productos_actualizados"] = 0
                        source["warning"] = None
                        source["detalle_error"] = str(exc)

                    errors.append(f"{supermercado}: {str(exc)}")

                elapsed = (datetime.now() - start).total_seconds()
                avg_seconds = elapsed / index if index else 0
                remaining = max(int(avg_seconds * (total - index)), 0)
                progress = int((index / total) * 100) if total > 0 else 100

                with AdminService._scraping_lock:
                    AdminService._scraping_state["progreso_general"] = progress
                    AdminService._scraping_state["tiempo_restante_segundos"] = remaining

            with AdminService._scraping_lock:
                AdminService._scraping_state["en_curso"] = False
                AdminService._scraping_state["ultima_ejecucion_fecha"] = (
                    datetime.now().strftime("%d %b %Y - %H:%M")
                )

                if AdminService._scraping_state["cancel_requested"]:
                    AdminService._scraping_state["ultima_ejecucion_estado"] = "cancelado"
                else:
                    successful_sources = [
                        source
                        for source in AdminService._scraping_state["fuentes"]
                        if source.get("estado") == "ok"
                    ]

                    failed_sources = [
                        source
                        for source in AdminService._scraping_state["fuentes"]
                        if source.get("estado") == "error"
                    ]

                    if successful_sources and failed_sources:
                        AdminService._scraping_state["ultima_ejecucion_estado"] = "parcial"
                    elif successful_sources and not failed_sources:
                        AdminService._scraping_state["ultima_ejecucion_estado"] = "ok"
                    elif failed_sources:
                        AdminService._scraping_state["ultima_ejecucion_estado"] = "error"
                    else:
                        AdminService._scraping_state["ultima_ejecucion_estado"] = "sin_cambios"

                AdminService._scraping_state["detalle_error"] = (
                    "; ".join(errors) if errors else None
                )
                AdminService._scraping_state["tiempo_restante_segundos"] = 0
                AdminService._scraping_state["cancel_requested"] = False

        finally:
            db.close()

    @staticmethod
    def get_dashboard(db: Session) -> AdminDashboardResponse:
        total_usuarios = UserRepository.count_all(db)
        total_usuarios_activos = UserRepository.count_by_estado(db, "activo")
        total_usuarios_inactivos = UserRepository.count_by_estado(db, "inactivo")
        total_listas = ListaCompraRepository.count_all(db)

        ultimo_usuario = UserRepository.get_latest_registered(db)
        ultima_lista = ListaCompraRepository.get_latest_created(db)

        pending_deletion_requests = AccountRequestRepository.get_pending_deletion_requests(db)

        actividad = []

        if ultimo_usuario:
            actividad.append(
                f"Usuario nuevo creado: {ultimo_usuario.nombre_usuario} ({ultimo_usuario.email})"
            )

        if ultima_lista:
            actividad.append(
                f'Última lista creada: "{ultima_lista.nombre_lista}" '
                f"(usuario {ultima_lista.usuario_id})"
            )

        return AdminDashboardResponse(
            total_usuarios=total_usuarios,
            total_usuarios_activos=total_usuarios_activos,
            total_usuarios_inactivos=total_usuarios_inactivos,
            total_listas=total_listas,
            ultimo_usuario_registrado=ultimo_usuario,
            ultima_lista_creada=ultima_lista,
            actividad_reciente=actividad,
            solicitudes_eliminacion_pendientes=[
                {
                    "id_solicitud": request.id_solicitud,
                    "usuario_id": request.usuario_id,
                    "nombre_usuario": request.usuario.nombre_usuario,
                    "nombre_completo": request.usuario.nombre_completo,
                    "email": request.usuario.email,
                    "fecha_solicitud": request.fecha_solicitud,
                    "motivo": request.motivo,
                }
                for request in pending_deletion_requests
                if request.usuario is not None
            ],
        )

    @staticmethod
    def list_users(
        db: Session,
        page: int,
        size: int,
        search: str | None = None,
    ) -> AdminUsersPageResponse:
        items, total = UserRepository.get_paginated(db, page, size, search)
        total_pages = math.ceil(total / size) if total > 0 else 1

        return AdminUsersPageResponse(
            items=[AdminService._map_user(user) for user in items],
            total=total,
            page=page,
            size=size,
            total_pages=total_pages,
        )

    @staticmethod
    def get_user_by_id(db: Session, user_id: int) -> AdminUserListItem:
        user = UserRepository.get_by_id(db, user_id)

        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Usuario no encontrado",
            )

        return AdminService._map_user(user)

    @staticmethod
    def create_user(db: Session, data: AdminUserCreate) -> AdminUserListItem:
        if UserRepository.get_by_email(db, data.email):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="El email ya está registrado",
            )

        if UserRepository.get_by_username(db, data.nombre_usuario):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="El nombre de usuario ya está en uso",
            )

        role = AdminService._get_role_or_404(db, data.rol_nombre)
        estado = AdminService._validate_estado(data.estado)

        new_user = User(
            nombre_usuario=data.nombre_usuario,
            nombre_completo=data.nombre_completo,
            email=data.email,
            contrasena=hash_password(data.contrasena),
            telefono=data.telefono,
            estado=estado,
            rol_id=role.id_rol,
        )

        created_user = UserRepository.create(db, new_user)
        created_user = UserRepository.get_by_id(db, created_user.id_usuario)

        return AdminService._map_user(created_user)

    @staticmethod
    def update_user(
        db: Session,
        user_id: int,
        data: AdminUserUpdate,
    ) -> AdminUserListItem:
        user = UserRepository.get_by_id(db, user_id)

        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Usuario no encontrado",
            )

        if data.email and data.email != user.email:
            existing_email = UserRepository.get_by_email(db, data.email)

            if existing_email and existing_email.id_usuario != user.id_usuario:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="El email ya está registrado",
                )

        if data.nombre_usuario and data.nombre_usuario != user.nombre_usuario:
            existing_username = UserRepository.get_by_username(db, data.nombre_usuario)

            if existing_username and existing_username.id_usuario != user.id_usuario:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="El nombre de usuario ya está en uso",
                )

        if data.nombre_usuario is not None:
            user.nombre_usuario = data.nombre_usuario

        if data.nombre_completo is not None:
            user.nombre_completo = data.nombre_completo

        if data.email is not None:
            user.email = data.email

        if data.telefono is not None:
            user.telefono = data.telefono

        if data.estado is not None:
            user.estado = AdminService._validate_estado(data.estado)

        if data.rol_nombre is not None:
            role = AdminService._get_role_or_404(db, data.rol_nombre)
            user.rol_id = role.id_rol

        saved_user = UserRepository.save(db, user)
        saved_user = UserRepository.get_by_id(db, saved_user.id_usuario)

        return AdminService._map_user(saved_user)

    @staticmethod
    def activate_user(db: Session, user_id: int) -> AdminUserListItem:
        user = UserRepository.get_by_id(db, user_id)

        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Usuario no encontrado",
            )

        if user.estado == "activo":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="El usuario ya está activo",
            )

        user.estado = "activo"
        saved_user = UserRepository.save(db, user)
        saved_user = UserRepository.get_by_id(db, saved_user.id_usuario)

        return AdminService._map_user(saved_user)

    @staticmethod
    def deactivate_user(db: Session, user_id: int) -> AdminUserListItem:
        user = UserRepository.get_by_id(db, user_id)

        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Usuario no encontrado",
            )

        if user.estado == "inactivo":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="El usuario ya está inactivo",
            )

        user.estado = "inactivo"
        saved_user = UserRepository.save(db, user)
        saved_user = UserRepository.get_by_id(db, saved_user.id_usuario)

        return AdminService._map_user(saved_user)

    @staticmethod
    def delete_user(db: Session, user_id: int) -> dict:
        user = UserRepository.get_by_id(db, user_id)

        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Usuario no encontrado",
            )

        UserRepository.delete(db, user)

        return {"message": "Usuario eliminado correctamente"}

    @staticmethod
    def get_scraping_overview() -> AdminScrapingOverviewResponse:
        AdminService._ensure_state_sources_loaded()

        with AdminService._scraping_lock:
            state = AdminService._scraping_state.copy()
            fuentes = [
                AdminScrapingStoreStatus(
                    supermercado=source["supermercado"],
                    estado=source["estado"],
                    fecha=source["fecha"],
                    precios_detectados=source.get("precios_detectados", 0),
                    productos_actualizados=source.get("productos_actualizados", 0),
                    warning=source.get("warning"),
                    detalle_error=source.get("detalle_error"),
                )
                for source in AdminService._scraping_state["fuentes"]
            ]

        return AdminScrapingOverviewResponse(
            ultima_ejecucion_fecha=state["ultima_ejecucion_fecha"],
            ultima_ejecucion_estado=state["ultima_ejecucion_estado"],
            progreso_general=state["progreso_general"],
            en_curso=state["en_curso"],
            tiempo_restante_segundos=state["tiempo_restante_segundos"],
            detalle_error=state["detalle_error"],
            fuentes=fuentes,
        )

    @staticmethod
    def force_scraping() -> AdminScrapingActionResponse:
        with AdminService._scraping_lock:
            if AdminService._scraping_state["en_curso"]:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Ya hay un scraping en ejecución",
                )

            AdminService._scraping_state["fuentes"] = []

        AdminService._ensure_state_sources_loaded()

        with AdminService._scraping_lock:
            AdminService._scraping_state["en_curso"] = True
            AdminService._scraping_state["ultima_ejecucion_estado"] = "en_proceso"
            AdminService._scraping_state["progreso_general"] = 0
            AdminService._scraping_state["tiempo_restante_segundos"] = max(
                len(AdminService._scraping_state["fuentes"])
                * settings.scraping_timeout_seconds,
                0,
            )
            AdminService._scraping_state["detalle_error"] = None
            AdminService._scraping_state["cancel_requested"] = False

            for source in AdminService._scraping_state["fuentes"]:
                source["estado"] = "en_cola"
                source["fecha"] = "-"
                source["precios_detectados"] = 0
                source["productos_actualizados"] = 0
                source["warning"] = None
                source["detalle_error"] = None

        thread = threading.Thread(target=AdminService._run_scraping_job, daemon=True)
        thread.start()

        return AdminScrapingActionResponse(
            message="Scraping iniciado correctamente",
            status="started",
        )

    @staticmethod
    def cancel_scraping() -> AdminScrapingActionResponse:
        with AdminService._scraping_lock:
            if not AdminService._scraping_state["en_curso"]:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="No hay scraping en ejecución",
                )

            AdminService._scraping_state["en_curso"] = False
            AdminService._scraping_state["ultima_ejecucion_estado"] = "cancelado"
            AdminService._scraping_state["tiempo_restante_segundos"] = 0
            AdminService._scraping_state["cancel_requested"] = True

            for source in AdminService._scraping_state["fuentes"]:
                if source["estado"] in {"en_proceso", "en_cola"}:
                    source["estado"] = "cancelado"
                    source["fecha"] = datetime.now().strftime("%d %b %Y - %H:%M")

        return AdminScrapingActionResponse(
            message=(
                "Scraping marcado como cancelado. "
                "Si ya había peticiones activas terminarán en segundo plano."
            ),
            status="cancelled",
        )