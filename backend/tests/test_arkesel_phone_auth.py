"""Security and provider-contract tests for passwordless phone authentication."""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import time
from unittest.mock import AsyncMock, MagicMock, call

import pytest
import httpx
from fastapi.testclient import TestClient

from app.core.config import settings
from app.integrations.arkesel import (
    ArkeselSMSClient,
    ArkeselProviderError,
    SMSValidationError,
    verify_supabase_hook_signature,
)


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
@pytest.mark.parametrize("phone", ["+233241234567", "233241234567"])
async def test_arkesel_sender_uses_v2_contract_without_plus(
    monkeypatch: pytest.MonkeyPatch,
    phone: str,
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
        phone_e164=phone,
        otp="123456",
    )

    assert captured["url"] == "https://sms.arkesel.com/api/v2/sms/send"
    assert captured["headers"]["api-key"] == "test-main-key"
    assert captured["json"]["sender"] == "VeloxaHire"
    assert captured["json"]["recipients"] == ["+233241234567"]
    assert "123456" in captured["json"]["message"]


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "status_code,error_code",
    [(401, "arkesel_credentials_rejected"), (403, "arkesel_sender_or_account_not_authorized"), (429, "arkesel_rate_limited")],
)
async def test_arkesel_provider_failure_has_safe_diagnostic(
    monkeypatch: pytest.MonkeyPatch,
    status_code: int,
    error_code: str,
):
    response = MagicMock(status_code=status_code)
    response.json.return_value = {
        "message": "sender Veloxa is not approved for +233241234567",
        "otp": "123456",
    }
    transport = AsyncMock()
    transport.__aenter__.return_value = transport
    transport.post.return_value = response
    monkeypatch.setattr(settings, "ARKESEL_SMS_ENABLED", True)
    monkeypatch.setattr(settings, "ARKESEL_API_KEY", "test-main-key")
    monkeypatch.setattr(settings, "ARKESEL_SENDER_ID", "Veloxa")
    monkeypatch.setattr("app.integrations.arkesel.httpx.AsyncClient", MagicMock(return_value=transport))
    log = MagicMock()
    monkeypatch.setattr("app.integrations.arkesel.logger", log)

    with pytest.raises(ArkeselProviderError) as caught:
        await ArkeselSMSClient().send_auth_code(phone_e164="+233241234567", otp="123456")

    assert caught.value.error_code == error_code
    failure = log.error.call_args
    assert failure.args == ("arkesel_auth_sms_failed",)
    assert failure.kwargs["error_code"] == error_code
    assert "[redacted-number]" in failure.kwargs["response_body"]
    assert "123456" not in failure.kwargs["response_body"]


@pytest.mark.asyncio
async def test_arkesel_timeout_has_safe_diagnostic(monkeypatch: pytest.MonkeyPatch):
    transport = AsyncMock()
    transport.__aenter__.return_value = transport
    transport.post.side_effect = httpx.ReadTimeout("timed out")
    monkeypatch.setattr(settings, "ARKESEL_SMS_ENABLED", True)
    monkeypatch.setattr(settings, "ARKESEL_API_KEY", "test-main-key")
    monkeypatch.setattr(settings, "ARKESEL_SENDER_ID", "Veloxa")
    monkeypatch.setattr(settings, "ARKESEL_HTTP_TIMEOUT_SECONDS", 4.5)
    monkeypatch.setattr("app.integrations.arkesel.httpx.AsyncClient", MagicMock(return_value=transport))
    log = MagicMock()
    monkeypatch.setattr("app.integrations.arkesel.logger", log)

    with pytest.raises(ArkeselProviderError) as caught:
        await ArkeselSMSClient().send_auth_code(phone_e164="+233241234567", otp="123456")

    assert caught.value.error_code == "arkesel_timeout"
    assert log.error.call_args.kwargs == {"timeout_seconds": 4.5}


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "phone,otp,error_code",
    [
        ("0241234567", "123456", "invalid_phone_format"),
        ("++233241234567", "123456", "invalid_phone_format"),
        ("23324 1234567", "123456", "invalid_phone_format"),
        ("2332412345678901", "123456", "invalid_phone_format"),
        ("23324123456١", "123456", "invalid_phone_format"),
        ("233241234567", "123", "invalid_otp_format"),
        ("233241234567", "12345x", "invalid_otp_format"),
        ("233241234567", "١٢٣٤٥٦", "invalid_otp_format"),
    ],
)
async def test_arkesel_invalid_input_never_contacts_provider(
    monkeypatch: pytest.MonkeyPatch, phone: str, otp: str, error_code: str,
):
    transport = MagicMock()
    monkeypatch.setattr("app.integrations.arkesel.httpx.AsyncClient", transport)
    with pytest.raises(SMSValidationError) as caught:
        await ArkeselSMSClient().send_auth_code(phone_e164=phone, otp=otp)
    assert caught.value.error_code == error_code
    transport.assert_not_called()


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
@pytest.mark.parametrize("user,sms_fields", [
    ({"phone": "+233241234567"}, {}),
    ({"phone": "233241234567"}, {}),
    ({"phone": "", "new_phone": "233241234567"}, {"phone": "233241234567"}),
    ({"phone": "233201234567"}, {"phone": "233241234567"}),
    ({"phone": "", "new_phone": "233241234567"}, {}),
    ({"phone": "233201234567", "new_phone": "233241234567"}, {}),
    ({"phone": "233201234567", "new_phone": "233501234567"}, {"phone": "233241234567"}),
])
def test_send_sms_hook_delivers_verified_supabase_otp(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
    user: dict,
    sms_fields: dict,
):
    payload = {"user": user, "sms": {"otp": "012345", **sms_fields}}
    body = json.dumps(payload, separators=(",", ":")).encode()
    raw_secret = b"s" * 32
    monkeypatch.setattr(
        settings,
        "SUPABASE_SEND_SMS_HOOK_SECRETS",
        f"v1,whsec_{base64.b64encode(raw_secret).decode()}",
    )
    monkeypatch.setattr(settings, "ARKESEL_SMS_ENABLED", True)
    monkeypatch.setattr(settings, "ARKESEL_API_KEY", "test-main-key")
    monkeypatch.setattr(settings, "ARKESEL_SENDER_ID", "VeloxaHire")
    provider_response = MagicMock(status_code=200)
    provider_response.json.return_value = {"status": "success"}
    transport = AsyncMock()
    transport.__aenter__.return_value = transport
    transport.post.return_value = provider_response
    monkeypatch.setattr(
        "app.integrations.arkesel.httpx.AsyncClient",
        MagicMock(return_value=transport),
    )

    response = client.post(
        "/api/v1/auth/hooks/send-sms",
        content=body,
        headers=_signed_headers(body, raw_secret),
    )

    assert response.status_code == 200
    transport.post.assert_awaited_once()
    sms = transport.post.call_args.kwargs["json"]
    assert sms["recipients"] == ["+233241234567"]
    assert "012345" in sms["message"]


