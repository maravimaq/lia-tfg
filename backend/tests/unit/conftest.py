from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest


@pytest.fixture
def db():
    """Doble de prueba: nunca abre una conexión real."""
    return MagicMock(name="db_session")


@pytest.fixture
def user():
    return SimpleNamespace(
        id_usuario=1,
        email="juan@example.com",
        nombre_usuario="juan",
        nombre_completo="Juan",
        contrasena="hash",
        estado="activo",
        proveedor_auth="local",
        telefono=None,
        avatar_url=None,
        rol_id=2,
    )
