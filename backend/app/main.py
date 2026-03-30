from fastapi import FastAPI

from app.db.session import engine
from app.db.base import Base

from app.controllers.auth_controller import router as auth_router


app = FastAPI()


@app.on_event("startup")
def on_startup():
    Base.metadata.create_all(bind=engine)


# 🔥 AQUÍ REGISTRAS LOS ENDPOINTS
app.include_router(auth_router)


@app.get("/health")
def health():
    return {"status": "ok"}