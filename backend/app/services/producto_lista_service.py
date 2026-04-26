from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.producto_lista import ProductoLista
from app.models.user import User
from app.repositories.lista_compra_repository import ListaCompraRepository
from app.repositories.producto_lista_repository import ProductoListaRepository
from app.schemas.producto_lista import ProductoListaCreate, ProductoListaUpdate


class ProductoListaService:

    @staticmethod
    def _recalcular_total_lista(db: Session, lista_id: int) -> None:
        lista = ListaCompraRepository.get_by_id(db, lista_id)

        if not lista:
            return

        productos = ProductoListaRepository.get_by_lista_id(db, lista_id)
        lista.total_estimado = sum(producto.precio_estimado * producto.cantidad for producto in productos)

        ListaCompraRepository.save(db, lista)

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

        producto_creado = ProductoListaRepository.create(db, nuevo_producto)

        ProductoListaService._recalcular_total_lista(db, producto_data.lista_id)

        return producto_creado

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

    @staticmethod
    def update_producto(
        db: Session,
        producto_id: int,
        producto_data: ProductoListaUpdate,
        current_user: User
    ) -> ProductoLista:
        producto = ProductoListaService.get_producto_by_id(
            db,
            producto_id,
            current_user
        )

        update_data = producto_data.model_dump(exclude_unset=True)

        for field, value in update_data.items():
            setattr(producto, field, value)

        producto_actualizado = ProductoListaRepository.save(db, producto)

        ProductoListaService._recalcular_total_lista(db, producto.lista_id)

        return producto_actualizado

    @staticmethod
    def delete_producto(
        db: Session,
        producto_id: int,
        current_user: User
    ) -> None:
        producto = ProductoListaService.get_producto_by_id(
            db,
            producto_id,
            current_user
        )

        lista_id = producto.lista_id

        ProductoListaRepository.delete(db, producto)

        ProductoListaService._recalcular_total_lista(db, lista_id)