from typing import Any
from jose import jwt, JWTError
from fastapi import HTTPException, status

from app.schemas.auth import ExternalUserPayload


def _build_username_from_email(email: str) -> str:
    return email.split("@")[0]


def verify_google_id_token(id_token: str) -> ExternalUserPayload:
    """
    Implementación simplificada para entorno TFG/desarrollo.

    En producción deberías verificar firma, audience, issuer y expiración
    contra Google. Aquí decodificamos el JWT sin validar firma para poder
    desarrollar la integración de extremo a extremo.
    """
    try:
        payload: dict[str, Any] = jwt.get_unverified_claims(id_token)
        email = payload.get("email")
        name = payload.get("name") or payload.get("given_name")

        if not email:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="El token de Google no contiene email"
            )

        return ExternalUserPayload(
            email=email,
            nombre_completo=name or _build_username_from_email(email),
            nombre_usuario=_build_username_from_email(email),
        )
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Token de Google inválido"
        )
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No se pudo procesar el token de Google"
        )


def verify_apple_id_token(id_token: str) -> ExternalUserPayload:
    """
    Implementación simplificada para entorno TFG/desarrollo.

    En producción deberías verificar firma, audience, issuer y claims
    específicos de Apple.
    """
    try:
        payload: dict[str, Any] = jwt.get_unverified_claims(id_token)
        email = payload.get("email")

        if not email:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="El token de Apple no contiene email"
            )

        return ExternalUserPayload(
            email=email,
            nombre_completo=_build_username_from_email(email),
            nombre_usuario=_build_username_from_email(email),
        )
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Token de Apple inválido"
        )
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No se pudo procesar el token de Apple"
        )