from __future__ import annotations

import calendar
import re
import unicodedata
from collections import Counter, defaultdict
from datetime import datetime
from decimal import Decimal, InvalidOperation
from typing import Any

from sqlalchemy.orm import Session

from app.models.historial_listas import HistorialListas
from app.models.historial_producto_lista import HistorialProductoLista
from app.models.producto_lista import ProductoLista
from app.models.user import User
from app.repositories.analytics_repository import AnalyticsRepository


class AnalyticsService:
    WEEKDAYS_ES = [
        "Lunes",
        "Martes",
        "Miércoles",
        "Jueves",
        "Viernes",
        "Sábado",
        "Domingo",
    ]

    STOPWORDS = {
        "de",
        "del",
        "la",
        "las",
        "el",
        "los",
        "y",
        "con",
        "sin",
        "para",
        "por",
        "en",
        "un",
        "una",
        "unos",
        "unas",
        "mercadona",
        "carrefour",
        "aldi",
        "alcampo",
        "dia",
        "hacendado",
    }

    PRODUCT_FAMILIES = {
        "pollo": {"pollo", "pechuga", "pechugas", "contramuslo", "contramuslos"},
        "carne": {"carne", "ternera", "cerdo", "vacuno", "lomo", "hamburguesa", "hamburguesas"},
        "pescado": {"pescado", "merluza", "salmon", "salmón", "atun", "atún", "bacalao"},
        "leche": {"leche"},
        "huevo": {"huevo", "huevos"},
        "yogur": {"yogur", "yogurt", "yogures"},
        "arroz": {"arroz"},
        "pasta": {"pasta", "macarrones", "espaguetis", "spaghetti"},
        "pan": {"pan", "molde", "baguette", "barra"},
        "fruta": {"manzana", "manzanas", "platano", "plátano", "platanos", "plátanos", "naranja", "naranjas"},
        "verdura": {"verdura", "verduras", "lechuga", "tomate", "tomates", "cebolla", "zanahoria"},
        "papel": {"papel", "servilleta", "servilletas"},
        "detergente": {"detergente", "suavizante", "lavavajillas"},
    }

    @staticmethod
    def get_monthly_expenses(
        db: Session,
        current_user: User,
        year: int,
        month: int,
    ) -> dict[str, Any]:
        start, end = AnalyticsService._month_bounds(year, month)
        previous_start, previous_end = AnalyticsService._previous_month_bounds(year, month)

        histories = AnalyticsRepository.get_histories_by_user_between(
            db,
            current_user.id_usuario,
            start,
            end,
        )
        previous_histories = AnalyticsRepository.get_histories_by_user_between(
            db,
            current_user.id_usuario,
            previous_start,
            previous_end,
        )

        products_by_history = AnalyticsService._products_grouped_by_history(db, histories)

        total_month = sum(AnalyticsService._to_decimal(item.total_gastado) for item in histories)
        previous_total = sum(AnalyticsService._to_decimal(item.total_gastado) for item in previous_histories)
        days_in_month = calendar.monthrange(year, month)[1]
        variation = None
        if previous_total > 0:
            variation = round(float(((total_month - previous_total) / previous_total) * Decimal("100")), 2)

        weekly_totals: dict[int, Decimal] = defaultdict(lambda: Decimal("0"))
        for item in histories:
            week = ((item.fecha.day - 1) // 7) + 1
            weekly_totals[week] += AnalyticsService._to_decimal(item.total_gastado)

        max_week = ((days_in_month - 1) // 7) + 1
        weekly_items = [
            {
                "semana": week,
                "etiqueta": f"Semana {week}",
                "total": AnalyticsService._round_money(weekly_totals.get(week, Decimal("0"))),
            }
            for week in range(1, max_week + 1)
        ]

        lists = []
        for item in histories:
            products = products_by_history.get(item.id_historial, [])
            lists.append(
                {
                    "id_historial": item.id_historial,
                    "nombre_lista": item.nombre_lista,
                    "fecha": item.fecha.isoformat(),
                    "supermercado_principal": AnalyticsService._main_supermarket(products),
                    "total_gastado": AnalyticsService._round_money(item.total_gastado),
                    "num_productos": int(item.num_productos or 0),
                }
            )

        return {
            "year": year,
            "month": month,
            "resumen": {
                "total_mensual": AnalyticsService._round_money(total_month),
                "variacion_vs_mes_pasado": variation,
                "media_diaria": AnalyticsService._round_money(total_month / Decimal(days_in_month)),
                "numero_compras": len(histories),
            },
            "gasto_semana": weekly_items,
            "listas_mes": lists,
        }

    @staticmethod
    def get_categories_analytics(
        db: Session,
        current_user: User,
        year: int,
        month: int,
    ) -> dict[str, Any]:
        start, end = AnalyticsService._month_bounds(year, month)
        histories = AnalyticsRepository.get_histories_by_user_between(
            db,
            current_user.id_usuario,
            start,
            end,
        )
        history_ids = [history.id_historial for history in histories]
        products = AnalyticsRepository.get_history_products_by_historial_ids(db, history_ids)

        category_totals: dict[str, Decimal] = defaultdict(lambda: Decimal("0"))
        category_product_units: dict[str, Counter[str]] = defaultdict(Counter)
        category_product_kinds: dict[str, int] = defaultdict(int)

        for product in products:
            category = AnalyticsService._clean_category(product.categoria)
            subtotal = AnalyticsService._to_decimal(product.precio_estimado)
            quantity = int(product.cantidad or 0)
            name = product.nombre_producto or "Producto sin nombre"

            category_totals[category] += subtotal
            category_product_units[category][name] += quantity
            category_product_kinds[category] += 1

        total = sum(category_totals.values(), Decimal("0"))
        categories = []
        for category, amount in sorted(category_totals.items(), key=lambda item: item[1], reverse=True):
            percentage = round(float((amount / total) * Decimal("100")), 2) if total > 0 else 0.0
            categories.append(
                {
                    "categoria": category,
                    "porcentaje_total": percentage,
                    "gasto": AnalyticsService._round_money(amount),
                    "num_productos": category_product_kinds[category],
                }
            )

        products_by_category = []
        for category, counter in sorted(category_product_units.items()):
            top_products = [
                f"{name} ({quantity})"
                for name, quantity in counter.most_common(6)
            ]
            products_by_category.append(
                {
                    "categoria": category,
                    "productos": top_products,
                }
            )

        return {
            "year": year,
            "month": month,
            "total_mensual": AnalyticsService._round_money(total),
            "categorias": categories,
            "productos_por_categoria": products_by_category,
        }

    @staticmethod
    def get_purchase_habits(
        db: Session,
        current_user: User,
    ) -> dict[str, Any]:
        histories = AnalyticsRepository.get_all_histories_by_user(
            db,
            current_user.id_usuario,
        )
        products_by_history = AnalyticsService._products_grouped_by_history(db, histories)

        if not histories:
            return {
                "frecuencia_general": "Todavía no hay compras finalizadas suficientes para calcular hábitos.",
                "dias_medios_entre_compras": None,
                "dia_habitual_compra": None,
                "gasto_por_dia_semana": [
                    {"dia_semana": day, "total": 0.0}
                    for day in AnalyticsService.WEEKDAYS_ES
                ],
                "rango_horario_frecuente": None,
                "promedio_productos_por_compra": 0.0,
                "listas_repetidas": [],
                "supermercados_favoritos": [],
            }

        average_days = AnalyticsService._average_days_between_purchases(histories)
        weekday_counter: Counter[int] = Counter(history.fecha.weekday() for history in histories)
        habitual_weekday = weekday_counter.most_common(1)[0][0] if weekday_counter else None

        weekday_spending: dict[int, Decimal] = defaultdict(lambda: Decimal("0"))
        for history in histories:
            weekday_spending[history.fecha.weekday()] += AnalyticsService._to_decimal(history.total_gastado)

        hour_ranges = Counter(
            AnalyticsService._hour_range(history.fecha.hour)
            for history in histories
        )

        repeated_lists = Counter(
            AnalyticsService._normalize_list_name(history.nombre_lista)
            for history in histories
            if AnalyticsService._normalize_list_name(history.nombre_lista)
        )

        supermarket_visits: Counter[str] = Counter()
        for history in histories:
            supermarkets_in_history = {
                product.supermercado
                for product in products_by_history.get(history.id_historial, [])
                if product.supermercado
            }
            for supermarket in supermarkets_in_history:
                supermarket_visits[supermarket] += 1

        avg_products = round(
            sum(int(history.num_productos or 0) for history in histories) / len(histories),
            2,
        )

        return {
            "frecuencia_general": AnalyticsService._format_purchase_frequency(average_days),
            "dias_medios_entre_compras": average_days,
            "dia_habitual_compra": AnalyticsService.WEEKDAYS_ES[habitual_weekday] if habitual_weekday is not None else None,
            "gasto_por_dia_semana": [
                {
                    "dia_semana": AnalyticsService.WEEKDAYS_ES[index],
                    "total": AnalyticsService._round_money(weekday_spending.get(index, Decimal("0"))),
                }
                for index in range(7)
            ],
            "rango_horario_frecuente": hour_ranges.most_common(1)[0][0] if hour_ranges else None,
            "promedio_productos_por_compra": avg_products,
            "listas_repetidas": [
                {"nombre_lista": name, "veces": count}
                for name, count in repeated_lists.most_common(5)
                if count > 1
            ],
            "supermercados_favoritos": [
                {"supermercado": supermarket, "visitas": count}
                for supermarket, count in supermarket_visits.most_common(5)
            ],
        }

    @staticmethod
    def build_chatbot_analytics_context(
        db: Session,
        current_user: User,
        productos_lista: list[ProductoLista],
    ) -> dict[str, Any]:
        histories = AnalyticsRepository.get_all_histories_by_user(
            db,
            current_user.id_usuario,
        )
        all_history_products = AnalyticsRepository.get_all_history_products_by_user(
            db,
            current_user.id_usuario,
        )

        now = datetime.utcnow()
        days_in_month = calendar.monthrange(now.year, now.month)[1]
        month_progress = round(now.day / days_in_month, 4)
        current_month_key = (now.year, now.month)
        average_days = AnalyticsService._average_days_between_purchases(histories)

        insights: list[dict[str, Any]] = []

        for producto_lista in productos_lista:
            producto = getattr(producto_lista, "producto", None)
            if producto is None:
                continue

            family = AnalyticsService._detect_product_family(producto.nombre)
            relevant_history = AnalyticsService._filter_relevant_history_products(
                product_name=producto.nombre,
                category=producto.categoria,
                family=family,
                history_products=all_history_products,
            )

            month_totals: dict[tuple[int, int], int] = defaultdict(int)
            for history_product in relevant_history:
                history = getattr(history_product, "historial", None)
                if history is None or history.fecha is None:
                    continue
                month_totals[(history.fecha.year, history.fecha.month)] += int(history_product.cantidad or 0)

            current_month_total = float(month_totals.get(current_month_key, 0))
            historical_months = [
                total
                for key, total in month_totals.items()
                if key != current_month_key and total > 0
            ]
            avg_monthly_quantity = (
                round(sum(historical_months) / len(historical_months), 2)
                if historical_months
                else None
            )
            avg_per_purchase = (
                round(sum(int(item.cantidad or 0) for item in relevant_history) / len(relevant_history), 2)
                if relevant_history
                else None
            )

            expected_remaining = None
            recommendation = "No hay historial suficiente para comparar esta cantidad con tus compras anteriores."
            current_quantity = int(producto_lista.cantidad or 0)

            if avg_monthly_quantity is not None:
                expected_remaining = round(max(avg_monthly_quantity - current_month_total, 0) * (1 - month_progress), 2)
                if current_quantity > expected_remaining * 1.25 and expected_remaining > 0:
                    recommendation = (
                        "La cantidad actual parece algo alta para lo que queda de mes según tu historial. "
                        "Compraría menos salvo que quieras hacer stock."
                    )
                elif current_quantity < expected_remaining * 0.6:
                    recommendation = (
                        "La cantidad actual parece prudente, incluso algo baja si esta lista cubre lo que queda de mes."
                    )
                else:
                    recommendation = "La cantidad actual encaja razonablemente con tu patrón histórico."

            insights.append(
                {
                    "producto_actual": producto.nombre,
                    "categoria": producto.categoria,
                    "supermercado": producto.supermercado,
                    "cantidad_actual": current_quantity,
                    "unidad_medida": producto.unidad_medida,
                    "familia_detectada": family,
                    "compras_historicas": len(relevant_history),
                    "cantidad_media_por_compra": avg_per_purchase,
                    "cantidad_media_mensual": avg_monthly_quantity,
                    "cantidad_total_mes_actual": current_month_total,
                    "cantidad_esperada_restante_mes": expected_remaining,
                    "porcentaje_mes_transcurrido": round(month_progress * 100, 2),
                    "recomendacion_orientativa": recommendation,
                }
            )

        return {
            "cadencia_compra": {
                "dias_medios_entre_compras": average_days,
                "frecuencia_general": AnalyticsService._format_purchase_frequency(average_days),
                "fecha_referencia": now.isoformat(),
                "porcentaje_mes_transcurrido": round(month_progress * 100, 2),
            },
            "productos_relevantes": insights,
            "nota": (
                "Este bloque usa historial de listas finalizadas para comparar cantidades actuales con hábitos reales. "
                "Las cantidades son unidades registradas en la app, no gramos exactos salvo que el producto lo indique en su nombre o unidad."
            ),
        }

    @staticmethod
    def _products_grouped_by_history(
        db: Session,
        histories: list[HistorialListas],
    ) -> dict[int, list[HistorialProductoLista]]:
        history_ids = [history.id_historial for history in histories]
        products = AnalyticsRepository.get_history_products_by_historial_ids(db, history_ids)
        grouped: dict[int, list[HistorialProductoLista]] = defaultdict(list)
        for product in products:
            grouped[product.historial_id].append(product)
        return grouped

    @staticmethod
    def _month_bounds(year: int, month: int) -> tuple[datetime, datetime]:
        start = datetime(year, month, 1)
        if month == 12:
            end = datetime(year + 1, 1, 1)
        else:
            end = datetime(year, month + 1, 1)
        return start, end

    @staticmethod
    def _previous_month_bounds(year: int, month: int) -> tuple[datetime, datetime]:
        if month == 1:
            return AnalyticsService._month_bounds(year - 1, 12)
        return AnalyticsService._month_bounds(year, month - 1)

    @staticmethod
    def _to_decimal(value: Any) -> Decimal:
        try:
            return Decimal(str(value or 0))
        except (InvalidOperation, ValueError, TypeError):
            return Decimal("0")

    @staticmethod
    def _round_money(value: Any) -> float:
        return round(float(AnalyticsService._to_decimal(value)), 2)

    @staticmethod
    def _main_supermarket(products: list[HistorialProductoLista]) -> str | None:
        if not products:
            return None

        totals: dict[str, Decimal] = defaultdict(lambda: Decimal("0"))
        for product in products:
            supermarket = product.supermercado or "Sin supermercado"
            totals[supermarket] += AnalyticsService._to_decimal(product.precio_estimado)

        return max(totals.items(), key=lambda item: item[1])[0]

    @staticmethod
    def _clean_category(category: str | None) -> str:
        clean = (category or "Otros").strip()
        return clean if clean else "Otros"

    @staticmethod
    def _average_days_between_purchases(histories: list[HistorialListas]) -> float | None:
        if len(histories) < 2:
            return None

        sorted_histories = sorted(histories, key=lambda item: item.fecha)
        differences = []
        for previous, current in zip(sorted_histories, sorted_histories[1:]):
            diff = (current.fecha - previous.fecha).total_seconds() / 86400
            if diff >= 0:
                differences.append(diff)

        if not differences:
            return None

        return round(sum(differences) / len(differences), 2)

    @staticmethod
    def _format_purchase_frequency(average_days: float | None) -> str:
        if average_days is None:
            return "Todavía no hay compras suficientes para calcular una frecuencia estable."

        rounded = round(average_days, 1)
        if rounded <= 1.2:
            return "Realizas una compra prácticamente diaria."
        if rounded <= 7:
            return f"Realizas una compra cada {rounded:g} días aproximadamente."
        if rounded <= 16:
            return f"Realizas una compra cada {rounded:g} días aproximadamente; tu patrón parece quincenal."
        return f"Realizas una compra cada {rounded:g} días aproximadamente; tu patrón parece mensual o poco frecuente."

    @staticmethod
    def _hour_range(hour: int) -> str:
        start = (hour // 2) * 2
        end = start + 2
        return f"{start:02d}:00 – {end:02d}:00"

    @staticmethod
    def _normalize_list_name(name: str | None) -> str:
        if not name:
            return ""
        clean = re.sub(r"^copia de\s+", "", name.strip(), flags=re.IGNORECASE)
        clean = re.sub(r"\s+", " ", clean)
        return clean

    @staticmethod
    def _normalize(text: str | None) -> str:
        if not text:
            return ""
        without_accents = "".join(
            char
            for char in unicodedata.normalize("NFD", text.lower())
            if unicodedata.category(char) != "Mn"
        )
        clean = re.sub(r"[^a-z0-9ñ\s]", " ", without_accents)
        return re.sub(r"\s+", " ", clean).strip()

    @staticmethod
    def _keywords(text: str | None) -> set[str]:
        normalized = AnalyticsService._normalize(text)
        return {
            token
            for token in normalized.split()
            if len(token) >= 4 and token not in AnalyticsService.STOPWORDS
        }

    @staticmethod
    def _detect_product_family(text: str | None) -> str | None:
        normalized = AnalyticsService._normalize(text)
        tokens = set(normalized.split())
        for family, aliases in AnalyticsService.PRODUCT_FAMILIES.items():
            normalized_aliases = {AnalyticsService._normalize(alias) for alias in aliases}
            if tokens.intersection(normalized_aliases):
                return family
        return None

    @staticmethod
    def _filter_relevant_history_products(
        *,
        product_name: str | None,
        category: str | None,
        family: str | None,
        history_products: list[HistorialProductoLista],
    ) -> list[HistorialProductoLista]:
        product_tokens = AnalyticsService._keywords(product_name)
        normalized_category = AnalyticsService._normalize(category)
        relevant = []

        for history_product in history_products:
            history_family = AnalyticsService._detect_product_family(history_product.nombre_producto)
            history_category = AnalyticsService._normalize(history_product.categoria)
            history_tokens = AnalyticsService._keywords(history_product.nombre_producto)

            if family and history_family == family:
                relevant.append(history_product)
                continue

            if normalized_category and history_category and normalized_category == history_category:
                if product_tokens and history_tokens and product_tokens.intersection(history_tokens):
                    relevant.append(history_product)
                    continue

            if product_tokens and history_tokens and len(product_tokens.intersection(history_tokens)) >= 1:
                relevant.append(history_product)

        return relevant
