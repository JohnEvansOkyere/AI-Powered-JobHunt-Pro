"""
Pytest Configuration and Fixtures

This module provides shared fixtures for all tests including:
- Test database setup/teardown (PostgreSQL)
- Test client with mocked authentication
- Mock Supabase services
- Mock AI providers
- Test data generators
"""

import pytest
import os
from typing import Generator, Dict, Any
from unittest.mock import AsyncMock, MagicMock, patch
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session, sessionmaker
from fastapi.testclient import TestClient
import uuid

from app.main import app
from app.core.database import Base, get_db
from app.core.config import settings
from app.api.v1.dependencies import get_current_user


# =====================================================
# TEST CONFIGURATION
# =====================================================

# Use a separate test database (PostgreSQL)
# Option 1: Create a test database in Supabase
# Option 2: Use local PostgreSQL test instance
# Option 3: Mock database entirely for unit tests

TEST_DATABASE_URL = os.getenv(
    "TEST_DATABASE_URL",
    # For now, we'll use mocking approach - no real DB
    None
)


# =====================================================
# AUTHENTICATION MOCKING
# =====================================================

@pytest.fixture
def mock_user_id() -> str:
    """Generate a mock user ID (UUID format)."""
    return str(uuid.uuid4())


@pytest.fixture
def mock_user_email() -> str:
    """Generate a mock user email."""
    return "test@example.com"


@pytest.fixture
def mock_user_data(mock_user_id: str, mock_user_email: str) -> Dict[str, Any]:
    """
    Mock Supabase user data returned from get_current_user.

    This mimics the structure returned by Supabase Auth API.
    """
    return {
        "id": mock_user_id,
        "email": mock_user_email,
        "email_confirmed_at": "2024-01-01T00:00:00Z",
        "created_at": "2024-01-01T00:00:00Z",
        "user_metadata": {
            "full_name": "Test User"
        }
    }


@pytest.fixture
def mock_authenticated_user(mock_user_data: Dict[str, Any]):
    """
    Override get_current_user dependency to return mock user.

    This bypasses actual Supabase authentication for testing.
    """
    async def override_get_current_user():
        return mock_user_data

    app.dependency_overrides[get_current_user] = override_get_current_user

    yield mock_user_data

    # Cleanup
    if get_current_user in app.dependency_overrides:
        del app.dependency_overrides[get_current_user]


@pytest.fixture
def auth_headers() -> Dict[str, str]:
    """
    Create authentication headers for requests.

    Note: With mock_authenticated_user, the token value doesn't matter
    since we're bypassing actual validation.
    """
    return {
        "Authorization": "Bearer mock_test_token_12345"
    }


# =====================================================
# DATABASE MOCKING
# =====================================================

@pytest.fixture
def mock_db_session():
    """
    Mock database session for unit tests.

    For integration tests, you would use a real test database.
    """
    mock_session = MagicMock(spec=Session)

    # Configure common session methods
    mock_session.add = MagicMock()
    mock_session.commit = MagicMock()
    mock_session.rollback = MagicMock()
    mock_session.close = MagicMock()
    mock_session.refresh = MagicMock()
    mock_session.query = MagicMock()

    return mock_session


@pytest.fixture
def override_get_db(mock_db_session):
    """Override get_db dependency with mock session."""
    def override():
        try:
            yield mock_db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override

    yield mock_db_session

    if get_db in app.dependency_overrides:
        del app.dependency_overrides[get_db]


# =====================================================
# TEST CLIENT
# =====================================================

@pytest.fixture
def client() -> Generator[TestClient, None, None]:
    """
    Create a test client for making API requests.

    Note: Use with mock_authenticated_user and override_get_db
    for testing protected endpoints.
    """
    with TestClient(app) as test_client:
        yield test_client

    # Cleanup all dependency overrides
    app.dependency_overrides.clear()


# =====================================================
# SUPABASE MOCKING
# =====================================================

@pytest.fixture
def mock_supabase_storage():
    """
    Mock Supabase Storage operations.

    Mocks: upload, download, remove, create_signed_url
    """
    class MockStorageBucket:
        def upload(self, path: str, file_bytes: bytes, options: dict = None):
            """Mock file upload - returns success."""
            return MagicMock(error=None, data={"path": path})

        def download(self, path: str):
            """Mock file download - returns fake bytes."""
            return b"mock_file_content"

        def remove(self, paths: list):
            """Mock file deletion - returns success."""
            return MagicMock(error=None)

        def create_signed_url(self, path: str, expires_in: int):
            """Mock signed URL generation."""
            return {
                "signedURL": f"https://mock-storage.supabase.co/{path}?token=mock",
                "error": None
            }

    class MockStorage:
        def from_(self, bucket: str):
            return MockStorageBucket()

    return MockStorage()


@pytest.fixture
def mock_supabase_client(mock_supabase_storage):
    """
    Mock complete Supabase client.
    """
    mock_client = MagicMock()
    mock_client.storage = mock_supabase_storage

    return mock_client


# =====================================================
# AI PROVIDER MOCKING
# =====================================================

