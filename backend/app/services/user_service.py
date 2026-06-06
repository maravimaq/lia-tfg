from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.core.security import hash_password, verify_password
from app.models.configuracion_bot_externo import ConfiguracionBotExterno
from app.models.preferencias_usuario import PreferenciasUsuario
from app.models.solicitud_baja_usuario import SolicitudBajaUsuario
from app.models.user import User
from app.models.seguimiento_usuario import SeguimientoUsuario
from app.models.solicitud_seguimiento import SolicitudSeguimiento
from app.repositories.account_request_repository import AccountRequestRepository
from app.repositories.bot_config_repository import BotConfigRepository
from app.repositories.follow_repository import FollowRepository
from app.repositories.preferences_repository import PreferencesRepository
from app.repositories.session_repository import SessionRepository
from app.repositories.user_repository import UserRepository
from app.schemas.account_request import AccountActionRequestCreate
from app.schemas.bot_config import BotConfigUpdate
from app.schemas.follow import FollowRequestAction
from app.schemas.preferences import PreferenciasUpdate
from app.schemas.user import ChangePasswordRequest, UserUpdate


class UserService:
    @staticmethod
    def get_profile(current_user: User) -> User:
        return current_user

    @staticmethod
    def update_profile(db: Session, current_user: User, data: UserUpdate) -> User:
        email_changed = False

        if data.email and data.email != current_user.email:
            existing = UserRepository.get_by_email(db, data.email)
            if existing:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="El email ya está registrado"
                )
            current_user.email = data.email
            email_changed = True

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

        if data.avatar_url is not None:
            current_user.avatar_url = data.avatar_url

        updated_user = UserRepository.save(db, current_user)

        if email_changed:
            SessionRepository.revoke_all_user_sessions(db, current_user.id_usuario)

        return updated_user

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
        return PreferencesRepository.get_or_create_by_user_id(
            db,
            current_user.id_usuario,
        )

    @staticmethod
    def update_preferences(
        db: Session,
        current_user: User,
        data: PreferenciasUpdate,
    ) -> PreferenciasUsuario:
        prefs = PreferencesRepository.get_or_create_by_user_id(
            db,
            current_user.id_usuario,
        )

        update_data = data.model_dump(exclude_unset=True)

        for field, value in update_data.items():
            setattr(prefs, field, value)

        return PreferencesRepository.save(db, prefs)

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
            existing.tipo = data.tipo
            existing.motivo = data.motivo
            db.add(existing)
            db.commit()
            db.refresh(existing)
            created_request = existing
        else:
            solicitud = SolicitudBajaUsuario(
                tipo=data.tipo,
                motivo=data.motivo,
                usuario_id=current_user.id_usuario,
            )
            created_request = AccountRequestRepository.create(db, solicitud)

        if data.tipo == "eliminacion":
            current_user.estado = "inactivo"
            UserRepository.save(db, current_user)
            SessionRepository.revoke_all_user_sessions(db, current_user.id_usuario)

        return created_request

    @staticmethod
    def discover_users(db: Session, current_user: User, search: str | None = None):
        users = UserRepository.discover_users(db, current_user.id_usuario, search)
        results = []

        for user in users:
            follow = FollowRepository.get_follow(db, current_user.id_usuario, user.id_usuario)
            request = FollowRepository.get_request_between(db, current_user.id_usuario, user.id_usuario)

            status = "none"
            if follow is not None:
                status = "followed"
            elif request is not None and request.estado == "pendiente":
                status = "pending"

            results.append(
                {
                    "id_usuario": user.id_usuario,
                    "nombre_usuario": user.nombre_usuario,
                    "nombre_completo": user.nombre_completo,
                    "email": user.email,
                    "avatar_url": user.avatar_url,
                    "follow_status": status,
                    "_followed_at": follow.fecha_seguimiento if follow else None,
                }
            )

        followed = [item for item in results if item["follow_status"] == "followed"]
        pending_or_none = [item for item in results if item["follow_status"] != "followed"]

        followed.sort(key=lambda item: item["_followed_at"], reverse=True)
        pending_or_none.sort(key=lambda item: item["nombre_completo"].lower())

        ordered = followed + pending_or_none

        for item in ordered:
            item.pop("_followed_at", None)

        return ordered

    @staticmethod
    def request_follow(db: Session, current_user: User, target_user_id: int):
        if current_user.id_usuario == target_user_id:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No puedes seguirte a ti mismo")

        target = UserRepository.get_by_id(db, target_user_id)
        if target is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Usuario destino no encontrado")

        existing_follow = FollowRepository.get_follow(db, current_user.id_usuario, target_user_id)
        if existing_follow is not None:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Ya sigues a este usuario")

        existing_request = FollowRepository.get_request_between(db, current_user.id_usuario, target_user_id)
        if existing_request and existing_request.estado == "pendiente":
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Ya existe una solicitud pendiente")

        solicitud = SolicitudSeguimiento(
            solicitante_id=current_user.id_usuario,
            destinatario_id=target_user_id,
            estado="pendiente",
        )

        return FollowRepository.create_request(db, solicitud)

    @staticmethod
    def get_incoming_follow_requests(db: Session, current_user: User):
        requests = FollowRepository.get_incoming_pending_requests(db, current_user.id_usuario)
        response = []

        for req in requests:
            solicitante = req.solicitante
            response.append(
                {
                    "id_solicitud_seguimiento": req.id_solicitud_seguimiento,
                    "estado": req.estado,
                    "fecha_solicitud": req.fecha_solicitud,
                    "solicitante": {
                        "id_usuario": solicitante.id_usuario,
                        "nombre_usuario": solicitante.nombre_usuario,
                        "nombre_completo": solicitante.nombre_completo,
                        "email": solicitante.email,
                        "avatar_url": solicitante.avatar_url,
                        "follow_status": "none",
                    },
                }
            )

        return response

    @staticmethod
    def respond_follow_request(
        db: Session,
        current_user: User,
        request_id: int,
        action: FollowRequestAction,
    ):
        req = FollowRepository.get_request_by_id(db, request_id)
        if req is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Solicitud no encontrada")

        if req.destinatario_id != current_user.id_usuario:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="No puedes responder esta solicitud")

        if action.accion not in {"aceptar", "rechazar"}:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Acción inválida")

        if action.accion == "rechazar":
            FollowRepository.delete_request(db, req)
            return {"message": "Solicitud rechazada"}

        req.estado = "aceptada"
        FollowRepository.save_request(db, req)

        if FollowRepository.get_follow(db, req.solicitante_id, req.destinatario_id) is None:
            follow = SeguimientoUsuario(
                seguidor_id=req.solicitante_id,
                seguido_id=req.destinatario_id,
            )
            FollowRepository.create_follow(db, follow)

        return {"message": "Solicitud aceptada"}

    @staticmethod
    def get_public_profile(db: Session, user_id: int):
        user = UserRepository.get_by_id(db, user_id)
        if user is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Usuario no encontrado")

        return {
            "id_usuario": user.id_usuario,
            "nombre_usuario": user.nombre_usuario,
            "nombre_completo": user.nombre_completo,
            "email": user.email,
            "avatar_url": user.avatar_url,
            "estado": user.estado,
            "fecha_registro": user.fecha_registro,
            "rol_id": user.rol_id,
            "proveedor_auth": user.proveedor_auth,
            "telefono": user.telefono,
        }