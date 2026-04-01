from app.db.session import SessionLocal

# Importar TODOS los modelos para que SQLAlchemy registre las relaciones
from app.models.role import Role
from app.models.user import User
from app.models.preferencias_usuario import PreferenciasUsuario
from app.models.configuracion_bot_externo import ConfiguracionBotExterno
from app.models.sesion_autenticacion import SesionAutenticacion
from app.models.solicitud_baja_usuario import SolicitudBajaUsuario
from app.models.lista_compra import ListaCompra
from app.models.producto_lista import ProductoLista

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
            "estado": "inactivo",
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
        }
    ]

    for user_data in users_data:
        existing_user = db.query(User).filter(User.email == user_data["email"]).first()

        if existing_user:
            print(f"Usuario ya existe: {existing_user.email}")
            continue

        new_user = User(
            nombre_usuario=user_data["nombre_usuario"],
            nombre_completo=user_data["nombre_completo"],
            email=user_data["email"],
            contrasena=hash_password(user_data["contrasena"]),
            telefono=user_data["telefono"],
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

        print(f"Usuario creado: {new_user.email}")


def run_seed():
    db = SessionLocal()
    try:
        print("Insertando roles por defecto...")
        roles = seed_roles(db)

        print("Insertando usuarios por defecto...")
        seed_users(db, roles)

        print("Seed completado correctamente.")
    except Exception as e:
        db.rollback()
        print(f"Error durante el seed: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    run_seed()