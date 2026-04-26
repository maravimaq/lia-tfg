from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.lista_compra import ListaCompra
from app.models.user import User
from app.repositories.lista_compra_repository import ListaCompraRepository
from app.schemas.lista_compra import ListaCompraCreate, ListaCompraUpdate


class ListaCompraService:

    @staticmethod
    def create_lista(
        db: Session,
        lista_data: ListaCompraCreate,
        current_user: User
    ) -> ListaCompra:

        nueva_lista = ListaCompra(
            nombre_lista=lista_data.nombre_lista,
            compartida=lista_data.compartida,
            usuario_id=current_user.id_usuario
        )

        return ListaCompraRepository.create(db, nueva_lista)

    @staticmethod
    def get_mis_listas(
        db: Session,
        current_user: User
    ) -> list[ListaCompra]:

        return ListaCompraRepository.get_all_by_user_id(
            db,
            current_user.id_usuario
        )

    @staticmethod
    def get_lista_by_id(
        db: Session,
        lista_id: int,
        current_user: User
    ) -> ListaCompra:

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

        return lista

    @staticmethod
    def update_lista(
        db: Session,
        lista_id: int,
        lista_data: ListaCompraUpdate,
        current_user: User
    ) -> ListaCompra:

        lista = ListaCompraService.get_lista_by_id(db, lista_id, current_user)

        update_data = lista_data.model_dump(exclude_unset=True)

        for field, value in update_data.items():
            setattr(lista, field, value)

        return ListaCompraRepository.save(db, lista)

    @staticmethod
    def delete_lista(
        db: Session,
        lista_id: int,
        current_user: User
    ) -> None:

        lista = ListaCompraService.get_lista_by_id(db, lista_id, current_user)

        ListaCompraRepository.delete(db, lista)