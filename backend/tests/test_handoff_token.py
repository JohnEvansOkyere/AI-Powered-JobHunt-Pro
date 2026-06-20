from datetime import datetime, timedelta, timezone

import pytest
from jose import JWTError, jwt

from app.api.v1.endpoints import auth


def _handoff_payload(**overrides):
    now = datetime.now(timezone.utc)
    payload = {
        "email": "candidate@example.com",
        "full_name": "Candidate One",
        "phone": "+233200000000",
        "job_id": "11111111-1111-1111-1111-111111111111",
        "purpose": auth.HANDOFF_TOKEN_PURPOSE,
        "iss": auth.HANDOFF_TOKEN_ISSUER,
        "aud": auth.HANDOFF_TOKEN_AUDIENCE,
        "iat": now,
        "exp": now + timedelta(minutes=15),
    }
    payload.update(overrides)
    return payload


def test_decode_handoff_token_accepts_valid_ats_payload(monkeypatch):
    monkeypatch.setattr(auth.settings, "HANDOFF_TOKEN_SECRET", "handoff-secret-123")
    monkeypatch.setattr(auth.settings, "PREVIOUS_HANDOFF_TOKEN_SECRET", "")
    token = jwt.encode(_handoff_payload(), "handoff-secret-123", algorithm="HS256")

    payload = auth._decode_handoff_token(token)

    assert payload["email"] == "candidate@example.com"
    assert payload["purpose"] == auth.HANDOFF_TOKEN_PURPOSE
    assert payload["aud"] == auth.HANDOFF_TOKEN_AUDIENCE


def test_decode_handoff_token_rejects_wrong_audience(monkeypatch):
    monkeypatch.setattr(auth.settings, "HANDOFF_TOKEN_SECRET", "handoff-secret-123")
    monkeypatch.setattr(auth.settings, "PREVIOUS_HANDOFF_TOKEN_SECRET", "")
    token = jwt.encode(
        _handoff_payload(aud="other-app"),
        "handoff-secret-123",
        algorithm="HS256",
    )

    with pytest.raises(JWTError):
        auth._decode_handoff_token(token)
