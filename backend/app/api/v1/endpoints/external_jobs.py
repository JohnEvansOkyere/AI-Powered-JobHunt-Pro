"""
External Jobs API Endpoints

Endpoints for users to manually add external job postings.
"""

import json
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, HttpUrl, Field, validator
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.api.v1.dependencies import get_current_user
from app.services.external_job_parser import get_job_parser
from app.models.job import Job
from app.core.logging import get_logger

logger = get_logger(__name__)

router = APIRouter()


class ExternalJobURLRequest(BaseModel):
    """Request to add a job from URL."""
    url: HttpUrl = Field(..., description="Job posting URL")


class ExternalJobTextRequest(BaseModel):
    """Request to add a job from text."""
    text: str = Field(..., min_length=50, description="Job posting text")
    source_url: Optional[HttpUrl] = Field(None, description="Optional source URL")
    
    @validator('text')
    def validate_text_length(cls, v):
        if len(v) > 10000:
            raise ValueError("Job description is too long (max 10,000 characters)")
        return v


class ExternalJobResponse(BaseModel):
    """Response after adding external job."""
    id: str
    title: str
    company: str
    location: Optional[str]  # Make optional since AI might not extract it
    message: str = "Job added successfully"


@router.post("/external/from-url", response_model=ExternalJobResponse, status_code=status.HTTP_201_CREATED)
async def add_job_from_url(
    request: ExternalJobURLRequest,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Add a job posting by providing a URL.
    
    The system will fetch the page, extract job details using AI,
    and add it to your job list.
    """
    try:
        # Parse job from URL
        parser = get_job_parser()
        job_data = await parser.parse_from_url(str(request.url))
        
        # Create job in database
        job = Job(
            title=job_data['title'],
            company=job_data['company'],
            location=job_data['location'],
            job_type=job_data.get('job_type', 'full-time'),
            salary_min=job_data.get('salary_min'),
            salary_max=job_data.get('salary_max'),
            salary_currency=job_data.get('salary_currency'),
            description=job_data['description'],
            requirements=json.dumps(job_data.get('requirements', [])),
            responsibilities=json.dumps(job_data.get('responsibilities', [])),
            skills=json.dumps(job_data.get('skills', [])),
            experience_level=job_data.get('experience_level'),
            remote_option=job_data.get('remote_option', False),
            source='external',
            source_url=str(request.url),
            added_by_user_id=current_user['id']
        )
        
        db.add(job)
        db.commit()
        db.refresh(job)
        
        logger.info(
            f"User {current_user['id']} added external job from URL",
            job_id=str(job.id),
            url=str(request.url)
        )
        
        return ExternalJobResponse(
            id=str(job.id),
            title=job.title,
            company=job.company,
            location=job.location or "Not specified",
            message="Job successfully extracted and added to your list"
        )
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error adding job from URL: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to process job posting. Please try again or paste the job description manually."
        )


@router.post("/external/from-text", response_model=ExternalJobResponse, status_code=status.HTTP_201_CREATED)
async def add_job_from_text(
    request: ExternalJobTextRequest,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Add a job posting by pasting the job description text.
    
    The system will use AI to extract job details and add it to your job list.
    """
    try:
        # Parse job from text
        parser = get_job_parser()
        job_data = await parser.parse_from_text(
            request.text,
            str(request.source_url) if request.source_url else None
        )
        
        # Create job in database
        job = Job(
            title=job_data['title'],
            company=job_data['company'],
            location=job_data['location'],
            job_type=job_data.get('job_type', 'full-time'),
            salary_min=job_data.get('salary_min'),
            salary_max=job_data.get('salary_max'),
            salary_currency=job_data.get('salary_currency'),
            description=job_data['description'],
            requirements=json.dumps(job_data.get('requirements', [])),
            responsibilities=json.dumps(job_data.get('responsibilities', [])),
            skills=json.dumps(job_data.get('skills', [])),
            experience_level=job_data.get('experience_level'),
            remote_option=job_data.get('remote_option', False),
            source='external',
            source_url=str(request.source_url) if request.source_url else None,
            added_by_user_id=current_user['id']
        )
        
        db.add(job)
        db.commit()
        db.refresh(job)
        
        logger.info(
            f"User {current_user['id']} added external job from text",
            job_id=str(job.id)
        )
        
        return ExternalJobResponse(
            id=str(job.id),
            title=job.title,
            company=job.company,
            location=job.location or "Not specified",
            message="Job successfully parsed and added to your list"
        )
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error adding job from text: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to process job description. Please ensure the text contains valid job details."
        )
