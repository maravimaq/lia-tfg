from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.producto_lista import ProductoListaCreate, ProductoListaResponse
from app.services.producto_lista_service import ProductoListaService

router = APIRouter(prefix="/productos-lista", tags=["productos-lista"])

@router.post("", response_model=ProductoListaResponse)
def create_producto(
    producto_data: ProductoListaCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    return ProductoListaService.create_producto(db, producto_data, current_user)


@router.get("/lista/{lista_id}", response_model=list[ProductoListaResponse])
def get_productos_by_lista(
    lista_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    return ProductoListaService.get_productos_by_lista(db, lista_id, current_user)


@router.get("/{producto_id}", response_model=ProductoListaResponse)
def get_producto_by_id(
    producto_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    return ProductoListaService.get_producto_by_id(db, producto_id, current_user)