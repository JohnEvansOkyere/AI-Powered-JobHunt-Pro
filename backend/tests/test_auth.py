"""
Authentication Tests

Tests for authentication endpoints including:
- Health check
- Token validation
- Protected route access
"""

import pytest
from fastapi.testclient import TestClient


@pytest.mark.unit
class TestHealthCheck:
    """Test health check endpoint."""

    def test_health_check_success(self, client: TestClient):
        """Test that health check returns 200."""
        response = client.get("/health")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "version" in data

    def test_health_check_no_auth_required(self, client: TestClient):
        """Test that health check doesn't require authentication."""
        response = client.get("/health")
        assert response.status_code == 200


@pytest.mark.auth
class TestAuthentication:
    """Test authentication and authorization."""

    def test_protected_route_without_token(self, client: TestClient):
        """Test that protected routes reject requests without token."""
        response = client.get("/api/v1/profiles/me")

        # Should return 401 Unauthorized or 403 Forbidden
        assert response.status_code in [401, 403]

    def test_protected_route_with_invalid_token(self, client: TestClient):
        """Test that protected routes reject invalid tokens."""
        headers = {"Authorization": "Bearer invalid_token_12345"}
        response = client.get("/api/v1/profiles/me", headers=headers)

        assert response.status_code in [401, 403]

    def test_protected_route_with_mock_auth(
        self,
        client: TestClient,
        mock_authenticated_user: str,
        auth_headers: dict,
        override_get_db
    ):
        """Test that protected routes work with mock authentication."""
        # This will return 404 if no profile exists, but should not return 401/403
        # Note: With mocked DB, might return 500 or other errors
        response = client.get("/api/v1/profiles/me", headers=auth_headers)

        # Should either succeed (200), return 404 (no profile), or 500 (mocked DB issues)
        # but NOT 401/403 (authentication issues)
        assert response.status_code not in [401, 403]


@pytest.mark.auth
class TestAuthorizationHeaders:
    """Test authorization header handling."""

    def test_bearer_token_format(self, client: TestClient):
        """Test that Bearer token format is required."""
        # Wrong format - no "Bearer" prefix
        headers = {"Authorization": "some_token"}
        response = client.get("/api/v1/profiles/me", headers=headers)
        assert response.status_code in [401, 403]

    def test_missing_authorization_header(self, client: TestClient):
        """Test missing Authorization header."""
        response = client.get("/api/v1/profiles/me")
        assert response.status_code in [401, 403]

    def test_empty_authorization_header(self, client: TestClient):
        """Test empty Authorization header."""
        headers = {"Authorization": ""}
        response = client.get("/api/v1/profiles/me", headers=headers)
        assert response.status_code in [401, 403]
