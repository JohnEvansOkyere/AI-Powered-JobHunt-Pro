"""Constants used across the application."""

from app.constants.tech_keywords import TECH_JOB_KEYWORDS
from app.constants.general_keywords import GENERAL_JOB_KEYWORDS

ALL_JOB_KEYWORDS = TECH_JOB_KEYWORDS + GENERAL_JOB_KEYWORDS

__all__ = ["TECH_JOB_KEYWORDS", "GENERAL_JOB_KEYWORDS", "ALL_JOB_KEYWORDS"]
