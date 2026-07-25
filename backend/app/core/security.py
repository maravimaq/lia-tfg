from datetime import datetime, timedelta
import hashlib
from uuid import uuid4

from fastapi import HTTPException, status
from jose import JWTError, jwt
from passlib.context import CryptContext

from app.core.config import settings


pwd_context = CryptContext(
    schemes=["bcrypt"],
    deprecated="auto"
)


def _normalize_password_for_bcrypt(password: str) -> str:
    return hashlib.sha256(password.encode("utf-8")).hexdigest()


# -----------------------
# PASSWORD
# -----------------------

def hash_password(password: str) -> str:
    try:
        normalized_password = _normalize_password_for_bcrypt(password)
        return pwd_context.hash(normalized_password)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Se produjo un error al cifrar la contraseña: {str(exc)}"
        ) from exc


def verify_password(plain_password: str, hashed_password: str) -> bool:
    try:
        normalized_password = _normalize_password_for_bcrypt(plain_password)
        return pwd_context.verify(normalized_password, hashed_password)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Se produjo un error al verificar la contraseña: {str(exc)}"
        ) from exc


# -----------------------
# JWT
# -----------------------

def create_access_token(data: dict) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(
        minutes=settings.access_token_expire_minutes
    )

    # jti (JWT ID) garantiza que dos tokens emitidos en el mismo segundo
    # para el mismo usuario sigan siendo diferentes.
    to_encode.update({
        "exp": expire,
        "type": "access",
        "jti": uuid4().hex,
    })

    encoded_jwt = jwt.encode(
        to_encode,
        settings.jwt_secret_key,
        algorithm=settings.jwt_algorithm
    )
    return encoded_jwt


def create_password_reset_token(email: str) -> str:
    expire = datetime.utcnow() + timedelta(minutes=30)
    data = {
        "sub": email,
        "exp": expire,
        "type": "password_reset",
    }
    return jwt.encode(
        data,
        settings.jwt_secret_key,
        algorithm=settings.jwt_algorithm,
    )


def decode_token(token: str) -> dict:
    return jwt.decode(
        token,
        settings.jwt_secret_key,
        algorithms=[settings.jwt_algorithm],
    )


def is_password_reset_token(token: str) -> bool:
    try:
        payload = decode_token(token)
        return payload.get("type") == "password_reset"
    except JWTError:
        return False
