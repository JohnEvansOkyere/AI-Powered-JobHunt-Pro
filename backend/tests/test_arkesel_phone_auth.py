"""Security and provider-contract tests for passwordless phone authentication."""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import time
from unittest.mock import AsyncMock

import pytest
from fastapi.testclient import TestClient

from app.core.config import settings
from app.integrations.arkesel import ArkeselSMSClient, verify_supabase_hook_signature


def _signed_headers(body: bytes, raw_secret: bytes) -> dict[str, str]:
    webhook_id = "msg_phone_auth_test"
    timestamp = str(int(time.time()))
    signed = b"%s.%s.%s" % (webhook_id.encode(), timestamp.encode(), body)
    signature = base64.b64encode(
        hmac.new(raw_secret, signed, hashlib.sha256).digest()
    ).decode()
    return {
        "webhook-id": webhook_id,
        "webhook-timestamp": timestamp,
        "webhook-signature": f"v1,{signature}",
        "content-type": "application/json",
    }


def test_supabase_hook_signature_accepts_prefixed_rotation_secret():
    body = b'{"user":{"phone":"+233241234567"},"sms":{"otp":"123456"}}'
    raw_secret = b"s" * 32
    encoded = base64.b64encode(raw_secret).decode()
    headers = _signed_headers(body, raw_secret)

    assert verify_supabase_hook_signature(
        body,
        webhook_id=headers["webhook-id"],
        webhook_timestamp=headers["webhook-timestamp"],
        webhook_signature=headers["webhook-signature"],
        secrets=f"v1,whsec_{encoded}|v1,whsec_{base64.b64encode(b'x' * 32).decode()}",
    )


def test_supabase_hook_signature_rejects_tampered_body():
    body = b'{"user":{"phone":"+233241234567"},"sms":{"otp":"123456"}}'
    raw_secret = b"s" * 32
    headers = _signed_headers(body, raw_secret)

    assert not verify_supabase_hook_signature(
        body.replace(b"123456", b"654321"),
        webhook_id=headers["webhook-id"],
        webhook_timestamp=headers["webhook-timestamp"],
        webhook_signature=headers["webhook-signature"],
        secrets=f"v1,whsec_{base64.b64encode(raw_secret).decode()}",
    )


@pytest.mark.asyncio
async def test_arkesel_sender_uses_v2_contract_without_plus(
    monkeypatch: pytest.MonkeyPatch,
):
    captured: dict = {}

    class FakeResponse:
        status_code = 200

        @staticmethod
        def json():
            return {"status": "success", "data": []}

    class FakeAsyncClient:
        def __init__(self, *, timeout: float):
            captured["timeout"] = timeout

        async def __aenter__(self):
            return self

        async def __aexit__(self, *_args):
            return None

        async def post(self, url: str, *, headers: dict, json: dict):
            captured.update(url=url, headers=headers, json=json)
            return FakeResponse()

    monkeypatch.setattr(settings, "ARKESEL_SMS_ENABLED", True)
    monkeypatch.setattr(settings, "ARKESEL_API_KEY", "test-main-key")
    monkeypatch.setattr(settings, "ARKESEL_SENDER_ID", "VeloxaHire")
    monkeypatch.setattr("app.integrations.arkesel.httpx.AsyncClient", FakeAsyncClient)

    await ArkeselSMSClient().send_auth_code(
        phone_e164="+233241234567",
        otp="123456",
    )

    assert captured["url"] == "https://sms.arkesel.com/api/v2/sms/send"
    assert captured["headers"]["api-key"] == "test-main-key"
    assert captured["json"]["sender"] == "VeloxaHire"
    assert captured["json"]["recipients"] == ["233241234567"]
    assert "123456" in captured["json"]["message"]


@pytest.mark.asyncio
async def test_arkesel_sender_fails_closed_when_disabled(
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.setattr(settings, "ARKESEL_SMS_ENABLED", False)
    with pytest.raises(RuntimeError, match="disabled"):
        await ArkeselSMSClient().send_auth_code(
            phone_e164="+233241234567",
            otp="123456",
        )


@pytest.mark.auth
def test_send_sms_hook_rejects_unsigned_request(client: TestClient):
    response = client.post(
        "/api/v1/auth/hooks/send-sms",
        json={"user": {"phone": "+233241234567"}, "sms": {"otp": "123456"}},
    )
    assert response.status_code == 401


@pytest.mark.auth
def test_send_sms_hook_delivers_verified_supabase_otp(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
):
    payload = {"user": {"phone": "+233241234567"}, "sms": {"otp": "123456"}}
    body = json.dumps(payload, separators=(",", ":")).encode()
    raw_secret = b"s" * 32
    monkeypatch.setattr(
        settings,
        "SUPABASE_SEND_SMS_HOOK_SECRETS",
        f"v1,whsec_{base64.b64encode(raw_secret).decode()}",
    )
    send = AsyncMock(return_value=None)
    monkeypatch.setattr(
        "app.api.v1.endpoints.auth.arkesel_sms.send_auth_code",
        send,
    )

    response = client.post(
        "/api/v1/auth/hooks/send-sms",
        content=body,
        headers=_signed_headers(body, raw_secret),
    )

    assert response.status_code == 200
    send.assert_awaited_once_with(phone_e164="+233241234567", otp="123456")


@pytest.mark.auth
def test_send_sms_hook_rejects_invalid_payload_after_signature(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
):
    body = b'{"user":{"phone":"+233241234567"},"sms":{}}'
    raw_secret = b"s" * 32
    monkeypatch.setattr(
        settings,
        "SUPABASE_SEND_SMS_HOOK_SECRETS",
        f"v1,whsec_{base64.b64encode(raw_secret).decode()}",
    )

    response = client.post(
        "/api/v1/auth/hooks/send-sms",
        content=body,
        headers=_signed_headers(body, raw_secret),
    )

    assert response.status_code == 422
    assert response.json()["error"]["http_code"] == 422
