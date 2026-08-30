import secrets
import string

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.sesion_autenticacion import SesionAutenticacion
from app.models.user import User
from app.repositories.role_repository import RoleRepository
from app.repositories.session_repository import SessionRepository
from app.repositories.user_repository import UserRepository
from app.schemas.user import UserCreate
from app.services.email_service import EmailService
from app.core.security import (
    hash_password,
    verify_password,
    create_access_token,
)


class AuthService:
    @staticmethod
    def register(db: Session, user_data: UserCreate) -> User:
        if UserRepository.get_by_email(db, user_data.email):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="El email ya está registrado"
            )

        if UserRepository.get_by_username(db, user_data.nombre_usuario):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="El nombre de usuario ya está en uso"
            )

        user_role = RoleRepository.get_by_name(db, "usuario")

        if not user_role:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="El rol por defecto 'usuario' no existe"
            )

        hashed_password = hash_password(user_data.contrasena)

        new_user = User(
            nombre_usuario=user_data.nombre_usuario,
            nombre_completo=user_data.nombre_completo,
            email=user_data.email,
            contrasena=hashed_password,
            telefono=user_data.telefono,
            estado="activo",
            rol_id=user_role.id_rol,
            proveedor_auth="local",
        )

        return UserRepository.create(db, new_user)

    @staticmethod
    def login(db: Session, email: str, password: str) -> str:
        user = UserRepository.get_by_email(db, email)

        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Credenciales incorrectas"
            )

        if user.proveedor_auth != "local":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Esta cuenta usa autenticación externa con {user.proveedor_auth}"
            )

        if not verify_password(password, user.contrasena):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Credenciales incorrectas"
            )

        if user.estado != "activo":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Usuario inactivo"
            )

        access_token = create_access_token(
            data={"sub": user.email}
        )

        nueva_sesion = SesionAutenticacion(
            proveedor="local",
            token=access_token,
            usuario_id=user.id_usuario,
        )
        SessionRepository.create(db, nueva_sesion)

        return access_token


    @staticmethod
    def logout(db: Session, token: str) -> dict:
        sesion = SessionRepository.get_active_by_token(db, token)

        if sesion is None:
            return {"message": "La sesión ya estaba cerrada o revocada"}

        SessionRepository.close_session(db, sesion)
        return {"message": "Sesión cerrada correctamente"}

    @staticmethod
    def _generate_temporary_password(length: int = 12) -> str:
        alphabet = string.ascii_letters + string.digits
        return "".join(secrets.choice(alphabet) for _ in range(length))

    @staticmethod
    def forgot_password(db: Session, email: str) -> dict:
        user = UserRepository.get_by_email(db, email)

        if user is None:
            return {
                "message": "Si el correo existe en el sistema, se ha generado un enlace de recuperación"
            }

        if user.proveedor_auth != "local":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Esta cuenta usa autenticación externa con {user.proveedor_auth} y no admite recuperación por contraseña local"
            )

        temporary_password = AuthService._generate_temporary_password()

        try:
            EmailService.send_temporary_password_email(
                user.email,
                temporary_password,
            )
        except Exception as exc:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=f"No se pudo enviar el correo de recuperación: {str(exc)}",
            ) from exc

        # Solo cambiamos las credenciales si el correo se ha enviado correctamente.
        user.contrasena = hash_password(temporary_password)
        UserRepository.save(db, user)
        SessionRepository.revoke_all_user_sessions(db, user.id_usuario)

        return {
            "message": "Si el correo existe en el sistema, te hemos enviado una contraseña temporal."
        }

    @staticmethod
    def reset_password(db: Session, token: str, new_password: str) -> dict:
        raise HTTPException(
            status_code=status.HTTP_410_GONE,
            detail=(
                "Este flujo ya no usa token de recuperación. "
                "Solicita una nueva contraseña temporal desde '¿Olvidaste tu contraseña?'."
            ),
        )