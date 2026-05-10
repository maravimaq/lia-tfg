from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.lista_compartida import ListaCompartida
from app.models.user import User
from app.repositories.lista_compartida_repository import (
    ListaCompartidaRepository
)
from app.repositories.lista_compra_repository import ListaCompraRepository
from app.repositories.user_repository import UserRepository
from app.schemas.lista_compartida import CompartirListaRequest


class ListaCompartidaService:

    @staticmethod
    def compartir_lista(
        db: Session,
        lista_id: int,
        compartir_data: CompartirListaRequest,
        current_user: User
    ) -> ListaCompartida:

        lista = ListaCompraRepository.get_by_id(db, lista_id)

        if not lista:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Lista no encontrada"
            )

        if lista.usuario_id != current_user.id_usuario:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="No puedes compartir esta lista"
            )

        usuario = UserRepository.get_by_email(
            db,
            compartir_data.email_usuario
        )

        if not usuario:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Usuario no encontrado"
            )

        if usuario.id_usuario == current_user.id_usuario:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No puedes compartir contigo mismo"
            )

        ya_compartida = (
            ListaCompartidaRepository.get_by_lista_and_usuario(
                db,
                lista_id,
                usuario.id_usuario
            )
        )

        if ya_compartida:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="La lista ya está compartida con este usuario"
            )

        nueva_comparticion = ListaCompartida(
            lista_id=lista_id,
            usuario_id=usuario.id_usuario
        )

        return ListaCompartidaRepository.create(
            db,
            nueva_comparticion
        )

    @staticmethod
    def get_listas_compartidas(
        db: Session,
        current_user: User
    ) -> list[ListaCompartida]:

        return ListaCompartidaRepository.get_all_by_usuario(
            db,
            current_user.id_usuario
        )

    @staticmethod
    def eliminar_comparticion(
        db: Session,
        lista_id: int,
        usuario_id: int,
        current_user: User
    ):

        lista = ListaCompraRepository.get_by_id(db, lista_id)

        if not lista:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Lista no encontrada"
            )

        if lista.usuario_id != current_user.id_usuario:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="No puedes modificar esta lista"
            )

        comparticion = (
            ListaCompartidaRepository.get_by_lista_and_usuario(
                db,
                lista_id,
                usuario_id
            )
        )

        if not comparticion:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Compartición no encontrada"
            )

        ListaCompartidaRepository.delete(db, comparticion)