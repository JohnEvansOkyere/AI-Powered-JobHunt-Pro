"""Recommendation Engine V2 — tiered, embedding-based, LLM-reranked.

Replaces the v1 ``RecommendationGenerator``. The old file is kept as
``recommendation_generator.py`` for backward compatibility (legacy
scheduler / endpoints still reference it); new code should use this module.

Pipeline per-user (see docs/RECOMMENDATIONS_V2_PLAN.md §5.6):

    1. Ensure user embedding is fresh (short-circuits on hash match).
    2. Retrieve top-200 jobs by cosine similarity (pgvector ANN or Python fallback).
    3. Compute sub-scores (title_alignment, skill_overlap, freshness, channel_bonus,
       interest_affinity).
    4. LLM-rerank the top-50 by semantic_fit.
    5. Classify into tier1 / tier2 / tier3.
    6. Upsert into job_recommendations (atomic user-level replace).

Tier rules (from the plan §5.3):
    Tier 1  — llm_rerank_score ≥ 85 AND freshness ≥ 0.8 AND (title_alignment ≥ 0.6 OR skill_overlap ≥ 0.3)
    Tier 2  — (llm_rerank_score ≥ 60 OR semantic_fit ≥ 0.55) and not Tier 1
    Tier 3  — everything else in the candidate pool
"""

from __future__ import annotations

import hashlib
import re
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Sequence, Tuple

import numpy as np
from sqlalchemy import and_, delete, or_, text
from sqlalchemy.orm import Session

from app.ai.embeddings import EmbeddingUnavailableError
from app.ai.reranker import RerankCandidate, RerankedScore, rerank_candidates
from app.core.config import settings
from app.core.logging import get_logger
from app.models.application import Application
from app.models.cv import CV
from app.models.embeddings import JobEmbedding, UserEmbedding
from app.models.job import Job
from app.models.job_recommendation import JobRecommendation
from app.models.user_profile import UserProfile
from app.services.embedding_pipeline import (
    upsert_user_embedding,
    user_embedding_text,
)

logger = get_logger(__name__)

# ---- Constants -----------------------------------------------------------

CANDIDATE_POOL_SIZE = 200
RERANK_TOP_K = 30
TIER1_CAP = 10
TIER2_CAP = 30
RECOMMENDATION_TTL_HOURS = 72  # 3 days
RECENT_JOB_WINDOW_DAYS = 14

# Tier thresholds (plan §5.3)
TIER1_RERANK_FLOOR = 85.0
TIER1_FRESHNESS_FLOOR = 0.8
TIER1_TITLE_FLOOR = 0.6
TIER1_SKILL_FLOOR = 0.3
TIER1_SEMANTIC_TITLE_FLOOR = 0.74
TIER1_STRONG_TITLE_FLOOR = 0.8
TIER1_RERANK_SEMANTIC_FLOOR = 0.70
TIER1_RERANK_WEAK_TITLE_FLOOR = 0.45
TIER2_RERANK_FLOOR = 60.0
TIER2_SEMANTIC_FLOOR = 0.55


# ---- Score helpers -------------------------------------------------------


def _same_uuid(left: Any, right: Any) -> bool:
    if left is None or right is None:
        return False
    try:
        return uuid.UUID(str(left)) == uuid.UUID(str(right))
    except (TypeError, ValueError):
        return False


def freshness_score(job: Job, *, user_id: Optional[str] = None) -> float:
    """Piecewise freshness decay on posted_date (fallback: scraped_at)."""
    if (job.source or "").lower() == "external" and _same_uuid(
        getattr(job, "added_by_user_id", None), user_id
    ):
        # Candidate-added jobs are active intent signals. Their scraped_at is
        # import time, not a reliable proxy for whether the role is still open.
        return 1.0
    ref: Optional[datetime] = job.posted_date or job.scraped_at
    if ref is None:
        return 0.1
    now = datetime.now(timezone.utc)
    # Normalise to UTC-aware
    if ref.tzinfo is None:
        ref = ref.replace(tzinfo=timezone.utc)
    age_hours = (now - ref).total_seconds() / 3600
    if age_hours <= 48:
        return 1.0
    if age_hours <= 168:
        return 0.8
    if age_hours <= 336:
        return 0.4
    return 0.1


