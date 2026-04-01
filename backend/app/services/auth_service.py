from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.core.external_auth import verify_apple_id_token, verify_google_id_token
from app.models.sesion_autenticacion import SesionAutenticacion
from app.models.user import User
from app.repositories.role_repository import RoleRepository
from app.repositories.session_repository import SessionRepository
from app.repositories.user_repository import UserRepository
from app.schemas.auth import ExternalUserPayload
from app.schemas.user import UserCreate
from app.core.security import (
    hash_password,
    verify_password,
    create_access_token,
    create_password_reset_token,
    is_password_reset_token,
    decode_token,
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
    def _create_external_user_if_needed(
        db: Session,
        external_user: ExternalUserPayload,
        proveedor: str,
    ) -> User:
        existing_user = UserRepository.get_by_email(db, external_user.email)
        if existing_user:
            return existing_user

        user_role = RoleRepository.get_by_name(db, "usuario")
        if not user_role:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="El rol por defecto 'usuario' no existe"
            )

        base_username = external_user.nombre_usuario or external_user.email.split("@")[0]
        username = base_username
        suffix = 1

        while UserRepository.get_by_username(db, username):
            username = f"{base_username}{suffix}"
            suffix += 1

        new_user = User(
            nombre_usuario=username,
            nombre_completo=external_user.nombre_completo or username,
            email=external_user.email,
            contrasena=hash_password("oauth_placeholder_password"),
            telefono=None,
            estado="activo",
            rol_id=user_role.id_rol,
            proveedor_auth=proveedor,
        )

        return UserRepository.create(db, new_user)

    @staticmethod
    def login_with_google(db: Session, id_token: str) -> str:
        external_user = verify_google_id_token(id_token)
        user = AuthService._create_external_user_if_needed(db, external_user, "google")

        if user.estado != "activo":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Usuario inactivo"
            )

        access_token = create_access_token(data={"sub": user.email})

        nueva_sesion = SesionAutenticacion(
            proveedor="google",
            token=access_token,
            usuario_id=user.id_usuario,
        )
        SessionRepository.create(db, nueva_sesion)

        return access_token

    @staticmethod
    def login_with_apple(db: Session, id_token: str) -> str:
        external_user = verify_apple_id_token(id_token)
        user = AuthService._create_external_user_if_needed(db, external_user, "apple")

        if user.estado != "activo":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Usuario inactivo"
            )

        access_token = create_access_token(data={"sub": user.email})

        nueva_sesion = SesionAutenticacion(
            proveedor="apple",
            token=access_token,
            usuario_id=user.id_usuario,
        )
        SessionRepository.create(db, nueva_sesion)

        return access_token

    @staticmethod
    def logout(db: Session, token: str) -> dict:
        sesion = SessionRepository.get_active_by_token(db, token)

        if sesion is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No existe una sesión activa para este token"
            )

        SessionRepository.close_session(db, sesion)
        return {"message": "Sesión cerrada correctamente"}

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

        reset_token = create_password_reset_token(user.email)

        return {
            "message": "Token de recuperación generado",
            "reset_token": reset_token
        }

    @staticmethod
    def reset_password(db: Session, token: str, new_password: str) -> dict:
        if not is_password_reset_token(token):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Token de recuperación inválido"
            )

        payload = decode_token(token)
        email = payload.get("sub")

        if email is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Token de recuperación inválido"
            )

        user = UserRepository.get_by_email(db, email)
        if user is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Usuario no encontrado"
            )

        if user.proveedor_auth != "local":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Esta cuenta usa autenticación externa con {user.proveedor_auth}"
            )

        user.contrasena = hash_password(new_password)
        UserRepository.save(db, user)

        SessionRepository.revoke_all_user_sessions(db, user.id_usuario)

        return {
            "message": "Contraseña restablecida correctamente. Inicia sesión de nuevo."
        }