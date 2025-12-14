"""
User Profile Endpoints

Handles user profile CRUD operations including comprehensive
career targeting, skills, experience, and preferences.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field, EmailStr
from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import and_

from app.api.v1.dependencies import get_current_user
from app.core.database import get_db
from app.models.user_profile import UserProfile
from app.core.logging import get_logger
import uuid

logger = get_logger(__name__)

router = APIRouter()


# Pydantic models for request/response
class TechnicalSkill(BaseModel):
    """Technical skill with experience and confidence."""
    skill: str
    years: Optional[int] = 0
    confidence: Optional[int] = Field(1, ge=1, le=5)  # 1-5 scale


class ExperienceItem(BaseModel):
    """Work experience item."""
    role: str
    company: str
    duration: str
    achievements: List[str] = []
    metrics: Optional[Dict[str, Any]] = {}


class AIPreferences(BaseModel):
    """AI model preferences per task."""
    job_matching: Optional[str] = "gemini"
    cv_tailoring: Optional[str] = "openai"
    cover_letter: Optional[str] = "openai"
    email: Optional[str] = "grok"
    speed_vs_quality: Optional[str] = "balanced"  # "speed", "quality", "balanced"


class UserProfileCreate(BaseModel):
    """User profile creation model."""
    # Career Targeting
    primary_job_title: Optional[str] = None
    secondary_job_titles: Optional[List[str]] = None
    seniority_level: Optional[str] = None
    desired_industries: Optional[List[str]] = None
    company_size_preference: Optional[str] = None
    salary_range_min: Optional[int] = None
    salary_range_max: Optional[int] = None
    contract_type: Optional[List[str]] = None
    work_preference: Optional[str] = None
    
    # Skills & Tools
    technical_skills: Optional[List[TechnicalSkill]] = None
    soft_skills: Optional[List[str]] = None
    tools_technologies: Optional[List[str]] = None
    
    # Experience
    experience: Optional[List[ExperienceItem]] = None
    
    # Job Filtering Preferences
    preferred_keywords: Optional[List[str]] = None
    excluded_keywords: Optional[List[str]] = None
    blacklisted_companies: Optional[List[str]] = None
    job_boards_include: Optional[List[str]] = None
    job_boards_exclude: Optional[List[str]] = None
    job_freshness_days: Optional[int] = 30
    
    # Application Style
    writing_tone: Optional[str] = "professional"
    personal_branding_summary: Optional[str] = None
    first_person: Optional[bool] = True
    email_length_preference: Optional[str] = "medium"
    
    # Language & Localization
    preferred_language: Optional[str] = "en"
    local_job_market: Optional[str] = None
    
    # AI Preferences
    ai_preferences: Optional[AIPreferences] = None


class UserProfileUpdate(UserProfileCreate):
    """User profile update model (all fields optional)."""
    pass


class UserProfileResponse(BaseModel):
    """User profile response model."""
    id: str
    user_id: str
    primary_job_title: Optional[str] = None
    secondary_job_titles: Optional[List[str]] = None
    seniority_level: Optional[str] = None
    desired_industries: Optional[List[str]] = None
    company_size_preference: Optional[str] = None
    salary_range_min: Optional[int] = None
    salary_range_max: Optional[int] = None
    contract_type: Optional[List[str]] = None
    work_preference: Optional[str] = None
    technical_skills: Optional[List[Dict[str, Any]]] = None
    soft_skills: Optional[List[str]] = None
    tools_technologies: Optional[List[str]] = None
    experience: Optional[List[Dict[str, Any]]] = None
    preferred_keywords: Optional[List[str]] = None
    excluded_keywords: Optional[List[str]] = None
    blacklisted_companies: Optional[List[str]] = None
    job_boards_include: Optional[List[str]] = None
    job_boards_exclude: Optional[List[str]] = None
    job_freshness_days: Optional[int] = 30
    writing_tone: Optional[str] = None
    personal_branding_summary: Optional[str] = None
    first_person: Optional[bool] = True
    email_length_preference: Optional[str] = None
    preferred_language: Optional[str] = "en"
    local_job_market: Optional[str] = None
    ai_preferences: Optional[Dict[str, Any]] = None
    created_at: str
    updated_at: str

    class Config:
        from_attributes = True


def profile_to_response(profile: UserProfile) -> UserProfileResponse:
    """
    Convert SQLAlchemy UserProfile model to Pydantic response model.
    Handles UUID and datetime serialization.
    
    Args:
        profile: SQLAlchemy UserProfile instance
        
    Returns:
        UserProfileResponse: Pydantic response model
    """
    return UserProfileResponse(
        id=str(profile.id),
        user_id=str(profile.user_id),
        primary_job_title=profile.primary_job_title,
        secondary_job_titles=profile.secondary_job_titles,
        seniority_level=profile.seniority_level,
        desired_industries=profile.desired_industries,
        company_size_preference=profile.company_size_preference,
        salary_range_min=profile.salary_range_min,
        salary_range_max=profile.salary_range_max,
        contract_type=profile.contract_type,
        work_preference=profile.work_preference,
        technical_skills=profile.technical_skills,
        soft_skills=profile.soft_skills,
        tools_technologies=profile.tools_technologies,
        experience=profile.experience,
        preferred_keywords=profile.preferred_keywords,
        excluded_keywords=profile.excluded_keywords,
        blacklisted_companies=profile.blacklisted_companies,
        job_boards_include=profile.job_boards_include,
        job_boards_exclude=profile.job_boards_exclude,
        job_freshness_days=profile.job_freshness_days,
        writing_tone=profile.writing_tone,
        personal_branding_summary=profile.personal_branding_summary,
        first_person=profile.first_person,
        email_length_preference=profile.email_length_preference,
        preferred_language=profile.preferred_language,
        local_job_market=profile.local_job_market,
        ai_preferences=profile.ai_preferences,
        created_at=profile.created_at.isoformat() if profile.created_at else "",
        updated_at=profile.updated_at.isoformat() if profile.updated_at else "",
    )


@router.get("/me", response_model=UserProfileResponse)
async def get_my_profile(
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Get current user's profile.
    
    Returns:
        UserProfileResponse: User profile data
    """
    try:
        # Convert user_id string to UUID
        user_id_str = current_user.get("id")
        if not user_id_str:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid user ID",
            )
        user_id = uuid.UUID(str(user_id_str))
    except (ValueError, TypeError) as e:
        logger.error(f"Invalid user ID format: {user_id_str}, error: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid user ID format",
        )
    
    try:
        profile = db.query(UserProfile).filter(UserProfile.user_id == user_id).first()
        
        if not profile:
            # Auto-create empty profile if it doesn't exist (lazy creation)
            # This handles cases where the database trigger didn't fire
            logger.info(f"Profile not found for user {user_id}, creating empty profile")
            try:
                profile = UserProfile(user_id=user_id)
                db.add(profile)
                db.commit()
                db.refresh(profile)
                logger.info(f"Auto-created profile for user {user_id}")
            except Exception as create_error:
                db.rollback()
                logger.error(f"Failed to create profile for user {user_id}: {create_error}")
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Failed to create profile. Please try again.",
                )
        
        return profile_to_response(profile)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Database error getting profile for user {user_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Database connection error. Please check your database configuration.",
        )