def channel_bonus_score(job: Job, *, user_id: Optional[str] = None) -> float:
    """Source-channel quality bonus."""
    source = (job.source or "").lower()
    if source == "recruiter":
        return 1.0
    if source == "external":
        if _same_uuid(getattr(job, "added_by_user_id", None), user_id):
            return 0.6
        return 0.0
    return 0.8


_TITLE_DELIMITER_RE = re.compile(r"\s*(?:\||,|;|\bor\b)\s*", re.IGNORECASE)
_TITLE_TOKEN_RE = re.compile(r"[a-z0-9]+")
_GENERIC_TITLE_TOKENS = {
    "senior",
    "junior",
    "jr",
    "sr",
    "lead",
    "principal",
    "staff",
    "manager",
    "engineer",
    "developer",
    "specialist",
    "consultant",
    "associate",
}
_ROLE_FAMILY_ALIASES: Dict[str, Tuple[str, ...]] = {
    "ai_ml": (
        "ai engineer",
        "artificial intelligence",
        "machine learning",
        "ml engineer",
        "ml scientist",
        "deep learning",
        "nlp",
        "llm",
        "computer vision",
        "prompt engineer",
    ),
    "data_science": (
        "data scientist",
        "data science",
        "research scientist",
        "statistician",
        "statistical",
        "quantitative analyst",
        "analytics scientist",
    ),
    "data_engineering": (
        "data engineer",
        "etl",
        "elt",
        "data pipeline",
        "data platform",
        "analytics engineer",
        "warehouse",
        "spark",
        "dbt",
    ),
    "analytics_bi": (
        "data analyst",
        "business analyst",
        "business intelligence",
        "bi analyst",
        "analytics",
        "tableau",
        "power bi",
        "reporting",
    ),
    "backend": (
        "backend",
        "back end",
        "api engineer",
        "server side",
        "django",
        "fastapi",
        "node",
        "java engineer",
        "python engineer",
        "software engineer",
    ),
    "frontend": (
        "frontend",
        "front end",
        "react",
        "next.js",
        "web developer",
        "ui engineer",
        "javascript developer",
        "typescript developer",
    ),
    "fullstack": (
        "full stack",
        "fullstack",
        "software engineer",
        "web engineer",
    ),
    "devops_cloud": (
        "devops",
        "sre",
        "site reliability",
        "cloud engineer",
        "platform engineer",
        "infrastructure",
        "kubernetes",
        "terraform",
        "aws",
        "azure",
        "gcp",
    ),
    "security": (
        "security engineer",
        "cybersecurity",
        "application security",
        "appsec",
        "infosec",
        "security analyst",
        "penetration",
    ),
    "mobile": (
        "mobile",
        "android",
        "ios",
        "swift",
        "kotlin",
        "react native",
        "flutter",
    ),
    "qa": (
        "qa",
        "quality assurance",
        "test engineer",
        "automation tester",
        "sdet",
        "software testing",
    ),
    "product": (
        "product manager",
        "product owner",
        "growth product",
        "technical product",
        "program manager",
    ),
    "design": (
        "product designer",
        "ux",
        "ui designer",
        "user experience",
        "visual designer",
    ),
}
_ROLE_FAMILY_RELATEDNESS: Dict[Tuple[str, str], float] = {
    ("ai_ml", "data_science"): 0.78,
    ("ai_ml", "data_engineering"): 0.55,
    ("ai_ml", "backend"): 0.50,
    ("data_science", "analytics_bi"): 0.68,
    ("data_science", "data_engineering"): 0.58,
    ("data_engineering", "analytics_bi"): 0.62,
    ("backend", "fullstack"): 0.78,
    ("frontend", "fullstack"): 0.78,
    ("backend", "devops_cloud"): 0.55,
    ("devops_cloud", "security"): 0.45,
    ("frontend", "design"): 0.45,
    ("mobile", "frontend"): 0.42,
    ("qa", "backend"): 0.35,
}


def _title_tokens(value: str) -> set[str]:
    return set(_TITLE_TOKEN_RE.findall(value.lower()))


def _normalize_title_text(value: str) -> str:
    return re.sub(r"\s+", " ", value.lower().replace("/", " ").replace("-", " ")).strip()


