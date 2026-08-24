"""ALX Ghana job digest importer.

The ALX Ghana Community mails a weekly PDF listing local job openings. Each
entry follows a fixed shape:

    N. <Company> is hiring a <role>.
    Apply here: <url>
    Deadline: <Month DD, YYYY>

The PDF carries a rotated watermark in the text layer (Poppins-Italic at ~50pt)
which is dropped by size, and its apply links wrap across lines in the text
layer, so URLs are read from the PDF link annotations instead.
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, Iterable, List, Optional, Tuple
from urllib.parse import urlparse, urlunparse

import pdfplumber
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.core.logging import get_logger
from app.models.job import Job

logger = get_logger(__name__)

ALX_SOURCE = "alx"
ALX_ORIGIN_SYSTEM = "alx"
DEFAULT_LOCATION = "Ghana"

# Body copy is 12pt; the watermark is ~50-65pt. Anything large is decoration.
_MAX_BODY_FONT_SIZE = 20

_ENTRY_SPLIT = re.compile(r"\n(?=\d{1,3}\.\s)")
_HEADLINE = re.compile(r"^\d{1,3}\.\s+(?P<head>.+?)\s+Apply\s+here\b", re.IGNORECASE)
_DEADLINE = re.compile(r"Deadline:?\s*(?P<date>[A-Z][a-z]+\s+\d{1,2},\s*\d{4})")
_HIRING = re.compile(
    r"^(?P<company>.+?)\s+is\s+hiring\s+(?:an?\s+|the\s+)?(?P<title>.+?)\.?$",
    re.IGNORECASE,
)
_DEADLINE_FORMATS = ("%B %d, %Y", "%b %d, %Y")


@dataclass
class ParsedAlxJob:
    """One entry lifted out of the digest, before enrichment."""

    index: int
    company: str
    title: str
    apply_url: str
    deadline: Optional[datetime]
    raw_headline: str

    @property
    def origin_job_id(self) -> str:
        return hashlib.sha256(normalize_url(self.apply_url).encode()).hexdigest()[:32]

    def as_dict(self) -> Dict[str, Any]:
        return {
            "index": self.index,
            "company": self.company,
            "title": self.title,
            "apply_url": self.apply_url,
            "deadline": self.deadline.isoformat() if self.deadline else None,
            "origin_job_id": self.origin_job_id,
            "raw_headline": self.raw_headline,
        }


@dataclass
class AlxImportStats:
    parsed: int = 0
    created: int = 0
    updated: int = 0
    skipped_duplicate: int = 0
    skipped_expired: int = 0
    enrichment_failed: int = 0
    errors: List[str] = field(default_factory=list)

    def as_dict(self) -> Dict[str, Any]:
        return {
            "parsed": self.parsed,
            "created": self.created,
            "updated": self.updated,
            "skipped_duplicate": self.skipped_duplicate,
            "skipped_expired": self.skipped_expired,
            "enrichment_failed": self.enrichment_failed,
            "errors": self.errors,
        }


def normalize_url(url: str) -> str:
    """Collapse a URL to a comparable form for de-duplication."""
    parsed = urlparse(url.strip())
    netloc = parsed.netloc.lower()
    if netloc.startswith("www."):
        netloc = netloc[4:]
    path = parsed.path.rstrip("/")
    return urlunparse(("https", netloc, path, "", parsed.query, ""))


def _parse_deadline(value: str) -> Optional[datetime]:
    cleaned = re.sub(r"\s+", " ", value).strip()
    for fmt in _DEADLINE_FORMATS:
        try:
            return datetime.strptime(cleaned, fmt).replace(tzinfo=timezone.utc)
        except ValueError:
            continue
    return None


def _is_body_char(obj: Dict[str, Any]) -> bool:
    if obj.get("object_type") != "char":
        return True
    return float(obj.get("size") or 0) < _MAX_BODY_FONT_SIZE


def _extract_lines_and_links(
    pdf: "pdfplumber.PDF",
) -> Tuple[List[Tuple[int, float, str]], List[Tuple[int, float, str]]]:
    """Return positioned body lines and positioned apply links.

    Both are keyed by (page index, vertical offset) so entries and the links
    belonging to them can be matched by position rather than by order.
    """
    lines: List[Tuple[int, float, str]] = []
    links: List[Tuple[int, float, str]] = []

    for page_index, page in enumerate(pdf.pages):
        body = page.filter(_is_body_char)
        for line in body.extract_text_lines() or []:
            text = (line.get("text") or "").strip()
            if text:
                lines.append((page_index, float(line["top"]), text))

        seen_on_page: set[str] = set()
        for annotation in sorted(page.annots or [], key=lambda a: a.get("top") or 0):
            uri = annotation.get("uri")
            if not uri or not uri.lower().startswith(("http://", "https://")):
                continue
            key = normalize_url(uri)
            if key in seen_on_page:
                continue
            seen_on_page.add(key)
            links.append((page_index, float(annotation.get("top") or 0), uri))

    lines.sort(key=lambda item: (item[0], item[1]))
    links.sort(key=lambda item: (item[0], item[1]))
    return lines, links


def _entry_spans(
    lines: List[Tuple[int, float, str]]
) -> List[Tuple[Tuple[int, float], Tuple[int, float], str]]:
    """Group body lines into numbered entries with their positional span."""
    entries: List[Tuple[Tuple[int, float], Tuple[int, float], str]] = []
    current_start: Optional[Tuple[int, float]] = None
    current_text: List[str] = []

    def flush(end: Tuple[int, float]) -> None:
        if current_start is not None and current_text:
            entries.append((current_start, end, " ".join(current_text)))

    for page_index, top, text in lines:
        if re.match(r"^\d{1,3}\.\s", text):
            flush((page_index, top))
            current_start = (page_index, top)
            current_text = [text]
        elif current_start is not None:
            current_text.append(text)

    flush((10**6, 10**6))
    return entries


def parse_digest_text(text: str, links: Optional[List[str]] = None) -> List[ParsedAlxJob]:
    """Parse already-extracted digest text. Exposed for testing."""
    normalized = re.sub(r"[ \t]+", " ", text)
    jobs: List[ParsedAlxJob] = []
    link_iter = iter(links or [])

    for block in _ENTRY_SPLIT.split(normalized):
        flat = " ".join(block.split())
        if not re.match(r"^\d{1,3}\.\s", flat):
            continue
        job = _build_job(
            index=int(flat.split(".", 1)[0]),
            flat_block=flat,
            apply_url=next(link_iter, None) or _url_in_block(flat),
        )
        if job:
            jobs.append(job)
    return jobs


def _url_in_block(flat_block: str) -> Optional[str]:
    match = re.search(r"https?://\S+", flat_block)
    return match.group(0) if match else None


def _build_job(*, index: int, flat_block: str, apply_url: Optional[str]) -> Optional[ParsedAlxJob]:
    if not apply_url:
        logger.warning("ALX digest entry %s has no apply URL; skipping", index)
        return None

    headline_match = _HEADLINE.match(flat_block)
    headline = headline_match.group("head").strip() if headline_match else ""
    if not headline:
        logger.warning("ALX digest entry %s has no parsable headline; skipping", index)
        return None

    hiring_match = _HIRING.match(headline)
    if hiring_match:
        company = hiring_match.group("company").strip(" .")
        title = hiring_match.group("title").strip(" .")
    else:
        # Entries that break the "X is hiring a Y" pattern still carry a usable
        # headline; keep it as the title rather than dropping the job.
        company = "ALX Ghana Community"
        title = headline.strip(" .")

    deadline_match = _DEADLINE.search(flat_block)
    return ParsedAlxJob(
        index=index,
        company=company,
        title=title,
        apply_url=apply_url.strip(),
        deadline=_parse_deadline(deadline_match.group("date")) if deadline_match else None,
        raw_headline=headline,
    )


def parse_digest_pdf(file_bytes: bytes) -> List[ParsedAlxJob]:
    """Extract every job entry from a weekly ALX digest PDF."""
    import io

    with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
        lines, links = _extract_lines_and_links(pdf)

    entries = _entry_spans(lines)
    if not entries:
        return []

    jobs: List[ParsedAlxJob] = []
    for position, (start, end, block_text) in enumerate(entries):
        url = _link_for_span(links, start, end) or _url_in_block(block_text)
        number = re.match(r"\s*(\d{1,3})\.", block_text)
        job = _build_job(
            index=int(number.group(1)) if number else position + 1,
            flat_block=" ".join(block_text.split()),
            apply_url=url,
        )
        if job:
            jobs.append(job)
    return jobs


def _link_for_span(
    links: List[Tuple[int, float, str]],
    start: Tuple[int, float],
    end: Tuple[int, float],
) -> Optional[str]:
    """First link whose position falls inside this entry's vertical span."""
    for page_index, top, uri in links:
        position = (page_index, top)
        if start <= position < end:
            return uri
    return None


