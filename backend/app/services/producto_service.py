from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.producto import Producto
from app.repositories.producto_repository import ProductoRepository
from app.schemas.producto import ProductoCreate, ProductoUpdate


class ProductoService:

    @staticmethod
    def create_producto(
        db: Session,
        producto_data: ProductoCreate
    ) -> Producto:

        nuevo_producto = Producto(
            nombre=producto_data.nombre,
            marca=producto_data.marca,
            categoria=producto_data.categoria,
            supermercado=producto_data.supermercado,
            precio_unitario=producto_data.precio_unitario,
            unidad_medida=producto_data.unidad_medida,
            imagen_url=producto_data.imagen_url,
        )

        return ProductoRepository.create(db, nuevo_producto)

    @staticmethod
    def get_all_productos(db: Session) -> list[Producto]:
        return ProductoRepository.get_all(db)

    @staticmethod
    def get_producto_by_id(
        db: Session,
        producto_id: int
    ) -> Producto:

        producto = ProductoRepository.get_by_id(db, producto_id)

        if not producto:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Producto no encontrado"
            )

        return producto

    @staticmethod
    def update_producto(
        db: Session,
        producto_id: int,
        producto_data: ProductoUpdate
    ) -> Producto:

        producto = ProductoRepository.get_by_id(db, producto_id)

        if not producto:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Producto no encontrado"
            )

        # actualizar solo campos enviados
        for field, value in producto_data.model_dump(exclude_unset=True).items():
            setattr(producto, field, value)

        return ProductoRepository.update(db, producto)

    @staticmethod
    def delete_producto(
        db: Session,
        producto_id: int
    ) -> dict:

        producto = ProductoRepository.get_by_id(db, producto_id)

        if not producto:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Producto no encontrado"
            )

        ProductoRepository.delete(db, producto)

        return {"message": "Producto eliminado correctamente"}
    
    @staticmethod
    def search_productos(
        db: Session,
        nombre: str | None = None,
        categoria: str | None = None,
        supermercado: str | None = None,
        marca: str | None = None,
        orden_precio: str | None = None
    ) -> list[Producto]:

        if orden_precio and orden_precio not in ["asc", "desc"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="orden_precio debe ser 'asc' o 'desc'"
            )

        return ProductoRepository.search(
            db,
            nombre=nombre,
            categoria=categoria,
            supermercado=supermercado,
            marca=marca,
            orden_precio=orden_precio
        )

    @staticmethod
    def comparar_productos(
        db: Session,
        nombre: str
    ) -> list[Producto]:

        if not nombre or not nombre.strip():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="El nombre del producto es obligatorio"
            )

        return ProductoRepository.search(
            db,
            nombre=nombre,
            orden_precio="asc"
        )