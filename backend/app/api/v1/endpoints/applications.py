"""
Applications API Endpoints

Minimal application tracker: save, dismiss/hide, mark applied externally,
and progress through a simple interview pipeline. CV tailoring and
cover-letter generation were removed in v2 (see docs/RECOMMENDATIONS_V2_PLAN.md).

Valid statuses (see migrations/007_remove_cv_tailoring.sql):
    saved, applied, dismissed, hidden, interviewing, rejected, offer
"""

from datetime import datetime, timedelta, timezone
from typing import Optional
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, field_serializer
from sqlalchemy import and_
from sqlalchemy.orm import Session, joinedload

from app.api.v1.dependencies import get_current_user
from app.core.database import get_db
from app.core.logging import get_logger
from app.models.application import Application
from app.models.job import Job

router = APIRouter()
logger = get_logger(__name__)


VALID_STATUSES = frozenset(
    {"saved", "applied", "dismissed", "hidden", "interviewing", "rejected", "offer"}
)
APPLIED_STATUSES = frozenset({"applied", "interviewing", "offer"})
MAX_SAVED_JOBS = 20


class JobDetails(BaseModel):
    id: uuid.UUID
    title: str
    company: str
    location: Optional[str]
    job_link: Optional[str]
    source: str
    posted_date: Optional[datetime]
    salary_range: Optional[str]
    job_type: Optional[str]
    remote_type: Optional[str]

    @field_serializer("posted_date")
    def serialize_posted_date(self, dt: Optional[datetime], _info):
        return dt.isoformat() if dt else None

    class Config:
        from_attributes = True


