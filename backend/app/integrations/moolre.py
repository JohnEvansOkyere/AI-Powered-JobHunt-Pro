"""Moolre SMS delivery for the Supabase phone-auth hook."""

from __future__ import annotations

import uuid

import httpx

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)


class MoolreSMSClient:
    async def send_auth_code(self, *, phone_e164: str, otp: str) -> None:
        if not settings.MOOLRE_SMS_ENABLED:
            raise RuntimeError("Moolre SMS is disabled")
        if not settings.MOOLRE_VAS_KEY.strip() or not settings.MOOLRE_SENDER_ID.strip():
            raise RuntimeError("Moolre SMS credentials are incomplete")

        payload = {
            "type": 1,
            "senderid": settings.MOOLRE_SENDER_ID.strip(),
            "messages": [
                {
                    "recipient": phone_e164.removeprefix("+"),
                    "message": (
                        f"Your VeloxaHire verification code is {otp}. "
                        "It expires shortly. Do not share this code."
                    ),
                    "ref": f"veloxahire-{uuid.uuid4()}",
                }
            ],
        }
        async with httpx.AsyncClient(timeout=3.5) as client:
            response = await client.post(
                settings.MOOLRE_API_URL.strip(),
                headers={"X-API-VASKEY": settings.MOOLRE_VAS_KEY.strip()},
                json=payload,
            )
        response.raise_for_status()
        try:
            result = response.json()
        except ValueError as exc:
            raise RuntimeError("Moolre returned an invalid response") from exc
        if str(result.get("status")) != "1":
            logger.error("moolre_auth_sms_unsuccessful", provider_code=str(result.get("code", "unknown")))
            raise RuntimeError("Moolre did not accept the SMS request")


moolre_sms = MoolreSMSClient()