@pytest.fixture
def mock_ai_response():
    """Mock AI response for CV parsing."""
    return {
        "personal_info": {
            "name": "John Doe",
            "email": "john@example.com",
            "phone": "+1234567890",
            "location": "San Francisco, CA"
        },
        "summary": "Experienced software engineer...",
        "experience": [
            {
                "title": "Senior Software Engineer",
                "company": "Tech Corp",
                "start_date": "2020-01",
                "end_date": "Present",
                "description": "Led development of microservices"
            }
        ],
        "education": [
            {
                "degree": "BS Computer Science",
                "institution": "University of California",
                "graduation_date": "2018"
            }
        ],
        "skills": {
            "technical": ["Python", "FastAPI", "PostgreSQL"],
            "languages": ["English", "Spanish"]
        }
    }


@pytest.fixture
def mock_ai_router(mock_ai_response, monkeypatch):
    """
    Mock AI router to avoid actual API calls.

    Returns mock responses for all AI tasks.
    """
    import json

    class MockAIRouter:
        async def generate(self, task_type, prompt, **kwargs):
            """Return mock AI response based on task type."""
            if "cv_parsing" in task_type.value.lower() or "parse" in prompt.lower():
                return json.dumps(mock_ai_response)
            elif "cover_letter" in task_type.value.lower():
                return "Dear Hiring Manager,\n\nMock cover letter content..."
            elif "email" in task_type.value.lower():
                return "Subject: Application for Position\n\nMock email content..."
            else:
                return "Mock AI response"

    # Patch the get_model_router function
    from app.ai import router as ai_router_module
    monkeypatch.setattr(ai_router_module, "get_model_router", lambda: MockAIRouter())

    return MockAIRouter()


# =====================================================
# DATA FIXTURES
# =====================================================

@pytest.fixture
def sample_user_profile_data() -> Dict[str, Any]:
    """Sample user profile data for testing."""
    return {
        "primary_job_title": "Senior Software Engineer",
        "secondary_job_titles": ["Full Stack Developer", "Backend Engineer"],
        "seniority_level": "senior",
        "desired_industries": ["Technology", "Finance"],
        "company_size_preference": "medium",
        "salary_range_min": 100000,
        "salary_range_max": 150000,
        "contract_type": ["full-time"],
        "work_preference": "remote",
        "technical_skills": [
            {"skill": "Python", "years": 5, "confidence": 9},
            {"skill": "FastAPI", "years": 2, "confidence": 8}
        ],
        "soft_skills": ["Communication", "Leadership"],
        "tools_technologies": ["Docker", "PostgreSQL", "Git"],
        "preferred_keywords": ["python", "fastapi", "remote"],
        "writing_tone": "professional",
        "preferred_language": "en"
    }


@pytest.fixture
def sample_cv_file():
    """
    Create a mock CV file for upload testing.
    """
    from io import BytesIO

    # Mock PDF content
    pdf_content = b"%PDF-1.4\n1 0 obj\n<<\n/Type /Catalog\n>>\nendobj\nMock PDF content for testing"

    return {
        "filename": "test_resume.pdf",
        "content": BytesIO(pdf_content),
        "content_type": "application/pdf"
    }


@pytest.fixture
def sample_job_data() -> Dict[str, Any]:
    """Sample job listing data for testing."""
    return {
        "title": "Senior Python Developer",
        "company": "Tech Innovations Inc",
        "location": "Remote",
        "description": "We are looking for an experienced Python developer with 5+ years of experience...",
        "job_link": "https://example.com/jobs/12345",
        "source": "linkedin",
        "job_type": "full-time",
        "remote_type": "remote",
        "salary_range": "$120,000 - $150,000"
    }


# =====================================================
# UTILITY FIXTURES
# =====================================================

@pytest.fixture(autouse=True)
def reset_app_state():
    """
    Reset application state between tests.

    This runs automatically before each test.
    """
    # Clear any dependency overrides
    app.dependency_overrides.clear()

    yield

    # Cleanup after test
    app.dependency_overrides.clear()


@pytest.fixture
def temp_file():
    """
    Create temporary files for upload tests.
    """
    import tempfile
    import os

    created_files = []

    def _create_temp_file(content: bytes = b"Test content", suffix=".pdf"):
        temp = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
        temp.write(content)
        temp.close()
        created_files.append(temp.name)
        return temp.name

    yield _create_temp_file

    # Cleanup
    for file_path in created_files:
        try:
            os.unlink(file_path)
        except:
            pass


# =====================================================
# ASYNC TEST SUPPORT
# =====================================================

@pytest.fixture
def event_loop():
    """
    Create an event loop for async tests.

    Required for pytest-asyncio.
    """
    import asyncio
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


# =====================================================
# ENVIRONMENT CONFIGURATION
# =====================================================

@pytest.fixture(scope="session", autouse=True)
def test_environment():
    """
    Set up test environment variables.

    This runs once per test session.
    """
    # Store original values
    original_env = dict(os.environ)

    # Set test environment
    os.environ["ENVIRONMENT"] = "test"
    os.environ["DEBUG"] = "False"

    yield

    # Restore original environment
    os.environ.clear()
    os.environ.update(original_env)
