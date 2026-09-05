import io
import uuid

from docx import Document
from fastapi import FastAPI
from fastapi import HTTPException
from fastapi.testclient import TestClient

from app.api.v1.endpoints.cv_generations import _owned_generation, router
from app.core.database import get_db
from app.services.cv_document import render_cv_docx
from app.services.cv_tailoring import content_hash, merge_ai_draft, normalize_cv_content


def source_cv():
    return {
        "personal_info": {
            "name": "Ama Mensah",
            "email": "ama@example.com",
            "phone": "+233200000000",
            "location": "Accra",
            "linkedin": "linkedin.com/in/ama",
            "github": "github.com/ama",
            "website": "",
        },
        "summary": "Operations professional.",
        "experience": [
            {
                "title": "Operations Officer",
                "company": "Example Ltd",
                "location": "Accra",
                "start_date": "2022",
                "end_date": "Present",
                "description": "Managed a team of 5.",
                "achievements": ["Reduced turnaround time by 20%."],
            }
        ],
        "education": [
            {
                "degree": "BSc Administration",
                "institution": "University of Ghana",
                "location": "Legon",
                "graduation_date": "2021",
                "gpa": "",
            }
        ],
        "skills": {
            "technical": ["Excel", "Power BI"],
            "languages": ["English", "Twi"],
            "certifications": [],
        },
        "projects": [],
    }


def test_merge_keeps_source_facts_and_filters_invented_skills():
    proposed = source_cv()
    proposed["personal_info"]["name"] = "Wrong Name"
    proposed["experience"][0].update(
        {
            "title": "Chief Executive",
            "company": "Invented Plc",
            "description": "Coordinated operations for senior stakeholders.",
            "achievements": ["Raised performance by 75%."],
        }
    )
    proposed["skills"]["technical"] = ["Power BI", "Python"]

    merged, warnings = merge_ai_draft(source_cv(), proposed)

    assert merged["personal_info"]["name"] == "Ama Mensah"
    assert merged["experience"][0]["title"] == "Operations Officer"
    assert merged["experience"][0]["company"] == "Example Ltd"
    assert merged["experience"][0]["description"].startswith("Coordinated")
    assert merged["skills"]["technical"] == ["Power BI"]
    assert any("number not found" in warning for warning in warnings)


def test_normalize_produces_stable_editor_shape_and_hash():
    content = normalize_cv_content({"summary": "  Clear summary  ", "skills": ["Excel"]})
    assert content["summary"] == "Clear summary"
    assert content["skills"]["technical"] == ["Excel"]
    assert content["experience"] == []
    assert content_hash(content) == content_hash(dict(reversed(list(content.items()))))


def test_docx_export_contains_candidate_and_role():
    data = render_cv_docx(source_cv())
    document = Document(io.BytesIO(data))
    text = "\n".join(paragraph.text for paragraph in document.paragraphs)
    assert "Ama Mensah" in text
    assert "Operations Officer" in text
    assert "Reduced turnaround time by 20%." in text


def test_every_cv_draft_route_rejects_anonymous_users():
    app = FastAPI()
    app.include_router(router, prefix="/cv-generations")
    app.dependency_overrides[get_db] = lambda: None
    client = TestClient(app)
    generation_id = uuid.uuid4()

    requests = [
        client.get("/cv-generations"),
        client.post("/cv-generations", json={"job_id": str(uuid.uuid4())}),
        client.get(f"/cv-generations/{generation_id}"),
        client.patch(
            f"/cv-generations/{generation_id}",
            json={"content": source_cv(), "expected_revision": 1},
        ),
        client.get(f"/cv-generations/{generation_id}/download.docx"),
    ]

    assert all(response.status_code in {401, 403} for response in requests)


def test_private_draft_lookup_always_filters_by_owner():
    class Query:
        def __init__(self):
            self.filters = ()

        def filter(self, *filters):
            self.filters = filters
            return self

        def first(self):
            return None

    class DB:
        def __init__(self):
            self.query_result = Query()

        def query(self, _model):
            return self.query_result

    db = DB()
    owner_id = uuid.uuid4()
    try:
        _owned_generation(db, uuid.uuid4(), owner_id)
        assert False, "lookup should hide missing or foreign drafts"
    except HTTPException as exc:
        assert exc.status_code == 404

    assert len(db.query_result.filters) == 2
    assert db.query_result.filters[1].left.key == "user_id"
    assert db.query_result.filters[1].right.value == owner_id
