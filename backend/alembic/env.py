from logging.config import fileConfig

from alembic import context
from sqlalchemy import create_engine, pool

from app.core.config import settings
from app.db.base import Base


# Objeto de configuración de Alembic.
config = context.config


# Configuración de los logs definidos en alembic.ini.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)


# Metadata con todas las tablas registradas en SQLAlchemy.
target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """
    Ejecuta migraciones sin abrir una conexión directa.

    Alembic genera las instrucciones SQL utilizando DATABASE_URL.
    """
    context.configure(
        url=settings.database_url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
        compare_server_default=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """
    Ejecuta migraciones conectándose directamente a la base de datos.
    """
    connectable = create_engine(
        settings.database_url,
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
            compare_server_default=True,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()