def role_families(value: str) -> set[str]:
    """Return broad role families detected from a title-like string."""
    text = _normalize_title_text(value)
    tokens = _title_tokens(text)
    families: set[str] = set()
    for family, aliases in _ROLE_FAMILY_ALIASES.items():
        for alias in aliases:
            alias_norm = _normalize_title_text(alias)
            alias_tokens = _title_tokens(alias_norm)
            if alias_norm in text or (alias_tokens and alias_tokens.issubset(tokens)):
                families.add(family)
                break
    return families


def _related_role_family_score(target_families: set[str], job_families: set[str]) -> float:
    if not target_families or not job_families:
        return 0.0
    if target_families & job_families:
        return 0.85
    best = 0.0
    for left in target_families:
        for right in job_families:
            best = max(
                best,
                _ROLE_FAMILY_RELATEDNESS.get((left, right), 0.0),
                _ROLE_FAMILY_RELATEDNESS.get((right, left), 0.0),
            )
    return best


def split_target_titles(raw: Optional[str]) -> List[str]:
    """Split user-entered target title strings into individual titles.

    Users commonly paste titles as "Data Scientist | AI/ML Engineer".
    Keep slash-delimited phrases intact so "AI/ML Engineer" does not become
    two weaker titles.
    """
    if not raw:
        return []
    return [part.strip() for part in _TITLE_DELIMITER_RE.split(raw) if part.strip()]


def title_alignment_score(
    job: Job,
    target_titles: Sequence[str],
    *,
    primary: Optional[str] = None,
) -> float:
    """Overlap between job title and the user's target titles."""
    job_title_lower = (job.normalized_title or job.title or "").lower()
    if not job_title_lower:
        return 0.0
    best = 0.0
    for t in [primary or ""] + list(target_titles):
        t = t.strip().lower()
        if not t:
            continue
        if t == job_title_lower:
            return 1.0
        if t in job_title_lower or job_title_lower in t:
            best = max(best, 0.75)
        words_t = _title_tokens(t)
        words_j = _title_tokens(job_title_lower)
        common = words_t & words_j
        best = max(best, _related_role_family_score(role_families(t), role_families(job_title_lower)))
        meaningful_t = words_t - _GENERIC_TITLE_TOKENS
        meaningful_common = common - _GENERIC_TITLE_TOKENS
        if meaningful_common:
            ratio = len(meaningful_common) / max(len(meaningful_t), 1)
            best = max(best, 0.45 * min(1.0, ratio))
    return best


def skill_overlap_score(job: Job, top_skills: Sequence[str]) -> float:
    """Fraction of user's top skills found in the job's normalised text."""
    if not top_skills:
        return 0.0
    haystack = " ".join(
        filter(None, [job.title, job.description, job.skills, job.requirements])
    ).lower()
    hits = sum(1 for s in top_skills if s.lower() in haystack)
    return hits / len(top_skills)


def _cosine(a: List[float], b: List[float]) -> float:
    av, bv = np.array(a, dtype=np.float32), np.array(b, dtype=np.float32)
    na, nb = np.linalg.norm(av), np.linalg.norm(bv)
    if na == 0 or nb == 0:
        return 0.0
    return float(np.dot(av, bv) / (na * nb))


def composite_score(
    semantic_fit: float,
    title_alignment: float,
    skill_overlap: float,
    freshness: float,
    channel_bonus: float,
    interest_affinity: Optional[float],
    llm_rerank_score: Optional[float],
) -> float:
    """Weighted composite used for ordering within a tier (not for tiering)."""
    deterministic = (
        0.40 * semantic_fit
        + 0.25 * title_alignment
        + 0.15 * skill_overlap
        + 0.10 * freshness
        + 0.05 * channel_bonus
        + 0.05 * (interest_affinity or 0.0)
    )
    if llm_rerank_score is None:
        return min(1.0, max(0.0, deterministic))

    rerank = max(0.0, min(1.0, llm_rerank_score / 100.0))
    total = 0.80 * rerank + 0.20 * deterministic
    return min(1.0, max(0.0, total))


# ---- Tiering -------------------------------------------------------------


