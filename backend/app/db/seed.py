from app.db.session import SessionLocal

from app.models.role import Role
from app.models.user import User
from app.models.preferencias_usuario import PreferenciasUsuario
from app.models.configuracion_bot_externo import ConfiguracionBotExterno
from app.models.sesion_autenticacion import SesionAutenticacion
from app.models.solicitud_baja_usuario import SolicitudBajaUsuario
from app.models.lista_compra import ListaCompra
from app.models.producto_lista import ProductoLista
from app.models.solicitud_seguimiento import SolicitudSeguimiento
from app.models.seguimiento_usuario import SeguimientoUsuario
from app.db.session import SessionLocal, engine
from app.db.base import Base

from app.core.security import hash_password


def seed_roles(db):
    roles_data = [
        {
            "nombre": "usuario",
            "descripcion": "Usuario estándar de la aplicación"
        },
        {
            "nombre": "administrador",
            "descripcion": "Administrador del sistema"
        },
    ]

    roles = {}

    for role_data in roles_data:
        role = db.query(Role).filter(Role.nombre == role_data["nombre"]).first()

        if not role:
            role = Role(
                nombre=role_data["nombre"],
                descripcion=role_data["descripcion"]
            )
            db.add(role)
            db.commit()
            db.refresh(role)
            print(f"Rol creado: {role.nombre}")
        else:
            print(f"Rol ya existe: {role.nombre}")

        roles[role.nombre] = role

    return roles


def seed_users(db, roles):
    users_data = [
        {
            "nombre_usuario": "admin",
            "nombre_completo": "Administrador por defecto",
            "email": "admin@lia.com",
            "contrasena": "admin1234",
            "telefono": "600000000",
            "avatar_url": "https://i.pravatar.cc/300?img=12",
            "estado": "activo",
            "proveedor_auth": "local",
            "rol_id": roles["administrador"].id_rol,
            "preferencias": {
                "idioma": "es",
                "modo_oscuro": False,
                "notificaciones": True,
                "unidad_peso": "kg",
                "unidad_precio": "EUR",
                "supermercado_favorito": "Mercadona"
            },
            "configuracion_bot": {
                "plataforma": "telegram",
                "token": None,
                "estado": "inactivo"
            }
        },
        {
            "nombre_usuario": "usuario1",
            "nombre_completo": "Usuario Prueba Uno",
            "email": "usuario1@lia.com",
            "contrasena": "usuario1234",
            "telefono": "611111111",
            "avatar_url": "https://i.pravatar.cc/300?img=33",
            "estado": "activo",
            "proveedor_auth": "local",
            "rol_id": roles["usuario"].id_rol,
            "preferencias": {
                "idioma": "es",
                "modo_oscuro": True,
                "notificaciones": True,
                "unidad_peso": "kg",
                "unidad_precio": "EUR",
                "supermercado_favorito": "Lidl"
            },
            "configuracion_bot": {
                "plataforma": "telegram",
                "token": None,
                "estado": "inactivo"
            }
        },
        {
            "nombre_usuario": "usuario2",
            "nombre_completo": "Usuario Prueba Dos",
            "email": "usuario2@lia.com",
            "contrasena": "usuario1234",
            "telefono": "622222222",
            "avatar_url": "https://i.pravatar.cc/300?img=22",
            "estado": "activo",
            "proveedor_auth": "local",
            "rol_id": roles["usuario"].id_rol,
            "preferencias": {
                "idioma": "es",
                "modo_oscuro": False,
                "notificaciones": False,
                "unidad_peso": "kg",
                "unidad_precio": "EUR",
                "supermercado_favorito": "Carrefour"
            },
            "configuracion_bot": {
                "plataforma": "telegram",
                "token": None,
                "estado": "inactivo"
            }
        },
        {
            "nombre_usuario": "usuario3",
            "nombre_completo": "Usuario Prueba Tres",
            "email": "usuario3@lia.com",
            "contrasena": "usuario1234",
            "telefono": "633333333",
            "avatar_url": "https://i.pravatar.cc/300?img=48",
            "estado": "activo",
            "proveedor_auth": "local",
            "rol_id": roles["usuario"].id_rol,
            "preferencias": {
                "idioma": "en",
                "modo_oscuro": False,
                "notificaciones": True,
                "unidad_peso": "lb",
                "unidad_precio": "USD",
                "supermercado_favorito": "Costco"
            },
            "configuracion_bot": {
                "plataforma": "telegram",
                "token": "token-prueba-usuario3",
                "estado": "activo"
            }
        }
    ]

    created_or_existing_users = {}

    for user_data in users_data:
        existing_user = db.query(User).filter(User.email == user_data["email"]).first()

        if existing_user:
            existing_user.avatar_url = user_data["avatar_url"]
            db.add(existing_user)
            db.commit()
            created_or_existing_users[existing_user.nombre_usuario] = existing_user
            print(f"Usuario ya existe: {existing_user.email}")
            continue

        new_user = User(
            nombre_usuario=user_data["nombre_usuario"],
            nombre_completo=user_data["nombre_completo"],
            email=user_data["email"],
            contrasena=hash_password(user_data["contrasena"]),
            telefono=user_data["telefono"],
            avatar_url=user_data["avatar_url"],
            estado=user_data["estado"],
            proveedor_auth=user_data["proveedor_auth"],
            rol_id=user_data["rol_id"],
        )

        db.add(new_user)
        db.commit()
        db.refresh(new_user)

        preferencias = PreferenciasUsuario(
            idioma=user_data["preferencias"]["idioma"],
            modo_oscuro=user_data["preferencias"]["modo_oscuro"],
            notificaciones=user_data["preferencias"]["notificaciones"],
            unidad_peso=user_data["preferencias"]["unidad_peso"],
            unidad_precio=user_data["preferencias"]["unidad_precio"],
            supermercado_favorito=user_data["preferencias"]["supermercado_favorito"],
            usuario_id=new_user.id_usuario
        )
        db.add(preferencias)

        config_bot = ConfiguracionBotExterno(
            plataforma=user_data["configuracion_bot"]["plataforma"],
            token=user_data["configuracion_bot"]["token"],
            estado=user_data["configuracion_bot"]["estado"],
            usuario_id=new_user.id_usuario
        )
        db.add(config_bot)

        sesion = SesionAutenticacion(
            proveedor="local",
            token=f"seed-token-{new_user.id_usuario}",
            estado="activa",
            usuario_id=new_user.id_usuario
        )
        db.add(sesion)

        db.commit()

        created_or_existing_users[new_user.nombre_usuario] = new_user
        print(f"Usuario creado: {new_user.email}")

    return created_or_existing_users


