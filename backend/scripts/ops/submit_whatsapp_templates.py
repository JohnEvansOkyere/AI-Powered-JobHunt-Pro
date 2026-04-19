#!/usr/bin/env python3
"""
WhatsApp Cloud API — template submission helper.

Meta approves templates through the Business Manager UI or the Graph API.
This script prints **ready-to-paste** JSON bodies for the three templates
from ``docs/RECOMMENDATIONS_V2_PLAN.md`` §6.10 plus example ``curl`` lines
so you can submit them without hunting the docs.

It does **not** auto-submit unless you pass ``--execute`` (which requires
``WHATSAPP_BUSINESS_ACCOUNT_ID`` + ``WHATSAPP_ACCESS_TOKEN`` with the
``whatsapp_business_management`` scope).

Usage::

    cd backend
    venv/bin/python scripts/ops/submit_whatsapp_templates.py
    venv/bin/python scripts/ops/submit_whatsapp_templates.py --execute
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from app.core.config import settings  # noqa: E402


def _otp_template() -> dict:
    return {
        "name": "otp_verification",
        "language": "en",
        "category": "AUTHENTICATION",
        "components": [
            {
                "type": "BODY",
                "text": "Your JobHunt Pro verification code is {{1}}. It expires in 10 minutes.",
            },
            {
                "type": "FOOTER",
                "text": "Do not share this code.",
            },
        ],
    }


def _digest_template() -> dict:
    return {
        "name": "daily_job_digest",
        "language": "en",
        "category": "MARKETING",
        "components": [
            {
                "type": "BODY",
                "text": (
                    "Hi {{1}}, here are your top job matches today:\n\n"
                    "{{2}}\n\n"
                    "Open your picks: {{3}}"
                ),
            },
        ],
    }


def _unsub_template() -> dict:
    return {
        "name": "unsubscribe_confirmation",
        "language": "en",
        "category": "UTILITY",
        "components": [
            {
                "type": "BODY",
                "text": "You have been unsubscribed from JobHunt Pro WhatsApp alerts. Reply START to re-enable.",
            },
        ],
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="WhatsApp template helper")
    parser.add_argument(
        "--execute",
        action="store_true",
        help="POST each template to the Graph API (requires WABA id + token).",
    )
    args = parser.parse_args(argv)

    waba = (settings.WHATSAPP_BUSINESS_ACCOUNT_ID or "").strip()
    ver = settings.WHATSAPP_GRAPH_API_VERSION.strip().lstrip("/")
    token = (settings.WHATSAPP_ACCESS_TOKEN or "").strip()

    templates = [_otp_template(), _digest_template(), _unsub_template()]

    print("=" * 72)
    print("WhatsApp Cloud API — template bodies (RECOMMENDATIONS_V2_PLAN §6.10)")
    print("=" * 72)
    for t in templates:
        print(json.dumps(t, indent=2))
        print("-" * 72)

    url_base = f"https://graph.facebook.com/{ver}/{waba}/message_templates"
    print("\nExample curl (one template — paste JSON from above):\n")
    print(
        f'  curl -X POST "{url_base}" \\\n'
        f'    -H "Authorization: Bearer $WHATSAPP_ACCESS_TOKEN" \\\n'
        f'    -H "Content-Type: application/json" \\\n'
        f"    -d @template.json\n"
    )

    if not args.execute:
        print("Dry-run only. Re-run with --execute to POST via Graph API.\n")
        return 0

    if not waba or not token:
        print("ERROR: WHATSAPP_BUSINESS_ACCOUNT_ID and WHATSAPP_ACCESS_TOKEN must be set for --execute.", file=sys.stderr)
        return 1

    import httpx

    for t in templates:
        name = t["name"]
        resp = httpx.post(
            url_base,
            headers={"Authorization": f"Bearer {token}"},
            json=t,
            timeout=60.0,
        )
        print(f"POST {name}: HTTP {resp.status_code}")
        try:
            print(json.dumps(resp.json(), indent=2))
        except Exception:
            print(resp.text[:2000])
        if resp.status_code >= 400:
            return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
