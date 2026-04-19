# How to Fix Database Test Errors

## Problem

Tests are failing with SQLAlchemy connection errors because they're trying to connect to the real PostgreSQL database instead of using mocked database sessions.

## Solution

Add the `override_get_db` fixture to any test that makes API calls to endpoints that use the database.

## Quick Fix Pattern

### Before (Failing):
```python
def test_list_cvs_empty(
    self,
    client: TestClient,
    mock_authenticated_user: str,
    auth_headers: dict
):
    response = client.get("/api/v1/cvs/", headers=auth_headers)
    assert response.status_code == 200
```

### After (Working):
```python
def test_list_cvs_empty(
    self,
    client: TestClient,
    mock_authenticated_user: str,
    auth_headers: dict,
    override_get_db  # <-- ADD THIS
):
    response = client.get("/api/v1/cvs/", headers=auth_headers)
    assert response.status_code == 200
```

## Apply to All Files

### tests/test_cvs.py
Add `override_get_db` to these test methods:
- `test_list_cvs_empty`
- `test_list_cvs_with_data`
- `test_get_active_cv_exists`
- `test_get_active_cv_not_found`
- `test_get_cv_by_id`
- `test_activate_cv`
- `test_activate_already_active_cv`
- `test_activate_nonexistent_cv`
- `test_delete_cv_success`
- `test_delete_nonexistent_cv`
- `test_get_download_url`

### tests/test_jobs.py
Add `override_get_db` to these test methods:
- `test_search_jobs_empty`
- `test_search_jobs_with_data`
- `test_search_jobs_with_query`
- `test_search_jobs_with_location_filter`
- `test_search_jobs_with_source_filter`
- `test_search_jobs_pagination`
- `test_get_job_by_id`
- `test_get_nonexistent_job`
- `test_start_scraping_job`
- `test_get_scraping_job_status`
- `test_list_scraping_jobs`

### tests/test_profiles.py
Add `override_get_db` to these test methods:
- `test_get_profile_not_found`
- `test_get_existing_profile`
- `test_create_profile_success`
- `test_create_profile_invalid_seniority`
- `test_create_profile_invalid_work_preference`
- `test_update_profile_success`
- `test_update_nonexistent_profile`
- `test_partial_update`
- And all other profile tests

## Automated Fix Script

Here's a Python script to automatically add the fixture:

```python
import re

def add_override_db_fixture(file_path):
    with open(file_path, 'r') as f:
        content = f.read()

    # Pattern: function definition with client, mock_authenticated_user, auth_headers
    # but WITHOUT override_get_db
    pattern = r'(def test_\w+\(\s*self,\s*client: TestClient,\s*mock_authenticated_user: str,\s*auth_headers: dict)(\s*\))'

    # Replace with added override_get_db
    replacement = r'\1,\n        override_get_db\2'

    new_content = re.sub(pattern, replacement, content)

    with open(file_path, 'w') as f:
        f.write(new_content)

# Apply to test files
add_override_db_fixture('tests/test_cvs.py')
add_override_db_fixture('tests/test_jobs.py')
add_override_db_fixture('tests/test_profiles.py')
```

## Manual Fix (Recommended for Production Code)

1. Open each test file
2. Find test methods that call API endpoints
3. Add `override_get_db` parameter after `auth_headers`
4. Run `pytest` to verify

## Why This Works

The `override_get_db` fixture (defined in `conftest.py`) replaces FastAPI's `get_db()` dependency with a mocked database session. This prevents tests from:
- Connecting to real PostgreSQL
- Making actual database queries
- Requiring database setup/teardown

## Alternative: Use Markers

You could also mark tests that need database mocking:

```python
@pytest.mark.usefixtures("override_get_db")
class TestCVRetrieval:
    def test_list_cvs_empty(
        self,
        client: TestClient,
        mock_authenticated_user: str,
        auth_headers: dict
    ):
        # No need to add override_get_db parameter
        # The marker applies it automatically
        pass
```

## Verify the Fix

After applying, run:
```bash
pytest tests/test_cvs.py::TestCVRetrieval -v
```

All tests should now pass or fail with assertion errors (not connection errors).

## Expected Results After Fix

Before: `19 ERRORS` (connection failures)
After: Tests either `PASS` or `FAIL` with assertion errors (logic issues, not infrastructure)

The goal is to eliminate all SQLAlchemy connection errors.