def seed_follow_data(db, users):
    pairs_follow = [
        ("usuario1", "usuario2"),
        ("usuario1", "usuario3"),
    ]

    for seguidor_username, seguido_username in pairs_follow:
        seguidor = users.get(seguidor_username)
        seguido = users.get(seguido_username)

        if not seguidor or not seguido:
            continue

        existing_follow = (
            db.query(SeguimientoUsuario)
            .filter(
                SeguimientoUsuario.seguidor_id == seguidor.id_usuario,
                SeguimientoUsuario.seguido_id == seguido.id_usuario,
            )
            .first()
        )

        if not existing_follow:
            db.add(
                SeguimientoUsuario(
                    seguidor_id=seguidor.id_usuario,
                    seguido_id=seguido.id_usuario,
                )
            )

    pending_requests = [
        ("usuario3", "usuario1"),
    ]

    for solicitante_username, destinatario_username in pending_requests:
        solicitante = users.get(solicitante_username)
        destinatario = users.get(destinatario_username)

        if not solicitante or not destinatario:
            continue

        existing_request = (
            db.query(SolicitudSeguimiento)
            .filter(
                SolicitudSeguimiento.solicitante_id == solicitante.id_usuario,
                SolicitudSeguimiento.destinatario_id == destinatario.id_usuario,
                SolicitudSeguimiento.estado == "pendiente",
            )
            .first()
        )

        if not existing_request:
            db.add(
                SolicitudSeguimiento(
                    solicitante_id=solicitante.id_usuario,
                    destinatario_id=destinatario.id_usuario,
                    estado="pendiente",
                )
            )

    db.commit()
    print("Relaciones y solicitudes de seguimiento insertadas/actualizadas.")


def run_seed():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        print("Insertando roles por defecto...")
        roles = seed_roles(db)

        print("Insertando usuarios por defecto...")
        users = seed_users(db, roles)

        print("Insertando datos de amigos/seguimientos...")
        seed_follow_data(db, users)

        print("Seed completado correctamente.")
    except Exception as e:
        db.rollback()
        print(f"Error durante el seed: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    run_seed()