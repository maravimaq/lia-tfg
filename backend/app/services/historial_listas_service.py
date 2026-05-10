from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.historial_listas import HistorialListas
from app.models.historial_producto_lista import HistorialProductoLista
from app.models.lista_compra import ListaCompra
from app.models.producto_lista import ProductoLista
from app.models.user import User
from app.repositories.historial_listas_repository import HistorialListasRepository
from app.repositories.historial_producto_lista_repository import HistorialProductoListaRepository
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

        productos_lista = ProductoListaRepository.get_by_lista_id(db, lista_id)

        if not productos_lista:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No puedes finalizar una lista vacía"
            )

        historial = HistorialListas(
            lista_id=lista.id_lista,
            usuario_id=current_user.id_usuario,
            estado="finalizada",
            num_productos=sum(producto.cantidad for producto in productos_lista),
            total_gastado=lista.total_estimado
        )

        historial_creado = HistorialListasRepository.create(db, historial)

        productos_historial = []

        for producto_lista in productos_lista:
            producto_catalogo = producto_lista.producto

            productos_historial.append(
                HistorialProductoLista(
                    historial_id=historial_creado.id_historial,
                    producto_id=producto_lista.producto_id,
                    nombre_producto=producto_catalogo.nombre,
                    marca=producto_catalogo.marca,
                    categoria=producto_catalogo.categoria,
                    supermercado=producto_catalogo.supermercado,
                    unidad_medida=producto_catalogo.unidad_medida,
                    precio_unitario=producto_catalogo.precio_unitario,
                    cantidad=producto_lista.cantidad,
                    precio_estimado=producto_lista.precio_estimado
                )
            )

        HistorialProductoListaRepository.create_all(db, productos_historial)

        return historial_creado

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

    @staticmethod
    def get_detalle_historial(
        db: Session,
        historial_id: int,
        current_user: User
    ) -> dict:

        historial = HistorialListasService.get_historial_by_id(
            db,
            historial_id,
            current_user
        )

        productos = HistorialProductoListaRepository.get_by_historial_id(
            db,
            historial_id
        )

        return {
            "id_historial": historial.id_historial,
            "fecha": historial.fecha,
            "estado": historial.estado,
            "num_productos": historial.num_productos,
            "total_gastado": historial.total_gastado,
            "lista_id": historial.lista_id,
            "usuario_id": historial.usuario_id,
            "productos": productos
        }

    @staticmethod
    def repetir_lista(
        db: Session,
        historial_id: int,
        current_user: User
    ) -> ListaCompra:

        historial = HistorialListasService.get_historial_by_id(
            db,
            historial_id,
            current_user
        )

        productos_historial = HistorialProductoListaRepository.get_by_historial_id(
            db,
            historial_id
        )

        if not productos_historial:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No se puede repetir una lista sin productos"
            )

        nueva_lista = ListaCompra(
            nombre_lista=f"Copia de lista {historial.id_historial}",
            compartida=False,
            total_estimado=historial.total_gastado,
            usuario_id=current_user.id_usuario
        )

        nueva_lista = ListaCompraRepository.create(db, nueva_lista)

        nuevos_productos_lista = []

        for producto_historial in productos_historial:
            nuevos_productos_lista.append(
                ProductoLista(
                    lista_id=nueva_lista.id_lista,
                    producto_id=producto_historial.producto_id,
                    cantidad=producto_historial.cantidad,
                    precio_estimado=producto_historial.precio_estimado
                )
            )

        for producto_lista in nuevos_productos_lista:
            ProductoListaRepository.create(db, producto_lista)

        return nueva_lista