"""Unit tests for the Recommendations V2 pipeline.

Tests are deliberately free of DB I/O and live-provider calls. They
focus on the pieces that are most likely to regress silently:

1.  Tier assignment rules (from docs/RECOMMENDATIONS_V2_PLAN.md §5.3).
2.  Sub-score functions (freshness, title_alignment, skill_overlap).
3.  Reranker JSON parsing and validation guardrails (§5.4).
4.  Embedding deduplication logic.
5.  source_hash stability (change detection for cache short-circuit).
"""

import asyncio
import json
from datetime import datetime, timedelta, timezone
from typing import List, Optional
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


# ---- Helpers to make test models without DB --------------------------------

def make_job(
    *,
    title: str = "Software Engineer",
    company: str = "Acme",
    location: Optional[str] = "Remote",
    description: str = "Python Django REST API",
    skills: Optional[str] = None,
    requirements: Optional[str] = None,
    source: str = "remoteok",
    scraped_at: Optional[datetime] = None,
    posted_date: Optional[datetime] = None,
    normalized_title: Optional[str] = None,
    remote_type: Optional[str] = "remote",
    experience_level: Optional[str] = None,
) -> MagicMock:
    """Return a lightweight Job mock (no DB session required)."""
    job = MagicMock()
    job.title = title
    job.company = company
    job.location = location
    job.description = description
    job.skills = skills
    job.requirements = requirements
    job.source = source
    job.scraped_at = scraped_at or datetime.now(timezone.utc) - timedelta(hours=12)
    job.posted_date = posted_date
    job.normalized_title = normalized_title or title
    job.remote_type = remote_type
    job.experience_level = experience_level
    return job


# ---- 1. Tier assignment --------------------------------------------------


class TestAssignTier:
    from app.services.recommendation_engine_v2 import assign_tier  # noqa: PLC0415

    def test_tier1_all_conditions_met(self):
        from app.services.recommendation_engine_v2 import assign_tier

        tier = assign_tier(
            semantic_fit=0.80,
            title_alignment=0.70,
            skill_overlap=0.50,
            freshness=0.90,
            llm_rerank_score=90.0,
        )
        assert tier == "tier1"

    def test_tier1_requires_freshness(self):
        from app.services.recommendation_engine_v2 import assign_tier

        tier = assign_tier(
            semantic_fit=0.80,
            title_alignment=0.70,
            skill_overlap=0.50,
            freshness=0.50,  # below 0.8 floor
            llm_rerank_score=90.0,
        )
        assert tier != "tier1"

    def test_tier1_requires_title_or_skill(self):
        from app.services.recommendation_engine_v2 import assign_tier

        # Neither title_alignment ≥ 0.6 nor skill_overlap ≥ 0.3 → not tier1
        tier = assign_tier(
            semantic_fit=0.80,
            title_alignment=0.40,
            skill_overlap=0.10,
            freshness=0.90,
            llm_rerank_score=90.0,
        )
        assert tier != "tier1"

    def test_tier1_skill_overlap_saves_it(self):
        from app.services.recommendation_engine_v2 import assign_tier

        # Low title but high skill_overlap → still tier1
        tier = assign_tier(
            semantic_fit=0.70,
            title_alignment=0.20,
            skill_overlap=0.35,
            freshness=0.85,
            llm_rerank_score=88.0,
        )
        assert tier == "tier1"

    def test_tier2_by_rerank(self):
        from app.services.recommendation_engine_v2 import assign_tier

        tier = assign_tier(
            semantic_fit=0.40,
            title_alignment=0.10,
            skill_overlap=0.10,
            freshness=0.30,  # stale
            llm_rerank_score=65.0,  # ≥ 60 → tier2
        )
        assert tier == "tier2"

    def test_tier2_by_semantic_fit(self):
        from app.services.recommendation_engine_v2 import assign_tier

        tier = assign_tier(
            semantic_fit=0.60,  # ≥ 0.55 → tier2
            title_alignment=0.10,
            skill_overlap=0.10,
            freshness=0.30,
            llm_rerank_score=None,  # no rerank
        )
        assert tier == "tier2"

    def test_tier3_low_everything(self):
        from app.services.recommendation_engine_v2 import assign_tier

        tier = assign_tier(
            semantic_fit=0.30,
            title_alignment=0.05,
            skill_overlap=0.05,
            freshness=0.10,
            llm_rerank_score=40.0,
        )
        assert tier == "tier3"

    def test_tier3_no_rerank(self):
        from app.services.recommendation_engine_v2 import assign_tier

        tier = assign_tier(
            semantic_fit=0.30,
            title_alignment=0.05,
            skill_overlap=0.05,
            freshness=0.10,
            llm_rerank_score=None,
        )
        assert tier == "tier3"


# ---- 2. Sub-scores -------------------------------------------------------


