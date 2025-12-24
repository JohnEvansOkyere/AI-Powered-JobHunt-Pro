"""
Job Management API Endpoints

Handles job listing, searching, filtering, and scraping operations.
"""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func, desc
from typing import List, Optional
from datetime import datetime, timedelta
import uuid

from app.core.database import get_db
from app.api.v1.dependencies import get_current_user
from app.core.logging import get_logger
from app.models.job import Job
from app.models.scraping_job import ScrapingJob
from app.models.job_match import JobMatch
from app.services.job_scraper_service import JobScraperService
from app.services.job_matching_service import JobMatchingService
from app.services.job_matching_service_optimized import get_optimized_matching_service
from app.services.ai_job_matcher import get_ai_job_matcher
from app.tasks.job_scraping import scrape_jobs_task
from pydantic import BaseModel, field_serializer

router = APIRouter()
logger = get_logger(__name__)
scraper_service = JobScraperService()
matching_service = JobMatchingService()
optimized_matching_service = get_optimized_matching_service()
ai_matcher = get_ai_job_matcher()  # AI-powered semantic matching


# Pydantic models
class JobResponse(BaseModel):
    """Job response model."""
    
    id: uuid.UUID
    title: str
    company: str
    location: Optional[str]
    description: str
    job_link: str
    source: str
    source_id: Optional[str]
    posted_date: Optional[datetime]
    scraped_at: datetime
    normalized_title: Optional[str]
    normalized_location: Optional[str]
    salary_range: Optional[str]
    job_type: Optional[str]
    remote_type: Optional[str]
    processing_status: str
    created_at: datetime
    updated_at: datetime
    match_score: Optional[float] = None  # Relevance score (0-100)
    match_reasons: Optional[List[str]] = None  # Match reasons
    
    @field_serializer('posted_date', 'scraped_at', 'created_at', 'updated_at')
    def serialize_datetime(self, dt: datetime, _info):
        """Serialize datetime to ISO format string."""
        return dt.isoformat() if dt else None
    
    class Config:
        from_attributes = True


