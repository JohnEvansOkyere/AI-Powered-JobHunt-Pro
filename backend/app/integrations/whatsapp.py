"""Meta WhatsApp Cloud API client (template sends + webhook signature verification)."""

from __future__ import annotations

import asyncio
import hashlib
import hmac
import json
import time
from typing import Any, Dict, List, Optional

import httpx

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)


def verify_webhook_signature(
    body: bytes,
    signature_header: Optional[str],
    *,
    app_secret: str,
) -> bool:
    """Verify ``X-Hub-Signature-256`` from Meta (HMAC-SHA256 over raw body)."""
    if not app_secret or not signature_header:
        return False
    if not signature_header.startswith("sha256="):
        return False
    expected = hmac.new(
        app_secret.encode("utf-8"),
        body,
        hashlib.sha256,
    ).hexdigest()
    received = signature_header[7:]
    try:
        return hmac.compare_digest(expected, received)
    except TypeError:
        return False


def phone_e164_to_whatsapp_digits(e164: str) -> str:
    """Strip ``+`` / spaces; Meta ``to`` field wants digits only."""
    return "".join(c for c in e164 if c.isdigit())


class WhatsappCloudClient:
    """Thin async wrapper around ``POST /{phone_number_id}/messages``."""

    def __init__(self) -> None:
        self._send_lock = asyncio.Lock()
        self._last_send_ts = 0.0

    def _base_url(self) -> str:
        ver = settings.WHATSAPP_GRAPH_API_VERSION.strip().lstrip("/")
        return f"https://graph.facebook.com/{ver}/{settings.WHATSAPP_PHONE_NUMBER_ID}"

    async def _throttle(self) -> None:
        """Client-side spacing so we never burst faster than ``WHATSAPP_PROVIDER_RPS``."""
        rps = max(1, int(settings.WHATSAPP_PROVIDER_RPS))
        min_interval = 1.0 / float(rps)
        async with self._send_lock:
            now = time.monotonic()
            wait = self._last_send_ts + min_interval - now
            if wait > 0:
                await asyncio.sleep(wait)
            self._last_send_ts = time.monotonic()

    async def send_template(
        self,
        *,
        to_e164: str,
        template_name: str,
        language_code: str = "en",
        body_parameters: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        Send a pre-approved Cloud API template.

        Returns the parsed JSON body from Meta. In ``dry_run`` mode no HTTP
        request is made; a synthetic response is returned so callers can
        exercise the full code path in CI.
        """
        to_digits = phone_e164_to_whatsapp_digits(to_e164)
        if len(to_digits) < 8:
            raise ValueError("Invalid destination phone (too few digits).")

        template: Dict[str, Any] = {
            "name": template_name,
            "language": {"code": language_code},
        }
        if body_parameters:
            template["components"] = [
                {
                    "type": "body",
                    "parameters": [{"type": "text", "text": str(p)} for p in body_parameters],
                }
            ]

        payload: Dict[str, Any] = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": to_digits,
            "type": "template",
            "template": template,
        }

        mode = settings.WHATSAPP_SEND_MODE
        if mode == "dry_run":
            logger.info(
                "whatsapp_send_dry_run",
                template=template_name,
                to_digits_prefix=to_digits[:5] + "***",
            )
            return {"messages": [{"id": "dry-run", "message_status": "accepted"}]}

        if not settings.WHATSAPP_ENABLED:
            raise RuntimeError(
                "WHATSAPP_ENABLED=false blocks live/sandbox sends. "
                "Use WHATSAPP_SEND_MODE=dry_run for no-network tests."
            )

        token = (settings.WHATSAPP_ACCESS_TOKEN or "").strip()
        if not token or not (settings.WHATSAPP_PHONE_NUMBER_ID or "").strip():
            raise RuntimeError("WHATSAPP_ACCESS_TOKEN and WHATSAPP_PHONE_NUMBER_ID must be set for live sends.")

        await self._throttle()
        url = f"{self._base_url()}/messages"
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(url, headers=headers, content=json.dumps(payload))
        try:
            data = resp.json()
        except Exception:
            data = {"raw": resp.text}

        if resp.status_code >= 400:
            logger.warning(
                "whatsapp_send_failed",
                status_code=resp.status_code,
                body=data,
            )
            raise httpx.HTTPStatusError(
                f"WhatsApp API error {resp.status_code}",
                request=resp.request,
                response=resp,
            )
        return data


_default_client: Optional[WhatsappCloudClient] = None


def get_whatsapp_client() -> WhatsappCloudClient:
    global _default_client
    if _default_client is None:
        _default_client = WhatsappCloudClient()
    return _default_client
