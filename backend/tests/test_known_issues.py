from __future__ import annotations

from datetime import datetime

import pytest
from jose import jwt

import app.core.security as security


@pytest.mark.unit
def test_access_tokens_created_same_second_are_unique(monkeypatch):
    class FixedDateTime(datetime):
        @classmethod
        def utcnow(cls):
            return cls(2026, 7, 22, 18, 0, 0)

    monkeypatch.setattr(security, "datetime", FixedDateTime)

    first = security.create_access_token({"sub": "usuario@example.com"})
    second = security.create_access_token({"sub": "usuario@example.com"})

    assert first != second

    first_payload = jwt.get_unverified_claims(first)
    second_payload = jwt.get_unverified_claims(second)

    assert first_payload["jti"] != second_payload["jti"]
    assert first_payload["type"] == "access"
    assert second_payload["type"] == "access"
