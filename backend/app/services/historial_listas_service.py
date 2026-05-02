from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.historial_listas import HistorialListas
from app.models.user import User
from app.repositories.historial_listas_repository import HistorialListasRepository
from app.repositories.lista_compra_repository import ListaCompraRepository
from app.repositories.producto_lista_repository import ProductoListaRepository


class HistorialListasService:

    @staticmethod
    def finalizar_lista(
        db: Session,
        lista_id: int,
        current_user: User
    ) -> HistorialListas:

        lista = ListaCompraRepository.get_by_id(db, lista_id)

        if not lista:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Lista no encontrada"
            )

        if lista.usuario_id != current_user.id_usuario:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="No tienes permiso para finalizar esta lista"
            )

        productos = ProductoListaRepository.get_by_lista_id(db, lista_id)

        historial = HistorialListas(
            lista_id=lista.id_lista,
            usuario_id=current_user.id_usuario,
            estado="finalizada",
            num_productos=sum(producto.cantidad for producto in productos),
            total_gastado=lista.total_estimado
        )

        return HistorialListasRepository.create(db, historial)

    @staticmethod
    def get_mi_historial(
        db: Session,
        current_user: User
    ) -> list[HistorialListas]:

        return HistorialListasRepository.get_all_by_user_id(
            db,
            current_user.id_usuario
        )

    @staticmethod
    def get_historial_by_id(
        db: Session,
        historial_id: int,
        current_user: User
    ) -> HistorialListas:

        historial = HistorialListasRepository.get_by_id(db, historial_id)

        if not historial:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Historial no encontrado"
            )

        if historial.usuario_id != current_user.id_usuario:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="No tienes permiso para acceder a este historial"
            )

        return historial