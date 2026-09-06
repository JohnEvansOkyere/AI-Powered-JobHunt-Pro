"""Public discovery regressions using real SQL against an isolated in-memory DB."""

import uuid
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.api.v1.dependencies import get_optional_user
from app.api.v1.endpoints import jobs
from app.api.v1.endpoints.analytics import _attribution
from app.core.database import get_db
from app.models.job import Job


@pytest.fixture
def discovery(monkeypatch):
    engine = create_engine('sqlite://', connect_args={'check_same_thread': False}, poolclass=StaticPool)
    Job.__table__.create(engine)
    db = Session(engine)
    app = FastAPI()
    app.include_router(jobs.router, prefix='/jobs')
    app.dependency_overrides[get_db] = lambda: db
    app.dependency_overrides[get_optional_user] = lambda: None
    rate = AsyncMock()
    monkeypatch.setattr(jobs, 'enforce_rate_limit', rate)
    now = datetime.now(timezone.utc)

    def add(**overrides):
        values = dict(id=uuid.uuid4(), title='Data Analyst', company='Example Employer',
                      description='Analyse data with SQL.', source='fixture', location='Accra, Ghana',
                      job_link='https://example.test/apply', processing_status='processed',
                      posted_date=now, scraped_at=now, created_at=now, updated_at=now)
        values.update(overrides)
        job = Job(**values)
        db.add(job)
        db.commit()
        return job.id

    with TestClient(app) as client:
        yield client, db, add, rate
    db.close()
    engine.dispose()


@pytest.mark.parametrize('state', [
    {'application_deadline': datetime.now(timezone.utc) - timedelta(days=1)},
    {'processing_status': 'archived'},
    {'publication_status': 'hidden'},
    {'publication_status': 'closed'},
])
def test_closed_jobs_leave_all_public_surfaces_without_deleting_history(discovery, state):
    client, db, add, rate = discovery
    live = add(source='recruiter', publication_status='published')
    closed = add(source='recruiter', **state)
    for path in ['/jobs/', '/jobs/?scope=local', '/jobs/sitemap']:
        response = client.get(path)
        assert response.status_code == 200
        body = response.json()
        rows = body if isinstance(body, list) else body['jobs']
        assert [row['id'] for row in rows] == [str(live)]
    assert client.get(f'/jobs/{closed}').status_code == 404
    assert client.get(f'/jobs/{live}').status_code == 200
    assert db.get(Job, closed) is not None
    assert rate.await_count == 5


def test_age_alone_does_not_close_recruiter_jobs_and_deadline_is_exposed(discovery):
    client, _, add, _ = discovery
    deadline = datetime.now(timezone.utc) + timedelta(days=3)
    job = add(source='recruiter', posted_date=datetime.now(timezone.utc) - timedelta(days=100), application_deadline=deadline)
    response = client.get(f'/jobs/{job}')
    assert response.status_code == 200
    assert response.json()['application_deadline'].startswith(deadline.strftime('%Y-%m-%d'))
    assert client.get('/jobs/sitemap').json()[0]['id'] == str(job)


@pytest.mark.parametrize('fields', [
    {'processing_status': 'pending'}, {'posted_date': None}, {'title': '  '},
    {'company': ' '}, {'description': ' '}, {'job_link': None},
    {'job_link': 'javascript:alert(1)'},
])
def test_incomplete_jobs_are_not_in_sitemap(discovery, fields):
    client, _, add, _ = discovery
    add(**fields)
    assert client.get('/jobs/sitemap').json() == []


def test_alternate_source_url_and_public_pagination(discovery):
    client, _, add, _ = discovery
    for _ in range(3):
        add(job_link=None, source_url='https://example.test/careers')
    assert len(client.get('/jobs/sitemap').json()) == 3
    response = client.get('/jobs/?page=2&page_size=2').json()
    assert response['total'] == 3
    assert response['total_pages'] == 2
    assert len(response['jobs']) == 1


@pytest.mark.parametrize('host,source', [
    ('chatgpt.com', 'chatgpt'), ('chat.openai.com', 'chatgpt'),
    ('www.perplexity.ai', 'perplexity'), ('claude.ai', 'claude'),
    ('gemini.google.com', 'gemini'), ('copilot.microsoft.com', 'copilot'),
])
def test_ai_referrals_are_recognized_before_general_search(host, source):
    assert _attribution({}, f'https://{host}/')['source'] == source
    assert _attribution({}, f'https://{host}/')['medium'] == 'ai'


def test_ai_attribution_preserves_explicit_campaigns_and_rejects_lookalike_hosts():
    result = _attribution({'utm_source': 'chatgpt.com', 'utm_medium': 'campaign', 'utm_campaign': 'launch'}, None)
    assert (result['source'], result['medium'], result['campaign']) == ('chatgpt', 'campaign', 'launch')
    assert _attribution({}, 'https://notchatgpt.com/')['medium'] == 'referral'
    assert _attribution({}, None)['source'] == 'direct'