@router.post("", response_model=UserProfileResponse, status_code=status.HTTP_201_CREATED)
async def create_profile(
    profile_data: UserProfileCreate,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Create user profile.
    
    Args:
        profile_data: Profile data to create
        
    Returns:
        UserProfileResponse: Created profile
    """
    try:
        user_id_str = current_user.get("id")
        if not user_id_str:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid user ID",
            )
        user_id = uuid.UUID(str(user_id_str))
    except (ValueError, TypeError) as e:
        logger.error(f"Invalid user ID format: {user_id_str}, error: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid user ID format",
        )
    
    # Check if profile already exists
    existing = db.query(UserProfile).filter(UserProfile.user_id == user_id).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Profile already exists. Use PUT to update.",
        )
    
    # Prepare data for database
    profile_dict = profile_data.model_dump(exclude_unset=True)
    
    # Convert technical_skills to JSONB format
    if "technical_skills" in profile_dict and profile_dict["technical_skills"]:
        profile_dict["technical_skills"] = [
            skill.model_dump() if isinstance(skill, TechnicalSkill) else skill
            for skill in profile_dict["technical_skills"]
        ]
    
    # Convert experience to JSONB format
    if "experience" in profile_dict and profile_dict["experience"]:
        profile_dict["experience"] = [
            exp.model_dump() if isinstance(exp, ExperienceItem) else exp
            for exp in profile_dict["experience"]
        ]
    
    # Convert AI preferences to JSONB format
    if "ai_preferences" in profile_dict and profile_dict["ai_preferences"]:
        if isinstance(profile_dict["ai_preferences"], AIPreferences):
            profile_dict["ai_preferences"] = profile_dict["ai_preferences"].model_dump()
    
    # Create profile
    profile = UserProfile(user_id=user_id, **profile_dict)
    db.add(profile)
    db.commit()
    db.refresh(profile)
    
    logger.info(f"Created profile for user {user_id}")
    
    return profile_to_response(profile)


@router.put("", response_model=UserProfileResponse)
async def update_profile(
    profile_data: UserProfileUpdate,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Update user profile.
    
    Args:
        profile_data: Profile data to update (all fields optional)
        
    Returns:
        UserProfileResponse: Updated profile
    """
    try:
        user_id_str = current_user.get("id")
        if not user_id_str:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid user ID",
            )
        user_id = uuid.UUID(str(user_id_str))
    except (ValueError, TypeError) as e:
        logger.error(f"Invalid user ID format: {user_id_str}, error: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid user ID format",
        )
    
    profile = db.query(UserProfile).filter(UserProfile.user_id == user_id).first()
    
    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Profile not found. Use POST to create.",
        )
    
    # Prepare update data
    update_data = profile_data.model_dump(exclude_unset=True)
    
    # Convert technical_skills to JSONB format
    if "technical_skills" in update_data and update_data["technical_skills"]:
        update_data["technical_skills"] = [
            skill.model_dump() if isinstance(skill, TechnicalSkill) else skill
            for skill in update_data["technical_skills"]
        ]
    
    # Convert experience to JSONB format
    if "experience" in update_data and update_data["experience"]:
        update_data["experience"] = [
            exp.model_dump() if isinstance(exp, ExperienceItem) else exp
            for exp in update_data["experience"]
        ]
    
    # Convert AI preferences to JSONB format
    if "ai_preferences" in update_data and update_data["ai_preferences"]:
        if isinstance(update_data["ai_preferences"], AIPreferences):
            update_data["ai_preferences"] = update_data["ai_preferences"].model_dump()
    
    # Update profile
    for key, value in update_data.items():
        setattr(profile, key, value)
    
    db.commit()
    db.refresh(profile)
    
    logger.info(f"Updated profile for user {user_id}")
    
    return profile_to_response(profile)


@router.delete("", status_code=status.HTTP_204_NO_CONTENT)
async def delete_profile(
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Delete user profile.
    
    Returns:
        None (204 No Content)
    """
    try:
        user_id_str = current_user.get("id")
        if not user_id_str:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid user ID",
            )
        user_id = uuid.UUID(str(user_id_str))
    except (ValueError, TypeError) as e:
        logger.error(f"Invalid user ID format: {user_id_str}, error: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid user ID format",
        )
    
    profile = db.query(UserProfile).filter(UserProfile.user_id == user_id).first()
    
    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Profile not found",
        )
    
    db.delete(profile)
    db.commit()
    
    logger.info(f"Deleted profile for user {user_id}")
    
    return None