class ApplicationResponse(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    job_id: uuid.UUID
    cv_id: Optional[uuid.UUID]
    status: str
    saved_at: Optional[datetime]
    expires_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime

    @field_serializer("created_at", "updated_at", "saved_at", "expires_at")
    def serialize_datetime(self, dt: Optional[datetime], _info):
        return dt.isoformat() if dt else None

    class Config:
        from_attributes = True


class ApplicationWithJobResponse(ApplicationResponse):
    job: Optional[JobDetails] = None


class UpdateStatusRequest(BaseModel):
    status: str


def _uid(current_user: dict) -> uuid.UUID:
    user_id = current_user["id"]
    return uuid.UUID(user_id) if isinstance(user_id, str) else user_id


def _to_response(app: Application, include_job: bool = False) -> ApplicationWithJobResponse:
    payload = {
        "id": app.id,
        "user_id": app.user_id,
        "job_id": app.job_id,
        "cv_id": app.cv_id,
        "status": app.status,
        "saved_at": app.saved_at,
        "expires_at": app.expires_at,
        "created_at": app.created_at,
        "updated_at": app.updated_at,
        "job": None,
    }
    if include_job and app.job:
        payload["job"] = {
            "id": app.job.id,
            "title": app.job.title,
            "company": app.job.company,
            "location": app.job.location,
            "job_link": app.job.job_link,
            "source": app.job.source,
            "posted_date": app.job.posted_date,
            "salary_range": app.job.salary_range,
            "job_type": app.job.job_type,
            "remote_type": app.job.remote_type,
        }
    return ApplicationWithJobResponse(**payload)


# ---------------------------------------------------------------------------
# Static routes first so they take priority over `/{application_id}` below.
# ---------------------------------------------------------------------------


@router.get("/saved-jobs", response_model=list[ApplicationWithJobResponse])
def get_saved_jobs(
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """All saved jobs for the current user, newest first, with job details."""
    user_id = _uid(current_user)
    saved = (
        db.query(Application)
        .options(joinedload(Application.job))
        .filter(and_(Application.user_id == user_id, Application.status == "saved"))
        .order_by(Application.saved_at.desc())
        .all()
    )
    return [_to_response(app, include_job=True) for app in saved]


@router.get("/stats")
def get_applications_stats(
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Dashboard counts: total tracked applications and jobs the user has actually applied to."""
    user_id = _uid(current_user)
    base = db.query(Application).filter(Application.user_id == user_id)
    applications_total = base.count()
    submitted_count = base.filter(Application.status.in_(tuple(APPLIED_STATUSES))).count()
    return {
        "applications_total": applications_total,
        "submitted_count": submitted_count,
    }


@router.get("/", response_model=list[ApplicationWithJobResponse])
def list_applications(
    status_filter: Optional[str] = Query(None, description="Filter by status"),
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List the user's applications (with job details), newest first."""
    user_id = _uid(current_user)
    query = (
        db.query(Application)
        .options(joinedload(Application.job))
        .filter(Application.user_id == user_id)
    )
    if status_filter:
        normalized = status_filter.lower()
        if normalized not in VALID_STATUSES:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid status. Must be one of: {sorted(VALID_STATUSES)}",
            )
        query = query.filter(Application.status == normalized)
    applications = query.order_by(Application.created_at.desc()).limit(50).all()
    return [_to_response(app, include_job=True) for app in applications]


# ---------------------------------------------------------------------------
# Mutations (saved / applied / dismissed / hidden)
# ---------------------------------------------------------------------------


@router.post(
    "/save-job/{job_id}",
    response_model=ApplicationResponse,
    status_code=status.HTTP_201_CREATED,
)
def save_job(
    job_id: uuid.UUID,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Bookmark a job. Creates a `saved` row with a 10-day expiry."""
    user_id = _uid(current_user)

    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")

    existing = (
        db.query(Application)
        .filter(and_(Application.user_id == user_id, Application.job_id == job_id))
        .first()
    )
    if existing:
        if existing.status == "saved":
            return _to_response(existing)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Job already tracked with status '{existing.status}'",
        )

    saved_count = (
        db.query(Application)
        .filter(and_(Application.user_id == user_id, Application.status == "saved"))
        .count()
    )
    if saved_count >= MAX_SAVED_JOBS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Saved jobs limit reached ({MAX_SAVED_JOBS}). Remove some before saving more.",
        )

    now = datetime.now(timezone.utc)
    application = Application(
        user_id=user_id,
        job_id=job_id,
        status="saved",
        saved_at=now,
        expires_at=now + timedelta(days=10),
    )
    db.add(application)
    db.commit()
    db.refresh(application)
    logger.info(f"Job {job_id} saved by user {user_id}")
    return _to_response(application)


@router.delete("/unsave-job/{job_id}", status_code=status.HTTP_204_NO_CONTENT)
def unsave_job(
    job_id: uuid.UUID,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Remove a saved job. Only 'saved' rows can be unsaved."""
    user_id = _uid(current_user)
    application = (
        db.query(Application)
        .filter(and_(Application.user_id == user_id, Application.job_id == job_id))
        .first()
    )
    if not application:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Saved job not found")
    if application.status != "saved":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot unsave job with status '{application.status}'",
        )
    db.delete(application)
    db.commit()
    logger.info(f"Job {job_id} unsaved by user {user_id}")
    return None


@router.patch("/update-status/{job_id}", response_model=ApplicationResponse)
def update_application_status(
    job_id: uuid.UUID,
    request: UpdateStatusRequest,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Update application status. Creates the row if it doesn't exist yet."""
    normalized = request.status.lower().strip()
    if normalized not in VALID_STATUSES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid status. Must be one of: {sorted(VALID_STATUSES)}",
        )

    user_id = _uid(current_user)

    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")

    application = (
        db.query(Application)
        .filter(and_(Application.user_id == user_id, Application.job_id == job_id))
        .first()
    )

    if not application:
        application = Application(user_id=user_id, job_id=job_id, status=normalized)
        db.add(application)
    else:
        application.status = normalized

    db.commit()
    db.refresh(application)
    logger.info(f"Application status for job {job_id} set to '{normalized}' by user {user_id}")
    return _to_response(application)


@router.post("/mark-applied/{job_id}", response_model=ApplicationResponse)
def mark_applied_external(
    job_id: uuid.UUID,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Mark a job as applied (shortcut used after clicking the external Apply button)."""
    return update_application_status(
        job_id=job_id,
        request=UpdateStatusRequest(status="applied"),
        current_user=current_user,
        db=db,
    )


# ---------------------------------------------------------------------------
# Dynamic routes (keep these LAST).
# ---------------------------------------------------------------------------


@router.get("/{application_id}", response_model=ApplicationResponse)
def get_application(
    application_id: uuid.UUID,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    user_id = _uid(current_user)
    application = (
        db.query(Application)
        .filter(and_(Application.id == application_id, Application.user_id == user_id))
        .first()
    )
    if not application:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Application not found")
    return _to_response(application)


@router.get("/job/{job_id}", response_model=Optional[ApplicationResponse])
def get_application_for_job(
    job_id: uuid.UUID,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    user_id = _uid(current_user)
    application = (
        db.query(Application)
        .filter(and_(Application.job_id == job_id, Application.user_id == user_id))
        .first()
    )
    return _to_response(application) if application else None
