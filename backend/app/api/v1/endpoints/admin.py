"""Administrator dashboard and product analytics API."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Optional
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy import distinct, func, or_
from sqlalchemy.orm import Session

from app.api.v1.dependencies import require_admin
from app.core.database import get_db
from app.models.analytics import AnalyticsEvent, AnalyticsSession
from app.models.application import Application
from app.models.job import Job
from app.models.user import User
from app.models.user_profile import UserProfile
from app.services.ats_sync_status_service import get_sync_status_async
from app.api.v1.endpoints.users import _current_user_uuid, _delete_account_data
from app.core.supabase_client import get_supabase_service_client
from app.core.logging import get_logger

router = APIRouter()
logger = get_logger(__name__)


class AdminUserStatusUpdate(BaseModel):
    is_active: bool


def _user_payload(user: User) -> dict:
    return {
        "id": str(user.id),
        "email": user.email,
        "full_name": user.full_name,
        "is_active": bool(user.is_active),
        "is_admin": bool(user.is_admin),
        "email_verified": bool(user.email_verified),
        "last_login_at": _iso(user.last_login_at),
        "created_at": _iso(user.created_at),
        "updated_at": _iso(user.updated_at),
    }


def _range_start(days: int) -> datetime:
    return datetime.now(timezone.utc) - timedelta(days=max(1, min(days, 90)))


def _count(query) -> int:
    return int(query.scalar() or 0)


def _iso(value: Any) -> Optional[str]:
    return value.isoformat() if value else None


@router.get("/me")
async def admin_me(current_user: dict = Depends(require_admin)) -> dict:
    return {"is_admin": True, "email": current_user.get("email")}


@router.get("/users")
async def admin_users(
    search: str = Query(default="", max_length=120),
    status_filter: str = Query(default="all", alias="status", pattern="^(all|active|suspended)$"),
    db: Session = Depends(get_db),
    _admin: dict = Depends(require_admin),
) -> dict:
    """List candidate accounts for the admin user-control surface."""
    query = db.query(User)
    if search.strip():
        term = f"%{search.strip()}%"
        query = query.filter(or_(User.email.ilike(term), User.full_name.ilike(term)))
    if status_filter == "active":
        query = query.filter(User.is_active.is_(True))
    elif status_filter == "suspended":
        query = query.filter(User.is_active.is_(False))

    users = query.order_by(User.created_at.desc()).limit(500).all()
    return {
        "users": [_user_payload(user) for user in users],
        "total": db.query(User).count(),
        "active": db.query(User).filter(User.is_active.is_(True)).count(),
        "suspended": db.query(User).filter(User.is_active.is_(False)).count(),
    }


@router.patch("/users/{user_id}/status")
async def admin_update_user_status(
    user_id: uuid.UUID,
    payload: AdminUserStatusUpdate,
    db: Session = Depends(get_db),
    current_admin: dict = Depends(require_admin),
) -> dict:
    """Suspend or reactivate a user; the status is enforced on every API request."""
    target = db.query(User).filter(User.id == user_id).first()
    if not target:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    admin_id = _current_user_uuid(current_admin)
    if target.id == admin_id and not payload.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You cannot suspend your own administrator account.",
        )

    target.is_active = payload.is_active
    db.commit()
    db.refresh(target)
    return {"user": _user_payload(target)}


@router.delete("/users/{user_id}")
async def admin_revoke_user(
    user_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_admin: dict = Depends(require_admin),
) -> dict:
    """Permanently revoke a user from the platform and delete their Auth account."""
    target = db.query(User).filter(User.id == user_id).first()
    if not target:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    admin_id = _current_user_uuid(current_admin)
    if target.id == admin_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You cannot revoke your own administrator account.",
        )
    if target.is_admin and db.query(User).filter(User.is_admin.is_(True)).count() <= 1:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Create another administrator before revoking the last administrator.",
        )

    deleted_counts, cv_files_deleted = _delete_account_data(db, user_id)
    auth_user_deleted = False
    warning: Optional[str] = None
    try:
        get_supabase_service_client().auth.admin.delete_user(str(user_id))
        auth_user_deleted = True
    except Exception as exc:
        warning = "Platform data was deleted, but the Supabase Auth user could not be deleted."
        logger.error("admin_auth_user_delete_failed", user_id=str(user_id), error=str(exc))

    return {
        "status": "revoked",
        "user_id": str(user_id),
        "deleted_counts": deleted_counts,
        "cv_files_deleted": cv_files_deleted,
        "auth_user_deleted": auth_user_deleted,
        "warning": warning,
    }


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
