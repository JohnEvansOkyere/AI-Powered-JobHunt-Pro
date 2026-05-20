"""Celery tasks for WhatsApp Tier-1 recommendation digests."""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from celery.utils.log import get_task_logger

from app.core.config import settings
from app.core.database import SessionLocal
from app.services.whatsapp_digest import (
    WhatsappDigestDispatcher,
    WhatsappDigestSendError,
)
from app.tasks.celery_app import celery_app

logger = get_task_logger(__name__)


def _run_async(coro):
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


def _sending_enabled() -> bool:
    if settings.WHATSAPP_SEND_MODE == "dry_run":
        return True
    return bool(settings.WHATSAPP_ENABLED)


@celery_app.task(
    name="notifications.dispatch_whatsapp_digests",
    ignore_result=False,
)
def dispatch_whatsapp_digests() -> Dict[str, Any]:
    """Queue digest sends for opted-in users whose local digest time is due."""
    if not _sending_enabled():
        logger.info("whatsapp_digest_dispatch_disabled")
        return {"status": "disabled", "queued": 0}

    db = SessionLocal()
    try:
        dispatcher = WhatsappDigestDispatcher(db)
        due = dispatcher.due_users(datetime.now(timezone.utc))
        queued = 0
        errors = 0
        for item in due:
            try:
                send_whatsapp_digest.delay(item.user_id, local_date=item.local_date)
                queued += 1
            except Exception as exc:  # noqa: BLE001 - broker can be unavailable
                errors += 1
                logger.warning(
                    "whatsapp_digest_enqueue_failed",
                    user_id=item.user_id,
                    error=str(exc),
                )
        return {
            "status": "success",
            "due": len(due),
            "queued": queued,
            "errors": errors,
        }
    finally:
        db.close()


@celery_app.task(
    name="notifications.send_whatsapp_digest",
    bind=True,
    autoretry_for=(WhatsappDigestSendError,),
    retry_backoff=True,
    retry_backoff_max=300,
    retry_jitter=True,
    max_retries=3,
    acks_late=True,
    ignore_result=False,
)
def send_whatsapp_digest(
    self,
    user_id: str,
    *,
    local_date: Optional[str] = None,
) -> Dict[str, Any]:
    """Send one user's Tier-1 recommendation digest."""
    if not _sending_enabled():
        return {"status": "disabled", "user_id": user_id}

    db = SessionLocal()
    try:
        dispatcher = WhatsappDigestDispatcher(db)
        return _run_async(
            dispatcher.send_digest_for_user(user_id, local_date=local_date)
        )
    finally:
        db.close()
