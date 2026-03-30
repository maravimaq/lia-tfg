from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.user import User
from app.repositories.user_repository import UserRepository
from app.schemas.user import UserCreate
from app.core.security import hash_password, verify_password, create_access_token


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

        hashed_password = hash_password(user_data.contrasena)

        new_user = User(
            nombre_usuario=user_data.nombre_usuario,
            nombre_completo=user_data.nombre_completo,
            email=user_data.email,
            contrasena=hashed_password,
            telefono=user_data.telefono,
            estado="activo",
            rol_id=1
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

        return access_token