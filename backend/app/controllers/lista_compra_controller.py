from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.lista_compra import ListaCompraCreate, ListaCompraResponse
from app.services.lista_compra_service import ListaCompraService

router = APIRouter(prefix="/listas", tags=["listas"])


@router.post("", response_model=ListaCompraResponse)
def create_lista(
    lista_data: ListaCompraCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    return ListaCompraService.create_lista(db, lista_data, current_user)


@router.get("", response_model=list[ListaCompraResponse])
def get_mis_listas(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    return ListaCompraService.get_mis_listas(db, current_user)


@router.get("/{lista_id}", response_model=ListaCompraResponse)
def get_lista(
    lista_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    return ListaCompraService.get_lista_by_id(db, lista_id, current_user)