import math

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.models.user import User
from app.repositories.lista_compra_repository import ListaCompraRepository
from app.repositories.role_repository import RoleRepository
from app.repositories.user_repository import UserRepository
from app.schemas.admin import (
    AdminDashboardResponse,
    AdminUserCreate,
    AdminUserListItem,
    AdminUsersPageResponse,
    AdminUserUpdate,
)


class AdminService:
    @staticmethod
    def _validate_estado(estado: str) -> str:
        estado_normalizado = estado.strip().lower()
        if estado_normalizado not in {"activo", "inactivo"}:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="El estado debe ser 'activo' o 'inactivo'",
            )
        return estado_normalizado

    @staticmethod
    def _get_role_or_404(db: Session, rol_nombre: str):
        role = RoleRepository.get_by_name(db, rol_nombre.strip().lower())
        if not role:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"El rol '{rol_nombre}' no existe",
            )
        return role

    @staticmethod
    def _map_user(user: User) -> AdminUserListItem:
        return AdminUserListItem(
            id_usuario=user.id_usuario,
            nombre_usuario=user.nombre_usuario,
            nombre_completo=user.nombre_completo,
            email=user.email,
            telefono=user.telefono,
            estado=user.estado,
            rol_id=user.rol_id,
            rol_nombre=user.rol.nombre if user.rol else "",
            fecha_registro=user.fecha_registro,
        )

    @staticmethod
    def get_dashboard(db: Session) -> AdminDashboardResponse:
        total_usuarios = UserRepository.count_all(db)
        total_usuarios_activos = UserRepository.count_by_estado(db, "activo")
        total_usuarios_inactivos = UserRepository.count_by_estado(db, "inactivo")
        total_listas = ListaCompraRepository.count_all(db)

        ultimo_usuario = UserRepository.get_latest_registered(db)
        ultima_lista = ListaCompraRepository.get_latest_created(db)

        actividad = []
        if ultimo_usuario:
            actividad.append(
                f"Usuario nuevo creado: {ultimo_usuario.nombre_usuario} ({ultimo_usuario.email})"
            )
        if ultima_lista:
            actividad.append(
                f'Última lista creada: "{ultima_lista.nombre_lista}" (usuario {ultima_lista.usuario_id})'
            )

        return AdminDashboardResponse(
            total_usuarios=total_usuarios,
            total_usuarios_activos=total_usuarios_activos,
            total_usuarios_inactivos=total_usuarios_inactivos,
            total_listas=total_listas,
            ultimo_usuario_registrado=ultimo_usuario,
            ultima_lista_creada=ultima_lista,
            actividad_reciente=actividad,
        )

    @staticmethod
    def list_users(
        db: Session,
        page: int,
        size: int,
        search: str | None = None,
    ) -> AdminUsersPageResponse:
        items, total = UserRepository.get_paginated(db, page, size, search)
        total_pages = math.ceil(total / size) if total > 0 else 1

        return AdminUsersPageResponse(
            items=[AdminService._map_user(user) for user in items],
            total=total,
            page=page,
            size=size,
            total_pages=total_pages,
        )

    @staticmethod
    def get_user_by_id(db: Session, user_id: int) -> AdminUserListItem:
        user = UserRepository.get_by_id(db, user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Usuario no encontrado",
            )
        return AdminService._map_user(user)

    @staticmethod
    def create_user(db: Session, data: AdminUserCreate) -> AdminUserListItem:
        if UserRepository.get_by_email(db, data.email):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="El email ya está registrado",
            )

        if UserRepository.get_by_username(db, data.nombre_usuario):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="El nombre de usuario ya está en uso",
            )

        role = AdminService._get_role_or_404(db, data.rol_nombre)
        estado = AdminService._validate_estado(data.estado)

        new_user = User(
            nombre_usuario=data.nombre_usuario,
            nombre_completo=data.nombre_completo,
            email=data.email,
            contrasena=hash_password(data.contrasena),
            telefono=data.telefono,
            estado=estado,
            rol_id=role.id_rol,
        )

        created_user = UserRepository.create(db, new_user)
        created_user = UserRepository.get_by_id(db, created_user.id_usuario)
        return AdminService._map_user(created_user)

    @staticmethod
    def update_user(
        db: Session,
        user_id: int,
        data: AdminUserUpdate,
    ) -> AdminUserListItem:
        user = UserRepository.get_by_id(db, user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Usuario no encontrado",
            )

        if data.email and data.email != user.email:
            existing_email = UserRepository.get_by_email(db, data.email)
            if existing_email and existing_email.id_usuario != user.id_usuario:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="El email ya está registrado",
                )

        if data.nombre_usuario and data.nombre_usuario != user.nombre_usuario:
            existing_username = UserRepository.get_by_username(db, data.nombre_usuario)
            if existing_username and existing_username.id_usuario != user.id_usuario:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="El nombre de usuario ya está en uso",
                )

        if data.nombre_usuario is not None:
            user.nombre_usuario = data.nombre_usuario

        if data.nombre_completo is not None:
            user.nombre_completo = data.nombre_completo

        if data.email is not None:
            user.email = data.email

        if data.telefono is not None:
            user.telefono = data.telefono

        if data.estado is not None:
            user.estado = AdminService._validate_estado(data.estado)

        if data.rol_nombre is not None:
            role = AdminService._get_role_or_404(db, data.rol_nombre)
            user.rol_id = role.id_rol

        saved_user = UserRepository.save(db, user)
        saved_user = UserRepository.get_by_id(db, saved_user.id_usuario)
        return AdminService._map_user(saved_user)

    @staticmethod
    def activate_user(db: Session, user_id: int) -> AdminUserListItem:
        user = UserRepository.get_by_id(db, user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Usuario no encontrado",
            )

        if user.estado == "activo":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="El usuario ya está activo",
            )

        user.estado = "activo"
        saved_user = UserRepository.save(db, user)
        saved_user = UserRepository.get_by_id(db, saved_user.id_usuario)
        return AdminService._map_user(saved_user)

    @staticmethod
    def deactivate_user(db: Session, user_id: int) -> AdminUserListItem:
        user = UserRepository.get_by_id(db, user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Usuario no encontrado",
            )

        if user.estado == "inactivo":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="El usuario ya está inactivo",
            )

        user.estado = "inactivo"
        saved_user = UserRepository.save(db, user)
        saved_user = UserRepository.get_by_id(db, saved_user.id_usuario)
        return AdminService._map_user(saved_user)

    @staticmethod
    def delete_user(db: Session, user_id: int) -> dict:
        user = UserRepository.get_by_id(db, user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Usuario no encontrado",
            )

        UserRepository.delete(db, user)
        return {"message": "Usuario eliminado correctamente"}