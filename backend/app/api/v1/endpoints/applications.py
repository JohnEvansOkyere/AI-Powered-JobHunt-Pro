"""
Application Generation API Endpoints

Handles generation of tailored CVs, cover letters, and application materials.
"""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from sqlalchemy import and_
from typing import Optional
from datetime import datetime
import uuid

from app.core.database import get_db
from app.api.v1.dependencies import get_current_user
from app.core.logging import get_logger
from app.models.application import Application
from app.models.job import Job
from app.services.cv_generator import get_cv_generator
from pydantic import BaseModel, field_serializer

router = APIRouter()
logger = get_logger(__name__)


# Pydantic models
class GenerateCVRequest(BaseModel):
    """Request model for CV generation."""
    
    tone: Optional[str] = "professional"  # professional, confident, friendly
    highlight_skills: bool = True
    emphasize_relevant_experience: bool = True


class GenerateCVResponse(BaseModel):
    """Response model for CV generation."""
    
    application_id: str
    cv_path: str
    public_url: Optional[str]
    status: str
    created_at: Optional[str]


class ApplicationResponse(BaseModel):
    """Application response model."""

    id: uuid.UUID
    user_id: uuid.UUID
    job_id: uuid.UUID
    cv_id: Optional[uuid.UUID]
    tailored_cv_path: Optional[str]
    cover_letter: Optional[str]
    application_email: Optional[str]
    status: str
    saved_at: Optional[datetime]
    expires_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime

    @field_serializer('created_at', 'updated_at', 'saved_at', 'expires_at')
    def serialize_datetime(self, dt: datetime, _info):
        """Serialize datetime to ISO format string."""
        return dt.isoformat() if dt else None
    
    class Config:
        from_attributes = True


@router.post("/generate-cv/{job_id}", response_model=GenerateCVResponse, status_code=status.HTTP_201_CREATED)
async def generate_tailored_cv(
    job_id: uuid.UUID,
    request: GenerateCVRequest,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Generate a tailored CV for a specific job.
    
    - Requires an active CV to be uploaded
    - Uses AI to tailor the CV to the job requirements
    - Saves the tailored CV to storage
    - Creates/updates an Application record
    """
    user_id = current_user["id"]
    if isinstance(user_id, str):
        user_id = uuid.UUID(user_id)
    
    # Verify job exists
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job not found"
        )
    
    try:
        cv_generator = get_cv_generator()
        result = await cv_generator.generate_tailored_cv(
            user_id=str(user_id),
            job_id=str(job_id),
            db=db,
            tone=request.tone,
            highlight_skills=request.highlight_skills,
            emphasize_relevant_experience=request.emphasize_relevant_experience
        )
        
        return GenerateCVResponse(**result)
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error generating tailored CV: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate tailored CV: {str(e)}"
        )


@router.get("/{application_id}", response_model=ApplicationResponse)
def get_application(
    application_id: uuid.UUID,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get a specific application by ID."""
    user_id = current_user["id"]
    if isinstance(user_id, str):
        user_id = uuid.UUID(user_id)
    
    application = db.query(Application).filter(
        and_(
            Application.id == application_id,
            Application.user_id == user_id
        )
    ).first()
    
    if not application:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Application not found"
        )
    
    return ApplicationResponse.from_orm(application)


