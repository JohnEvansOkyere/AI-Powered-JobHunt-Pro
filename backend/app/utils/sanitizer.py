"""
Data Sanitization Utilities

Sanitizes user-provided data before sending to AI models to:
1. Prevent prompt injection attacks
2. Remove potentially malicious content
3. Protect sensitive information
4. Reduce token usage
"""

import re
from typing import Dict, Any, List, Optional
import html
from app.core.logging import get_logger

logger = get_logger(__name__)


class DataSanitizer:
    """Sanitizes data before sending to AI models."""

    # Common prompt injection patterns
    INJECTION_PATTERNS = [
        # System prompt overrides
        r"\bignore\s+(previous|all)\s+(instructions|prompts|commands)\b",
        r"\bdisregard\s+(previous|all)\s+(instructions|prompts|commands)\b",
        r"\bforget\s+(previous|all)\s+(instructions|prompts|commands)\b",
        r"\bnew\s+(instructions|system\s+prompt|prompt)\b",

        # Role manipulation
        r"\byou\s+are\s+(now|actually|really)\s+(a|an)\b",
        r"\bact\s+as\s+(a|an|if\s+you)\b",
        r"\bpretend\s+(to\s+be|you\s+are)\b",
        r"\broleplay\s+as\b",

        # Output manipulation
        r"\boutput\s+(exactly|only|just)\b",
        r"\brespond\s+(with|in)\s+(json|code|sql|javascript)\b",
        r"\bexecute\s+(this|the\s+following|code)\b",
        r"\brun\s+(this|the\s+following|code)\b",

        # Jailbreak attempts
        r"\bDAN\s+mode\b",
        r"\bdeveloper\s+mode\b",
        r"\bsudo\s+mode\b",
        r"\bgod\s+mode\b",
    ]

    # Sensitive data patterns (for logging/redaction)
    SENSITIVE_PATTERNS = {
        "ssn": r"\b\d{3}-\d{2}-\d{4}\b",
        "credit_card": r"\b\d{4}[\s-]?\d{4}[\s-]?\d{4}[\s-]?\d{4}\b",
        "api_key": r"\b(sk|pk|key)[-_][a-zA-Z0-9]{32,}\b",
        "password": r"(password|passwd|pwd)\s*[:=]\s*\S+",
    }

    def __init__(self):
        """Initialize sanitizer with compiled patterns."""
        self.injection_regex = re.compile(
            "|".join(self.INJECTION_PATTERNS),
            re.IGNORECASE | re.MULTILINE
        )
        self.sensitive_regexes = {
            name: re.compile(pattern, re.IGNORECASE)
            for name, pattern in self.SENSITIVE_PATTERNS.items()
        }

    def sanitize_text(
        self,
        text: str,
        max_length: Optional[int] = None,
        remove_html: bool = True,
        check_injection: bool = True
    ) -> str:
        """
        Sanitize text input.

        Args:
            text: Text to sanitize
            max_length: Maximum length (truncate if exceeded)
            remove_html: Whether to remove HTML tags
            check_injection: Whether to check for prompt injection

        Returns:
            str: Sanitized text
        """
        if not text or not isinstance(text, str):
            return ""

        # Remove null bytes
        text = text.replace("\x00", "")

        # Remove HTML if requested
        if remove_html:
            text = html.unescape(text)
            text = re.sub(r"<[^>]+>", "", text)

        # Remove excessive whitespace
        text = re.sub(r"\s+", " ", text)
        text = text.strip()

        # Check for prompt injection attempts
        if check_injection:
            matches = self.injection_regex.findall(text)
            if matches:
                logger.warning(f"Potential prompt injection detected: {matches[:3]}")
                # Remove matched patterns
                text = self.injection_regex.sub("[REDACTED]", text)

        # Truncate if needed
        if max_length and len(text) > max_length:
            text = text[:max_length] + "..."
            logger.debug(f"Text truncated to {max_length} characters")

        return text

    def sanitize_cv_data(self, cv_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Sanitize CV data structure.

        Args:
            cv_data: Original CV data

        Returns:
            dict: Sanitized CV data
        """
        if not isinstance(cv_data, dict):
            logger.warning(f"CV data is not a dict: {type(cv_data)}")
            return {}

        sanitized = {}

        # Sanitize personal info
        if "personal_info" in cv_data and isinstance(cv_data["personal_info"], dict):
            sanitized["personal_info"] = {
                "name": self.sanitize_text(
                    str(cv_data["personal_info"].get("name", "")),
                    max_length=100
                ),
                "email": self.sanitize_text(
                    str(cv_data["personal_info"].get("email", "")),
                    max_length=100
                ),
                "phone": self.sanitize_text(
                    str(cv_data["personal_info"].get("phone", "")),
                    max_length=50
                ),
                "location": self.sanitize_text(
                    str(cv_data["personal_info"].get("location", "")),
                    max_length=100
                ),
                "linkedin": self.sanitize_text(
                    str(cv_data["personal_info"].get("linkedin", "")),
                    max_length=200
                ),
                "website": self.sanitize_text(
                    str(cv_data["personal_info"].get("website", "")),
                    max_length=200
                ),
            }

        # Sanitize summary
        if "summary" in cv_data:
            sanitized["summary"] = self.sanitize_text(
                str(cv_data.get("summary", "")),
                max_length=1000
            )

        # Sanitize experience
        if "experience" in cv_data and isinstance(cv_data["experience"], list):
            sanitized["experience"] = []
            for exp in cv_data["experience"][:10]:  # Limit to 10 entries
                if isinstance(exp, dict):
                    sanitized["experience"].append({
                        "title": self.sanitize_text(str(exp.get("title", "")), max_length=200),
                        "company": self.sanitize_text(str(exp.get("company", "")), max_length=200),
                        "location": self.sanitize_text(str(exp.get("location", "")), max_length=100),
                        "start_date": self.sanitize_text(str(exp.get("start_date", "")), max_length=50),
                        "end_date": self.sanitize_text(str(exp.get("end_date", "")), max_length=50),
                        "description": self.sanitize_text(str(exp.get("description", "")), max_length=1000),
                        "achievements": [
                            self.sanitize_text(str(ach), max_length=300)
                            for ach in (exp.get("achievements", []) if isinstance(exp.get("achievements"), list) else [])[:5]
                        ]
                    })

        # Sanitize skills
        if "skills" in cv_data:
            skills_data = cv_data["skills"]
            if isinstance(skills_data, dict):
                sanitized["skills"] = {}
                for skill_category, skill_list in skills_data.items():
                    if isinstance(skill_list, list):
                        sanitized["skills"][skill_category] = [
                            self.sanitize_text(str(skill), max_length=100)
                            for skill in skill_list[:20]  # Limit to 20 per category
                        ]
            elif isinstance(skills_data, list):
                sanitized["skills"] = [
                    self.sanitize_text(str(skill), max_length=100)
                    for skill in skills_data[:30]  # Limit to 30 total
                ]

        # Sanitize education
        if "education" in cv_data and isinstance(cv_data["education"], list):
            sanitized["education"] = []
            for edu in cv_data["education"][:5]:  # Limit to 5 entries
                if isinstance(edu, dict):
                    sanitized["education"].append({
                        "degree": self.sanitize_text(str(edu.get("degree", "")), max_length=200),
                        "institution": self.sanitize_text(str(edu.get("institution", "")), max_length=200),
                        "location": self.sanitize_text(str(edu.get("location", "")), max_length=100),
                        "graduation_date": self.sanitize_text(str(edu.get("graduation_date", "")), max_length=50),
                        "gpa": self.sanitize_text(str(edu.get("gpa", "")), max_length=20),
                    })

        # Sanitize projects
        if "projects" in cv_data and isinstance(cv_data["projects"], list):
            sanitized["projects"] = []
            for proj in cv_data["projects"][:10]:  # Limit to 10 entries
                if isinstance(proj, dict):
                    sanitized["projects"].append({
                        "name": self.sanitize_text(str(proj.get("name", "")), max_length=200),
                        "description": self.sanitize_text(str(proj.get("description", "")), max_length=800),
                        "technologies": [
                            self.sanitize_text(str(tech), max_length=100)
                            for tech in (proj.get("technologies", []) if isinstance(proj.get("technologies"), list) else [])[:10]
                        ],
                        "url": self.sanitize_text(str(proj.get("url", "")), max_length=200),
                    })

        # Sanitize certifications
        if "certifications" in cv_data and isinstance(cv_data["certifications"], list):
            sanitized["certifications"] = [
                self.sanitize_text(str(cert), max_length=200)
                for cert in cv_data["certifications"][:10]  # Limit to 10
            ]

        # Sanitize languages
        if "languages" in cv_data and isinstance(cv_data["languages"], list):
            sanitized["languages"] = [
                self.sanitize_text(str(lang), max_length=100)
                for lang in cv_data["languages"][:10]  # Limit to 10
            ]

        return sanitized

    def sanitize_job_data(self, job_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Sanitize job listing data.

        Args:
            job_data: Original job data

        Returns:
            dict: Sanitized job data
        """
        if not isinstance(job_data, dict):
            logger.warning(f"Job data is not a dict: {type(job_data)}")
            return {}

        return {
            "title": self.sanitize_text(str(job_data.get("title", "")), max_length=200),
            "company": self.sanitize_text(str(job_data.get("company", "")), max_length=200),
            "location": self.sanitize_text(str(job_data.get("location", "")), max_length=200),
            "job_type": self.sanitize_text(str(job_data.get("job_type", "")), max_length=100),
            "remote_type": self.sanitize_text(str(job_data.get("remote_type", "")), max_length=100),
            "description": self.sanitize_text(
                str(job_data.get("description", "")),
                max_length=3000,
                check_injection=True  # Important: check job descriptions for injection
            ),
            "requirements": self.sanitize_text(
                str(job_data.get("requirements", "")),
                max_length=2000
            ),
        }

    def sanitize_profile_data(self, profile_data: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Sanitize user profile data.

        Args:
            profile_data: Original profile data (can be None)

        Returns:
            dict: Sanitized profile data
        """
        if not profile_data or not isinstance(profile_data, dict):
            return {}

        sanitized = {
            "primary_job_title": self.sanitize_text(
                str(profile_data.get("primary_job_title", "")),
                max_length=200
            ),
            "seniority_level": self.sanitize_text(
                str(profile_data.get("seniority_level", "")),
                max_length=100
            ),
            "work_preference": self.sanitize_text(
                str(profile_data.get("work_preference", "")),
                max_length=100
            ),
        }

        # Sanitize technical skills
        if "technical_skills" in profile_data:
            tech_skills = profile_data["technical_skills"]
            if isinstance(tech_skills, list):
                sanitized["technical_skills"] = [
                    self.sanitize_text(
                        str(skill.get("skill", skill) if isinstance(skill, dict) else skill),
                        max_length=100
                    )
                    for skill in tech_skills[:20]  # Limit to 20
                ]

        # Sanitize soft skills
        if "soft_skills" in profile_data and isinstance(profile_data["soft_skills"], list):
            sanitized["soft_skills"] = [
                self.sanitize_text(str(skill), max_length=100)
                for skill in profile_data["soft_skills"][:10]  # Limit to 10
            ]

        return sanitized

    def check_for_sensitive_data(self, text: str) -> List[str]:
        """
        Check if text contains sensitive data patterns.

        Args:
            text: Text to check

        Returns:
            list: List of sensitive data types found
        """
        found = []
        for name, regex in self.sensitive_regexes.items():
            if regex.search(text):
                found.append(name)
                logger.warning(f"Sensitive data detected: {name}")
        return found


# Global sanitizer instance
_sanitizer: Optional[DataSanitizer] = None


def get_sanitizer() -> DataSanitizer:
    """Get or create the global sanitizer instance."""
    global _sanitizer
    if _sanitizer is None:
        _sanitizer = DataSanitizer()
    return _sanitizer
