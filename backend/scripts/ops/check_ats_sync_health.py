#!/usr/bin/env python3
"""Exit non-zero when the ATS job mirror is stale or failing.

Intended for cron, Uptime Kuma, DigitalOcean alerts, or any monitor that treats
non-zero exit status as unhealthy.
"""

from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.request


def _env(name: str, default: str | None = None) -> str:
    value = os.getenv(name, default)
    if not value:
        print(f"Missing required env var: {name}", file=sys.stderr)
        sys.exit(2)
    return value


def main() -> int:
    api_url = _env("VELOXAHIRE_API_URL", "http://127.0.0.1:8000").rstrip("/")
    cron_secret = _env("CRON_SECRET")
    timeout = float(os.getenv("ATS_SYNC_HEALTH_TIMEOUT_SECONDS", "10"))

    request = urllib.request.Request(
        f"{api_url}/api/v1/ops/ats-sync/status",
        headers={"X-Cron-Secret": cron_secret},
        method="GET",
    )

    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        print(f"ATS sync health check HTTP {exc.code}: {exc.reason}", file=sys.stderr)
        return 2
    except Exception as exc:
        print(f"ATS sync health check failed: {exc}", file=sys.stderr)
        return 2

    print(json.dumps(payload, sort_keys=True))

    if payload.get("last_error"):
        print(f"ATS sync has last_error: {payload['last_error']}", file=sys.stderr)
        return 1
    if payload.get("stale"):
        age = payload.get("age_seconds")
        print(f"ATS sync is stale; age_seconds={age}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
