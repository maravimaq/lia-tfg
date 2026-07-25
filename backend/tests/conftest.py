from __future__ import annotations

import os
from collections.abc import Generator

# Deben definirse antes de importar cualquier módulo de app.
os.environ.setdefault("DATABASE_URL", "sqlite+pysqlite:///:memory:")
os.environ.setdefault("JWT_SECRET_KEY", "test-secret-key-only-for-pytest-123456789")
os.environ.setdefault("JWT_ALGORITHM", "HS256")
os.environ.setdefault("ACCESS_TOKEN_EXPIRE_MINUTES", "60")
os.environ.setdefault("AI_PROVIDER", "mock")
os.environ.setdefault("TELEGRAM_BOT_TOKEN", "")
os.environ.setdefault("TELEGRAM_WEBHOOK_SECRET", "test-telegram-secret")

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool


@compiles(JSONB, "sqlite")
def _compile_jsonb_for_sqlite(_type, _compiler, **_kw):
    """Permite crear en SQLite las tablas que usan JSONB en producción."""
    return "JSON"


from app.core.security import hash_password
from app.db.base import Base
from app.db.session import get_db
from app.main import app
from app.models.role import Role
from app.models.user import User


TEST_DATABASE_URL = "sqlite+pysqlite:///:memory:"

test_engine = create_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    expire_on_commit=False,
    bind=test_engine,
)


@pytest.fixture(autouse=True)
def reset_database() -> Generator[None, None, None]:
    Base.metadata.drop_all(bind=test_engine)
    Base.metadata.create_all(bind=test_engine)

    with TestingSessionLocal() as db:
        db.add_all(
            [
                Role(nombre="usuario", descripcion="Usuario estándar"),
                Role(nombre="administrador", descripcion="Administrador"),
            ]
        )
        db.commit()

    yield

    app.dependency_overrides.clear()


@pytest.fixture
def db() -> Generator[Session, None, None]:
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def client() -> Generator[TestClient, None, None]:
    def override_get_db() -> Generator[Session, None, None]:
        session = TestingSessionLocal()
        try:
            yield session
        finally:
            session.close()

    app.dependency_overrides[get_db] = override_get_db
    test_client = TestClient(app)
    try:
        yield test_client
    finally:
        test_client.close()


@pytest.fixture
def create_admin(db: Session):
    def _create_admin(
        *,
        email: str = "admin@example.com",
        username: str = "admin_test",
        password: str = "Admin1234!",
    ) -> User:
        role = db.query(Role).filter(Role.nombre == "administrador").one()
        user = User(
            nombre_usuario=username,
            nombre_completo="Administrador Test",
            email=email,
            contrasena=hash_password(password),
            telefono=None,
            estado="activo",
            rol_id=role.id_rol,
            proveedor_auth="local",
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        return user

    return _create_admin
