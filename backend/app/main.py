from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.db.session import engine
from app.db.base import Base

from app.controllers.auth_controller import router as auth_router
from app.controllers.user_controller import router as user_router
from app.controllers.admin_controller import router as admin_router
from app.controllers.lista_compra_controller import router as lista_router
from app.controllers.producto_lista_controller import router as producto_router


app = FastAPI()


app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:8081",
        "http://127.0.0.1:8081",
        "http://localhost:19006",
        "http://127.0.0.1:19006",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def on_startup():
    Base.metadata.create_all(bind=engine)


# REGISTRO ENDPOINTS
app.include_router(auth_router)
app.include_router(user_router)
app.include_router(admin_router)
app.include_router(lista_router)
app.include_router(producto_router)


@app.get("/health")
def health():
    return {"status": "ok"}