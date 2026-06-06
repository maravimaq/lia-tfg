from __future__ import annotations

from datetime import datetime

from sqlalchemy.orm import Session

from app.models.historial_listas import HistorialListas
from app.models.historial_producto_lista import HistorialProductoLista


class AnalyticsRepository:
    @staticmethod
    def get_histories_by_user_between(
        db: Session,
        user_id: int,
        start: datetime,
        end: datetime,
    ) -> list[HistorialListas]:
        return (
            db.query(HistorialListas)
            .filter(
                HistorialListas.usuario_id == user_id,
                HistorialListas.fecha >= start,
                HistorialListas.fecha < end,
            )
            .order_by(HistorialListas.fecha.asc())
            .all()
        )

    @staticmethod
    def get_all_histories_by_user(
        db: Session,
        user_id: int,
    ) -> list[HistorialListas]:
        return (
            db.query(HistorialListas)
            .filter(HistorialListas.usuario_id == user_id)
            .order_by(HistorialListas.fecha.asc())
            .all()
        )

    @staticmethod
    def get_history_products_by_historial_ids(
        db: Session,
        historial_ids: list[int],
    ) -> list[HistorialProductoLista]:
        if not historial_ids:
            return []

        return (
            db.query(HistorialProductoLista)
            .filter(HistorialProductoLista.historial_id.in_(historial_ids))
            .all()
        )

    @staticmethod
    def get_all_history_products_by_user(
        db: Session,
        user_id: int,
    ) -> list[HistorialProductoLista]:
        return (
            db.query(HistorialProductoLista)
            .join(
                HistorialListas,
                HistorialProductoLista.historial_id == HistorialListas.id_historial,
            )
            .filter(HistorialListas.usuario_id == user_id)
            .all()
        )
