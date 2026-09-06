"""No providers, storage or live database: use the actual profile/CV models."""
import asyncio
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import BackgroundTasks, HTTPException
from starlette.requests import Request

from app.models.cv import CV
from app.models.user_profile import UserProfile
from app.services.embedding_pipeline import user_embedding_text, USER_TEXT_CHAR_BUDGET
from app.services.matching_readiness import matching_ready, active_parsed_cv
from app.services.recommendation_engine_v2 import RecommendationEngineV2


def profile():
    return UserProfile(primary_job_title="Accountant", seniority_level="entry", work_preference="flexible", technical_skills=[{"skill": "Excel"}])


def cv(**overrides):
    values = dict(is_active=True, parsing_status="completed", parsed_content={
        "personal_info": {"name": "Private Candidate", "email": "private@example.test", "phone": "private-phone"},
        "summary": "Financial reporting specialist",
        "skills": {"technical": ["Bookkeeping", "Excel"]},
        "experience": [{"title": "Accounts assistant", "company": "Example Ltd", "description": "Prepared monthly ledgers"}],
        "education": [{"degree": "Accounting diploma", "institution": "Example College"}],
    }, raw_text="Do not embed raw personal contact data")
    values.update(overrides)
    return CV(**values)


def test_real_cv_and_profile_both_reach_matching_input():
    text = user_embedding_text(profile(), cv())
    for evidence in ("Accountant", "flexible", "Excel", "Bookkeeping", "Financial reporting", "Accounts assistant", "monthly ledgers", "Accounting diploma"):
        assert evidence in text
    for private in ("Private Candidate", "private@example.test", "private-phone", "raw personal"):
        assert private not in text


def test_profile_cannot_crowd_cv_out_of_embedding_budget():
    candidate = profile()
    candidate.personal_branding_summary = "long profile " * 2000
    text = user_embedding_text(candidate, cv())
    assert len(text) <= USER_TEXT_CHAR_BUDGET
    assert "Bookkeeping" in text


@pytest.mark.parametrize("changes", [{"is_active": False}, {"parsing_status": "pending"}, {"parsing_status": "processing"}, {"parsing_status": "failed"}, {"parsed_content": None}, {"parsed_content": {}}])
def test_cv_must_be_active_and_parsed(changes):
    candidate_cv = cv(**changes)
    assert not matching_ready(profile(), candidate_cv)
    assert "Bookkeeping" not in user_embedding_text(profile(), candidate_cv)


def test_profile_and_cv_are_both_required():
    assert matching_ready(profile(), cv())
    assert not matching_ready(profile(), None)
    assert not matching_ready(None, cv())
    candidate = profile()
    candidate.technical_skills = [{"skill": "   "}]
    assert not matching_ready(candidate, cv())


def test_active_cv_lookup_is_owned_and_ignores_failed_or_inactive_files():
    db = MagicMock()
    owner = uuid.uuid4()
    active_parsed_cv(db, owner)
    predicates = db.query.return_value.filter.call_args.args
    sql = " ".join(str(predicate) for predicate in predicates)
    assert "cvs.user_id =" in sql
    assert predicates[0].right.value == owner
    assert "cvs.is_active IS true" in sql
    assert "cvs.parsing_status =" in sql
    assert predicates[2].right.value == "completed"


def test_cv_skills_feed_rule_scoring_and_reranking():
    skills = RecommendationEngineV2(MagicMock())._top_skills(profile(), cv=cv())
    assert skills == ["Excel", "Bookkeeping"]


def test_cv_changes_invalidate_embedding_input():
    from app.ai.embeddings import source_hash
    first = cv()
    second = cv(parsed_content={"skills": {"technical": ["Payroll"]}})
    assert source_hash(user_embedding_text(profile(), first)) != source_hash(user_embedding_text(profile(), second))


def test_generation_cannot_bypass_cv_requirement():
    from app.api.v1.endpoints.recommendations import regenerate_recommendations
    db = MagicMock()
    db.query.return_value.filter.return_value.first.return_value = profile()
    background = BackgroundTasks()
    with patch('app.api.v1.endpoints.recommendations.active_parsed_cv', return_value=None), patch('app.api.v1.endpoints.recommendations.enforce_rate_limit', new_callable=AsyncMock) as rate:
        with pytest.raises(HTTPException) as exc:
            asyncio.run(regenerate_recommendations(Request({"type": "http"}), background, {"id": str(uuid.uuid4())}, db))
        assert exc.value.status_code == 400
        assert not background.tasks
        rate.assert_not_awaited()


def test_scheduled_engine_does_not_call_providers_without_cv():
    db = MagicMock()
    db.query.return_value.filter.return_value.first.return_value = profile()
    with patch('app.services.recommendation_engine_v2.active_parsed_cv', return_value=None), patch('app.services.recommendation_engine_v2.upsert_user_embedding', new_callable=AsyncMock) as embed:
        result = asyncio.run(RecommendationEngineV2(db).run_for_user(str(uuid.uuid4())))
        assert result.total == 0
        embed.assert_not_awaited()
