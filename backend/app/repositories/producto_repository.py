from sqlalchemy import case, func, or_
from sqlalchemy.orm import Session

from app.models.producto import Producto


class ProductoRepository:

    @staticmethod
    def create(db: Session, producto: Producto) -> Producto:
        db.add(producto)
        db.commit()
        db.refresh(producto)
        return producto

    @staticmethod
    def get_by_id(db: Session, producto_id: int) -> Producto | None:
        return db.query(Producto).filter(
            Producto.id_producto == producto_id
        ).first()

    @staticmethod
    def get_all(db: Session) -> list[Producto]:
        return db.query(Producto).all()

    @staticmethod
    def update(db: Session, producto: Producto) -> Producto:
        db.commit()
        db.refresh(producto)
        return producto

    @staticmethod
    def delete(db: Session, producto: Producto) -> None:
        db.delete(producto)
        db.commit()
        
    @staticmethod
    def search(
        db: Session,
        nombre: str | None = None,
        categoria: str | None = None,
        supermercado: str | None = None,
        marca: str | None = None,
        orden_precio: str | None = None
    ) -> list[Producto]:

        query = db.query(Producto)

        if nombre:
            query = query.filter(Producto.nombre.ilike(f"%{nombre}%"))

        if categoria:
            query = query.filter(Producto.categoria.ilike(f"%{categoria}%"))

        if supermercado:
            query = query.filter(Producto.supermercado.ilike(f"%{supermercado}%"))

        if marca:
            query = query.filter(Producto.marca.ilike(f"%{marca}%"))

        if orden_precio == "asc":
            query = query.order_by(Producto.precio_unitario.asc())
        elif orden_precio == "desc":
            query = query.order_by(Producto.precio_unitario.desc())

        return query.all()

    @staticmethod
    def search_by_text(
        db: Session,
        text: str,
        limit: int = 8,
        orden_precio: str | None = "asc",
    ) -> list[Producto]:
        clean_text = text.strip()

        if not clean_text:
            return []

        lowered_text = clean_text.lower()
        name_lower = func.lower(Producto.nombre)
        brand_lower = func.lower(Producto.marca)
        category_lower = func.lower(Producto.categoria)
        supermarket_lower = func.lower(Producto.supermercado)

        query = db.query(Producto).filter(
            or_(
                Producto.nombre.ilike(f"%{clean_text}%"),
                Producto.marca.ilike(f"%{clean_text}%"),
                Producto.categoria.ilike(f"%{clean_text}%"),
                Producto.supermercado.ilike(f"%{clean_text}%"),
            )
        )

        # Ordenamos por relevancia antes que por precio.
        # Ejemplo: para "leche" deben salir antes "Leche semidesnatada"
        # que productos secundarios como "Café con leche".
        relevance = case(
            (name_lower == lowered_text, 0),
            (name_lower.like(f"{lowered_text}%"), 1),
            (name_lower.like(f"% {lowered_text}%"), 2),
            (category_lower.like(f"%{lowered_text}%"), 3),
            (brand_lower.like(f"%{lowered_text}%"), 4),
            (supermarket_lower.like(f"%{lowered_text}%"), 5),
            else_=6,
        )

        if orden_precio == "desc":
            query = query.order_by(relevance.asc(), Producto.precio_unitario.desc())
        else:
            query = query.order_by(relevance.asc(), Producto.precio_unitario.asc())

        return query.limit(limit).all()
