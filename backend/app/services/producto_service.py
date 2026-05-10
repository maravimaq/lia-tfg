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
            unidad_medida=producto_data.unidad_medida
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