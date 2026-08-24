"""Admin-only bulk job import from curated digests (ALX Ghana Community)."""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.api.v1.dependencies import require_admin
from app.core.database import get_db
from app.core.logging import get_logger
from app.services.alx_job_importer import (
    AlxImportStats,
    AlxJobImportService,
    ParsedAlxJob,
    parse_digest_pdf,
)
from app.services.external_job_parser import ExternalJobParser

router = APIRouter()
logger = get_logger(__name__)

MAX_DIGEST_BYTES = 10 * 1024 * 1024
MAX_ENTRIES_PER_IMPORT = 200
ENRICHMENT_CONCURRENCY = 5
ENRICHMENT_TIMEOUT_SECONDS = 45


class AlxImportEntry(BaseModel):
    """One approved digest entry sent back from the preview step."""

    index: int = 0
    company: str = Field(min_length=1, max_length=300)
    title: str = Field(min_length=1, max_length=300)
    apply_url: str = Field(min_length=1, max_length=2000)
    deadline: Optional[str] = None
    raw_headline: str = ""


class AlxImportRequest(BaseModel):
    entries: List[AlxImportEntry] = Field(min_length=1, max_length=MAX_ENTRIES_PER_IMPORT)
    enrich: bool = True


def _to_parsed(entry: AlxImportEntry) -> ParsedAlxJob:
    deadline = None
    if entry.deadline:
        try:
            deadline = datetime.fromisoformat(entry.deadline)
        except ValueError:
            deadline = None
        if deadline is not None and deadline.tzinfo is None:
            deadline = deadline.replace(tzinfo=timezone.utc)

    return ParsedAlxJob(
        index=entry.index,
        company=entry.company.strip(),
        title=entry.title.strip(),
        apply_url=entry.apply_url.strip(),
        deadline=deadline,
        raw_headline=entry.raw_headline,
    )


async def _read_digest(file: UploadFile) -> bytes:
    filename = (file.filename or "").lower()
    if not filename.endswith(".pdf"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only PDF digests are supported.",
        )

    content = await file.read()
    if not content:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="The uploaded file is empty.",
        )
    if len(content) > MAX_DIGEST_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="Digest is too large. Maximum size: 10MB",
        )
    if not content.startswith(b"%PDF"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="The uploaded file is not a valid PDF.",
        )
    return content


@router.post("/alx/preview")
async def preview_alx_digest(
    file: UploadFile = File(...),
    current_user: dict = Depends(require_admin),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """Parse a weekly ALX digest and report what would be imported. Read-only."""
    content = await _read_digest(file)

    try:
        parsed = parse_digest_pdf(content)
    except Exception as exc:
        logger.exception("Failed to parse ALX digest")
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Could not read the digest PDF: {exc}",
        )

    if not parsed:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="No job entries were found in this PDF. Expected lines like "
            "'1. Company is hiring a role.' followed by an apply link.",
        )

    service = AlxJobImportService(db)
    already_imported = service.existing_by_origin_id(job.origin_job_id for job in parsed)

    entries: List[Dict[str, Any]] = []
    for job in parsed:
        payload = job.as_dict()
        existing = already_imported.get(job.origin_job_id)
        if existing is not None:
            payload["status"] = "already_imported"
            payload["existing_job_id"] = str(existing.id)
        else:
            duplicate = service.find_existing_by_url(job.apply_url)
            if duplicate is not None:
                payload["status"] = "duplicate_of_scraped"
                payload["existing_job_id"] = str(duplicate.id)
                payload["existing_source"] = duplicate.source
            else:
                payload["status"] = "new"
        entries.append(payload)

    counts: Dict[str, int] = {}
    for entry in entries:
        counts[entry["status"]] = counts.get(entry["status"], 0) + 1

    return {
        "filename": file.filename,
        "parsed": len(entries),
        "counts": counts,
        "entries": entries,
    }


@router.post("/alx/commit", status_code=status.HTTP_201_CREATED)
async def commit_alx_digest(
    payload: AlxImportRequest,
    current_user: dict = Depends(require_admin),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """Import approved digest entries as Ghana-local jobs."""
    submitted = [_to_parsed(entry) for entry in payload.entries]
    stats = AlxImportStats(parsed=len(submitted))

    now = datetime.now(timezone.utc)
    parsed_entries = []
    for entry in submitted:
        if entry.deadline is not None and entry.deadline < now:
            stats.skipped_expired += 1
            continue
        parsed_entries.append(entry)

    service = AlxJobImportService(db)
    enrichment_by_url: Dict[str, Dict[str, Any]] = {}
    if payload.enrich:
        enrichment_by_url = await _enrich_entries(parsed_entries, stats)

    imported: List[Dict[str, Any]] = []
    for entry in parsed_entries:
        try:
            values = service.build_job_values(
                entry, enrichment_by_url.get(entry.apply_url)
            )
            job, created = service.upsert(values)
        except Exception as exc:
            db.rollback()
            stats.errors.append(f"{entry.title} @ {entry.company}: {exc}")
            logger.exception("Failed to import ALX entry %s", entry.apply_url)
            continue

        if created:
            stats.created += 1
        else:
            stats.updated += 1
        imported.append(
            {
                "job_id": str(job.id),
                "title": job.title,
                "company": job.company,
                "created": created,
            }
        )

    db.commit()
    _queue_embeddings(item["job_id"] for item in imported)

    logger.info(
        "ALX import by admin %s: %s created, %s updated, %s enrichment failures",
        current_user.get("id"),
        stats.created,
        stats.updated,
        stats.enrichment_failed,
    )
    return {"stats": stats.as_dict(), "jobs": imported}


async def _enrich_entries(
    entries: List[ParsedAlxJob],
    stats: AlxImportStats,
) -> Dict[str, Dict[str, Any]]:
    """Fetch each apply URL and extract a full listing. Failures are tolerated."""
    parser = ExternalJobParser()
    semaphore = asyncio.Semaphore(ENRICHMENT_CONCURRENCY)
    results: Dict[str, Dict[str, Any]] = {}

    async def enrich(entry: ParsedAlxJob) -> None:
        async with semaphore:
            try:
                data = await asyncio.wait_for(
                    parser.parse_from_url(entry.apply_url),
                    timeout=ENRICHMENT_TIMEOUT_SECONDS,
                )
                if isinstance(data, dict):
                    results[entry.apply_url] = data
            except Exception as exc:
                stats.enrichment_failed += 1
                logger.warning(
                    "ALX enrichment failed for %s: %s", entry.apply_url, exc
                )

    await asyncio.gather(*(enrich(entry) for entry in entries))
    return results


def _queue_embeddings(job_ids) -> None:
    """Best-effort embedding refresh; import failures must not fail the import."""
    try:
        from app.tasks.embeddings import embed_job_task
    except Exception:
        logger.warning("Embedding task unavailable; skipping ALX embedding refresh")
        return

    for job_id in job_ids:
        try:
            embed_job_task.delay(job_id)
        except Exception as exc:
            logger.warning("Could not queue embedding for job %s: %s", job_id, exc)
