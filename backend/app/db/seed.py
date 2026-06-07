from datetime import datetime
from decimal import Decimal

from app.core.security import hash_password
from app.db.base import Base
from app.db.session import SessionLocal, engine
from app.models.configuracion_bot_externo import ConfiguracionBotExterno
from app.models.lista_compra import ListaCompra
from app.models.preferencias_usuario import PreferenciasUsuario
from app.models.producto_lista import ProductoLista
from app.models.role import Role
from app.models.seguimiento_usuario import SeguimientoUsuario
from app.models.sesion_autenticacion import SesionAutenticacion
from app.models.solicitud_baja_usuario import SolicitudBajaUsuario
from app.models.solicitud_seguimiento import SolicitudSeguimiento
from app.models.user import User


def seed_roles(db):
    roles_data = [
        {
            "nombre": "usuario",
            "descripcion": "Usuario estándar de la aplicación",
        },
        {
            "nombre": "administrador",
            "descripcion": "Administrador del sistema",
        },
    ]

    roles = {}

    for role_data in roles_data:
        role = db.query(Role).filter(Role.nombre == role_data["nombre"]).first()

        if not role:
            role = Role(
                nombre=role_data["nombre"],
                descripcion=role_data["descripcion"],
            )
            db.add(role)
            db.commit()
            db.refresh(role)
            print(f"Rol creado: {role.nombre}")
        else:
            role.descripcion = role_data["descripcion"]
            db.add(role)
            db.commit()
            db.refresh(role)
            print(f"Rol ya existe: {role.nombre}")

        roles[role.nombre] = role

    return roles


def upsert_preferences(db, user, preferencias_data):
    preferencias = (
        db.query(PreferenciasUsuario)
        .filter(PreferenciasUsuario.usuario_id == user.id_usuario)
        .first()
    )

    if not preferencias:
        preferencias = PreferenciasUsuario(usuario_id=user.id_usuario)

    preferencias.idioma = preferencias_data["idioma"]
    preferencias.modo_oscuro = preferencias_data["modo_oscuro"]
    preferencias.notificaciones = preferencias_data["notificaciones"]
    preferencias.unidad_peso = preferencias_data["unidad_peso"]
    preferencias.unidad_precio = preferencias_data["unidad_precio"]
    preferencias.supermercado_favorito = preferencias_data["supermercado_favorito"]

    db.add(preferencias)
    db.commit()
    db.refresh(preferencias)

    return preferencias


def upsert_bot_config(db, user, configuracion_data):
    config_bot = (
        db.query(ConfiguracionBotExterno)
        .filter(ConfiguracionBotExterno.usuario_id == user.id_usuario)
        .first()
    )

    if not config_bot:
        config_bot = ConfiguracionBotExterno(usuario_id=user.id_usuario)

    config_bot.plataforma = configuracion_data["plataforma"]
    config_bot.token = configuracion_data["token"]
    config_bot.estado = configuracion_data["estado"]

    db.add(config_bot)
    db.commit()
    db.refresh(config_bot)

    return config_bot


