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
        "jti": "handoff-token-id",
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


def test_decode_handoff_token_rejects_missing_jti(monkeypatch):
    monkeypatch.setattr(auth.settings, "HANDOFF_TOKEN_SECRET", "handoff-secret-123")
    monkeypatch.setattr(auth.settings, "PREVIOUS_HANDOFF_TOKEN_SECRET", "")
    payload = _handoff_payload()
    payload.pop("jti")
    token = jwt.encode(payload, "handoff-secret-123", algorithm="HS256")

    with pytest.raises(JWTError):
        auth._decode_handoff_token(token)


@pytest.mark.asyncio
async def test_consume_handoff_jti_rejects_replay(monkeypatch):
    class FakeRedis:
        def __init__(self):
            self.keys = set()

        async def set(self, key, value, ex=None, nx=False):
            if nx and key in self.keys:
                return None
            self.keys.add(key)
            return True

    fake_redis = FakeRedis()

    async def fake_get_async_redis():
        return fake_redis

    monkeypatch.setattr(auth, "get_async_redis", fake_get_async_redis)
    claims = _handoff_payload()

    await auth._consume_handoff_jti(claims)
    with pytest.raises(JWTError):
        await auth._consume_handoff_jti(claims)