class JobSearchResponse(BaseModel):
    """Job search response with pagination."""
    
    jobs: List[JobResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


class ScrapeJobsRequest(BaseModel):
    """Request model for starting a job scraping task."""
    
    sources: List[str]
    keywords: Optional[List[str]] = None
    location: Optional[str] = None
    max_results_per_source: int = 50


class ScrapeJobsResponse(BaseModel):
    """Response model for scraping job creation."""
    
    scraping_job_id: uuid.UUID
    status: str
    message: str


class ScrapingJobResponse(BaseModel):
    """Scraping job status response."""
    
    id: uuid.UUID
    user_id: Optional[uuid.UUID]
    sources: List[str]
    keywords: Optional[List[str]]
    status: str
    progress: int
    jobs_found: int
    jobs_processed: int
    error_message: Optional[str]
    result_summary: Optional[dict]
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    created_at: datetime
    
    @field_serializer('started_at', 'completed_at', 'created_at')
    def serialize_datetime(self, dt: datetime, _info):
        """Serialize datetime to ISO format string."""
        return dt.isoformat() if dt else None
    
    class Config:
        from_attributes = True


@router.get("/", response_model=JobSearchResponse)
async def search_jobs(
    q: Optional[str] = Query(None, description="Search query (title, company, description)"),
    source: Optional[str] = Query(None, description="Filter by source"),
    location: Optional[str] = Query(None, description="Filter by location"),
    job_type: Optional[str] = Query(None, description="Filter by job type"),
    remote_type: Optional[str] = Query(None, description="Filter by remote type"),
    min_posted_days: Optional[int] = Query(None, description="Minimum days since posted"),
    matched: bool = Query(False, description="Return only matched jobs with scores"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Search and filter jobs.
    
    If matched=True, returns jobs matched to the user with relevance scores.
    Otherwise returns all jobs matching the criteria.
    """
    query = db.query(Job)
    
    # Text search
    if q:
        search_term = f"%{q}%"
        query = query.filter(
            or_(
                Job.title.ilike(search_term),
                Job.company.ilike(search_term),
                Job.description.ilike(search_term)
            )
        )
    
    # Source filter
    if source:
        query = query.filter(Job.source == source.lower())
    
    # Location filter
    if location:
        location_term = f"%{location}%"
        query = query.filter(
            or_(
                Job.location.ilike(location_term),
                Job.normalized_location.ilike(location_term)
            )
        )
    
    # Job type filter
    if job_type:
        query = query.filter(Job.job_type == job_type.lower())
    
    # Remote type filter
    if remote_type:
        query = query.filter(Job.remote_type == remote_type.lower())
    
    # Posted date filter
    if min_posted_days:
        cutoff_date = datetime.utcnow() - timedelta(days=min_posted_days)
        query = query.filter(Job.posted_date >= cutoff_date)
    
    # Show both processed and pending jobs (pending will be processed later)
    # Filter out archived jobs
    query = query.filter(Job.processing_status != "archived")
    
    # If matched=True, get matched jobs with scores
    if matched:
        user_id = current_user["id"]
        if isinstance(user_id, str):
            import uuid
            user_id = uuid.UUID(user_id)

        # Use AI-POWERED matching service (60%+ quality matches only)
        matches = await ai_matcher.get_cached_matches(
            user_id=str(user_id),
            db=db,
            limit=page_size * 2  # Get more for pagination
        )
        
        # Extract job IDs from matches
        matched_job_ids = [match["job"].id for match in matches]
        
        if matched_job_ids:
            # Filter query to only matched jobs
            query = query.filter(Job.id.in_(matched_job_ids))
            
            # Sort by relevance score (get from job_matches table)
            job_matches = db.query(JobMatch).filter(
                and_(
                    JobMatch.user_id == user_id,
                    JobMatch.job_id.in_(matched_job_ids)
                )
            ).all()
            
            # Create a map of job_id -> relevance_score
            score_map = {match.job_id: match.relevance_score for match in job_matches}
            
            # Get total count
            total = len(matched_job_ids)
            
            # Sort matches by relevance score
            matches.sort(key=lambda x: x["relevance_score"], reverse=True)
            
            # Paginate
            offset = (page - 1) * page_size
            paginated_matches = matches[offset:offset + page_size]
            
            # Convert to JobResponse with match scores
            jobs_with_scores = []
            for match in paginated_matches:
                job = match["job"]
                job_dict = JobResponse.from_orm(job).dict()
                job_dict["match_score"] = match["relevance_score"]
                job_dict["match_reasons"] = match.get("match_reasons", [])
                jobs_with_scores.append(job_dict)
            
            total_pages = (total + page_size - 1) // page_size
            
            return JobSearchResponse(
                jobs=jobs_with_scores,
                total=total,
                page=page,
                page_size=page_size,
                total_pages=total_pages
            )
        else:
            # No matches found
            return JobSearchResponse(
                jobs=[],
                total=0,
                page=page,
                page_size=page_size,
                total_pages=0
            )
    
    # Regular search (not matched)
    # Get total count
    total = query.count()
    
    # Pagination
    offset = (page - 1) * page_size
    jobs = query.order_by(desc(Job.posted_date)).offset(offset).limit(page_size).all()
    
    total_pages = (total + page_size - 1) // page_size
    
    return JobSearchResponse(
        jobs=[JobResponse.from_orm(job) for job in jobs],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages
    )


@router.get("/{job_id}", response_model=JobResponse)
def get_job(
    job_id: uuid.UUID,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get a specific job by ID."""
    job = db.query(Job).filter(Job.id == job_id).first()
    
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job not found"
        )
    
    return JobResponse.from_orm(job)


@router.get("/sources/available", response_model=List[str])
def get_available_sources(
    current_user: dict = Depends(get_current_user),
):
    """Get list of available job scraping sources."""
    return scraper_service.get_available_sources()


@router.post("/scrape", response_model=ScrapeJobsResponse, status_code=status.HTTP_202_ACCEPTED)
def start_scraping(
    request: ScrapeJobsRequest,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Start a background job scraping task.
    
    Returns immediately with scraping job ID.
    Scraping runs in the background via Celery.
    """
    # Validate sources
    available_sources = scraper_service.get_available_sources()
    invalid_sources = [s for s in request.sources if s.lower() not in available_sources]
    if invalid_sources:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid sources: {invalid_sources}. Available: {available_sources}"
        )
    
    # Convert user_id to UUID if it's a string
    user_id = current_user["id"]
    if isinstance(user_id, str):
        user_id = uuid.UUID(user_id)
    
    # Create scraping job record
    scraping_job = ScrapingJob(
        user_id=user_id,
        sources=request.sources,
        keywords=request.keywords,
        filters={
            "location": request.location,
            "max_results_per_source": request.max_results_per_source
        },
        status="pending"
    )
    
    db.add(scraping_job)
    db.commit()
    db.refresh(scraping_job)
    
    # Start background task
    try:
        scrape_jobs_task.delay(
            scraping_job_id=str(scraping_job.id),
            sources=request.sources,
            keywords=request.keywords,
            location=request.location,
            max_results_per_source=request.max_results_per_source
        )
        logger.info(f"Started scraping job {scraping_job.id} for user {user_id}")
    except Exception as e:
        logger.error(f"Failed to start scraping task: {e}")
        scraping_job.status = "failed"
        scraping_job.error_message = str(e)
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to start scraping task: {str(e)}"
        )
    
    return ScrapeJobsResponse(
        scraping_job_id=scraping_job.id,
        status="pending",
        message="Scraping job started. Check status via /jobs/scraping/{id}"
    )


@router.get("/scraping/{scraping_job_id}", response_model=ScrapingJobResponse)
def get_scraping_job(
    scraping_job_id: uuid.UUID,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get status of a scraping job."""
    # Convert user_id to UUID if it's a string
    user_id = current_user["id"]
    if isinstance(user_id, str):
        user_id = uuid.UUID(user_id)
    
    scraping_job = db.query(ScrapingJob).filter(
        and_(
            ScrapingJob.id == scraping_job_id,
            ScrapingJob.user_id == user_id
        )
    ).first()
    
    if not scraping_job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Scraping job not found"
        )
    
    return ScrapingJobResponse.from_orm(scraping_job)


@router.get("/scraping/", response_model=List[ScrapingJobResponse])
def list_scraping_jobs(
    status_filter: Optional[str] = Query(None, description="Filter by status"),
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get list of user's scraping jobs."""
    # Convert user_id to UUID if it's a string
    user_id = current_user["id"]
    if isinstance(user_id, str):
        user_id = uuid.UUID(user_id)
    
    query = db.query(ScrapingJob).filter(ScrapingJob.user_id == user_id)
    
    if status_filter:
        query = query.filter(ScrapingJob.status == status_filter.lower())
    
    scraping_jobs = query.order_by(desc(ScrapingJob.created_at)).limit(50).all()
    
    return [ScrapingJobResponse.from_orm(job) for job in scraping_jobs]

