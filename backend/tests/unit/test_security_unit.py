import pytest
from jose import JWTError

from app.core.security import (
    create_access_token,
    create_password_reset_token,
    decode_token,
    hash_password,
    is_password_reset_token,
    verify_password,
)


def test_hash_password_no_devuelve_texto_plano():
    password = "UnaClaveMuySegura123"
    hashed = hash_password(password)

    assert hashed != password
    assert hashed.startswith("$2")


def test_verify_password_acepta_clave_correcta():
    hashed = hash_password("clave-correcta")
    assert verify_password("clave-correcta", hashed) is True


def test_verify_password_rechaza_clave_incorrecta():
    hashed = hash_password("clave-correcta")
    assert verify_password("otra-clave", hashed) is False


def test_access_token_contiene_sub_tipo_y_jti():
    token = create_access_token({"sub": "juan@example.com"})
    payload = decode_token(token)

    assert payload["sub"] == "juan@example.com"
    assert payload["type"] == "access"
    assert isinstance(payload["jti"], str)
    assert payload["jti"]
    assert "exp" in payload


def test_dos_access_tokens_son_distintos():
    first = create_access_token({"sub": "juan@example.com"})
    second = create_access_token({"sub": "juan@example.com"})
    assert first != second


def test_password_reset_token_se_reconoce():
    token = create_password_reset_token("juan@example.com")
    payload = decode_token(token)

    assert payload["sub"] == "juan@example.com"
    assert payload["type"] == "password_reset"
    assert is_password_reset_token(token) is True


def test_access_token_no_es_password_reset_token():
    token = create_access_token({"sub": "juan@example.com"})
    assert is_password_reset_token(token) is False


def test_token_invalido_no_es_password_reset_token():
    assert is_password_reset_token("token-invalido") is False


def test_decode_token_invalido_lanza_error():
    with pytest.raises(JWTError):
        decode_token("token-invalido")
