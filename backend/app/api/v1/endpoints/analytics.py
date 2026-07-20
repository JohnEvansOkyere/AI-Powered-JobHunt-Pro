"""Public first-party analytics ingestion."""

from __future__ import annotations

import json
import re
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, Optional
from urllib.parse import urlparse

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.api.v1.dependencies import get_optional_user
from app.core.database import get_db
from app.core.rate_limit import ANALYTICS_INGEST_RATE_LIMIT, enforce_rate_limit
from app.models.analytics import AnalyticsEvent, AnalyticsSession

router = APIRouter()
EVENT_NAME_RE = re.compile(r"^[a-z][a-z0-9_]{1,59}$")


class AnalyticsEventIn(BaseModel):
    session_id: str = Field(min_length=36, max_length=80)
    anonymous_id: str = Field(min_length=16, max_length=80)
    event_name: str = Field(min_length=2, max_length=60)
    path: str = Field(min_length=1, max_length=500)
    referrer: Optional[str] = Field(default=None, max_length=1000)
    target: Optional[str] = Field(default=None, max_length=1000)
    label: Optional[str] = Field(default=None, max_length=300)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    duration_ms: Optional[int] = Field(default=None, ge=0, le=3_600_000)
    user_agent: Optional[str] = Field(default=None, max_length=1000)


def _clean_metadata(value: Dict[str, Any]) -> Dict[str, Any]:
    """Keep analytics metadata small and JSON-safe."""
    cleaned: Dict[str, Any] = {}
    for key, item in list(value.items())[:20]:
        if not isinstance(key, str) or len(key) > 80:
            continue
        if isinstance(item, (str, int, float, bool)) or item is None:
            cleaned[key] = str(item)[:500] if isinstance(item, str) else item
    try:
        if len(json.dumps(cleaned, separators=(",", ":"))) > 4000:
            return {}
    except (TypeError, ValueError):
        return {}
    return cleaned


def _attribution(metadata: Dict[str, Any], referrer: Optional[str]) -> Dict[str, Optional[str]]:
    """Resolve campaign tags first, then infer a useful source from referrer."""
    def clean(value: Any, limit: int = 160) -> Optional[str]:
        if value is None:
            return None
        value = str(value).strip().lower()
        return value[:limit] if value else None

    source = clean(metadata.get("utm_source") or metadata.get("source"), 80)
    medium = clean(metadata.get("utm_medium") or metadata.get("medium"), 80)
    campaign = clean(metadata.get("utm_campaign") or metadata.get("campaign"))
    content = clean(metadata.get("utm_content") or metadata.get("content"))
    term = clean(metadata.get("utm_term") or metadata.get("term"))

    if not source and referrer:
        host = (urlparse(referrer).hostname or "").lower().removeprefix("www.")
        if "google." in host or "bing." in host or "duckduckgo." in host:
            source, medium = host.split(".", 1)[0], medium or "organic"
        elif "linkedin." in host:
            source, medium = "linkedin", medium or "social"
        elif host in {"t.co", "twitter.com", "x.com"}:
            source, medium = "x", medium or "social"
        elif "reddit." in host:
            source, medium = "reddit", medium or "social"
        elif host:
            source, medium = host, medium or "referral"
        else:
            source, medium = "direct", medium or "none"
    elif not source:
        source, medium = "direct", medium or "none"

    return {
        "source": source,
        "medium": medium or "unknown",
        "campaign": campaign,
        "content": content,
        "term": term,
    }


@router.post("/events", status_code=202)
async def ingest_event(
    payload: AnalyticsEventIn,
    request: Request,
    current_user: Optional[dict] = Depends(get_optional_user),
    db: Session = Depends(get_db),
) -> dict:
    """Record one browser event for both anonymous and authenticated visitors."""
    await enforce_rate_limit(request, ANALYTICS_INGEST_RATE_LIMIT)

    if not EVENT_NAME_RE.fullmatch(payload.event_name):
        return {"accepted": False}

    try:
        session_id = uuid.UUID(payload.session_id)
    except ValueError:
        return {"accepted": False}

    user_id = None
    if current_user and current_user.get("id"):
        try:
            user_id = uuid.UUID(str(current_user["id"]))
        except ValueError:
            user_id = None

    now = datetime.now(timezone.utc)
    attribution = _attribution(payload.metadata, payload.referrer)
    session = db.query(AnalyticsSession).filter(AnalyticsSession.id == session_id).first()
    if session is None:
        session = AnalyticsSession(
            id=session_id,
            anonymous_id=payload.anonymous_id,
            user_id=user_id,
            landing_path=payload.path,
            last_path=payload.path,
            referrer=payload.referrer,
            acquisition_source=attribution["source"],
            acquisition_medium=attribution["medium"],
            acquisition_campaign=attribution["campaign"],
            acquisition_content=attribution["content"],
            acquisition_term=attribution["term"],
            user_agent=payload.user_agent,
            page_views=0,
            event_count=0,
            engaged_seconds=0,
            first_seen_at=now,
            last_seen_at=now,
        )
        db.add(session)
    else:
        if user_id:
            session.user_id = user_id
        session.last_path = payload.path
        session.last_seen_at = now
        session.ended_at = None
        if payload.user_agent and not session.user_agent:
            session.user_agent = payload.user_agent
        if not session.acquisition_source:
            session.acquisition_source = attribution["source"]
            session.acquisition_medium = attribution["medium"]
            session.acquisition_campaign = attribution["campaign"]
            session.acquisition_content = attribution["content"]
            session.acquisition_term = attribution["term"]

    if payload.event_name in {"page_view", "jobs_page_view", "job_detail_view"}:
        session.page_views = (session.page_views or 0) + 1
    if payload.event_name in {"page_exit", "page_heartbeat"} and payload.duration_ms:
        session.engaged_seconds = (session.engaged_seconds or 0) + min(
            payload.duration_ms // 1000, 3600
        )
    session.event_count = (session.event_count or 0) + 1

    db.add(
        AnalyticsEvent(
            session_id=session_id,
            anonymous_id=payload.anonymous_id,
            user_id=user_id,
            event_name=payload.event_name,
            path=payload.path,
            referrer=payload.referrer,
            target=payload.target,
            label=payload.label,
            event_metadata=_clean_metadata(payload.metadata),
            duration_ms=payload.duration_ms,
            user_agent=payload.user_agent,
            occurred_at=now,
        )
    )
    db.commit()
    return {"accepted": True}
