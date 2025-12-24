# Backend Testing Guide

Comprehensive testing infrastructure for the AI-Powered JobHunt Pro backend.

## Quick Start

### Install Test Dependencies

```bash
cd backend
source venv/bin/activate  # or venv\Scripts\activate on Windows
pip install -r requirements.txt
```

### Run All Tests

```bash
# Run all tests with coverage
pytest

# Run with verbose output
pytest -v

# Run specific test file
pytest tests/test_auth.py

# Run specific test class
pytest tests/test_profiles.py::TestProfileCreation

# Run specific test
pytest tests/test_profiles.py::TestProfileCreation::test_create_profile_success
```

## Test Organization

### Test Structure

```
tests/
├── conftest.py              # Shared fixtures and configuration
├── test_auth.py             # Authentication tests
├── test_profiles.py         # User profile tests
├── test_cvs.py              # CV management tests
├── test_ai_router.py        # AI model router tests
└── test_jobs.py             # Job scraping and search tests
```

### Test Markers

Tests are organized with markers for easy filtering:

```bash
# Run only unit tests (fast, no external dependencies)
pytest -m unit

# Run only integration tests
pytest -m integration

# Run only authentication tests
pytest -m auth

# Run profile-related tests
pytest -m profile

# Run CV-related tests
pytest -m cv

# Run job-related tests
pytest -m jobs

# Run AI-related tests
pytest -m ai

# Exclude slow tests
pytest -m "not slow"
```

## Test Fixtures

### Database Fixtures

- `test_engine` - SQLite in-memory database engine (session scope)
- `db_session` - Database session with automatic rollback (function scope)
- `client` - FastAPI TestClient with database override

### Authentication Fixtures

- `mock_user_id` - Generate a mock user ID
- `mock_access_token` - Mock access token for testing
- `auth_headers` - Pre-built authorization headers
- `mock_authenticated_user` - Mock authenticated user dependency

### Data Fixtures

- `sample_user_profile_data` - Sample profile data dictionary
- `create_test_profile` - Factory for creating test profiles
- `sample_cv_data` - Sample CV parsed data
- `create_test_cv` - Factory for creating test CVs
- `sample_job_data` - Sample job listing data
- `create_test_job` - Factory for creating test jobs

### Mock Fixtures

- `mock_supabase_storage` - Mock Supabase Storage operations
- `mock_ai_router` - Mock AI router (no actual API calls)
- `temp_file` - Create temporary files for upload tests

## Coverage

### Generate Coverage Report

```bash
# HTML coverage report
pytest --cov=app --cov-report=html

# View report
open htmlcov/index.html  # macOS
xdg-open htmlcov/index.html  # Linux
start htmlcov/index.html  # Windows
```

### Coverage Goals

- **Target**: 80%+ overall coverage
- **Critical paths**: 90%+ coverage
  - Authentication
  - Profile CRUD
  - CV upload and parsing
  - Job scraping

## Writing New Tests

### Example: Testing a New Endpoint

```python
import pytest
from fastapi.testclient import TestClient

@pytest.mark.unit
def test_my_endpoint(client: TestClient, auth_headers: dict):
    """Test description."""
    response = client.get("/api/v1/my-endpoint", headers=auth_headers)

    assert response.status_code == 200
    data = response.json()
    assert "expected_field" in data
```

### Example: Testing with Database

```python
@pytest.mark.integration
def test_database_operation(
    client: TestClient,
    db_session: Session,
    create_test_profile
):
    """Test that requires database."""
    # Create test data
    profile = create_test_profile(primary_job_title="Engineer")

    # Test operation
    # ...

    # Assertions
    assert profile.id is not None
```

### Example: Testing Async Functions

```python
import pytest

@pytest.mark.asyncio
async def test_async_function():
    """Test async function."""
    result = await my_async_function()
    assert result is not None
```

## Best Practices

### 1. Test Naming

- Use descriptive names: `test_<what>_<when>_<expected>`
- Example: `test_create_profile_invalid_seniority_returns_422`

### 2. Test Organization

- Group related tests in classes
- Use markers for categorization
- Keep tests focused (one assertion per test when possible)

### 3. Test Data

- Use fixtures for reusable test data
- Don't hardcode IDs or timestamps
- Clean up after tests (fixtures handle this)

### 4. Assertions

```python
# Good - specific assertion
assert response.status_code == 200

# Good - multiple specific checks
assert data["id"] is not None
assert data["title"] == "Expected Title"

# Avoid - too generic
assert data
```

### 5. Mocking

```python
# Mock external services
@pytest.fixture
def mock_external_api(monkeypatch):
    def mock_call(*args, **kwargs):
        return {"success": True}

    monkeypatch.setattr("module.function", mock_call)
    return mock_call
```

## Common Issues

### Issue: Tests fail with database errors

**Solution**: Ensure you're using the `db_session` fixture, which automatically rolls back changes.

### Issue: Authentication tests fail

**Solution**: Use the `mock_authenticated_user` fixture to bypass real authentication.

### Issue: Async tests not running

**Solution**: Add `@pytest.mark.asyncio` decorator and install `pytest-asyncio`.

### Issue: Fixtures not found

**Solution**: Ensure `conftest.py` is in the `tests/` directory.

## Continuous Integration

Tests are designed to run in CI/CD pipelines:

```yaml
# Example GitHub Actions
- name: Run tests
  run: |
    cd backend
    pytest --cov=app --cov-report=xml

- name: Upload coverage
  uses: codecov/codecov-action@v3
  with:
    file: ./backend/coverage.xml
```

## Performance

### Speed Up Tests

```bash
# Run tests in parallel (requires pytest-xdist)
pip install pytest-xdist
pytest -n auto

# Run only failed tests from last run
pytest --lf

# Run failed tests first
pytest --ff
```

### Test Timing

```bash
# Show slowest tests
pytest --durations=10
```

## Debugging Tests

```bash
# Drop into debugger on failure
pytest --pdb

# Show print statements
pytest -s

# Very verbose output
pytest -vv
```

## Next Steps

1. **Increase coverage**: Aim for 80%+ coverage
2. **Add integration tests**: Test complete workflows
3. **Add performance tests**: Test with large datasets
4. **Add security tests**: Test auth bypass attempts
5. **Add load tests**: Use locust or similar tools

## Resources

- [pytest documentation](https://docs.pytest.org/)
- [FastAPI testing](https://fastapi.tiangolo.com/tutorial/testing/)
- [pytest-asyncio](https://pytest-asyncio.readthedocs.io/)
