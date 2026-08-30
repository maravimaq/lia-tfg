from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from fastapi.security import HTTPAuthorizationCredentials

from app.core.dependencies import security
from app.db.session import get_db
from app.schemas.user import (
    UserCreate,
    UserResponse,
    ForgotPasswordRequest,
    ResetPasswordRequest,
)
from app.schemas.auth import LoginRequest, TokenResponse
from app.services.auth_service import AuthService


router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=UserResponse)
def register(user_data: UserCreate, db: Session = Depends(get_db)):
    user = AuthService.register(db, user_data)
    return user


@router.post("/login", response_model=TokenResponse)
def login(login_data: LoginRequest, db: Session = Depends(get_db)):
    token = AuthService.login(db, login_data.email, login_data.contrasena)
    return {"access_token": token, "token_type": "bearer"}


@router.post("/logout")
def logout(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db),
):
    return AuthService.logout(db, credentials.credentials)


@router.post("/forgot-password")
def forgot_password(
    request_data: ForgotPasswordRequest,
    db: Session = Depends(get_db),
):
    return AuthService.forgot_password(db, request_data.email)


@router.post("/reset-password")
def reset_password(
    request_data: ResetPasswordRequest,
    db: Session = Depends(get_db),
):
    return AuthService.reset_password(
        db,
        request_data.token,
        request_data.nueva_contrasena,
    )