from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.core.security import create_access_token, decode_token, hash_password, verify_password
from app.schemas.preferences import PreferenciasUpdate


@pytest.mark.unit
def test_password_hash_and_verification_support_long_passwords():
    password = "a" * 300 + "Z9!"
    hashed = hash_password(password)
    assert hashed != password
    assert verify_password(password, hashed) is True
    assert verify_password(password + "x", hashed) is False


@pytest.mark.unit
def test_access_token_contains_expected_claims():
    token = create_access_token({"sub": "usuario@example.com"})
    payload = decode_token(token)
    assert payload["sub"] == "usuario@example.com"
    assert payload["type"] == "access"
    assert "exp" in payload


@pytest.mark.unit
def test_preferences_normalize_valid_values():
    prefs = PreferenciasUpdate(
        idioma="ES",
        unidad_peso="KG",
        unidad_precio="eur",
        supermercado_favorito="día",
    )
    assert prefs.idioma == "es"
    assert prefs.unidad_peso == "kg"
    assert prefs.unidad_precio == "EUR"
    assert prefs.supermercado_favorito == "DIA"


@pytest.mark.unit
def test_preferences_reject_invalid_values():
    with pytest.raises(ValidationError):
        PreferenciasUpdate(idioma="fr")
