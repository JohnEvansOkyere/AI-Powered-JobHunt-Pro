from datetime import datetime, timedelta, timezone

import pytest
from fastapi import HTTPException
from jose import jwt

from app.api.v1 import dependencies


def _access_token(secret: str, **overrides):
    now = datetime.now(timezone.utc)
    payload = {
        "sub": "11111111-1111-1111-1111-111111111111",
        "email": "candidate@example.com",
        "aud": "authenticated",
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(minutes=15)).timestamp()),
    }
    payload.update(overrides)
    return jwt.encode(payload, secret, algorithm="HS256")


def test_local_auth_verifier_prefers_canonical_auth_secret(monkeypatch):
    monkeypatch.setattr(dependencies.settings, "AUTH_SUPABASE_JWT_SECRET", "canonical-auth-secret")
    monkeypatch.setattr(dependencies.settings, "SUPABASE_JWT_SECRET", "veloxahire-data-secret")

    token = _access_token("canonical-auth-secret")

    user = dependencies._verify_supabase_jwt_locally(token)

    assert user["id"] == "11111111-1111-1111-1111-111111111111"
    assert user["email"] == "candidate@example.com"


def test_local_auth_verifier_rejects_data_project_token_when_canonical_auth_is_set(monkeypatch):
    monkeypatch.setattr(dependencies.settings, "AUTH_SUPABASE_JWT_SECRET", "canonical-auth-secret")
    monkeypatch.setattr(dependencies.settings, "SUPABASE_JWT_SECRET", "veloxahire-data-secret")

    token = _access_token("veloxahire-data-secret")

    with pytest.raises(HTTPException):
        dependencies._verify_supabase_jwt_locally(token)
