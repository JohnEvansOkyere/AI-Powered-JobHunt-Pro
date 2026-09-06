"""Arkesel SMS delivery for Supabase phone-auth hooks."""

from __future__ import annotations

import base64
import hashlib
import hmac
import re
import time
from typing import Optional

import httpx

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)

ARKESEL_SMS_URL = "https://sms.arkesel.com/api/v2/sms/send"
WEBHOOK_TOLERANCE_SECONDS = 5 * 60
E164_RE = re.compile(r"^\+?[1-9][0-9]{7,14}$")


class SMSValidationError(ValueError):
    """Validation failure carrying a safe diagnostic code, never input values."""

    def __init__(self, error_code: str):
        self.error_code = error_code
        super().__init__(error_code)


class ArkeselProviderError(RuntimeError):
    """Provider failure carrying a safe diagnostic code for the hook log."""

    def __init__(self, error_code: str, message: str = "Arkesel rejected the SMS request"):
        self.error_code = error_code
        super().__init__(message)


def _safe_response_preview(response: httpx.Response) -> str:
    """Return a bounded provider response without exposing phone/OTP values."""
    try:
        value = response.json()
        if isinstance(value, dict):
            # Provider error payloads are useful for diagnosis, but never log
            # arbitrary nested data or values that could contain user inputs.
            value = {
                str(key): str(item)[:240]
                for key, item in value.items()
                if str(key).lower() not in {"phone", "recipient", "recipients", "otp", "api_key"}
            }
            preview = str(value)
        else:
            preview = str(value)
    except ValueError:
        preview = response.text
    preview = re.sub(r"\b\+?[0-9][0-9\s().-]{7,}\b", "[redacted-number]", preview)
    preview = re.sub(r"(?<![0-9])[0-9]{4,10}(?![0-9])", "[redacted-code]", preview)
    return preview[:500]


def _arkesel_http_error_code(status_code: int) -> str:
    if status_code == 401:
        return "arkesel_credentials_rejected"
    if status_code == 403:
        return "arkesel_sender_or_account_not_authorized"
    if status_code == 429:
        return "arkesel_rate_limited"
    if 400 <= status_code < 500:
        return "arkesel_request_rejected"
    if status_code >= 500:
        return "arkesel_provider_unavailable"
    return "arkesel_http_error"


def _hook_secret_values(configured: str) -> list[str]:
    """Return decoded-secret candidates from Supabase's rotation format."""
    values: list[str] = []
    for item in (configured or "").split("|"):
        value = item.strip()
        if value.startswith("v1,"):
            value = value[3:]
        if value.startswith("whsec_"):
            value = value[len("whsec_") :]
        if value:
            values.append(value)
    return values


def verify_supabase_hook_signature(
    body: bytes,
    *,
    webhook_id: Optional[str],
    webhook_timestamp: Optional[str],
    webhook_signature: Optional[str],
    secrets: str,
) -> bool:
    """Verify a Supabase HTTP Auth Hook using Standard Webhooks signing."""
    if not webhook_id or not webhook_timestamp or not webhook_signature:
        return False

    try:
        sent_at = int(webhook_timestamp)
    except (TypeError, ValueError):
        return False
    if abs(time.time() - sent_at) > WEBHOOK_TOLERANCE_SECONDS:
        return False

    signed_payload = b"%s.%s.%s" % (
        webhook_id.encode("utf-8"),
        webhook_timestamp.encode("utf-8"),
        body,
    )
    candidates = []
    for part in webhook_signature.split(" "):
        version, _, signature = part.partition(",")
        if version == "v1" and signature:
            candidates.append(signature)

    for secret in _hook_secret_values(secrets):
        try:
            key = base64.b64decode(secret, validate=True)
        except Exception:  # noqa: BLE001 - malformed configuration fails closed
            continue
        expected = base64.b64encode(
            hmac.new(key, signed_payload, hashlib.sha256).digest()
        ).decode("utf-8")
        if any(hmac.compare_digest(expected, candidate) for candidate in candidates):
            return True
    return False


class ArkeselSMSClient:
    """Minimal async client for Arkesel SMS API v2."""

    async def send_auth_code(self, *, phone_e164: str, otp: str) -> None:
        # Supabase Auth normalizes phone numbers by removing the leading '+'.
        # Accept both representations, keeping the country code mandatory.
        phone = (phone_e164 or "").strip()
        code = (otp or "").strip()
        if not E164_RE.fullmatch(phone):
            raise SMSValidationError("invalid_phone_format")
        if not re.fullmatch(r"[0-9]{4,10}", code):
            raise SMSValidationError("invalid_otp_format")
        if not settings.ARKESEL_SMS_ENABLED:
            raise RuntimeError("Arkesel SMS is disabled")
        if not settings.ARKESEL_API_KEY.strip() or not settings.ARKESEL_SENDER_ID.strip():
            raise ArkeselProviderError("arkesel_credentials_incomplete", "Arkesel SMS credentials are incomplete")

        message = (
            f"Your VeloxaHire verification code is {code}. "
            "It expires shortly. Do not share this code."
        )
        # Arkesel's v2 API expects recipients as international numbers. Keep
        # the leading '+' even when Supabase supplied its digits-only form.
        recipient = phone if phone.startswith("+") else f"+{phone}"
        payload = {
            "sender": settings.ARKESEL_SENDER_ID.strip(),
            "message": message,
            "recipients": [recipient],
        }
        async with httpx.AsyncClient(timeout=3.5) as client:
            response = await client.post(
                ARKESEL_SMS_URL,
                headers={
                    "api-key": settings.ARKESEL_API_KEY.strip(),
                    "Content-Type": "application/json",
                },
                json=payload,
            )

        if response.status_code != 200:
            error_code = _arkesel_http_error_code(response.status_code)
            logger.error(
                "arkesel_auth_sms_failed",
                status_code=response.status_code,
                error_code=error_code,
                response_body=_safe_response_preview(response),
            )
            raise ArkeselProviderError(error_code)

        try:
            result = response.json()
        except ValueError as exc:
            logger.error(
                "arkesel_auth_sms_invalid_response",
                status_code=response.status_code,
                response_body=_safe_response_preview(response),
            )
            raise ArkeselProviderError("arkesel_invalid_response", "Arkesel returned an invalid response") from exc
        if str(result.get("status", "")).lower() != "success":
            logger.error(
                "arkesel_auth_sms_unsuccessful",
                status_code=response.status_code,
                provider_status=str(result.get("status", ""))[:80],
                response_body=_safe_response_preview(response),
            )
            raise ArkeselProviderError("arkesel_request_unsuccessful")


arkesel_sms = ArkeselSMSClient()
