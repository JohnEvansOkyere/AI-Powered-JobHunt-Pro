"""Operator-only endpoints for ecosystem maintenance."""

from __future__ import annotations

import asyncio
from typing import Optional

from fastapi import APIRouter, Header, HTTPException, Request, status

from app.core.config import settings
from app.core.database import SessionLocal
from app.core.rate_limit import CRON_RATE_LIMIT, enforce_rate_limit
from app.services.ats_job_sync_service import ATSJobSyncService
from app.services.ats_sync_status_service import (
    get_sync_status_async,
    record_sync_failure_sync,
    record_sync_started_sync,
    record_sync_success_sync,
)

router = APIRouter()


def _verify_cron_secret(x_cron_secret: Optional[str]) -> None:
    if not settings.CRON_SECRET or x_cron_secret != settings.CRON_SECRET:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid cron secret.",
        )


def _run_full_ats_sync() -> dict:
    db = SessionLocal()
    try:
        record_sync_started_sync("manual")
        stats = ATSJobSyncService(db).sync(force_full=True)
        payload = stats.as_dict()
        record_sync_success_sync(payload, "manual")
        return payload
    except Exception as exc:
        db.rollback()
        record_sync_failure_sync(str(exc), "manual")
        raise
    finally:
        db.close()


@router.get("/ats-sync/status")
async def get_ats_sync_status(
    request: Request,
    x_cron_secret: Optional[str] = Header(default=None, alias="X-Cron-Secret"),
) -> dict:
    """Return last ATS mirror result and stale status for operator dashboards."""
    _verify_cron_secret(x_cron_secret)
    await enforce_rate_limit(request, CRON_RATE_LIMIT, subject="ats-sync-status")
    return await get_sync_status_async()


@router.post("/ats-sync/backfill")
async def backfill_ats_sync(
    request: Request,
    x_cron_secret: Optional[str] = Header(default=None, alias="X-Cron-Secret"),
) -> dict:
    """Force a full ATS job mirror pass, bypassing updated_since."""
    _verify_cron_secret(x_cron_secret)
    await enforce_rate_limit(request, CRON_RATE_LIMIT, subject="ats-sync-backfill")
    try:
        stats = await asyncio.to_thread(_run_full_ats_sync)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"ATS backfill failed: {exc}",
        ) from exc

    return {
        "status": "success",
        **stats,
        "sync_status": await get_sync_status_async(),
    }
