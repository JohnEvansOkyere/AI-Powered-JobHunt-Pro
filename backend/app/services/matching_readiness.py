"""Shared profile and CV requirements for recommendation generation."""

from app.models.cv import CV
from app.models.user_profile import UserProfile
from sqlalchemy.orm import Session
from uuid import UUID


def active_parsed_cv(db: Session, user_id: str | UUID) -> CV | None:
    return db.query(CV).filter(
        CV.user_id == user_id,
        CV.is_active.is_(True),
        CV.parsing_status == "completed",
        CV.parsed_content.isnot(None),
    ).order_by(CV.updated_at.desc()).first()


def matching_ready(profile: UserProfile | None, cv: CV | None) -> bool:
    return bool(
        profile and (profile.primary_job_title or "").strip()
        and profile.seniority_level and profile.work_preference
        and isinstance(profile.technical_skills, list)
        and any(isinstance(skill, dict) and str(skill.get("skill") or "").strip() for skill in profile.technical_skills)
        and cv and cv.is_active and cv.parsing_status == "completed"
        and isinstance(cv.parsed_content, dict) and cv.parsed_content
    )
