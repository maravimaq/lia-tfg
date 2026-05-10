import json
import math
import re
import threading
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
from app.models.producto_lista import ProductoLista
from app.models.user import User
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
    def _build_request_headers(url: str, *, json_preferred: bool = False) -> dict[str, str]:
        parsed = url_parse.urlparse(url)
        origin = f"{parsed.scheme}://{parsed.netloc}"
        return {
            "User-Agent": settings.scraping_user_agent,
            "Accept": "application/json,text/plain,*/*" if json_preferred else "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "es-ES,es;q=0.9,en;q=0.8",
            "Cache-Control": "no-cache",
            "Pragma": "no-cache",
            "Referer": origin,
            "Origin": origin,
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
        }

    @staticmethod
    def _fetch_url(url: str, *, timeout_seconds: int | None = None) -> httpx.Response:
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
                    headers=AdminService._build_request_headers(url, json_preferred=attempt["json_preferred"]),
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
        return [
            {
                "supermercado": "Mercadona",
                "urls": ["https://tienda.mercadona.es"],
                "crawl_internal_links": True,
                "link_include_regex": r"/categories/\d+",
                "selector": None,
                "price_regex": AdminService.DEFAULT_PRICE_REGEX,
            },
            {
                "supermercado": "Carrefour",
                "urls": [
                    "https://www.carrefour.es/supermercado/frescos/cat20002/c",
                    "https://www.carrefour.es/supermercado/la-despensa/cat20001/c",
                    "https://www.carrefour.es/supermercado/bebidas/cat20003/c",
                    "https://www.carrefour.es/supermercado/drogueria-y-limpieza/cat20005/c",
                    "https://www.carrefour.es/supermercado/cuidado-personal-e-higiene/cat20004/c",
                    "https://www.carrefour.es/supermercado/congelados/cat21449123/c",
                    "https://www.carrefour.es/supermercado/bebe/cat20006/c",
                    "https://www.carrefour.es/supermercado/mascotas/cat20007/c",
                    "https://www.carrefour.es/supermercado/parafarmacia/cat20008/c",
                ],
                "crawl_internal_links": False,
                "link_include_regex": None,
                "selector": None,
                "price_regex": AdminService.DEFAULT_PRICE_REGEX,
            },
            {
                "supermercado": "DIA",
                "urls": ["https://www.dia.es"],
                "crawl_internal_links": True,
                "link_include_regex": r"/.*/c/L\d+",
                "selector": None,
                "price_regex": AdminService.DEFAULT_PRICE_REGEX,
            },
            {
                "supermercado": "Lidl",
                "urls": [
                    "https://www.lidl.es/l/folletos",
                    "https://www.lidl.es/c/alimentos/s10068374",
                    "https://www.lidl.es/c/ofertas/s10067753",
                ],
                "crawl_internal_links": True,
                "link_include_regex": r"/(l/folletos/.+|c/.+/s\d+)",
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
                        "price_regex": item.get("price_regex") or AdminService.DEFAULT_PRICE_REGEX,
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
                    "price_regex": source.get("price_regex") or AdminService.DEFAULT_PRICE_REGEX,
                    "precios_detectados": 0,
                    "productos_actualizados": 0,
                    "warning": None,
                    "detalle_error": None,
                }
                for source in AdminService._get_configured_sources()
            ]

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

        def parse_price(raw: str) -> float | None:
            cleaned = raw.strip().replace("€", "").replace(" ", "")
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

        for text in texts:
            for match in pattern.findall(text):
                raw = match if isinstance(match, str) else match[0]
                parsed = parse_price(raw)
                if parsed is not None:
                    prices.append(parsed)

        # Fallback común para tiendas que inyectan precios en JSON dentro de scripts.
        json_price_pattern = re.compile(
            r'"(?:price|salePrice|unitPrice|amount|value)"\s*:\s*"?(\d+(?:[.,]\d{1,2})?)"?',
            re.IGNORECASE,
        )
        for text in texts:
            for raw in json_price_pattern.findall(text):
                parsed = parse_price(raw)
                if parsed is not None:
                    prices.append(parsed)

        # Fallback adicional para SPAs: intenta decodificar JSON embebido completo
        # y localizar cualquier campo relacionado con precio en estructuras profundas.
        def collect_prices_from_obj(obj):
            if isinstance(obj, dict):
                for key, value in obj.items():
                    key_lower = str(key).lower()
                    if any(token in key_lower for token in ["price", "precio", "amount", "importe", "value"]):
                        if isinstance(value, (int, float, str)):
                            parsed = parse_price(str(value))
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

            candidates: list[str] = []
            trimmed = raw_script.strip()
            if trimmed.startswith("{") or trimmed.startswith("["):
                candidates.append(trimmed)

            for marker in ("=", "window.__", "INITIAL_STATE", "__NEXT_DATA__"):
                marker_pos = raw_script.find(marker)
                if marker_pos < 0:
                    continue
                start_obj = raw_script.find("{", marker_pos)
                start_arr = raw_script.find("[", marker_pos)
                starts = [pos for pos in (start_obj, start_arr) if pos >= 0]
                if starts:
                    candidates.append(raw_script[min(starts):].strip())

            for candidate in candidates:
                cleaned = candidate
                if cleaned.endswith(";"):
                    cleaned = cleaned[:-1]
                try:
                    parsed_json = json.loads(cleaned)
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
                normalized = raw.replace(".", "").replace(",", ".")
                try:
                    prices.append(float(normalized))
                except ValueError:
                    continue

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
            response = AdminService._fetch_url("https://tienda.mercadona.es/api/categories/")
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
        urls.extend([f"https://tienda.mercadona.es/api/categories/{cat_id}" for cat_id in sorted(ids)])
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
    def _update_products_price_for_store(db: Session, store: str, average_price: float) -> int:
        products = db.query(ProductoLista).filter(
            ProductoLista.supermercado.isnot(None)
        ).all()

        updated = 0
        target = store.strip().lower()
        for product in products:
            if (product.supermercado or "").strip().lower() == target:
                product.precio_estimado = round(average_price, 2)
                updated += 1

        if updated > 0:
            db.commit()

        return updated

    @staticmethod
    def _run_scraping_job() -> None:
        db = SessionLocal()
        start = datetime.now()

        try:
            with AdminService._scraping_lock:
                sources = AdminService._scraping_state["fuentes"]

            total = len(sources)
            errors: list[str] = []

            for index, source in enumerate(sources, start=1):
                with AdminService._scraping_lock:
                    if AdminService._scraping_state["cancel_requested"]:
                        break

                with AdminService._scraping_lock:
                    source["estado"] = "en_proceso"
                    source["fecha"] = datetime.now().strftime("%d %b %Y - %H:%M")
                    source["warning"] = None
                    source["detalle_error"] = None
                    source["precios_detectados"] = 0
                    source["productos_actualizados"] = 0

                try:
                    all_prices: list[float] = []
                    url_errors: list[str] = []
                    successful_responses = 0
                    candidate_urls = AdminService._expand_source_urls(source)

                    for url in candidate_urls:
                        try:
                            response = AdminService._fetch_url(url)
                            successful_responses += 1

                            is_pdf = (
                                url.lower().endswith(".pdf")
                                or "application/pdf"
                                in response.headers.get("content-type", "").lower()
                            )
                            if is_pdf:
                                prices = AdminService._extract_prices_from_pdf(
                                    response.content,
                                    source.get("price_regex") or AdminService.DEFAULT_PRICE_REGEX,
                                )
                            else:
                                prices = AdminService._extract_prices(
                                    response.text,
                                    source.get("selector"),
                                    source.get("price_regex") or AdminService.DEFAULT_PRICE_REGEX,
                                )

                            all_prices.extend(prices)
                        except Exception as url_exc:
                            url_errors.append(f"{url} -> {str(url_exc)}")

                    if not all_prices:
                        only_403_errors = bool(url_errors) and all(
                            "403" in error_message for error_message in url_errors
                        )
                        if only_403_errors:
                            with AdminService._scraping_lock:
                                source["estado"] = "error"
                                source["precios_detectados"] = 0
                                source["fecha"] = datetime.now().strftime("%d %b %Y - %H:%M")
                                source["productos_actualizados"] = 0
                                source["detalle_error"] = " | ".join(url_errors)
                                source["warning"] = (
                                    "Acceso bloqueado por la tienda (HTTP 403). "
                                    "Requiere integración oficial/API o scraper con navegador."
                                )
                            errors.append(
                                f"{source['supermercado']}: bloqueo HTTP 403 en todas las URLs"
                            )
                            continue
                        if successful_responses > 0:
                            # Hay acceso al sitio pero no hubo precios parseables: se marca error explícito.
                            with AdminService._scraping_lock:
                                source["estado"] = "error"
                                source["precios_detectados"] = 0
                                source["fecha"] = datetime.now().strftime("%d %b %Y - %H:%M")
                                source["productos_actualizados"] = 0
                                source["detalle_error"] = " | ".join(url_errors) if url_errors else None
                                source["warning"] = "No se detectaron precios parseables en las páginas consultadas"
                            errors.append(
                                f"{source['supermercado']}: acceso OK pero sin precios parseables"
                            )
                            continue
                        raise ValueError(
                            "No se detectaron precios en ninguna URL. "
                            + (" | ".join(url_errors) if url_errors else "")
                        )

                    average_price = sum(all_prices[:25]) / min(len(all_prices), 25)
                    updated_count = AdminService._update_products_price_for_store(
                        db,
                        source["supermercado"],
                        average_price,
                    )

                    with AdminService._scraping_lock:
                        source["estado"] = "ok"
                        source["precios_detectados"] = len(all_prices)
                        source["fecha"] = datetime.now().strftime("%d %b %Y - %H:%M")
                        source["productos_actualizados"] = updated_count
                        source["detalle_error"] = None
                except Exception as exc:
                    with AdminService._scraping_lock:
                        source["estado"] = "error"
                        source["fecha"] = datetime.now().strftime("%d %b %Y - %H:%M")
                        source["precios_detectados"] = 0
                        source["detalle_error"] = str(exc)
                    errors.append(f"{source['supermercado']}: {str(exc)}")

                elapsed = (datetime.now() - start).total_seconds()
                avg_seconds = elapsed / index if index else 0
                remaining = max(int(avg_seconds * (total - index)), 0)
                progress = int((index / total) * 100) if total > 0 else 100

                with AdminService._scraping_lock:
                    AdminService._scraping_state["progreso_general"] = progress
                    AdminService._scraping_state["tiempo_restante_segundos"] = remaining

            with AdminService._scraping_lock:
                AdminService._scraping_state["en_curso"] = False
                AdminService._scraping_state["ultima_ejecucion_fecha"] = datetime.now().strftime(
                    "%d %b %Y - %H:%M"
                )
                if AdminService._scraping_state["cancel_requested"]:
                    AdminService._scraping_state["ultima_ejecucion_estado"] = "cancelado"
                else:
                    AdminService._scraping_state["ultima_ejecucion_estado"] = (
                        "ok" if not errors else "error"
                    )
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
                f'Última lista creada: "{ultima_lista.nombre_lista}" (usuario {ultima_lista.usuario_id})'
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

            # Recargar fuentes en cada ejecución para aplicar cambios de configuración
            # y mejoras de defaults sin reiniciar el servicio.
            AdminService._scraping_state["fuentes"] = []
        AdminService._ensure_state_sources_loaded()

        with AdminService._scraping_lock:

            AdminService._scraping_state["en_curso"] = True
            AdminService._scraping_state["ultima_ejecucion_estado"] = "en_proceso"
            AdminService._scraping_state["progreso_general"] = 0
            AdminService._scraping_state["tiempo_restante_segundos"] = max(
                len(AdminService._scraping_state["fuentes"]) * settings.scraping_timeout_seconds,
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
            message="Scraping marcado como cancelado. Si ya había peticiones activas terminarán en segundo plano.",
            status="cancelled",
        )