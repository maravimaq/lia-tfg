from unittest.mock import MagicMock

import pytest
from fastapi import HTTPException
from jose import JWTError

import app.core.external_auth as external_auth


def test_username_from_email():
    assert external_auth._build_username_from_email("juan@example.com") == "juan"


def test_google_payload_completo(monkeypatch):
    monkeypatch.setattr(
        external_auth.jwt,
        "get_unverified_claims",
        MagicMock(return_value={"email": "juan@example.com", "name": "Juan"}),
    )
    payload = external_auth.verify_google_id_token("token")
    assert payload.email == "juan@example.com"
    assert payload.nombre_completo == "Juan"
    assert payload.nombre_usuario == "juan"


def test_google_usa_given_name(monkeypatch):
    monkeypatch.setattr(
        external_auth.jwt,
        "get_unverified_claims",
        MagicMock(return_value={"email": "ana@example.com", "given_name": "Ana"}),
    )
    assert external_auth.verify_google_id_token("token").nombre_completo == "Ana"


def test_google_sin_email(monkeypatch):
    monkeypatch.setattr(
        external_auth.jwt, "get_unverified_claims", MagicMock(return_value={})
    )
    with pytest.raises(HTTPException) as exc:
        external_auth.verify_google_id_token("token")
    assert exc.value.status_code == 400


def test_google_jwt_invalido(monkeypatch):
    monkeypatch.setattr(
        external_auth.jwt,
        "get_unverified_claims",
        MagicMock(side_effect=JWTError("bad")),
    )
    with pytest.raises(HTTPException, match="Google inválido"):
        external_auth.verify_google_id_token("token")


def test_apple_payload(monkeypatch):
    monkeypatch.setattr(
        external_auth.jwt,
        "get_unverified_claims",
        MagicMock(return_value={"email": "ana@example.com"}),
    )
    payload = external_auth.verify_apple_id_token("token")
    assert payload.nombre_usuario == "ana"
    assert payload.nombre_completo == "ana"


def test_apple_sin_email(monkeypatch):
    monkeypatch.setattr(
        external_auth.jwt, "get_unverified_claims", MagicMock(return_value={})
    )
    with pytest.raises(HTTPException) as exc:
        external_auth.verify_apple_id_token("token")
    assert exc.value.status_code == 400


def test_apple_jwt_invalido(monkeypatch):
    monkeypatch.setattr(
        external_auth.jwt,
        "get_unverified_claims",
        MagicMock(side_effect=JWTError("bad")),
    )
    with pytest.raises(HTTPException, match="Apple inválido"):
        external_auth.verify_apple_id_token("token")
