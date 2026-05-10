from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.lista_compra import (
    ListaCompraCreate,
    ListaCompraResponse,
    ListaCompraDetalleResponse,
    ListaCompraUpdate
)
from app.services.lista_compra_service import ListaCompraService


router = APIRouter(prefix="/listas", tags=["listas"])


@router.post("", response_model=ListaCompraResponse)
def create_lista(
    lista_data: ListaCompraCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    return ListaCompraService.create_lista(
        db,
        lista_data,
        current_user
    )


@router.get("", response_model=list[ListaCompraResponse])
def get_mis_listas(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    return ListaCompraService.get_mis_listas(
        db,
        current_user
    )


@router.get("/{lista_id}", response_model=ListaCompraDetalleResponse)
def get_lista_by_id(
    lista_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    return ListaCompraService.get_lista_detalle(
        db,
        lista_id,
        current_user
    )


@router.put("/{lista_id}", response_model=ListaCompraResponse)
def update_lista(
    lista_id: int,
    lista_data: ListaCompraUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    return ListaCompraService.update_lista(
        db,
        lista_id,
        lista_data,
        current_user
    )


@router.delete("/{lista_id}")
def delete_lista(
    lista_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    ListaCompraService.delete_lista(
        db,
        lista_id,
        current_user
    )

    return {"message": "Lista eliminada correctamente"}