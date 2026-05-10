from sqlalchemy.orm import Session

from app.models.historial_producto_lista import HistorialProductoLista


class HistorialProductoListaRepository:

    @staticmethod
    def create(
        db: Session,
        historial_producto: HistorialProductoLista
    ) -> HistorialProductoLista:
        db.add(historial_producto)
        db.commit()
        db.refresh(historial_producto)
        return historial_producto

    @staticmethod
    def create_all(
        db: Session,
        productos: list[HistorialProductoLista]
    ) -> list[HistorialProductoLista]:
        db.add_all(productos)
        db.commit()

        for producto in productos:
            db.refresh(producto)

        return productos

    @staticmethod
    def get_by_historial_id(
        db: Session,
        historial_id: int
    ) -> list[HistorialProductoLista]:
        return db.query(HistorialProductoLista).filter(
            HistorialProductoLista.historial_id == historial_id
        ).all()