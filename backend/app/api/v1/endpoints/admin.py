"""Administrator dashboard and product analytics API."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy import distinct, func
from sqlalchemy.orm import Session

from app.api.v1.dependencies import require_admin
from app.core.database import get_db
from app.models.analytics import AnalyticsEvent, AnalyticsSession
from app.models.application import Application
from app.models.job import Job
from app.models.user import User
from app.models.user_profile import UserProfile
from app.services.ats_sync_status_service import get_sync_status_async

router = APIRouter()


def _range_start(days: int) -> datetime:
    return datetime.now(timezone.utc) - timedelta(days=max(1, min(days, 90)))


def _count(query) -> int:
    return int(query.scalar() or 0)


def _iso(value: Any) -> Optional[str]:
    return value.isoformat() if value else None


@router.get("/me")
async def admin_me(current_user: dict = Depends(require_admin)) -> dict:
    return {"is_admin": True, "email": current_user.get("email")}


@router.get("/overview")
async def admin_overview(
    days: int = Query(default=30, ge=1, le=90),
    db: Session = Depends(get_db),
    _admin: dict = Depends(require_admin),
) -> dict:
    start = _range_start(days)
    event_scope = db.query(AnalyticsEvent).filter(AnalyticsEvent.occurred_at >= start)
    session_scope = db.query(AnalyticsSession).filter(AnalyticsSession.first_seen_at >= start)

    job_page_events = {"jobs_page_view", "job_detail_view"}
    signup_events = {"signup_completed"}
    job_sessions = (
        db.query(distinct(AnalyticsEvent.session_id))
        .filter(
            AnalyticsEvent.occurred_at >= start,
            AnalyticsEvent.event_name.in_(job_page_events),
        )
        .subquery()
    )
    converted_sessions = (
        db.query(distinct(AnalyticsEvent.session_id))
        .filter(
            AnalyticsEvent.occurred_at >= start,
            AnalyticsEvent.event_name.in_(signup_events),
        )
        .subquery()
    )

    unique_visitors = _count(session_scope.with_entities(func.count(distinct(AnalyticsSession.anonymous_id))))
    authenticated_visitors = _count(
        session_scope.filter(AnalyticsSession.user_id.isnot(None)).with_entities(
            func.count(distinct(AnalyticsSession.user_id))
        )
    )
    sessions = _count(session_scope.with_entities(func.count(AnalyticsSession.id)))
    page_views = _count(event_scope.filter(AnalyticsEvent.event_name.in_(job_page_events | {"page_view"})).with_entities(func.count(AnalyticsEvent.id)))
    anonymous_job_sessions = _count(
        session_scope.filter(
            AnalyticsSession.user_id.is_(None),
            AnalyticsSession.id.in_(job_sessions),
            ~AnalyticsSession.id.in_(converted_sessions),
        ).with_entities(func.count(AnalyticsSession.id))
    )
    engaged_seconds = _count(session_scope.with_entities(func.sum(AnalyticsSession.engaged_seconds)))

    daily_rows = (
        event_scope.with_entities(
            func.date_trunc("day", AnalyticsEvent.occurred_at).label("day"),
            func.count(distinct(AnalyticsEvent.session_id)).label("sessions"),
            func.count(AnalyticsEvent.id).label("events"),
        )
        .group_by("day")
        .order_by("day")
        .all()
    )
    path_rows = (
        event_scope.filter(AnalyticsEvent.event_name.in_(job_page_events | {"page_view"}))
        .with_entities(AnalyticsEvent.path, func.count(AnalyticsEvent.id).label("count"))
        .group_by(AnalyticsEvent.path)
        .order_by(func.count(AnalyticsEvent.id).desc())
        .limit(12)
        .all()
    )
    click_rows = (
        event_scope.filter(AnalyticsEvent.event_name == "click", AnalyticsEvent.target.isnot(None))
        .with_entities(AnalyticsEvent.target, AnalyticsEvent.label, func.count(AnalyticsEvent.id).label("count"))
        .group_by(AnalyticsEvent.target, AnalyticsEvent.label)
        .order_by(func.count(AnalyticsEvent.id).desc())
        .limit(10)
        .all()
    )
    job_rows = (
        event_scope.filter(AnalyticsEvent.event_name == "job_detail_view")
        .with_entities(AnalyticsEvent.path, func.count(AnalyticsEvent.id).label("views"))
        .group_by(AnalyticsEvent.path)
        .order_by(func.count(AnalyticsEvent.id).desc())
        .limit(10)
        .all()
    )
    source_expr = func.coalesce(AnalyticsSession.acquisition_source, "direct").label("source")
    medium_expr = func.coalesce(AnalyticsSession.acquisition_medium, "none").label("medium")
    campaign_expr = func.coalesce(AnalyticsSession.acquisition_campaign, "").label("campaign")
    acquisition_rows = (
        session_scope.outerjoin(
            AnalyticsEvent,
            (AnalyticsEvent.session_id == AnalyticsSession.id)
            & (AnalyticsEvent.occurred_at >= start),
        )
        .with_entities(
            source_expr,
            medium_expr,
            campaign_expr,
            func.count(distinct(AnalyticsSession.id)).label("sessions"),
            func.count(distinct(AnalyticsSession.anonymous_id)).label("visitors"),
            func.count(distinct(AnalyticsEvent.id)).filter(
                AnalyticsEvent.event_name.in_(job_page_events)
            ).label("job_views"),
            func.count(distinct(AnalyticsEvent.id)).filter(
                AnalyticsEvent.event_name == "job_apply_click"
            ).label("apply_clicks"),
            func.count(distinct(AnalyticsEvent.session_id)).filter(
                AnalyticsEvent.event_name == "signup_completed"
            ).label("signups"),
        )
        .group_by(source_expr, medium_expr, campaign_expr)
        .order_by(func.count(distinct(AnalyticsSession.id)).desc())
        .limit(20)
        .all()
    )
    recent_event_rows = (
        event_scope.outerjoin(User, User.id == AnalyticsEvent.user_id)
        .with_entities(
            AnalyticsEvent.id,
            AnalyticsEvent.event_name,
            AnalyticsEvent.path,
            AnalyticsEvent.target,
            AnalyticsEvent.label,
            AnalyticsEvent.event_metadata,
            AnalyticsEvent.occurred_at,
            AnalyticsEvent.anonymous_id,
            User.email,
        )
        .order_by(AnalyticsEvent.occurred_at.desc())
        .limit(30)
        .all()
    )
    recent_session_rows = (
        session_scope.outerjoin(User, User.id == AnalyticsSession.user_id)
        .with_entities(
            AnalyticsSession.id,
            AnalyticsSession.anonymous_id,
            AnalyticsSession.user_id,
            AnalyticsSession.landing_path,
            AnalyticsSession.last_path,
            AnalyticsSession.referrer,
            AnalyticsSession.acquisition_source,
            AnalyticsSession.acquisition_medium,
            AnalyticsSession.acquisition_campaign,
            AnalyticsSession.page_views,
            AnalyticsSession.event_count,
            AnalyticsSession.engaged_seconds,
            AnalyticsSession.first_seen_at,
            AnalyticsSession.last_seen_at,
            User.email,
        )
        .order_by(AnalyticsSession.last_seen_at.desc())
        .limit(30)
        .all()
    )
    converted_ids = {
        str(item[0])
        for item in db.query(AnalyticsEvent.session_id)
        .filter(
            AnalyticsEvent.occurred_at >= start,
            AnalyticsEvent.event_name == "signup_completed",
        )
        .distinct()
        .all()
    }

    return {
        "range": {"days": days, "start": start.isoformat(), "end": datetime.now(timezone.utc).isoformat()},
        "system": {"ats_sync": await get_sync_status_async()},
        "metrics": {
            "unique_visitors": unique_visitors,
            "authenticated_visitors": authenticated_visitors,
            "sessions": sessions,
            "page_views": page_views,
            "total_events": _count(event_scope.with_entities(func.count(AnalyticsEvent.id))),
            "clicks": _count(event_scope.filter(AnalyticsEvent.event_name == "click").with_entities(func.count(AnalyticsEvent.id))),
            "job_apply_clicks": _count(event_scope.filter(AnalyticsEvent.event_name == "job_apply_click").with_entities(func.count(AnalyticsEvent.id))),
            "signup_starts": _count(event_scope.filter(AnalyticsEvent.event_name == "signup_started").with_entities(func.count(AnalyticsEvent.id))),
            "signups": _count(event_scope.filter(AnalyticsEvent.event_name == "signup_completed").with_entities(func.count(AnalyticsEvent.id))),
            "login_completions": _count(event_scope.filter(AnalyticsEvent.event_name == "login_completed").with_entities(func.count(AnalyticsEvent.id))),
            "anonymous_job_sessions_without_signup": anonymous_job_sessions,
            "engaged_seconds": engaged_seconds,
            "avg_session_seconds": round(engaged_seconds / sessions, 1) if sessions else 0,
            "users_total": _count(db.query(User).with_entities(func.count(User.id))),
            "active_jobs": _count(db.query(Job).filter(Job.processing_status != "archived").with_entities(func.count(Job.id))),
            "applications_total": _count(db.query(Application).with_entities(func.count(Application.id))),
            "profiles_total": _count(db.query(UserProfile).with_entities(func.count(UserProfile.id))),
        },
        "daily": [{"day": _iso(row.day), "sessions": int(row.sessions), "events": int(row.events)} for row in daily_rows],
        "top_paths": [{"path": row.path, "count": int(row.count)} for row in path_rows],
        "top_clicks": [{"target": row.target, "label": row.label, "count": int(row.count)} for row in click_rows],
        "top_jobs": [{"path": row.path, "views": int(row.views)} for row in job_rows],
        "acquisition_sources": [
            {
                "source": row.source,
                "medium": row.medium,
                "campaign": row.campaign or None,
                "sessions": int(row.sessions),
                "visitors": int(row.visitors),
                "job_views": int(row.job_views),
                "apply_clicks": int(row.apply_clicks),
                "signups": int(row.signups),
            }
            for row in acquisition_rows
        ],
        "recent_events": [
            {
                "id": str(row.id), "event_name": row.event_name, "path": row.path,
                "target": row.target, "label": row.label, "metadata": row.event_metadata or {},
                "occurred_at": _iso(row.occurred_at), "anonymous_id": row.anonymous_id,
                "email": row.email,
            }
            for row in recent_event_rows
        ],
        "recent_sessions": [
            {
                "id": str(row.id), "anonymous_id": row.anonymous_id,
                "email": row.email, "landing_path": row.landing_path,
                "last_path": row.last_path, "referrer": row.referrer,
                "acquisition_source": row.acquisition_source,
                "acquisition_medium": row.acquisition_medium,
                "acquisition_campaign": row.acquisition_campaign,
                "page_views": row.page_views,
                "event_count": row.event_count, "engaged_seconds": row.engaged_seconds,
                "first_seen_at": _iso(row.first_seen_at), "last_seen_at": _iso(row.last_seen_at),
                "signed_in": bool(row.user_id),
                "converted": str(row.id) in converted_ids,
            }
            for row in recent_session_rows
        ],
    }