def assign_tier(
    *,
    semantic_fit: float,
    title_alignment: float,
    skill_overlap: float,
    freshness: float,
    llm_rerank_score: Optional[float],
) -> str:
    is_fresh_enough = freshness >= TIER1_FRESHNESS_FLOOR
    has_title_or_skill = (
        title_alignment >= TIER1_TITLE_FLOOR or skill_overlap >= TIER1_SKILL_FLOOR
    )
    rerank = llm_rerank_score if llm_rerank_score is not None else 0.0
    has_strong_semantic_title = (
        semantic_fit >= TIER1_SEMANTIC_TITLE_FLOOR
        and title_alignment >= TIER1_STRONG_TITLE_FLOOR
    )
    has_reranked_semantic_title = (
        semantic_fit >= TIER1_RERANK_SEMANTIC_FLOOR
        and title_alignment >= TIER1_RERANK_WEAK_TITLE_FLOOR
    )
    if is_fresh_enough and (
        (rerank >= TIER1_RERANK_FLOOR and (has_title_or_skill or has_reranked_semantic_title))
        or has_strong_semantic_title
    ):
        return "tier1"
    if rerank >= TIER2_RERANK_FLOOR or semantic_fit >= TIER2_SEMANTIC_FLOOR:
        return "tier2"
    return "tier3"


def _coerce_uuid(value: str) -> Optional[uuid.UUID]:
    try:
        return uuid.UUID(str(value))
    except (TypeError, ValueError):
        return None


# ---- Main service --------------------------------------------------------


@dataclass
class GenerationStats:
    user_id: str
    tier1: int = 0
    tier2: int = 0
    tier3: int = 0
    total: int = 0
    reranked: bool = False
    rerank_fallback: bool = False
    error: Optional[str] = None


