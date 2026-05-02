from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.historial_listas import HistorialListasResponse
from app.services.historial_listas_service import HistorialListasService


router = APIRouter(prefix="/historial", tags=["historial"])


@router.post("/listas/{lista_id}/finalizar", response_model=HistorialListasResponse)
def finalizar_lista(
    lista_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    return HistorialListasService.finalizar_lista(db, lista_id, current_user)


@router.get("", response_model=list[HistorialListasResponse])
def get_mi_historial(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    return HistorialListasService.get_mi_historial(db, current_user)


@router.get("/{historial_id}", response_model=HistorialListasResponse)
def get_historial_by_id(
    historial_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    return HistorialListasService.get_historial_by_id(
        db,
        historial_id,
        current_user
    )