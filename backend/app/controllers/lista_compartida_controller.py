from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.lista_compartida import (
    CompartirListaRequest,
    ListaCompartidaResponse,
)
from app.services.lista_compartida_service import ListaCompartidaService


router = APIRouter(prefix="/listas", tags=["listas compartidas"])


@router.post("/{lista_id}/compartir", response_model=ListaCompartidaResponse)
def compartir_lista(
    lista_id: int,
    compartir_data: CompartirListaRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    return ListaCompartidaService.compartir_lista(
        db,
        lista_id,
        compartir_data,
        current_user
    )


@router.get("/compartidas", response_model=list[ListaCompartidaResponse])
def get_listas_compartidas(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    return ListaCompartidaService.get_listas_compartidas(db, current_user)


@router.delete("/{lista_id}/compartir/{usuario_id}")
def eliminar_comparticion(
    lista_id: int,
    usuario_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    ListaCompartidaService.eliminar_comparticion(
        db,
        lista_id,
        usuario_id,
        current_user
    )

    return {"message": "Acceso eliminado correctamente"}