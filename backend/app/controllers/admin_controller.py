from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.dependencies import require_role
from app.db.session import get_db
from app.models.user import User
from app.schemas.admin import (
    AdminDashboardResponse,
    AdminScrapingActionResponse,
    AdminScrapingOverviewResponse,
    AdminUserCreate,
    AdminUserListItem,
    AdminUsersPageResponse,
    AdminUserUpdate,
)
from app.services.admin_service import AdminService

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/only-admin")
def only_admin(
    current_user: User = Depends(require_role("administrador"))
):
    return {
        "message": "Acceso concedido al administrador",
        "user": current_user.nombre_usuario
    }


@router.get("/dashboard", response_model=AdminDashboardResponse)
def get_dashboard(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("administrador"))
):
    return AdminService.get_dashboard(db)


@router.get("/users", response_model=AdminUsersPageResponse)
def list_users(
    page: int = Query(1, ge=1),
    size: int = Query(10, ge=1, le=100),
    search: str | None = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("administrador"))
):
    return AdminService.list_users(db, page, size, search)


@router.get("/users/{user_id}", response_model=AdminUserListItem)
def get_user_by_id(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("administrador"))
):
    return AdminService.get_user_by_id(db, user_id)


@router.post("/users", response_model=AdminUserListItem)
def create_user(
    user_data: AdminUserCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("administrador"))
):
    return AdminService.create_user(db, user_data)


@router.put("/users/{user_id}", response_model=AdminUserListItem)
def update_user(
    user_id: int,
    user_data: AdminUserUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("administrador"))
):
    return AdminService.update_user(db, user_id, user_data)


@router.patch("/users/{user_id}/activate", response_model=AdminUserListItem)
def activate_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("administrador"))
):
    return AdminService.activate_user(db, user_id)


@router.patch("/users/{user_id}/deactivate", response_model=AdminUserListItem)
def deactivate_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("administrador"))
):
    return AdminService.deactivate_user(db, user_id)


@router.delete("/users/{user_id}")
def delete_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("administrador"))
):
    return AdminService.delete_user(db, user_id)

@router.get("/scraping/overview", response_model=AdminScrapingOverviewResponse)
def get_scraping_overview(
    current_user: User = Depends(require_role("administrador"))
):
    return AdminService.get_scraping_overview()


@router.post("/scraping/force", response_model=AdminScrapingActionResponse)
def force_scraping(
    current_user: User = Depends(require_role("administrador"))
):
    return AdminService.force_scraping()


@router.post("/scraping/cancel", response_model=AdminScrapingActionResponse)
def cancel_scraping(
    current_user: User = Depends(require_role("administrador"))
):
    return AdminService.cancel_scraping()