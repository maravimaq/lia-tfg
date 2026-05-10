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