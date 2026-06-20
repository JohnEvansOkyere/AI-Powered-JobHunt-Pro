"""Security response headers for API responses."""

from __future__ import annotations

from starlette.types import ASGIApp, Receive, Scope, Send

from app.core.config import settings


class SecurityHeadersMiddleware:
    """Attach conservative browser-facing security headers to every response."""

    def __init__(self, app: ASGIApp):
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        async def send_with_headers(message):
            if message["type"] == "http.response.start":
                headers = message.setdefault("headers", [])
                existing = {key.lower() for key, _ in headers}

                def add_header(name: str, value: str) -> None:
                    key = name.lower().encode("latin-1")
                    if key not in existing:
                        headers.append((key, value.encode("latin-1")))

                add_header("Content-Security-Policy", "default-src 'none'; frame-ancestors 'none'")
                add_header("X-Frame-Options", "DENY")
                add_header("X-Content-Type-Options", "nosniff")
                add_header("Referrer-Policy", "no-referrer")
                add_header("Permissions-Policy", "geolocation=(), microphone=(), camera=()")
                add_header("Cross-Origin-Opener-Policy", "same-origin")
                if settings.is_production:
                    add_header("Strict-Transport-Security", "max-age=31536000; includeSubDomains")

            await send(message)

        await self.app(scope, receive, send_with_headers)
