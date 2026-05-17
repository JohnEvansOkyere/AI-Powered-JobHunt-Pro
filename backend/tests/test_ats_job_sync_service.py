from datetime import datetime, timezone
from uuid import UUID

from app.services.ats_job_sync_service import job_values_from_payload


def test_job_values_from_payload_maps_published_ats_job():
    payload = {
        "id": "11111111-1111-1111-1111-111111111111",
        "organization_id": "22222222-2222-2222-2222-222222222222",
        "company_name": "Acme",
        "company_logo_url": "https://example.com/logo.png",
        "title": "Backend Engineer",
        "description": "Build APIs",
        "requirements": "Python",
        "location": "Remote",
        "employment_type": "full-time",
        "experience_level": "senior",
        "job_level": "senior",
        "public_apply_url": "https://ats.example/apply/1",
        "publication_status": "published",
        "created_at": "2026-05-17T10:00:00+00:00",
        "updated_at": "2026-05-17T10:05:00+00:00",
    }

    values = job_values_from_payload(payload)

    assert values["source"] == "recruiter"
    assert values["source_id"] == payload["id"]
    assert values["origin_system"] == "ats"
    assert values["origin_job_id"] == payload["id"]
    assert values["company"] == "Acme"
    assert values["processing_status"] == "processed"
    assert values["ats_organization_id"] == UUID(payload["organization_id"])
    assert values["origin_updated_at"] == datetime(2026, 5, 17, 10, 5, tzinfo=timezone.utc)


def test_job_values_from_payload_archives_hidden_ats_job():
    payload = {
        "id": "11111111-1111-1111-1111-111111111111",
        "organization_id": None,
        "company_name": None,
        "company_logo_url": None,
        "title": "Backend Engineer",
        "description": "Build APIs",
        "requirements": None,
        "location": None,
        "employment_type": None,
        "experience_level": None,
        "job_level": None,
        "public_apply_url": "https://ats.example/apply/1",
        "publication_status": "hidden",
        "created_at": "2026-05-17T10:00:00+00:00",
        "updated_at": "2026-05-17T10:05:00+00:00",
    }

    values = job_values_from_payload(payload)

    assert values["company"] == "Hiring company"
    assert values["processing_status"] == "archived"
