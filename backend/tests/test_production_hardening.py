"""Production hardening regression tests."""

import asyncio

from fastapi import HTTPException

from app.core.config import settings
from app.core.rate_limit import RateLimit, enforce_rate_limit
from app.api.v1.endpoints import jobs, recommendations
from app.middleware.request_size_limit import RequestSizeLimitMiddleware
from app.middleware.security_headers import SecurityHeadersMiddleware
from app.services.external_job_parser import ExternalJobParser


def test_external_parser_rejects_non_https_url():
    parser = ExternalJobParser()

    try:
        asyncio.run(parser._validate_public_url("http://example.com/jobs/1"))
    except ValueError as exc:
        assert "HTTPS" in str(exc)
    else:
        raise AssertionError("Expected non-HTTPS URL to be rejected")


def test_external_parser_rejects_private_and_metadata_ips():
    parser = ExternalJobParser()

    blocked_urls = [
        "https://127.0.0.1/jobs",
        "https://10.0.0.10/jobs",
        "https://172.16.0.5/jobs",
        "https://192.168.1.20/jobs",
        "https://169.254.169.254/latest/meta-data",
        "https://[::1]/jobs",
    ]

    for url in blocked_urls:
        try:
            asyncio.run(parser._validate_public_url(url))
        except ValueError:
            continue
        raise AssertionError(f"Expected blocked URL to be rejected: {url}")


def test_external_parser_rejects_embedded_credentials():
    parser = ExternalJobParser()

    try:
        asyncio.run(parser._validate_public_url("https://user:pass@example.com/jobs"))
    except ValueError as exc:
        assert "credentials" in str(exc)
    else:
        raise AssertionError("Expected URL credentials to be rejected")


def test_cron_endpoints_fail_closed_without_secret(monkeypatch):
    monkeypatch.setattr(settings, "CRON_SECRET", "")

    async def call_endpoints():
        results = []
        for call in (
            lambda: jobs.trigger_cleanup_old_jobs(None),
            lambda: jobs.generate_recommendations_for_all_users(None, db=object()),
            lambda: recommendations.generate_all(None, db=object()),
        ):
            try:
                await call()
            except HTTPException as exc:
                results.append(exc.status_code)
        return results

    assert asyncio.run(call_endpoints()) == [401, 401, 403]


def test_security_headers_are_present():
    async def dummy_app(scope, receive, send):
        await send(
            {
                "type": "http.response.start",
                "status": 200,
                "headers": [],
            }
        )
        await send({"type": "http.response.body", "body": b"ok"})

    async def call_middleware():
        sent = []

        async def receive():
            return {"type": "http.request", "body": b"", "more_body": False}

        async def send(message):
            sent.append(message)

        middleware = SecurityHeadersMiddleware(dummy_app)
        await middleware(
            {
                "type": "http",
                "method": "GET",
                "path": "/",
                "headers": [],
            },
            receive,
            send,
        )
        return sent

    start = asyncio.run(call_middleware())[0]
    headers = {
        key.decode("latin-1"): value.decode("latin-1")
        for key, value in start["headers"]
    }
    assert headers["x-frame-options"] == "DENY"
    assert headers["x-content-type-options"] == "nosniff"
    assert headers["referrer-policy"] == "no-referrer"
    assert "default-src 'none'" in headers["content-security-policy"]


def test_request_size_limit_rejects_chunked_body():
    async def dummy_app(scope, receive, send):
        await send(
            {
                "type": "http.response.start",
                "status": 200,
                "headers": [],
            }
        )
        await send({"type": "http.response.body", "body": b"ok"})

    async def call_middleware():
        sent = []

        async def receive():
            return {"type": "http.request", "body": b"x", "more_body": False}

        async def send(message):
            sent.append(message)

        middleware = RequestSizeLimitMiddleware(dummy_app, max_size=10)
        await middleware(
            {
                "type": "http",
                "method": "POST",
                "path": "/api/v1/jobs/external/from-text",
                "headers": [(b"transfer-encoding", b"chunked")],
                "query_string": b"",
                "http_version": "1.1",
                "scheme": "http",
                "client": ("127.0.0.1", 12345),
                "server": ("testserver", 80),
            },
            receive,
            send,
        )
        return sent

    sent = asyncio.run(call_middleware())
    assert sent[0]["type"] == "http.response.start"
    assert sent[0]["status"] == 411


def test_redis_rate_limit_blocks_after_limit(monkeypatch):
    class FakeRedis:
        def __init__(self):
            self.counts = {}

        async def incr(self, key):
            self.counts[key] = self.counts.get(key, 0) + 1
            return self.counts[key]

        async def expire(self, key, seconds):
            return True

        async def ttl(self, key):
            return 60

    fake_redis = FakeRedis()

    async def fake_get_async_redis():
        return fake_redis

    monkeypatch.setattr("app.core.rate_limit.get_async_redis", fake_get_async_redis)

    async def call_limiter():
        from starlette.requests import Request

        request = Request(
            {
                "type": "http",
                "method": "POST",
                "path": "/expensive",
                "headers": [],
                "client": ("203.0.113.10", 12345),
                "server": ("testserver", 80),
                "scheme": "https",
            }
        )
        policy = RateLimit("test", limit=2, window_seconds=60)
        await enforce_rate_limit(request, policy, subject="user-1")
        await enforce_rate_limit(request, policy, subject="user-1")
        try:
            await enforce_rate_limit(request, policy, subject="user-1")
        except HTTPException as exc:
            return exc.status_code, exc.headers
        raise AssertionError("Expected rate limit to be exceeded")

    status_code, headers = asyncio.run(call_limiter())
    assert status_code == 429
    assert headers["Retry-After"] == "60"
