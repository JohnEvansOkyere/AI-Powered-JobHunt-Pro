"""User endpoints and account privacy workflows."""

from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Dict, Optional
import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.encoders import jsonable_encoder
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.v1.dependencies import get_current_user
from app.core.database import get_db
from app.core.logging import get_logger
from app.core.supabase_client import get_supabase_service_client
from app.core.config import settings
from app.models.application import Application
from app.models.cv import CV
from app.models.embeddings import UserEmbedding
from app.models.job import Job
from app.models.job_match import JobMatch
from app.models.job_recommendation import JobRecommendation
from app.models.notification import (
    NotificationPreferences,
    WhatsappIncomingEvent,
    WhatsappMessage,
)
from app.models.scraping_job import ScrapingJob
from app.models.user import User
from app.models.user_profile import UserProfile

logger = get_logger(__name__)

router = APIRouter()


class UserResponse(BaseModel):
    """User response model."""
    id: str
    email: Optional[str] = None
    full_name: Optional[str] = None
    avatar_url: Optional[str] = None
    is_active: bool = True
    email_verified: bool = False
    last_login_at: Optional[str] = None
    user_metadata: Optional[Dict[str, Any]] = {}
    created_at: str
    updated_at: str

    class Config:
        from_attributes = True


class UserUpdate(BaseModel):
    """User update model."""
    full_name: Optional[str] = None
    avatar_url: Optional[str] = None
    user_metadata: Optional[Dict[str, Any]] = None


def _current_user_uuid(current_user: dict) -> uuid.UUID:
    try:
        user_id_str = current_user.get("id")
        if not user_id_str:
            raise ValueError("missing user id")
        return uuid.UUID(str(user_id_str))
    except (ValueError, TypeError) as exc:
        logger.error("Invalid user ID format: %s, error: %s", current_user.get("id"), exc)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid user ID format",
        ) from exc


def _serialize_model(row: Any) -> Dict[str, Any]:
    """Serialize one SQLAlchemy model without loading relationships."""
    if row is None:
        return {}
    data: Dict[str, Any] = {}
    for column in row.__table__.columns:
        value = getattr(row, column.name)
        if isinstance(value, Decimal):
            value = float(value)
        data[column.name] = value
    return jsonable_encoder(data)


def _serialize_rows(rows: list[Any]) -> list[Dict[str, Any]]:
    return [_serialize_model(row) for row in rows]


def _remove_cv_storage_files(paths: list[str]) -> None:
    if not paths:
        return
    try:
        response = (
            get_supabase_service_client()
            .storage
            .from_(settings.SUPABASE_STORAGE_BUCKET)
            .remove(paths)
        )
    except Exception as exc:
        logger.error("cv_storage_delete_failed", error=str(exc))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not delete stored CV files. Account deletion was not completed.",
        ) from exc

    error = getattr(response, "error", None)
    if isinstance(response, dict):
        error = response.get("error")
    if error:
        logger.error("cv_storage_delete_failed", error=str(error))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not delete stored CV files. Account deletion was not completed.",
        )


