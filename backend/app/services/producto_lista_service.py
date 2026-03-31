from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.producto_lista import ProductoLista
from app.models.user import User
from app.repositories.lista_compra_repository import ListaCompraRepository
from app.repositories.producto_lista_repository import ProductoListaRepository
from app.schemas.producto_lista import ProductoListaCreate


class ProductoListaService:

    @staticmethod
    def create_producto(
        db: Session,
        producto_data: ProductoListaCreate,
        current_user: User
    ) -> ProductoLista:
        lista = ListaCompraRepository.get_by_id(db, producto_data.lista_id)

        if not lista:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Lista no encontrada"
            )

        if lista.usuario_id != current_user.id_usuario:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="No tienes permiso para modificar esta lista"
            )

        nuevo_producto = ProductoLista(
            nombre_producto=producto_data.nombre_producto,
            cantidad=producto_data.cantidad,
            unidad_medida=producto_data.unidad_medida,
            supermercado=producto_data.supermercado,
            precio_estimado=producto_data.precio_estimado,
            lista_id=producto_data.lista_id
        )

        return ProductoListaRepository.create(db, nuevo_producto)

    @staticmethod
    def get_productos_by_lista(
        db: Session,
        lista_id: int,
        current_user: User
    ) -> list[ProductoLista]:
        lista = ListaCompraRepository.get_by_id(db, lista_id)

        if not lista:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Lista no encontrada"
            )

        if lista.usuario_id != current_user.id_usuario:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="No tienes permiso para acceder a esta lista"
            )

        return ProductoListaRepository.get_by_lista_id(db, lista_id)

    @staticmethod
    def get_producto_by_id(
        db: Session,
        producto_id: int,
        current_user: User
    ) -> ProductoLista:
        producto = ProductoListaRepository.get_by_id(db, producto_id)

        if not producto:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Producto no encontrado"
            )

        lista = ListaCompraRepository.get_by_id(db, producto.lista_id)

        if not lista:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Lista asociada no encontrada"
            )

        if lista.usuario_id != current_user.id_usuario:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="No tienes permiso para acceder a este producto"
            )

        return producto