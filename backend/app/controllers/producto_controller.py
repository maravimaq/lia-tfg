from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.producto import (
    ProductoCreate,
    ProductoResponse,
    ProductoUpdate
)
from app.services.producto_service import ProductoService


router = APIRouter(prefix="/productos", tags=["productos"])


@router.post("", response_model=ProductoResponse)
def create_producto(
    producto_data: ProductoCreate,
    db: Session = Depends(get_db)
):
    return ProductoService.create_producto(db, producto_data)


@router.get("", response_model=list[ProductoResponse])
def get_all_productos(
    db: Session = Depends(get_db)
):
    return ProductoService.get_all_productos(db)


@router.get("/{producto_id}", response_model=ProductoResponse)
def get_producto_by_id(
    producto_id: int,
    db: Session = Depends(get_db)
):
    return ProductoService.get_producto_by_id(db, producto_id)


@router.put("/{producto_id}", response_model=ProductoResponse)
def update_producto(
    producto_id: int,
    producto_data: ProductoUpdate,
    db: Session = Depends(get_db)
):
    return ProductoService.update_producto(db, producto_id, producto_data)


@router.delete("/{producto_id}")
def delete_producto(
    producto_id: int,
    db: Session = Depends(get_db)
):
    return ProductoService.delete_producto(db, producto_id)