class RecommendationEngineV2:
    """Stateless service; instantiate fresh per run or reuse across runs."""

    def __init__(self, db: Session):
        self.db = db

    # ---- Top-level entry -------------------------------------------------

    async def run_for_user(self, user_id: str) -> GenerationStats:
        """Full pipeline for one user. Returns stats even on partial failure."""
        stats = GenerationStats(user_id=user_id)
        try:
            await self._run(user_id, stats)
        except Exception as exc:  # noqa: BLE001 — log, never rethrow
            logger.error(
                "Recommendation run failed for user=%s: %r", user_id, exc, exc_info=True
            )
            stats.error = repr(exc)
        return stats

    async def run_for_all_eligible_users(self) -> Dict[str, Any]:
        """Iterate all users who have any profile signal."""
        user_ids = self._eligible_user_ids()
        logger.info("Running recommendations V2 for %d eligible users.", len(user_ids))
        all_stats: List[GenerationStats] = []
        for uid in user_ids:
            s = await self.run_for_user(uid)
            all_stats.append(s)
        return {
            "total_users": len(all_stats),
            "successful": sum(1 for s in all_stats if not s.error),
            "failed": sum(1 for s in all_stats if s.error),
            "tier1_total": sum(s.tier1 for s in all_stats),
            "tier2_total": sum(s.tier2 for s in all_stats),
            "tier3_total": sum(s.tier3 for s in all_stats),
        }

    # ---- Pipeline internals ----------------------------------------------

    async def _run(self, user_id: str, stats: GenerationStats) -> None:
        profile = self.db.query(UserProfile).filter(UserProfile.user_id == user_id).first()
        cv = (
            self.db.query(CV)
            .filter(CV.user_id == user_id)
            .order_by(CV.created_at.desc())
            .first()
        )
        if not profile and not cv:
            logger.info("User %s has no data; skipping.", user_id)
            return

        # 1. Ensure user embedding is current.
        try:
            await upsert_user_embedding(self.db, user_id)
        except EmbeddingUnavailableError as exc:
            logger.warning(
                "Cannot embed user %s; skipping this run: %r", user_id, exc
            )
            return

        user_emb_row: Optional[UserEmbedding] = self.db.get(UserEmbedding, user_id)
        if user_emb_row is None:
            logger.warning("User %s has no embedding after upsert; skipping.", user_id)
            return

        user_vec: List[float] = list(user_emb_row.embedding) if user_emb_row.embedding is not None else []
        model = user_emb_row.model

        # 2. Retrieve candidate pool.
        candidates = self._fetch_candidates(user_vec, model, user_id)
        if not candidates:
            logger.info("No embedding-matched candidates for user %s.", user_id)
            return

        # 3. Build profile context for scoring.
        target_titles = self._target_titles(profile)
        top_skills = self._top_skills(profile)

        # 4. Compute sub-scores.
        interest_vecs = self._interest_centroid(user_id, model)
        scored = self._score_candidates(
            candidates, user_vec, target_titles, top_skills, interest_vecs, user_id
        )

        # 5. LLM rerank the top-50 by raw semantic fit, per the V2 retrieval
        # contract. Composite ordering is recomputed after rerank scores land.
        top_50 = sorted(scored, key=lambda x: x.semantic_fit, reverse=True)[:RERANK_TOP_K]
        rerank_map = await self._rerank(top_50, target_titles, top_skills, user_id)
        stats.reranked = bool(rerank_map)
        stats.rerank_fallback = not stats.reranked

        # Apply rerank scores.
        for sc in top_50:
            if rerank_map and sc.job_id in rerank_map:
                rv = rerank_map[sc.job_id]
                sc.llm_rerank_score = rv.score
                if rv.reason:
                    sc.match_reason = rv.reason

        for sc in scored:
            sc.match_score = composite_score(
                sc.semantic_fit,
                sc.title_alignment,
                sc.skill_overlap,
                sc.freshness,
                sc.channel_bonus,
                sc.interest_affinity,
                sc.llm_rerank_score,
            )
        scored.sort(key=lambda x: x.match_score, reverse=True)

        # 6. Assign tiers and cap.
        self._classify_tiers(scored)
        to_persist = self._apply_caps(scored)

        # 7. Upsert.
        self._save(user_id, to_persist)

        counts = {"tier1": 0, "tier2": 0, "tier3": 0}
        for s in to_persist:
            counts[s.tier] += 1
        stats.tier1 = counts["tier1"]
        stats.tier2 = counts["tier2"]
        stats.tier3 = counts["tier3"]
        stats.total = len(to_persist)
        logger.info(
            "Recommendations V2 user=%s: tier1=%d tier2=%d tier3=%d reranked=%s",
            user_id,
            stats.tier1,
            stats.tier2,
            stats.tier3,
            stats.reranked,
        )

    # ---- Step helpers ----------------------------------------------------

    def _fetch_candidates(
        self,
        user_vec: List[float],
        model: str,
        user_id: str,
    ) -> List["_CandidateScore"]:
        """Try pgvector ANN first; fall back to Python cosine over recent jobs."""
        try:
            return self._fetch_via_pgvector(user_vec, model, user_id)
        except Exception as exc:  # noqa: BLE001
            logger.warning(
                "pgvector ANN failed (%r); falling back to in-memory cosine.", exc
            )
        return self._fetch_via_python(user_vec, model, user_id)

    def _fetch_via_pgvector(
        self,
        user_vec: List[float],
        model: str,
        user_id: str,
    ) -> List["_CandidateScore"]:
        """Use pgvector ``<=>`` operator (cosine distance = 1 - cosine)."""
        cutoff = datetime.now(timezone.utc) - timedelta(days=RECENT_JOB_WINDOW_DAYS)
        user_uuid = _coerce_uuid(user_id)
        raw = self.db.execute(
            text(
                """
                SELECT j.id,
                       1 - (e.embedding <=> :uvec) AS cosine
                FROM jobs j
                JOIN job_embeddings e ON e.job_id = j.id
                WHERE e.model = :model
                  AND (
                    (
                      j.source != 'external'
                      AND (j.scraped_at > :cutoff OR j.posted_date > :cutoff)
                    )
                    OR (
                      j.source = 'external'
                      AND j.added_by_user_id = :user_uuid
                    )
                  )
                ORDER BY e.embedding <=> :uvec
                LIMIT :limit
                """
            ),
            {
                "uvec": f"[{','.join(str(x) for x in user_vec)}]",
                "model": model,
                "cutoff": cutoff,
                "user_uuid": user_uuid,
                "limit": CANDIDATE_POOL_SIZE,
            },
        ).fetchall()

        if not raw:
            return []

        job_ids = [r[0] for r in raw]
        sim_map = {r[0]: float(r[1]) for r in raw}
        jobs = self.db.query(Job).filter(Job.id.in_(job_ids)).all()
        job_map = {j.id: j for j in jobs}

        return [
            _CandidateScore(
                job_id=str(jid),
                job=job_map[jid],
                semantic_fit=sim_map.get(jid, 0.0),
            )
            for jid in job_ids
            if jid in job_map
        ]

    def _fetch_via_python(
        self,
        user_vec: List[float],
        model: str,
        user_id: str,
    ) -> List["_CandidateScore"]:
        """Fallback: load all embedded recent jobs and rank in Python."""
        cutoff = datetime.now(timezone.utc) - timedelta(days=RECENT_JOB_WINDOW_DAYS)
        user_uuid = _coerce_uuid(user_id)
        non_external_recent = and_(
            Job.source != "external",
            or_(Job.scraped_at > cutoff, Job.posted_date > cutoff),
        )
        own_external = and_(
            Job.source == "external",
            Job.added_by_user_id == user_uuid,
        )
        rows = (
            self.db.query(Job, JobEmbedding.embedding)
            .join(JobEmbedding, JobEmbedding.job_id == Job.id)
            .filter(
                JobEmbedding.model == model,
                or_(non_external_recent, own_external),
            )
            .all()
        )
        scored = [
            _CandidateScore(
                job_id=str(job.id),
                job=job,
                semantic_fit=_cosine(user_vec, list(emb) if emb is not None else []),
            )
            for job, emb in rows
        ]
        scored.sort(key=lambda x: x.semantic_fit, reverse=True)
        return scored[:CANDIDATE_POOL_SIZE]

    def _score_candidates(
        self,
        candidates: List["_CandidateScore"],
        user_vec: List[float],
        target_titles: List[str],
        top_skills: List[str],
        interest_vecs: Optional[List[float]],
        user_id: str,
    ) -> List["_CandidateScore"]:
        primary = target_titles[0] if target_titles else None
        for c in candidates:
            c.title_alignment = title_alignment_score(c.job, target_titles, primary=primary)
            c.skill_overlap = skill_overlap_score(c.job, top_skills)
            c.freshness = freshness_score(c.job, user_id=user_id)
            c.channel_bonus = channel_bonus_score(c.job, user_id=user_id)
            if interest_vecs:
                c.interest_affinity = _cosine(user_vec, interest_vecs)
        for c in candidates:
            c.match_score = composite_score(
                c.semantic_fit,
                c.title_alignment,
                c.skill_overlap,
                c.freshness,
                c.channel_bonus,
                c.interest_affinity,
                c.llm_rerank_score,
            )
        candidates.sort(key=lambda x: x.match_score, reverse=True)
        return candidates

    async def _rerank(
        self,
        top_50: List["_CandidateScore"],
        target_titles: List[str],
        top_skills: List[str],
        user_id: str,
    ) -> Optional[Dict[str, RerankedScore]]:
        rc = [
            RerankCandidate(
                job_id=c.job_id,
                title=c.job.title or "",
                company=c.job.company,
                description=c.job.description or "",
            )
            for c in top_50
        ]
        try:
            results = await rerank_candidates(
                target_titles=target_titles,
                top_skills=top_skills,
                candidates=rc,
                user_id=user_id,
            )
        except Exception as exc:  # noqa: BLE001 — reranker has its own guards
            logger.warning("Rerank raised outside its guard: %r", exc)
            return None
        if results is None:
            return None
        return {r.job_id: r for r in results}

    def _classify_tiers(self, scored: List["_CandidateScore"]) -> None:
        for c in scored:
            c.tier = assign_tier(
                semantic_fit=c.semantic_fit,
                title_alignment=c.title_alignment,
                skill_overlap=c.skill_overlap,
                freshness=c.freshness,
                llm_rerank_score=c.llm_rerank_score,
            )

    def _apply_caps(self, scored: List["_CandidateScore"]) -> List["_CandidateScore"]:
        tier1 = [c for c in scored if c.tier == "tier1"][:TIER1_CAP]
        tier2 = [c for c in scored if c.tier == "tier2"][:TIER2_CAP]
        tier3 = [c for c in scored if c.tier == "tier3"]
        return tier1 + tier2 + tier3

    def _save(self, user_id: str, candidates: List["_CandidateScore"]) -> None:
        expires_at = datetime.now(timezone.utc) + timedelta(hours=RECOMMENDATION_TTL_HOURS)
        self.db.execute(
            delete(JobRecommendation).where(JobRecommendation.user_id == user_id)
        )
        for c in candidates:
            try:
                rec = JobRecommendation(
                    id=uuid.uuid4(),
                    user_id=user_id,
                    job_id=c.job_id,
                    match_score=c.match_score,
                    match_reason=c.match_reason,
                    tier=c.tier,
                    semantic_fit=c.semantic_fit,
                    title_alignment=c.title_alignment,
                    skill_overlap=c.skill_overlap,
                    freshness=c.freshness,
                    channel_bonus=c.channel_bonus,
                    interest_affinity=c.interest_affinity,
                    llm_rerank_score=c.llm_rerank_score,
                    expires_at=expires_at,
                )
                self.db.add(rec)
            except Exception as exc:  # noqa: BLE001
                logger.error("Could not persist rec for job %s: %r", c.job_id, exc)
        self.db.commit()

    # ---- Profile helpers -------------------------------------------------

    def _target_titles(self, profile: Optional[UserProfile]) -> List[str]:
        if not profile:
            return []
        out = []
        if profile.primary_job_title:
            out.extend(split_target_titles(profile.primary_job_title))
        if profile.secondary_job_titles:
            for title in profile.secondary_job_titles:
                out.extend(split_target_titles(title))
        return out

    def _top_skills(self, profile: Optional[UserProfile], n: int = 15) -> List[str]:
        if not profile:
            return []
        raw = profile.technical_skills or []
        if isinstance(raw, str):
            import json
            try:
                raw = json.loads(raw)
            except ValueError:
                return []
        skills: List[str] = []
        for item in raw:
            if isinstance(item, dict) and item.get("skill"):
                skills.append(str(item["skill"]))
            elif isinstance(item, str):
                skills.append(item)
        return skills[:n]

    def _interest_centroid(
        self, user_id: str, model: str
    ) -> Optional[List[float]]:
        """Average embedding of the user's last 10 saved/applied job embeddings."""
        recent_job_ids = (
            self.db.query(Application.job_id)
            .filter(
                and_(
                    Application.user_id == user_id,
                    Application.status.in_(["saved", "applied"]),
                )
            )
            .order_by(Application.created_at.desc())
            .limit(10)
            .all()
        )
        if len(recent_job_ids) < 3:
            return None  # too few signals per plan §5.2
        jids = [r[0] for r in recent_job_ids]
        embs = (
            self.db.query(JobEmbedding.embedding)
            .filter(JobEmbedding.job_id.in_(jids), JobEmbedding.model == model)
            .all()
        )
        if len(embs) < 3:
            return None
        arr = np.array([list(e[0]) for e in embs], dtype=np.float32)
        centroid = arr.mean(axis=0)
        norm = np.linalg.norm(centroid)
        if norm == 0:
            return None
        return (centroid / norm).tolist()

    def _eligible_user_ids(self) -> List[str]:
        from sqlalchemy import or_

        rows = (
            self.db.query(UserProfile.user_id)
            .filter(
                or_(
                    UserProfile.primary_job_title.isnot(None),
                    UserProfile.technical_skills.isnot(None),
                )
            )
            .distinct()
            .all()
        )
        from app.models.cv import CV as _CV

        cv_rows = self.db.query(_CV.user_id).distinct().all()
        user_ids = {str(r[0]) for r in rows} | {str(r[0]) for r in cv_rows}
        return list(user_ids)

    # ---- Read path (used by API endpoint) --------------------------------

    def get_for_user(
        self,
        user_id: str,
        *,
        tier: Optional[str] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> Dict[str, Any]:
        now = datetime.now(timezone.utc)
        q = self.db.query(JobRecommendation).filter(
            JobRecommendation.user_id == user_id,
            JobRecommendation.expires_at > now,
        )
        if tier:
            q = q.filter(JobRecommendation.tier == tier)
        q = q.order_by(JobRecommendation.match_score.desc())

        total = q.count()
        offset = (page - 1) * page_size
        recs = q.offset(offset).limit(page_size).all()

        return {
            "recommendations": recs,
            "total": total,
            "page": page,
            "page_size": page_size,
            "total_pages": max(1, (total + page_size - 1) // page_size),
            "tier": tier,
        }


# ---- Internal score carrier ----------------------------------------------


@dataclass
class _CandidateScore:
    """Mutable scratch-pad, internal to the pipeline. Not a DB model."""

    job_id: str
    job: Job
    semantic_fit: float = 0.0
    title_alignment: float = 0.0
    skill_overlap: float = 0.0
    freshness: float = 0.0
    channel_bonus: float = 0.0
    interest_affinity: Optional[float] = None
    llm_rerank_score: Optional[float] = None
    match_score: float = 0.0
    match_reason: Optional[str] = None
    tier: str = "tier3"
