from fastapi import APIRouter, Depends

from app.core.dependencies import require_role
from app.models.user import User

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/only-admin")
def only_admin(
    current_user: User = Depends(require_role("administrador"))
):
    return {
        "message": "Acceso concedido al administrador",
        "user": current_user.nombre_usuario
    }