class TestFreshnessScore:
    def test_very_fresh(self):
        from app.services.recommendation_engine_v2 import freshness_score

        job = make_job(scraped_at=datetime.now(timezone.utc) - timedelta(hours=6))
        assert freshness_score(job) == 1.0

    def test_day_old(self):
        from app.services.recommendation_engine_v2 import freshness_score

        job = make_job(scraped_at=datetime.now(timezone.utc) - timedelta(days=3))
        assert freshness_score(job) == 0.8

    def test_two_weeks(self):
        from app.services.recommendation_engine_v2 import freshness_score

        # 10 days = 240h → "≤14d" bucket → 0.4
        job = make_job(scraped_at=datetime.now(timezone.utc) - timedelta(days=10))
        assert freshness_score(job) == 0.4

    def test_old(self):
        from app.services.recommendation_engine_v2 import freshness_score

        job = make_job(scraped_at=datetime.now(timezone.utc) - timedelta(days=30))
        assert freshness_score(job) == 0.1

    def test_no_date(self):
        from app.services.recommendation_engine_v2 import freshness_score

        job = make_job()
        job.scraped_at = None
        job.posted_date = None
        assert freshness_score(job) == 0.1

    def test_posted_date_takes_priority(self):
        from app.services.recommendation_engine_v2 import freshness_score

        job = make_job(
            scraped_at=datetime.now(timezone.utc) - timedelta(days=30),  # stale scraped
            posted_date=datetime.now(timezone.utc) - timedelta(hours=10),  # fresh posted
        )
        assert freshness_score(job) == 1.0


class TestTitleAlignment:
    def test_exact_match(self):
        from app.services.recommendation_engine_v2 import title_alignment_score

        job = make_job(title="Software Engineer", normalized_title="Software Engineer")
        assert title_alignment_score(job, ["software engineer"], primary="software engineer") == 1.0

    def test_substring_match(self):
        from app.services.recommendation_engine_v2 import title_alignment_score

        job = make_job(title="Senior Software Engineer", normalized_title="Senior Software Engineer")
        score = title_alignment_score(job, ["software engineer"], primary="software engineer")
        assert score >= 0.6

    def test_no_match(self):
        from app.services.recommendation_engine_v2 import title_alignment_score

        job = make_job(title="Chef", normalized_title="Chef")
        score = title_alignment_score(job, ["Software Engineer"], primary="Software Engineer")
        assert score == 0.0

    def test_secondary_title_matches(self):
        from app.services.recommendation_engine_v2 import title_alignment_score

        job = make_job(title="Backend Engineer", normalized_title="Backend Engineer")
        score = title_alignment_score(
            job,
            ["Data Scientist", "Backend Engineer"],
            primary="Data Scientist",
        )
        assert score >= 0.6


class TestSkillOverlap:
    def test_full_overlap(self):
        from app.services.recommendation_engine_v2 import skill_overlap_score

        job = make_job(description="Python Django REST API. Requires Django and Python.")
        score = skill_overlap_score(job, ["python", "django"])
        assert score == 1.0

    def test_partial_overlap(self):
        from app.services.recommendation_engine_v2 import skill_overlap_score

        job = make_job(description="Requires Python only.")
        score = skill_overlap_score(job, ["python", "django"])
        assert 0.4 < score < 0.6

    def test_no_skills(self):
        from app.services.recommendation_engine_v2 import skill_overlap_score

        job = make_job(description="Python")
        assert skill_overlap_score(job, []) == 0.0


# ---- 3. Reranker parsing -------------------------------------------------


class TestRerankParser:
    """Test _extract_json_array and _coerce_scores without calling the LLM."""

    def test_clean_array(self):
        from app.ai.reranker import _extract_json_array

        raw = '[{"job_id":"abc","score":90,"reason":"great fit"}]'
        parsed = _extract_json_array(raw)
        assert isinstance(parsed, list)
        assert len(parsed) == 1
        assert parsed[0]["score"] == 90

    def test_strips_code_fence(self):
        from app.ai.reranker import _extract_json_array

        raw = '```json\n[{"job_id":"abc","score":70,"reason":"ok"}]\n```'
        parsed = _extract_json_array(raw)
        assert parsed is not None
        assert len(parsed) == 1

    def test_strips_prose_preamble(self):
        from app.ai.reranker import _extract_json_array

        raw = 'Sure! Here is the JSON:\n[{"job_id":"x","score":50,"reason":"meh"}]'
        parsed = _extract_json_array(raw)
        assert parsed is not None

    def test_malformed_returns_none(self):
        from app.ai.reranker import _extract_json_array

        assert _extract_json_array("not json at all") is None
        assert _extract_json_array("") is None
        assert _extract_json_array(None) is None  # type: ignore

    def test_coerce_drops_hallucinated_ids(self):
        from app.ai.reranker import _coerce_scores

        items = [
            {"job_id": "real-id", "score": 80, "reason": "match"},
            {"job_id": "fake-id", "score": 90, "reason": "invented"},
        ]
        result = _coerce_scores(items, allowed_ids={"real-id"})
        assert len(result) == 1
        assert result[0].job_id == "real-id"

    def test_coerce_clamps_reason_words(self):
        from app.ai.reranker import _coerce_scores, REASON_WORD_BUDGET

        long_reason = " ".join(["word"] * (REASON_WORD_BUDGET + 10))
        items = [{"job_id": "x", "score": 70, "reason": long_reason}]
        result = _coerce_scores(items, allowed_ids={"x"})
        assert len(result[0].reason.split()) == REASON_WORD_BUDGET

    def test_coerce_drops_out_of_range_score(self):
        from app.ai.reranker import _coerce_scores

        items = [
            {"job_id": "a", "score": -5, "reason": "neg"},
            {"job_id": "b", "score": 150, "reason": "too high"},
            {"job_id": "c", "score": 50, "reason": "ok"},
        ]
        result = _coerce_scores(items, allowed_ids={"a", "b", "c"})
        assert len(result) == 1
        assert result[0].job_id == "c"


