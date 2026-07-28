from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.db.base import Base
from app.db.session import engine

from app.controllers.admin_controller import router as admin_router
from app.controllers.analytics_controller import router as analytics_router
from app.controllers.auth_controller import router as auth_router
from app.controllers.chat_controller import router as chat_router
from app.controllers.external_bot_controller import router as external_bot_router
from app.controllers.historial_listas_controller import router as historial_router
from app.controllers.lista_compartida_controller import (
    router as lista_compartida_router,
)
from app.controllers.lista_compra_controller import router as lista_router
from app.controllers.producto_controller import (
    router as producto_catalogo_router,
)
from app.controllers.producto_lista_controller import router as producto_router
from app.controllers.user_controller import router as user_router


@asynccontextmanager
async def lifespan(_: FastAPI):
    """
    Gestiona el ciclo de vida de la aplicación.

    En desarrollo permite crear las tablas automáticamente.
    En producción esta opción estará desactivada y se utilizará Alembic.
    """
    if settings.create_tables_on_startup:
        Base.metadata.create_all(bind=engine)

    yield


app = FastAPI(
    title="LIA API",
    description="API de Lista Inteligente Asistida",
    version="1.0.0",
    lifespan=lifespan,
)


app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Registro de endpoints
app.include_router(auth_router)
app.include_router(user_router)
app.include_router(admin_router)
app.include_router(lista_compartida_router)
app.include_router(lista_router)
app.include_router(historial_router)
app.include_router(producto_router)
app.include_router(producto_catalogo_router)
app.include_router(chat_router)
app.include_router(analytics_router)
app.include_router(external_bot_router)


@app.get("/health", tags=["Health"])
def health() -> dict[str, str]:
    return {
        "status": "ok",
        "environment": settings.environment,
    }