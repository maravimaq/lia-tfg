from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.lista_compra import ListaCompra
from app.models.user import User
from app.repositories.historial_listas_repository import HistorialListasRepository
from app.repositories.lista_compartida_repository import ListaCompartidaRepository
from app.repositories.lista_compra_repository import ListaCompraRepository
from app.repositories.producto_lista_repository import ProductoListaRepository
from app.schemas.lista_compra import (
    ListaCompraCreate,
    ListaCompraUpdate,
)


class ListaCompraService:

    @staticmethod
    def _get_comparticion_usuario(
        db: Session,
        lista: ListaCompra,
        current_user: User,
    ):
        if lista.usuario_id == current_user.id_usuario:
            return None

        return ListaCompartidaRepository.get_by_lista_and_usuario(
            db,
            lista.id_lista,
            current_user.id_usuario,
        )

    @staticmethod
    def _usuario_tiene_acceso(
        db: Session,
        lista: ListaCompra,
        current_user: User,
    ) -> bool:
        if lista.usuario_id == current_user.id_usuario:
            return True

        comparticion = ListaCompraService._get_comparticion_usuario(
            db,
            lista,
            current_user,
        )

        return comparticion is not None

    @staticmethod
    def _usuario_es_propietario(
        lista: ListaCompra,
        current_user: User,
    ) -> bool:
        return lista.usuario_id == current_user.id_usuario

    @staticmethod
    def _lista_esta_finalizada(db: Session, lista_id: int) -> bool:
        return HistorialListasRepository.get_by_lista_id(db, lista_id) is not None

    @staticmethod
    def _validar_lista_no_finalizada(db: Session, lista_id: int) -> None:
        if ListaCompraService._lista_esta_finalizada(db, lista_id):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Esta lista ya está finalizada. Consulta el historial.",
            )

    @staticmethod
    def _inyectar_tipo_compartido(
        db: Session,
        lista: ListaCompra,
        current_user: User,
    ) -> ListaCompra:
        comparticion = ListaCompraService._get_comparticion_usuario(
            db,
            lista,
            current_user,
        )

        lista.tipo_compartido = (
            comparticion.tipo_compartido if comparticion else None
        )

        return lista

    @staticmethod
    def create_lista(
        db: Session,
        lista_data: ListaCompraCreate,
        current_user: User,
    ) -> ListaCompra:

        nueva_lista = ListaCompra(
            nombre_lista=lista_data.nombre_lista,
            compartida=lista_data.compartida,
            usuario_id=current_user.id_usuario,
        )

        return ListaCompraRepository.create(db, nueva_lista)

    @staticmethod
    def get_mis_listas(
        db: Session,
        current_user: User,
    ) -> list[ListaCompra]:

        return ListaCompraRepository.get_all_by_user_id(
            db,
            current_user.id_usuario,
        )

    @staticmethod
    def get_lista_by_id(
        db: Session,
        lista_id: int,
        current_user: User,
    ) -> ListaCompra:

        lista = ListaCompraRepository.get_by_id(db, lista_id)

        if not lista:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Lista no encontrada",
            )

        if not ListaCompraService._usuario_tiene_acceso(db, lista, current_user):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="No tienes permiso para acceder a esta lista",
            )

        ListaCompraService._validar_lista_no_finalizada(db, lista_id)

        return ListaCompraService._inyectar_tipo_compartido(
            db,
            lista,
            current_user,
        )

    @staticmethod
    def get_lista_detalle(
        db: Session,
        lista_id: int,
        current_user: User,
    ):

        lista = ListaCompraService.get_lista_by_id(
            db,
            lista_id,
            current_user,
        )

        productos = ProductoListaRepository.get_by_lista_id(
            db,
            lista_id,
        )

        lista.productos = productos

        return lista

    @staticmethod
    def update_lista(
        db: Session,
        lista_id: int,
        lista_data: ListaCompraUpdate,
        current_user: User,
    ) -> ListaCompra:

        lista = ListaCompraRepository.get_by_id(db, lista_id)

        if not lista:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Lista no encontrada",
            )

        if not ListaCompraService._usuario_es_propietario(lista, current_user):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Solo el propietario puede editar la lista",
            )

        ListaCompraService._validar_lista_no_finalizada(db, lista_id)

        update_data = lista_data.model_dump(exclude_unset=True)

        for key, value in update_data.items():
            setattr(lista, key, value)

        return ListaCompraRepository.save(db, lista)

    @staticmethod
    def delete_lista(
        db: Session,
        lista_id: int,
        current_user: User,
    ):

        lista = ListaCompraRepository.get_by_id(db, lista_id)

        if not lista:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Lista no encontrada",
            )

        if not ListaCompraService._usuario_es_propietario(lista, current_user):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Solo el propietario puede eliminar la lista",
            )

        ListaCompraService._validar_lista_no_finalizada(db, lista_id)

        productos = ProductoListaRepository.get_by_lista_id(db, lista_id)

        for producto in productos:
            ProductoListaRepository.delete(db, producto)

        ListaCompraRepository.delete(db, lista)