# ---- 4. Embedding deduplication -----------------------------------------


def test_dedupe_collapses_identical():
    from app.ai.embeddings import _dedupe

    unique, inverse = _dedupe(["a", "b", "a", "c", "b"])
    assert len(unique) == 3  # a, b, c
    # Verify the inverse correctly maps back
    original = ["a", "b", "a", "c", "b"]
    reconstructed = [unique[i] for i in inverse]
    assert reconstructed == original


def test_dedupe_single_item():
    from app.ai.embeddings import _dedupe

    unique, inverse = _dedupe(["x"])
    assert unique == ["x"]
    assert inverse == [0]


def test_dedupe_all_unique():
    from app.ai.embeddings import _dedupe

    texts = ["alpha", "beta", "gamma"]
    unique, inverse = _dedupe(texts)
    assert unique == texts
    assert inverse == [0, 1, 2]


# ---- 5. source_hash stability -------------------------------------------


def test_source_hash_stable():
    from app.ai.embeddings import source_hash

    h1 = source_hash("hello world")
    h2 = source_hash("hello world")
    assert h1 == h2


def test_source_hash_sensitive():
    from app.ai.embeddings import source_hash

    h1 = source_hash("hello world")
    h2 = source_hash("Hello World")  # different casing
    assert h1 != h2


def test_source_hash_length():
    from app.ai.embeddings import source_hash

    h = source_hash("anything")
    assert len(h) == 64  # SHA-256 hex


# ---- 6. Embedding pipeline text recipe ----------------------------------


def test_job_text_includes_title():
    from app.services.embedding_pipeline import job_embedding_text

    job = make_job(title="Data Scientist", company="OpenAI")
    text = job_embedding_text(job)
    assert "Data Scientist" in text
    assert "OpenAI" in text


def test_job_text_respects_budget():
    from app.services.embedding_pipeline import job_embedding_text, JOB_TEXT_CHAR_BUDGET

    job = make_job(description="x" * 10_000)
    text = job_embedding_text(job)
    assert len(text) <= JOB_TEXT_CHAR_BUDGET


def test_user_text_uses_profile_fields():
    from app.services.embedding_pipeline import user_embedding_text

    profile = MagicMock()
    profile.primary_job_title = "ML Engineer"
    profile.secondary_job_titles = ["Data Scientist"]
    profile.seniority_level = "senior"
    profile.desired_industries = ["Tech"]
    profile.work_preference = "remote"
    profile.technical_skills = [{"skill": "Python"}, {"skill": "TensorFlow"}]
    profile.soft_skills = ["communication"]
    profile.tools_technologies = ["Docker"]
    profile.personal_branding_summary = "I build ML systems."

    text = user_embedding_text(profile, cv=None)
    assert "ML Engineer" in text
    assert "Python" in text
    assert "remote" in text


def test_user_text_empty_when_no_signal():
    from app.services.embedding_pipeline import user_embedding_text

    text = user_embedding_text(None, None)
    assert text == ""


# ---- 7. Channel bonus ---------------------------------------------------


def test_channel_bonus_recruiter():
    from app.services.recommendation_engine_v2 import channel_bonus_score

    job = make_job(source="recruiter")
    assert channel_bonus_score(job) == 1.0


def test_channel_bonus_external():
    from app.services.recommendation_engine_v2 import channel_bonus_score

    job = make_job(source="external")
    assert channel_bonus_score(job) == 0.0


def test_channel_bonus_scraped():
    from app.services.recommendation_engine_v2 import channel_bonus_score

    job = make_job(source="remoteok")
    assert channel_bonus_score(job) == 0.8