@router.get("/job/{job_id}", response_model=Optional[ApplicationResponse])
def get_application_for_job(
    job_id: uuid.UUID,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get application for a specific job."""
    user_id = current_user["id"]
    if isinstance(user_id, str):
        user_id = uuid.UUID(user_id)
    
    application = db.query(Application).filter(
        and_(
            Application.job_id == job_id,
            Application.user_id == user_id
        )
    ).first()
    
    if application:
        return ApplicationResponse.from_orm(application)
    return None


@router.get("/", response_model=list[ApplicationResponse])
def list_applications(
    status_filter: Optional[str] = Query(None, description="Filter by status"),
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get list of user's applications."""
    user_id = current_user["id"]
    if isinstance(user_id, str):
        user_id = uuid.UUID(user_id)
    
    query = db.query(Application).filter(Application.user_id == user_id)
    
    if status_filter:
        query = query.filter(Application.status == status_filter.lower())
    
    applications = query.order_by(Application.created_at.desc()).limit(50).all()
    
    return [ApplicationResponse.from_orm(app) for app in applications]


@router.get("/{application_id}/download-url")
def get_cv_download_url(
    application_id: uuid.UUID,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get download URL for tailored CV."""
    from app.core.supabase_client import get_supabase_service_client
    from app.core.config import settings
    
    user_id = current_user["id"]
    if isinstance(user_id, str):
        user_id = uuid.UUID(user_id)
    
    application = db.query(Application).filter(
        and_(
            Application.id == application_id,
            Application.user_id == user_id
        )
    ).first()
    
    if not application:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Application not found"
        )
    
    if not application.tailored_cv_path:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No tailored CV found for this application"
        )
    
    try:
        supabase = get_supabase_service_client()
        url_result = supabase.storage.from_(settings.SUPABASE_STORAGE_BUCKET).get_public_url(
            application.tailored_cv_path
        )
        public_url = url_result if isinstance(url_result, str) else url_result.get("publicUrl", "")
        
        return {"download_url": public_url}
    except Exception as e:
        logger.error(f"Error getting download URL: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get download URL"
        )


@router.post("/save-job/{job_id}", response_model=ApplicationResponse, status_code=status.HTTP_201_CREATED)
def save_job(
    job_id: uuid.UUID,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Save a job for later (bookmark it).

    Creates an application record with status='saved' and expires_at=now+10days.
    User can save up to 10 jobs at a time.
    """
    from datetime import timedelta

    user_id = current_user["id"]
    if isinstance(user_id, str):
        user_id = uuid.UUID(user_id)

    # Check if job exists
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job not found"
        )

    # Check if already saved
    existing = db.query(Application).filter(
        and_(
            Application.user_id == user_id,
            Application.job_id == job_id
        )
    ).first()

    if existing:
        # If already exists, just return it
        if existing.status == 'saved':
            logger.info(f"Job {job_id} already saved by user {user_id}")
            return ApplicationResponse.from_orm(existing)
        else:
            # If in progress or submitted, don't allow re-saving
            logger.warning(f"Job {job_id} already has application in status: {existing.status}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Job already has an application in '{existing.status}' status"
            )

    # Check saved jobs limit (max 10)
    saved_count = db.query(Application).filter(
        and_(
            Application.user_id == user_id,
            Application.status == 'saved'
        )
    ).count()

    if saved_count >= 10:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You have reached the maximum limit of 10 saved jobs. Please remove some before saving more."
        )

    # Create saved application
    now = datetime.utcnow()
    expires_at = now + timedelta(days=10)

    application = Application(
        user_id=user_id,
        job_id=job_id,
        status="saved",
        saved_at=now,
        expires_at=expires_at
    )

    db.add(application)
    db.commit()
    db.refresh(application)

    logger.info(f"Job {job_id} saved by user {user_id}, expires at {expires_at}")

    return ApplicationResponse.from_orm(application)


@router.delete("/unsave-job/{job_id}", status_code=status.HTTP_204_NO_CONTENT)
def unsave_job(
    job_id: uuid.UUID,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Remove a saved job (unsave/unbookmark).

    Deletes the application record if status is 'saved'.
    Cannot unsave if CV has been generated (status != 'saved').
    """
    user_id = current_user["id"]
    if isinstance(user_id, str):
        user_id = uuid.UUID(user_id)

    application = db.query(Application).filter(
        and_(
            Application.user_id == user_id,
            Application.job_id == job_id
        )
    ).first()

    if not application:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Saved job not found"
        )

    if application.status != 'saved':
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot unsave job with status '{application.status}'. Only 'saved' jobs can be removed."
        )

    db.delete(application)
    db.commit()

    logger.info(f"Job {job_id} unsaved by user {user_id}")

    return None


@router.get("/saved-jobs", response_model=list[ApplicationResponse])
def get_saved_jobs(
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Get all saved jobs for the current user.

    Returns applications with status='saved', ordered by saved_at desc.
    """
    user_id = current_user["id"]
    if isinstance(user_id, str):
        user_id = uuid.UUID(user_id)

    saved_apps = db.query(Application).filter(
        and_(
            Application.user_id == user_id,
            Application.status == 'saved'
        )
    ).order_by(Application.saved_at.desc()).all()

    logger.info(f"Retrieved {len(saved_apps)} saved jobs for user {user_id}")

    return [ApplicationResponse.from_orm(app) for app in saved_apps]


