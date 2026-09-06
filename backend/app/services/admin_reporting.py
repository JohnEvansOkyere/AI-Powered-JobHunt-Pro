"""Profile reporting aligned with frontend/lib/profile-utils.ts weights.

Only completion flags leave the database; profile content is not returned.
"""

from sqlalchemy import case, func

from app.models.user_profile import UserProfile as P


def profile_checks():
    return [
        ("Job title", 10, func.length(func.trim(P.primary_job_title)) > 0),
        ("Seniority", 10, func.length(P.seniority_level) > 0),
        ("Work preference", 10, func.length(P.work_preference) > 0),
        ("Technical skills", 20, case(
            (func.jsonb_typeof(P.technical_skills) == "array", func.jsonb_array_length(P.technical_skills) > 0),
            else_=False,
        )),
        ("Soft skills", 10, func.cardinality(P.soft_skills) > 0),
        ("Work experience", 20, func.jsonb_path_exists(
            P.experience,
            '$[*] ? (@.role.type() == "string" && @.role != "" && '
            '@.company.type() == "string" && @.company != "" && '
            '@.duration.type() == "string" && @.duration != "")',
        )),
        ("Writing tone", 10, func.length(P.writing_tone) > 0),
        ("AI preferences", 10, func.length(P.ai_preferences["speed_vs_quality"].astext) > 0),
    ]


def profile_score():
    return sum(case((check, weight), else_=0) for _, weight, check in profile_checks())


def profile_status(score):
    return "complete" if score == 100 else "partial" if score else "not_started"
