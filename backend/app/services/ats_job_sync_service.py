"""Mirror published recruiter jobs from the ATS into the candidate platform."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Iterable, Optional
from uuid import UUID

import requests
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.logging import get_logger
from app.models.job import Job

logger = get_logger(__name__)

ATS_ORIGIN_SYSTEM = "ats"
ATS_SOURCE = "recruiter"
SYNC_OVERLAP_SECONDS = 60


@dataclass(frozen=True)
class ATSJobSyncStats:
    fetched: int = 0
    created: int = 0
    updated: int = 0
    archived: int = 0
    skipped: int = 0

    def as_dict(self) -> Dict[str, int]:
        return {
            "fetched": self.fetched,
            "created": self.created,
            "updated": self.updated,
            "archived": self.archived,
            "skipped": self.skipped,
        }


def _parse_dt(value: Optional[str]) -> Optional[datetime]:
    if not value:
        return None
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)


def job_values_from_payload(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Map one ATS publication payload into the local jobs shape."""
    published = payload.get("publication_status") == "published"
    created_at = _parse_dt(payload.get("created_at"))
    updated_at = _parse_dt(payload.get("updated_at"))
    return {
        "title": payload["title"],
        "company": payload.get("company_name") or "Hiring company",
        "location": payload.get("location"),
        "description": payload["description"],
        "job_link": payload.get("public_apply_url"),
        "source": ATS_SOURCE,
        "source_id": str(payload["id"]),
        "source_url": payload.get("public_apply_url"),
        "posted_date": created_at,
        "origin_system": ATS_ORIGIN_SYSTEM,
        "origin_job_id": str(payload["id"]),
        "origin_updated_at": updated_at,
        "ats_organization_id": UUID(str(payload["organization_id"])) if payload.get("organization_id") else None,
        "organization_name": payload.get("company_name"),
        "organization_logo_url": payload.get("company_logo_url"),
        "publication_status": payload.get("publication_status"),
        "job_type": payload.get("employment_type"),
        "experience_level": payload.get("experience_level") or payload.get("job_level"),
        "requirements": payload.get("requirements"),
        "processing_status": "processed" if published else "archived",
    }


class ATSJobSyncService:
    """Pull and upsert candidate-safe ATS job projections."""

    def __init__(self, db: Session):
        self.db = db

    def _updated_since(self) -> Optional[datetime]:
        latest = (
            self.db.query(func.max(Job.origin_updated_at))
            .filter(Job.origin_system == ATS_ORIGIN_SYSTEM)
            .scalar()
        )
        if latest is None:
            return None
        if latest.tzinfo is None:
            latest = latest.replace(tzinfo=timezone.utc)
        return latest - timedelta(seconds=SYNC_OVERLAP_SECONDS)

    def _fetch_jobs(self, *, updated_since: Optional[datetime], limit: int = 500) -> Iterable[Dict[str, Any]]:
        if not settings.ATS_PUBLISHED_JOBS_URL or not settings.ATS_SYNC_TOKEN:
            raise RuntimeError("ATS job sync is enabled but URL/token is not configured")

        params: Dict[str, Any] = {"limit": limit}
        if updated_since is not None:
            params["updated_since"] = updated_since.astimezone(timezone.utc).isoformat()

        response = requests.get(
            settings.ATS_PUBLISHED_JOBS_URL,
            headers={"X-Candidate-Sync-Token": settings.ATS_SYNC_TOKEN},
            params=params,
            timeout=settings.ATS_SYNC_TIMEOUT_SECONDS,
        )
        response.raise_for_status()
        body = response.json()
        if not body.get("success"):
            raise RuntimeError("ATS published-jobs endpoint returned an unsuccessful payload")
        return body.get("data", {}).get("jobs", [])

    def sync(self) -> ATSJobSyncStats:
        updated_since = self._updated_since()
        payloads = list(self._fetch_jobs(updated_since=updated_since))
        created = updated = archived = skipped = 0
        jobs_to_embed = []

        for payload in payloads:
            values = job_values_from_payload(payload)
            existing = (
                self.db.query(Job)
                .filter(
                    Job.origin_system == ATS_ORIGIN_SYSTEM,
                    Job.origin_job_id == values["origin_job_id"],
                )
                .first()
            )

            if existing is None:
                if values["publication_status"] != "published":
                    skipped += 1
                    continue
                job = Job(**values)
                self.db.add(job)
                self.db.flush()
                created += 1
                jobs_to_embed.append(job)
                continue

            prior_status = existing.publication_status
            prior_updated_at = existing.origin_updated_at
            if prior_updated_at == values["origin_updated_at"] and prior_status == values["publication_status"]:
                skipped += 1
                continue

            for key, value in values.items():
                setattr(existing, key, value)
            updated += 1
            if values["publication_status"] == "hidden":
                archived += 1
            else:
                jobs_to_embed.append(existing)

        self.db.commit()

        if jobs_to_embed:
            from app.tasks.embeddings import embed_job_task

            for job in jobs_to_embed:
                try:
                    embed_job_task.delay(str(job.id))
                except Exception as exc:  # pragma: no cover - broker failure is environment-specific
                    logger.warning("ats_job_sync.embedding_enqueue_failed", job_id=str(job.id), error=str(exc))

        stats = ATSJobSyncStats(
            fetched=len(payloads),
            created=created,
            updated=updated,
            archived=archived,
            skipped=skipped,
        )
        logger.info("ats_job_sync.completed", **stats.as_dict())
        return stats
