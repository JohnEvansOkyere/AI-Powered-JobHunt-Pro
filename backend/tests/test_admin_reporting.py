"""Reporting regressions. PostgreSQL checks use an explicitly isolated test DB."""

import os
import uuid
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.api.v1.dependencies import get_current_user, require_admin
from app.api.v1.endpoints.admin import router
from app.core.database import get_db
from app.models.user import User
from app.models.user_profile import UserProfile


@pytest.fixture
def report_app():
    app = FastAPI()
    app.include_router(router, prefix="/admin")
    return app


@pytest.mark.parametrize("path", ["/admin/users", "/admin/registrations", "/admin/overview"])
def test_reporting_requires_authentication(report_app, path):
    report_app.dependency_overrides[get_db] = lambda: MagicMock()
    response = TestClient(report_app).get(path)
    assert response.status_code in (401, 403)


@pytest.mark.parametrize("path", ["/admin/users", "/admin/registrations", "/admin/overview"])
def test_reporting_rejects_non_admin(report_app, path):
    db = MagicMock()
    db.query.return_value.filter.return_value.first.return_value = User(is_admin=False)
    report_app.dependency_overrides[get_db] = lambda: db
    report_app.dependency_overrides[get_current_user] = lambda: {"id": str(uuid.uuid4())}
    assert TestClient(report_app).get(path).status_code == 403


@pytest.fixture
def reporting_client(report_app):
    url = os.getenv("ADMIN_REPORTING_TEST_DATABASE_URL")
    if not url:
        pytest.skip("Set ADMIN_REPORTING_TEST_DATABASE_URL to an isolated PostgreSQL database")
    engine = create_engine(url)
    # A transaction rolls back both test tables and fixtures; never uses the app DB.
    with engine.connect() as connection:
        transaction = connection.begin()
        User.__table__.create(connection)
        UserProfile.__table__.create(connection)
        db = Session(bind=connection)
        now = datetime.now(timezone.utc)
        complete = dict(primary_job_title="Engineer", seniority_level="mid", work_preference="remote",
                        technical_skills=[{"skill": "Python"}], soft_skills=["Teamwork"],
                        experience=[{"role": "Engineer", "company": "Example", "duration": "2 years"}],
                        writing_tone="professional", ai_preferences={"speed_vs_quality": "balanced"})
        for name, age, fields in [
            ("Complete", 1, complete), ("Partial", 2, {"primary_job_title": "Engineer"}),
            ("Missing", 3, None), ("Empty", 4, {}),
            ("Old", 100, complete),
            ("Invalid experience", 5, {**complete, "experience": [{"role": "Engineer"}]}),
        ]:
            user_id = uuid.uuid4()
            db.add(User(id=user_id, full_name=name, email=f"{name.replace(' ', '')}@example.test",
                        created_at=now - timedelta(days=age), is_active=name != "Partial"))
            if fields is not None:
                db.add(UserProfile(user_id=user_id, **fields))
        db.flush()
        report_app.dependency_overrides[get_db] = lambda: db
        report_app.dependency_overrides[require_admin] = lambda: {"id": str(uuid.uuid4())}
        yield TestClient(report_app)
        db.close()
        transaction.rollback()
    engine.dispose()


def test_registrations_use_accounts_and_current_profile_cohort(reporting_client):
    response = reporting_client.get("/admin/registrations?days=30")
    assert response.status_code == 200, response.text
    data = response.json()
    assert (data["total_accounts"], data["signups"], data["complete"], data["partial"], data["not_started"]) == (6, 5, 1, 2, 2)
    assert sum(day["signups"] for day in data["daily"]) == 5
    assert any(day["signups"] == 0 for day in data["daily"])


@pytest.mark.parametrize("profile,expected", [
    ("complete", {"Complete"}), ("partial", {"Partial", "Invalid experience"}),
    ("not_started", {"Missing", "Empty"}),
])
def test_profile_filters_include_missing_and_empty_rows(reporting_client, profile, expected):
    response = reporting_client.get(f"/admin/users?days=30&profile={profile}")
    assert response.status_code == 200, response.text
    data = response.json()
    assert {u["full_name"] for u in data["users"]} == expected
    assert data["filtered_total"] == len(expected)
    for user in data["users"]:
        assert user["profile_status"] == profile
        assert "experience" not in user and "technical_skills" not in user


def test_user_details_search_status_and_pagination(reporting_client):
    data = reporting_client.get("/admin/users?search=partial&status=suspended").json()
    assert data["filtered_total"] == 1
    assert data["users"][0]["profile_completion"] == 10
    assert "Technical skills" in data["users"][0]["missing_fields"]
    first = reporting_client.get("/admin/users?page_size=2&page=1").json()
    second = reporting_client.get("/admin/users?page_size=2&page=2").json()
    assert first["filtered_total"] == second["filtered_total"] == 6
    assert len(first["users"]) == len(second["users"]) == 2
    assert not ({u["id"] for u in first["users"]} & {u["id"] for u in second["users"]})
    empty = reporting_client.get("/admin/users?search=nobody").json()
    assert empty["users"] == [] and empty["filtered_total"] == 0


@pytest.mark.parametrize("query", ["page=0", "page_size=101", "days=91", "profile=invalid"])
def test_report_filters_are_bounded(report_app, query):
    report_app.dependency_overrides[get_db] = lambda: MagicMock()
    report_app.dependency_overrides[require_admin] = lambda: {"id": str(uuid.uuid4())}
    assert TestClient(report_app).get(f"/admin/users?{query}").status_code == 422