class AlxJobImportService:
    """Turn parsed digest entries into candidate-visible job rows."""

    def __init__(self, db: Session):
        self.db = db

    def existing_by_origin_id(self, origin_ids: Iterable[str]) -> Dict[str, Job]:
        ids = [oid for oid in origin_ids]
        if not ids:
            return {}
        rows = (
            self.db.query(Job)
            .filter(Job.origin_system == ALX_ORIGIN_SYSTEM, Job.origin_job_id.in_(ids))
            .all()
        )
        return {row.origin_job_id: row for row in rows}

    def find_existing_by_url(self, apply_url: str) -> Optional[Job]:
        """Match a job already pulled in by one of the scrapers."""
        normalized = normalize_url(apply_url)
        path = urlparse(normalized).path
        if not path:
            return None
        like = f"%{path}%"
        return (
            self.db.query(Job)
            .filter(
                Job.source != ALX_SOURCE,
                or_(Job.job_link.ilike(like), Job.source_url.ilike(like)),
            )
            .first()
        )

    def build_job_values(
        self,
        parsed: ParsedAlxJob,
        enrichment: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        enrichment = enrichment or {}
        now = datetime.now(timezone.utc)

        description = (enrichment.get("description") or "").strip()
        if not description:
            description = f"{parsed.company} is hiring a {parsed.title}."

        location = (enrichment.get("location") or "").strip() or DEFAULT_LOCATION
        remote_option = enrichment.get("remote_option")

        values: Dict[str, Any] = {
            "title": (enrichment.get("title") or parsed.title).strip(),
            "company": (enrichment.get("company") or parsed.company).strip(),
            "location": location,
            "normalized_location": location.lower(),
            "description": description,
            "job_link": parsed.apply_url,
            "source": ALX_SOURCE,
            "source_id": parsed.origin_job_id,
            "source_url": parsed.apply_url,
            "posted_date": now,
            "origin_system": ALX_ORIGIN_SYSTEM,
            "origin_job_id": parsed.origin_job_id,
            "origin_updated_at": now,
            "application_deadline": parsed.deadline,
            "processing_status": "processed",
        }

        if enrichment.get("job_type"):
            values["job_type"] = str(enrichment["job_type"]).lower()
        if enrichment.get("experience_level"):
            values["experience_level"] = str(enrichment["experience_level"]).lower()
        if remote_option is not None:
            values["remote_type"] = "remote" if remote_option else "onsite"
            values["remote_option"] = str(bool(remote_option)).lower()
        for key in ("requirements", "responsibilities", "skills"):
            value = enrichment.get(key)
            if value:
                import json

                values[key] = json.dumps(value) if isinstance(value, list) else str(value)

        return values

    def upsert(self, values: Dict[str, Any]) -> Tuple[Job, bool]:
        """Insert or refresh one ALX job. Returns (job, created)."""
        existing = (
            self.db.query(Job)
            .filter(
                Job.origin_system == ALX_ORIGIN_SYSTEM,
                Job.origin_job_id == values["origin_job_id"],
            )
            .one_or_none()
        )
        if existing is None:
            job = Job(**values)
            self.db.add(job)
            self.db.flush()
            return job, True

        # Keep the original posted_date so a re-listed job does not jump the
        # recency ordering every week.
        for key, value in values.items():
            if key == "posted_date":
                continue
            setattr(existing, key, value)
        self.db.flush()
        return existing, False
