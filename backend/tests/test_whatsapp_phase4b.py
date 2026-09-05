"""Phase 4b: WhatsApp client + webhook verification (no Meta network)."""

from __future__ import annotations

import hashlib
import hmac
import json
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi.testclient import TestClient

from app.api.v1.endpoints import whatsapp as wa_module
from app.core.config import settings
from app.core.database import get_db
from app.integrations.whatsapp import (
    WhatsappCloudClient,
    sandbox_recipient_digits,
    verify_webhook_signature,
)
from app.main import app


def test_verify_webhook_signature_ok():
    secret = "test-secret"
    body = b'{"object":"whatsapp_business_account"}'
    sig = "sha256=" + hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
    assert verify_webhook_signature(body, sig, app_secret=secret) is True


def test_verify_webhook_signature_bad():
    secret = "test-secret"
    body = b'{"object":"whatsapp_business_account"}'
    assert verify_webhook_signature(body, "sha256=deadbeef", app_secret=secret) is False
    assert verify_webhook_signature(body, None, app_secret=secret) is False


@pytest.mark.asyncio
async def test_send_template_dry_run_no_network(monkeypatch):
    monkeypatch.setattr(settings, "WHATSAPP_SEND_MODE", "dry_run")
    monkeypatch.setattr(settings, "WHATSAPP_ENABLED", False)
    client = WhatsappCloudClient()
    out = await client.send_template(
        to_e164="+15551234567",
        template_name="otp_verification",
        body_parameters=["123456"],
    )
    assert out["messages"][0]["id"] == "dry-run"


def test_sandbox_recipient_allowlist_normalizes_numbers():
    assert sandbox_recipient_digits("+233 24 123 4567, +44-7700-900123") == {
        "233241234567",
        "447700900123",
    }


@pytest.mark.asyncio
async def test_sandbox_blocks_recipient_outside_allowlist(monkeypatch):
    monkeypatch.setattr(settings, "WHATSAPP_SEND_MODE", "sandbox")
    monkeypatch.setattr(settings, "WHATSAPP_ENABLED", True)
    monkeypatch.setattr(settings, "WHATSAPP_SANDBOX_RECIPIENTS", "+233241111111")
    client = WhatsappCloudClient()

    with pytest.raises(RuntimeError, match="Sandbox send blocked"):
        await client.send_template(
            to_e164="+233242222222",
            template_name="daily_job_digest",
        )


def test_map_meta_status():
    assert wa_module._map_meta_status("pending") == "queued"
    assert wa_module._map_meta_status("sent") == "sent"
    assert wa_module._map_meta_status("delivered") == "delivered"
    assert wa_module._map_meta_status("read") == "read"
    assert wa_module._map_meta_status("unknown") == "failed"


def test_webhook_verify_challenge(monkeypatch):
    monkeypatch.setattr(settings, "WHATSAPP_VERIFY_TOKEN", "my-test-token")
    c = TestClient(app)
    r = c.get(
        "/api/v1/webhooks/whatsapp",
        params={
            "hub.mode": "subscribe",
            "hub.verify_token": "my-test-token",
            "hub.challenge": "1234567890",
        },
    )
    assert r.status_code == 200
    assert r.text == "1234567890"


def test_webhook_verify_rejects_bad_token(monkeypatch):
    monkeypatch.setattr(settings, "WHATSAPP_VERIFY_TOKEN", "good")
    c = TestClient(app)
    r = c.get(
        "/api/v1/webhooks/whatsapp",
        params={
            "hub.mode": "subscribe",
            "hub.verify_token": "bad",
            "hub.challenge": "x",
        },
    )
    assert r.status_code == 403


def test_webhook_post_rejects_bad_hmac(monkeypatch):
    monkeypatch.setattr(settings, "WHATSAPP_APP_SECRET", "s3cr3t")
    c = TestClient(app)
    body = json.dumps({"object": "whatsapp_business_account", "entry": []})
    r = c.post(
        "/api/v1/webhooks/whatsapp",
        content=body,
        headers={"X-Hub-Signature-256": "sha256=invalid"},
    )
    assert r.status_code == 403


def test_webhook_post_fails_closed_without_app_secret(monkeypatch):
    monkeypatch.setattr(settings, "WHATSAPP_APP_SECRET", "")
    c = TestClient(app)
    r = c.post(
        "/api/v1/webhooks/whatsapp",
        json={"object": "whatsapp_business_account", "entry": []},
    )
    assert r.status_code == 503


def test_webhook_post_accepts_good_hmac(monkeypatch):
    secret = "s3cr3t"
    monkeypatch.setattr(settings, "WHATSAPP_APP_SECRET", secret)
    monkeypatch.setattr(wa_module, "_process_whatsapp_value", AsyncMock())

    def _mock_db():
        yield MagicMock()

    app.dependency_overrides[get_db] = _mock_db
    try:
        c = TestClient(app)
        body = json.dumps({"object": "whatsapp_business_account", "entry": []})
        sig = "sha256=" + hmac.new(secret.encode(), body.encode(), hashlib.sha256).hexdigest()
        r = c.post(
            "/api/v1/webhooks/whatsapp",
            content=body,
            headers={"X-Hub-Signature-256": sig, "Content-Type": "application/json"},
        )
        assert r.status_code == 200
        assert r.json().get("detail") == "ok"
    finally:
        app.dependency_overrides.pop(get_db, None)
