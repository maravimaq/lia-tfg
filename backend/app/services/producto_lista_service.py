from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.producto_lista import ProductoLista
from app.models.user import User
from app.repositories.lista_compra_repository import ListaCompraRepository
from app.repositories.producto_lista_repository import ProductoListaRepository
from app.repositories.producto_repository import ProductoRepository
from app.schemas.producto_lista import ProductoListaCreate, ProductoListaUpdate


class ProductoListaService:

    @staticmethod
    def _recalcular_total_lista(db: Session, lista_id: int) -> None:
        lista = ListaCompraRepository.get_by_id(db, lista_id)

        if not lista:
            return

        productos_lista = ProductoListaRepository.get_by_lista_id(db, lista_id)
        lista.total_estimado = sum(
            producto_lista.precio_estimado
            for producto_lista in productos_lista
        )

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

        producto_catalogo = ProductoRepository.get_by_id(
            db,
            producto_data.producto_id
        )

        if not producto_catalogo:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Producto de catálogo no encontrado"
            )

        precio_estimado = producto_catalogo.precio_unitario * producto_data.cantidad

        nuevo_producto_lista = ProductoLista(
            lista_id=producto_data.lista_id,
            producto_id=producto_data.producto_id,
            cantidad=producto_data.cantidad,
            precio_estimado=precio_estimado
        )

        producto_creado = ProductoListaRepository.create(db, nuevo_producto_lista)

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
        producto_lista_id: int,
        current_user: User
    ) -> ProductoLista:
        producto_lista = ProductoListaRepository.get_by_id(db, producto_lista_id)

        if not producto_lista:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Producto de lista no encontrado"
            )

        lista = ListaCompraRepository.get_by_id(db, producto_lista.lista_id)

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

        return producto_lista

    @staticmethod
    def update_producto(
        db: Session,
        producto_lista_id: int,
        producto_data: ProductoListaUpdate,
        current_user: User
    ) -> ProductoLista:
        producto_lista = ProductoListaService.get_producto_by_id(
            db,
            producto_lista_id,
            current_user
        )

        if producto_data.cantidad is not None:
            producto_catalogo = ProductoRepository.get_by_id(
                db,
                producto_lista.producto_id
            )

            if not producto_catalogo:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Producto de catálogo no encontrado"
                )

            producto_lista.cantidad = producto_data.cantidad
            producto_lista.precio_estimado = (
                producto_catalogo.precio_unitario * producto_data.cantidad
            )

        producto_actualizado = ProductoListaRepository.save(db, producto_lista)

        ProductoListaService._recalcular_total_lista(db, producto_lista.lista_id)

        return producto_actualizado

    @staticmethod
    def delete_producto(
        db: Session,
        producto_lista_id: int,
        current_user: User
    ) -> None:
        producto_lista = ProductoListaService.get_producto_by_id(
            db,
            producto_lista_id,
            current_user
        )

        lista_id = producto_lista.lista_id

        ProductoListaRepository.delete(db, producto_lista)

        ProductoListaService._recalcular_total_lista(db, lista_id)