@pytest.mark.auth
@pytest.mark.parametrize("payload", [
    {"user": {"phone": "+233241234567"}, "sms": {}},
    {"user": {"phone": "+233241234567"}, "sms": {"otp": "012345", "phone": None}},
    {"user": {"phone": "+233241234567"}, "sms": {"otp": "012345", "phone": ""}},
    {"user": {"phone": "+233241234567"}, "sms": {"otp": "012345", "phone": 233241234567}},
    {"user": {"phone": "+233241234567"}, "sms": {"otp": 123456}},
    {"user": {"phone": "+233241234567", "new_phone": []}, "sms": {"otp": "012345"}},
    {"user": None, "sms": {"otp": "012345"}},
    {"sms": []},
    [],
])
def test_send_sms_hook_rejects_invalid_payload_after_signature(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
    payload,
):
    body = json.dumps(payload).encode()
    raw_secret = b"s" * 32
    monkeypatch.setattr(
        settings,
        "SUPABASE_SEND_SMS_HOOK_SECRETS",
        f"v1,whsec_{base64.b64encode(raw_secret).decode()}",
    )
    sender = AsyncMock()
    monkeypatch.setattr("app.api.v1.endpoints.auth.arkesel_sms.send_auth_code", sender)
    monkeypatch.setattr("app.api.v1.endpoints.auth.moolre_sms.send_auth_code", sender)

    response = client.post(
        "/api/v1/auth/hooks/send-sms",
        content=body,
        headers=_signed_headers(body, raw_secret),
    )

    assert response.status_code == 422
    assert response.json()["error"]["http_code"] == 422
    sender.assert_not_awaited()


@pytest.mark.auth
@pytest.mark.parametrize("validation_error", [True, False])
def test_send_sms_hook_logs_safe_failure_without_sensitive_values(
    client: TestClient, monkeypatch: pytest.MonkeyPatch, validation_error: bool,
):
    body = b'{"user":{"phone":"+233241234567"},"sms":{"otp":"012345"}}'
    raw_secret = b"s" * 32
    monkeypatch.setattr(
        settings, "SUPABASE_SEND_SMS_HOOK_SECRETS",
        f"v1,whsec_{base64.b64encode(raw_secret).decode()}",
    )
    monkeypatch.setattr(settings, "SMS_PROVIDERS", "arkesel")
    error = (
        SMSValidationError("invalid_phone_format") if validation_error
        else RuntimeError("sensitive provider response +233241234567 012345")
    )
    monkeypatch.setattr(
        "app.api.v1.endpoints.auth.arkesel_sms.send_auth_code",
        AsyncMock(side_effect=error),
    )
    log = MagicMock()
    monkeypatch.setattr("app.api.v1.endpoints.auth.logger", log)
    response = client.post(
        "/api/v1/auth/hooks/send-sms", content=body,
        headers=_signed_headers(body, raw_secret),
    )
    assert response.status_code == 502
    assert response.json()["error"]["message"] == "Could not send the verification code."
    assert call(
        "supabase_send_sms_provider_failed",
        provider="arkesel",
        error_type=type(error).__name__,
        error_code="invalid_phone_format" if validation_error else "sms_delivery_failed",
    ) in log.error.call_args_list
    assert call(
        "supabase_send_sms_hook_delivery_failed", providers=["arkesel"]
    ) in log.error.call_args_list