@router.get("/me", response_model=UserResponse)
async def get_my_user_info(
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Get current user information from public.users table.
    
    Returns:
        UserResponse: User information
    """
    user_id = _current_user_uuid(current_user)
    
    user = db.query(User).filter(User.id == user_id).first()
    
    if not user:
        # User might not be synced yet, return from auth data
        return UserResponse(
            id=current_user.get("id", ""),
            email=current_user.get("email"),
            full_name=current_user.get("user_metadata", {}).get("full_name"),
            email_verified=current_user.get("email_confirmed_at") is not None,
            user_metadata=current_user.get("user_metadata", {}),
            created_at=current_user.get("created_at", ""),
            updated_at=current_user.get("updated_at", ""),
        )
    
    return UserResponse(
        id=str(user.id),
        email=user.email,
        full_name=user.full_name,
        avatar_url=user.avatar_url,
        is_active=user.is_active,
        email_verified=user.email_verified,
        last_login_at=user.last_login_at.isoformat() if user.last_login_at else None,
        user_metadata=user.user_metadata or {},
        created_at=user.created_at.isoformat() if user.created_at else "",
        updated_at=user.updated_at.isoformat() if user.updated_at else "",
    )


@router.put("/me", response_model=UserResponse)
async def update_my_user_info(
    user_data: UserUpdate,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Update current user information.
    
    Args:
        user_data: User data to update
        
    Returns:
        UserResponse: Updated user information
    """
    user_id = _current_user_uuid(current_user)
    
    user = db.query(User).filter(User.id == user_id).first()
    
    if not user:
        # Create user record if it doesn't exist
        user = User(
            id=user_id,
            email=current_user.get("email"),
            email_verified=current_user.get("email_confirmed_at") is not None,
            user_metadata=current_user.get("user_metadata", {}),
        )
        db.add(user)
    
    # Update fields
    update_data = user_data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        if key == "user_metadata" and user.user_metadata:
            # Merge metadata instead of replacing
            user.user_metadata = {**(user.user_metadata or {}), **(value or {})}
        else:
            # Map user_metadata to the actual column name
            if key == "user_metadata":
                setattr(user, "user_metadata", value)
            else:
                setattr(user, key, value)
    
    db.commit()
    db.refresh(user)
    
    logger.info(f"Updated user {user_id}")
    
    return UserResponse(
        id=str(user.id),
        email=user.email,
        full_name=user.full_name,
        avatar_url=user.avatar_url,
        is_active=user.is_active,
        email_verified=user.email_verified,
        last_login_at=user.last_login_at.isoformat() if user.last_login_at else None,
        user_metadata=user.user_metadata or {},
        created_at=user.created_at.isoformat() if user.created_at else "",
        updated_at=user.updated_at.isoformat() if user.updated_at else "",
    )


@router.get("/me/export")
async def export_my_data(
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Export the current user's candidate-platform data as JSON."""
    user_id = _current_user_uuid(current_user)

    local_user = db.query(User).filter(User.id == user_id).first()
    profile = db.query(UserProfile).filter(UserProfile.user_id == user_id).first()
    cvs = db.query(CV).filter(CV.user_id == user_id).all()
    applications = db.query(Application).filter(Application.user_id == user_id).all()
    job_matches = db.query(JobMatch).filter(JobMatch.user_id == user_id).all()
    recommendations = (
        db.query(JobRecommendation).filter(JobRecommendation.user_id == user_id).all()
    )
    scraping_jobs = db.query(ScrapingJob).filter(ScrapingJob.user_id == user_id).all()
    user_embedding = db.query(UserEmbedding).filter(UserEmbedding.user_id == user_id).first()
    notification_preferences = (
        db.query(NotificationPreferences)
        .filter(NotificationPreferences.user_id == user_id)
        .first()
    )
    whatsapp_messages = (
        db.query(WhatsappMessage).filter(WhatsappMessage.user_id == user_id).all()
    )
    whatsapp_incoming_events = (
        db.query(WhatsappIncomingEvent)
        .filter(WhatsappIncomingEvent.user_id == user_id)
        .all()
    )
    external_jobs = db.query(Job).filter(Job.added_by_user_id == user_id).all()

    return {
        "exported_at": datetime.now(timezone.utc).isoformat(),
        "auth_user": jsonable_encoder(
            {
                "id": current_user.get("id"),
                "email": current_user.get("email"),
                "email_confirmed_at": current_user.get("email_confirmed_at"),
                "created_at": current_user.get("created_at"),
                "user_metadata": current_user.get("user_metadata", {}),
            }
        ),
        "user": _serialize_model(local_user) if local_user else None,
        "profile": _serialize_model(profile) if profile else None,
        "cvs": _serialize_rows(cvs),
        "applications": _serialize_rows(applications),
        "job_matches": _serialize_rows(job_matches),
        "job_recommendations": _serialize_rows(recommendations),
        "scraping_jobs": _serialize_rows(scraping_jobs),
        "user_embedding": _serialize_model(user_embedding) if user_embedding else None,
        "notification_preferences": (
            _serialize_model(notification_preferences)
            if notification_preferences
            else None
        ),
        "whatsapp_messages": _serialize_rows(whatsapp_messages),
        "whatsapp_incoming_events": _serialize_rows(whatsapp_incoming_events),
        "external_jobs_added_by_user": _serialize_rows(external_jobs),
    }


@router.delete("/me", status_code=status.HTTP_200_OK)
async def delete_my_account(
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Delete the current user's candidate data and best-effort remove Auth user."""
    user_id = _current_user_uuid(current_user)

    cvs = db.query(CV).filter(CV.user_id == user_id).all()
    cv_paths = [cv.file_path for cv in cvs if cv.file_path]
    _remove_cv_storage_files(cv_paths)

    deleted_counts: Dict[str, int] = {}
    try:
        delete_specs = (
            ("whatsapp_incoming_events", WhatsappIncomingEvent),
            ("whatsapp_messages", WhatsappMessage),
            ("notification_preferences", NotificationPreferences),
            ("job_recommendations", JobRecommendation),
            ("job_matches", JobMatch),
            ("applications", Application),
            ("scraping_jobs", ScrapingJob),
            ("user_embeddings", UserEmbedding),
            ("cvs", CV),
            ("user_profiles", UserProfile),
        )
        for name, model in delete_specs:
            deleted_counts[name] = (
                db.query(model)
                .filter(getattr(model, "user_id") == user_id)
                .delete(synchronize_session=False)
            )

        deleted_counts["external_jobs_detached_from_user"] = (
            db.query(Job)
            .filter(Job.added_by_user_id == user_id)
            .update({"added_by_user_id": None}, synchronize_session=False)
        )
        deleted_counts["users"] = (
            db.query(User).filter(User.id == user_id).delete(synchronize_session=False)
        )
        db.commit()
    except Exception as exc:
        db.rollback()
        logger.error("account_delete_failed", user_id=str(user_id), error=str(exc))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not delete account data.",
        ) from exc

    auth_user_deleted = False
    auth_delete_error: Optional[str] = None
    try:
        get_supabase_service_client().auth.admin.delete_user(str(user_id))
        auth_user_deleted = True
    except Exception as exc:
        auth_delete_error = "Supabase Auth user deletion failed; local data was deleted."
        logger.error("auth_user_delete_failed", user_id=str(user_id), error=str(exc))

    return {
        "status": "deleted",
        "deleted_counts": deleted_counts,
        "cv_files_deleted": len(cv_paths),
        "auth_user_deleted": auth_user_deleted,
        "warning": auth_delete_error,
    }