def seed_user_session(db, user):
    token = f"seed-token-{user.id_usuario}"
    sesion = (
        db.query(SesionAutenticacion)
        .filter(SesionAutenticacion.token == token)
        .first()
    )

    session_status = "activa" if user.estado == "activo" else "revocada"
    session_end = None if session_status == "activa" else datetime.utcnow()

    if not sesion:
        sesion = SesionAutenticacion(
            proveedor=user.proveedor_auth or "local",
            token=token,
            estado=session_status,
            fecha_fin=session_end,
            usuario_id=user.id_usuario,
        )
    else:
        sesion.proveedor = user.proveedor_auth or "local"
        sesion.estado = session_status
        sesion.fecha_fin = session_end
        sesion.usuario_id = user.id_usuario

    db.add(sesion)
    db.commit()
    db.refresh(sesion)

    return sesion


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
                "supermercado_favorito": "Mercadona",
            },
            "configuracion_bot": {
                "plataforma": "telegram",
                "token": None,
                "estado": "inactivo",
            },
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
                "supermercado_favorito": "DIA",
            },
            "configuracion_bot": {
                "plataforma": "telegram",
                "token": None,
                "estado": "inactivo",
            },
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
                "supermercado_favorito": "Carrefour",
            },
            "configuracion_bot": {
                "plataforma": "telegram",
                "token": None,
                "estado": "inactivo",
            },
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
                "supermercado_favorito": "Alcampo",
            },
            "configuracion_bot": {
                "plataforma": "telegram",
                "token": "token-prueba-usuario3",
                "estado": "activo",
            },
        },
        {
            "nombre_usuario": "usuario_baja",
            "nombre_completo": "Usuario Pendiente Baja",
            "email": "usuario_baja@lia.com",
            "contrasena": "usuario1234",
            "telefono": "644444444",
            "avatar_url": "https://i.pravatar.cc/300?img=56",
            "estado": "inactivo",
            "proveedor_auth": "local",
            "rol_id": roles["usuario"].id_rol,
            "preferencias": {
                "idioma": "es",
                "modo_oscuro": False,
                "notificaciones": True,
                "unidad_peso": "kg",
                "unidad_precio": "EUR",
                "supermercado_favorito": "DIA",
            },
            "configuracion_bot": {
                "plataforma": "telegram",
                "token": None,
                "estado": "inactivo",
            },
        },
    ]

    created_or_existing_users = {}

    for user_data in users_data:
        user = db.query(User).filter(User.email == user_data["email"]).first()

        if not user:
            user = User(
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
            db.add(user)
            db.commit()
            db.refresh(user)
            print(f"Usuario creado: {user.email}")
        else:
            user.nombre_usuario = user_data["nombre_usuario"]
            user.nombre_completo = user_data["nombre_completo"]
            user.telefono = user_data["telefono"]
            user.avatar_url = user_data["avatar_url"]
            user.estado = user_data["estado"]
            user.proveedor_auth = user_data["proveedor_auth"]
            user.rol_id = user_data["rol_id"]
            db.add(user)
            db.commit()
            db.refresh(user)
            print(f"Usuario ya existe y se actualizó: {user.email}")

        upsert_preferences(db, user, user_data["preferencias"])
        upsert_bot_config(db, user, user_data["configuracion_bot"])
        seed_user_session(db, user)

        created_or_existing_users[user.nombre_usuario] = user

    return created_or_existing_users


def seed_follow_data(db, users):
    pairs_follow = [
        ("usuario1", "usuario2"),
        ("usuario1", "usuario3"),
        ("usuario2", "usuario1"),
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
        else:
            existing_request.estado = "pendiente"
            db.add(existing_request)

    db.commit()
    print("Relaciones y solicitudes de seguimiento insertadas/actualizadas.")


def seed_account_requests(db, users):
    requests_data = [
        {
            "usuario": "usuario_baja",
            "tipo": "eliminacion",
            "motivo": "Solicitud seed para probar la notificación preferente del dashboard admin.",
            "estado": "pendiente",
        },
        {
            "usuario": "usuario3",
            "tipo": "desactivacion",
            "motivo": "Ejemplo seed de solicitud histórica rechazada.",
            "estado": "rechazada",
        },
    ]

    for request_data in requests_data:
        user = users.get(request_data["usuario"])

        if not user:
            continue

        existing_request = (
            db.query(SolicitudBajaUsuario)
            .filter(
                SolicitudBajaUsuario.usuario_id == user.id_usuario,
                SolicitudBajaUsuario.tipo == request_data["tipo"],
                SolicitudBajaUsuario.estado == request_data["estado"],
            )
            .first()
        )

        if not existing_request:
            existing_request = SolicitudBajaUsuario(
                usuario_id=user.id_usuario,
                tipo=request_data["tipo"],
                motivo=request_data["motivo"],
                estado=request_data["estado"],
            )
        else:
            existing_request.motivo = request_data["motivo"]

        db.add(existing_request)

        if request_data["tipo"] == "eliminacion" and request_data["estado"] == "pendiente":
            user.estado = "inactivo"
            db.add(user)
            active_sessions = (
                db.query(SesionAutenticacion)
                .filter(
                    SesionAutenticacion.usuario_id == user.id_usuario,
                    SesionAutenticacion.estado == "activa",
                )
                .all()
            )
            for session in active_sessions:
                session.estado = "revocada"
                session.fecha_fin = datetime.utcnow()
                db.add(session)

    db.commit()
    print("Solicitudes de baja/eliminación insertadas/actualizadas.")


def seed_shopping_lists(db, users):
    lists_data = [
        {
            "usuario": "usuario1",
            "nombre_lista": "Compra semanal",
            "compartida": True,
            "total_estimado": Decimal("18.25"),
            "productos": [
                {
                    "nombre_producto": "Leche",
                    "cantidad": 2,
                    "unidad_medida": "L",
                    "supermercado": "Mercadona",
                    "precio_estimado": Decimal("1.10"),
                },
                {
                    "nombre_producto": "Pan integral",
                    "cantidad": 1,
                    "unidad_medida": "ud",
                    "supermercado": "Carrefour",
                    "precio_estimado": Decimal("1.45"),
                },
                {
                    "nombre_producto": "Manzanas",
                    "cantidad": 2,
                    "unidad_medida": "kg",
                    "supermercado": "Lidl",
                    "precio_estimado": Decimal("2.30"),
                },
            ],
        },
        {
            "usuario": "usuario2",
            "nombre_lista": "Cena amigos",
            "compartida": False,
            "total_estimado": Decimal("27.80"),
            "productos": [
                {
                    "nombre_producto": "Pasta",
                    "cantidad": 3,
                    "unidad_medida": "paquetes",
                    "supermercado": "DIA",
                    "precio_estimado": Decimal("1.25"),
                },
                {
                    "nombre_producto": "Tomate frito",
                    "cantidad": 2,
                    "unidad_medida": "botes",
                    "supermercado": "Mercadona",
                    "precio_estimado": Decimal("1.60"),
                },
            ],
        },
    ]

    for list_data in lists_data:
        user = users.get(list_data["usuario"])

        if not user:
            continue

        lista = (
            db.query(ListaCompra)
            .filter(
                ListaCompra.usuario_id == user.id_usuario,
                ListaCompra.nombre_lista == list_data["nombre_lista"],
            )
            .first()
        )

        if not lista:
            lista = ListaCompra(
                nombre_lista=list_data["nombre_lista"],
                compartida=list_data["compartida"],
                total_estimado=list_data["total_estimado"],
                usuario_id=user.id_usuario,
            )
        else:
            lista.compartida = list_data["compartida"]
            lista.total_estimado = list_data["total_estimado"]

        db.add(lista)
        db.commit()
        db.refresh(lista)

        for product_data in list_data["productos"]:
            producto = (
                db.query(ProductoLista)
                .filter(
                    ProductoLista.lista_id == lista.id_lista,
                    ProductoLista.nombre_producto == product_data["nombre_producto"],
                )
                .first()
            )

            if not producto:
                producto = ProductoLista(
                    nombre_producto=product_data["nombre_producto"],
                    lista_id=lista.id_lista,
                )

            producto.cantidad = product_data["cantidad"]
            producto.unidad_medida = product_data["unidad_medida"]
            producto.supermercado = product_data["supermercado"]
            producto.precio_estimado = product_data["precio_estimado"]
            db.add(producto)

    db.commit()
    print("Listas de compra y productos insertados/actualizados.")


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

        print("Insertando solicitudes de baja/eliminación...")
        seed_account_requests(db, users)

        print("Insertando listas y productos de prueba...")
        seed_shopping_lists(db, users)

        print("Seed completado correctamente.")
    except Exception as e:
        db.rollback()
        print(f"Error durante el seed: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    run_seed()