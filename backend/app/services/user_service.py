from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.core.security import hash_password, verify_password
from app.models.configuracion_bot_externo import ConfiguracionBotExterno
from app.models.preferencias_usuario import PreferenciasUsuario
from app.models.solicitud_baja_usuario import SolicitudBajaUsuario
from app.models.user import User
from app.repositories.account_request_repository import AccountRequestRepository
from app.repositories.bot_config_repository import BotConfigRepository
from app.repositories.preferences_repository import PreferencesRepository
from app.repositories.session_repository import SessionRepository
from app.repositories.user_repository import UserRepository
from app.schemas.account_request import AccountActionRequestCreate
from app.schemas.bot_config import BotConfigUpdate
from app.schemas.preferences import PreferenciasUpdate
from app.schemas.user import ChangePasswordRequest, UserUpdate


class UserService:
    @staticmethod
    def get_profile(current_user: User) -> User:
        return current_user

    @staticmethod
    def update_profile(db: Session, current_user: User, data: UserUpdate) -> User:
        if data.email and data.email != current_user.email:
            existing = UserRepository.get_by_email(db, data.email)
            if existing:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="El email ya está registrado"
                )
            current_user.email = data.email

        if data.nombre_usuario and data.nombre_usuario != current_user.nombre_usuario:
            existing = UserRepository.get_by_username(db, data.nombre_usuario)
            if existing:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="El nombre de usuario ya está en uso"
                )
            current_user.nombre_usuario = data.nombre_usuario

        if data.nombre_completo is not None:
            current_user.nombre_completo = data.nombre_completo

        if data.telefono is not None:
            current_user.telefono = data.telefono

        return UserRepository.save(db, current_user)

    @staticmethod
    def change_password(
        db: Session,
        current_user: User,
        data: ChangePasswordRequest,
    ) -> dict:
        if not verify_password(data.contrasena_actual, current_user.contrasena):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="La contraseña actual no es correcta"
            )

        current_user.contrasena = hash_password(data.nueva_contrasena)
        UserRepository.save(db, current_user)

        SessionRepository.revoke_all_user_sessions(db, current_user.id_usuario)

        return {"message": "Contraseña actualizada correctamente. Inicia sesión de nuevo."}

    @staticmethod
    def get_preferences(db: Session, current_user: User) -> PreferenciasUsuario:
        prefs = PreferencesRepository.get_by_user_id(db, current_user.id_usuario)
        if prefs is None:
            prefs = PreferenciasUsuario(usuario_id=current_user.id_usuario)
            prefs = PreferencesRepository.create(db, prefs)
        return prefs

    @staticmethod
    def update_preferences(
        db: Session,
        current_user: User,
        data: PreferenciasUpdate,
    ) -> dict:
        prefs = PreferencesRepository.get_by_user_id(db, current_user.id_usuario)
        if prefs is None:
            prefs = PreferenciasUsuario(usuario_id=current_user.id_usuario)

        prefs.idioma = data.idioma
        prefs.modo_oscuro = data.modo_oscuro
        prefs.notificaciones = data.notificaciones
        prefs.unidad_peso = data.unidad_peso
        prefs.unidad_precio = data.unidad_precio
        prefs.supermercado_favorito = data.supermercado_favorito

        if prefs.id_preferencia is None:
            PreferencesRepository.create(db, prefs)
        else:
            PreferencesRepository.save(db, prefs)

        SessionRepository.revoke_all_user_sessions(db, current_user.id_usuario)

        return {
            "message": "Preferencias actualizadas correctamente. Inicia sesión de nuevo."
        }

    @staticmethod
    def get_bot_config(db: Session, current_user: User) -> ConfiguracionBotExterno:
        config = BotConfigRepository.get_by_user_id(db, current_user.id_usuario)
        if config is None:
            config = ConfiguracionBotExterno(usuario_id=current_user.id_usuario)
            config = BotConfigRepository.create(db, config)
        return config

    @staticmethod
    def update_bot_config(
        db: Session,
        current_user: User,
        data: BotConfigUpdate,
    ) -> ConfiguracionBotExterno:
        config = BotConfigRepository.get_by_user_id(db, current_user.id_usuario)
        if config is None:
            config = ConfiguracionBotExterno(usuario_id=current_user.id_usuario)

        config.plataforma = data.plataforma
        config.token = data.token
        config.estado = data.estado

        if config.id_configuracion is None:
            return BotConfigRepository.create(db, config)

        return BotConfigRepository.save(db, config)

    @staticmethod
    def get_active_sessions(db: Session, current_user: User):
        return SessionRepository.get_active_by_user_id(db, current_user.id_usuario)

    @staticmethod
    def request_account_action(
        db: Session,
        current_user: User,
        data: AccountActionRequestCreate,
    ) -> SolicitudBajaUsuario:
        if data.tipo not in {"desactivacion", "eliminacion"}:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="El tipo debe ser 'desactivacion' o 'eliminacion'"
            )

        existing = AccountRequestRepository.get_pending_by_user_id(
            db,
            current_user.id_usuario,
        )
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Ya existe una solicitud pendiente para esta cuenta"
            )

        solicitud = SolicitudBajaUsuario(
            tipo=data.tipo,
            motivo=data.motivo,
            usuario_id=current_user.id_usuario,
        )

        return AccountRequestRepository.create(db, solicitud)