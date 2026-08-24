"""Resend transactional email client + webhook signature verification.

Shaped like :mod:`app.integrations.whatsapp`: a throttled async sender with a
``dry_run`` mode so CI and local dev run the whole code path without network
access or a verified sending domain.
"""

from __future__ import annotations

import asyncio
import base64
import hashlib
import hmac
import json
import time
from typing import Any, Dict, List, Optional

import httpx

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)

RESEND_API_URL = "https://api.resend.com/emails"

# Svix tolerates a 5-minute clock skew; anything older is a replay.
WEBHOOK_TOLERANCE_SECONDS = 5 * 60


def verify_webhook_signature(
    body: bytes,
    *,
    svix_id: Optional[str],
    svix_timestamp: Optional[str],
    svix_signature: Optional[str],
    secret: str,
) -> bool:
    """Verify a Resend (Svix) webhook signature.

    Svix signs ``{id}.{timestamp}.{body}`` with HMAC-SHA256 keyed by the
    base64 body of the ``whsec_`` secret, and sends the result base64-encoded
    in a space-separated ``v1,<sig>`` list (multiple entries during rotation).
    """
    if not secret or not svix_id or not svix_timestamp or not svix_signature:
        return False

    try:
        sent_at = int(svix_timestamp)
    except (TypeError, ValueError):
        return False
    if abs(time.time() - sent_at) > WEBHOOK_TOLERANCE_SECONDS:
        return False

    raw_secret = secret.strip()
    if raw_secret.startswith("whsec_"):
        raw_secret = raw_secret[len("whsec_") :]
    try:
        key = base64.b64decode(raw_secret)
    except Exception:  # noqa: BLE001 - malformed secret is a config error
        return False

    signed_payload = b"%s.%s.%s" % (
        svix_id.encode("utf-8"),
        svix_timestamp.encode("utf-8"),
        body,
    )
    expected = base64.b64encode(
        hmac.new(key, signed_payload, hashlib.sha256).digest()
    ).decode("utf-8")

    for part in svix_signature.split(" "):
        version, _, candidate = part.partition(",")
        if version != "v1" or not candidate:
            continue
        if hmac.compare_digest(expected, candidate):
            return True
    return False


class ResendClient:
    """Thin async wrapper around ``POST https://api.resend.com/emails``."""

    def __init__(self) -> None:
        self._send_lock = asyncio.Lock()
        self._last_send_ts = 0.0

    async def _throttle(self) -> None:
        """Client-side spacing so we never burst past ``EMAIL_PROVIDER_RPS``."""
        rps = max(1, int(settings.EMAIL_PROVIDER_RPS))
        min_interval = 1.0 / float(rps)
        async with self._send_lock:
            now = time.monotonic()
            wait = self._last_send_ts + min_interval - now
            if wait > 0:
                await asyncio.sleep(wait)
            self._last_send_ts = time.monotonic()

    def _from_header(self) -> str:
        name = (settings.EMAIL_FROM_NAME or "").strip()
        address = (settings.EMAIL_FROM_ADDRESS or "").strip()
        return f"{name} <{address}>" if name else address

    async def send_email(
        self,
        *,
        to: str,
        subject: str,
        html: str,
        text: str,
        headers: Optional[Dict[str, str]] = None,
        tags: Optional[List[Dict[str, str]]] = None,
    ) -> Dict[str, Any]:
        """Send one email.

        Returns Resend's parsed JSON body (``{"id": ...}``). In ``dry_run``
        mode no HTTP request is made and a synthetic response is returned.
        """
        recipient = (to or "").strip()
        if "@" not in recipient:
            raise ValueError("Invalid destination email address.")

        payload: Dict[str, Any] = {
            "from": self._from_header(),
            "to": [recipient],
            "subject": subject,
            "html": html,
            "text": text,
        }
        if settings.EMAIL_REPLY_TO.strip():
            payload["reply_to"] = settings.EMAIL_REPLY_TO.strip()
        if headers:
            payload["headers"] = headers
        if tags:
            payload["tags"] = tags

        if settings.EMAIL_SEND_MODE == "dry_run":
            local, _, domain = recipient.partition("@")
            logger.info(
                "email_send_dry_run",
                subject=subject,
                to=f"{local[:2]}***@{domain}",
                html_bytes=len(html),
            )
            return {"id": "dry-run"}

        if not settings.EMAIL_ENABLED:
            raise RuntimeError(
                "EMAIL_ENABLED=false blocks live sends. "
                "Use EMAIL_SEND_MODE=dry_run for no-network tests."
            )

        api_key = (settings.RESEND_API_KEY or "").strip()
        if not api_key:
            raise RuntimeError("RESEND_API_KEY must be set for live sends.")

        await self._throttle()
        request_headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(
                RESEND_API_URL,
                headers=request_headers,
                content=json.dumps(payload),
            )
        try:
            data = resp.json()
        except Exception:  # noqa: BLE001 - provider may return non-JSON on 5xx
            data = {"raw": resp.text}

        if resp.status_code >= 400:
            logger.warning(
                "email_send_failed",
                status_code=resp.status_code,
                body=data,
            )
            raise httpx.HTTPStatusError(
                f"Resend API error {resp.status_code}",
                request=resp.request,
                response=resp,
            )
        return data


_default_client: Optional[ResendClient] = None


def get_email_client() -> ResendClient:
    global _default_client
    if _default_client is None:
        _default_client = ResendClient()
    return _default_client
